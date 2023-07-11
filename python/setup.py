#!/usr/bin/env python3


"""
Install HQ Python module
"""


from distutils.core import setup
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
        "hq.hardware",
    ],
    scripts=list(map(str, Path("applications").iterdir())),
    install_requires=[
        "pylint",
        "flake8",
        "numpy>1.20",
        "virtualenv",
    ],
)
