from configparser import ConfigParser

from app.utils import root_path

from .models import Config
from .services import AppConfigLoader


def get_config(config_file: str) -> Config:
    app_config_loader = AppConfigLoader(
        config_parser=ConfigParser(),
        config_path=root_path(config_file),
    )

    return app_config_loader.load()
