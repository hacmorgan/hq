#!/usr/bin/env python3


"""
Lightweight application for writing and aggregating TODOs
"""


from pathlib import Path
from datetime import datetime
from shutil import copyfile
from os import environ
from usb import USBError

from hq.cli import getchar, run_typer_app
from hq.shell import sh_run
from hq.hardware.thermal_printer import print_thermally, print_thermally_unpriveliged

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

        # Clear the terminal and print the menu
        sh_run("clear")
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

    # Convert org mode format to printable text and escape escape sequences for
    # unpriveliged print function
    todo_text = (
        todo_path.read_text()
        .replace("\n", r"\n\n")
        .replace("*", "  ")
        .replace("TODO", "[]")
        .replace("DONE", "[x]")
    )

    # Send formatted text to thermal printer
    try:
        print_thermally_unpriveliged(todo_text)
    except USBError as exc:
        raise NotImplementedError(
            "Unable to print to thermal printer without sudo"
        ) from exc


if __name__ == "__main__":
    run_typer_app(todo)
