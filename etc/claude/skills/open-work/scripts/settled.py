"""
Remember the answers an interrogation session has already had, so the next session
spends its questions on what has changed rather than on what was settled last time.

Two kinds of memory, deliberately separate:

  settled.json   one answered question, keyed by what it was about
  `Reviewed:`    a date on the thread itself, written when it was walked through

Both expire the same way: an answer is about the work as it stood that day, so when a
thread's `Updated:` date is newer than the day its question was answered, the answer
no longer covers it and the question is asked again. Nothing here expires on a timer —
a merge pair judged distinct stays distinct until one of the two threads moves.

  python3 settled.py --list
  python3 settled.py --record distinct cluster_instability|drain_pass_cost --note "..."
"""

import os
import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tracker

HERE = Path(os.environ.get("OPEN_WORK_DATA", Path.home() / "src/abyss/.open-work"))  # data, not code
SETTLED = HERE / "settled.json"

# what each group remembers, and how its keys are built
GROUPS = {
    "distinct": "merge candidates judged to be separate work — key `slug_a|slug_b`, sorted",
    "queue_only": "inbound PRs that belong in the review queue, not in a thread — key `repo#number`",
    "confirmed": "hypotheses the user has ruled on — key `slug:first 40 chars of the claim`",
    "acknowledged": "contradictions seen and accepted as they are — key `slug:kind`",
    "live": "stale threads confirmed still live — key `slug`",
    "accepted": "threads whose vague `Next:` the user is happy with — key `slug`",
    "kept": "long-tail PRs deliberately left open — key `repo#number`",
}


def pair_key(one: str, two: str) -> str:
    """
    The order two slugs were asked about is not part of the question.
    """
    return "|".join(sorted([one, two]))


def load() -> dict:
    """
    Read settled.json, upgrading the bare lists an earlier version wrote.
    """
    if not SETTLED.exists():
        return {group: {} for group in GROUPS}
    raw = json.loads(SETTLED.read_text())
    settled = {}
    for group in GROUPS:
        entries = raw.get(group, {})
        if isinstance(entries, list):
            # legacy: a list of keys with no date, so nothing can expire — treat as ancient
            entries = {(pair_key(*entry) if isinstance(entry, list) else entry):
                       {"on": "1970-01-01", "note": ""} for entry in entries}
        settled[group] = entries
    return settled


def save(settled: dict) -> None:
    SETTLED.write_text(json.dumps(settled, indent=2, sort_keys=True) + "\n")


def record(group: str, key: str, note: str = "", on: str = None, settled: dict = None) -> dict:
    """
    Remember one answer. Pass `settled` to batch several before one save.
    """
    if group not in GROUPS:
        raise KeyError(f"unknown group {group!r} — one of {', '.join(GROUPS)}")
    own_save = settled is None
    settled = load() if own_save else settled
    settled.setdefault(group, {})[key] = {"on": on or date.today().isoformat(), "note": note}
    if own_save:
        save(settled)
    return settled


def forget(group: str, key: str) -> bool:
    """
    Drop an answer, so the next session asks again.
    """
    settled = load()
    if settled.get(group, {}).pop(key, None) is None:
        return False
    save(settled)
    return True


def is_settled(group: str, key: str, moved_on: str = None, settled: dict = None) -> bool:
    """
    Whether this question has an answer that still stands.

    `moved_on` is the date the thing it was about last changed — an `Updated:` date,
    usually. An answer older than that is an answer to a different question.
    """
    settled = load() if settled is None else settled
    entry = settled.get(group, {}).get(key)
    if entry is None:
        return False
    return not (moved_on and moved_on > entry.get("on", "1970-01-01"))


# --- the per-thread half: `Reviewed:` says the thread itself was walked through ---
def reviewed_on(thread) -> str:
    """
    The date this thread was last walked through, or None.
    """
    return (thread["fields"].get("reviewed", "") or "").split(" ")[0][:10] or None


def updated_on(thread) -> str:
    return (thread["fields"].get("updated", "") or "").split(" ")[0][:10] or None


def is_fresh(thread) -> bool:
    """
    True when the thread has been reviewed since the last time it moved — the question
    "is this still right?" has an answer that still stands.
    """
    reviewed, updated = reviewed_on(thread), updated_on(thread)
    return bool(reviewed and (not updated or reviewed >= updated))


def mark_reviewed(slugs, note: str = "", on: str = None) -> list:
    """
    Stamp `Reviewed:` on each thread, writing the tracker once.
    """
    on = on or date.today().isoformat()
    threads = tracker.parse_threads(tracker.TRACKER.read_text())
    wanted, stamped = set(slugs), []
    for thread in threads:
        if thread["slug"] in wanted:
            thread["fields"]["reviewed"] = f"{on}{' — ' + note if note else ''}"
            stamped.append(thread["slug"])
    missing = wanted - set(stamped)
    if missing:
        raise KeyError(f"no such thread: {', '.join(sorted(missing))}")
    tracker.write_threads(threads)
    return stamped


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--list", action="store_true", help="print what is remembered")
    parser.add_argument("--record", nargs=2, metavar=("GROUP", "KEY"))
    parser.add_argument("--forget", nargs=2, metavar=("GROUP", "KEY"))
    parser.add_argument("--note", default="")
    parser.add_argument("--reviewed", nargs="*", metavar="SLUG",
                        help="stamp today's date on these threads' `Reviewed:` field")
    args = parser.parse_args()

    if args.record:
        record(group=args.record[0], key=args.record[1], note=args.note)
        print(f"settled {args.record[0]}: {args.record[1]}")
    if args.forget:
        print(("forgot " if forget(group=args.forget[0], key=args.forget[1]) else "not held: ")
              + f"{args.forget[0]}: {args.forget[1]}")
    if args.reviewed:
        print("reviewed " + ", ".join(mark_reviewed(slugs=args.reviewed, note=args.note)))
    if args.list or not any([args.record, args.forget, args.reviewed]):
        settled = load()
        for group, description in GROUPS.items():
            entries = settled.get(group, {})
            print(f"\n=== {group} ({len(entries)}) — {description}")
            for key, entry in sorted(entries.items()):
                print(f"  {entry['on']}  {key}" + (f"  — {entry['note']}" if entry["note"] else ""))
        threads = tracker.parse_threads(tracker.TRACKER.read_text())
        fresh = [thread["slug"] for thread in threads if is_fresh(thread)]
        print(f"\n=== threads reviewed since they last moved ({len(fresh)} of {len(threads)})")
        print("  " + (", ".join(fresh) if fresh else "none yet"))


if __name__ == "__main__":
    main()
