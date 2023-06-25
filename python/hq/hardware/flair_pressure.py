#!/usr/bin/env python3
# coding: utf-8


"""
Read pressure from flair and provide a timer
"""


import os
import sys
from math import atan2, degrees
from subprocess import run
from time import sleep, time
from typing import Optional
from pathlib import Path

import cv2
import numpy as np
from hq.io_tools import getchar

CTRL_C = b"\x03"
BACKSPACE = b"\x7f"
CLEAR = b"\x0c"
SPACE = b" "


def clear() -> None:
    run("clear", shell=True)


class FlairPressure:
    def __init__(self) -> None:
        """
        Construct the Flair pressure reader
        """
        self.load_dial_mask()
        self.needle_cetre = np.array((267, 312))

    def capture_frame(self, vid_in: Optional[cv2.VideoCapture] = None) -> np.ndarray:
        """
        Capture an image from the webcam

        Args:
            vid_in: Existing video capture object. New one crated if not given
        Returns:
            Image from webcam as (H, W, 3) array
        """
        # Create video capture device if required
        if vid_in is None:
            vid = cv2.VideoCapture(0)
        else:
            vid = vid_in

        # # Set capture parameters
        # cap.set(cv2.cv.CV_CAP_PROP_EXPOSURE, 0.1)

        # Capture the frame
        _, frame = vid.read()

        # Destroy the video capture device if required
        if vid_in is None:
            vid.release()

        return frame

    def collect_data(
        self, output_directory: str, interval: Optional[float] = 0.5
    ) -> None:
        """
        Save a bunch of images to disk

        Args:
            output_directory: Directory to write images under
            interval: How often to capture images
        """
        vid = cv2.VideoCapture(0)
        i = 0
        while True:
            i = i + 1
            output_path = os.path.join(output_directory, f"{i}.jpg")
            cv2.imwrite(
                filename=output_path,
                img=self.capture_frame(vid_in=vid),
            )
            print(f"Wrote {output_path}")

            if interval is None:
                input()
            else:
                sleep(interval)
        vid.release()

    def detect_needle_position(self, img: np.ndarray) -> float:
        """
        Compute pressure from images of gauge

        Returns:
            Current pressure (bar)
        """
        # Convert image to grayscale
        gray = cv2.cvtColor(src=img, code=cv2.COLOR_BGR2GRAY)
        cv2.imwrite(filename="/tmp/gray.png", img=gray)

        # Blur image to optimise thresholding performance
        blur = cv2.GaussianBlur(src=gray, ksize=(5, 5), sigmaX=0)

        # Increase contrast
        alpha = 1.2
        beta = -20
        blur = np.clip(blur * alpha + beta, 0, 255).astype(np.uint8)
        cv2.imwrite(filename="/tmp/contrast_blur.png", img=blur)

        # Binarise by thresholding
        # _, binary = cv2.threshold(src=blur, thresh=0, maxval=255, type=cv2.THRESH_OTSU)
        # _, binary = cv2.threshold(src=blur, thresh=100, maxval=255, type=cv2.THRESH_BINARY)
        binary = cv2.adaptiveThreshold(
            # blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 7
            blur, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 25, 9
        )
        cv2.imwrite(filename="/tmp/binary.png", img=binary)

        # Mask out everything but the dial
        binary[self.dial_mask == 0] = 255
        cv2.imwrite(filename="/tmp/masked.png", img=binary)

        # Dilate to remove other end of needle
        dilated = cv2.dilate(binary, kernel=(17, 17))
        cv2.imwrite(filename="/tmp/dilated.png", img=dilated)

        # Find centre of needle tail
        centroid = np.mean(np.argwhere(255 - dilated), axis=0).astype(int)
        centroid = tuple(reversed(centroid))  # Switch to X, Y instead of Y, X
        cv2.imwrite(
            filename="/tmp/centroid.png",
            img=cv2.line(dilated, centroid, centroid, (255, 0, 0), 2),
        )

        # Get angle of needle from centre spindle
        direction_vector = centroid - self.needle_cetre
        angle = 180 + degrees(atan2(*direction_vector))

        # TODO Apply some calibration function to produce a pressure value
        pressure = angle

        return pressure

    def detect_needle_position_learned(self) -> float:
        """
        Compute pressure from images of gauge using a neural net

        Returns:
            Current pressure (bar)
        """
        raise NotImplementedError("Learned gauge reading has not been implemented yet")

    def cli_main(self) -> None:
        """
        Main CLI tool routine
        """
        vid = cv2.VideoCapture(0)
        log_directory = "/tmp/flair_pressure_logs"
        os.makedirs(log_directory, exist_ok=True)

        clear()
        start = time()

        with open(
            os.path.join(log_directory, "pressures.log"), mode="w", encoding="utf-8"
        ) as log_fp:
            i = 0
            while True:
                i = i + 1

                output_path = os.path.join(log_directory, f"{i}.jpg")

                # Capture and save image
                img = self.capture_frame(vid_in=vid)
                cv2.imwrite(filename=output_path, img=img)

                # Compute angle of needle
                angle = self.detect_needle_position(img=img)
                sys.stdout.write(f"\rTime: {time() - start:.2f}, angle {angle:.2f}")
                log_fp.write(f"{angle}\n")

        vid.release()

    def load_dial_mask(self) -> None:
        mask_path = os.path.expanduser("~/src/hq/etc/flair_pressure/dial_mask.png")
        mask = cv2.imread(mask_path)
        if mask is None:
            raise ValueError(f"Could not load mask at {mask_path}")
        self.dial_mask = mask[..., 0]


if __name__ == "__main__":
    pressure_monitor = FlairPressure()

    pressure_monitor.collect_data(output_directory="/tmp/flair_pressure_logs_2", interval=0.01)

    # pressure_monitor.detect_needle_position(
    #     img=pressure_monitor.capture_frame(),
    # )

    # pressure_monitor.cli_main()

    # for path in sorted(Path("/tmp/flair_pressure_logs/").iterdir()):
    #     img = cv2.imread(str(path))
    #     pressure_monitor.detect_needle_position(img=img)
    #     input()

    sys.exit(0)
