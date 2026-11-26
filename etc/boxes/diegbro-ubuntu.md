# diegbro — Ubuntu 24.04

Branch: `diegbro-ubuntu`, kept **identical to `diego`** (see
[Branches](#branches)) · Last verified: **2026-11-23**

New work laptop. It joined alongside diego (the older work laptop, XPS 15
9520, also Ubuntu 24.04) rather than replacing it. Hostname
`diegos-smaller-fatter-newer-brother`. A **26.04 install is planned** as an
early test ahead of the rest of the team. [Next: 26.04](#next-2604) is the
checklist for that.

## Hardware

| | |
|---|---|
| Model | Dell Pro Max 14 MC14250, BIOS 1.9.1 (2025-12-10) |
| CPU | Intel Core Ultra 7 265H (Arrow Lake-H), 16 threads |
| RAM | 62 GiB |
| GPU | Intel Arrow Lake-P iGPU (`i915`) + **NVIDIA `10de:2db9`** (Blackwell-generation dGPU) |
| Disk | 954 GB NVMe: 1G ESP, the rest ext4 `/`. Single-boot, no Windows |
| Display | 1920x1200 internal panel (`eDP-1`), same as diego |
| Secure Boot | **disabled** |

## Network

| Interface | MAC | Address | ssh alias |
|---|---|---|---|
| Ethernet `enp0s31f6` | `24:53:ed:c6:97:cc` | 192.168.0.165 | `diegbro` |
| Wi-Fi `wlp0s20f3` | `d4:94:a9:73:f6:c2` | 192.168.0.4 | `diegbro_wifi` |

Both are DHCP leases, and Hamish is setting router reservations for them
(2026-11-23). Until that's done, an address can move and the alias goes stale.
Barrier doesn't care, because the client dials enzo. Both addresses present
the same host key; when the `.4` entry was added to enzo's `known_hosts`, its
key was checked against the one read over the wired link.

For comparison, diego has Wi-Fi only in practice (`f4:ce:23:b6:6b:2e`,
192.168.0.38, `diego_wifi`). Its Ethernet is unplugged, so `diego`
(192.168.0.140) doesn't resolve to anything live.

## Graphics — the NVIDIA GPU is not in use

No NVIDIA driver is installed. `nouveau` is loaded but holds no references,
and X runs entirely on the Intel iGPU. That's fine for i3 and office work, and
it's why nothing has broken. Anything needing CUDA or a fast GL path will hit it.

`ubuntu-drivers` recommends `nvidia-driver-595-open`. Blackwell is supported
**only by the open kernel modules**, so the closed `nvidia-driver-*` (non
`-open`) packages it also lists are a dead end on this GPU. Secure Boot is off,
so DKMS modules load without MOK enrolment.

Deliberately deferred: installing the driver on 24.04 right before a 26.04
reinstall is wasted effort.

## Session

GDM starts the **i3** X session. There's no GNOME session in use, so GNOME
settings such as the wallpaper have no effect. `~/.xsessionrc` is the hook,
and it's shared with diego.

How it's sourced, verified on both laptops 2026-11-23: GDM uses
**`/etc/gdm3/Xsession`, which is bash with no `set -e`**, not
`/etc/X11/Xsession` (dash, `set -e`). So a failing line only logs to the user
journal (`gdm-x-session ... .xsessionrc: line N`), and zsh's `&!` happens to
parse. This record originally claimed both would abort the login; that was
tested against the wrong shell and is false. The file now uses plain `&`
anyway, so it's still safe if a future release swaps the wrapper. Re-check
on 26.04.

The X display number differs: **`:0` here and `:1` on diego**. Nothing in the
config may hardcode it. barrierc inherits `$DISPLAY`. Likewise, xinput ids
differ, and on *both* machines id 12 is the "Intel HID 5 button array", not
the touchpad. diego's old `xinput set-prop 12 372 1` had been silently doing
nothing. Tap-to-click comes from `configure-xinput`, which matches the
touchpad by name, and is confirmed on for both.

### Session dependencies nothing installs

hq has no Ubuntu package list (`etc/distro-packagelists/` is Arch-only), so
on both laptops the tools the session config calls were installed by hand or
not at all. The failure mode is silent: a missing tool logs to the journal or
pops one notification at login, and the feature quietly doesn't run.

- `xprintidle` and `pulseaudio-utils` (`pactl`): listed in `DEPENDENCIES` but
  **missing on diego too**. So since diego's i3 lock work, its `idle-lock`
  had exited at every login ("Idle auto-lock disabled"), meaning **no idle
  auto-lock**, and `in-call` could see the camera but not the mic. Installed
  on both 2026-11-23. `pactl` talks to PipeWire's Pulse layer here.
- `feh`, `picom`, `numlockx`: called from `.xsessionrc`. Installed on diegbro.
  diego got `picom` 2026-11-23 (v10, which accepts `dots/picom.conf` without
  errors on both). **diego still lacks `numlockx`.** That's harmless (journal
  noise), but it's the same class of gap.

The 26.04 reinstall will lose all of these. Reinstall them, or better, add an
Ubuntu list so `sysbs` does it.

## Branches

On 2026-11-23, both laptops ran the same session config and the remaining
differences (display number, xinput ids) are handled at runtime. So
`diegbro-ubuntu` was merged into `diego` and set to the same commit. The
separate branch exists only because records and the per-box convention are
keyed by branch. If it never diverges, collapsing it into `diego` is
reasonable. It **will** diverge at the 26.04 reinstall, which is when it
earns its keep.

History, for anyone confused by old refs: before induction this box ran a
stale pre-rebase copy of `diego`, tagged `pre-diegbro-induction` in its
clone. Nothing on it was missing from origin. diego itself was then **59
commits ahead of `origin/diego`**, because it had never pushed.

## hq cannot pull from GitHub

`~/.ssh` has no private key, so `git fetch origin` fails with
`Permission denied (publickey)`. Updates get **pushed from enzo** into this
clone. Its `origin/*` refs are only as fresh as that push. The i3 config's
`ssh-add ~/.ssh/id_rsa` and the systemd ssh-agent unit are no-ops here until a
key exists. Plan: add the key after the 26.04 install, not before.

## Barrier

Barrier **client**. The server is enzo (`enzo-arch`:
`dots/barrier/diego-enzo-george.conf`). Layout, left to right:

    diegbro  ·  diego  ·  enzo

The screen name is the hostname (no `--name`), so **renaming the host breaks
the link** until the server config is updated. Barrier links are strict
neighbours, **so diegbro can only be reached through diego**: if diego is off
or asleep, diegbro is unreachable. If diego is retired, re-link diegbro
directly to enzo's left.

**Changing networks drops barrier for about 30 seconds, then it recovers on its own.**
Pulling the Ethernet cable (verified 2026-11-23) leaves the client's TCP link
to enzo dead. barrierc only notices when its keepalive times out ("server is
dead", ~25–30 s after the last traffic), then redials enzo within seconds
over whatever link is up. No restart is needed: wait half a minute before
diagnosing. The old socket lingers on enzo in `FIN-WAIT-1` for a while, which
is harmless.

## Next: 26.04

Checked 2026-11-23 against Launchpad, GitHub and Arch:

- **Barrier is still in 26.04** (`resolute`: barrier 2.4.0+dfsg-4build3, the
  same build as 24.04). The reinstall does **not** force a KVM migration.
  Keep barrier. (An earlier version of this record guessed otherwise.)
- **input-leap is not an option.** It's archived upstream and was never in
  Ubuntu's archive.
- **Deskflow** is the maintained line: `deskflow` 1.26 in 26.04, 1.27 in Arch
  `extra`, absent from 24.04. Per its README, it's network-compatible with
  barrier in both directions, so this box could run a Deskflow client against
  enzo's barrier server on its own. If trying that, turn off Deskflow's
  default TLS to match `--disable-crypto`. Under i3/X11 there's no reason to
  bother. It only matters when enzo goes to sway, and Deskflow doesn't
  support sway either. See enzo-arch.md, item 7.
- **Hostname**: keep `diegos-smaller-fatter-newer-brother`, or update enzo's
  barrier config to match (see above).
- **NVIDIA**: install the `-open` driver fresh on 26.04.
- **ssh key**: create one and add it to GitHub so the clone can pull.
- **MACs** don't change on reinstall, so the router reservations survive. The
  `known_hosts` entries on enzo won't, because the host key is regenerated:
  remove both `.165` and `.4` lines.
- **Xsession**: re-check which wrapper GDM uses (see [Session](#session)).
- **Session packages**: reinstall the hand-installed set (see
  [Session dependencies](#session-dependencies-nothing-installs)).
- **Branch**: this is the point to let `diegbro-ubuntu` diverge from `diego`.

## Change log

**2026-11-23**: Inducted. Merged into `diego` the same day.
- Set up the new box: moved the clone off its stale pre-rebase `diego`, linked
  `~/.xsessionrc` and `~/.config/zellij`, and installed `feh`, `picom` and
  `numlockx`. Set the wallpaper to
  `etc/wallpapers/eboy_tok_1920_1200.png`.
- Added the box to enzo's barrier server as the leftmost screen.
- Wi-Fi brought up at .4. Split the aliases into `diegbro` (wired) and
  `diegbro_wifi`.
- Made `.xsessionrc` machine-neutral (no display number, no xinput id) and
  merged it into `diego`, so both laptops share one file.
- Confirmed barrier recovers by itself when the Ethernet cable is pulled
  (~30 s keepalive gap, then reconnects over Wi-Fi).
- Installed `xprintidle` and `pulseaudio-utils` on both laptops: diego's
  idle auto-lock had never been able to run. Added `picom` to diego.
- Corrected this record's original claims about `set -e` and `&!` (wrong
  shell) and about 26.04 dropping barrier (it doesn't).
