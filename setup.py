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
        "cattrs",
        "cloudpickle",
        "distro",
        "flake8",
        "ipython",
        "jedi_language_server",
        "keyboard",
        "numpy",
        "opencv-python-headless",
        "pillow",
        "pygls>1.1.1",  # Avoids (1) from version 1.1.1
        "pylint",
        "typer",
        "virtualenv",
    ]
    + (["torch", "torchvision"] if "HQML" in os.environ else []),
)


# Errors
# (1) - TypeError when initialising jedi-language-server in emacs
#         TypeError: Options of method "textDocument/completion" should be instance of
#         type <class 'lsprotocol.types.CompletionOptions'>
