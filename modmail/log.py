import logging
from typing import Any


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
