import datetime
import enum
import typing

import arrow


class TimeStampEnum(enum.Enum):
    """
    Timestamp modes for discord.

    Full docs on this format are viewable here:
    https://discord.com/developers/docs/reference#message-formatting
    """

    SHORT_TIME = "t"
    LONG_TIME = "T"
    SHORT_DATE = "d"
    LONG_DATE = "D"
    SHORT_DATE_TIME = "f"
    LONG_DATE_TIME = "F"
    RELATIVE_TIME = "R"

    # DEFAULT
    DEFAULT = SHORT_DATE_TIME


TypeTimes = typing.Union[arrow.Arrow, datetime.datetime]


def get_discord_formatted_timestamp(
    timestamp: TypeTimes, format: TimeStampEnum = TimeStampEnum.DEFAULT
) -> str:
    """
    Return a discord formatted timestamp from a datetime compatiable datatype.

    `format` must be an enum member of TimeStampEnum. Default style is SHORT_DATE_TIME
    """
    return f"<t:{int(timestamp.timestamp())}:{format.value}>"
