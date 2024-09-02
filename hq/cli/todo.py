#!/usr/bin/env python3


"""
Lightweight application for writing and aggregating TODOs
"""


from pathlib import Path
from datetime import datetime
from shutil import copyfile
from os import environ
import sys
from usb import USBError

from hq.cli import getchar, run_typer_app
from hq.shell import sh_run
from hq.hardware.thermal_printer import (
    print_thermally,
    print_thermally_unpriveliged,
    MAX_LINE_WIDTH,
)

# Parent directory under which TODOs are saved
_user = environ.get("SUDO_USER", environ["USER"])
ROOT_TODO_DIR = Path(f"/home/{_user}/.hq-secret/etc/todo").expanduser()

# File format of TODO files
TODO_SUFFIX = ".org"

# Command to run an editor
TODO_EDITOR = "emacs -nw"

# Main menu text
TODO_MENU = """

    todo - {todo_name} (previous: {previous_todo_name})

    (n) new todo / edit existing todo
    (c) copy from previous
    (d) dump to stdout
    (p) print
    (q) quit

"""


def todo(name: str | None = None) -> None:
    """
    Lightweight application for writing and aggregating TODOs

    Args:
        name: Specific name for this TODO, instead of default name by date. Will be
            saved under a directory for the current year/month unless `name` contains a
            "/" anywhere, in which case it is treated as a path relative to
            ~/hq/etc/todo
    """
    # Construct path to which we will (maybe) save this TODO later
    if name is not None and "/" in name:
        todo_dir = ROOT_TODO_DIR
        todo_path = (ROOT_TODO_DIR / name).with_suffix(TODO_SUFFIX)
    else:
        now = datetime.now()
        todo_dir = ROOT_TODO_DIR / f"{now.year}/{now.month}"
        todo_path = (
            todo_dir / (name if name is not None else str(now.day))
        ).with_suffix(TODO_SUFFIX)

    # Find the previous TODO (if it exists)
    previous = find_previous()

    # We need to be able to return to the menu after editing, so we read keys from stdin
    # on repeat
    while True:

        # Print the menu
        print(
            TODO_MENU.format(
                todo_name=todo_path.relative_to(ROOT_TODO_DIR),
                previous_todo_name=previous.relative_to(ROOT_TODO_DIR),
            )
        )

        # Wait for the next keypress and get the value
        match (char := getchar()):

            # (n): New TODO
            case b"n":
                todo_path.parent.mkdir(exist_ok=True, parents=True)
                edit_todo(todo_path=todo_path)

            # (c): Copy from previous TODO
            case b"c":
                todo_path.parent.mkdir(exist_ok=True, parents=True)
                if previous is not None:
                    copyfile(src=previous, dst=todo_path)
                edit_todo(todo_path=todo_path)

            # (p): Print TODO (to thermal printer)
            case b"p":
                print_todo(todo_path=todo_path)

            # (d): Dump TODO (to stdout)
            case b"d":
                print(todo_path.read_text())

            # (q): Quit
            case b"q":
                break

            # Anything else is undefined
            case _:
                print(f"Undefined input character: {char}")


def edit_todo(todo_path: Path) -> None:
    """
    Open the TODO editor (to edit a TODO)

    Args:
        todo_path: Path to save TODO to/open editor at
    """
    sh_run(f"{TODO_EDITOR} {todo_path}")


def find_previous() -> Path | None:
    """
    Search the TODO dir for the most recent TODO

    Returns:
        Path of the most recent TODO if there is one, None otherwise
    """
    try:
        return sorted(
            (
                path
                for path in ROOT_TODO_DIR.rglob("**/*")
                if not path.is_dir()
                and not any(path.stem.startswith(char) for char in ".#")
            )
        )[0]
    except IndexError:
        return None


def print_todo(todo_path: Path) -> None:
    """
    Print a TODO on a thermal printer

    Args:
        todo_path: Path to load TODO from for printing
    """
    # Start with a header
    todo_name = str(todo_path.with_suffix("").relative_to(ROOT_TODO_DIR))
    todo_text = " " * 4 + todo_name + r"\n" + " " * 4 + "-" * len(todo_name) + r"\n" * 2

    # Read lines of TODO text from org file
    org_lines = todo_path.read_text().split("\n")

    # Process lines sequentially, adding section indices and formatting for printing
    entry_idx = "0"
    level = 1
    for line in org_lines:

        # We add a few spaces to give ourselves some speace to attach to a clipboard
        line_start = "    "

        # Compute the section index for this TODO based on number of asterisks
        if line.strip().startswith("*"):
            this_level = line.split(" ")[0].count("*")

            # Simply add another section index (i.e. "0.0" -> "0.0.0") for indents
            if this_level > level:
                entry_idx += ".1"
                level += 1

            # Drop the innermost index and increment the second innermost (i.e. "0.0.0"
            # -> "0.1") for outdents
            elif this_level < level:
                entry_idx_parts = entry_idx.split(".")[:-1]
                entry_idx_parts[-1] = str(int(entry_idx_parts[-1]) + 1)
                entry_idx = ".".join(entry_idx_parts)
                level -= 1

            # Increment innermost index if the level hasn't changed
            else:
                entry_idx_parts = entry_idx.split(".")
                entry_idx_parts[-1] = str(int(entry_idx_parts[-1]) + 1)
                entry_idx = ".".join(entry_idx_parts)

            # Add section index to output text (to be printed) and appropriate indent
            line_start += f"({entry_idx})"

        # Format TODO nicely
        line = line_start + line.replace("*", "").replace("TODO", "[]").replace(
            "DONE", "[x]"
        )

        # Split line if it is too long
        while len(line) > MAX_LINE_WIDTH:
            split_idx = max(
                idx
                for idx, char in enumerate(line)
                if char == " " and idx < MAX_LINE_WIDTH
            )
            todo_text += line[:split_idx] + r"\n" + level * "  " + " " * 8
            line = line[split_idx:]

        todo_text += rf"{line}\n"

    # Send formatted text to thermal printer
    print_thermally_unpriveliged(todo_text)


if __name__ == "__main__":
    run_typer_app(todo)
