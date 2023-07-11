#!/usr/bin/env python3


"""
Segmentation network for auto-generating waals for wwd
"""

import sys

import numpy as np
import PIL.Image
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch import optim
from torch.optim.lr_scheduler import StepLR
from torch.utils.data import DataLoader
from torchvision import datasets, transforms


def main() -> int:
    """ """


class CsvDataset(torch.utils.data.IterableDataset):
    """
    Load train/test data
    """

    def __init__(self, rgb_path: str, labels_path: str) -> None:
        """
        Construct the datatset object

        Args:
            rgb_path: Path to input rgb image
            labels_path: Path to ground truth labels mask
        """
        super().__init__()
        self.rgb = np.array(PIL.Image.open(rgb_path))
        self.labels = np.array(PIL.Image.open(labels_path))
        self.tile_size = 64
        self.num_rows = self.rgb.shape[0]
        self.num_cols = self.rgb.shape[1]

    def __iter__(self):
        """
        Yield training examples
        """
        for row in range(0, self.num_rows, self.tile_size):
            for col in range(0, self.num_cols, self.tile_size):
                rgb_tile = self.rgb[
                    row : row + self.tile_size,
                    col : col + self.tile_size,
                    :,
                ]
                labels_tile = self.rgb[
                    row : row + self.tile_size,
                    col : col + self.tile_size,
                    :,
                ]
                training_example = (rgb_tile, labels_tile)
                yield training_example

    def __len__(self) -> int:
        return int(self.num_rows / self.tile_size * self.num_cols / self.tile_size)


if __name__ == "__main__":
    sys.exit(main())
