#!/usr/bin/env python3


"""
Lightweight application for writing and aggregating TODOs

- Maybe just use org mode's TODO capabilities
    - Make org -> printable format converter

    - Example raw org
        * TODO get char
        ** TODO put char back
        * TODO sfsaaslidfhasdf somthing reall longkasjfd skhfkjs
        ** TODO     

    - logic: replace * with \t, replace TODO with a circle   

    - Use emacs by default, fall back on $EDITOR

- just need main menu
    - (n) new todo
    - (c) copy from previous
    - (p) print
"""


from pathlib import Path
from datetime import datetime
from shutil import copyfile

from hq.cli import getchar, run_typer_app
from hq.shell import sh_run
from hq.hardware.thermal_printer import print_thermally


# Parent directory under which TODOs are saved
ROOT_TODO_DIR = Path("~/hq/etc/todo").expanduser()

# File format of TODO files
TODO_SUFFIX = ".org"

# Command to run an editor
TODO_EDITOR = "emacs -nw"

# Main menu text
TODO_MENU = """

    todo

    (n) new todo
    (c) copy from previous
    (p) print

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
    if "/" in name:
        todo_dir = ROOT_TODO_DIR
        todo_path = (ROOT_TODO_DIR / name).with_suffix(TODO_SUFFIX)
    else:
        now = datetime.now()
        todo_dir = ROOT_TODO_DIR / f"{now.year}/{now.month}"
        todo_path = (
            todo_dir / (name if name is not None else str(now.day))
        ).with_suffix(TODO_SUFFIX)

    # We need to be able to return to the menu after editing, so we read keys from stdin
    # on repeat
    while True:

        # Clear the terminal and print the menu
        sh_run("clear")
        print(TODO_MENU)

        match (char := getchar()):

            # (n): New TODO
            case "n":
                edit_todo(todo_path=todo_path)

            # (c): Copy from previous TODO
            case "c":
                if (previous := find_previous()) is not None:
                    copyfile(src=previous, dst=todo_path)
                edit_todo(todo_path=todo_path)

            # (p): Print TODO (to thermal printer)
            case "p":
                print_todo(todo_path=todo_path)

            # (q): Quit
            case "q":
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
        return next(sorted(ROOT_TODO_DIR.rglob("**/*")))
    except StopIteration:
        return None


def print_todo(todo_path: Path) -> None:
    """
    Print a TODO on a thermal printer

    Args:
        todo_path: Path to load TODO from for printing
    """
    # Convert org mode format to printable text
    todo_text = todo_path.read_text().replace("*", "\t").replace("TODO", "○")

    # Send formatted text to thermal printer
    print_thermally(todo_text)


if __name__ == "__main__":
    run_typer_app(todo)
