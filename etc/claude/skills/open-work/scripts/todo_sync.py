"""
Reconcile the tracker's threads against the latest daily TODO.

The TODO owns two things the tracker only mirrors:

  which work exists   — one level-2 headline per piece of work under *WORK*
  how it is ranked    — the `[#A]`-`[#D]` priority cookie

A headline is linked to a thread by `[[ow:<slug>][text]]`, which displays as just
the text. Position in the list is used **only** to seed a priority for an item
that has no cookie yet, so nothing has to be typed twice.

  python3 todo_sync.py                report drift; propose links and priorities
  python3 todo_sync.py --apply        mirror TODO priorities into OPEN_WORK.md
  python3 todo_sync.py --write-links  write links, seed missing cookies, drop old tags
  python3 todo_sync.py --adopt        also create a stub thread for each new TODO item
"""

import argparse
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import orgtodo
import closed_work
import tracker

TODO_ROOT = Path(os.environ.get("HQ_TODO_ROOT", Path.home() / ".hq-secret/etc/todo"))
WORK_SECTION = "*WORK*"
KEYWORD_RANK = {"IN-PROGRESS": 0, "AWAITING-REVIEW": 1, "HANDED-OFF": 1, "TODO": 2,
                "DONE": 9, "CANCELLED": 9}
SLUG_STOP_WORDS = {"the", "a", "an", "and", "or", "of", "to", "for", "in", "on", "into",
                   "with", "at", "up", "out", "from", "this", "that", "is", "it"}


def latest_daily_todo() -> Path:
    candidates = sorted(
        path for path in TODO_ROOT.glob("[0-9][0-9][0-9][0-9]/[0-9][0-9]/[0-9][0-9].org")
        if not path.name.startswith((".", "#")) and not path.name.endswith("~")
    )
    if not candidates:
        raise SystemExit(f"no daily TODO found under {TODO_ROOT}")
    return candidates[-1]


def parse_todo(path: Path) -> list:
    """
    Every level-2 headline in the WORK section, in file order, with its children.
    """
    items, section, current = [], None, None
    for line in path.read_text().splitlines():
        top = re.match(r"^\* +(.*)$", line)
        if top:
            section = top.group(1).strip()
            continue
        if section != WORK_SECTION:
            continue
        headline = orgtodo.parse_headline(line)
        if headline and headline["level"] == 2:
            headline.update({"children": [], "notes": [], "position": len(items)})
            current = headline
            items.append(current)
        elif headline and current is not None:
            current["children"].append(headline)
        elif current is not None and line.strip():
            current["notes"].append(line.strip())
    return items


def effective_keyword(item) -> str:
    """
    A parent marked DONE with an open child is not done; the strongest open child wins.
    """
    keywords = [item["keyword"] or "TODO"] + [child["keyword"] or "TODO" for child in item["children"]]
    open_keywords = [keyword for keyword in keywords if keyword not in ("DONE", "CANCELLED")]
    if not open_keywords:
        return item["keyword"] or "TODO"
    return min(open_keywords, key=lambda keyword: KEYWORD_RANK.get(keyword, 5))


def seeded_priority(item, total: int) -> str:
    """
    A priority for an item that carries no cookie yet: where it sits in the list,
    adjusted by its keyword. Only ever used to seed — a cookie always wins.
    """
    keyword = effective_keyword(item)
    if keyword in ("DONE", "CANCELLED"):
        return "P3"
    fraction = item["position"] / max(total - 1, 1)
    if keyword == "IN-PROGRESS" or fraction <= 0.25:
        return "P1"
    if keyword in ("AWAITING-REVIEW", "HANDED-OFF") or fraction <= 0.55:
        return "P2"
    return "P3"


def slug_for(title: str, taken: set) -> str:
    """
    A short, whole-word identifier — never a truncated word, since the user reads it.
    """
    words = [word for word in re.findall(r"[a-z0-9]+", title.lower())
             if word not in SLUG_STOP_WORDS and len(word) > 1]
    slug = "_".join(words[:4]) or "untitled"
    candidate, suffix = slug, 2
    while candidate in taken:
        candidate, suffix = f"{slug}_{suffix}", suffix + 1
    taken.add(candidate)
    return candidate


def todo_field(item, total: int, parent=None) -> str:
    if parent is not None:
        return f"`{item['title']}` ({item['keyword'] or 'TODO'}, under `{parent['title']}`)"
    return f"`{item['title']}` ({effective_keyword(item)}, #{item['position'] + 1} of {total})"


def stub_thread(item, slug, total):
    children = ", ".join(f"**{child['title']}**" for child in item["children"]
                         if child["keyword"] not in ("DONE", "CANCELLED"))
    nxt = f"open sub-items: {children}." if children else "not started — no detail captured yet."
    if item["notes"]:
        nxt += " From the TODO: " + " ".join(item["notes"])
    return {
        "slug": slug,
        "title": item["title"],
        "fields": {
            "status": "review" if effective_keyword(item) in ("AWAITING-REVIEW", "HANDED-OFF") else "active",
            "priority": item["priority"] or seeded_priority(item, total),
            "todo": todo_field(item, total),
            "waiting on": item["handoff"] or "you",
            "next": nxt,
            "updated": f"{__import__('datetime').date.today().isoformat()} — adopted from the TODO; "
                       "no repo work linked yet.",
        },
        "paragraphs": [],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, default=None)
    parser.add_argument("--apply", action="store_true", help="mirror TODO priorities into the tracker")
    parser.add_argument("--write-links", action="store_true", help="write ow links and missing cookies")
    parser.add_argument("--adopt", action="store_true", help="create a stub thread for each new item")
    parser.add_argument("--tidy", action="store_true",
                        help="drop finished WORK items and order the rest by priority (the user asked "
                             "for this on 2026-10-29; run it after --apply so cookies are settled)")
    args = parser.parse_args()

    todo_path = args.file or latest_daily_todo()
    if args.tidy:
        removed, reordered = orgtodo.tidy(todo_path, WORK_SECTION)
        for title in removed:
            print(f"removed finished item: {title}")
        print(f"tidied {todo_path}: {len(removed)} removed, "
              f"{'reordered by priority' if reordered else 'order unchanged'}\n")
    items = parse_todo(todo_path)
    threads = tracker.parse_threads(tracker.TRACKER.read_text())
    by_slug = {thread["slug"]: thread for thread in threads}
    total = len(items)
    print(f"TODO: {todo_path}  ({total} WORK items)\ntracker: {len(threads)} threads\n")

    taken = set(by_slug)
    linked, linked_children, adopted, dangling = [], [], [], []
    for item in items:
        for child in item["children"]:
            if child["slug"] and child["slug"] in by_slug:
                linked_children.append((child, item, by_slug[child["slug"]]))
            elif child["slug"]:
                dangling.append(child)
        if item["slug"] and item["slug"] in by_slug:
            linked.append((item, by_slug[item["slug"]]))
        elif item["slug"]:
            dangling.append(item)
        else:
            item["proposed_slug"] = slug_for(item["title"], taken)
            adopted.append(item)

    print("=== LINKED ===")
    for item, thread in linked:
        marker = "link" if item["linked"] else "tag "
        print(f"  [{marker}] {thread['slug']:28s} {effective_keyword(item):15s} "
              f"{item['cookie'] or '-'}  {item['title'][:44]}")
        for child, parent, child_thread in linked_children:
            if parent is item:
                marker = "link" if child["linked"] else "----"
                print(f"    [{marker}] {child_thread['slug']:26s} {child['keyword'] or 'TODO':15s} "
                      f"{child['cookie'] or '^'}  {child['title'][:42]}")

    # a link to an archived thread is history, not drift
    archived = closed_work.archived_slugs()
    archived_links = [item for item in dangling if item["slug"] in archived]
    dangling = [item for item in dangling if item["slug"] not in archived]
    if archived_links:
        print(f"\n({len(archived_links)} TODO item(s) link to archived threads in closed-work/)")
    if dangling:
        print("\n=== LINKED TO A MISSING THREAD ===")
        for item in dangling:
            print(f"  {item['slug']:28s} {item['title'][:50]}")

    print("\n=== IN TODO, NOT TRACKED ===")
    for item in adopted:
        print(f"  #{item['position'] + 1:<3} {effective_keyword(item):15s} "
              f"[#{item['cookie'] or '?'}] {item['title'][:52]}"
              f"   -> slug `{item['proposed_slug']}`")
    if not adopted:
        print("  (none)")

    linked_slugs = ({thread["slug"] for _, thread in linked}
                    | {thread["slug"] for _, _, thread in linked_children})
    print("\n=== TRACKED, NOT IN TODO ===")
    for thread in threads:
        if thread["slug"] not in linked_slugs:
            print(f"  {thread['slug']:28s} {thread['fields'].get('priority', '?'):12s} "
                  f"{thread['fields'].get('status', '?')}")

    # --- priority: the cookie wins; a missing cookie gets seeded from position ---
    print("\n=== PRIORITY ===")
    wanted_priority, thread_changes = {}, []
    for item, thread in linked:
        current = thread["fields"].get("priority", "").split()[0]
        if item["priority"]:
            source, wanted = "cookie", item["priority"]
        else:
            source, wanted = "seeded", seeded_priority(item, total)
            wanted_priority[id(item)] = wanted
        verdict = "same" if current == wanted else f"{current or '—'} -> {wanted}"
        print(f"  {thread['slug']:28s} {source:6s} {wanted:6s} {verdict}")
        if current != wanted:
            thread_changes.append((thread, wanted))
    for item in adopted:
        if not item["priority"]:
            wanted = seeded_priority(item, total)
            print(f"  {item['proposed_slug']:28s} seeded {wanted:6s} (new)")

    for child, parent, thread in linked_children:
        inherited = parent["priority"] or seeded_priority(parent, total)
        wanted = child["priority"] or inherited
        current = thread["fields"].get("priority", "").split()[0]
        source = "cookie" if child["priority"] else "parent"
        print(f"  {thread['slug']:28s} {source:6s} {wanted:6s} "
              f"{'same' if current == wanted else f'{current} -> {wanted}'}")
        if current != wanted:
            thread_changes.append((thread, wanted))

    handoffs = [(item, thread) for item, thread in linked
                if item["keyword"] == "HANDED-OFF" or item["handoff"]]
    if handoffs:
        print("\n=== HANDED OFF ===")
        for item, thread in handoffs:
            print(f"  {thread['slug']:28s} -> {item['handoff'] or '(nobody named)'}")

    # --- writes ---
    if args.apply:
        for thread, wanted in thread_changes:
            thread["fields"]["priority"] = wanted
        for child, parent, thread in linked_children:
            thread["fields"]["todo"] = todo_field(child, total, parent=parent)
            parent_thread = next((t for i, t in linked if i is parent), None)
            if parent_thread:
                thread["fields"]["parent"] = parent_thread["slug"]
        for item, thread in linked:
            thread["fields"]["todo"] = todo_field(item, total)
            thread["fields"].pop("parent", None)  # promoted out of a fold, or never in one
            if item["handoff"]:
                thread["fields"]["waiting on"] = f"{item['handoff']} — handed off"
                thread["fields"]["status"] = "review"
        if args.adopt:
            for item in adopted:
                threads.append(stub_thread(item, item["proposed_slug"], total))
        tracker.write_threads(threads)
        print(f"\napplied {len(thread_changes)} priority changes"
              + (f" and adopted {len(adopted)} new threads" if args.adopt else ""))

    if args.write_links:
        changes = {}
        for item, thread in linked:
            # render once: a missing link and a missing cookie are the same edit
            rendered = orgtodo.render_headline(
                item, slug=thread["slug"], priority=wanted_priority.get(id(item))
            )
            if rendered != item["raw"]:
                changes[item["raw"]] = rendered
        for child, parent, thread in linked_children:
            rendered = orgtodo.render_headline(child, slug=thread["slug"])
            if rendered != child["raw"]:
                changes[child["raw"]] = rendered
        if args.adopt:
            for item in adopted:
                changes[item["raw"]] = orgtodo.render_headline(
                    item, slug=item["proposed_slug"],
                    priority=item["priority"] or seeded_priority(item, total),
                )
        written = orgtodo.rewrite(todo_path, changes)
        print(f"\nrewrote {written} headlines in {todo_path}"
              + (f" (backup: {todo_path}.pre-ow)" if written else ""))


if __name__ == "__main__":
    main()
