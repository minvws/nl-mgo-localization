import asyncio

import pytest
from pytest_mock import MockerFixture, MockType

from app.cron_tasks.models import CronTask
from app.cron_tasks.orchestrator import CronTaskOrchestrator
from app.cron_tasks.runner import CronTaskRunner


class TestCronTaskOrchestrator:
    @pytest.fixture
    def cron_task_runner_mock(self, mocker: MockerFixture) -> MockType:
        mock_runner: MockType = mocker.Mock(spec=CronTaskRunner)
        mock_runner.run = mocker.AsyncMock(return_value=None)
        return mock_runner

    @pytest.fixture
    def cron_task_orchestrator(self, cron_task_runner_mock: MockType) -> MockType:
        return CronTaskOrchestrator(cron_task_runner_mock)  # type: ignore

    @pytest.fixture
    def cron_tasks(self) -> list[CronTask]:
        return [
            CronTask(
                name="search-index:update",
                args=["--scrape-limit", "1"],
            ),
        ]

    @pytest.mark.asyncio
    async def test_start_creates_asyncio_tasks_for_each_cron_task(
        self,
        cron_task_orchestrator: CronTaskOrchestrator,
        cron_tasks: list[CronTask],
        cron_task_runner_mock: MockType,
    ) -> None:
        cron_task_orchestrator.start(cron_tasks)

        tasks = cron_task_orchestrator.orchestrated_tasks
        assert isinstance(tasks, list)
        assert len(tasks) == len(cron_tasks)

        for task in tasks:
            assert isinstance(task, asyncio.Task)

        await asyncio.gather(*tasks)

        for cron_task in cron_tasks:
            cron_task_runner_mock.run.assert_any_await(cron_task)

    @pytest.mark.asyncio
    async def test_stop_cancels_all_running_tasks_and_clears_list(
        self,
        mocker: MockerFixture,
        cron_tasks: list[CronTask],
    ) -> None:
        # Create a Future that never completes until we manually set it
        pending_future: asyncio.Future[None] = asyncio.Future()

        async def mock_run(_cron_task: CronTask) -> None:
            return await pending_future  # won't finish until we set result

        mock_runner = mocker.Mock(spec=CronTaskRunner)
        mock_runner.run = mocker.AsyncMock(side_effect=mock_run)

        orchestrator = CronTaskOrchestrator(mock_runner)
        orchestrator.start(cron_tasks)

        tasks = orchestrator.orchestrated_tasks
        assert len(tasks) == len(cron_tasks)

        # Call stop while tasks are still pending
        stop_task = asyncio.create_task(orchestrator.stop())

        for task in tasks:
            assert not task.done()

        # Complete the futures to allow stop() to finish
        pending_future.set_result(None)
        await stop_task

        assert len(orchestrator.orchestrated_tasks) == 0

    @pytest.mark.asyncio
    async def test_orchestrated_tasks_returns_current_active_tasks(
        self,
        cron_task_orchestrator: CronTaskOrchestrator,
        cron_tasks: list[CronTask],
    ) -> None:
        cron_task_orchestrator.start(cron_tasks)

        tasks = cron_task_orchestrator.orchestrated_tasks
        assert isinstance(tasks, list)
        assert len(tasks) == len(cron_tasks)
        for task in tasks:
            assert isinstance(task, asyncio.Task)

    @pytest.mark.asyncio
    async def test_start_replaces_finished_tasks_with_new_tasks(
        self,
        cron_task_orchestrator: CronTaskOrchestrator,
        cron_tasks: list[CronTask],
        cron_task_runner_mock: MockType,
    ) -> None:
        # First start: schedule tasks and let them finish.
        cron_task_orchestrator.start(cron_tasks)
        first_batch_tasks = list(cron_task_orchestrator.orchestrated_tasks)
        await asyncio.gather(*first_batch_tasks)

        # All tasks in the first batch should be done.
        assert all(task.done() for task in first_batch_tasks)

        # Second start: previously finished tasks should be dropped,
        # new tasks should be created (size remains equal to cron_tasks).
        cron_task_orchestrator.start(cron_tasks)
        second_batch_tasks = cron_task_orchestrator.orchestrated_tasks

        assert len(second_batch_tasks) == len(cron_tasks)
        # Ensure we do not keep references to only-done tasks.
        assert not all(task in first_batch_tasks for task in second_batch_tasks)

        await asyncio.gather(*second_batch_tasks)

        # Runner should have been called for both batches.
        assert cron_task_runner_mock.run.await_count == 2 * len(cron_tasks)

    @pytest.mark.asyncio
    async def test_stop_logs_errors_when_tasks_raise_exceptions(
        self,
        mocker: MockerFixture,
        cron_task_orchestrator: CronTaskOrchestrator,
        cron_tasks: list[CronTask],
    ) -> None:
        cron_task_orchestrator.start(cron_tasks)

        gather_mock = mocker.patch(
            "app.cron_tasks.orchestrator.asyncio.gather",
            new=mocker.AsyncMock(return_value=[Exception("boom")]),
        )
        logger_mock = mocker.patch("app.cron_tasks.orchestrator.logger")

        await cron_task_orchestrator.stop()

        gather_mock.assert_awaited_once()
        logger_mock.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_logs_info_and_exits_when_no_tasks_to_stop(
        self,
        mocker: MockerFixture,
        cron_task_orchestrator: CronTaskOrchestrator,
    ) -> None:
        cron_tasks: list[CronTask] = []

        gather_mock = mocker.patch(
            "app.cron_tasks.orchestrator.asyncio.gather",
            new=mocker.AsyncMock(return_value=[Exception("boom")]),
        )
        logger_mock = mocker.patch("app.cron_tasks.orchestrator.logger")

        cron_task_orchestrator.start(cron_tasks)
        await cron_task_orchestrator.stop()

        gather_mock.assert_not_awaited()
        logger_mock.info.assert_called_once_with("No cron tasks to stop.")
