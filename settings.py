import os
import pathlib
from logging.config import dictConfig
import logging
from dotenv import load_dotenv

load_dotenv()

DISCORD_API_SECRET = os.getenv("DISCORD_API_TOKEN")

OWNER_ID = 350393195085168650

BASE_DIR = pathlib.Path(__file__).parent

COGS_DIR = BASE_DIR / "cogs"

CHANGELOG_PATH = BASE_DIR / "changelog.txt"

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
        "discordFile": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": "logs/discord.log",
            "mode": "w",
            "formatter": "verbose",
        },
        "botFile": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": "logs/bot.log",
            "mode": "w",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "bot": {
            "handlers": ["consoleDebug", "botFile"],
            "level": "INFO",
            "propagate": False
        },
        "discord": {
            "handlers": ["consoleWarning", "discordFile"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

dictConfig(LOGGING_CONFIG)

###
# WHEN WE RETURN: WE WERE WORKING MAKING A NEW HANDLER THAT USES THE VERBOSE FORMATTER
