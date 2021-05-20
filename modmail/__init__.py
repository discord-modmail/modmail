import logging
import logging.handlers
import os
from pathlib import Path

import coloredlogs

from .log import ModmailLogger

logging.TRACE = 5
logging.NOTICE = 25
logging.addLevelName(logging.TRACE, "TRACE")
logging.addLevelName(logging.NOTICE, "NOTICE")

LOG_LEVEL = 20


logging.setLoggerClass(ModmailLogger)

# Set up file logging
log_dir = Path("./logs")
log_file = log_dir / "bot.log"
os.makedirs(log_dir, exist_ok=True)

# Default formats
fmt = "%(asctime)s %(levelname)s %(name)s - [%(lineno)d]: %(message)s"
datefmt="%Y/%m/%d %H:%M:%S"

colored_formatter = coloredlogs.ColoredFormatter(
    fmt=fmt,
    datefmt=datefmt,
)
formatter = logging.Formatter(
    fmt=fmt,
    datefmt=datefmt,
)


# Console handler prints to terminal
# console_handler = logging.StreamHandler()

# console_handler.setFormatter(colored_formatter)
# console_handler.setLevel(logging.TRACE)


# file handler
file_handler = logging.handlers.RotatingFileHandler(
    log_file, maxBytes=5 * (2 ** 12), backupCount=5, encoding="utf-8",
)
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.TRACE)


# Silence irrelevant loggers
logging.getLogger("discord").setLevel(logging.WARNING)
logging.getLogger("websockets").setLevel(logging.ERROR)
logging.getLogger("asyncio").setLevel(logging.INFO)

coloredlogs.install(
    level=LOG_LEVEL,
    fmt=fmt,
    datefmt=datefmt,
)

root: ModmailLogger = logging.getLogger()
root.addHandler(file_handler)
# Set back to the default of INFO even if asyncio's debug mode is enabled.
logging.getLogger("asyncio").setLevel(logging.INFO)

root.debug("Logging initialization complete")
