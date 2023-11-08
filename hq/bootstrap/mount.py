#!/usr/bin/env python3
# coding: utf-8


"""
Filesystem mount wrangling tools
"""


from os import makedirs
from os.path import expanduser
from typing import Optional

import typer
from hq.shell import sh_run


def mount_remote(host: str, path: str, local_path: Optional[str] = None) -> None:
    """
    Mount a remote filesystem unter ~/mnt

    e.g. mount_remote(host="enzo", path="~/Documents/lmms/projects") will mount to
    ~/mnt/enzo/home/hamish/Documents/lmms/projects

    Args:
        host: Name of host (in ssh config)
        path: Path to mount on remote host
        local_path: Path to mount to locally. Constructed as above by default
    """
    # Resolve full remote path
    remote_path = sh_run(f"ssh {host} realpath {path}").stdout.decode("utf-8").strip()

    # Construct path to mount to on local machine if required
    if local_path is None:
        local_path = f"{expanduser('~')}/mnt/{host}/{remote_path}"
    makedirs(local_path, exist_ok=True)

    # Execute sshfs command
    sh_run(f"sshfs {host}:{remote_path} {local_path}")


if __name__ == "__main__":
    typer.run(mount_remote)
