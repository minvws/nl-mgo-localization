import configparser

from app.utils import root_path

from .models import Config
from .services import ConfigParser


def get_config(config_file: str) -> Config:
    config_parser: ConfigParser = ConfigParser(
        config_parser=configparser.ConfigParser(
            interpolation=configparser.ExtendedInterpolation(),
        ),
        config_path=root_path(config_file),
    )

    return config_parser.parse()
