import os
import pathlib
import logging
from logging.config import dictConfig
from dotenv import load_dotenv

load_dotenv()

DISCORD_API_SECRET = os.getenv("DISCORD_API_TOKEN")

BASE_DIR = pathlib.Path(__file__).parent

CMDS_DIR = BASE_DIR / "cmds"

COGS_DIR = BASE_DIR / "cogs"

LOGGING_CONFIG = {
    "version": 1,
    "disabled_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(levelname)-10s - %(asctime)s - %(module)-15s : %(message)s"
        },
        "standard": {"format": "%(levelname)-10s - %(name)-15s : %(message)s"},
    },
    "handlers": {
        "consoleDebug": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
        "consoleDebugVerbose": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "consoleWarning": {
            "level": "WARNING",
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
        "file": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": "logs/infos.log",
            "mode": "w",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "bot": {"handlers": ["consoleDebug"], "level": "INFO", "propagate": False},
        "econ": {"handlers": ["consoleDebugVerbose"], "level": "INFO", "propagate": False},
        "discord": {
            "handlers": ["consoleWarning", "file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

dictConfig(LOGGING_CONFIG)

###
# WHEN WE RETURN: WE WERE WORKING MAKING A NEW HANDLER THAT USES THE VERBOSE FORMATTER
