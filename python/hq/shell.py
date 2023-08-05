"""
Standard logic for running shell commands
"""


from functools import partial
from subprocess import run


sh_run = partial(run, shell=True, check=True)
