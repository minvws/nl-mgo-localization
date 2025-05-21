from typing import Any

import inject
import pytest
from pytest_mock import MockerFixture

from app.bindings import configure_bindings as configure_app_bindings
from app.config.factories import get_config
from app.cron.cron import CRON_COMMANDS, CronCommand, command_exists, command_get, run_command
from app.cron.zal_importer import OrganisationImportCommand
from tests.utils import clear_bindings, configure_bindings


def test_main_with_valid_command(mocker: MockerFixture) -> None:
    configure_bindings()
    cron_command = mocker.Mock(CronCommand)
    mocker.patch(
        "argparse.ArgumentParser.parse_args", return_value=mocker.MagicMock(command=OrganisationImportCommand.NAME)
    )
    mocker.patch("app.cron.cron.command_get", return_value=cron_command)

    with pytest.raises(SystemExit):
        run_command()

    assert inject.is_configured()
    cron_command.run.assert_called_once()
    clear_bindings()


def test_command_exists_with_existing_command() -> None:
    assert command_exists(OrganisationImportCommand.NAME) is True


def test_command_exists_with_non_existing_command(mocker: MockerFixture) -> None:
    cron_command = mocker.Mock(CronCommand)

    mocker.patch.dict(CRON_COMMANDS, {OrganisationImportCommand.NAME: cron_command}, clear=True)
    assert command_exists("non_existing_command") is False


def test_command_get_with_non_existing_command() -> None:
    with pytest.raises(ValueError, match="Unknown command: non_existing_command"):
        command_get("non_existing_command")


def test_cron_command_interface(mocker: MockerFixture) -> None:
    configure_bindings()

    parsed_args = mocker.MagicMock(return_value=mocker.MagicMock(command="validObject"))
    mocker.patch("argparse.ArgumentParser.parse_args", parsed_args)

    class ImporterInstance(CronCommand):
        def run(self, args: Any) -> int:
            return 0

        @staticmethod
        def init_arguments(subparser: Any) -> None:
            return None

    mocker.patch.dict(CRON_COMMANDS, {"validObject": ImporterInstance}, clear=True)

    with pytest.raises(SystemExit) as context:
        run_command()

    assert context.value.code == 0
    clear_bindings()


def test_cron_run_command_without_bindings(mocker: MockerFixture) -> None:
    parsed_args = mocker.MagicMock(return_value=mocker.MagicMock(command="validObject"))
    mocker.patch("argparse.ArgumentParser.parse_args", parsed_args)

    mock_get_config = mocker.patch("app.cron.cron.get_config")
    mock_get_config.return_value = get_config(config_file="app.conf.test")

    class ImporterInstance(CronCommand):
        def run(self, args: Any) -> int:
            return 0

        @staticmethod
        def init_arguments(subparser: Any) -> None:
            return None

    mocker.patch.dict(CRON_COMMANDS, {"validObject": ImporterInstance}, clear=True)

    mock_configure_bindings = mocker.patch("app.cron.cron.configure_bindings", side_effect=configure_app_bindings)

    with pytest.raises(SystemExit) as context:
        run_command()

    mock_configure_bindings.assert_called_once()

    assert context.value.code == 0

    clear_bindings()


def test_cron_run_help(mocker: MockerFixture) -> None:
    configure_bindings()
    mocker.patch("argparse.ArgumentParser.parse_args", mocker.MagicMock(return_value=mocker.MagicMock(command="help")))

    with pytest.raises(SystemExit) as context:
        run_command()

    assert context.value.code == 0
