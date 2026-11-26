# Box records

One file per machine+distro, named to match that machine's branch:
`enzo-arch.md`, `bruno-ubuntu.md`, `bisous-arch.md`, and so on.

## Why these live on `main`

Everything else in this repo is branch-per-box because *configuration* has to
diverge. Records are the opposite: their whole value is being readable from any
box without checking out another branch. "What did we do to enzo's bootloader?"
should be answerable from bruno.

So `etc/boxes/` lives on `main` and propagates to every box branch through the
merges that already happen routinely. Each box only ever writes its own file,
so the merges never conflict.

## Updating a record

Record changes go on `main`, then merge into the box branch:

```sh
git worktree add /tmp/hq-main main    # avoids swapping live dotfiles
cd /tmp/hq-main
$EDITOR etc/boxes/<box>.md
git commit -am "boxes: <what changed>" && git push
cd ~/hq && git merge main
git worktree remove /tmp/hq-main
```

Use a worktree rather than `git checkout main`. `dots/` is symlinked into `~`,
so checking out another branch rewrites your live i3, zsh and X config.

## What belongs here

Hard-won state that is **not** recoverable from the config in this repo or from
package metadata — why a workaround exists, which constraints are permanent,
what was tried and rejected, and what will break next and when.

Not: package lists (`etc/pacagelist.txt` has those), dotfile contents, or
anything a command can print in a second.
