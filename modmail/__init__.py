import logging
import logging.handlers
from pathlib import Path

import coloredlogs

from modmail.log import ModmailLogger


logging.TRACE = 5
logging.NOTICE = 25
logging.addLevelName(logging.TRACE, "TRACE")
logging.addLevelName(logging.NOTICE, "NOTICE")


LOG_FILE_SIZE = 8 * (2 ** 10) ** 2  # 8MB, discord upload limit

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
    maxBytes=LOG_FILE_SIZE,
    backupCount=7,
    encoding="utf-8",
)

file_handler.setFormatter(
    logging.Formatter(
        fmt=FMT,
        datefmt=DATEFMT,
    )
)

file_handler.setLevel(logging.TRACE)

coloredlogs.DEFAULT_LEVEL_STYLES["trace"] = coloredlogs.DEFAULT_LEVEL_STYLES["spam"]

coloredlogs.install(level=logging.TRACE, fmt=FMT, datefmt=DATEFMT)

# Create root logger
root: ModmailLogger = logging.getLogger()
root.setLevel(ROOT_LOG_LEVEL)
root.addHandler(file_handler)

# Silence irrelevant loggers
logging.getLogger("discord").setLevel(logging.WARNING)
logging.getLogger("websockets").setLevel(logging.ERROR)
# Set asyncio logging back to the default of INFO even if asyncio's debug mode is enabled.
logging.getLogger("asyncio").setLevel(logging.INFO)
