#!/usr/bin/env python3


"""
Record or execute keyboard macros

Recording keystrokes (until hitting `esc`):

    sudo examples/autokbd.py record > etc/keyboard-automation/harvest.cloudpickle

Replaying keystrokes:

    sudo examples/autokbd.py < etc/keyboard-automation/harvest.cloudpickle
"""


import keyboard
import cloudpickle
from time import sleep
import sys


if len(sys.argv) > 1 and sys.argv[1] in "record":
    recorded = keyboard.record(until="space")
    cloudpickle.dump(recorded, sys.stdout.buffer)
else:
    recorded = cloudpickle.load(sys.stdin.buffer)
    sleep(2.0)
    keyboard.play(recorded, speed_factor=5)
