"""
Time and date utilities
"""

from datetime import datetime


def dense_iso_timestamp(dtm: datetime | None = None) -> str:
    """
    Generate a timestamp in dense ISO format (i.e. no dashes or spaces)

    Args:
        dtm: Datetime to format (current time if not given)

    Returns:
        Timestamp in dense ISO format
    """
    return (dtm or datetime.now()).strftime("%Y%m%dT%H%M%S")
