import inject
import pytest
from fastapi import FastAPI
from pytest_mock import MockerFixture

from app.config.models import Config
from app.cron_tasks import CronTask, CronTaskOrchestrator
from app.main import create_fastapi_app, lifespan, run_uvicorn
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


def test_run_uvicorn_calls_get_uvicorn_params_with_app_conf(mocker: MockerFixture) -> None:
    mock_get_config = mocker.patch("app.main.get_config")
    mocker.patch("uvicorn.run")

    run_uvicorn()

    mock_get_config.assert_called_once_with(config_file="app.conf")


@pytest.mark.asyncio
async def test_lifespan_starts_cron_tasks_and_sets_app_state(mocker: MockerFixture, config: Config) -> None:
    config.app.on_startup_cron_commands = ["search-index:update --scrape-limit 1"]

    orchestrator = mocker.Mock(spec=CronTaskOrchestrator)

    orchestrated_tasks = [mocker.Mock()]
    orchestrator.orchestrated_tasks = mocker.PropertyMock(return_value=orchestrated_tasks)

    configure_bindings(lambda binder: binder.bind(CronTaskOrchestrator, orchestrator), config=config)

    app = FastAPI()
    async with lifespan(app):
        pass

    expected_tasks = [CronTask("search-index:update", ["--scrape-limit", "1"])]

    orchestrator.start.assert_called_once_with(expected_tasks)
    assert app.state.cron_tasks is orchestrator.orchestrated_tasks


@pytest.mark.asyncio
async def test_lifespan_stops_cron_tasks_on_exit(mocker: MockerFixture, config: Config) -> None:
    config.app.on_startup_cron_commands = ["search-index:update --scrape-limit 1"]

    orchestrator = mocker.Mock(spec=CronTaskOrchestrator)
    configure_bindings(lambda binder: binder.bind(CronTaskOrchestrator, orchestrator), config=config)

    async with lifespan(FastAPI()):
        pass

    orchestrator.stop.assert_awaited_once()
