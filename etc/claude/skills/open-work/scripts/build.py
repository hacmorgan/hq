"""
Render OPEN_WORK.md into the published board, and regenerate the PR section inside
OPEN_WORK.md from the latest sweep.

OPEN_WORK.md is the source of truth for threads; open-prs.json for pull requests.
Priority, parking and hand-offs can also be set on the board itself — those land in
the artifact's database and are folded back into OPEN_WORK.md by apply_decisions.py.
"""

import os
import html
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tracker

HERE = Path(os.environ.get("OPEN_WORK_DATA", Path.home() / "src/abyss/.open-work"))  # data, not code
data = json.loads(HERE.joinpath("open-prs.json").read_text())
prs = data["prs"]
summary = data["summary"]
threads = tracker.sort_threads(tracker.parse_threads(tracker.TRACKER.read_text()))
people = {name: entry for name, entry in
          json.loads((HERE / "people.json").read_text()).items() if not name.startswith("_")}
decisions_path = HERE / "decisions.json"
pr_decisions = json.loads(decisions_path.read_text()) if decisions_path.exists() else {}


def decision_for(pr) -> dict:
    return pr_decisions.get(f"{pr['repo']}#{pr['number']}", {})


def is_parked(pr) -> bool:
    return decision_for(pr).get("priority") == "parked"


def handed_off(pr):
    return decision_for(pr).get("handoff")

PRIORITY_LANES = [
    ("P1", "P1 — do these", "What is at the top of your TODO, or actively in progress."),
    ("P2", "P2 — next", "In flight but not the current focus, or waiting on someone else."),
    ("P3", "P3 — later", "Real work, not now."),
    ("parked", "Parked", "Deliberately set aside. Nothing here is waiting on a decision."),
]
STATUS_CHIP = {
    "active": "bad", "blocked": "bad", "review": "warn", "resolved": "ok",
    "flagged": "warn", "backlog": "muted", "done": "ok",
}


def esc(text) -> str:
    return html.escape(str(text if text is not None else ""))


def inline(text: str) -> str:
    """
    Render the small subset of markdown the tracker uses: links, bold, code.
    """
    out = html.escape(text)
    out = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    return out


# --- which thread owns which PR, from the PR links each thread carries ---
pr_to_thread = {}
for thread in threads:
    for repo_hint, number in re.findall(r"github\.com/abyss-solutions/([\w.-]+)/pull/(\d+)",
                                        thread["fields"].get("links", "")):
        pr_to_thread[(repo_hint, int(number))] = thread
by_number = {(pr["repo"], pr["number"]): pr for pr in prs}

# --- inbound: PRs waiting on the user's review ---
inbound_path = HERE / "inbound-prs.json"
inbound = json.loads(inbound_path.read_text())["prs"] if inbound_path.exists() else []
for review in inbound:
    review["thread"] = pr_to_thread.get((review["repo"], review["number"]))
# a review a thread has claimed belongs to that thread; the rest are the queue
review_queue = [review for review in inbound
                if not review["thread"] and not is_parked(review) and not handed_off(review)]
TICKET_RE = re.compile(r"\b(?:AFP|FABP|FABPRO|AIR|SO)-\d+\b", re.I)


def review_clusters(reviews) -> tuple:
    """
    Reviews that quote the same ticket are one sitting, not several.
    """
    by_ticket = {}
    for review in reviews:
        for ticket in {match.upper() for match in TICKET_RE.findall(review["title"])}:
            by_ticket.setdefault(ticket, []).append(review)
    clustered, clusters = set(), {}
    for ticket, group in sorted(by_ticket.items(), key=lambda item: -len(item[1])):
        group = [review for review in group if id(review) not in clustered]
        if len(group) > 1:
            clusters[ticket] = group
            clustered.update(id(review) for review in group)
    loose = [review for review in reviews if id(review) not in clustered]
    return clusters, loose


def thread_for(pr):
    return pr_to_thread.get((pr["repo"], pr["number"]))


def priority_of(pr) -> str:
    owner = thread_for(pr)
    if owner:
        return owner["fields"].get("priority", "P3").split()[0]
    return "P3"


def item_id(kind, *parts) -> str:
    return "__".join([kind, *[str(part).replace("/", "_") for part in parts]])


# --- controls: the board writes these into the artifact database ---
def controls(identifier, kind, promote=False) -> str:
    buttons = "".join(
        f'<button class="ctl" data-action="priority" data-value="{value}" title="set {value}">{value}</button>'
        for value in ("P1", "P2", "P3")
    )
    return f"""<div class="controls" data-item="{identifier}" data-kind="{kind}">
      {buttons}
      {'<button class="ctl ctl-promote" data-action="promote" title="lift this out of the fold and make it a top-level item">promote</button>' if promote else ''}
      <button class="ctl" data-action="park" title="deprioritise indefinitely">park</button>
      <button class="ctl" data-action="handoff" title="hand this to someone else">hand off</button>
      <button class="ctl ctl-clear" data-action="clear" title="clear board decision">reset</button>
      <span class="ctl-state"></span>
    </div>"""


# ---------- stacks, at the top ----------
def stack_block(stack) -> str:
    bottom = by_number.get((stack["repo"], stack["chain_bottom_to_top"][0]))
    owner = thread_for(bottom) if bottom else None
    priority = owner["fields"].get("priority", "P3").split()[0] if owner else "P3"
    label = (f'<a class="stack-thread" href="#thread-{owner["slug"]}">{esc(owner["slug"])}</a>'
             if owner else '<span class="muted">no thread</span>')
    links, blockers = [], []
    for number in stack["chain_bottom_to_top"]:
        pr = by_number.get((stack["repo"], number))
        classes = []
        if pr and pr["mergeable"] == "CONFLICTING":
            classes.append("is-conflicting")
            blockers.append(f"#{number} conflicts")
        if pr and pr["ci"]["state"] == "failing":
            classes.append("is-failing")
        links.append(
            f'<a class="{" ".join(classes)}" '
            f'href="https://github.com/abyss-solutions/{stack["repo"]}/pull/{number}">#{number}</a>'
        )
    chain = " <span class='arrow'>▸</span> ".join(links)
    note = (f'<p class="stack-note">Cannot start: {", ".join(blockers)} — the bottom of the train '
            f'has to land first.</p>' if blockers else
            '<p class="stack-note">Clear to merge bottom-up.</p>')
    branches = "<br>".join(f'<span class="mono-sm">{esc(branch)}</span>' for branch in stack["branches"])
    return f"""<div class="stack" data-priority="{priority}">
      <div class="stack-head">
        <span class="chip chip-pri chip-{priority.lower()}">{priority}</span>
        <span class="stack-repo">{esc(stack['repo'])}</span>
        {label}
      </div>
      <div class="stack-chain">{chain}</div>
      <div class="stack-branches">{branches}</div>
      {note}
    </div>"""


stacks = sorted(
    summary["stacks"],
    key=lambda stack: tracker.PRIORITIES.index(
        (thread_for(by_number.get((stack["repo"], stack["chain_bottom_to_top"][0])) or {}) or
         {"fields": {}})["fields"].get("priority", "P3").split()[0]
        if thread_for(by_number.get((stack["repo"], stack["chain_bottom_to_top"][0])) or {}) else "P3"
    ),
)


# ---------- threads ----------
children_by_parent = {}
for thread in threads:
    parent_slug = thread["fields"].get("parent")
    if parent_slug:
        children_by_parent.setdefault(parent_slug, []).append(thread)


def fold(thread) -> str:
    """
    Sub-threads, folded into their parent. They are findings against the parent's
    work, not peers of it, so they say what they are before they say anything else.
    """
    children = children_by_parent.get(thread["slug"], [])
    if not children:
        return ""
    tally = {}
    for child in children:
        status = child["fields"].get("status", "active")
        tally[status] = tally.get(status, 0) + 1
    breakdown = " · ".join(f"{count} {status}" for status, count in sorted(tally.items()))
    return f"""<details class="fold">
      <summary><strong>{len(children)} findings</strong> under this work — {esc(breakdown)}
      <span class="muted">(click to open)</span></summary>
      <div class="fold-body">{"".join(thread_card(child, nested=True) for child in children)}</div>
    </details>"""


def thread_card(thread, nested=False) -> str:
    fields = thread["fields"]
    status = fields.get("status", "backlog")
    priority = fields.get("priority", "P3").split()[0]
    pinned = "(pinned)" in fields.get("priority", "")
    owned_prs = [pr for pr in prs if thread_for(pr) is thread]
    pr_chips = "".join(
        f'<a class="chip chip-pr" href="{esc(pr["url"])}">#{pr["number"]}</a>' for pr in owned_prs
    ) + "".join(
        f'<a class="chip chip-review" href="{esc(review["url"])}" '
        f'title="waiting on your review — {esc(review["author"])}">review #{review["number"]}</a>'
        for review in inbound if review["thread"] is thread
    )
    rows = "".join(
        f'<div class="tf"><span class="tf-key">{esc(key)}</span>'
        f'<span class="tf-val">{inline(fields[key])}</span></div>'
        for key in ("todo", "waiting on", "next", "links", "repos", "updated")
        if fields.get(key)
    )
    paragraphs = "".join(f"<p>{inline(paragraph)}</p>" for paragraph in thread["paragraphs"])
    return f"""<article class="thread{' is-sub' if nested else ''}" id="thread-{esc(thread['slug'])}"
      data-item="{item_id('thread', thread['slug'])}" data-priority="{priority}"
      data-slug="{esc(thread['slug'])}">
      <header class="thread-head">
        <span class="chip chip-pri chip-{priority.lower()}">{priority}{' 📌' if pinned else ''}</span>
        <span class="chip chip-{STATUS_CHIP.get(status, 'muted')}">{esc(status)}</span>
        <h3>{esc(thread['title'])}</h3>
        <span class="slug mono-sm">{esc(thread['slug'])}</span>
        {pr_chips}
      </header>
      {rows}
      {paragraphs}
      {controls(item_id('thread', thread['slug']), 'thread', promote=nested)}
      {fold(thread) if not nested else ""}
    </article>"""


# ---------- pull requests ----------
def ci_chip(pr) -> str:
    label = {"passing": "pass", "failing": "fail", "none": "—", "pending": "…", "unknown": "?"}[pr["ci"]["state"]]
    css = {"passing": "ok", "failing": "bad", "none": "muted", "pending": "warn", "unknown": "muted"}[pr["ci"]["state"]]
    return f'<span class="chip chip-{css}">{label}</span>'


def merge_chip(pr) -> str:
    if pr["mergeable"] == "CONFLICTING":
        return '<span class="chip chip-bad">conflicts</span>'
    return '<span class="chip chip-ok">clean</span>'


def review_chip(pr) -> str:
    if pr["review_decision"] == "APPROVED":
        return '<span class="chip chip-ok">approved</span>'
    if pr["review_decision"] == "CHANGES_REQUESTED":
        return '<span class="chip chip-warn">changes</span>'
    if not pr["has_reviewer"] and not pr["is_draft"]:
        return '<span class="chip chip-bad">no reviewer</span>'
    if pr["reviewers"] or pr["review_requests"]:
        who = (pr["reviewers"] + pr["review_requests"])[0]
        return f'<span class="chip chip-muted">{esc(who)}</span>'
    return '<span class="chip chip-muted">—</span>'


def behind_cell(pr) -> str:
    behind = pr["commits_behind_base"]
    if behind is None:
        return '<span class="muted">?</span>'
    if behind == 0:
        return '<span class="muted">0</span>'
    css = "num-bad" if behind > 500 else ("num-warn" if behind > 100 else "num")
    return f'<span class="{css}">{behind:,}</span>'


def base_cell(pr) -> str:
    if pr["base_is_default"]:
        return f'<span class="muted">{esc(pr["base"])}</span>'
    stacked = f' <span class="chip chip-info">on #{pr["stacked_on"]}</span>' if pr["stacked_on"] else ""
    return f'<span class="mono-sm">{esc(pr["base"])}</span>{stacked}'


def pr_row(pr) -> str:
    draft = ' <span class="chip chip-muted">draft</span>' if pr["is_draft"] else ""
    decided = ""
    if is_parked(pr):
        decided += ' <span class="chip chip-parked">parked</span>'
    if handed_off(pr):
        decided += f' <span class="chip chip-thread">→ {esc(handed_off(pr)["to"])}</span>' 
    owner = thread_for(pr)
    thread_link = (f' <a class="chip chip-thread" href="#thread-{owner["slug"]}">{esc(owner["slug"])}</a>'
                   if owner else "")
    identifier = item_id("pr", pr["repo"], pr["number"])
    classes = " ".join(filter(None, ["is-parked" if is_parked(pr) else "",
                                     "is-handed-off" if handed_off(pr) else ""]))
    return f"""<tr data-item="{identifier}" data-kind="pr" class="{classes}">
      <td class="pr-num"><a href="{esc(pr['url'])}">#{pr['number']}</a></td>
      <td class="pr-title">{esc(pr['title'])}{draft}{decided}{thread_link}</td>
      <td>{base_cell(pr)}</td>
      <td class="right">{behind_cell(pr)}</td>
      <td>{ci_chip(pr)}</td>
      <td>{merge_chip(pr)}</td>
      <td>{review_chip(pr)}</td>
      <td class="right muted">{pr['days_since_update']}d</td>
      <td class="row-ctl">{controls(identifier, 'pr')}</td>
    </tr>"""


def repo_table(repo: str) -> str:
    rows_for_repo = sorted(
        [pr for pr in prs if pr["repo"] == repo],
        key=lambda pr: (is_parked(pr),
                        not (pr["mergeable"] == "CONFLICTING" or pr["ci"]["state"] == "failing"),
                        -pr["number"]),
    )
    rows = "\n".join(pr_row(pr) for pr in rows_for_repo)
    return f"""<h3 class="repo-head">{esc(repo)} <span class="repo-count">{len(rows_for_repo)}</span></h3>
<div class="table-wrap"><table>
  <thead><tr>
    <th>PR</th><th>Title</th><th>Base</th><th class="right">Behind</th>
    <th>CI</th><th>Merge</th><th>Review</th><th class="right">Idle</th><th></th>
  </tr></thead>
  <tbody>
{rows}
  </tbody>
</table></div>"""


def mini_row(pr, note, kind="", extra="") -> str:
    identifier = item_id("pr", pr["repo"], pr["number"])
    return f"""<div class="mini {kind}" data-item="{identifier}" data-kind="pr">
      <a class="pr-num" href="{esc(pr['url'])}">{esc(pr['repo'])} #{pr['number']}</a>
      <span class="mini-title">{esc(pr['title'])}{extra}</span>
      <span class="mini-note">{note}</span>
      {controls(identifier, 'pr')}
    </div>"""


needs_reviewer = sorted(
    [pr for pr in prs if not pr["has_reviewer"] and not pr["is_draft"]
     and not is_parked(pr) and not handed_off(pr)],
    key=lambda pr: (tracker.PRIORITIES.index(priority_of(pr)), pr["days_since_update"] * -1),
)
handed_off_prs = [pr for pr in prs if handed_off(pr)]
blocked_on_author = sorted(
    [pr for pr in prs if pr["review_decision"] == "APPROVED" and not is_parked(pr)
     and (pr["mergeable"] == "CONFLICTING" or pr["ci"]["state"] == "failing")],
    key=lambda pr: -(pr["commits_behind_base"] or 0),
)
approved_and_clean = [pr for pr in prs if pr["review_decision"] == "APPROVED" and pr not in blocked_on_author]
stale = sorted([pr for pr in prs if pr["days_since_update"] > 180], key=lambda pr: -pr["days_since_update"])


def blocked_note(pr) -> str:
    return " · ".join(filter(None, [
        "conflicts" if pr["mergeable"] == "CONFLICTING" else None,
        "CI failing" if pr["ci"]["state"] == "failing" else None,
        f"{pr['commits_behind_base']:,} behind" if (pr["commits_behind_base"] or 0) > 0 else None,
    ]))


def named_in_thread(pr):
    """
    Someone the thread itself names — a far better suggestion than repo frequency.
    """
    owner = thread_for(pr)
    if not owner:
        return None
    haystack = " ".join(owner["fields"].values()).lower() + " " + " ".join(owner["paragraphs"]).lower()
    mentions = [
        (len(re.findall(rf"\b{re.escape(first_name)}\b", haystack)), first_name, entry)
        for first_name, entry in people.items()
    ]
    count, first_name, entry = max(mentions, key=lambda hit: hit[0])
    if not count:
        return None
    return {"login": entry["login"], "why": f"named in {owner['slug']} ({first_name.title()})"}


def reviewer_row(pr) -> str:
    suggestions = list(pr["suggested_reviewers"])
    named = named_in_thread(pr)
    if named:
        # being named in the thread is a better reason than repo frequency
        suggestions = [other for other in suggestions if other["login"] != named["login"]]
        suggestions.insert(0, named)
    if suggestions:
        best = suggestions[0]
        rest = "".join(f'<button class="ctl" data-action="handoff" data-value="{esc(other["login"])}">'
                       f'{esc(other["login"])}</button>' for other in suggestions[1:3])
        suggestion = (f'<span class="suggest">suggested: <strong>{esc(best["login"])}</strong> '
                      f'<span class="muted">— {esc(best["why"])}</span></span>{rest}')
    else:
        suggestion = '<span class="muted">no suggestion</span>'
    return mini_row(pr, f'{priority_of(pr)} · {pr["days_since_update"]}d idle',
                    kind="is-reviewer", extra=f'<br>{suggestion}')


def review_row(review, note=None) -> str:
    """
    One inbound review. The note is what decides whether to open it now: who is
    waiting, how long they have waited, and whether it is even ready to read.
    """
    identifier = item_id("review", review["repo"], review["number"])
    flags = note or " · ".join(filter(None, [
        f'<strong>{esc(review["author"])}</strong>',
        f'{review["days_since_update"]}d idle',
        "draft" if review["is_draft"] else "",
        "stale" if review["days_since_update"] > 180 else "",
    ]))
    return f"""<div class="mini is-review{' is-draft' if review['is_draft'] else ''}"
      data-item="{identifier}" data-kind="review">
      <a class="pr-num" href="{esc(review['url'])}">{esc(review['repo'])} #{review['number']}</a>
      <span class="mini-title">{esc(review['title'])}</span>
      <span class="mini-note">{flags}</span>
      {controls(identifier, 'review')}
    </div>"""


review_cluster_map, review_loose = review_clusters(review_queue)
review_sections = "".join(
    f"""<div class="cluster">
      <h4 class="cluster-head">{esc(ticket)} <span class="muted">— {len(group)} PRs, one sitting</span></h4>
      {"".join(review_row(review) for review in sorted(group, key=lambda review: review["number"]))}
    </div>"""
    for ticket, group in sorted(review_cluster_map.items(), key=lambda item: -len(item[1]))
) + "".join(
    review_row(review) for review in
    sorted(review_loose, key=lambda review: (review["is_draft"], -review["days_since_update"]))
)
claimed_reviews = [review for review in inbound if review["thread"]]
parked_reviews = [review for review in inbound if is_parked(review)]
handed_off_reviews = [review for review in inbound if handed_off(review)]

stale_rows = "\n".join(
    f'<li><a href="{esc(pr["url"])}">{esc(pr["repo"])} #{pr["number"]}</a> '
    f'<span class="muted">{esc(pr["title"][:60])}</span> '
    f'<span class="num-warn">{pr["days_since_update"]}d idle</span>'
    + (f' · <span class="num-bad">{pr["commits_behind_base"]:,} behind</span>'
       if (pr["commits_behind_base"] or 0) > 500 else "") + "</li>"
    for pr in stale
)

# a sub-thread only folds into a live parent: one whose parent is done (rendered only in the
# done list) or archived to closed-work/ would vanish from the board, so it stands on its own
live_parent_slugs = {thread["slug"] for thread in threads if thread["fields"].get("status") != "done"}
for thread in threads:
    parent = thread["fields"].get("parent")
    if parent and parent not in live_parent_slugs and thread["fields"].get("status") != "done":
        print(f"warning: {thread['slug']} is open but its parent {parent} is done or archived "
              "— shown top-level; clear its Parent: or finish it")
live_threads = [thread for thread in threads
                if thread["fields"].get("status") != "done"
                and thread["fields"].get("parent") not in live_parent_slugs]
done_threads = [thread for thread in threads if thread["fields"].get("status") == "done"]

lanes = "".join(
    f"""<div class="lane" data-lane="{key}">
      <h3 class="lane-head"><span class="chip chip-pri chip-{key.lower()}">{key}</span> {esc(label)}</h3>
      <p class="lane-lede">{esc(lede)}</p>
      <div class="lane-body" data-lane-body="{key}">
        {"".join(thread_card(thread) for thread in live_threads
                 if thread["fields"].get("priority", "P3").split()[0] == key)}
      </div>
    </div>"""
    for key, label, lede in PRIORITY_LANES
)
done_rows = "".join(
    f'''<li><strong>{esc(thread["title"])}</strong> <span class="mono-sm muted">{esc(thread["slug"])}</span>
    <span class="muted">— {inline(thread["fields"].get("updated", ""))}</span></li>'''
    for thread in done_threads
)

swept = summary["generated_at"][:10]
counts = {key: len([t for t in live_threads if t["fields"].get("priority", "P3").split()[0] == key])
          for key, _, _, in PRIORITY_LANES}

done_section = ""
if done_threads:
    done_section = (
        '<section>\n<h2>Done — clear these out</h2>\n'
        '<p class="lede">Marked DONE in your TODO. Delete the thread once you have seen it, and '
        'the entry from the TODO when it stops being useful history.</p>\n'
        f'<ul class="stale">{done_rows}</ul>\n</section>'
    )

claimed_note = "".join([
    f", and {len(claimed_reviews)} more already folded into one" if claimed_reviews else "",
    f" ({len(parked_reviews)} parked, not shown)" if parked_reviews else "",
])

CODE = Path(__file__).resolve().parent
STYLE = CODE.joinpath("board-style.html").read_text()
SCRIPT = CODE.joinpath("board-script.html").read_text()

page = STYLE + f"""
<div class="wrap">
  <header class="masthead">
    <p class="eyebrow">hacmorgan · swept {swept}</p>
    <h1>Open Work</h1>
    <p class="standfirst">Every thread and every open pull request, ordered by what your TODO says
    matters. Merge trains first — they gate everything stacked on them — then threads by priority,
    then the pull requests that need a reviewer, a rebase, or a merge.</p>
    <div class="tiles">
      <div class="tile is-bad"><b>{counts['P1']}</b><span>P1 threads</span></div>
      <div class="tile is-warn"><b>{counts['P2']}</b><span>P2</span></div>
      <div class="tile"><b>{counts['P3']}</b><span>P3</span></div>
      <div class="tile"><b>{summary['total_open_prs']}</b><span>open PRs</span></div>
      <div class="tile is-warn"><b>{len(review_queue)}</b><span>to review</span></div>
      <div class="tile is-bad"><b>{len(needs_reviewer)}</b><span>no reviewer</span></div>
      <div class="tile is-bad"><b>{len(summary['prs_conflicting'])}</b><span>conflicting</span></div>
    </div>
  </header>

  <section>
    <h2>Merge trains</h2>
    <p class="lede">Each PR's base is the one to its left, so a train can only land bottom-up.
    Ordered by the priority of the thread that owns it.</p>
    <div class="stacks">{"".join(stack_block(stack) for stack in stacks)}</div>
  </section>

  <section>
    <h2>Threads</h2>
    <p class="lede">Priority comes from where the item sits in your daily TODO and its org keyword;
    <span class="mono-sm">📌</span> marks one pinned by hand. Use the buttons to change it — the
    board remembers, and the change is folded back into <code>OPEN_WORK.md</code> on the next sync.</p>
    {lanes}
  </section>

  <section id="review-queue">
    <h2>Review queue — waiting on you</h2>
    <p class="lede">{len(review_queue)} open PRs where you are a requested reviewer and no thread
    has claimed them{claimed_note}. These never appear in the PR sweep, which only sees what you
    wrote. Fold one into a thread by adding its URL to that thread's <code>Links:</code> — it
    leaves this queue and shows as a <span class="chip chip-review">review #n</span> chip on that
    thread instead. Same-ticket PRs are grouped: read them together or not at all.</p>
    {review_sections or '<p class="muted empty-note">Nothing waiting on your review.</p>'}
  </section>

  {done_section}

  <section>
    <h2>Needs a reviewer</h2>
    <p class="lede">{len(needs_reviewer)} open non-draft PRs have neither a requested reviewer nor a
    submitted review. The suggestion is whoever reviewed a sibling in the same stack, falling back to
    whoever reviews that repo most often — a starting point, not a recommendation.</p>
    {chr(10).join(reviewer_row(pr) for pr in needs_reviewer)}
  </section>

  <section>
    <h2>Blocked on you, not on reviewers</h2>
    <p class="lede">Approved, but cannot merge as they stand.</p>
    {chr(10).join(mini_row(pr, blocked_note(pr)) for pr in blocked_on_author)}
  </section>

  <section>
    <h2>Approved and clean — mergeable now</h2>
    <p class="lede">Nothing in the way of these {len(approved_and_clean)}.</p>
    {chr(10).join(mini_row(pr, f"{pr['commits_behind_base']:,} behind" if pr['commits_behind_base'] else "ready", kind="is-ready") for pr in approved_and_clean)}
  </section>

  <section id="handed-off">
    <h2>Handed off</h2>
    <p class="lede">Work you have passed to someone else. These are review-priority: the next move
    is theirs, but the nudge is yours.</p>
    <div id="handoff-list">{"".join(mini_row(pr, f"handed off {handed_off(pr).get('at', '')}", kind="is-handoff", extra=f" → <strong>{esc(handed_off(pr)['to'])}</strong>") for pr in handed_off_prs) + "".join(review_row(review, note=f"review passed to <strong>{esc(handed_off(review)['to'])}</strong> · {esc(review['author'])} is waiting") for review in handed_off_reviews) or '<p class="muted empty-note">Nothing handed off yet — use the <strong>hand off</strong> button on any thread or PR.</p>'}</div>
  </section>

  <section>
    <h2>All open PRs by repo</h2>
    <p class="lede">Needs-action rows first within each repo, then newest. <strong>Behind</strong>
    counts commits the base has that the branch does not.</p>
    {"".join(repo_table(repo) for repo in summary["per_repo_counts"])}
  </section>

  <section>
    <h2>The long tail</h2>
    <p class="lede">{len(stale)} PRs untouched for over six months.</p>
    <ul class="stale">{stale_rows}</ul>
  </section>

  <footer>
    Rendered from <code>~/src/abyss/OPEN_WORK.md</code> and the TODO at
    <code>~/.hq-secret/etc/todo</code>. PR state swept {swept} for PRs authored by hacmorgan across
    {summary['repos_scanned_with_github_remote']} repos with a GitHub remote. Mergeability is
    re-queried per PR. Decisions made on this page are stored with the artifact and folded back into
    the tracker by <code>.open-work/apply_decisions.py</code>. Built {date.today().isoformat()}.
  </footer>
</div>
{SCRIPT}
"""

HERE.joinpath("board.html").write_text(page)
print(f"wrote board.html ({len(page) // 1024} KB) — {len(threads)} threads, {len(prs)} PRs, "
      f"{len(stacks)} stacks, {len(needs_reviewer)} needing a reviewer, "
      f"{len(review_queue)} in the review queue ({len(claimed_reviews)} folded into threads)")


# --- regenerate the PR section inside the tracker ---
def md_row(pr) -> str:
    flags = " ".join(filter(None, [
        "draft" if pr["is_draft"] else "",
        "conflicts" if pr["mergeable"] == "CONFLICTING" else "",
        "ci-fail" if pr["ci"]["state"] == "failing" else "",
        "approved" if pr["review_decision"] == "APPROVED" else "",
        "changes-requested" if pr["review_decision"] == "CHANGES_REQUESTED" else "",
        "no-reviewer" if not pr["has_reviewer"] and not pr["is_draft"] else "",
    ])) or "—"
    behind = "?" if pr["commits_behind_base"] is None else f"{pr['commits_behind_base']:,}"
    base = f"{pr['base']} ↑#{pr['stacked_on']}" if pr["stacked_on"] else pr["base"]
    title = pr["title"].replace("|", "\\|")
    owner = thread_for(pr)
    return (f"| [#{pr['number']}]({pr['url']}) | {title} | {owner['slug'] if owner else '—'} | "
            f"`{base}` | {behind} | {pr['days_since_update']}d | {flags} |")


lines = [
    tracker.BEGIN_PRS, "", "## Open pull requests", "",
    f"Swept {swept}: **{summary['total_open_prs']} open** across {summary['repos_with_open_prs']} "
    f"repos — {len(summary['prs_conflicting'])} conflicting, {len(summary['prs_with_failing_ci'])} "
    f"with failing CI, {len(needs_reviewer)} with no reviewer, {summary['drafts']} drafts.", "",
]
for repo, count in summary["per_repo_counts"].items():
    rows = sorted([pr for pr in prs if pr["repo"] == repo],
                  key=lambda pr: (not (pr["mergeable"] == "CONFLICTING" or pr["ci"]["state"] == "failing"),
                                  -pr["number"]))
    lines += [f"### {repo} ({count})", "",
              "| PR | Title | Thread | Base | Behind | Idle | Flags |",
              "| --- | --- | --- | --- | ---: | ---: | --- |"]
    lines += [md_row(pr) for pr in rows]
    lines.append("")

# inbound reviews: not in the sweep above, because that only finds what this user wrote
lines += [f"### Reviews waiting on you ({len(inbound)})", "",
          "Open PRs where hacmorgan is a requested reviewer. A thread claims one by listing its "
          "URL in `Links:`; the rest sit in the review queue ([[review_queue]]).", "",
          "| PR | Title | Author | Thread | Idle |", "| --- | --- | --- | --- | ---: |"]
lines += [f"| [#{review['number']}]({review['url']}) | {review['title'].replace('|', chr(92) + '|')} | "
          f"{review['author']} | {review['thread']['slug'] if review['thread'] else '—'} | "
          f"{review['days_since_update']}d |"
          for review in sorted(inbound, key=lambda review: (review["repo"], -review["days_since_update"]))]
lines.append("")
lines.append(tracker.END_PRS)

text = tracker.TRACKER.read_text()
start, finish = text.index(tracker.BEGIN_PRS), text.index(tracker.END_PRS) + len(tracker.END_PRS)
tracker.TRACKER.write_text(text[:start] + "\n".join(lines) + text[finish:])
print("regenerated the PR section in OPEN_WORK.md")
