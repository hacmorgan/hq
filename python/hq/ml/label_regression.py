#!/usr/bin/env python3


"""
Label training data for a regression model
"""


import sys
from pathlib import Path

from hq.io_tools import getchar


def main() -> int:
    """
    
    """
    if len(sys.argv) < 2:
        raise ValueError("Please give input dir as 1st positional arg")

    pressure = 0
    dp = 0.5

    output_path = Path("labels.csv")
    if output_path.exists():
        raise ValueError("labels file exists")

    with open(output_path, mode="r", encoding="utf-8") as labels_fp:
    
        input_dir = Path(sys.argv[1])
        for img_path in input_dir.iterdir():
            cv2.imshow("img", cv2.imread(img_path))

            while True:
                char = getchar()
                if char == b"j":
                    pressure = max(0, pressure - dp)
                elif char == b"k":
                    pressure = min(10, pressure + dp)
                elif char in (b"\n", b"\r"):
                    labels_fp.write(f"{img_path},{pressure}\n")
                    continue
                


if __name__ == "__main__":
    sys.exit(main())
