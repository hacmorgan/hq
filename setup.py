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
        "hq.cli",
        "hq.emily",
        "hq.gui",
        "hq.gui.dashboard",
        "hq.gui.dashboard.lib",
        "hq.hardware",
        "hq.integrations",
        "hq.io",
        "hq.ml",
        "hq.ml.wwd",
    ],
    scripts=[
        str(path)
        for path in Path("applications").iterdir()
        if not path.stem.startswith(".") and not path.is_dir()
    ],
    install_requires=[
        "black",
        "cattrs",
        "cloudpickle",
        "distro",
        "escpos",
        "fastapi",
        "flake8",
        "ipython",
        "jedi_language_server",
        "keyboard",
        "numpy",
        "opencv-python-headless",
        "pillow",
        "pygls>1.1.1",  # Avoids (1) from version 1.1.1
        "pylint",
        "pyserial",
        "pytest",
        "typer",
        "uvicorn",
        "ytmusicapi",
    ]
    + (["torch", "torchvision"] if "HQML" in os.environ else []),
)


# Errors
# (1) - TypeError when initialising jedi-language-server in emacs
#         TypeError: Options of method "textDocument/completion" should be instance of
#         type <class 'lsprotocol.types.CompletionOptions'>
