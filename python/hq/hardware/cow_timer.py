#!/usr/bin/env python3
# coding: utf-8


"""
Cow-based timer
"""


from time import time, sleep
import subprocess
import sys


def cow_timer() -> None:
    """
    Start a timer, spoken by a cow
    """
    start = time()
    while True:
        duration = time() - start
        subprocess.run(f"clear; cowsay {duration:.2f}s", shell=True)
        sleep(1/30)


if __name__ =="__main__":
    sys.exit(cow_timer())

