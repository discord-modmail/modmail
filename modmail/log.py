import logging
from typing import Any, Union


def get_log_level_from_name(name: Union[str, int]) -> int:
    """Find the logging level given the provided name."""
    if isinstance(name, int):
        return name
    name = name.upper()
    value = getattr(logging, name, "")
    if not isinstance(value, int):
        raise TypeError("name must be an existing logging level.")
    return value


class ModmailLogger(logging.Logger):
    """Custom logging class implementation."""

    def trace(self, msg: Any, *args, **kwargs) -> None:
        """
        Log 'msg % args' with severity 'TRACE'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        logger.trace("Houston, we have a %s", "low-level problem", exc_info=1)
        """
        self.log(logging.TRACE, msg, *args, **kwargs)

    def notice(self, msg: Any, *args, **kwargs) -> None:
        """
        Log 'msg % args' with severity 'NOTICE'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        logger.notice("Houston, we have a %s", "not-quite-a-warning problem", exc_info=1)
        """
        self.log(logging.NOTICE, msg, *args, **kwargs)
