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

### 2. `nvidia-container-*` file conflict

`nvidia-container-runtime` / `nvidia-container-toolkit` have a file conflict
over `/usr/bin/nvidia-container-runtime`; `pacman -Dk` exits 1. Database
hygiene rather than a live failure.

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
fork of barrier and has Wayland support. Migration is genuine work rather than
a flag, and it is bilateral — the other machines run barrier too, so they have
to move in step. Probably the single largest obstacle to daily sway use.

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

## Change log

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
