from typing import Callable

import inject
from inject import Binder

from app.bindings import configure_bindings as configure_app_bindings
from app.config.factories import get_config


def configure_bindings(
    bindings_override: Callable[[Binder], Binder] | None = None,
) -> None:
    """
    Configures dependency injection bindings for the application.

    Sets up standard bindings using `app.conf.test`.
    If `bindings_override` is provided, it overrides bindings over other bindings.
    """

    def bindings_config(binder: inject.Binder) -> None:
        config = get_config(config_file="app.conf.test")
        binder.install(lambda binder: configure_app_bindings(binder, config=config))

        if bindings_override:
            bindings_override(binder)

    inject.configure(bindings_config, clear=True, allow_override=True)


def clear_bindings() -> None:
    inject.clear()
