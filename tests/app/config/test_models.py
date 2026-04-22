from configparser import ConfigParser
from typing import Any

import pytest
from pydantic import ValidationError

from app.config.models import Config
from app.config.services import AppConfigLoader
from app.utils import root_path


class TestConfig:
    @staticmethod
    def full_config_dict() -> dict[str, Any]:  # type: ignore[explicit-any]
        config_parser = AppConfigLoader(
            config_parser=ConfigParser(),
            config_path=root_path("app.conf.test"),
        )
        return config_parser.load_dict()

    @pytest.mark.parametrize(
        "raw_tasks, expected",
        [
            (
                """
                task1
                task2 -a value
                task3 --flag --option=value
                """,
                ["task1", "task2 -a value", "task3 --flag --option=value"],
            ),
            (
                """task-with-spaces  --dry-run""",
                ["task-with-spaces  --dry-run"],
            ),
            ("", []),
        ],
        ids=[
            "multiple_tasks_with_dash_args",
            "task_with_spaces",
            "empty_string_returns_empty_list",
        ],
    )
    def test_parse_on_startup_cron_commands(self, raw_tasks: str, expected: list[str]) -> None:
        config_dict = self.full_config_dict()
        config_dict["app"]["on_startup_cron_commands"] = raw_tasks

        config = Config.model_validate(config_dict)

        assert config.app.on_startup_cron_commands == expected

    def test_requires_mock_base_url(self) -> None:
        config_dict = self.full_config_dict()
        config_dict["app"].pop("mock_base_url")

        with pytest.raises(ValidationError):
            Config.model_validate(config_dict)
