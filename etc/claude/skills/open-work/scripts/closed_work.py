"""
The closed-work archive: finished threads and landed PRs, kept for later reference.

OPEN_WORK.md holds only what is in flight. When a thread is `done` and the user has seen it,
it moves here verbatim instead of being deleted, and every PR that leaves the open list
(merged or closed) is logged here with the thread that tracked it.

The archive rolls over monthly: one file per month of closure,
`~/src/abyss/closed-work/YYYY-MM.md`, so no single file grows without bound and a month
can be read on its own.

  python3 closed_work.py archive              move every `done` thread out of OPEN_WORK.md
  python3 closed_work.py archive SLUG ...     move just these (must be `done`)
  python3 closed_work.py archive --dry-run    say what would move
  python3 closed_work.py fold SRC INTO        fold thread SRC into thread INTO, archiving SRC
  python3 closed_work.py find TERM            search every month (slug, title, PR, ticket)
"""

import argparse
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

import tracker

CLOSED_DIR = tracker.HERE.parent / "closed-work"
THREADS_HEADING = "## Threads"
PRS_HEADING = "## Pull requests"
DATE_RE = re.compile(r"\b(20\d\d-\d\d-\d\d)\b")


def month_file(date: str) -> Path:
    """
    The archive file for the month `date` (YYYY-MM-DD) falls in, created on first use.
    """
    path = CLOSED_DIR / f"{date[:7]}.md"
    if not path.exists():
        CLOSED_DIR.mkdir(exist_ok=True)
        path.write_text(
            f"# Closed work — {date[:7]}\n\n"
            "Archived from `~/src/abyss/OPEN_WORK.md` by `.open-work/closed_work.py`. One file per\n"
            "month of closure; search them all with `python3 .open-work/closed_work.py find TERM`.\n\n"
            f"{THREADS_HEADING}\n\n{PRS_HEADING}\n"
        )
    return path


def insert_under(path: Path, heading: str, text: str) -> None:
    """
    Append `text` at the end of the `heading` section of an archive file.
    """
    content = path.read_text()
    start = content.index(heading) + len(heading)
    following = content.find("\n## ", start)
    end = len(content) if following == -1 else following
    section = content[start:end].rstrip("\n")
    content = content[:start] + section + "\n\n" + text.rstrip("\n") + "\n" + content[end:]
    path.write_text(content)


def archived_slugs() -> set:
    """
    Every thread slug the archive holds, across all months.
    """
    slugs = set()
    for path in sorted(CLOSED_DIR.glob("*.md")):
        slugs.update(re.findall(r"^### (\S+) · ", path.read_text(), flags=re.M))
    return slugs


def closed_date(thread) -> str:
    """
    The date a thread closed: the newest date on any of its `Updated:` lines.
    """
    dates = DATE_RE.findall("\n".join(
        line for line in thread["raw"].splitlines() if line.startswith("- **Updated")
    ))
    return max(dates) if dates else datetime.date.today().isoformat()


# --- move finished threads out of OPEN_WORK.md ---

def archive(slugs: list, dry_run: bool) -> None:
    text = tracker.TRACKER.read_text()
    threads = tracker.parse_threads(text)
    by_slug = {thread["slug"]: thread for thread in threads}
    unknown = [slug for slug in slugs if slug not in by_slug]
    if unknown:
        sys.exit(f"no such thread: {', '.join(unknown)}")
    chosen = [by_slug[slug] for slug in slugs] if slugs else [
        thread for thread in threads if thread["fields"].get("status") == "done"
    ]
    not_done = [thread["slug"] for thread in chosen if thread["fields"].get("status") != "done"]
    if not_done:
        sys.exit(f"not `done`, so not archived: {', '.join(not_done)}")
    # a parent with open findings is not finished, whatever its own status says
    open_children = {}
    for thread in threads:
        parent = thread["fields"].get("parent")
        if parent and thread["fields"].get("status") != "done":
            open_children.setdefault(parent, []).append(thread["slug"])
    held = [thread for thread in chosen if thread["slug"] in open_children]
    for thread in held:
        print(f"  kept {thread['slug']}: open sub-threads {', '.join(open_children[thread['slug']])}")
    if held and slugs:
        sys.exit("archive the open sub-threads first, or re-parent them")
    chosen = [thread for thread in chosen if thread not in held]
    if not chosen:
        print("nothing to archive")
        return

    today = datetime.date.today().isoformat()
    for thread in chosen:
        date = closed_date(thread)
        print(f"  {thread['slug']:40s} closed {date} -> closed-work/{date[:7]}.md")
        if dry_run:
            continue
        lines = thread["raw"].splitlines()
        lines.insert(1, f"- **Closed:** {date} (archived {today})")
        insert_under(month_file(date), THREADS_HEADING, "\n".join(lines))
        # drop the block and the blank lines after it; a `---` after the last thread is the
        # threads section's own closing rule, so it stays
        text = re.sub(re.escape(thread["raw"]) + r"\n+", "", text, count=1)
    if not dry_run:
        tracker.TRACKER.write_text(text)
        print(f"archived {len(chosen)} thread(s)")


# --- fold one thread into another ---

def fold(source: str, target: str) -> None:
    """
    Merge `source` into `target`: its Next becomes a sub-bullet under the target's Next, its
    whole block goes to this month's "Merged into other threads", and the target is dated.
    """
    text = tracker.TRACKER.read_text()
    by_slug = {thread["slug"]: thread for thread in tracker.parse_threads(text)}
    for slug in (source, target):
        if slug not in by_slug:
            sys.exit(f"no such thread: {slug}")
    today = datetime.date.today().isoformat()
    moved = by_slug[source]
    status = moved["fields"].get("status", "?")
    next_step = moved["fields"].get("next", "—")
    if len(next_step) > 500:
        next_step = next_step[:500].rsplit(" ", 1)[0] + " …"
    sub_bullet = (f"  - **Folded in from `{source}` ({today}) — {moved['title']}** (was `{status}`, "
                  f"{moved['fields'].get('priority', '?')}). Next was: {next_step} "
                  f"Full text: `closed-work/{today[:7]}.md`.")

    text = re.sub(re.escape(moved["raw"]) + r"\n+", "", text, count=1)
    lines = text.split("\n")
    start = next(i for i, line in enumerate(lines) if line.startswith(f"### {target} "))
    end = next(i for i in range(start + 1, len(lines))
               if lines[i].startswith(("### ", "## ", "<!-- BEGIN")))
    next_line = next((i for i in range(start, end) if lines[i].startswith("- **Next:**")), None)
    if next_line is None:
        sys.exit(f"{target} has no Next: field to fold under")
    insert_at = next_line + 1
    while lines[insert_at].startswith("  "):
        insert_at += 1
    lines.insert(insert_at, sub_bullet)
    updated = next((i for i in range(start, end + 1) if lines[i].startswith("- **Updated:**")), insert_at + 1)
    lines.insert(updated, f"- **Updated:** {today} — folded in `{source}` (one piece of work); its block is "
                          f"archived in `closed-work/{today[:7]}.md`.")
    tracker.TRACKER.write_text("\n".join(lines))
    path = month_file(today)
    if "## Merged into other threads" not in path.read_text():
        path.write_text(path.read_text().rstrip("\n") + "\n\n## Merged into other threads\n")
    insert_under(path, "## Merged into other threads",
                 f"### — Merged {today} into {target}\n\n{moved['raw']}")
    print(f"folded {source} into {target}")


# --- log PRs that left the open list ---

def thread_for_url(url: str, threads: list) -> str:
    for thread in threads:
        if url in thread["raw"]:
            return thread["slug"]
    return ""


def log_prs(records: list) -> None:
    """
    Log PRs that left the open list since the last sweep, under the month they landed or
    closed. Called by sweep.py with the departed records; safe to call twice for the same PR.
    """
    threads = tracker.parse_threads(tracker.TRACKER.read_text())
    for record in records:
        result = subprocess.run(
            ["gh", "pr", "view", str(record["number"]), "-R", record["repo_slug"],
             "--json", "state,mergedAt,closedAt"],
            capture_output=True, text=True, timeout=60,
        )
        info = json.loads(result.stdout) if result.returncode == 0 else {}
        state = info.get("state", "GONE").lower()
        when = (info.get("mergedAt") or info.get("closedAt") or "")[:10] \
            or datetime.date.today().isoformat()
        path = month_file(when)
        already_logged = any(
            line.startswith("- 20") and f"]({record['url']})" in line
            for line in path.read_text().splitlines()
        )
        if already_logged:
            continue
        slug = thread_for_url(record["url"], threads)
        line = (f"- {when} **{state}** [{record['repo']}#{record['number']}]({record['url']}) "
                f"{record['title']}" + (f" — thread `{slug}`" if slug else ""))
        insert_under(path, PRS_HEADING, line)
        print(f"  logged {record['repo']}#{record['number']} ({state}) -> closed-work/{when[:7]}.md")


# --- search ---

def find(term: str) -> None:
    pattern = re.compile(re.escape(term), re.I)
    for path in sorted(CLOSED_DIR.glob("*.md")):
        heading = None
        for line in path.read_text().splitlines():
            if line.startswith("### "):
                heading = line[4:]
            if pattern.search(line):
                where = f"thread {heading}" if heading and not line.startswith("- 20") else "PR log"
                print(f"{path.name}  [{where}]  {line[:160]}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    archive_parser = commands.add_parser("archive")
    archive_parser.add_argument("slugs", nargs="*")
    archive_parser.add_argument("--dry-run", action="store_true")
    fold_parser = commands.add_parser("fold")
    fold_parser.add_argument("source")
    fold_parser.add_argument("target")
    find_parser = commands.add_parser("find")
    find_parser.add_argument("term")
    args = parser.parse_args()
    if args.command == "archive":
        archive(args.slugs, dry_run=args.dry_run)
    elif args.command == "fold":
        fold(args.source, args.target)
    else:
        find(args.term)


if __name__ == "__main__":
    main()
