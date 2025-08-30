#!/usr/bin/env python3
# coding: utf-8


"""
Read pressure from flair and provide a timer
"""


import os
import signal
import sys
from math import acos, atan2, cos, degrees, radians, sqrt
from pathlib import Path
from random import shuffle
from serial import Serial
from subprocess import run
from time import sleep, time
from typing import Optional
from threading import Thread

import cv2
import numpy as np
from hq.cli.utils import getchar

CTRL_C = b"\x03"
BACKSPACE = b"\x7f"
CLEAR = b"\x0c"
CURSOR_HOME = "\033"
SPACE = b" "

# Terminal escape codes
TERMINAL_CLEAR = b"\x1bH\x1bJ"


DIAL_Y_MIN = 208
DIAL_Y_MAX = 300
DIAL_X_MIN = 212
DIAL_X_MAX = 404

ZERO_ANGLE = 213.69
NINE_BAR_ANGLE = 40
DEGREES_PER_BAR = 16 / 1.5

EXP_WEIGHT = 0.2
GRAPH_ROWS = 12
GRAPH_COLS = 76  # kopi (terminal)
# GRAPH_COLS = 150  # skoopi
GRAPH_UPDATE_PERIOD = 0.4
GRAPH_REDRAW_PERIOD = GRAPH_UPDATE_PERIOD  # skoopi
GRAPH_REDRAW_PERIOD_TERMINAL = 1.0  # terminal
UPDATES_PER_REFRESH = 50

CAPTURE_DEVICE = 0

# Global variable for the pressure graph (lets us print it one last time)
global pressure_graph
global pressure_str
global terminal_conection
pressure_graph = ""
pressure_str = ""
terminal_connection = None


def signal_handler(sig, frame):
    """
    Final routine run upon ctrl-c

    We print the graph nicely one last time, then exit gracefully
    """

    # Draw the graph one last time to stdout
    draw_graph(
        pressure_graph=pressure_graph,
        pressure_str=pressure_str + "\n",
    )

    # Also draw to terminal and close the serial connection, if we have one
    if terminal_connection is not None:
        draw_graph(
            pressure_graph=pressure_graph,
            pressure_str=pressure_str,
            connection=terminal_connection,
        )
        terminal_connection.close()

    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


def clear() -> None:
    """
    Clear screen
    """
    run("clear", shell=True)


class FlairPressure:
    """
    Flair 58 pressure gauge reader and TUI
    """

    def __init__(self) -> None:
        """
        Construct the Flair pressure reader
        """
        self.load_dial_mask()
        self.needle_cetre = np.array((254 - DIAL_Y_MIN, 316 - DIAL_X_MIN))
        self.log_to_stderr = "LOG_STDERR" in os.environ
        self.debug_mode = "FP_DEBUG" in os.environ
        self.pressure_graph = np.full((GRAPH_ROWS + 2, GRAPH_COLS + 2), fill_value="\0")
        self.pressure_graph[:, 0] = " "
        self.pressure_graph[1:GRAPH_ROWS, 0] = np.arange(GRAPH_ROWS - 2, -1, -1)
        self.pressure_graph[1, 0] = "X"
        self.pressure_graph[:, 1] = "|"
        self.pressure_graph[GRAPH_ROWS, :] = "-"

    def capture_frame(self, vid_in: Optional[cv2.VideoCapture] = None) -> np.ndarray:
        """
        Capture an image from the webcam

        Args:
            vid_in: Existing video capture object. New one created if not given

        Returns:
            Image from webcam as (H, W, 3) array
        """
        # Create video capture device if required
        if vid_in is None:
            vid = cv2.VideoCapture(CAPTURE_DEVICE)
        else:
            vid = vid_in

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
        vid = cv2.VideoCapture(CAPTURE_DEVICE)
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
        gray = img[..., 2]  # red channel should minimise red writing visibility

        # Crop image down to just the dial
        cropped = gray[DIAL_Y_MIN:DIAL_Y_MAX, DIAL_X_MIN:DIAL_X_MAX, ...]

        # Do histogram equalisation to make needle darkness consistent
        equ = cv2.equalizeHist(cropped)

        # Blur image to optimise thresholding performance
        blur = cv2.GaussianBlur(src=equ, ksize=(5, 5), sigmaX=0)

        # Binarise by thresholding
        _, binary = cv2.threshold(
            src=blur, thresh=80, maxval=255, type=cv2.THRESH_BINARY
        )

        # Mask out everything but the dial
        binary[self.dial_mask == 0] = 255

        # Dilate to remove noise
        dilated = cv2.dilate(binary, kernel=np.ones((5, 5)), iterations=1)

        # Find centre of needle tail
        centroid = np.mean(np.argwhere(255 - dilated), axis=0).astype(int)
        centroid = tuple(reversed(centroid))  # Switch to X, Y instead of Y, X

        # Get angle of needle relative to centre spindle in camera plane
        direction_vector = centroid - self.needle_cetre
        angle = degrees(atan2(*direction_vector))
        if angle < 0:
            angle = 360 + angle

        # Transform camera-plane angle to dial-plane
        angle = self.convert_angle(alpha=angle)

        # Apply a transformation function to produce a pressure value
        pressure = max(0, (ZERO_ANGLE - angle) / DEGREES_PER_BAR)

        if self.debug_mode:
            cv2.imwrite(filename="/tmp/gray.png", img=gray)
            cv2.imwrite(filename="/tmp/contrast.png", img=gray)
            cv2.imwrite(filename="/tmp/blur.png", img=blur)
            cv2.imwrite(filename="/tmp/equ.png", img=equ)
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
            breakpoint()

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
        self.pressure_graph[GRAPH_ROWS - 1 - round(new_pressure), 2] = "*"

        # Shift old timestamps
        self.pressure_graph[-1, 3:] = self.pressure_graph[-1, 2:-1]
        self.pressure_graph[-1, 3] = " "
        if new_time is not None:
            self.pressure_graph[-1, 3:6] = list(f"{new_time:3.0f}")

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

    def cli_main(self, terminal_connection: Serial) -> None:
        """
        Main CLI tool routine
        """
        # Open video capture object
        vid = cv2.VideoCapture(CAPTURE_DEVICE)

        # Clear screen
        clear()
        terminal_connection.write(TERMINAL_CLEAR)

        # Initialise loop variables
        start = time()
        i = 0
        pressures = []
        last_capture_time = -1.0
        last_redraw_time = -1.0
        last_terminal_redraw_time = -1.0
        num_updates = 0
        pressure = 0

        #
        global pressure_graph
        global pressure_str

        # Main application loop
        while True:

            # Capture image
            img = self.capture_frame(vid_in=vid)
            capture_time = time() - start

            # Compute pressure from angle of needle, apply exponential weighted moving average
            pressure = (
                EXP_WEIGHT * self.detect_needle_position(img=img)
                + (1 - EXP_WEIGHT) * pressure
            )
            if pressure is not None:
                pressures.append(pressure)

            # Construct string for printing to terminal and stdout
            pressure_str = (
                f"\r\tTime: {capture_time:.2f}\tPressure: {pressure:.2f} bar"
                if pressure is not None
                else "N/A"
            )

            # Update graph periodically
            if capture_time > last_capture_time + GRAPH_UPDATE_PERIOD:
                avg_pressure = np.mean(pressures) if pressures else 0
                if num_updates >= UPDATES_PER_REFRESH:
                    num_updates = 0
                    graph_time = capture_time
                else:
                    graph_time = None
                pressure_graph = self.update_pressures(
                    new_pressure=avg_pressure,
                    new_time=graph_time,
                )
                pressures = []
                last_capture_time = capture_time

                # Print to stdout again if enough time has elapsed
                if capture_time > last_redraw_time + GRAPH_REDRAW_PERIOD:
                    Thread(
                        target=draw_graph, kwargs={"pressure_graph": pressure_graph}
                    ).start()
                    last_redraw_time = capture_time

                # Print to the terminal again if enough time has elapsed
                if (
                    capture_time
                    > last_terminal_redraw_time + GRAPH_REDRAW_PERIOD_TERMINAL
                ):
                    Thread(
                        target=draw_graph,
                        kwargs={
                            "pressure_graph": pressure_graph,
                            "connection": terminal_connection,
                            "pressure_str": pressure_str,
                        },
                    ).start()
                    last_terminal_redraw_time = capture_time

            # Print fast-refresh pressure and time status line
            sys.stdout.write(pressure_str)
            if self.log_to_stderr:
                sys.stderr.write(f"{pressure}\n")

            # Update loop variables
            i += 1
            num_updates += 1

        vid.release()

    def load_dial_mask(self) -> None:
        """
        Load segmentation mask of relevant portion of flair dial
        """
        mask_path = os.path.expanduser("~/hq/etc/flair_pressure/dial_mask.png")
        mask = cv2.imread(mask_path)[DIAL_Y_MIN:DIAL_Y_MAX, DIAL_X_MIN:DIAL_X_MAX, ...]
        if mask is None:
            raise ValueError(f"Could not load mask at {mask_path}")

        # Mask is saved as RGB, just take first channel
        self.dial_mask = mask[..., 0]

    @staticmethod
    def convert_angle(alpha: float) -> float:
        """
        Convert a needle angle inferred from the camera to the true needle angle as
        viewed normal to the dial plane

        n.b. this assumes the camera is at a 30 degree angle to the dial plane

        Calculations at: https://photos.app.goo.gl/eC6Km3izzb3DakwEA

        Args:
            alpha: Angle of needle (degrees) as viewed from camera plane

        Returns:
            Angle of needle as viewed normal to the dial plane
        """
        ca = cos(radians(alpha))
        c2a = ca**2
        angle = degrees(acos(sqrt(c2a / (4 - 3 * c2a))))
        quadrant = int(alpha / 90)
        if quadrant == 0:
            return angle
        if quadrant == 1:
            return 180 - angle
        if quadrant == 2:
            return 180 + angle
        return 360 - angle


def draw_graph(
    pressure_graph: str,
    connection: Serial | None = None,
    pressure_str: str | None = None,
) -> None:
    """
    Draw graph to screen or terminal
    """
    # Print to terminal if given
    if connection:
        connection.write(TERMINAL_CLEAR)
        connection.write(
            b"\r\n" * 4
            + bytes(pressure_graph, encoding="utf-8").replace(b"\n", b"\n\r")
            + b"\r\n" * 2
        )
        connection.write(bytes(pressure_str, encoding="utf-8") + b"\n\r\n\n")
        return

    # Otherwise print to screen
    clear()
    sys.stdout.write("\n" * 2 + pressure_graph + "\n" * 2)
    if pressure_str is not None:
        sys.stdout.write(pressure_str)


if __name__ == "__main__":
    pressure_monitor = FlairPressure()

    # pressure_monitor.collect_data(output_directory="/tmp/flair_pressure_logs_2", interval=0.01)

    # pressure_monitor.detect_needle_position(
    #     img=pressure_monitor.capture_frame(),
    # )

    global terminal_conection
    with Serial("/dev/ttyUSB0", baudrate=19200) as conn:
        terminal_connection = conn

        # Run the pressure graph main application loop
        pressure_monitor.cli_main(terminal_connection=conn)

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
