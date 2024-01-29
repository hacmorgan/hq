#!/usr/bin/env python3
# coding: utf-8


"""
Coffee reference and calculation tool
"""


import subprocess
import sys
from functools import partial
from os import listdir, makedirs, environ
from os.path import basename, commonprefix, dirname, expanduser, isdir
from pathlib import Path
from typing import List, Optional

from hq.io_tools import getchar

CTRL_C = b"\x03"
BACKSPACE = b"\x7f"
CLEAR = b"\x0c"

KOPI_DB_DIR = "~/src/hq/etc/kopi/"
if not Path(KOPI_DB_DIR).expanduser().exists():
    KOPI_DB_DIR = "~/hq/etc/kopi"

PROMPT_LENGTH = 60


sh_run = partial(subprocess.run, shell=True)


def kopi(input_path: str = KOPI_DB_DIR, fuzzy: bool = False) -> None:
    """
    Database
    """
    input_path = expanduser(input_path)
    suggestions = []
    last_input_dir = None
    last_listdir = []
    while True:
        input_dir = dirname(input_path)
        if input_dir != last_input_dir:
            makedirs(input_dir, exist_ok=True)
            last_input_dir = input_dir
            last_listdir = sorted(listdir(last_input_dir))
        if fuzzy:
            input_chars = removeprefix(input_path, prefix=input_dir)
            suggestions = sorted(
                fuzzy_find(input_chars=input_chars, input_dir=input_dir)
            )
        else:
            suggestions = [
                entry
                for entry in last_listdir
                if entry.startswith(basename(input_path))
            ]

        sh_run("clear")
        prompt = "> "
        if len(input_path) > PROMPT_LENGTH:
            prompt += "..."
        print(f"{prompt}{input_path[-PROMPT_LENGTH:]}")
        print("\n".join(map(str, suggestions)))

        char = getchar()
        # print(char)
        # break

        if char == CTRL_C:
            return

        if char in (b"\r", b"\n"):
            path = f"{input_dir}/{suggestions[0]}" if suggestions else input_path
            makedirs(dirname(path), exist_ok=True)
            sh_run(f"{environ['EDITOR']} {path}")
            return

        if char == BACKSPACE:
            input_path = input_path[:-1]

        elif char == b"\t":
            prefix = commonprefix(suggestions)
            input_path = (
                f"{input_dir}/{prefix}"
                if len(prefix) > len(basename(input_path))
                else input_path
            )
            if len(suggestions) == 1:
                path = f"{input_dir}/{suggestions[0]}/"
                if isdir(path):
                    makedirs(path, exist_ok=True)
                    input_path = path

        elif char.isascii():
            input_path = input_path + char.decode()


def removeprefix(path: str, prefix: str) -> Optional[str]:
    """
    Remove prefix from string

    Args:
        path: Path to remove prefix from
        prefix: Prefix to remove from string

    Returns:
        Path with prefix removed, or None if prefix is not a valid prefix
    """
    prefix_size = len(prefix)
    if path[:prefix_size] != prefix:
        return None
    return path[prefix_size:]


def fuzzy_find(input_chars: str, input_dir: str) -> List[str]:
    """
    Find matching paths with fzf
    """
    return (
        sh_run(
            f"cd {input_dir} && fzf -f {input_chars}",
            capture_output=True,
        )
        .stdout.decode()
        .strip()
        .split()
    )


if __name__ == "__main__":
    kopi(fuzzy="-f" in sys.argv)
    sys.exit(0)
