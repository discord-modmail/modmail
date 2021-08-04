import logging
import logging.handlers
from pathlib import Path
from typing import TYPE_CHECKING

import coloredlogs

from .log import ModmailLogger

if TYPE_CHECKING:
    from modmail.bot import ModmailBot

logging.TRACE = 5
logging.NOTICE = 25
logging.addLevelName(logging.TRACE, "TRACE")
logging.addLevelName(logging.NOTICE, "NOTICE")

LOG_LEVEL = 20
fmt = "%(asctime)s %(levelname)10s %(name)15s - [%(lineno)5d]: %(message)s"
datefmt = "%Y/%m/%d %H:%M:%S"

logging.setLoggerClass(ModmailLogger)

# Set up file logging
log_file = Path("./logs/bot.log")
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
        fmt=fmt,
        datefmt=datefmt,
    )
)

file_handler.setLevel(logging.TRACE)

coloredlogs.install(
    level=LOG_LEVEL,
    fmt=fmt,
    datefmt=datefmt,
)

# Create root logger
root: ModmailLogger = logging.getLogger()
root.addHandler(file_handler)

# Silence irrelevant loggers
logging.getLogger("discord").setLevel(logging.WARNING)
logging.getLogger("websockets").setLevel(logging.ERROR)
# Set asyncio logging back to the default of INFO even if asyncio's debug mode is enabled.
logging.getLogger("asyncio").setLevel(logging.INFO)

root.debug("Logging initialization complete")

instance: "ModmailBot" = None  # Global ModmailBot instance.
