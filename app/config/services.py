import os
from configparser import ConfigParser
from typing import TypeAlias

from .models import Config

SectionName: TypeAlias = str
ConfigValue: TypeAlias = str
SectionDict: TypeAlias = dict[str, ConfigValue]
RawConfigDict: TypeAlias = dict[SectionName, SectionDict]


class AppConfigLoader:
    DEFAULT_SECTION = "default"

    def __init__(
        self,
        config_parser: ConfigParser,
        config_path: str,
    ) -> None:
        self.config_parser = config_parser
        self.config_path = config_path

    def load_dict(self) -> RawConfigDict:
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Configuration file '{self.config_path}' not found.")

        self.config_parser.read(self.config_path)

        conf_values: RawConfigDict = {}

        for section in self.config_parser.sections():
            conf_values[section] = dict(self.config_parser[section])

        return conf_values

    def load(self) -> Config:
        return Config.model_validate(self.load_dict())
