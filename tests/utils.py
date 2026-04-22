import logging
from typing import Tuple

import inject
from inject import BinderCallable
from pytest import LogCaptureFixture

from app.bindings import configure_bindings as configure_app_bindings
from app.config.factories import get_config
from app.config.models import Config


def configure_bindings(
    bindings_override: BinderCallable | None = None,
    config: Config | None = None,
) -> None:
    """
    Configures dependency injection bindings for the application.

    Sets up standard bindings using `app.conf.test`.
    If `bindings_override` is provided, it overrides bindings over other bindings.
    """

    def bindings_config(binder: inject.Binder) -> None:
        binder.install(
            lambda binder: configure_app_bindings(
                binder=binder,
                config=config or load_config(),
            )
        )

        if bindings_override:
            binder.install(bindings_override)

    inject.configure(bindings_config, clear=True, allow_override=True)


def clear_bindings() -> None:
    inject.clear()


def assert_captured_logs(caplog: LogCaptureFixture, expected: list[Tuple[str, int]]) -> None:
    """
    Helper to assert that each expected message appears in logs with correct severity.

    Usage:
        def test_example(caplog: LogCaptureFixture):
            expected_logs = [
                ("Process completed successfully", logging.INFO),
                ("Warning: something minor happened", logging.WARNING),
            ]
            assert_captured_logs(caplog, expected_logs)
    """
    for msg, level in expected:
        assert any(msg in record.message and record.levelno == level for record in caplog.records), (
            f"Expected log '{msg}' with level {logging.getLevelName(level)}"
        )


def load_config() -> Config:
    return get_config(config_file="app.conf.test")
