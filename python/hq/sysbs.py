"""
sysbs (system bootstrap) routines - set up environment(s)
"""


from pathlib import Path

import distro

from hq.shell import sh_run


ARCH = "arch"
UBUNTU = "ubuntu"
RASPBIAN = "raspbian"
PACKAGE_MANAGER_COMMAND = {
    ARCH: "pacman -Syu",
    UBUNTU: "apt install",
}
PACKAGE_MANAGER_COMMAND[RASPBIAN] = PACKAGE_MANAGER_COMMAND[UBUNTU]


def install_repo_packagelist() -> None:
    """
    Install standard packages for host distribution
    """
    # Determine host distro name and package manager install command
    distro_name = distro.id()

    # Read package list
    package_list_path = find_hq() / "etc/distro-packagelists" / distro_name
    with open(package_list_path, mode="r", encoding="utf-8") as pkg_lst_fp:
        package_list = pkg_lst_fp.read().strip().split()

    # Construct and run install command
    sh_run(f"sudo {PACKAGE_MANAGER_COMMAND[distro_name]} " + " ".join(package_list))


def find_hq() -> Path:
    """
    Find the HQ repo in the filesystem

    Returns:
        Path to root of HQ repo in filesystem
    """
    return Path("~/src/hq").expanduser()
