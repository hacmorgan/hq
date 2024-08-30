"""
CLI utilities
"""


import sys
import tty
import termios
from typing import Callable

import typer


def getchar() -> bytes:
    """
    Get a single character from stdin (without waiting for a newline)

    Returns:
        A single character from stdin, including escape codes
    """
    # Read and preserve current TTY settings (because we will be fiddling with them)
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    # Set the TTY to "raw" mode, wherein we don't need to wait for a newline character
    # before yielding a character (i.e. our `read()` call will return as soon as a
    # character is pressed, instead of waiting for the user to press enter)
    tty.setraw(sys.stdin.fileno())
    char = sys.stdin.buffer.read(1)

    # Restore previous TTY settings now that we have our character
    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    return char


def run_typer_app(func: Callable) -> None:
    """
    Run a function as a typer app with nice docstring formatting

    Args:
        func: Function to run as CLI application
    """
    # Insert linebreaks to format the docstring as it appears in code
    if func.__doc__ is not None:
        func.__doc__ = func.__doc__.replace("\n", "\b\n", -1)

    typer.run(func)
