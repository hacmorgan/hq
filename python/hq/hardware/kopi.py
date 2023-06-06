#!/usr/bin/env python3
# coding: utf-8


"""
Coffee reference and calculation tool

This command almost completely fixes agetty (at least CR-LF), but needs to be run before every command :(
sudo stty -F /dev/ttyUSB0 cs7
"""


import json
import subprocess
import sys
from typing import Any, Dict, List, Optional

import numpy as np
import serial

NROWS = 24
NCOLS = 80
CLEAR_HOME = b"\x1e"
# CTRL_L = b"\x0c"
CTRL_A = b"\x01"
CTRL_B = b"\x02"
CTRL_C = b"\x03"
# CTRL_D = b"\x04"
# CTRL_E = b"\x05"
CTRL_F = b"\x06"
CTRL_G = b"\x07"
CTRL_Q = b"\x11"
CTRL_V = b"\x16"
CTRL_W = b"\x17"
# CTRL_S = b"\x13"

UP_KEY = b"\x05"
DOWN_KEY = b"\x18"
LEFT_KEY = b"\x13"
RIGHT_KEY = b"\x04"

UP_CURSOR = b"\x0b"
DOWN_CURSOR = b"\n"
LEFT_CURSOR = b"\x08"
RIGHT_CURSOR = b"\x0c"

PERMISSIBLE_CHARS = b"`~!@#$%^&*()-_=+[]{}\\|;:'\"<>,./? "

# BEEP = b"\x07"
# BACKSPACE = b"\x08"
DELETE = b"\x7f"
CLEAR = b"\x1a"

BYTESIZE = 7
BAUDRATE = 9600
STOPBITS = 2
WORKING_DIR = "/home/pi"
DB_PATH = "/home/pi/src/hq/etc/kopi.json"
PORT = "/dev/ttyUSB0"

EXPANDED_KEY = {
    b"g": "grind settings",
    b"r": "recipes",
}

PRESS_ANY_KEY = "\r\n\nPress any key to continue"

DB_CTRLS = "ctrl-a: add new field/edit existing, ctrl-f: add new subdict"

SPLASH_SCREEN = """
                      @@@@@@@@@@@@@@@@@@@@
                #@.    @@@@@@@@@@@@@@@@@@@@@@@@#
              @@@@@     @@@@@@@@@@@@@@@@@@@@@@@@@@@/
             @@@@@@@    &@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
            @@@@@@@@@    (@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
           @@@@@@@@@@@     @@@@@@@@@@@@@@@      @@@@@@@@@@@@
           @@@@@@@@@@@@     @@@@@@@@@@@@@  kopi  @@@@@@@@@@@@@
          ,@@          @@     @@@@@@@@@@@@      @@@@@@@@@@@@@@@@
           @  s: shell  @@%     @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
           @@          @@@@@@     @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
           .@@@@@@@@@@@@@@@@@@@      @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
            @@@@@@           @@@@@       @@@@@@@@@ ctrl-q: home @@@@@
             @@@@  p: python  @@@@@@@@      @@@@@@@@@@@@@@@@@@@@@@@@@
              @@@@           @@@@@@@@@@@@       @@@@ (you are here) @@
                @@@@@@@@@@@@@@@@@@@@@@@@@@@@(     (@@@@@@@@@@@@@@@@@@@
                 @@@@@@@@                   @@@      @@@@@@@@@@@@@@@@@*
                   @@@@@  g: grind_settings  @@@@@     @@@@@@@@@@@@@@@
                     @@@@                   @@@@@@@@     @@@@@@@@@@@@@
                        @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@     @@@@@@@@@@
                          @@@@@@@@@@@@@@            @@@@     ,@@@@@@@
                              @@@@@@@@@  r: recipes  @@@@      @@@@@
                                 ,@@@@@@            @@@@@@@     ,*
                                       @@@@@@@@@@@@@@@@@@@@@
"""


class Kopi:
    """
    A lazy interface for a video terminal that refuses to talk to agetty
    """

    def __init__(
        self, serial_connection: serial.Serial, working_dir: str = WORKING_DIR
    ) -> None:
        """
        Create the interface

        Args:
            serial_connection: Open serial connection to video terminal
            working_dir: Initial working dir for shell sessions
        """
        self.ser = serial_connection
        self.working_dir = working_dir
        self.chars: List[str] = []
        self.database = self.load_db()

    @staticmethod
    def open_serial_connection() -> serial.Serial:
        """
        Open a serial connection to the video terminal

        Returns:
            Open serial connection
        """
        return serial.Serial(
            port=PORT, baudrate=BAUDRATE, bytesize=BYTESIZE, stopbits=STOPBITS
        )

    def load_db(self) -> Dict[str, Any]:
        """
        Load database from json file
        """
        with open(DB_PATH, mode="r", encoding="utf-8") as db_fd:
            return json.load(db_fd)

    def save_db(self) -> None:
        """
        Save database to json file
        """
        with open(DB_PATH, mode="w", encoding="utf-8") as db_fd:
            json.dump(self.database, db_fd)

    def main(self) -> None:
        """
        Main menu / mode select
        """
        self.clear()
        self.draw_splash_screen()

        while True:
            mode_char = self.ser.read()

            if mode_char == CTRL_Q:
                self.main()

            elif mode_char in (b"g", b"r"):
                self.clear()
                expanded_key = EXPANDED_KEY[mode_char]
                self.query_db(db=self.database[expanded_key], location=expanded_key)
                self.save_db()

            elif mode_char == b"s":
                self.shell()

            elif mode_char == b"p":
                self.python()

    def draw_splash_screen(self) -> None:
        """
        Draw a splash screen with instructions
        """
        self.clear()
        self.ser.write(insert_cr(SPLASH_SCREEN.encode()))
        # self.ser.write(BEEP)

    def query_db(self, db: Dict[str, Any], location: str = "") -> None:
        """
        Get info from db
        """
        options = list(db.keys())
        chars: List[bytes] = []
        highlighted_option = options[0] if len(options) > 0 else None
        partial_selection = ""
        insert_idx = None
        while True:
            self.print_options(options=options, location=location)
            self.ser.write(b"key: " + partial_selection.encode())
            if insert_idx is not None:
                self.ser.write(LEFT_KEY * abs(insert_idx))
            char = self.ser.read()

            # Enter: pull up info on this entry or enter subdict
            if char == b"\r":
                if highlighted_option is None or highlighted_option not in db:
                    continue
                field = db[highlighted_option]
                if isinstance(field, dict):
                    self.clear()
                    self.query_db(db=field, location=f"{location}.{highlighted_option}")
                else:
                    self.ser.write(b"\r\n\n" + insert_cr(field.encode()))
                    self.ser.write(PRESS_ANY_KEY.encode())
                    self.ser.read()
                    self.query_db(db=db, location=location)

            # Add current key
            elif char == CTRL_A:
                db[highlighted_option] = self.read_field(
                    prompt=f"{location}.{highlighted_option}: ",
                    multiline=True,
                    prior=db[highlighted_option] if highlighted_option in db else None,
                )
                self.save_db()
                self.query_db(db=db, location=location)
                return

            # Add new subdict
            elif char == CTRL_F:
                new_field = self.read_field(prompt=f"New dict: {location}.")
                db[new_field] = {}
                self.save_db()
                self.query_db(db=db[new_field], location=location + f".{new_field}")
                return

            # Back home
            elif char == CTRL_Q:
                self.main()

            elif char == LEFT_KEY:
                if insert_idx is not None:
                    if abs(insert_idx) >= len(chars):
                        continue
                    insert_idx -= 1
                else:
                    insert_idx = -1
            elif char == RIGHT_KEY:
                if insert_idx is not None and insert_idx < -1:
                    insert_idx += 1
                else:
                    insert_idx = None

            elif char == DELETE:
                if len(chars) > 0:
                    chars = chars[:-1]

                partial_selection = b"".join(chars).decode()
                options = [
                    key for key in db.keys() if key.startswith(partial_selection)
                ]
                options += [
                    key
                    for key in db.keys()
                    if (partial_selection in key and key not in options)
                ]
                highlighted_option = (
                    options[0] if len(options) > 0 else partial_selection
                )

            # New character
            else:

                # Only add valid characters
                if not char.isalnum() and char not in PERMISSIBLE_CHARS:
                    print(f"Got unknown char: {char}")
                    continue

                if insert_idx is None:
                    chars.append(char)
                else:
                    chars.insert(insert_idx, char)

                partial_selection = b"".join(chars).decode()
                options = [
                    key for key in db.keys() if key.startswith(partial_selection)
                ]
                options += [
                    key
                    for key in db.keys()
                    if (partial_selection in key and key not in options)
                ]
                highlighted_option = (
                    options[0] if len(options) > 0 else partial_selection
                )

    def print_options(self, options: List[str], location: str = "") -> None:
        """
        Print options in current dict of db
        """
        self.clear()
        self.ser.write(f"Location: {location}\r\n\n".encode())
        self.ser.write((DB_CTRLS + "\r\n\n").encode())
        self.ser.write(
            b"Options: \r\n\n> " + "\r\n- ".join(options).encode() + b"\r\n\n"
        )

    def read_field(
        self, prompt: str, multiline: bool = False, prior: Optional[str] = None
    ) -> str:
        """
        Read a bunch of data for a particular field
        """
        header = b"\n\n" + prompt.encode() + b"\n"
        if multiline:
            header = b"\n\n" + b"ctrl-w to save" + header
        self.ser.write(insert_cr(header))
        chars = []
        if prior is not None:
            chars = [char.encode() for char in prior]
            self.ser.write(insert_cr(b"".join(chars)))
        insert_idx = None
        redraw = False

        while True:

            char = self.ser.read()

            if char == CTRL_C:
                return self.read_field(prompt=prompt)

            elif char == CTRL_Q:
                self.main()

            elif char == DELETE:
                if insert_idx is None:
                    chars = chars[:-1] if len(chars) > 0 else chars
                else:
                    chars = chars[: insert_idx - 1] + chars[insert_idx:]
                redraw = True

            elif (char == b"\r" and not multiline) or (char == CTRL_W and multiline):
                return b"".join(chars).decode()

            elif multiline and char == b"\r":
                chars.append(b"\n")
                self.ser.write(b"\r\n")

            elif char in (LEFT_KEY, LEFT_CURSOR):
                if insert_idx is not None:
                    if abs(insert_idx) >= len(chars):
                        continue
                    insert_idx = insert_idx - 1
                else:
                    insert_idx = -1
                redraw = True
            elif char in (RIGHT_KEY, RIGHT_CURSOR):
                if insert_idx is not None and insert_idx < -1:
                    insert_idx += 1
                else:
                    insert_idx = None
                redraw = True

            else:
                if not char.isalnum() and char not in PERMISSIBLE_CHARS:
                    print(f"Got unknown char: {char}")
                    continue

                if insert_idx is None:
                    chars.append(char)
                    self.ser.write(char)
                else:
                    chars.insert(insert_idx, char)
                    redraw = True

            if redraw:
                redraw = False
                self.clear()
                self.ser.write(insert_cr(header))
                self.ser.write(insert_cr(b"".join(chars)))
                if insert_idx is not None:
                    if multiline:
                        before_point = b"".join(chars[:insert_idx])
                        after_point = b"".join(chars[insert_idx:])
                        lines_before_point = before_point.strip().split(b"\n")
                        lines_after_point = after_point.strip().split(b"\n")
                        self.ser.write(
                            b"\r"
                            + UP_CURSOR * len(lines_after_point)
                            + RIGHT_CURSOR * len(lines_before_point[-1])
                        )
                    else:
                        self.ser.write(
                            LEFT_CURSOR
                            * (abs(insert_idx) if insert_idx is not None else 0)
                        )

    def shell(self) -> None:
        """
        Run very basic shell commands
        """
        self.clear()
        while True:
            self.run_command(command=self.read_field(prompt=self.shell_prompt()))

    def python(self) -> None:
        """
        Run basic python commands
        """
        self.clear()
        while True:
            self.ser.write(b"\r\n" + str(eval(self.read_field(prompt=">>> "))).encode())

    def run_command(self, command: str) -> None:
        """
        Run the command that has been accumulated
        """
        result = subprocess.run(
            b"su pi /bin/bash -c '" + command.encode() + b"; pwd'",
            shell=True,
            capture_output=True,
            cwd=self.working_dir,
        )
        stdout_lines = result.stdout.decode().strip().split("\n")
        self.working_dir = stdout_lines[-1]
        print(f"result: {result}")
        self.ser.write(b"\r\n")
        self.ser.writelines(line.encode() + b"\r\n" for line in stdout_lines[:-1])
        self.ser.write(result.stderr)

    def shell_prompt(self) -> str:
        """
        Generate shell prompt
        """
        return f"\r\n{self.working_dir} :::: "

    def clear(self) -> None:
        """
        Clear screen
        """
        self.ser.write(CLEAR)


def insert_cr(bstr: bytes) -> bytes:
    """
    Insert carriage return character before each newline character
    """
    return bstr.replace(b"\n", b"\r\n")


def main() -> int:
    """
    Main routine

    Returns:
        Exit status
    """
    with Kopi.open_serial_connection() as ser:
        Kopi(serial_connection=ser).main()

    return 0


if __name__ == "__main__":
    sys.exit(main())
