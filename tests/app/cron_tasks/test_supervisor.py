from asyncio import CancelledError, TimeoutError

import pytest
from pytest_mock import MockerFixture

from app.cron_tasks.models import CronTask
from app.cron_tasks.supervisor import CronTaskSupervisor

from .utils import make_process_mock


@pytest.mark.asyncio
class TestCronTaskSupervisor:
    async def test_supervise_successful(self, mocker: MockerFixture) -> None:
        task = CronTask(name="success_task", args=[])
        process = make_process_mock(mocker, pid=1234)

        logger_mock = mocker.patch("app.cron_tasks.supervisor.logger")
        supervisor = CronTaskSupervisor()
        await supervisor.supervise(task, process)

        process.wait.assert_awaited_once()
        logger_mock.info.assert_called_once_with(
            "Cron task subprocess finished (TASK: %s, PID: %d, EXIT: %d)",
            "success_task",  # TASK
            1234,  # PID
            0,  # EXIT
        )

    async def test_supervise_non_zero_exit(self, mocker: MockerFixture) -> None:
        task = CronTask(name="error_task", args=[])
        process = make_process_mock(mocker, pid=5678, wait_side_effect=[1])

        logger_mock = mocker.patch("app.cron_tasks.supervisor.logger")
        supervisor = CronTaskSupervisor()
        await supervisor.supervise(task, process)

        process.wait.assert_awaited_once()
        logger_mock.info.assert_called_once_with(
            "Cron task subprocess finished (TASK: %s, PID: %d, EXIT: %d)",
            "error_task",  # TASK
            5678,  # PID
            1,  # EXIT
        )
        logger_mock.error.assert_called_once_with("Cron task failed (TASK: %s, EXIT: %d)", "error_task", 1)

    async def test_supervise_cancelled(self, mocker: MockerFixture) -> None:
        task = CronTask(name="cancel_task", args=[])
        process = make_process_mock(mocker, pid=9999, wait_side_effect=[CancelledError, TimeoutError, 0])

        logger_mock = mocker.patch("app.cron_tasks.supervisor.logger")
        supervisor = CronTaskSupervisor()

        with pytest.raises(CancelledError):
            await supervisor.supervise(task, process)

        process.terminate.assert_called_once()
        process.kill.assert_called_once()

        logger_mock.info.assert_called_once_with(
            "Cron task was cancelled, terminating process (TASK: %s, PID: %d)",
            "cancel_task",  # TASK
            9999,  # PID
        )
        logger_mock.warning.assert_called_once_with(
            "Cron task did not terminate gracefully, killing process (TASK: %s, PID: %d)",
            "cancel_task",  # TASK
            9999,  # PID
        )
