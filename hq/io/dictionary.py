"""
I/O tools for dictionaries
"""

import json
from typing import Hashable, Any
from pathlib import Path

import yaml


def load_dict(input_path: Path) -> dict[Hashable, Any]:
    """
    Load a dictionary from a file

    Args:
        input_path: Path to the file to load

    Returns:
        Dictionary loaded from the file
    """
    match input_path.suffix.lower():

        case ".json":
            return json.loads(input_path.read_text())

        case ".yaml", ".yml":
            return yaml.safe_load(input_path.read_text())

        case _:
            raise ValueError(f"Unsupported file type: {input_path}")


def save_dict(data: dict[Hashable, Any], output_path: Path) -> None:
    """
    Save a dictionary to a file

    Args:
        data: Dictionary to save
        output_path: Path to the file to save
    """
    # CReate intermediate directories if they don't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save the dictionary to the file with an appropriate dumper
    match output_path.suffix.lower():

        case ".json":
            output_path.write_text(json.dumps(data, indent=4))

        case ".yaml", ".yml":
            output_path.write_text(yaml.dump(data, sort_keys=False))

        case _:
            raise ValueError(f"Unsupported file type: {output_path}")
