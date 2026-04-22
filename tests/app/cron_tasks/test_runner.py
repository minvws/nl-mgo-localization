import asyncio
from asyncio.subprocess import Process

import pytest
from pytest_mock import MockerFixture

from app.cron_tasks.dispatcher import CronTaskDispatcher
from app.cron_tasks.models import CronTask
from app.cron_tasks.runner import CronTaskRunner
from app.cron_tasks.supervisor import CronTaskSupervisor


@pytest.mark.asyncio
class TestCronTaskRunner:
    async def test_run_executes_dispatch_and_supervise(self, mocker: MockerFixture) -> None:
        task = CronTask(name="runner_task", args=["a"])
        mock_process = mocker.Mock(spec=Process)

        dispatcher = mocker.AsyncMock(spec=CronTaskDispatcher)
        dispatcher.dispatch.return_value = mock_process

        supervisor = mocker.AsyncMock(spec=CronTaskSupervisor)
        runner = CronTaskRunner(dispatcher, supervisor)

        await runner.run(task)

        dispatcher.dispatch.assert_awaited_once_with(task)
        supervisor.supervise.assert_awaited_once_with(task, mock_process)

    async def test_run_dispatcher_raises_exception(self, mocker: MockerFixture) -> None:
        task = CronTask(name="fail_dispatch", args=[])

        dispatcher = mocker.AsyncMock(spec=CronTaskDispatcher)
        dispatcher.dispatch.side_effect = Exception("dispatch failed")

        supervisor = mocker.AsyncMock(spec=CronTaskSupervisor)
        runner = CronTaskRunner(dispatcher, supervisor)

        with pytest.raises(Exception, match="dispatch failed"):
            await runner.run(task)

        dispatcher.dispatch.assert_awaited_once_with(task)
        supervisor.supervise.assert_not_called()

    async def test_run_supervise_propagates_cancelled_error(self, mocker: MockerFixture) -> None:
        task = CronTask(name="cancel_task", args=[])

        mock_process = mocker.Mock()
        dispatcher = mocker.AsyncMock(spec=CronTaskDispatcher)
        dispatcher.dispatch.return_value = mock_process

        supervisor = mocker.AsyncMock(spec=CronTaskSupervisor)
        supervisor.supervise.side_effect = asyncio.CancelledError

        runner = CronTaskRunner(dispatcher, supervisor)

        with pytest.raises(asyncio.CancelledError):
            await runner.run(task)

        dispatcher.dispatch.assert_awaited_once_with(task)
        supervisor.supervise.assert_awaited_once_with(task, mock_process)
