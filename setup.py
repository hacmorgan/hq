#!/usr/bin/env python3


"""
Install HQ Python module
"""


from distutils.core import setup
import os
from pathlib import Path


setup(
    name="hq",
    version="1.0",
    description="Generic personal python library",
    author="Hamish Morgan",
    author_email="ham430@gmail.com",
    url="http://github.com/hacmorgan/hq",
    packages=[
        "hq",
        "hq.calculators",
        "hq.gui",
        "hq.hardware",
        "hq.ml",
        "hq.ml.wwd",
    ],
    scripts=list(map(str, Path("applications").iterdir())),
    install_requires=[
        "black",
        "distro",
        "flake8",
        "ipython",
        "jedi_language_server",
        "numpy",
        "opencv-python-headless",
        "pillow",
        "pylint",
        "typer",
        "virtualenv",
    ]
    + (["torch", "torchvision"] if "HQML" in os.environ else []),
)
