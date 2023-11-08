"""
Standard logic for running shell commands
"""


from functools import partial
from subprocess import run, PIPE


sh_run = partial(run, shell=True, check=True, stdout=PIPE, stderr=PIPE)
