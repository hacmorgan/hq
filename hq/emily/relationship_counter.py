"""
Compute how long Emily and Hamish have been going out for
"""

from datetime import datetime, timedelta


RELATIONSHIP_START = datetime(year=2017, month=6, day=2, hour=18)
STRING_FORMAT_TEMPLATE = """
Hamish and Emily have been going out for:

    {years} years
    {days} days
    {hours} hours
    {minutes} minutes
    {seconds} seconds
    {milliseconds} milliseconds
    {microseconds} microseconds
"""


def relationship_time(return_timedelta: bool = True) -> timedelta | str:
    """
    Compute relationship time as timedelta

    Args:
        return_timedelta: Return the relationship time as a timedelta if True, return as
            formatted string otherwise

    Returns:
        Relationship time as a timedelta or formatted string
    """
    # Find the timedelta between the current time and the start of the relationship
    rel_dt = datetime.now() - RELATIONSHIP_START

    # If that's all we want, return the timedelta
    if return_timedelta:
        return rel_dt

    # Otherwise, format the timedelta as a string
    years = rel_dt.days // 365
    days = rel_dt.days % 365
    hours, improper_seconds = divmod(rel_dt.seconds, 3600)
    minutes, seconds = divmod(improper_seconds, 60)
    milliseconds = rel_dt.microseconds // 1000
    microseconds = rel_dt.microseconds % 1000
    return STRING_FORMAT_TEMPLATE.format(
        years=years,
        days=days,
        hours=hours,
        minutes=minutes,
        seconds=seconds,
        milliseconds=milliseconds,
        microseconds=microseconds,
    )
