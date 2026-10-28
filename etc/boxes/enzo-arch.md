# enzo — Arch Linux

Branch: `enzo-arch` · Last verified: **2026-10-26**

Desktop workstation. Dual-boots Windows (systemd-boot shows a Windows Boot
Manager entry). The dominant constraint on this box is the **GPU**: see
[Graphics](#graphics), which is the section most likely to matter later.

## Hardware

| | |
|---|---|
| Board | Gigabyte X570 UD, firmware **F11** (2019-12-06 — never updated) |
| CPU | AMD Ryzen 9 3900X, 12C/24T |
| RAM | 62 GiB |
| GPU | **NVIDIA GTX 980** (GM204, Maxwell, PCI `10de:13c0`) |
| NVMe | 931.5 GB — `/boot` (600M, vfat), swap (15G), `/` (500G ext4), Windows partitions, spare 97G ext4 |
| SATA | 3.6 TB NTFS, label `games`, mounted `/mnt/storage` |

## Graphics

**This is the thing that will eventually force a decision.**

The GTX 980 is Maxwell. NVIDIA's **580 branch is the last one that supports
Maxwell**, and it is not in the Arch repos — it comes from the AUR as
`nvidia-580xx-dkms` + `nvidia-580xx-utils` (both pinned to the same version;
the dkms package hard-depends on the exact matching utils version).

### Update discipline — the important bit

Run **`yay -Syu`**, never bare `sudo pacman -Syu`.

`pacman` doesn't know about AUR packages. It will happily advance the kernel
while leaving the NVIDIA driver behind, the DKMS build then fails against the
new kernel, and you reboot into a `simpledrm` console with no acceleration.
This is not bad luck; it is structurally guaranteed. It happened on
2026-10-26 (kernel 7.1.7 → 7.2.11, driver stuck at 580.159.04).

**Rollback paths**, if a driver update goes wrong:

- Previous driver packages: `~/.cache/yay/nvidia-580xx-utils/*.pkg.tar.zst`
- Previous kernels: `/var/cache/pacman/pkg/` — `paccache.timer` is enabled
  weekly with `-k3`, so the last three are always kept
- Boot `Arch LTS`, which runs a separate kernel and its own DKMS build, and has
  so far survived every mainline breakage

**AUR gotcha:** the pkgbase is `nvidia-580xx-utils`, *not* `nvidia-580xx-dkms`.
Cloning `aur.archlinux.org/nvidia-580xx-dkms.git` returns an empty repo. Clone
the utils name, or let `yay` handle it.

### The nouveau endgame

When the 580 branch stops building against current kernels, nouveau is the
fallback. Current state of that option, checked 2026-10-26:

- **Good news:** NVK (nouveau's Vulkan driver) became a conformant Vulkan 1.3
  implementation on Maxwell in **Mesa 25.1** (April 2025) and is enabled by
  default. The driver software is genuinely modern now.
- **The permanent blocker:** GM204 is **GM20x**, and reclocking on GM20x
  requires NVIDIA-signed firmware that was never released. The nouveau project
  says there is little hope this will ever change. The card would run **stuck at
  boot clocks** — a fraction of its rated speed. (Earlier **GM10x** Maxwell
  *can* reclock. GM204 is on the wrong side of the line.)
- **No CUDA, no OpenCL.** Anything using the container toolkit, meshroom,
  cloudcompare or similar stops working entirely. Not slower — gone.

So nouveau is a usable **escape hatch**, not an upgrade path: the box stays a
working desktop while a replacement card is sourced, rather than being dead.
Don't plan around it; do remember it exists.

### Stack

`nvidia-580xx-dkms` 580.196.07 · `mesa` 26.2.5 · `xorg-server` 21.1.25 ·
`i3-wm` 4.25.1 (X11, not Wayland).

`nouveau` is blacklisted by `/usr/lib/modprobe.d/nvidia-580xx-utils.conf`,
shipped by the driver package. That blacklist is load-bearing — it is the only
thing keeping nouveau off the GPU now that `nomodeset` is gone from the
mainline entry.

## Audio — PipeWire

Migrated from PulseAudio to **PipeWire** on 2026-10-27. One server now handles
audio *and* video: `pipewire` is the graph engine, `wireplumber` is the policy
layer that decides what devices exist and where streams go, and
`pipewire-pulse` is a shim speaking the PulseAudio protocol on the usual
socket.

Nothing was ported. `pulsemixer`, the `i3status-rs` sound block, browsers and
VLC all link `libpulse` and reconnected without noticing — `pactl info`
reports `Server Name: PulseAudio (on PipeWire 1.6.10)`. Device names survived
the swap verbatim (`alsa_output.pci-0000_0a_00.4.analog-stereo` and friends),
so per-application device preferences carried over too.

**Why this happened.** The day before, installing `kooha` and
`xdg-desktop-portal-wlr` for Wayland screencast pulled in `wireplumber` as a
hard dependency. It started beside PulseAudio and its ALSA monitor claimed
`/dev/snd/controlC0..3`; two session managers then held the same cards,
neither could open the PCM devices, every sink sat `SUSPENDED`, and playback
died with `Failed to create sink input: sink is suspended`. The first fix
fenced WirePlumber off ALSA. Migrating properly removes the cause instead:
there is now exactly one thing managing the sound cards, which is the point.

**Two gains that were not the goal:**

- The onboard ALC887 capture input (`alsa_input.pci-0000_0a_00.4`) is now
  exposed. PulseAudio ran that card on an output-only profile and never
  offered it.
- Screencast and camera share the graph with audio, which is the arrangement
  the Wayland portal wanted all along (item 6).

### jack2 is deliberately still installed

`carla`, `lmms` and `audacity` are present, and `jack2` was left alone —
`pipewire-jack` *conflicts* with it, so adopting it is a separate decision
with its own risk. See backlog item 8. Until then JACK and PipeWire are two
servers that both want the hardware, so they must not run at once; this is the
same class of fault as the one above, merely dormant because `jackd` is not
started automatically.

### If audio ever goes silent again

Check for more than one daemon on the cards before anything else:

```
fuser -v /dev/snd/*      # should name wireplumber, and nothing else
wpctl status             # Audio section should be populated
pactl info               # should say "(on PipeWire ...)"
```

## Flatpak — two traps, both non-obvious

Only one app is installed (`org.cloudcompare.CloudCompare`), but it brings two
failure modes worth knowing before they bite again.

### GL extensions are pinned to the exact host driver

A flatpak ships its own userspace GL stack, which must match the host kernel
module **exactly** — `org.freedesktop.Platform.GL.nvidia-<version>`. So every
time the host NVIDIA driver moves, the installed extension is orphaned and GPU
apps silently lose acceleration until the matching one is fetched.

This is a standing consequence of the AUR driver situation in Graphics: each
`nvidia-580xx-dkms` bump breaks flatpak GPU apps until `flatpak update` runs.
Nothing warns you; the app just fails or falls back to software.

**Flatpak never garbage-collects the old ones.** By 2026-10-27 that had
accumulated 31 extensions spanning the 510 (2022) to 580 series, at 560–900 MB
each — about 17 GB of the 21 GB flatpak store, none of which matched the
running driver. `flatpak uninstall --unused` reclaimed it, taking the store to
3.7 GB. Expect this to creep back; see backlog item 9.

### Flatpak file dialogs hang when SSHFS mounts die

A sandboxed app cannot draw its own file chooser — it has no view of the
filesystem — so the dialog is a **separate top-level window owned by
`xdg-desktop-portal-gtk`**, and the app merely waits on a D-Bus reply.

The GTK chooser stats every entry in `~/.config/gtk-3.0/bookmarks` to draw its
sidebar. Those bookmarks point at `/mnt/vault`, `/mnt/pond`, `/mnt/rapid`,
`/mnt/2204` and `/mnt/work*` — the SSHFS mounts. When the VPN drops behind
them, stat blocks forever and the portal's main loop wedges.

**The important part: unmounting afterwards does not fix it.** Clearing the
mount frees the path, but a process already blocked stays blocked, and
`xdg-desktop-portal-gtk` is a long-lived session daemon — observed carrying
the wedge for 1 day 18 hours, breaking every file dialog opened since.

Diagnosis, because the symptom misleads. The *app* looks stuck but is in
ordinary interruptible `poll()`; it is the portal that is blocked:

```
ps -o stat,wchan <app pid>     # Sl+ / poll_... = waiting on D-Bus, not I/O
                               # D state would mean a genuinely dead mount
gdbus call ... Peer.Ping                  # answers even when wedged
gdbus call ... Settings.ReadAll '[]'      # times out iff the main loop is stuck
```

`Ping` is served by GDBus's worker thread, so it replying while a real method
call hangs is the signature of a blocked main loop, not a healthy daemon.

**Fix: `systemctl --user restart xdg-desktop-portal-gtk`** — restart the
backend, not the application. The pending request fails cleanly and the app
usually survives with its state intact. Native GTK apps (GIMP, etc.) are
unaffected: they draw their own chooser in-process and never involve the
portal, so only flatpaks are at risk.

## Boot

**systemd-boot.** ESP is `/dev/nvme0n1p1` (600 MB) at `/boot`.

| Entry | Kernel | Flags |
|---|---|---|
| `arch.conf` | `linux` | `rw nvidia_drm.modeset=1` |
| `arch-lts.conf` | `linux-lts` | `rw nomodeset nvidia_drm.modeset=0` |

Root is `UUID=673c2ece-cd2d-49d7-8fb8-abf78009b61d`.

### ESP budget

600 MB is tight, and `mkinitcpio` has filled it before. The trap:

The **`kms` hook pulls in `nouveau`**, and nouveau drags the *entire*
`/usr/lib/firmware/nvidia` tree into the early CPIO — **105 MiB**, of which
~101 MiB is GSP firmware for Ampere (`ga102`, 75 MiB) and Turing (`tu102`,
26 MiB) cards this machine does not have. The GTX 980's own `gm204` firmware
rounds to 0.00 MiB. That happened in *both* images, so 255 MB of a 600 MB ESP
was firmware for other people's GPUs, serving a blacklisted driver.

**Fix applied 2026-10-26:** `kms` removed from `HOOKS` in
`/etc/mkinitcpio.conf`. Safe here because the NVIDIA modules were never in the
initramfs anyway — modesetting happens after the root pivot. Images went
127 MB → 15.3 MB each; ESP **302 MB → 88 MB (51% → 15%)**.

LTS was rebuilt and booted first, before mainline was touched, so the slim
image was proven on a kernel that still had a known-good fallback.

Also removed: the `initrd /amd-ucode.img` line from both entries. The
`microcode` hook already embeds microcode in the early CPIO, and with
`autodetect` it ships only this CPU family's blob (21 KB, vs 300 KB for the
whole AMD set).

If `kms` is ever restored, watch the ESP immediately.

Default is **`arch.conf`** (mainline), set 2026-10-26 once mainline was proven.

`arch-lts.conf` deliberately keeps `nomodeset nvidia_drm.modeset=0` even though
DKMS builds the driver for both kernels and it could run KMS. Its value as a
rescue entry is being a *genuinely different* configuration — different kernel,
different DKMS build, all the old workarounds on. If KMS itself ever turns out
to be the problem, "everything off" is the fallback you want. The cost is only
a low-res TTY on a boot you rarely see.

### Gotcha: `default` must include `.conf`

`loader.conf` previously read `default arch-lts` and silently matched nothing —
`bootctl` kept reporting Arch as default. The `default` key is matched against
the entry **id**, which includes the `.conf` suffix. Always write
`default arch.conf`, not `default arch`.

Note that `bootctl list` marks the running entry `(selected)`, which is *not*
the same as `(default)`. Don't read one as confirmation of the other.

## Campaign backlog

Ongoing tidy-up of a long-running install. Ordered by value to Hamish, not by
effort. Keep this list current: tick things off into the change log, and add
what you find.

### 1. Fan noise and idle thermals

**The one that is actually felt day to day** — the CPU fan audibly spins up and
down at idle. Measured 2026-10-26 at load average 0.03:

| | |
|---|---|
| `Tctl` / `Tccd1` | **68.0 °C / 73.5 °C** — a 3900X should idle nearer 40 °C |
| cores at ~4.1 GHz | **10 of 24**, while essentially idle |
| frequency floor | **2200 MHz** (`cpuinfo_min_freq`) — the CPU cannot be asked to go lower |
| C-state residency | dominated by C2, so cores *are* sleeping properly |
| GPU | 50 °C, 31 % fan, 60 W — **not** the noise source |

Three independent levers, cheapest first. They are not alternatives; 1 and 2
are worth doing regardless of 3.

**(a) Fan curve hysteresis — free, no flashing. Try this first.**

*Hysteresis* means a system's response depends on its recent history, not just
its present input — the threshold to switch one way sits apart from the
threshold to switch back. A house thermostat is the everyday case: it starts
heating at 19 °C but does not stop until 21 °C. Without that gap it would
chatter on and off around a single setpoint. The deliberate "stickiness" is the
point.

A fan curve with no hysteresis does exactly that chattering. Sitting at the
temperature where the curve steps up, the fan speeds up, which cools the chip,
which drops it below the threshold, so the fan slows, so it heats again. That
audible up-down-up cycle is the symptom here, and it is a control-loop problem
rather than a cooling one.

Gigabyte Smart Fan 5 in the existing F11 BIOS exposes temperature hysteresis
plus step-up/step-down times (how long a reading must persist before the fan
reacts). Widening both damps the oscillation without changing peak cooling at
all. `fancontrol` from `lm_sensors` is the software equivalent if the BIOS
options prove too coarse.

**(b) Thermal interface — cheap, an hour.** The build is around six years old.
68-73 °C at genuine idle is abnormal for this chip and suggests dried-out paste
or a dust-loaded cooler. This addresses *why the fan has to work at all*,
rather than how it reacts. Strong candidate, and independent of anything
software can do.

**(c) `amd_pstate`, which needs a BIOS update — riskier, do last.**

The driver cannot load at all. CPPC is present —
`/sys/devices/system/cpu/cpu0/acpi_cppc/` exists and its *performance* fields
are populated (`highest_perf=216`, `nominal_perf=135`,
`lowest_nonlinear_perf=79`, `lowest_perf=20`) — but every *frequency* field
reads zero (`lowest_freq=0`, `nominal_freq=0`, `guaranteed_perf=0`), so
`amd_pstate` has no way to map a performance level onto MHz and exits
`-ENODEV`. The board's ACPI `_CPC` object is simply incomplete. No BIOS menu
setting fixes that; the table itself is wrong.

(The absent `cppc` CPU flag is a red herring — that is the MSR-based CPPC of
Zen 3+. Zen 2 uses the ACPI shared-memory interface, which is why the sysfs
directory exists at all.)

What it costs today: `acpi-cpufreq` exposes exactly **three** P-states —
3800 / 2800 / 2200 MHz. Scaling `lowest_perf` against `nominal_perf` (20 of
135, where 135 is the 3800 MHz base) puts `amd_pstate`'s floor near
**560 MHz** against today's **2200 MHz**. That is a real reduction in idle
power, plus continuous frequency selection and EPP instead of three coarse
steps that overshoot.

Fixing it means a firmware update. F11 dates to 2019-12-06 and Gigabyte shipped
considerably later BIOSes, so newer certainly exists — but files are specific
to board **revision 1.0 vs 1.1**, so confirm which this board is first.
Q-Flash Plus can flash without CPU, RAM or GPU installed, which lowers the
risk. Against it: a six-year-old board that currently boots reliably, a Windows
dual-boot, and a CMOS reset that would mean reconfiguring everything.

**Be honest about the causal chain before flashing.** (c) would lower idle
power and smooth frequency transitions, which plausibly reduces how often the
fan ramps. But if the real problem is (b), then (c) will disappoint, and it is
by far the most expensive of the three. Do (a) and (b) first and re-measure
idle temps before deciding.

### 2. 32 orphaned packages, and why `--remove-orphans` deserves care

`pacman -Qdt` lists 32 packages nothing depends on, and `sysbs
--remove-orphans` offers exactly that list. Most are plainly stale
(`gcc15`, `ffmpeg4.4`, `haskell-*`, `libxvmc`), but **`libe57format`** is an
E57 point-cloud library — the kind of thing the vision tooling pulls in. An
orphan is only "nothing *currently installed* depends on it", which is not the
same as unused: a locally built AUR package that was reinstalled or rebuilt can
leave its dependencies looking orphaned.

Read the list before accepting it, rather than taking the prompt at face
value.

### 3. Orphaned kernel module directories

`/usr/lib/modules/{5.19.13-arch1-1, 6.0.2-arch1-1, 6.14.7-arch2-1}` from
long-gone kernels. About 6.8 MB. Two minutes.

### 4. `ntfs3` for `/mnt/storage`

The 3.6 TB NTFS drive mounts as `fuseblk` — userspace `ntfs-3g` — not the
in-kernel `ntfs3`. `findmnt --verify` flags it. Works fine, but `ntfs3` is
considerably faster for large transfers.

### 5. `cuda` 13.4.3 against a 580-branch driver

Worth verifying rather than assuming. CUDA 13.x wants a recent driver and the
580 branch is roughly its floor, so this may be fine — but it has never been
tested, and the OpenCL mismatch below shows this class of problem fails
silently.

### 6. Wayland — aspirational, low priority

Hamish has explicitly said not to put much stock in this: a someday-maybe, not
a goal driving other decisions. Groundwork done 2026-10-26 so the experiment is
cheap whenever it is wanted.

`sway`, `swaybg`, `xorg-xwayland` and `wl-clipboard` are installed. Nothing
about the X setup was changed.

**How it starts — not via `.xinitrc`.** That file is consumed by
`startx`/`xinit`, which launches an *X server*. Sway is a Wayland compositor
and replaces the X server outright, so it reads none of it. `~/.zprofile` runs
`exec startx` only on `$XDG_VTNR -eq 1`, so tty1 keeps booting into i3
untouched; switch to another TTY and run `sway` to try it. No login manager is
involved, and nothing needs changing to go back.

**Requires the mainline boot.** Sway needs DRM/KMS. The `arch-lts` entry still
carries `nomodeset nvidia_drm.modeset=0` and lands on `simpledrm`, so sway
cannot work there at all. Use `arch`, which has `nvidia_drm.modeset=1`.

**The blockers are not sway itself — they are the X11-only tools around the
edges.** See item 7; that is where the actual work lives, and it is what keeps
this item low priority.

**Other things in the X config needing Wayland equivalents:** `picom` becomes
unnecessary (sway composites natively); `feh --bg-*` becomes `swaybg` /
`output * bg`; `xset r rate` and `numlockx` become sway `input` directives;
`xset s`/`dpms` and `xss-lock` become `swayidle` + `swaylock`; and
`configure-xinput` becomes sway `input` config.

**Sway was run for the first time on 2026-10-26 and works.** Findings:

- It shows a banner: *"Proprietary GPU drivers are not supported by sway. Do
  not report issues."* This is a disclaimer, not a failure — sway runs fine.
  (An earlier note here claimed `--unsupported-gpu` was gone because
  `sway --help` does not list it. That was wrong: `--help` is abridged to six
  options. The flag still exists, and the banner itself says to pass
  `--unsupported-gpu` or set `SWAY_UNSUPPORTED_GPU=true` to silence it.)
- **`i3status-rust` 0.36.2 works unchanged.** swaybar speaks the same protocol
  as i3bar, so the status bar is one less thing to port.
- **Sway is reading the i3 config directly — nothing was copied.** `sway(1)`
  searches `~/.sway/config`, `$XDG_CONFIG_HOME/sway/config`, `~/.i3/config`,
  then **`$XDG_CONFIG_HOME/i3/config`**, and falls through to the last of those
  since no sway config exists. So sway and i3 currently share one file:
  `~/.config/i3/config` → `hq/dots/i3/config`.

  That explains why it worked out of the box, but it is a trap rather than a
  feature. Both window managers now read the same tracked file, so any
  sway-only directive added there makes **i3** fail to parse, and the X-only
  `exec` lines (`xset`, `xss-lock`, `feh`, `configure-xinput`) are being run
  and failing under sway every time it starts.

  Before doing anything beyond casual experimenting, create
  `~/.config/sway/config` — search position 2, which wins over the i3 path.
  Track it as `dots/sway/config` so `sysbs` links it like the rest, and factor
  the genuinely shared bindings out rather than maintaining two divergent
  copies.
- **`peek` runs under XWayland but captures only the cursor.** A neat, concrete
  demonstration of why it cannot be ported: an XWayland client sees only other
  XWayland surfaces, never native Wayland ones, so there is nothing underneath
  it to capture. Not a bug to fix — it is the isolation model working as
  designed, and exactly the wall its author hit.

### 7. X11-only tooling that must be replaced before Wayland is viable

The window manager is the easy part. Sway reads an i3 config nearly unchanged.
What costs real effort is returning the *peripheral* tooling to parity — these
are the things that would silently stop working, and the reason item 6 stays
aspirational.

**`barrier` → `input-leap`.** Barrier 2.4.0 is X11-only. `.xinitrc` runs it as
a server sharing keyboard and mouse with diego and george, so under sway it
simply will not work. `input-leap` 3.0.3 is in `extra`; it is the maintained
fork of barrier and has Wayland support.

Scope is smaller than it first looked: **george is dead** (sitting unpowered in
the workshop as of 2026-10-26), so only **diego** has to move in step, and
Hamish's plan is to migrate both ends at once rather than run a mixed setup.
Still the largest piece of item 7, but a single coordinated change rather than
an open-ended one.

**`peek` → most likely `kooha`.** Peek 1.5.1 produces GIFs from a screen
region, which is a rare and genuinely useful capability, and it is X11-only.

Worth knowing before considering a fork: upstream **deprecated Peek
specifically because of Wayland**. The author's position was that the UI
approach has no future, because Wayland changed how applications are handled,
and that a replacement needs a new project with a new UI and a clean slate.

That is architectural rather than incidental. Peek works by positioning a
transparent frame over a screen region and capturing what is underneath —
Wayland deliberately refuses to tell a client where it is on screen or what
other windows contain. The capture backend would have to become
portal + PipeWire based, and region selection would have to be redesigned
around the portal's own picker. At that point very little of Peek survives,
and the result is approximately `kooha`.

So: try `kooha` (2.3.2, in `extra`) first — it is purpose-built for Wayland on
exactly this stack and does GIF output. `wf-recorder` (0.6.0) plus `gifski`
(1.34.0) is the CLI alternative and gives better GIF quality. A fork remains
reasonable if Kooha's UX disappoints, but it should be chosen with eyes open:
it is writing a new application, not patching an old one.

**Installed 2026-10-26:** `kooha` 2.3.2 and `xdg-desktop-portal-wlr` 0.8.4
(which pulled in `grim` and `slurp` — the wlroots screenshot and region-picker
tools, and what a sway-native `wf-recorder` GIF workflow would use). Neither is
tested yet.

**`dmenu-custom` needs reworking — and `dmenu` itself is the first problem.**
`applications/dmenu-custom` (150 lines) is the launcher front-end for a lot of
daily routines, and `dmenu` is X11-only, so the entry point goes before any of
its entries do. Replacements, all in `extra`: `wmenu` (sway's own default,
0.2.0), `bemenu`, `fuzzel`, `wofi`. `wmenu` is the closest drop-in.

Then its X11-bound actions, which are a decent map of the wider migration:

| in `dmenu-custom` | under sway |
|---|---|
| `scrot -z [-s] -e …` (4 call sites) | `grim` + `slurp` — both already installed |
| `picom-run` (turn compositor on/off) | delete it; sway composites natively |
| `xset -display :0.0 dpms force off` | `swaymsg "output * dpms off"` |
| `configure-xinput` | sway `input` directives in the config |

Only the `scrot` paths need real thought — two of the four use `-s` for
interactive region select, which is `slurp` piped into `grim`, and all four use
`-e` to post-process the capture, so the shell around them changes shape.

**Kooha is Wayland-only here, so peek is not replaced — it is complemented.**
Kooha needs the ScreenCast portal, and no installed backend offers that under
i3/X11: `wlr.portal` provides `ScreenCast`/`Screenshot` but declares
`UseIn=wlroots;sway;Wayfire;river;phosh;Hyprland`, so it never activates under
X11; `gtk.portal` does not implement ScreenCast at all and is `UseIn=gnome`.
Only GNOME's own backend would cover X11, and GNOME is not in use.

Keep both: `peek` for i3/X11, `kooha` for sway. That also means item 6 cannot
be evaluated on screen-recording grounds from the X session — the comparison
has to happen inside sway.

### 8. `pipewire-jack` — unify the pro-audio side, or keep jack2

The audio server question is **settled** (PipeWire, see above). What remains is
JACK. `carla`, `lmms` and `audacity` are installed alongside `jack2`.

Under the old arrangement, desktop audio and JACK were separate worlds and
running a DAW meant getting PulseAudio off the card first. `pipewire-jack`
collapses that: JACK clients become ordinary nodes in the same graph as the
browser, so Carla and LMMS can run without evicting anything.

The cost is that `pipewire-jack` **conflicts with `jack2`** and provides
`libjack.so` itself, so this is a swap, not an addition — and the **PreSonus
AudioBox 22 VSL** is the thing to watch, since latency and buffer settings are
configured differently (`pipewire.conf` quantum rather than `jackd -p`).

Worth doing on a day with time to re-test a DAW project. Until then, do not
start `jackd` while PipeWire holds the cards.

### 9. Teach `sysbs` to sweep unused flatpak refs

`flatpak uninstall --unused` is the flatpak analogue of `--remove-orphans`, and
nothing runs it automatically. Left alone it re-accumulates a GL extension per
driver update, which is how 17 GB built up unnoticed.

Safer than the pacman orphan list (item 2), since anything removed is simply
re-downloaded, so it is a reasonable candidate for standard operations rather
than a prompt. Worth pairing with a `flatpak update`, because the same driver
bump that orphans the old extension is what requires the new one.

## Change log

**2026-10-28** — CloudCompare had lost GPU acceleration: the 2026-10-26 driver
bump to 580.196.07 orphaned its flatpak GL extension, which must match the
host driver exactly. Swept 31 accumulated extensions (510-series onward) with
`flatpak uninstall --unused`, taking the store from 21 GB to 3.7 GB, and
updated — which also migrated CloudCompare off the end-of-life
`org.kde.Platform 5.15-24.08` onto 6.11.

Separately, a flatpak file dialog hung with every symptom of a dead SSHFS
mount while no dead mount existed. The culprit was `xdg-desktop-portal-gtk`,
wedged 1d18h earlier when the VPN dropped behind the mounts its bookmarks
point at; unmounting had not released it. Restarting the backend fixed it
without losing the application. Both recorded above.

Also fixed `$refresh_i3status`, which had been signalling `i3status` while the
bar runs as `i3status-rs`. Cosmetic only — the sound block is event-driven and
was never stale.

**2026-10-27 (later)** — Migrated the audio stack from PulseAudio to PipeWire:
installed `pipewire-pulse` and `pipewire-alsa`, which removed `pulseaudio`, and
retired the previous day's `50-no-alsa.conf` fence since WirePlumber is now
meant to own the cards. Restored the prior default sink/source and volumes,
which WirePlumber had reassigned to the AudioBox. Verified by measurement:
playback stream opens, mic captures real signal, `pulsemixer` and the
`i3status-rs` sound block reconnected through the shim unaided. `jack2` left
installed and untouched — see item 8.

**2026-10-27** — YouTube/YTMusic silent and microphone dead. Cause was *not*
sway, which was the natural suspicion: it was the previous day's `kooha` /
`xdg-desktop-portal-wlr` install dragging in WirePlumber, which fought
PulseAudio for the ALSA cards (see Audio, above). Fenced WirePlumber off the
sound hardware with `~/.config/wireplumber/wireplumber.conf.d/50-no-alsa.conf`
and restored audio live, without a reboot. Playback and capture both verified
by measurement rather than assumption. Added backlog item 8 — the config is
untracked, and the PulseAudio/PipeWire question is deferred, not answered.

**2026-10-26** — `pacman -Syu` broke mainline graphics (DKMS failed against
kernel 7.2.11; driver was 580.159.04). Fixed by updating the AUR driver to
580.196.07, which builds against both kernels. Then: reclaimed ~98 GB from
pacman/yay caches and enabled `paccache.timer`; enabled KMS on mainline
(`nvidia_drm.modeset=1`, verified `nvidia-drmdrmfb` rather than `simpledrm`);
removed the `kms` hook to recover ~210 MB of ESP; deleted the dead
`arch-fallback.conf` entry, which pointed at an
`initramfs-linux-fallback.img` that is never generated (both presets are
`PRESETS=('default')`); made mainline the boot default; and added these box
records plus the `sysbs --install-hq-claude` wiring that installs `CLAUDE.md`.
Both initramfs images rebuilt and verified booting; ESP ended at 88 MB (15%).
Tightened `/boot` to `fmask=0137,dmask=0077` (was `0022`/`0022`), silencing
systemd-boot's "random seed file is world accessible" warning. Note vfat
ignores these on `remount` — it took a full umount/mount to take effect.

Also fixed OpenCL, which was **entirely broken**: `clinfo` reported
`Number of platforms: 0`. The repo `opencl-nvidia` 615.78.08 was installed
against a 580-branch kernel driver. Replaced with `opencl-nvidia-580xx`
580.196.07 from the AUR, which `provides opencl-nvidia` so `cuda`'s dependency
survives the swap. Now reports one platform, GTX 980, OpenCL 3.0, 16 compute
units. Nothing would ever have reported this failure on its own — worth
remembering for the other version-mismatch items above.

**All of the above verified on the mainline boot** at the end of the day:
kernel 7.2.11 on the 15.3 MB initramfs, `nvidia_drm.parameters.modeset=Y` with
the console on `nvidia-drmdrmfb`, driver 580.196.07, OpenCL reporting one
platform, `/boot` at `0700` with no world-accessible warning from `bootctl`,
ESP at 88 MB of 599 MB. Both kernels were booted on their rebuilt images before
this was called done.

Finally, cleared the superseded initramfs backups from `~/.nvidia-fix-backup/`
(244 MB → 32 KB; the small config backups are kept), and resolved the
`nvidia-container-*` conflict. `nvidia-container-runtime` 3.8.1 turned out to
be a **2022 leftover that is no longer in any repo** — upstream folded the
runtime into `nvidia-container-toolkit`, which now ships
`/usr/bin/nvidia-container-runtime` itself along with 17 other files. Nothing
depended on the old package.

Two things that are easy to get wrong here, both hit during the fix:

1. **Removing it deletes the shared binary.** pacman does not check whether
   another package also owns a file, so `-R nvidia-container-runtime` took
   `/usr/bin/nvidia-container-runtime` with it. Reinstalling
   `nvidia-container-toolkit` restored it byte-identically.
2. **The toolkit was then an orphan.** It had been installed as a dependency
   *of the package just removed*, so `pacman -Qdt` listed it and
   `sysbs --remove-orphans` would have offered to delete the whole container
   stack. Marked explicit with `pacman -D --asexplicit`.

`pacman -Dk` now reports no database errors, and
`nvidia-container-runtime --version` reports 1.20.1.
