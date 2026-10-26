# hq

Hamish's personal config, scripts and system records. Branch per machine+distro
(`enzo-arch`, `bruno-ubuntu`, …); `main` holds what is common to all of them.

`dots/` is symlinked into `~` by `sysbs`. **Never `git checkout` another branch
in `~/hq`** — it rewrites the live i3, zsh and X config under the running
session. Use `git worktree add` instead.

## Box records — keep these current

`etc/boxes/<branch>.md` is a living record of each machine's state: why
workarounds exist, which constraints are permanent, what was tried and
rejected, and what will break next.

**When you do non-trivial system work on a box — bootloader, kernel, drivers,
partitions, package pinning, anything whose reasoning won't survive in the
config itself — update that box's record in the same session.** Add to the
change log with a date, and revise any section the work made stale rather than
leaving the old claim sitting there.

Record the *reasoning and the constraints*, not the commands. The value is in
what a future reader can't reconstruct: why this flag is set, what breaks if
it's removed, what the next failure will be. Package lists live in
`etc/pacagelist.txt`; anything a command prints in a second doesn't belong here.

Correct what you find wrong. A record that confidently states something untrue
is worse than no record — if you disprove a claim in it, fix the claim.

See `etc/boxes/README.md` for the update workflow.
