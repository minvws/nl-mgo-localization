import sys

import pytest
from pytest_mock import MockerFixture

from app.cron_tasks.dispatcher import CronTaskDispatcher
from app.cron_tasks.models import CronTask

from .utils import make_process_mock


@pytest.mark.asyncio
class TestCronTaskDispatcher:
    async def test_dispatch_successful(self, mocker: MockerFixture) -> None:
        task = CronTask(name="success_task", args=["arg1", "arg2"])
        mock_process = make_process_mock(mocker, pid=1234)

        create_mock = mocker.patch(
            "asyncio.create_subprocess_exec",
            new=mocker.AsyncMock(return_value=mock_process),
        )

        logger_mock = mocker.patch("app.cron_tasks.dispatcher.logger")

        dispatcher = CronTaskDispatcher()
        process = await dispatcher.dispatch(task)

        create_mock.assert_awaited_once_with(sys.executable, "-m", "app.cron", task.name, *task.args)
        assert process == mock_process

        logger_mock.info.assert_called_once_with(
            "Cron task subprocess started (TASK: %s, PID: %d)",
            "success_task",  # TASK
            1234,  # PID
        )

    async def test_dispatch_failure(self, mocker: MockerFixture) -> None:
        task = CronTask(name="fail_task", args=[])
        mocker.patch(
            "asyncio.create_subprocess_exec",
            new=mocker.AsyncMock(side_effect=Exception("cannot start")),
        )

        logger_mock = mocker.patch("app.cron_tasks.dispatcher.logger")

        dispatcher = CronTaskDispatcher()
        with pytest.raises(Exception, match="cannot start"):
            await dispatcher.dispatch(task)

        logger_mock.exception.assert_called_once_with("Failed to start cron subprocess (TASK: %s)", "fail_task")
