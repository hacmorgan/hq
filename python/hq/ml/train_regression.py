#!/usr/bin/env python3


"""
Train regression model
"""


#!/usr/bin/env python3


import sys
import os
from typing import Tuple

import numpy as np
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

NUM_EPOCHS = 15
LOG_INTERVAL = 1


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
        self.conv1 = nn.Conv2d(1, 32, 3, 1)
        self.conv2 = nn.Conv2d(32, 64, 3, 1)
        self.dropout1 = nn.Dropout(0.2)
        self.dropout2 = nn.Dropout(0.2)
        self.fc1 = nn.Linear(9216, 128)
        self.fc2 = nn.Linear(128, 10)

    def forward(self, x):
        x = self.conv1(x)
        x = F.relu(x)
        x = self.conv2(x)
        x = F.relu(x)
        x = F.max_pool2d(x, 2)
        x = self.dropout1(x)
        x = torch.flatten(x, 1)
        x = self.fc1(x)
        x = F.relu(x)
        x = self.dropout2(x)
        x = self.fc2(x)
        output = F.log_softmax(x, dim=1)
        return output


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


class MyIterableDataset(torch.utils.data.IterableDataset):
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
        loss = F.L1Loss()(output, target)

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
            test_loss += F.L1Loss()(output, target).item()  # sum up batch loss
            pred = output.argmax(
                dim=1, keepdim=True
            )  # get the index of the max log-probability
            correct += pred.eq(target.view_as(pred)).sum().item()

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
    train_loader, test_loader = load_datasets(use_cuda=use_cuda)

    torch.manual_seed(7777)

    # Construct the model
    # model = FullyConnectedNet().to(device)
    model = ConvotionalNet().to(device)

    # optimizer = optim.Adadelta(model.parameters(), lr=args.lr)
    optimizer = optim.Adam(model.parameters(), lr=1e-5)
    scheduler = StepLR(optimizer, step_size=1, gamma=0.7)

    for epoch in range(1, NUM_EPOCHS + 1):
        train(model, device, train_loader, optimizer, epoch)
        test(model, device, test_loader)
        scheduler.step()

    torch.save(model.state_dict(), "mnist_cnn.pt")

    return 0
