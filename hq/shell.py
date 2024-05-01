"""
Standard logic for running shell commands
"""


from functools import partial
from subprocess import (
    run,
    PIPE,
    CompletedProcess,
    CalledProcessError,
)
import sys


ERROR_TEMPLATE = """
Process {popenargs} returned nonzero exit status: {returncode}

stdout:
{stdout}

stderr:
{stderr}
"""


def sh_run(
    *popenargs,
    shell=True,
    stdout=PIPE,
    stderr=PIPE,
    **kwargs,
) -> CompletedProcess:
    """
    Run shell command
    """
    completed_process = run(
        *popenargs, shell=shell, check=False, stdout=stdout, stderr=stderr, **kwargs
    )
    if completed_process.returncode != 0:
        print(
            ERROR_TEMPLATE.format(
                popenargs=popenargs,
                returncode=completed_process.returncode,
                stdout=completed_process.stdout.decode("utf-8") or "",
                stderr=completed_process.stderr.decode("utf-8") or "",
            ),
            file=sys.stderr,
        )
    return completed_process
