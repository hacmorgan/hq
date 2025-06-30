#!/usr/bin/env python3


"""
Record or execute keyboard macros

Recording keystrokes (until hitting `space`):

    sudo examples/autokbd.py record > etc/keyboard-automation/harvest.cloudpickle

Replaying keystrokes:

    sudo examples/autokbd.py < etc/keyboard-automation/harvest.cloudpickle
"""


import keyboard
import cloudpickle
from time import sleep
import sys


# Record mode: read keystrokes until spacebar is pressed, and dump cloudpickled macro to
# stdout
if len(sys.argv) > 1 and sys.argv[1] in "record":
    recorded = keyboard.record(until="space")
    cloudpickle.dump(recorded, sys.stdout.buffer)

# Playback mode: load cloudpickled macro from stdin and playback keystrokes at 4x speed
else:
    recorded = cloudpickle.load(sys.stdin.buffer)
    sleep(2.0)  # Give a moment to position cursor on the relevant window
    keyboard.play(recorded, speed_factor=4)
