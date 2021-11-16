import logging
import logging.handlers

import coloredlogs

from modmail import log


LOG_FILE_SIZE = 8 * (2 ** 10) ** 2  # 8MB, discord upload limit


ROOT_LOG_LEVEL = log.get_logging_level()
FMT = "%(asctime)s %(levelname)10s %(name)15s - [%(lineno)5d]: %(message)s"
DATEFMT = "%Y/%m/%d %H:%M:%S"

logging.setLoggerClass(log.ModmailLogger)

# Set up file logging relative to the current path
log_file = log.get_log_dir() / "bot.log"
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
root: log.ModmailLogger = logging.getLogger()
root.setLevel(ROOT_LOG_LEVEL)
root.addHandler(file_handler)

# Silence irrelevant loggers
logging.getLogger("discord").setLevel(logging.WARNING)
logging.getLogger("websockets").setLevel(logging.ERROR)
# Set asyncio logging back to the default of INFO even if asyncio's debug mode is enabled.
logging.getLogger("asyncio").setLevel(logging.INFO)

# set up trace loggers
log.set_logger_levels()
