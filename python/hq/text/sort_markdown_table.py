#!/usr/bin/env python


"""
Sort a markdown table in alphabetical order, balance columns, and generate header

This is intended to automate the alphabetical sorting and column balancing required when
adding an element to a markdown table

Usage:

1. Paste the unsorted markdown table (without header rows) into a text file

2. Run the script as below

    python3 sort_markdown_table.py <input-path> <output-path>

where

    <input-path> is the path of the file created in step 1
    <output-path> is the path where this script will write the sorted table

Authors: Hamish Morgan, Alex Fraser
Date:    24/02/2023
License: BSD
"""


import sys

from math import ceil


def read_table(md_table: str) -> list[str]:
    """
    Parse markdown pipe-separated table

    Args:
        md_table: Markdown table text

    Returns:
        Elements in markdown table (unsorted)
    """
    return [elem for elem in md_table.split("|") if elem not in ("\n", "")]


def element_name(element: str) -> str:
    """
    Detect if element is plain HTML or HTML shortcode and extract element name

    Args:
        element: Full contents of table element

    Returns:
        Name of table element
    """
    # HTML shortcode
    if element.startswith("["):
        return element[1 : element.find("]")].lower()

    # Plain HTML
    name_start = element.find(">") + 1
    return element[name_start : element.find("<", name_start)].lower()


def split_into_columns(
    elements: list[str], num_columns: int = 3
) -> tuple[list[str], ...]:
    """
    Split a sorted list of table elements into columns

    Args:
        elements: Table elements in desired order
        num_columns: Number of columns to sort into

    Returns:
        Sorted, balanced table columns
    """
    num_rows = ceil(len(elements) / num_columns)
    return tuple(elements[i : i + num_rows] for i in range(0, len(elements), num_rows))


def create_table(columns: tuple[list[str], ...]) -> str:
    """
    Generate a markdown table from data in columns

    Also creates header rows

    Args:
        columns: Sorted, balanced table columns

    Returns:
        Markdown formatted table text
    """
    # Make header rows
    header_row_0 = "|"
    header_row_1 = "|"
    for column in columns:
        first_element_name, last_element_name = (
            element_name(column[idx]) for idx in (0, -1)
        )
        header_row_0 += (
            f"{first_element_name[0].upper()}-{last_element_name[0].upper()}|"
        )
        header_row_1 += "---|"

    return (
        "\n".join(
            [
                header_row_0,
                header_row_1,
            ]
            + [("|" + "|".join(row) + "|") for row in zip(*columns)]
        )
        + "\n"
    )


def sort_table(md_table: str) -> str:
    """
    Sort a markdown table alphabetically

    Args:
        md_table: Markdown table text

    Returns:
        Sorted, balanced markdown table
    """
    sorted_elements = sorted(read_table(md_table=md_table), key=element_name)
    columns = split_into_columns(elements=sorted_elements)
    return create_table(columns=columns)


def main() -> int:
    """
    Main CLI routine

    Returns:
        Exit status
    """
    # Parse positional command line args
    try:
        input_path, output_path = sys.argv[1:3]
    except IndexError:
        print(
            "Usage: python3 sort_markdown_table.py <input-path> <output-path>",
            file=sys.stderr,
        )
        return 1

    # Load unsorted markdown table
    with open(input_path, mode="r", encoding="utf-8") as input_fd:
        md_table = input_fd.read()

    # Write sorted markdown table
    with open(output_path, mode="w", encoding="utf-8") as output_fd:
        output_fd.write(sort_table(md_table=md_table))

    return 0


if __name__ == "__main__":
    sys.exit(main())
