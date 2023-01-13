#!/usr/bin/env python3


"""
Install HQ Python module
"""


from distutils.core import setup


setup(
    name="hq",
    version="1.0",
    description="Genric personal python library",
    author="Hamish Morgan",
    author_email="ham430@gmail.com",
    url="http://github.com/hacmorgan/hq",
    packages=[
        "hq.calculators",
    ],
    scripts=[
        "applications/backup-system",
        "applications/bash-std",
        "applications/branchify-ticket",
        "applications/clean-tmp",
        "applications/comma-help",
        "applications/dmenu-custom",
        "applications/em",
        "applications/gegl-cat",
        "applications/mount-shared-drives",
        "applications/oom-kill-first",
        "applications/rotate-speakers",
        "applications/sdc",
        "applications/snapmaker-status",
        "applications/update-git-repos",
        "applications/where-is-george",
        "applications/ytctl",
    ],
    install_requires=[
        "jedi-language-server",
        "pylint",
        "flake8",
    ],
)
