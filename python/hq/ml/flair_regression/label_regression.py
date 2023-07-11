#!/usr/bin/env python3


"""
Label training data for a regression model
"""


import sys
from pathlib import Path

import cv2
import datetime

from subprocess import run

from hq.io_tools import getchar
from hq.hardware.kopi import CTRL_C


def main() -> int:
    """
    Label images with a numeric value

    Used to label regression model training data
    """
    if len(sys.argv) < 2:
        raise ValueError("Please give input dir as 1st positional arg")

    pressure = 0
    dp = 0.5

    output_path = Path("labels.csv")

    with open(output_path, mode="a", encoding="utf-8") as labels_fp:
        labels_fp.write(f"{datetime.datetime.utcnow()}\n")
        input_dir = Path(sys.argv[1])
        for img_path in sorted(input_dir.iterdir(), key=lambda path: int(path.stem)):
            print(img_path)
            run(f"feh -d. {img_path}", shell=True)

            while True:
                print(f"pressure: {pressure}")
                char = getchar()
                if char == b"j":
                    pressure = max(0, pressure - dp)
                elif char == b"k":
                    pressure = min(10, pressure + dp)
                elif char == CTRL_C:
                    return 1
                elif char in (b"\n", b"\r"):
                    labels_fp.write(f"{img_path},{pressure}\n")
                    break


if __name__ == "__main__":
    sys.exit(main())
