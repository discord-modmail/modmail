import logging
import logging.handlers
from pathlib import Path

import coloredlogs

from modmail.log import ModmailLogger

# this block allows coloredlogs coloring to be overidden by the enviroment variable.
# coloredlogs contains support for it, but strangely does not default to the enviroment overriding.
try:
    # import the enviroment package
    from environs import Env
except ImportError:
    COLOREDLOGS_LEVEL_STYLES = None
else:
    env = Env()
    env.read_env("./env")
    COLOREDLOGS_LEVEL_STYLES = env.str("COLOREDLOGS_LEVEL_STYLES", None)

logging.TRACE = 5
logging.NOTICE = 25
logging.addLevelName(logging.TRACE, "TRACE")
logging.addLevelName(logging.NOTICE, "NOTICE")

# this logging level is set to logging.TRACE because if it is not set to the lowest level,
# the child level will be limited to the lowest level this is set to.
ROOT_LOG_LEVEL = logging.TRACE
FMT = "%(asctime)s %(levelname)10s %(name)15s - [%(lineno)5d]: %(message)s"
DATEFMT = "%Y/%m/%d %H:%M:%S"

logging.setLoggerClass(ModmailLogger)

# Set up file logging
log_file = Path("logs", "bot.log")
log_file.parent.mkdir(parents=True, exist_ok=True)

# file handler
file_handler = logging.handlers.RotatingFileHandler(
    log_file,
    maxBytes=5 * (2 ** 12),
    backupCount=5,
    encoding="utf-8",
)

file_handler.setFormatter(
    logging.Formatter(
        fmt=FMT,
        datefmt=DATEFMT,
    )
)

file_handler.setLevel(logging.TRACE)

# configure trace color if the env var is not configured
if COLOREDLOGS_LEVEL_STYLES is None:
    LEVEL_STYLES = coloredlogs.DEFAULT_LEVEL_STYLES
    LEVEL_STYLES["trace"] = LEVEL_STYLES["spam"]
else:
    LEVEL_STYLES = None

coloredlogs.install(level=logging.TRACE, fmt=FMT, datefmt=DATEFMT, level_styles=LEVEL_STYLES)

# Create root logger
root: ModmailLogger = logging.getLogger()
root.setLevel(ROOT_LOG_LEVEL)
root.addHandler(file_handler)

# Silence irrelevant loggers
logging.getLogger("discord").setLevel(logging.WARNING)
logging.getLogger("websockets").setLevel(logging.ERROR)
# Set asyncio logging back to the default of INFO even if asyncio's debug mode is enabled.
logging.getLogger("asyncio").setLevel(logging.INFO)
