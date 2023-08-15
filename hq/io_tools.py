"""
I/O utilities
"""


import sys
import tty
import termios


def getchar() -> bytes:
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    tty.setraw(sys.stdin.fileno())
    try:
        return bytes(sys.stdin.read(1), encoding="utf-8")
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
