"""
Record local work in progress: worktrees, dirty trees, and branches never pushed
or ahead of their upstream. This is work that exists only on this machine.
"""

import os
import json
import subprocess
from pathlib import Path

HERE = Path(os.environ.get("OPEN_WORK_DATA", Path.home() / "src/abyss/.open-work"))  # data, not code
REPO_ROOT = HERE.parent


def run(cmd, timeout=120):
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


# --- every checkout: main clones plus their linked worktrees ---
checkouts = []
for directory in sorted(REPO_ROOT.iterdir()):
    if not directory.is_dir() or not (directory / ".git").exists():
        continue
    code, out, _ = run(["git", "-C", str(directory), "worktree", "list", "--porcelain"])
    if code != 0:
        continue
    current = {}
    for line in out.splitlines():
        if line.startswith("worktree "):
            if current:
                checkouts.append(current)
            current = {"repo": directory.name, "path": line.split(" ", 1)[1]}
        elif line.startswith("branch "):
            current["branch"] = line.split("refs/heads/", 1)[-1]
        elif line == "detached":
            current["branch"] = "(detached)"
    if current:
        checkouts.append(current)


# --- dirty state and divergence per checkout ---
for checkout in checkouts:
    path = checkout["path"]
    _, status, _ = run(["git", "-C", path, "status", "--porcelain"])
    changed = [line for line in status.splitlines() if line.strip()]
    checkout["dirty_files"] = len(changed)
    checkout["untracked"] = len([line for line in changed if line.startswith("??")])
    checkout["sample_changes"] = [line[3:] for line in changed if not line.startswith("??")][:6]

    branch = checkout.get("branch", "(detached)")
    checkout["upstream"] = None
    checkout["ahead"] = None
    checkout["behind"] = None
    if branch != "(detached)":
        code, upstream, _ = run(["git", "-C", path, "rev-parse", "--abbrev-ref", f"{branch}@{{upstream}}"])
        if code == 0 and upstream:
            checkout["upstream"] = upstream
            code, counts, _ = run(["git", "-C", path, "rev-list", "--left-right", "--count", f"{upstream}...{branch}"])
            if code == 0 and counts:
                behind, ahead = counts.split()
                checkout["behind"], checkout["ahead"] = int(behind), int(ahead)
        else:
            checkout["upstream"] = "(none — never pushed)"
            code, count, _ = run(["git", "-C", path, "rev-list", "--count", f"origin/HEAD..{branch}"])
            checkout["ahead"] = int(count) if code == 0 and count.isdigit() else None

    _, last, _ = run(["git", "-C", path, "log", "-1", "--format=%cs %h %s", branch if branch != "(detached)" else "HEAD"])
    checkout["last_commit"] = last

    _, stash, _ = run(["git", "-C", path, "stash", "list"])
    checkout["stashes"] = len([line for line in stash.splitlines() if line.strip()])

HERE.joinpath("local-state.json").write_text(json.dumps(checkouts, indent=2))

interesting = [
    c for c in checkouts
    if c["dirty_files"] or c["stashes"] or (c["ahead"] or 0) > 0 or c.get("upstream") == "(none — never pushed)"
]
print(f"checkouts: {len(checkouts)}, with local-only state: {len(interesting)}\n")
for c in sorted(interesting, key=lambda c: (c["repo"], c["path"])):
    print(f"{c['repo']:32s} {c.get('branch','?'):48s} dirty={c['dirty_files']:<4} "
          f"ahead={c['ahead']} stashes={c['stashes']} upstream={c['upstream']}")
    print(f"    {c['path']}")
    print(f"    last: {c['last_commit']}")
    if c["sample_changes"]:
        print(f"    changed: {', '.join(c['sample_changes'])}")
