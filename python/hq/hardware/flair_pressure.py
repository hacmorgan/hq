#!/usr/bin/env python3
# coding: utf-8


"""
Read pressure from flair and provide a timer
"""


import os
import sys
from math import atan2, degrees
from subprocess import run
from random import shuffle
from time import sleep, time
from typing import Optional
from pathlib import Path

import cv2
import numpy as np
from hq.io_tools import getchar

CTRL_C = b"\x03"
BACKSPACE = b"\x7f"
CLEAR = b"\x0c"
CURSOR_HOME = "\033[H"
SPACE = b" "

DIAL_Y_MIN = 214
DIAL_Y_MAX = 307
DIAL_X_MIN = 209
DIAL_X_MAX = 403

ZERO_ANGLE = 189
NINE_BAR_ANGLE = 40
DEGREES_PER_BAR = 8

GRAPH_ROWS = 20
GRAPH_COLS = 60


def clear() -> None:
    run("clear", shell=True)


class FlairPressure:
    def __init__(self) -> None:
        """
        Construct the Flair pressure reader
        """
        self.load_dial_mask()
        self.needle_cetre = np.array((267 - DIAL_Y_MIN, 312 - DIAL_X_MIN))
        self.pressure_graph = np.full((GRAPH_ROWS + 2, GRAPH_COLS + 2), fill_value="\0")
        self.pressure_graph[:, 0] = " "
        self.pressure_graph[1:GRAPH_ROWS:2, 0] = np.arange(9, -1, -1)
        self.pressure_graph[:, 1] = "|"
        self.pressure_graph[GRAPH_ROWS, :] = "-"

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

    def detect_needle_position(self, img: np.ndarray) -> Optional[float]:
        """
        Compute pressure from images of gauge

        Returns:
            Current pressure (bar)
        """
        if img is None:
            return None

        # Convert image to grayscale
        # gray = cv2.cvtColor(src=img, code=cv2.COLOR_BGR2GRAY)
        gray = img[..., 2]  # red channel should minimise red writing visibility

        cropped = gray[DIAL_Y_MIN:DIAL_Y_MAX, DIAL_X_MIN:DIAL_X_MAX, ...]

        # # Decrease contrast
        # alpha = 0.5
        # beta = 0
        # gray = np.clip(gray * alpha + beta, 0, 255).astype(np.uint8)

        equ = cv2.equalizeHist(cropped)

        # Blur image to optimise thresholding performance
        # blur = cv2.GaussianBlur(src=gray, ksize=(13, 13), sigmaX=0)
        blur = cv2.GaussianBlur(src=equ, ksize=(5, 5), sigmaX=0)

        # canny = cv2.Canny(image=equ, threshold1=30, threshold2=100)
        # canny[self.dial_mask < 255] = 0

        # lines = cv2.HoughLines(
        #     canny,  # image
        #     1,  # rho
        #     np.pi / 360,  # theta
        #     5,  # threshold
        #     None,  # srn
        #     0,  # stn
        #     0,  # min_theta
        # )

        # if lines is not None:
        #     return np.mean([line[0][1] for line in lines])
        # return None

        cv2.imwrite(filename="/tmp/gray.png", img=gray)
        cv2.imwrite(filename="/tmp/contrast.png", img=gray)
        cv2.imwrite(filename="/tmp/blur.png", img=blur)
        cv2.imwrite(filename="/tmp/equ.png", img=equ)
        # cv2.imwrite(filename="/tmp/canny.png", img=canny)

        # # Find centre of needle tail
        # aw = np.argwhere(canny)
        # if aw.size == 0:
        #     return None
        # centroid = np.mean(aw, axis=0).astype(int)
        # centroid = tuple(reversed(centroid))  # Switch to X, Y instead of Y, X

        # # clahe = cv2.createCLAHE(clipLimit=5)
        # # equalised = clahe.apply(blur)

        # Binarise by thresholding
        # _, binary = cv2.threshold(src=blur, thresh=0, maxval=255, type=cv2.THRESH_OTSU)
        _, binary = cv2.threshold(
            src=blur, thresh=80, maxval=255, type=cv2.THRESH_BINARY
        )
        # binary = cv2.adaptiveThreshold(
        #     # blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 7
        #     equ, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 25, 11
        # )

        # Mask out everything but the dial
        binary[self.dial_mask == 0] = 255

        # Erode then dilate to remove noise
        dilated = cv2.dilate(binary, kernel=np.ones((5, 5)), iterations=1)

        # Find centre of needle tail
        centroid = np.mean(np.argwhere(255 - dilated), axis=0).astype(int)
        centroid = tuple(reversed(centroid))  # Switch to X, Y instead of Y, X

        # Get angle of needle from centre spindle
        direction_vector = centroid - self.needle_cetre
        angle = degrees(atan2(*direction_vector))
        if angle < 0:
            angle = 360 + angle

        # Apply some calibration function to produce a pressure value
        pressure = max(0, (ZERO_ANGLE - angle) / NINE_BAR_ANGLE * DEGREES_PER_BAR)

        cv2.imwrite(
            filename="/tmp/centroid.png",
            img=cv2.line(dilated, centroid, centroid, (255, 0, 0), 2),
        )
        cv2.imwrite(filename="/tmp/binary_masked.png", img=binary)
        cv2.imwrite(filename="/tmp/dilated.png", img=dilated)
        cv2.imwrite(
            filename="/tmp/centroid.png",
            img=cv2.line(dilated, centroid, centroid, (255, 0, 0), 2),
        )

        return pressure

    def update_pressures(
        self, new_pressure: float, new_time: Optional[float] = None
    ) -> str:
        """
        Update and return the ascii plot of pressures
        """
        # Shift existing graph
        self.pressure_graph[:GRAPH_ROWS, 3:] = self.pressure_graph[:GRAPH_ROWS, 2:-1]

        # Write latest timestep
        self.pressure_graph[:GRAPH_ROWS, 2] = " "
        self.pressure_graph[GRAPH_ROWS - 1 - int(new_pressure * 2), 2] = "*"

        # Shift old timestamps
        self.pressure_graph[-1, 3:] = self.pressure_graph[-1, 2:-1]
        self.pressure_graph[-1, 3] = " "
        if new_time is not None:
            self.pressure_graph[-1, 3:5] = list(f"{new_time:2.0f}")

        # Construct string representation
        return "\n".join(
            "  " + "".join(line[line != "\0"]) for line in self.pressure_graph
        )

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
            pressures = []
            last_capture_time_int = -1
            while True:
                output_path = os.path.join(log_directory, f"{i}.jpg")

                # Capture and save image
                img = self.capture_frame(vid_in=vid)
                capture_time = time() - start
                # cv2.imwrite(filename=output_path, img=img)

                # Compute angle of needle
                pressure = self.detect_needle_position(img=img)
                if pressure is not None:
                    pressures.append(pressure)

                capture_time_int = int(capture_time)
                if capture_time_int != last_capture_time_int:
                    avg_pressure = np.mean(pressures) if pressures else 0
                    pressure_graph = self.update_pressures(
                        new_pressure=avg_pressure,
                        new_time=capture_time if capture_time_int % 5 == 0 else None,
                    )
                    sys.stdout.write(CURSOR_HOME + "\n" * 2 + pressure_graph + "\n" * 2)
                    pressures = []
                    last_capture_time_int = capture_time_int

                pressure_str = f"{pressure:.2f}" if pressure is not None else "N/A"
                sys.stdout.write(
                    f"\r  Time: {capture_time:.2f}, Pressure: {pressure_str} bar"
                )
                log_fp.write(f"{pressure}\n")

                i += 1

        vid.release()

    def load_dial_mask(self) -> None:
        # mask_path = os.path.expanduser("~/src/hq/etc/flair_pressure/dial_mask.png")
        mask_path = os.path.expanduser(
            "~/src/hq/etc/flair_pressure/dial_mask_cropped.png"
        )
        mask = cv2.imread(mask_path)
        if mask is None:
            raise ValueError(f"Could not load mask at {mask_path}")
        self.dial_mask = mask[..., 0]


if __name__ == "__main__":
    pressure_monitor = FlairPressure()

    # pressure_monitor.collect_data(output_directory="/tmp/flair_pressure_logs_2", interval=0.01)

    # pressure_monitor.detect_needle_position(
    #     img=pressure_monitor.capture_frame(),
    # )

    pressure_monitor.cli_main()

    # paths = list(Path("/home/pi/src/hq/etc/flair_pressure/datasets/regression").iterdir())
    # # shuffle(paths)
    # # for path in paths:
    # for i in range(106, 400):
    #     # print(path)
    #     print(i)
    #     # img = cv2.imread(str(path))
    #     img = cv2.imread(f"/home/pi/src/hq/etc/flair_pressure/datasets/regression/{i}.jpg")
    #     print(pressure_monitor.detect_needle_position(img=img))
    #     input()

    sys.exit(0)
