#!/usr/bin/env python3
# coding: utf-8


"""
Coffee reference and calculation tool
"""


import subprocess
import sys
from os.path import commonprefix, basename, isdir, expanduser, dirname
from os import listdir, makedirs
from pathlib import Path
from functools import partial
from typing import List

from hq.io import getchar

CTRL_C = b"\x03"
BACKSPACE = b"\x7f"
CLEAR = b"\x0c"

KOPI_DB_DIR = "~/src/hq/etc/kopi/"


sh_run = partial(subprocess.run, shell=True)


def kopi(input_path: str = KOPI_DB_DIR) -> None:
    """
    Database
    """
    input_path = expanduser(input_path)
    suggestions = []
    while True:
        input_dir = dirname(input_path)
        makedirs(input_dir, exist_ok=True) 
        # suggestions = sorted(fuzzy_find(input_chars=input_chars, input_dir=input_dir))
        suggestions = [
            entry
            for entry in listdir(input_dir)
            if entry.startswith(basename(input_path))
        ]
        if len(suggestions) == 1:
            path = f"{input_dir}/{suggestions[0]}/"
            if isdir(path):
                makedirs(path, exist_ok=True)
                input_path = path
                continue

        sh_run("clear")
        print(f"> {input_path[-60:]}")
        print("\n".join(map(str, suggestions)))

        char = getchar()
        # print(char)
        # break

        if char == CTRL_C:
            return

        elif char in (b"\r", b"\n"):
            path = f"{input_dir}/{suggestions[0]}" if suggestions else input_path
            makedirs(dirname(path), exist_ok=True)
            sh_run(f"vim.basic {path}")
            return

        elif char == BACKSPACE:
            input_path = input_path[:-1]

        elif char == b"\t":
            prefix = commonprefix(suggestions)
            input_path = (
                f"{input_dir}/{prefix}"
                if len(prefix) > len(str(input_path))
                else input_path
            )

        elif char.isascii():
            input_path = input_path + char.decode()


def fuzzy_find(input_chars: bytes, input_dir: str) -> List[bytes]:
    """
    Find matching paths with fzf
    """
    return (
        sh_run(
            f"cd {input_dir} && fzf -f {input_chars.decode()}",
            capture_output=True,
        )
        .stdout.strip()
        .split()
    )


if __name__ == "__main__":
    # input_dir = KOPI_DB_DIR
    # if len(sys.argv) > 1:
    #     operation = sys.argv[1]
    #     if "grind-settings".startswith(operation):
    #         input_dir = f"{KOPI_DB_DIR}/grind-settings"
    #     elif "recipes".startswith(operation):
    #         input_dir = f"{KOPI_DB_DIR}/recipes"
    kopi()
    sys.exit(0)
