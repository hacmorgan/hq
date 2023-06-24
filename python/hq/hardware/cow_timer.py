#!/usr/bin/env python3
# coding: utf-8


"""
Cow-based timer
"""


from time import time, sleep
import subprocess
from functools import partial
import sys


sh_run = partial(subprocess.run, shell=True)


line1, msg_line, *cow_lines = sh_run("cowsay {duration}s", capture_output=True).stdout.decode().split()


def cow_timer() -> None:
    """
    Start a timer, spoken by a cow
    """
    start = time()
    sh_run("clear")
    while True:
        duration = time() - start
        # print_cow(duration=duration)
        sh_run(f"cowsay {duration:.3f}s")
        sleep(1/30)
        sh_run("clear")


def print_cow(duration: float) -> None:
    print(line1)
    print(msg_line.format(duration=duration))
    print("\n".join(cow_lines))


if __name__ =="__main__":
    sys.exit(cow_timer())

