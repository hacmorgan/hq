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


class SegmentationNet(torch.nn.Module):
    """
    Basic regression network
    """

    def __init__(self):
        super().__init__()

        self.conv_depth = 16

        # Input shape: (64, 64, 3)

        # -> (32, 32, conv_depth)
        self.conv1 = nn.Conv2d(
            in_channels=3,
            out_channels=self.conv_depth,
            kernel_size=5,
            stride=2,
            padding="same",
        )
        self.dropout1 = nn.Dropout(0.2)

        # -> (16, 16, conv_depth)
        self.conv2 = nn.Conv2d(
            in_channels=self.conv_depth,
            out_channels=self.conv_depth,
            kernel_size=5,
            stride=2,
            padding="same",
        )
        self.dropout2 = nn.Dropout(0.2)

        # -> (8, 8, conv_depth)
        self.conv3 = nn.Conv2d(
            in_channels=self.conv_depth,
            out_channels=self.conv_depth,
            kernel_size=5,
            stride=2,
            padding="same",
        )
        self.dropout3 = nn.Dropout(0.2)

        # -> (4, 4, conv_depth)
        self.conv4 = nn.Conv2d(
            in_channels=self.conv_depth,
            out_channels=self.conv_depth,
            kernel_size=5,
            stride=2,
            padding="same",
        )
        self.dropout4 = nn.Dropout(0.2)

        # -> (8, 8, conv_depth)
        self.deconv1 = nn.ConvTranspose2d(
            in_channels=self.conv_depth,
            out_channels=self.conv_depth,
            kernel_size=5,
            stride=2,
            padding="same",
        )
        self.dropout5 = nn.Dropout(0.2)

        # -> (16, 16, conv_depth)
        self.deconv2 = nn.ConvTranspose2d(
            in_channels=self.conv_depth,
            out_channels=self.conv_depth,
            kernel_size=5,
            stride=2,
            padding="same",
        )
        self.dropout6 = nn.Dropout(0.2)

        # -> (32, 32, conv_depth)
        self.deconv3 = nn.ConvTranspose2d(
            in_channels=self.conv_depth,
            out_channels=self.conv_depth,
            kernel_size=5,
            stride=2,
            padding="same",
        )
        self.dropout7 = nn.Dropout(0.2)

        # -> (64, 64, conv_depth)
        self.deconv4 = nn.ConvTranspose2d(
            in_channels=self.conv_depth,
            out_channels=1,
            kernel_size=5,
            stride=2,
            padding="same",
        )
        self.dropout8 = nn.Dropout(0.2)

    def forward(self, x) -> torch.Tensor:
        """
        Pass data through the network
        """
        # "Encoder"
        x = self.conv1(x)
        x = self.dropout1(x)
        x = F.relu(x)

        x = self.conv2(x)
        x = self.dropout2(x)
        x = F.relu(x)

        x = self.conv3(x)
        x = self.dropout3(x)
        x = F.relu(x)

        x = self.conv4(x)
        x = self.dropout4(x)
        x = F.relu(x)

        # "Decoder"
        x = self.deconv1(x)
        x = self.dropout5(x)
        x = F.relu(x)

        x = self.deconv2(x)
        x = self.dropout6(x)
        x = F.relu(x)

        x = self.deconv3(x)
        x = self.dropout7(x)
        x = F.relu(x)

        x = self.deconv4(x)
        x = self.dropout8(x)
        x = F.relu(x)

        return x


class WWDDataset(torch.utils.data.IterableDataset):
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
        # Run parent class constructor
        super().__init__()
        self.tile_size = 64

        # Load data from file
        self.rgb = np.array(PIL.Image.open(rgb_path)).transpose(2, 1, 0)
        self.labels = np.array(PIL.Image.open(labels_path))

        # Normalise and reshape RGB
        self.rgb = self.rgb.astype(np.float32) / 255

        # Binarise labels
        self.labels = self.labels[..., 3]
        self.labels = (self.labels > 128).astype(np.int64)

        self.num_rows = self.rgb.shape[2]
        self.num_cols = self.rgb.shape[1]
        breakpoint()

    def __iter__(self):
        """
        Yield training examples
        """
        for row in range(0, self.num_rows - 2 * self.tile_size, self.tile_size):
            for col in range(0, self.num_cols - 2 * self.tile_size, self.tile_size):
                rgb_tile = self.rgb[
                    :,
                    col : col + self.tile_size,
                    row : row + self.tile_size,
                ]
                labels_tile = self.labels[
                    None,
                    col : col + self.tile_size,
                    row : row + self.tile_size,
                ]
                training_example = (torch.Tensor(rgb_tile), torch.Tensor(labels_tile))
                yield training_example

    def __len__(self) -> int:
        """
        Compute the size of the dataset
        """
        return int(self.num_rows / self.tile_size * self.num_cols / self.tile_size)


def train(
    model: SegmentationNet,
    device: torch.device,
    train_loader: DataLoader,
    optimizer: optim.Optimizer,
    epoch: int,
) -> None:
    """
    Train the model

    Args:
        model: Model to train
        device: Device to run training on
        train_loader: Data loader to train from
        optimizer: Model optimizer
        epoch: Epoch number
    """
    model.train()
    for batch_idx, (data, target) in enumerate(train_loader):
        data, target = data.to(device), target.to(device)
        optimizer.zero_grad()

        # Predict on input data
        output = model(data)

        # Compute loss
        loss = torch.nn.functional.binary_cross_entropy(output, target)

        # Backpropagate loss through network and update weights
        loss.backward()
        optimizer.step()

        print(
            "Train Epoch: {epoch} [{progress}/{num_images} ({progress_percent:.0f}%)]\tLoss: {loss:.6f}".format(
                epoch=epoch,
                progress=batch_idx * len(data),
                num_images=len(train_loader.dataset),
                progress_percent=100.0 * batch_idx / len(train_loader),
                loss=loss.item(),
            )
        )


def test(
    model: SegmentationNet,
    device: torch.device,
    test_loader: DataLoader,
) -> None:
    """
    Test the model on some unseen data

    Args:
        model: Model to train
        device: Device to run training on
        test_loader: Data loader to test from
    """
    model.eval()
    test_loss = 0
    correct = 0
    with torch.no_grad():
        for data, target in test_loader:
            data, target = data.to(device), target.to(device)
            output = model(data)
            test_loss += F.l1_loss(output, target).item()  # sum up batch loss

    test_loss /= len(test_loader.dataset)

    print(
        "\nTest set: Average loss: {:.4f}, Accuracy: {}/{} ({:.0f}%)\n".format(
            test_loss,
            correct,
            len(test_loader.dataset),
            100.0 * correct / len(test_loader.dataset),
        )
    )


def main() -> int:
    """
    Main CLI routine

    Returns:
        Exit status
    """
    num_epochs = 10

    # Deterimine compute device
    use_cuda = torch.cuda.is_available()
    if use_cuda:
        device = torch.device("cuda")
    else:
        device = torch.device("cpu")

    train_loader = DataLoader(
        WWDDataset(
            rgb_path="../data/wwd/combined_bg.jpg",
            labels_path="../data/wwd/walls.png",
        ),
        batch_size=16,
    )
    torch.manual_seed(7777)

    # Construct the model
    model = SegmentationNet().to(device)

    # Construct the model optimizer and scheduler
    optimizer = optim.Adam(model.parameters(), lr=1e-5)
    scheduler = StepLR(optimizer, step_size=1, gamma=0.7)

    for epoch in range(1, num_epochs + 1):
        scheduler.step()
        train(model, device, train_loader, optimizer, epoch)
        # test(model, device, test_loader)

        torch.save(model.state_dict(), "wwd.pt")

    return 0


if __name__ == "__main__":
    sys.exit(main())
