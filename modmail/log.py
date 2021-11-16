import logging
import pathlib
from typing import Any


__all__ = [
    "DEFAULT",
    "get_logging_level",
    "set_logger_levels",
    "ModmailLogger",
]

logging.TRACE = 5
logging.NOTICE = 25
logging.addLevelName(logging.TRACE, "TRACE")
logging.addLevelName(logging.NOTICE, "NOTICE")

DEFAULT = logging.INFO


def _get_env() -> dict:
    import os

    try:
        from dotenv import dotenv_values
    except ModuleNotFoundError:
        dotenv_values = lambda *args, **kwargs: dict()  # noqa: E731

    return {**dotenv_values(), **os.environ}


def get_logging_level() -> None:
    """Get the configured logging level, defaulting to logging.INFO."""
    key = "MODMAIL_LOG_LEVEL"

    level = _get_env().get(key, DEFAULT)

    try:
        level = int(level)
    except TypeError:
        level = DEFAULT
    except ValueError:
        level = level.upper()
        if hasattr(logging, level) and isinstance(getattr(logging, level), int):
            return getattr(logging, level)
        print(
            f"Environment variable {key} must be able to be converted into an integer.\n"
            f"To resolve this issue, set {key} to an integer value, or remove it from the environment.\n"
            "It is also possible that it is sourced from an .env file."
        )
        exit(1)

    return level


def set_logger_levels() -> None:
    """
    Set all loggers to the provided environment variables.

    eg MODMAIL_TRACE_LOGGERS will be split by `,` and each logger will be set to the trace level
    This is applied for every logging level.
    """
    env_vars = _get_env()
    fmt_key = "MODMAIL_{level}_LOGGERS"

    for level in ["trace", "debug", "info", "notice", "warning", "error", "critical"]:
        level = level.upper()
        key = fmt_key.format(level=level)
        loggers: str = env_vars.get(key, None)
        if loggers is None:
            continue

        for logger in loggers.split(","):
            logging.getLogger(logger.strip()).setLevel(level)


def get_log_dir() -> pathlib.Path:
    """
    Return a directory to be used for logging.

    The log directory is made in the current directory
    unless the current directory shares a parent directory with the bot.

    This is ignored if a environment variable provides the logging directory.
    """
    env_vars = _get_env()
    key = "MODMAIL_LOGGING_DIRECTORY"
    if env_vars.get(key, None) is not None:
        return pathlib.Path(env_vars[key]).expanduser()

    import modmail

    path = pathlib.Path(modmail.__file__).parent.parent
    cwd = pathlib.Path.cwd()
    try:
        cwd.relative_to(path)
    except ValueError:
        return cwd / "logs"
    else:
        return path / "logs"


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
