#!/usr/bin/env python3


"""
Train regression model
"""


import sys
import os
from typing import Tuple

from random import shuffle
import numpy as np
import PIL.Image
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch import optim
from torch.optim.lr_scheduler import StepLR
from torch.utils.data import DataLoader
from torchvision import datasets, transforms


DEVICE = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")

NORMALISATION_MEAN = 0.1307
NORMALISATION_STD = 0.3081

NUM_EPOCHS = 5
LOG_INTERVAL = 10


class FullyConnectedNet(nn.Module):
    """
    Basic fully connected network
    """

    def __init__(self):
        super().__init__()
        self.fc1 = nn.Linear(784, 128)
        self.fc2 = nn.Linear(128, 10)

    def forward(self, x):
        x = torch.flatten(x, 1)
        x = self.fc1(x)
        x = F.relu(x)
        x = self.fc2(x)
        output = F.log_softmax(x, dim=1)
        return output


class RegressionNet(nn.Module):
    """
    Basic regression network
    """

    def __init__(self):
        super().__init__()

        self.conv_depth = 16

        # Input shape: (480, 640, 3)

        # -> (240, 320, 32)
        self.conv1 = nn.Conv2d(3, self.conv_depth, 3, 2)
        self.dropout1 = nn.Dropout(0.2)

        # -> (120, 160, 32)
        self.conv2 = nn.Conv2d(self.conv_depth, self.conv_depth, 3, 2)
        self.dropout2 = nn.Dropout(0.2)

        # -> (60, 80, 32)
        self.conv3 = nn.Conv2d(self.conv_depth, self.conv_depth, 3, 2)
        self.dropout3 = nn.Dropout(0.2)

        # -> (30, 40, 32)
        self.conv4 = nn.Conv2d(self.conv_depth, self.conv_depth, 3, 2)
        self.dropout4 = nn.Dropout(0.2)

        self.fc1 = nn.Linear(90480, 10)
        self.dropout5 = nn.Dropout(0.2)

        self.fc2 = nn.Linear(10, 1)

    def forward(self, x):
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

        x = torch.flatten(x)

        x = self.fc1(x)
        x = self.dropout5(x)
        x = F.relu(x)

        return self.fc2(x)


def load_mnist(use_cuda: bool) -> Tuple[DataLoader, DataLoader]:
    """
    Load train and test datasets
    """
    transform = transforms.Compose(
        [
            transforms.ToTensor(),
            transforms.Normalize((NORMALISATION_MEAN,), (NORMALISATION_STD,)),
        ]
    )
    train_ds = datasets.MNIST("data", train=True, download=True, transform=transform)
    test_ds = datasets.MNIST("data", train=False, transform=transform)
    train_kwargs = {"batch_size": 64}
    test_kwargs = {"batch_size": 1000}
    if use_cuda:
        cuda_kwargs = {"num_workers": 1, "pin_memory": True, "shuffle": True}
        train_kwargs.update(cuda_kwargs)
        test_kwargs.update(cuda_kwargs)
    train_loader = DataLoader(train_ds, **train_kwargs)
    test_loader = DataLoader(test_ds, **test_kwargs)
    return train_loader, test_loader


class WalkingDataset(torch.utils.data.IterableDataset):
    def __init__(self, root_dir: str):
        super().__init__()
        self.root_dir = root_dir
        self.paths = []
        self.have_seen_entire_datset = False

    def __iter__(self):
        if not self.have_seen_entire_datset:
            for dirname, _, files in os.walk(self.root_dir):
                for basename in files:
                    path = os.path.join(dirname, basename)
                    self.paths.append(path)
                    yield path
            self.have_seen_entire_datset = True
        else:
            yield from self.paths


class CsvDataset(torch.utils.data.IterableDataset):
    def __init__(self, csv_path: str):
        super().__init__()
        self.csv_path = csv_path
        self.examples = []
        self.have_seen_entire_datset = False

    def __iter__(self):
        if not self.have_seen_entire_datset:
            with open(self.csv_path, mode="r", encoding="utf-8") as csv_fp:
                for line in csv_fp.readlines():
                    path, label = line.strip().split(",")
                    img = (
                        torch.tensor(
                            np.array(PIL.Image.open(path)).transpose(2, 1, 0),
                            dtype=torch.float,
                        )
                        / 255.0
                    )
                    label = torch.tensor(float(label)) / 10
                    example = (img, label)
                    self.examples.append(example)
            self.have_seen_entire_dataset = True
        shuffle(self.examples)
        yield from self.examples

    def __len__(self):
        return len(self.examples)


def train(
    model: FullyConnectedNet,
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
        loss = F.l1_loss(output, target)

        # Backpropagate loss through network and update weights
        loss.backward()
        optimizer.step()

        if batch_idx % LOG_INTERVAL == 0:
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
    model: FullyConnectedNet,
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
    Train and evaluate model

    Returns:
        Exit status
    """
    # Deterimine compute device
    use_cuda = torch.cuda.is_available()
    if use_cuda:
        device = torch.device("cuda")
    else:
        device = torch.device("cpu")

    # Load dataset
    # train_loader, test_loader = load_datasets(use_cuda=use_cuda)
    train_loader = DataLoader(
        # CsvDataset(csv_path="/home/hamish/src/hq/python/hq/ml/labels.train.csv"),
        CsvDataset(csv_path="/home/hamish/src/hq/python/hq/ml/labels.csv"),
        batch_size=5,
    )
    test_loader = DataLoader(
        CsvDataset(csv_path="/home/hamish/src/hq/python/hq/ml/labels.val.csv"),
        batch_size=5,
    )

    torch.manual_seed(7777)

    # Construct the model
    # model = FullyConnectedNet().to(device)
    # model = ConvotionalNet().to(device)
    model = RegressionNet().to(device)

    # optimizer = optim.Adadelta(model.parameters(), lr=args.lr)
    optimizer = optim.Adam(model.parameters(), lr=1e-6)
    scheduler = StepLR(optimizer, step_size=1, gamma=0.7)

    for epoch in range(1, NUM_EPOCHS + 1):
        train(model, device, train_loader, optimizer, epoch)
        # test(model, device, test_loader)
        scheduler.step()

        torch.save(model.state_dict(), "mnist_cnn.pt")

    return 0


if __name__ == "__main__":
    sys.exit(main())
