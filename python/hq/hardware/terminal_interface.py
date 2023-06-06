#!/usr/bin/env python3
# coding: utf-8
import serial
import subprocess
import sys


"""
Alternative to actually getting a tty on terminal...

THis command almost completely fixes agetty...
sudo stty -F /dev/ttyUSB0 cs7
"""


NROWS = 24
NCOLS = 80
CLEAR_HOME = b"\x1e"
CTRL_L = b"\x0c"
CTRL_C = b"\x03"
BYTESIZE = 7
STOPBITS = 2
WORKING_DIR = "/home/kopi"
PORT = "/dev/ttyUSB0"


class TerminalInterface:
    """
    A lazy interface for a video terminal that refuses to talk to agetty
    """

    def __init__(
        self, serial_connection: serial.Serial, working_dir: str = WORKING_DIR
    ) -> None:
        """
        Create the interface
        """
        self.ser = serial_connection
        self.working_dir = working_dir
        self.chars = []

    @classmethod
    def open(cls, port: str = PORT) -> None:
        with serial.Serial(port=port, bytesize=BYTESIZE, stopbits=STOPBITS) as ser:
            return cls(serial_connection=ser).run()

    def run(self) -> None:
        self.reset()
        while True:
            char = self.ser.read()

            if char in (CLEAR_HOME, CTRL_L):
                self.clear()

            elif char == CTRL_C:
                self.reset()

            elif char == b"\r":
                self.run_command()

            else:
                self.chars.append(char)
                self.ser.write(char)

    def run_command(self) -> None:
        self.ser.write(b"\r\n")
        result = subprocess.run(
            b"su kopi /bin/bash -c '" + b"".join(self.chars) + b"; pwd'",
            shell=True,
            capture_output=True,
            cwd=self.working_dir,
        )
        stdout_lines = result.stdout.decode().strip().split("\n")
        self.working_dir = stdout_lines[-1]
        print(f"result: {result}")
        self.ser.write("\n\r".join(stdout_lines[:-1]).encode())
        self.ser.write(result.stderr)
        self.reset()
        

    def reset(self) -> None:
        self.chars = []
        self.draw_prompt()

    def draw_prompt(self) -> None:
        self.ser.write(b"\r\n" + f"{self.working_dir} :::: ".encode())

    def clear(self) -> None:
        self.ser.write(b" " * NROWS * NCOLS + CLEAR_HOME)
        self.reset()


def main() -> int:
    with serial.Serial(port=PORT, bytesize=BYTESIZE, stopbits=STOPBITS) as ser:
        TerminalInterface(serial_connection=ser).run()

    return 0


if __name__ == "__main__":
    sys.exit(main())
