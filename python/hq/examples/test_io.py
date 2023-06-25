#!/usr/bin/env python3


import sys
import tty
import termios


from hq.io_tools import getchar


while True:
    char = getchar()
    # char = sys.stdin.read(1)
    print(char)
    if char in (b"\r", b"\n"):
        break
