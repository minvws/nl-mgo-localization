from logging import Logger, getLogger

import inject
from pytest import CaptureFixture

from app.config.models import Config
from tests.utils import clear_bindings, configure_bindings


def test_logger_binding_resolves_the_main_application_logger(capfd: CaptureFixture[str]) -> None:
    configure_bindings()

    config = inject.instance(Config)

    expected_logger: Logger = getLogger(config.logging.logger_name)
    resolved_logger: Logger = inject.instance(Logger)

    assert resolved_logger == expected_logger
    clear_bindings()


def test_logger_writes_output_to_console(capfd: CaptureFixture[str]) -> None:
    configure_bindings()
    test_message = "This is a test log message."

    logger: Logger = inject.instance(Logger)
    logger.debug(test_message)

    assert test_message in capfd.readouterr().out
