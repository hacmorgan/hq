---
name: open-work
description: Sync and report everything currently open across the Abyss repos — threads, PRs, inbound reviews, priorities from the daily TODO — and walk through it interactively to merge, verify and reprioritise. Activate when the user asks what is open, what to work on, to refresh or update the open-work board or tracker, to go through or interrogate what is open, or invokes /open-work.
---

# Open Work

`~/src/abyss/OPEN_WORK.md` is the source of truth for everything in flight across the Abyss
repos. The board at <https://claude.ai/artifact/9rCQdRpXB5s6wSyJerfvV8> is rendered from it.
Threads are linked to the user's daily TODO (`~/.hq-secret/etc/todo/YYYY/MM/DD.org`) by
`[[ow:<slug>][text]]` org links — the slug rides in the link target, so the headline displays
only its words. A `***` sub-item can carry its own link, inherits its parent's priority, and renders folded
inside the parent's card on the board with its status shown (a finding, not a peer).

**Promoting a finding.** The board's folded cards carry a `promote` button; it records
`{promote: true}` and the next `apply_decisions.py` lifts that `***` line out of its parent's
subtree and re-files it as a `**` item directly after that subtree, with a cookie, leaving the
parent's other children in place. The user can do the same by hand in emacs — either way the sync
clears the thread's `Parent:` field, which is what unfolds it.

**Reviews waiting on the user are tracked too.** `sweep.py` finds PRs they *wrote*; a second query
(`gh search prs --review-requested=@me`) finds the ones waiting on them, which is where work hides.
Unclaimed ones sit in the `review_queue` thread's lane on the board; a thread claims one by listing
its URL in `Links:`, after which it renders as a chip on that thread instead.

**Only the `abyss-trinity-open` session publishes the board.** Other agents update `OPEN_WORK.md` and stop there; the
session that owns the board renders and publishes it. Two sessions publishing means the second one
must read the whole published page before it can overwrite — 2,500+ lines of derived HTML.

**Read `OPEN_WORK.md`'s own "Keeping this file current" section before editing anything — it is
authoritative.** This skill covers how to run a sync and what to tell the user.

## Run a sync

```
python3 ~/src/abyss/.open-work/sweep.py      # PR state, reviewers, diff vs the last run
python3 ~/src/abyss/.open-work/todo_sync.py  # TODO drift + derived priorities
python3 ~/src/abyss/.open-work/build.py      # regenerate the PR section and board.html
```

`sweep.py` takes a few minutes (it re-queries mergeability per PR, because `gh pr list` reports
`UNKNOWN` for most of them) — run it in the background and do something else meanwhile.

Then, when the drift looks right:

```
python3 ~/src/abyss/.open-work/todo_sync.py --apply --write-links --adopt --tidy
python3 ~/src/abyss/.open-work/build.py
```

`--apply` mirrors TODO priorities into the tracker, `--write-links` writes the `ow:` links and
seeds any missing priority cookie, and `--adopt` creates a stub thread for each new TODO item.
Propose the slugs it generates to the user before adopting a batch — they are what the user will
read in emacs.

If you are `abyss-trinity-open`, republish with the Artifact tool (anyone else: `SendMessage` it
and ask it to republish): `publish`, `url:` the board URL above, `file_path:`
`~/src/abyss/.open-work/board.html`. **Omit `capabilities`** — the stored `db` declaration carries
forward, and restating a different set would revoke it.

If the user has used the buttons on the board, pull those decisions down *before* rebuilding:

```
Artifact  action=read_db  url=<board>  db_op=list  collection=decisions \
          out_dir=~/src/abyss/.open-work/decisions
python3 ~/src/abyss/.open-work/apply_decisions.py
```

## Closed work — kept for later reference

Finished work is archived, not deleted. `~/src/abyss/closed-work/YYYY-MM.md` holds one month each
— the archive rolls over by month of closure, so no file grows without bound:

- **Threads.** Once a thread is `done` and the user has seen it, `closed_work.py archive` moves it
  out of `OPEN_WORK.md` verbatim, stamped `Closed:` with its last `Updated:` date. It refuses a
  thread that still has open sub-threads (`Parent:` pointing at it) — a release with open findings
  is not finished, whatever its own status says.
- **Pull requests.** `sweep.py` logs every PR that left the open list — merged or closed, with the
  date and the thread whose `Links:` named it — under the month it landed.
- **Merged threads.** Blocks folded into another thread during interrogation go under the month's
  "Merged into other threads" section; the surviving thread points there.

```
python3 ~/src/abyss/.open-work/closed_work.py archive --dry-run   # what would move
python3 ~/src/abyss/.open-work/closed_work.py archive             # move every done thread
python3 ~/src/abyss/.open-work/closed_work.py find TERM           # search every month
python3 ~/src/abyss/.open-work/closed_work.py fold SRC INTO       # merge thread SRC into INTO
```

**When the user asks about past work** — "what happened with X", "when did Y land", "didn't we
already look at Z" — search the archive with `find` before reading code or GitHub. A TODO link to
an archived slug is history, not drift: `todo_sync.py` counts those separately.

## Report the drift in chat

The syncs print it; the user wants it in conversation, not buried in the artifact. Always cover:

- **In the TODO, not tracked** — every WORK item with no thread. Propose a slug for each.
- **Tracked, not in the TODO** — threads with no TODO entry. Ask whether they want one, or whether
  the thread is deliberately off-list (the `flagged` and `parked` ones usually are).
- **Priority moves** — where the TODO now implies a different priority than the thread carries.
- **Merged, closed or newly opened PRs** since the last sweep.
- **Ambiguities** — two TODO entries that may be one piece of work, a PR link that was inferred
  from wording rather than stated. Say which are guesses.

## Priority lives in the TODO

The org priority cookie is authoritative: `[#A]` = P1, `[#B]` = P2, `[#C]` = P3, `[#D]` = parked.
The user sets it in emacs with `C-c ,` or `S-up`/`S-down`, and the tracker mirrors it — never the
other way round.

Position in the list is used **only to seed a cookie that does not exist yet**, so a new item never
has to be ranked twice: `IN-PROGRESS` or the top quarter → `[#A]`, `AWAITING-REVIEW`/`HANDED-OFF`
or the top half → `[#B]`, the rest → `[#C]`. A parent marked `DONE` with an open child counts as
open. Once a cookie is written, position is ignored for that item.

A thread with no TODO entry has nowhere to keep a cookie, so it carries `P2 (pinned)` in the
tracker instead; the sync leaves pinned priorities alone.

`HANDED-OFF` plus `[[ow-to:<login>][@login]]` means the work is someone else's now — not done,
still worth chasing. `apply_decisions.py` writes both when the hand-off comes from the board.
**The person is a link, not a tag:** org tags allow only `[[:alnum:]_@#%]`, so a login with a
hyphen (`bug-author`, `minahil-naeem`) cannot be one — an earlier version used a tag and the
unparseable text was swallowed into the link description and re-appended on every sync.

## Who to hand something to

`.open-work/people.json` maps the first names the user writes ("abdullah", "toby") to GitHub
logins, verified against the org member list. `build.py` uses it to suggest a reviewer when a
thread names someone, which beats the repo-frequency fallback. Add to it whenever a new name
appears; check for collisions first (there are three Abdullahs in the org).

## Interrogation mode — walking the board together

Invoked by `/open-work interrogate`, or by the user asking to go through what is open,
reprioritise, or work out where to start. A sync answers *what is open*; this answers *what is
actually true, what is really one piece of work, and what to do first*. It is a conversation, so
the work is in asking few, well-evidenced questions — `.open-work/interrogate.py` does the lookups
so the questions are about judgement.

```
python3 ~/src/abyss/.open-work/sweep.py        # first — the questions must be about today
python3 ~/src/abyss/.open-work/build.py
python3 ~/src/abyss/.open-work/interrogate.py  # all groups -> interrogation.json, agenda last
```

### Phase 0 — refresh, and say what moved

Always sweep first: the user's blind spot is the work that arrived while they were not looking, and
a question about a merged PR wastes the one thing this session spends. Report what changed since
the last sweep before asking anything.

### Phase 1 — hygiene, in batched questions

One `AskUserQuestion` per group, `multiSelect: true`, options carrying the evidence — never more
than four questions in a call, and never a question whose answer is already on disk. The groups, in
the order they are worth asking:

| Group | The question | What an answer changes |
| --- | --- | --- |
| `merge` | are these two threads one piece of work? | merge the blocks, keep the older slug, re-point `[[ow:…]]` links |
| `inbound` | does this inbound review belong to a thread? | add its URL to that thread's `Links:`; it leaves the queue |
| `contradictions` | the thread says X, GitHub says Y | fix `Status:`/`Next:`, or request the reviewer nobody asked for |
| `hypotheses` | this is marked unproven — still a guess? | promote to fact *with* what verified it, or drop it |
| `stale` | past its own priority's idle limit — still live? | re-date it, re-prioritise it, or close it |
| `vague` | `Next:` does not say what to do | get one concrete next action, or park it |
| `closeout` | open over six months — close it? | close on GitHub, or record it as deliberately kept |

Rules that matter more than coverage:

- **Evidence or no question.** Every option says why it was grouped — "both link bedrock#1027", not
  "these look related". A grouping the user cannot check is one they will rubber-stamp.
- **Never re-ask.** Record each answer the moment it is given, with `settled.py --record`. The next
  session will not ask again unless the thread moves.
- **Stop when the user tires.** Partial is fine; the settled answers persist. Getting through
  `merge` and `contradictions` alone is a good session.
- **Their words, their thread.** Write back what they said, not a tidied version of it.

### Phase 2 — where to start

Only once the board is honest. Ask for capacity in the user's terms (how much time, what kind of
work), then propose an order and argue for it in one line each — what it unblocks, who is waiting,
what it costs. The `agenda` group gives the walking order: priority first, then the threads
carrying the most unanswered questions, then the longest unlooked-at. Reprioritising is **always**
a TODO edit — the cookie is the source of truth, the tracker mirrors it.

### Phase 3 — write it back, in this order

1. `OPEN_WORK.md` — statuses, `Next:`, merged blocks, `Links:` for folded reviews.
2. `settled.py --reviewed <slug>…` — stamps `Reviewed:` on every thread actually walked through.
   That is what stops the next session re-opening settled ground; a thread is only fresh until its
   `Updated:` date moves past it.
3. The TODO — priority cookies only, via `todo_sync.py --apply`, backed up first.
4. GitHub — request the reviewers that were agreed, close what was agreed closed. Say what was
   done, not what was decided.
5. `closed_work.py archive` — every thread closed in this session, now the user has seen it.
6. `build.py`, then republish (or ask `abyss-trinity-open` to).

### What it must not do

Decide anything on the user's behalf. Reword their `Next:` into something tidier. Merge threads
because the slugs look alike — the evidence is PR links, cross-references and rare ticket keys, and
a shared epic is not evidence. Ask about `parked` work at all.

## Rules

- **Never edit the user's TODO except for its machine-readable parts** — the `ow:` link, the
  priority cookie, and the `HANDED-OFF` keyword with its `ow-to:` link — plus `--tidy`, which the
  user asked for on 2026-10-29: drop finished WORK items and order the rest by priority cookie
  (their order kept within a priority; other sections untouched). Every write backs the file up to
  `.pre-ow` first. Do not reword or complete their items, and add new ones **only when the user
  asks for them** (they did, for the release findings).
- Statuses are a fixed vocabulary: `blocked` · `active` · `review` · `resolved` · `flagged` ·
  `backlog` · `done`. `resolved` means the root cause is found but the fix is not applied. Put the
  nuance in `Waiting on`, not in the status field — prose there sorts last and renders grey.
- Never hand-edit between the `BEGIN GENERATED` / `END GENERATED` markers in `OPEN_WORK.md`.
- Label what was measured and what is a hypothesis. Never promote a guess to a fact by repetition.
- Absolute dates, never "last week".
- The board's buttons only work on the published artifact — a local `board.html` has no
  `window.claude`, so its controls hide themselves. Don't tell the user to click anything locally.
- `~/src/abyss` is not a git repo; `OPEN_WORK.md` is the only copy.

## Tooling

The code lives in hq, `~/hq/etc/claude/skills/open-work/scripts/`, and is symlinked into
`~/src/abyss/.open-work/` so the commands above keep working. Everything the scripts read and write
— `open-prs.json`, `people.json`, `settled.json`, `board.html`, decisions — stays in
`~/src/abyss/.open-work/` (override with `OPEN_WORK_DATA`), as do `OPEN_WORK.md` and `closed-work/`,
which are not versioned.

| File | Does |
| --- | --- |
| `.open-work/sweep.py` | GitHub sweep → `open-prs.json`; reviewers, drift, stacks |
| `.open-work/todo_sync.py` | reconcile threads against the TODO; mirror priorities; write links |
| `.open-work/orgtodo.py` | parse and rewrite org headlines (links, cookies, keywords, tags) |
| `.open-work/people.json` | first name → GitHub login, for reviewer suggestions |
| `.open-work/build.py` | regenerate the tracker's PR section and `board.html` |
| `.open-work/apply_decisions.py` | fold board button decisions back into the tracker |
| `.open-work/local_state.py` | worktrees, dirty trees, stashes, unpushed branches |
| `.open-work/tracker.py` | shared thread parser/writer — writes are surgical, only changed fields are re-rendered |
| `.open-work/interrogate.py` | the analysis an interrogation session runs on: merges, folds, contradictions, agenda |
| `.open-work/closed_work.py` | archive done threads and landed PRs to `closed-work/YYYY-MM.md`; search them |
| `.open-work/settled.py` | remembers answered questions and stamps `Reviewed:`, so they are not asked twice |
