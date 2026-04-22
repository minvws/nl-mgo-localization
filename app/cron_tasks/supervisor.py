import asyncio
import logging
from asyncio import CancelledError, TimeoutError
from asyncio.subprocess import Process

from .models import CronTask

logger = logging.getLogger(__name__)


class CronTaskSupervisor:
    """Responsible for supervising cron task subprocesses: monitoring, logging, and cancellation."""

    async def supervise(self, task: CronTask, process: Process) -> None:
        try:
            returncode = await process.wait()
            logger.info(
                "Cron task subprocess finished (TASK: %s, PID: %d, EXIT: %d)",
                task.name,
                process.pid,
                returncode,
            )
            if returncode != 0:
                logger.error("Cron task failed (TASK: %s, EXIT: %d)", task.name, returncode)

        except CancelledError:
            await self.__cancel(task, process)
            raise

    async def __cancel(self, task: CronTask, process: Process) -> None:
        logger.info(
            "Cron task was cancelled, terminating process (TASK: %s, PID: %d)",
            task.name,
            process.pid,
        )

        try:
            process.terminate()
            await asyncio.wait_for(process.wait(), timeout=5)
        except TimeoutError:
            logger.warning(
                "Cron task did not terminate gracefully, killing process (TASK: %s, PID: %d)",
                task.name,
                process.pid,
            )
            process.kill()
            await process.wait()
