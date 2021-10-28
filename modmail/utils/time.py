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

    # fmt: off
    SHORT_TIME = "t"        # 16:20
    LONG_TIME = "T"         # 16:20:30
    SHORT_DATE = "d"        # 20/04/2021
    LONG_DATE = "D"         # 20 April 2021
    SHORT_DATE_TIME = "f"   # 20 April 2021 16:20
    LONG_DATE_TIME = "F"    # Tuesday, 20 April 2021 16:20
    RELATIVE_TIME = "R"     # 2 months ago

    # fmt: on
    # DEFAULT alised to the default, so for all purposes, it behaves like SHORT_DATE_TIME, including the name
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
