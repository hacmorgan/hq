"""
Sweep every local abyss repo for the user's open PRs and record their true state.

Mergeability is re-queried per PR: `gh pr list` reports UNKNOWN for most of them
because GitHub computes it lazily, which badly understates the conflict count.
Duplicate clones of one origin (abyss-bedrock-alt) are counted once.

Writes open-prs.json beside this script, and prints a diff against the previous
sweep so what changed since the last refresh is explicit.
"""

import os
import json
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import closed_work

HERE = Path(os.environ.get("OPEN_WORK_DATA", Path.home() / "src/abyss/.open-work"))  # data, not code
REPO_ROOT = HERE.parent
USER = "hacmorgan"
NOW = datetime.now(timezone.utc)

LIST_FIELDS = "number,title,url,headRefName,baseRefName,isDraft,createdAt,updatedAt,additions,deletions,changedFiles"
VIEW_FIELDS = "mergeable,mergeStateStatus,reviewDecision,isDraft,reviewRequests,reviews"
# review bodies posted by automation are not a human having looked at the change
BOT_REVIEWERS = {"claude", "github-actions", "copilot-pull-request-reviewer", "sonarcloud",
                 "windsurf-bot", "dependabot"}


def run(cmd, timeout=300):
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return proc.returncode, proc.stdout, proc.stderr


# --- discover repos that have a github remote ---
def repo_slug(directory: Path):
    if not (directory / ".git").exists():
        return None
    code, out, _ = run(["git", "-C", str(directory), "remote", "get-url", "origin"])
    if code != 0 or "github.com" not in out:
        return None
    return out.strip().split("github.com")[-1].lstrip(":/").removesuffix(".git")


candidates = {}
for directory in sorted(REPO_ROOT.iterdir()):
    if not directory.is_dir():
        continue
    slug = repo_slug(directory)
    if slug:
        candidates[directory.name] = {"dir": directory, "slug": slug}

# one directory per origin: prefer the one named after the repo itself
canonical_dirs = {}
for name, info in candidates.items():
    slug = info["slug"]
    if slug not in canonical_dirs or name == slug.split("/")[-1]:
        canonical_dirs[slug] = name
duplicate_clones = sorted(set(candidates) - set(canonical_dirs.values()))
for name in duplicate_clones:
    candidates.pop(name)
print(f"repos with a github remote: {len(candidates)} (skipped duplicate clones: {duplicate_clones or 'none'})")


# --- list this user's open PRs per repo ---
def list_prs(item):
    name, info = item
    code, out, err = run(
        ["gh", "pr", "list", "--repo", info["slug"], "--author", USER,
         "--state", "open", "--limit", "200", "--json", LIST_FIELDS],
        timeout=300,
    )
    info["prs"] = json.loads(out) if code == 0 else []
    if code != 0:
        info["list_error"] = err.strip()[-300:]
        print(f"  !! {name}: {info['list_error']}")


with ThreadPoolExecutor(max_workers=8) as pool:
    list(pool.map(list_prs, candidates.items()))

repos = {name: info for name, info in candidates.items() if info.get("prs")}
print(f"repos with open PRs: {len(repos)}, total {sum(len(i['prs']) for i in repos.values())}")


# --- default branch plus every ref we need, fetched once per repo ---
def recent_reviewers(slug):
    """
    Who has reviewed this user's recently closed PRs in this repo, most frequent first.
    """
    code, out, _ = run(
        ["gh", "pr", "list", "--repo", slug, "--author", USER, "--state", "closed",
         "--limit", "40", "--json", "reviews,reviewRequests"], timeout=300,
    )
    if code != 0:
        return []
    tally = {}
    for pr in json.loads(out):
        people = {review.get("author", {}).get("login") for review in pr.get("reviews") or []}
        people |= {request.get("login") for request in pr.get("reviewRequests") or []}
        for login in people:
            if login and login not in BOT_REVIEWERS and login != USER:
                tally[login] = tally.get(login, 0) + 1
    return [login for login, _ in sorted(tally.items(), key=lambda pair: -pair[1])]


def prepare_repo(item):
    name, info = item
    _, def_out, _ = run(["gh", "api", f"repos/{info['slug']}", "--jq", ".default_branch"])
    info["default"] = def_out.strip()
    refs = {pr["headRefName"] for pr in info["prs"]} | {pr["baseRefName"] for pr in info["prs"]}
    refs.add(info["default"])
    code, _, _ = run(["git", "-C", str(info["dir"]), "fetch", "--no-tags", "origin", *sorted(refs)], timeout=900)
    lcode, lout, _ = run(["git", "-C", str(info["dir"]), "ls-remote", "--heads", "origin"], timeout=300)
    info["remote_heads"] = {
        line.split("\trefs/heads/")[1] for line in lout.splitlines() if "\trefs/heads/" in line
    } if lcode == 0 else set()
    info["ls_remote_ok"] = lcode == 0
    info["recent_reviewers"] = recent_reviewers(info["slug"])
    print(f"  fetched {name}: default={info['default']} ok={code == 0} "
          f"reviewers={info['recent_reviewers'][:3]}")


with ThreadPoolExecutor(max_workers=6) as pool:
    list(pool.map(prepare_repo, repos.items()))


# --- per-PR enrichment: real mergeability, CI, drift ---
def pr_view(slug, number):
    """
    Re-query one PR; GitHub computes mergeability lazily, so a first UNKNOWN is retried.
    """
    for attempt in range(3):
        code, out, _ = run(["gh", "pr", "view", str(number), "--repo", slug, "--json", VIEW_FIELDS], timeout=120)
        if code != 0:
            return {}
        data = json.loads(out)
        if data.get("mergeable") != "UNKNOWN" or attempt == 2:
            return data
        subprocess.run(["sleep", "3"])
    return {}


def pr_checks(slug, number):
    code, out, err = run(
        ["gh", "pr", "checks", str(number), "--repo", slug, "--json", "name,state,bucket,link"], timeout=180
    )
    if code != 0 and not out.strip():
        text = (err or "").lower()
        if "no checks" in text or "no check runs" in text:
            return {"state": "none", "failing_checks": [], "counts": {}}
        return {"state": "unknown", "failing_checks": [], "counts": {}}
    try:
        checks = json.loads(out)
    except json.JSONDecodeError:
        return {"state": "unknown", "failing_checks": [], "counts": {}}
    if not checks:
        return {"state": "none", "failing_checks": [], "counts": {}}
    counts, failing = {}, []
    for check in checks:
        bucket = check.get("bucket") or check.get("state", "").lower()
        counts[bucket] = counts.get(bucket, 0) + 1
        if bucket in ("fail", "cancel"):
            failing.append(check.get("name"))
    if counts.get("fail") or counts.get("cancel"):
        state = "failing"
    elif counts.get("pending"):
        state = "pending"
    elif counts.get("pass"):
        state = "passing"
    else:
        state = "none"
    return {"state": state, "failing_checks": failing[:3], "counts": counts}


def enrich(args):
    name, info, pr = args
    base, head = pr["baseRefName"], pr["headRefName"]
    base_exists = base in info["remote_heads"] if info["ls_remote_ok"] else None

    behind, behind_note = None, None
    if base_exists:
        code, out, err = run(
            ["git", "-C", str(info["dir"]), "rev-list", "--count", f"origin/{head}..origin/{base}"], timeout=180
        )
        if code == 0 and out.strip().isdigit():
            behind = int(out.strip())
        else:
            behind_note = (err or out).strip()[-200:] or "rev-list failed"
    else:
        behind_note = "base branch no longer exists on remote"

    view = pr_view(info["slug"], pr["number"])
    checks = pr_checks(info["slug"], pr["number"])
    head_to_number = {other["headRefName"]: other["number"] for other in info["prs"]}
    updated = datetime.fromisoformat(pr["updatedAt"].replace("Z", "+00:00"))
    created = datetime.fromisoformat(pr["createdAt"].replace("Z", "+00:00"))

    requested = [
        request.get("login") for request in (view.get("reviewRequests") or []) if request.get("login")
    ]
    reviewed = []
    for review in view.get("reviews") or []:
        login = (review.get("author") or {}).get("login")
        if login and login not in BOT_REVIEWERS and login != USER and login not in reviewed:
            reviewed.append(login)

    record = {
        "repo": name,
        "repo_slug": info["slug"],
        "default_branch": info["default"],
        "number": pr["number"],
        "title": pr["title"],
        "url": pr["url"],
        "head": head,
        "base": base,
        "base_is_default": base == info["default"],
        "base_exists_on_remote": base_exists,
        "commits_behind_base": behind,
        "commits_behind_note": behind_note,
        "is_draft": pr["isDraft"],
        "mergeable": view.get("mergeable", "UNKNOWN"),
        "merge_state_status": view.get("mergeStateStatus", "UNKNOWN"),
        "review_decision": view.get("reviewDecision") or None,
        "review_requests": requested,
        "reviewers": reviewed,
        "has_reviewer": bool(requested or reviewed),
        "ci": checks,
        "created_at": pr["createdAt"],
        "updated_at": pr["updatedAt"],
        "additions": pr["additions"],
        "deletions": pr["deletions"],
        "changed_files": pr["changedFiles"],
        "stacked_on": head_to_number.get(base),
        "days_since_update": (NOW - updated).days,
        "age_days": (NOW - created).days,
        "needs_retarget": base_exists is False,
    }
    print(f"  {name}#{pr['number']} ci={checks['state']} merge={record['mergeable']} behind={behind}")
    return record


jobs = [(name, info, pr) for name, info in repos.items() for pr in info["prs"]]
with ThreadPoolExecutor(max_workers=8) as pool:
    records = list(pool.map(enrich, jobs))
records.sort(key=lambda record: (record["repo"], record["number"]))


# --- stacks: chains of PRs whose base is another open PR's head ---
children = {}
for record in records:
    if record["stacked_on"]:
        children.setdefault((record["repo"], record["base"]), []).append(record)

stacks = []
for record in records:
    if record["stacked_on"] is not None:
        continue  # only walk from the bottom of a stack
    chains = []

    def walk(node, trail):
        trail = trail + [node]
        kids = children.get((node["repo"], node["head"]), [])
        if not kids:
            chains.append(trail)
            return
        for kid in kids:
            walk(kid, trail)

    walk(record, [])
    for chain in chains:
        if len(chain) > 1:
            stacks.append({
                "repo": record["repo"],
                "chain_bottom_to_top": [node["number"] for node in chain],
                "branches": [node["head"] for node in chain],
            })


def suggest_reviewers(record, records, repo_reviewers):
    """
    Who could review this: whoever reviewed another PR in the same stack first,
    then whoever reviews this repo most often.
    """
    suggestions = []

    def add(login, why):
        if not login or login == USER or login in BOT_REVIEWERS:
            return
        if any(login == suggestion["login"] for suggestion in suggestions):
            return
        suggestions.append({"login": login, "why": why})

    stack_mates = [
        other for other in records
        if other["repo"] == record["repo"] and other["number"] != record["number"]
        and (other["base"] == record["head"]
             or other["head"] == record["base"]
             or (other["base"] == record["base"] and not record["base_is_default"]))
    ]
    for mate in stack_mates:
        for login in mate["reviewers"] + mate["review_requests"]:
            add(login, f"reviewed #{mate['number']} in the same stack")
    for login in repo_reviewers.get(record["repo"], []):
        add(login, f"reviews {record['repo']} most often")
    return suggestions[:3]


def tally(key):
    counts = {}
    for record in records:
        counts[str(record[key])] = counts.get(str(record[key]), 0) + 1
    return counts


repo_reviewers = {name: info.get("recent_reviewers", []) for name, info in repos.items()}
for record in records:
    record["suggested_reviewers"] = (
        [] if record["has_reviewer"] else suggest_reviewers(record, records, repo_reviewers)
    )

summary = {
    "generated_at": NOW.isoformat(),
    "repo_reviewers": repo_reviewers,
    "prs_without_reviewer": [
        f"{r['repo']}#{r['number']}" for r in records if not r["has_reviewer"] and not r["is_draft"]
    ],
    "github_user": USER,
    "total_open_prs": len(records),
    "repos_scanned_with_github_remote": len(candidates),
    "repos_with_open_prs": len(repos),
    "duplicate_clones_skipped": duplicate_clones,
    "per_repo_counts": {
        name: len([r for r in records if r["repo"] == name])
        for name in sorted({r["repo"] for r in records},
                           key=lambda n: -len([r for r in records if r["repo"] == n]))
    },
    "by_ci_state": {
        state: len([r for r in records if r["ci"]["state"] == state])
        for state in sorted({r["ci"]["state"] for r in records})
    },
    "by_mergeable": tally("mergeable"),
    "by_merge_state_status": tally("merge_state_status"),
    "by_review_decision": tally("review_decision"),
    "drafts": len([r for r in records if r["is_draft"]]),
    "prs_on_deleted_base": [f"{r['repo']}#{r['number']}" for r in records if r["needs_retarget"]],
    "prs_with_failing_ci": [f"{r['repo']}#{r['number']}" for r in records if r["ci"]["state"] == "failing"],
    "prs_conflicting": [f"{r['repo']}#{r['number']}" for r in records if r["mergeable"] == "CONFLICTING"],
    "stacks": stacks,
}

# --- inbound: PRs waiting on this user's review, which the author query never sees ---
def inbound_reviews():
    code, out, _ = run(
        ["gh", "search", "prs", "--review-requested=@me", "--state=open", "--limit", "100",
         "--json", "repository,number,title,author,updatedAt,createdAt,url,isDraft"], timeout=300,
    )
    if code != 0:
        print("  !! inbound review search failed")
        return []
    records = []
    for pr in json.loads(out):
        updated = datetime.fromisoformat(pr["updatedAt"].replace("Z", "+00:00"))
        records.append({
            "repo": pr["repository"]["name"],
            "number": pr["number"],
            "title": pr["title"],
            "url": pr["url"],
            "author": pr["author"]["login"],
            "is_draft": pr.get("isDraft", False),
            "updated_at": pr["updatedAt"],
            "days_since_update": (NOW - updated).days,
        })
    return sorted(records, key=lambda record: (record["author"], -record["days_since_update"]))


inbound = inbound_reviews()
by_author = {}
for record in inbound:
    by_author.setdefault(record["author"], []).append(record)
summary["inbound_reviews"] = len(inbound)
summary["inbound_by_author"] = {login: len(prs) for login, prs in
                                sorted(by_author.items(), key=lambda kv: -len(kv[1]))}
HERE.joinpath("inbound-prs.json").write_text(json.dumps({"prs": inbound}, indent=2))
print(f"\ninbound reviews waiting on you: {len(inbound)} from {len(by_author)} people")


# --- diff against the previous sweep, then replace it ---
output = HERE / "open-prs.json"
if output.exists():
    previous = json.loads(output.read_text())
    shutil.copy(output, HERE / "open-prs.previous.json")
    old = {f"{r['repo']}#{r['number']}": r for r in previous["prs"]}
    new = {f"{r['repo']}#{r['number']}": r for r in records}
    print(f"\nCLOSED OR MERGED since {previous['summary']['generated_at'][:10]}:")
    for key in sorted(set(old) - set(new)):
        print(f"  {key}  {old[key]['title'][:70]}")
    # keep a record of what landed, for later reference
    closed_work.log_prs([old[key] for key in sorted(set(old) - set(new))])
    print("NEWLY OPENED:")
    for key in sorted(set(new) - set(old)):
        print(f"  {key}  {new[key]['title'][:70]}")
    print("STATE CHANGES:")
    for key in sorted(set(old) & set(new)):
        diffs = [
            f"{field}: {old[key][field]} -> {new[key][field]}"
            for field in ("mergeable", "review_decision", "is_draft", "base")
            if old[key][field] != new[key][field]
        ]
        if old[key]["ci"]["state"] != new[key]["ci"]["state"]:
            diffs.append(f"ci: {old[key]['ci']['state']} -> {new[key]['ci']['state']}")
        if diffs:
            print(f"  {key}: " + "; ".join(diffs))

output.write_text(json.dumps({"summary": summary, "prs": records}, indent=2))
print(f"\nwrote {output} — {len(records)} open PRs across {len(repos)} repos")
