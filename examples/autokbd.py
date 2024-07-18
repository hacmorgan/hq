#!/usr/bin/env python3


"""
Automatically fill out harvest logs

Recording keystrokes:

    sudo examples/autoharvest.py record > etc/auto-harvest/default.cloudpickle

Replaying keystrokes:

    sudo examples/autoharvest.py < etc/auto-harvest/default.cloudpickle
"""


import keyboard
import cloudpickle
from time import sleep
import sys


if len(sys.argv) > 1 and sys.argv[1] in "record":
    recorded = keyboard.record(until="esc")
    cloudpickle.dump(recorded, sys.stdout.buffer)
else:
    recorded = cloudpickle.load(sys.stdin.buffer)
    sleep(2.0)
    keyboard.play(recorded, speed_factor=5)
