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
127 MB → ~15 MB each; ESP 51% → 33% and falling.

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

## Open items

- `opencl-nvidia` 615.78.08 is installed, from the normal repos, while the
  driver is on the 580 branch — a version mismatch. The AUR has a matching
  `opencl-nvidia-580xx` which is **not** installed. Untested whether OpenCL
  actually works right now.
- `nvidia-container-runtime` / `nvidia-container-toolkit` have a file conflict;
  `pacman -Dk` exits 1.
- Orphaned `/usr/lib/modules` directories from long-gone kernels
  (`5.19.13-arch1-1`, `6.0.2-arch1-1`, `6.14.7-arch2-1`).
- Wayland has never been tried. KMS is now on for mainline, which was the
  blocker. `sway` is the natural first experiment given i3.
- Board firmware F11 is from 2019 and has never been updated.

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
