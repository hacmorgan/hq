#!/usr/bin/env -S pytest -vvv


"""
Unit tests for bash-std argument parsing logic.

Each test drives bash-std-application-init with a small inline script,
then checks the resulting shell variable values and exit code.
"""


import os
import shlex
from dataclasses import dataclass
from pathlib import Path

import pytest

from hq.shell import sh_run

# Always source the local bash-std so tests reflect uncommitted changes
_BASH_STD = Path(__file__).parent.parent / "bash-std"


# ---------------------------------------------------------------------------
# Shared OPTIONS fixture used by most tests
# ---------------------------------------------------------------------------

SIMPLE_OPTIONS = """\
--verbose,-v; More output
--output,-o=<path>; default=/dev/stdout; Output file path
--jump,-j=<host>; default=localhost; Host to connect to
--mode=<mode>; Processing mode
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@dataclass
class ParseResult:
    returncode: int
    stdout: str
    stderr: str

    @property
    def succeeded(self) -> bool:
        return self.returncode == 0


def _build_script(options: str, args: list[str], echo_vars: list[str]) -> str:
    """
    Build an inline bash script that sources bash-std, parses args, and echoes variables.

    Args:
        options: Newline-separated bash-std option definitions.
        args: Command-line arguments to pass to bash-std-application-init.
        echo_vars: Shell variable names to echo to stdout after parsing.

    Returns:
        A bash script string ready to be passed to ``bash -c``.
    """
    args_str = " ".join(shlex.quote(a) for a in args)
    echo_cmds = "\n".join(f'echo "{v}=${{{v}}}"' for v in echo_vars)
    return f"""\
source {_BASH_STD}
OPTIONS=$(cat <<'BASH_STD_OPTIONS'
{options}
BASH_STD_OPTIONS
)
bash-std-application-init {args_str} <<< "$OPTIONS"
{echo_cmds}
"""


def parse(
    options: str,
    args: list[str] = (),
    echo_vars: list[str] = (),
    env: dict[str, str] | None = None,
) -> ParseResult:
    """
    Run bash-std argument parsing and return the result.

    Args:
        options: Newline-separated bash-std option definitions.
        args: Command-line arguments to pass to bash-std-application-init.
        echo_vars: Shell variable names to echo to stdout after parsing.
        env: Extra environment variables to set (merged with os.environ).

    Returns:
        ParseResult containing the exit code and captured stdout/stderr.
    """
    script = _build_script(options, args, echo_vars)
    full_env = None
    if env is not None:
        full_env = os.environ.copy()
        full_env.update(env)
    result = sh_run(["bash", "-c", script], shell=False, env=full_env)
    return ParseResult(
        returncode=result.returncode,
        stdout=result.stdout.decode(),
        stderr=result.stderr.decode(),
    )


# ---------------------------------------------------------------------------
# Flag tests
# ---------------------------------------------------------------------------


def test_flag_defaults_to_zero() -> None:
    """
    A flag option is initialised to 0 when not supplied.
    """
    result = parse(SIMPLE_OPTIONS, args=["--mode=fast"], echo_vars=["options_verbose"])
    assert result.succeeded
    assert "options_verbose=0" in result.stdout


def test_flag_set_by_long_form() -> None:
    """
    Passing --verbose sets options_verbose=1.
    """
    result = parse(
        SIMPLE_OPTIONS,
        args=["--verbose", "--mode=fast"],
        echo_vars=["options_verbose"],
    )
    assert result.succeeded
    assert "options_verbose=1" in result.stdout


def test_flag_set_by_short_form() -> None:
    """
    Passing -v (short alias) sets options_verbose=1.
    """
    result = parse(
        SIMPLE_OPTIONS,
        args=["-v", "--mode=fast"],
        echo_vars=["options_verbose"],
    )
    assert result.succeeded
    assert "options_verbose=1" in result.stdout


# ---------------------------------------------------------------------------
# Value option tests
# ---------------------------------------------------------------------------


def test_value_set_with_equals_syntax() -> None:
    """
    --output=/path sets options_output via the --key=value form.
    """
    result = parse(
        SIMPLE_OPTIONS,
        args=["--output=/tmp/out.txt", "--mode=fast"],
        echo_vars=["options_output"],
    )
    assert result.succeeded
    assert "options_output=/tmp/out.txt" in result.stdout


def test_value_set_with_space_syntax() -> None:
    """
    --output /path sets options_output via the --key <space> value form.
    """
    result = parse(
        SIMPLE_OPTIONS,
        args=["--output", "/tmp/out.txt", "--mode=fast"],
        echo_vars=["options_output"],
    )
    assert result.succeeded
    assert "options_output=/tmp/out.txt" in result.stdout


def test_value_set_by_short_form_equals() -> None:
    """
    -o=/path (short alias with =) sets options_output.
    """
    result = parse(
        SIMPLE_OPTIONS,
        args=["-o=/tmp/out.txt", "--mode=fast"],
        echo_vars=["options_output"],
    )
    assert result.succeeded
    assert "options_output=/tmp/out.txt" in result.stdout


def test_value_set_by_short_form_space() -> None:
    """
    -o /path (short alias with space) sets options_output.
    """
    result = parse(
        SIMPLE_OPTIONS,
        args=["-o", "/tmp/out.txt", "--mode=fast"],
        echo_vars=["options_output"],
    )
    assert result.succeeded
    assert "options_output=/tmp/out.txt" in result.stdout


# ---------------------------------------------------------------------------
# Default value tests
# ---------------------------------------------------------------------------


def test_default_used_when_option_absent() -> None:
    """
    A value option with a default keeps that default when not supplied.
    """
    result = parse(
        SIMPLE_OPTIONS,
        args=["--mode=fast"],
        echo_vars=["options_jump"],
    )
    assert result.succeeded
    assert "options_jump=localhost" in result.stdout


def test_default_overridden() -> None:
    """
    Passing --jump=myserver overrides the default value.
    """
    result = parse(
        SIMPLE_OPTIONS,
        args=["--jump=myserver", "--mode=fast"],
        echo_vars=["options_jump"],
    )
    assert result.succeeded
    assert "options_jump=myserver" in result.stdout


# ---------------------------------------------------------------------------
# Alias tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "alias",
    ["--backup-directory=/data", "--backup-dir=/data", "-b=/data"],
)
def test_multiple_aliases_set_same_variable(alias: str) -> None:
    """
    All aliases (long, abbreviated long, short) set the canonical variable.
    """
    options = "--backup-directory,--backup-dir,-b=<dir>; default=/tmp; Directory"
    result = parse(options, args=[alias], echo_vars=["options_backup_directory"])
    assert result.succeeded, f"Failed for alias {alias!r}:\n{result.stderr}"
    assert "options_backup_directory=/data" in result.stdout


# ---------------------------------------------------------------------------
# Error / validation tests
# ---------------------------------------------------------------------------


def test_missing_required_value_causes_failure() -> None:
    """
    Omitting a required value option (no default) must exit non-zero.
    """
    # --mode=<mode> is required and has no default; --output is also required
    result = parse(SIMPLE_OPTIONS, args=["--verbose"])
    assert not result.succeeded


def test_unknown_argument_causes_failure() -> None:
    """
    An unrecognised argument must cause a non-zero exit by default.
    """
    result = parse(SIMPLE_OPTIONS, args=["--mode=fast", "--not-a-real-flag"])
    assert not result.succeeded
    assert "unrecognised" in result.stderr


def test_unknown_argument_ignored_with_env_var() -> None:
    """
    BASH_STD_IGNORE_UNKNOWN_ARGS=1 suppresses the error for unknown args.
    """
    result = parse(
        SIMPLE_OPTIONS,
        args=["--mode=fast", "--not-a-real-flag"],
        echo_vars=["options_mode"],
        env={"BASH_STD_IGNORE_UNKNOWN_ARGS": "1"},
    )
    assert result.succeeded
    assert "options_mode=fast" in result.stdout


# ---------------------------------------------------------------------------
# Help tests
# ---------------------------------------------------------------------------


def test_help_long_form_exits_zero() -> None:
    """
    --help must print usage and exit 0.
    """
    result = parse(SIMPLE_OPTIONS, args=["--help"])
    assert result.succeeded


def test_help_short_form_exits_zero() -> None:
    """
    -h must print usage and exit 0.
    """
    result = parse(SIMPLE_OPTIONS, args=["-h"])
    assert result.succeeded


# ---------------------------------------------------------------------------
# Positional argument tests
# ---------------------------------------------------------------------------

POSITIONAL_OPTIONS = """\
source-file; Source file to process
destination; Destination path
--verbose,-v; More output
"""


def test_positional_assigned_in_order() -> None:
    """
    Positional values are captured into variables in definition order.
    """
    result = parse(
        POSITIONAL_OPTIONS,
        args=["/tmp/input.txt", "/tmp/output.txt"],
        echo_vars=["options_source_file", "options_destination"],
    )
    assert result.succeeded
    assert "options_source_file=/tmp/input.txt" in result.stdout
    assert "options_destination=/tmp/output.txt" in result.stdout


def test_positional_interleaved_with_flags() -> None:
    """
    Positionals and flags can appear in any order; both are captured correctly.
    """
    result = parse(
        POSITIONAL_OPTIONS,
        args=["--verbose", "/tmp/input.txt", "/tmp/output.txt"],
        echo_vars=["options_source_file", "options_destination", "options_verbose"],
    )
    assert result.succeeded
    assert "options_source_file=/tmp/input.txt" in result.stdout
    assert "options_destination=/tmp/output.txt" in result.stdout
    assert "options_verbose=1" in result.stdout


def test_positional_hyphen_becomes_underscore() -> None:
    """
    Hyphens in positional names are converted to underscores in the variable name.
    """
    options = "input-file; Input file\n"
    result = parse(options, args=["/tmp/in.txt"], echo_vars=["options_input_file"])
    assert result.succeeded
    assert "options_input_file=/tmp/in.txt" in result.stdout


def test_missing_required_positional_causes_failure() -> None:
    """
    Omitting a required positional (no default) must exit non-zero.
    """
    result = parse(POSITIONAL_OPTIONS, args=["/tmp/input.txt"])  # destination missing
    assert not result.succeeded


def test_positional_with_default_not_required() -> None:
    """
    A positional with a default does not fail when omitted.
    """
    options = "output; default=/dev/stdout; Output path\n"
    result = parse(options, args=[], echo_vars=["options_output"])
    assert result.succeeded
    assert "options_output=/dev/stdout" in result.stdout
