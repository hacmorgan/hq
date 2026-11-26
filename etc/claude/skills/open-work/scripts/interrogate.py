"""
Do the analysis an interrogation session needs, so the session spends its questions
on judgement rather than on lookups.

Emits findings in groups, each row carrying the evidence behind it — a grouping the
user cannot check is a grouping they will rubber-stamp. Nothing here writes: it
proposes, the session asks, and apply steps act.

Questions already answered are not asked again: `settled.json` remembers each answer
and `Reviewed:` dates the thread it was about, and both lapse the moment the thread
moves on — an answer is about the work as it stood that day.

  python3 interrogate.py               every group
  python3 interrogate.py --group agenda merge inbound hypotheses contradictions stale closeout vague
  python3 interrogate.py --all         include what is settled, with a `settled` marker
"""

import os
import argparse
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import settled as settled_store
import tracker

HERE = Path(os.environ.get("OPEN_WORK_DATA", Path.home() / "src/abyss/.open-work"))  # data, not code
# how long a thread may sit untouched before that is itself a question. How important
# the user said it was decides: a P1 quiet for a week is a story, a P3 quiet for a
# month is just a P3.
STALE_DAYS = {"P1": 7, "P2": 21, "P3": 60, "parked": None}
LONG_TAIL_DAYS = 180

TICKET = re.compile(r"\b(?:AFP|FABP|FABPRO|SO)-\d+\b", re.I)
PR_LINK = re.compile(r"github\.com/abyss-solutions/([\w.-]+)/pull/(\d+)")
# words too common in this codebase to be evidence of anything
GENERIC = {"update", "added", "adding", "support", "feature", "changes", "files", "abyss",
           "against", "before", "through", "replace", "region", "notes", "custom", "shared",
           "stages", "flow", "flows", "python", "tests", "testing"}
HEDGES = [
    "hypothesis", "hypotheses", "not confirmed", "not verified", "unverified", "inferred",
    "not independently reproduced", "not measured", "worth confirming", "confirm the link",
    "a guess", "assume", "not yet proven", "may be", "possibly the same",
]


def load(name, default=None):
    path = HERE / name
    return json.loads(path.read_text()) if path.exists() else (default if default is not None else {})


def blob(thread) -> str:
    return (" ".join(thread["fields"].values()) + " " + thread["title"] + " "
            + " ".join(thread["paragraphs"])).lower()


def thread_prs(thread):
    return {(repo, int(number)) for repo, number in PR_LINK.findall(" ".join(thread["fields"].values()))}


def thread_tickets(thread):
    return {ticket.upper() for ticket in TICKET.findall(blob(thread))}


def updated_date(thread):
    match = re.match(r"(\d{4}-\d{2}-\d{2})", thread["fields"].get("updated", ""))
    return datetime.strptime(match.group(1), "%Y-%m-%d").date() if match else None


# ---------- groups ----------
def merge_candidates(threads, settled, show_settled=False, limit=10):
    """
    Pairs of threads that may be one piece of work, strongest evidence first.

    Evidence is weighted by how rare it is: AFP-536 appears in a third of the board,
    so two threads sharing it means nothing, while two threads sharing a PR link or
    naming each other means a great deal.
    """
    ticket_frequency, stem_frequency = {}, {}
    for thread in threads:
        for ticket in thread_tickets(thread):
            ticket_frequency[ticket] = ticket_frequency.get(ticket, 0) + 1
        for stem in {part for part in thread["slug"].split("_") if len(part) > 4}:
            stem_frequency[stem] = stem_frequency.get(stem, 0) + 1

    pairs = {}

    def note(one, two, why, weight):
        # a folded finding naming its own parent is the fold working, not a merge candidate
        if one["fields"].get("parent") == two["slug"] or two["fields"].get("parent") == one["slug"]:
            return
        key = tuple(sorted([one["slug"], two["slug"]]))
        moved = max(filter(None, [settled_store.updated_on(one), settled_store.updated_on(two)]),
                    default=None)
        if not show_settled and settled_store.is_settled(
                "distinct", settled_store.pair_key(*key), moved_on=moved, settled=settled):
            return
        entry = pairs.setdefault(key, {"why": set(), "score": 0})
        if why not in entry["why"]:
            entry["why"].add(why)
            entry["score"] += weight

    for index, one in enumerate(threads):
        for two in threads[index + 1:]:
            for repo, number in sorted(thread_prs(one) & thread_prs(two)):
                note(one, two, f"both link {repo}#{number}", 5)
            if two["slug"] in blob(one) or one["slug"] in blob(two):
                note(one, two, "one thread names the other's slug", 4)
            for ticket in sorted(thread_tickets(one) & thread_tickets(two)):
                if ticket_frequency[ticket] <= 3:  # a rare ticket is a real link
                    note(one, two, f"both mention {ticket} (only {ticket_frequency[ticket]} threads do)", 3)
            stems = {part for part in one["slug"].split("_") if len(part) > 4}
            stems &= {part for part in two["slug"].split("_") if len(part) > 4}
            for stem in sorted(stems):
                if stem_frequency[stem] <= 3:
                    note(one, two, f"slugs share `{stem}`", 1)

    ranked = sorted(pairs.items(), key=lambda item: -item[1]["score"])
    return [{"pair": list(key), "score": entry["score"], "why": sorted(entry["why"])}
            for key, entry in ranked if entry["score"] >= 3][:limit]


def inbound_analysis(threads, inbound, settled, show_settled=False):
    """
    Inbound reviews that look like existing work, and inbound PRs that are one review.
    """
    clusters, folds = {}, []
    for pr in inbound:
        for ticket in {t.upper() for t in TICKET.findall(pr["title"])}:
            clusters.setdefault(ticket, []).append(pr)
    clusters = {ticket: prs for ticket, prs in clusters.items() if len(prs) > 1}

    claimed = {key for thread in threads for key in thread_prs(thread)}
    for pr in inbound:
        if (pr["repo"], pr["number"]) in claimed:
            continue  # a thread lists it in Links:, so it is already somebody's work
        if not show_settled and settled_store.is_settled(
                "queue_only", f"{pr['repo']}#{pr['number']}", settled=settled):
            continue
        tickets = {t.upper() for t in TICKET.findall(pr["title"])}
        words = {word for word in re.findall(r"[a-z_]{5,}", pr["title"].lower())
                 if word not in GENERIC}
        for thread in threads:
            text = blob(thread)
            why = [f"thread mentions {ticket}" for ticket in sorted(tickets) if ticket.lower() in text]
            if pr["repo"] in thread["fields"].get("repos", ""):
                shared = sorted(word for word in words if word in text)
                if len(shared) >= 2:
                    why.append("shared terms: " + ", ".join(shared[:4]))
            if why:
                folds.append({"pr": f"{pr['repo']}#{pr['number']}", "title": pr["title"],
                              "author": pr["author"], "thread": thread["slug"], "why": why})
    return {"clusters": {t: [f"{pr['repo']}#{pr['number']}" for pr in prs] for t, prs in clusters.items()},
            "folds": folds}


def hypotheses(threads, settled, show_settled=False):
    """
    Every line a thread has itself marked as unproven.
    """
    found = []
    for thread in threads:
        for field in ("next", "updated"):
            value = thread["fields"].get(field, "")
            for sentence in re.split(r"(?<=[.!?])\s+", value):
                lowered = sentence.lower()
                hit = next((hedge for hedge in HEDGES if hedge in lowered), None)
                if hit and len(sentence) > 40:
                    key = f"{thread['slug']}:{sentence[:40]}"
                    if not show_settled and settled_store.is_settled(
                            "confirmed", key, moved_on=settled_store.updated_on(thread),
                            settled=settled):
                        continue
                    found.append({"thread": thread["slug"], "marker": hit,
                                  "claim": sentence.strip()[:240]})
    return found


def pr_states(threads, open_prs):
    """
    The real state of every PR a thread links.

    A linked PR missing from the sweep has not necessarily gone anywhere — the sweep
    only finds PRs this user wrote, and a review thread links someone else's. So ask
    GitHub, and keep enough of the answer to judge it the same way.
    """
    open_keys = {(pr["repo"], pr["number"]): pr for pr in open_prs}
    unknown = sorted({key for thread in threads for key in thread_prs(thread)} - set(open_keys))

    def fetch(key):
        repo, number = key
        result = subprocess.run(
            ["gh", "pr", "view", str(number), "--repo", f"abyss-solutions/{repo}", "--json",
             "state,title,mergedAt,updatedAt,isDraft,author,reviewRequests,reviews"],
            capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            return key, None
        return key, json.loads(result.stdout)

    fetched = {}
    if unknown:
        with ThreadPoolExecutor(max_workers=8) as pool:
            for key, data in pool.map(fetch, unknown):
                fetched[key] = data

    # an open PR somebody else wrote is still an open PR; normalise it into the same
    # shape the sweep produces so the checks below do not have to care who wrote it
    elsewhere, closed = {}, {}
    for key, data in fetched.items():
        if data and data.get("state") == "OPEN":
            updated = datetime.fromisoformat(data["updatedAt"].replace("Z", "+00:00"))
            elsewhere[key] = {
                "repo": key[0], "number": key[1], "title": data["title"],
                "author": (data.get("author") or {}).get("login", "?"),
                "is_draft": data.get("isDraft", False),
                "has_reviewer": bool(data.get("reviewRequests") or data.get("reviews")),
                "days_since_update": (datetime.now(updated.tzinfo) - updated).days,
                "not_mine": True,
            }
        else:
            closed[key] = data
    return open_keys, elsewhere, closed


def contradictions(threads, open_prs, settled=None, show_settled=False):
    """
    Claims a thread makes that its own pull requests do not support.
    """
    open_keys, elsewhere, closed = pr_states(threads, open_prs)
    found = []

    def note(thread, kind, detail):
        if not show_settled and settled_store.is_settled(
                "acknowledged", f"{thread['slug']}:{kind}",
                moved_on=settled_store.updated_on(thread), settled=settled):
            return
        found.append({"thread": thread["slug"], "kind": kind, "detail": detail})

    # fields outside their vocabulary: the board renders them as unknown, silently
    for thread in threads:
        status = thread["fields"].get("status", "")
        if status and status not in tracker.STATUS_ORDER:
            note(thread, "status outside the vocabulary",
                 f"`{status}` — not one of {', '.join(tracker.STATUS_ORDER)}; the board renders "
                 f"it muted and the sort treats it as last")
        priority = thread["fields"].get("priority", "").split()[0]
        if priority and priority not in tracker.PRIORITIES:
            note(thread, "priority outside the vocabulary",
                 f"`{priority}` — not one of {', '.join(tracker.PRIORITIES)}; it falls into P3")

    for thread in threads:
        keys = thread_prs(thread)
        status = thread["fields"].get("status", "")
        if not keys:
            continue
        open_linked = [open_keys[key] for key in keys if key in open_keys]
        open_linked += [elsewhere[key] for key in keys if key in elsewhere]
        gone = [(key, closed[key]) for key in keys if key in closed]

        mine_open = [pr for pr in open_linked if not pr.get("not_mine")]
        if status == "review" and mine_open and not any(pr["has_reviewer"] for pr in mine_open):
            note(thread, "awaiting review with nobody asked",
                 f"{len(mine_open)} open PR(s), none with a requested reviewer or a "
                 f"submitted review: " + ", ".join(f"#{pr['number']}" for pr in mine_open))
        if gone and not open_linked and status not in ("done", "resolved"):
            note(thread, f"status `{status}` but every linked PR has landed or closed", ", ".join(
                f"#{key[1]} {(data or {}).get('state', 'unknown').lower()}" for key, data in gone))
        stale_open = [pr for pr in open_linked if pr["days_since_update"] > 30]
        if thread["fields"].get("priority", "").startswith("P1") and stale_open:
            note(thread, "P1 with untouched PRs",
                 ", ".join(f"#{pr['number']} {pr['days_since_update']}d" for pr in stale_open))
    return found


def stale(threads, settled=None, show_settled=False):
    """
    Threads nobody has touched in a fortnight. One confirmed still live stays quiet
    until it next moves — and a thread walked through in a session counts as touched,
    which is what `Reviewed:` is for.
    """
    today = date.today()
    found = []
    for thread in threads:
        when = updated_date(thread)
        priority = thread["fields"].get("priority", "P3").split()[0]
        limit = STALE_DAYS.get(priority, 60)
        if not when or limit is None or (today - when).days < limit:
            continue
        if thread["fields"].get("status") == "done":
            continue
        if not show_settled and (settled_store.is_fresh(thread) or settled_store.is_settled(
                "live", thread["slug"], moved_on=settled_store.updated_on(thread), settled=settled)):
            continue
        found.append({"thread": thread["slug"], "age_days": (today - when).days,
                      "over_by_days": (today - when).days - limit,
                      "status": thread["fields"].get("status"),
                      "priority": thread["fields"].get("priority"),
                      "reviewed": settled_store.reviewed_on(thread)})
    return sorted(found, key=lambda row: -row["over_by_days"])


def closeout(open_prs, inbound, settled=None, show_settled=False):
    def keep(pr):
        return show_settled or not settled_store.is_settled(
            "kept", f"{pr['repo']}#{pr['number']}", settled=settled)

    mine = [{"pr": f"{pr['repo']}#{pr['number']}", "title": pr["title"],
             "idle_days": pr["days_since_update"], "behind": pr["commits_behind_base"]}
            for pr in open_prs if pr["days_since_update"] > LONG_TAIL_DAYS and keep(pr)]
    theirs = [{"pr": f"{pr['repo']}#{pr['number']}", "title": pr["title"], "author": pr["author"],
               "idle_days": pr["days_since_update"]}
              for pr in inbound if pr["days_since_update"] > LONG_TAIL_DAYS and keep(pr)]
    return {"mine": sorted(mine, key=lambda row: -row["idle_days"]),
            "inbound": sorted(theirs, key=lambda row: -row["idle_days"])}


def vague(threads, settled=None, show_settled=False):
    found = []
    for thread in threads:
        nxt = thread["fields"].get("next", "")
        if thread["fields"].get("status") in ("done", "resolved"):
            continue
        if not show_settled and (settled_store.is_fresh(thread) or settled_store.is_settled(
                "accepted", thread["slug"], moved_on=settled_store.updated_on(thread),
                settled=settled)):
            continue
        if len(nxt) < 90 or nxt.lower().startswith(("not started", "no detail")):
            if not thread_prs(thread):
                found.append({"thread": thread["slug"], "title": thread["title"], "next": nxt[:120]})
    return found


def agenda(threads, findings, inbound):
    """
    The order to walk the board in.

    Priority first, because that is the user's own ranking, then how many unanswered
    questions a thread carries, then how long since anyone looked at it. A thread with
    no questions and a fresh `Reviewed:` date is listed last and can be skipped aloud.
    """
    questions = {}

    def ask(slug, group):
        questions.setdefault(slug, []).append(group)

    for pair in findings.get("merge", []):
        for slug in pair["pair"]:
            ask(slug, "merge")
    for fold in findings.get("inbound", {}).get("folds", []):
        ask(fold["thread"], "inbound")
    for group in ("hypotheses", "contradictions", "stale", "vague"):
        for row in findings.get(group, []):
            ask(row["thread"], group)

    rows = []
    for thread in threads:
        if thread["fields"].get("status") == "done":
            continue
        slug = thread["slug"]
        rows.append({
            "thread": slug,
            "title": thread["title"],
            "priority": thread["fields"].get("priority", "P3").split()[0],
            "status": thread["fields"].get("status", ""),
            "parent": thread["fields"].get("parent"),
            "questions": sorted(set(questions.get(slug, []))),
            "question_count": len(questions.get(slug, [])),
            "reviewed": settled_store.reviewed_on(thread),
            "fresh": settled_store.is_fresh(thread),
            "updated": settled_store.updated_on(thread),
        })
    return sorted(rows, key=lambda row: (
        tracker.PRIORITIES.index(row["priority"]) if row["priority"] in tracker.PRIORITIES else 9,
        -row["question_count"],
        row["reviewed"] or "",
    ))


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--group", nargs="*", default=None)
    parser.add_argument("--all", action="store_true",
                        help="include questions already settled, to review the answers")
    args = parser.parse_args()

    threads = tracker.parse_threads(tracker.TRACKER.read_text())
    open_prs = load("open-prs.json", {"prs": []})["prs"]
    inbound = load("inbound-prs.json", {"prs": []})["prs"]
    settled = settled_store.load()
    show = args.all

    groups = {
        "merge": lambda: merge_candidates(threads, settled, show_settled=show),
        "inbound": lambda: inbound_analysis(threads, inbound, settled, show_settled=show),
        "hypotheses": lambda: hypotheses(threads, settled, show_settled=show),
        "contradictions": lambda: contradictions(threads, open_prs, settled, show_settled=show),
        "stale": lambda: stale(threads, settled, show_settled=show),
        "closeout": lambda: closeout(open_prs, inbound, settled, show_settled=show),
        "vague": lambda: vague(threads, settled, show_settled=show),
    }
    wanted = [name for name in (args.group or list(groups) + ["agenda"]) if name != "agenda"]
    findings = {name: groups[name]() for name in wanted}
    if not args.group or "agenda" in args.group:
        findings["agenda"] = agenda(threads, findings, inbound)
    HERE.joinpath("interrogation.json").write_text(json.dumps(findings, indent=2))

    for name, result in findings.items():
        if name == "agenda":
            continue
        rows = result if isinstance(result, list) else sum(
            (value if isinstance(value, list) else list(value) for value in result.values()), [])
        print(f"\n=== {name.upper()} ({len(rows)}) ===")
        print(json.dumps(result, indent=1)[:2600])

    if "agenda" in findings:
        walk = [row for row in findings["agenda"] if row["question_count"]]
        print(f"\n=== AGENDA — {len(walk)} threads carry a question, "
              f"{len(findings['agenda']) - len(walk)} are quiet ===")
        for row in walk:
            marker = "fresh" if row["fresh"] else (f"reviewed {row['reviewed']}" if row["reviewed"]
                                                   else "never reviewed")
            print(f"  {row['priority']:<6} {row['thread']:<38} {','.join(row['questions']):<40} {marker}")

    settled_count = sum(len(entries) for entries in settled.values())
    print(f"\nwrote {HERE / 'interrogation.json'}"
          + (f" — {settled_count} settled answers held back (--all to see them)"
             if settled_count and not show else ""))


if __name__ == "__main__":
    main()
