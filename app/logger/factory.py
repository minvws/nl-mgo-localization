import logging.config
from logging import Logger

from app.config.models import Config


def create_logger(config: Config) -> Logger:
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "uvicorn": {  # rewrites uvicorn.error to uvicorn
                    "format": "%(asctime)s - uvicorn - %(levelname)s - %(message)s"
                },
                "brief": {"format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"},
                "precise": {"format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(pathname)s:%(lineno)s"},
            },
            "handlers": {
                "uvicorn": {
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                    "formatter": "uvicorn",
                    "level": config.logging.log_level,
                },
                "console.brief": {
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                    "formatter": "brief",
                    "level": config.logging.log_level,
                },
                "console.precise": {
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                    "formatter": "precise",
                    "level": config.logging.log_level,
                },
            },
            "root": {
                "level": config.logging.log_level,
                "handlers": ["console.brief"],
            },
            "loggers": {
                "uvicorn.error": {
                    "level": "INFO",
                    "handlers": ["uvicorn"],
                    "propagate": False,
                },
                "uvicorn.access": {
                    "level": "INFO",
                    "handlers": ["console.brief"],
                    "propagate": False,
                },
                config.logging.logger_name: {
                    "handlers": ["console.precise"],
                    "level": config.logging.log_level,
                    "propagate": False,
                },
            },
        }
    )

    logger = logging.getLogger(config.logging.logger_name)
    return logger
