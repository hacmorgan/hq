"""
Fold decisions made on the board back into the tracker and the TODO.

The board writes each priority change, park and hand-off into the artifact's
database. Pull them down first, then run this:

  Artifact  action=read_db  url=<board>  db_op=list  collection=decisions \
            out_dir=~/src/abyss/.open-work/decisions
  python3 .open-work/apply_decisions.py

A thread decision updates the thread *and* the priority cookie on its TODO
headline, so the TODO stays the one place priority is written. A hand-off sets
the headline to `HANDED-OFF` and appends an `[[ow-to:<login>][@login]]` link.
Decisions on a pull request — whether one this user wrote or one waiting on their
review — are kept in decisions.json, which build.py renders on those rows.
"""

import os
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import orgtodo
import todo_sync
import tracker

HERE = Path(os.environ.get("OPEN_WORK_DATA", Path.home() / "src/abyss/.open-work"))  # data, not code
INBOX = HERE / "decisions"
STORE = HERE / "decisions.json"


def load_inbox() -> dict:
    if not INBOX.exists():
        return {}
    decisions = {}
    for path in sorted(INBOX.rglob("*.json")):
        body = json.loads(path.read_text())
        decisions[path.stem] = body.get("data", body)
    return decisions


def main():
    inbox = load_inbox()
    if not inbox:
        print(f"no decision documents under {INBOX} — pull them with Artifact read_db first")
        return

    threads = tracker.parse_threads(tracker.TRACKER.read_text())
    by_slug = {thread["slug"]: thread for thread in threads}

    todo_path = todo_sync.latest_daily_todo()
    parsed = todo_sync.parse_todo(todo_path)
    todo_items = {item["slug"]: item for item in parsed if item["slug"]}
    child_items = {
        child["slug"]: (child, parent)
        for parent in parsed for child in parent["children"] if child["slug"]
    }

    pr_decisions, applied, skipped, org_changes = {}, [], [], {}

    for identifier, decision in sorted(inbox.items()):
        if identifier.startswith("thread__"):
            slug = identifier[len("thread__"):]
            thread = by_slug.get(slug)
            if not thread:
                skipped.append(f"{identifier} (no such thread)")
                continue
            before = thread["fields"].get("priority", "")
            handoff = decision.get("handoff")
            if decision.get("priority"):
                thread["fields"]["priority"] = decision["priority"]
            if handoff:
                thread["fields"]["waiting on"] = (
                    f"{handoff['to']} — handed off {handoff.get('at', '')}".strip()
                )
                thread["fields"]["status"] = "review"

            if decision.get("promote") and slug in child_items:
                child, parent = child_items[slug]
                promoted = orgtodo.render_headline(
                    child, slug=slug, level=2,
                    priority=decision.get("priority") or thread["fields"].get("priority", "P2").split()[0],
                )
                if orgtodo.promote(todo_path, child["raw"], parent["raw"], promoted):
                    thread["fields"].pop("parent", None)
                    applied.append(f"{slug}: promoted out of `{parent['title']}` to a top-level item")
                    continue

            item = todo_items.get(slug)
            if item:
                rendered = orgtodo.render_headline(
                    item,
                    priority=decision.get("priority"),
                    keyword="HANDED-OFF" if handoff else None,
                    handoff=handoff["to"] if handoff else None,
                )
                if rendered != item["raw"]:
                    org_changes[item["raw"]] = rendered
            elif decision.get("priority"):
                # no TODO headline to hold the cookie, so pin it in the tracker
                thread["fields"]["priority"] = f"{decision['priority']} (pinned)"

            applied.append(f"{slug}: {before or '—'} -> {thread['fields']['priority']}"
                           + (f", handed to {handoff['to']}" if handoff else "")
                           + ("" if item else "  [no TODO entry — pinned]"))
        elif identifier.startswith(("pr__", "review__")):
            # a review queue decision is a decision about a PR, stored the same way:
            # park means "not reading this", hand off means "someone else should"
            kind, repo, number = identifier.split("__", 2)
            pr_decisions[f"{repo}#{number}"] = decision
            applied.append(f"{repo}#{number}" + (" (review)" if kind == "review" else "") + ": "
                           + ", ".join(filter(None, [
                               decision.get("priority"),
                               f"handed to {decision['handoff']['to']}" if decision.get("handoff") else None,
                           ])))
        else:
            skipped.append(f"{identifier} (unrecognised id)")

    tracker.write_threads(threads)
    STORE.write_text(json.dumps(pr_decisions, indent=2))
    written = orgtodo.rewrite(todo_path, org_changes) if org_changes else 0

    print(f"applied {len(applied)} decisions:")
    for line in applied:
        print(f"  {line}")
    if skipped:
        print("skipped:")
        for line in skipped:
            print(f"  {line}")
    print(f"\n{written} TODO headlines updated in {todo_path}")
    print(f"PR decisions saved to {STORE} — run build.py, then republish.")


if __name__ == "__main__":
    main()
