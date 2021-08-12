from datetime import datetime

from discord.ext.commands import BadArgument, Context, Converter

from modmail.utils.time import parse_duration_string


class Duration(Converter):
    """Convert duration strings into UTC datetime.datetime objects."""

    async def convert(self, ctx: Context, duration: str) -> datetime:
        """
        Converts a `duration` string to a datetime object that's `duration` in the future.

        The converter supports the following symbols for each unit of time:
            - years: `Y`, `y`, `year`, `years`
            - months: `m`, `month`, `months`
            - weeks: `w`, `W`, `week`, `weeks`
            - days: `d`, `D`, `day`, `days`
            - hours: `H`, `h`, `hour`, `hours`
            - minutes: `M`, `minute`, `minutes`
            - seconds: `S`, `s`, `second`, `seconds`
        The units need to be provided in descending order of magnitude.
        """
        if not (delta := parse_duration_string(duration)):
            raise BadArgument(f"`{duration}` is not a valid duration string.")
        now = datetime.utcnow()

        try:
            return now + delta
        except (ValueError, OverflowError):
            raise BadArgument(f"`{duration}` results in a datetime outside the supported range.")
