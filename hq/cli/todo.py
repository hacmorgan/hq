#!/usr/bin/env python3


"""
Formatting and thermal printing of TODOs

The `todo` application (a bash script) handles creating, resuming and editing TODOs;
this module holds the org -> thermal printer formatting it delegates to.
"""


from os import environ
from pathlib import Path

from hq.cli import run_typer_app
from hq.hardware.thermal_printer import MAX_LINE_WIDTH, print_thermally_unpriveliged

# Parent directory under which TODOs are saved, kept in step with the `todo` script
_user = environ.get("SUDO_USER", environ["USER"])
ROOT_TODO_DIR = Path(
    environ.get("HQ_TODO_ROOT", f"/home/{_user}/.hq-secret/etc/todo")
).expanduser()

# File format of TODO files
TODO_SUFFIX = ".org"


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
                entry_idx += ".0"
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
    run_typer_app(print_todo)
