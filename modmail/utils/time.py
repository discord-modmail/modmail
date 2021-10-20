import datetime
import enum
import typing

import arrow
import discord


__all__ = [
    "TimeStampEnum",
    "get_discord_formatted_timestamp",
    "monkeypatch_discord_time",
]


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


def parse_time(timestamp: typing.Optional[str]) -> typing.Optional[arrow.Arrow]:
    if timestamp:
        return arrow.get(timestamp)
    return None


def snowflake_time(id: int) -> arrow.Arrow:
    """
    Convert a discord snowflake to a discord markdown timestamp.

    Parameters
    -----------
    id: :class:`int`
        The snowflake ID.

    Returns
    --------
    :class:`arrow.Arrow`
        An aware Arrow in UTC representing the creation time of the snowflake.
    """
    timestamp = ((id >> 22) + discord.utils.DISCORD_EPOCH) / 1000

    return arrow.Arrow.fromtimestamp(timestamp, tzinfo=datetime.timezone.utc)


def monkeypatch_discord_time(*, force: bool = False) -> None:
    """Monkey-patch discord.Object in order to make all created_at times arrow.Arrow objects."""
    if hasattr(discord.utils, "_snowflake_time") and not force:
        raise AttributeError(
            "discord.utils.snowflake_time is already patched. To force a repatch, set force to True."
        )
    discord.utils._snowflake_time = discord.utils.snowflake_time
    discord.utils.snowflake_time = snowflake_time

    # this is necessary because the below imports `from utils` so it
    # is not the same scope to change just discord.utils
    discord.user.snowflake_time = snowflake_time
    discord.invite.snowflake_time = snowflake_time

    # also need to patch the parse_time method
    discord.utils._parse_time = discord.utils.parse_time
    discord.utils.parse_time = parse_time


def _revert_monkeypatch_discord_time() -> None:  # pragma: nocover
    """Revert the discord.py time monkeypatch."""
    if not hasattr(discord.utils, "_snowflake_time"):
        raise AttributeError("discord.utils.snowflake_time is already reverted or was not patched.")

    discord.utils.snowflake_time = discord.utils._snowflake_time

    discord.user.snowflake_time = discord.utils._snowflake_time
    discord.invite.snowflake_time = discord.utils._snowflake_time

    discord.utils.parse_time = discord.utils._parse_time

    del discord.utils._parse_time
    del discord.utils._snowflake_time
