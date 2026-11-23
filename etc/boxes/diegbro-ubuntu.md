# diegbro — Ubuntu 24.04

Branch: `diegbro-ubuntu` · Last verified: **2026-11-23**

New work laptop, which joined alongside diego (the older work laptop) rather than
replacing it. Hostname `diegos-smaller-fatter-newer-brother`; ssh alias
`diegbro_wifi`. A **26.04 install is planned** as an early test ahead of the
rest of the team. See [Next: 26.04](#next-2604) for what that will disturb.

## Hardware

| | |
|---|---|
| Model | Dell Pro Max 14 MC14250, BIOS 1.9.1 (2025-12-10) |
| CPU | Intel Core Ultra 7 265H (Arrow Lake-H), 16 threads |
| RAM | 62 GiB |
| GPU | Intel Arrow Lake-P iGPU (`i915`) + **NVIDIA `10de:2db9`** (Blackwell-generation dGPU) |
| Disk | 954 GB NVMe: 1G ESP, the rest ext4 `/`. Single-boot, no Windows |
| Display | 1920x1200 internal panel (`eDP-1`) |
| Secure Boot | **disabled** |

The ssh alias says `_wifi`, but at induction `192.168.0.165` was a DHCP lease
on **Ethernet** (`enp0s31f6`), and the Wi-Fi interface was down. If the box
moves to Wi-Fi, it gets a different MAC and probably a different address, and
the alias stops resolving to it. Barrier doesn't care, because the client
dials enzo.

## Graphics — the NVIDIA GPU is not in use

No NVIDIA driver is installed. `nouveau` is loaded but holds no references,
and X runs entirely on the Intel iGPU. That's fine for i3 and office work, and
it's why nothing has broken. Anything needing CUDA or a fast GL path will hit it.

`ubuntu-drivers` recommends `nvidia-driver-595-open`. Blackwell is supported
**only by the open kernel modules**, so the closed `nvidia-driver-*` (non
`-open`) packages it also lists are a dead end on this GPU. Secure Boot is off,
so DKMS modules load without MOK enrolment.

Deliberately deferred: installing the driver on 24.04 right before a 26.04
reinstall is wasted effort, and a hybrid-graphics driver is the most likely
thing to complicate the upgrade.

## Session

GDM starts the **i3** X session (`gdm-x-session --run-script i3`). There is no
GNOME session in use, so GNOME settings (wallpaper and so on) have no effect.

`~/.xsessionrc` is the hook. GDM's `/etc/X11/Xsession` sources it with
**`/bin/sh` (dash) under `set -e`**, which creates two traps:

- **No zsh syntax.** The `diego` branch's `.xsessionrc` backgrounds with `&!`.
  dash reads that as a syntax error and aborts the source, which ends the
  login under `set -e`. This branch uses plain `&`. Check with `dash -n`
  before relying on any edit.
- **No foreground command that can fail.** A non-zero exit also kills the
  login. diego's file had `xinput set-prop 12 372 1`; on this machine device
  12 is the "Intel HID 5 button array", so that line fails. Tap-to-click is
  handled by `configure-xinput` from the i3 config instead, which finds the
  touchpad by name.

`.xinitrc` was renamed to `.xsessionrc` upstream. This box's old `~/.xinitrc`
link was dangling and has been removed. `startx` is not used here.

## Why a separate branch from `diego`

Before induction, this box ran a **stale, pre-rebase copy of `diego`**. Its
commits were later rebased into origin under new hashes, and its only
unpublished change (sourcing `~/.config/secret-sauce` in zshrc) was already
upstream. The old HEAD is kept as tag `pre-diegbro-induction` in the box's
own clone. The two laptops differ in display number (`:0` here, `:1` on
diego), xinput ids, panel size and barrier position, and these differences
live in session config that the two branches can't share. The fork point is
`origin/diego` as of 2026-11-23.

## hq cannot pull from GitHub

`~/.ssh` has no private key, so `git fetch origin` fails with
`Permission denied (publickey)`. Updates currently get **pushed from enzo**
straight into this clone (`git push diegbro_wifi:hq <branch>`). Its
`origin/*` refs are only as fresh as the last push from enzo.

The `ssh-add ~/.ssh/id_rsa` line in the i3 config, and the systemd ssh-agent
unit, are no-ops until a key exists. Fixing this means generating a key here
and adding it to GitHub. That needs Hamish.

## Barrier

Barrier **client**. The server runs on enzo (`enzo-arch`:
`dots/barrier/diego-enzo-george.conf`). Layout, left to right:

    diegbro  ·  diego  ·  enzo

The screen name is the hostname (no `--name`), so **renaming the host breaks
the link** until the server config is updated. A 26.04 reinstall is the
likely way that would happen.

Barrier links are strict neighbours. **The mouse reaches diegbro only by
passing through diego, so with diego off or asleep, diegbro can't be reached.**
If diego is retired, re-link diegbro directly to enzo's left.

## Next: 26.04

Things the reinstall will disturb, roughly by likelihood:

- **Barrier package.** Barrier is unmaintained, and recent Debian/Ubuntu
  releases are dropping it for `input-leap`. Check whether 26.04 still ships
  `barrier`. If it doesn't, this box becomes the first `input-leap` client
  against enzo's barrier 2.4 server, which needs protocol compatibility
  tested. enzo's own record plans to move barrier to input-leap for Wayland
  anyway.
- **NVIDIA.** Install the `-open` driver on 26.04 rather than carrying anything
  over from 24.04.
- **Hostname and ssh key.** Both are lost on reinstall unless backed up. The
  hostname feeds barrier (see above). Set up the GitHub key on 26.04 rather
  than on 24.04.
- **Xsession behaviour.** Re-verify that GDM still sources `~/.xsessionrc` via
  dash under `set -e` before assuming the traps above still apply or are gone.

## Change log

**2026-11-23**: Inducted. Forked `diegbro-ubuntu` from `diego` and moved the
clone onto it from its stale pre-rebase `diego` (old HEAD tagged
`pre-diegbro-induction`). Fixed the `.xsessionrc` traps above, linked
`~/.xsessionrc` and `~/.config/zellij`, and installed `feh`, `picom` and
`numlockx`. Set the wallpaper to `etc/wallpapers/eboy_tok_1920_1200.png`, which
matches the panel. Added the box to enzo's barrier server as the leftmost
screen.
