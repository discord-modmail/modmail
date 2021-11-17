import arrow
import pytest

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
