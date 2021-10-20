import arrow
import discord
import pytest

from modmail import utils
from modmail.utils import time as utils_time
from modmail.utils.time import TimeStampEnum


@pytest.mark.parametrize(
    ["timestamp", "expected", "mode"],
    [
        [arrow.get(1634593650), "<t:1634593650:f>", TimeStampEnum.SHORT_DATE_TIME],
        [arrow.get(1), "<t:1:f>", TimeStampEnum.DEFAULT],
        [arrow.get(12356941), "<t:12356941:R>", TimeStampEnum.RELATIVE_TIME],
        [arrow.get(8675309).datetime, "<t:8675309:D>", TimeStampEnum.LONG_DATE],
    ],
)
def test_timestamp(timestamp, expected: str, mode: utils_time.TimeStampEnum):
    """Test the timestamp is of the proper form."""
    fmtted_timestamp = utils_time.get_discord_formatted_timestamp(timestamp, mode)
    assert expected == fmtted_timestamp


def test_enum_default():
    """Ensure that the default mode is of the correct mode, and works properly."""
    assert TimeStampEnum.DEFAULT.name == TimeStampEnum.SHORT_DATE_TIME.name
    assert TimeStampEnum.DEFAULT.value == TimeStampEnum.SHORT_DATE_TIME.value


@pytest.mark.parametrize(
    ["id", "expected"],
    [
        [20 << 22, arrow.Arrow.fromtimestamp("1420070400020")],
    ],
)
def test_snowflake_time(id: int, expected: arrow.Arrow):
    """Test snowflake_time properly converts an id to the proper arrow.Arrow object."""
    timestamp = utils_time.snowflake_time(id)
    assert timestamp == expected


def test_monkeypatch():
    """
    Assert that discord.utils.snowflake_time was properly monkeypatched.

    If it is not, there is an issue with the entire testing procedure
    and some tests may not be accurate if this test fails.
    """
    assert utils_time.snowflake_time == discord.utils.snowflake_time
    assert utils_time.parse_time == discord.utils.parse_time

    with pytest.raises(AttributeError):
        utils_time.monkeypatch_discord_time()
