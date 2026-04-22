import asyncio
import logging
from typing import Iterable

import inject

from .models import CronTask
from .runner import CronTaskRunner

logger = logging.getLogger(__name__)


class CronTaskOrchestrator:
    """Orchestrates the execution of multiple CronTask objects as asyncio tasks."""

    @inject.autoparams("runner")
    def __init__(self, runner: CronTaskRunner) -> None:
        self.__runner = runner
        self.__tasks: list[asyncio.Task[None]] = []

    def start(self, cron_tasks: Iterable[CronTask]) -> None:
        self.__tasks = [task for task in self.__tasks if not task.done()]

        for cron_task in cron_tasks:
            task = asyncio.create_task(self.__runner.run(cron_task))
            self.__tasks.append(task)
            logger.info("Orchestrated cron task started: %s", cron_task.name)

    async def stop(self) -> None:
        """Cancel any unfinished tasks and wait for all tasks to complete."""
        if not self.__tasks:
            logger.info("No cron tasks to stop.")
            return

        logger.info("Stopping %d orchestrated cron tasks", len(self.__tasks))
        for task in self.__tasks:
            if not task.done():
                task.cancel()

        results = await asyncio.gather(*self.__tasks, return_exceptions=True)

        errors = [result for result in results if isinstance(result, Exception)]
        if errors:
            logger.error("One or more cron tasks finished with errors: %s", errors)

        self.__tasks.clear()
        logger.info("All orchestrated cron tasks have been stopped.")

    @property
    def orchestrated_tasks(self) -> list[asyncio.Task[None]]:
        """Return all currently orchestrated asyncio tasks."""
        return self.__tasks
