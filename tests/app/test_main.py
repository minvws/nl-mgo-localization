import inject
import pytest
from pytest_mock import MockerFixture

from app.main import create_app, create_fastapi_app
from tests.utils import clear_bindings, configure_bindings


def test_it_calls_inject_configure_when_no_injector_configured(mocker: MockerFixture) -> None:
    clear_bindings()
    mock_get_config = mocker.patch("app.main.get_config")
    mock_inject = mocker.patch("inject.configure")

    with pytest.raises(inject.InjectorException):
        create_fastapi_app()

    mock_inject.assert_called_once()
    mock_get_config.assert_called_once_with(config_file="app.conf")


def test_it_does_not_call_inject_configure_when_injector_configured(mocker: MockerFixture) -> None:
    configure_bindings()

    mock_inject = mocker.patch("inject.configure")
    create_fastapi_app()

    mock_inject.assert_not_called()


def test_create_app_calls_get_uvicorn_params_with_app_conf(mocker: MockerFixture) -> None:
    mock_get_config = mocker.patch("app.main.get_config")
    mocker.patch("uvicorn.run")

    create_app()

    mock_get_config.assert_called_once_with(config_file="app.conf")
