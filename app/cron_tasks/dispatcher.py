import asyncio
import logging
import sys
from asyncio.subprocess import Process

from .models import CronTask

logger = logging.getLogger(__name__)


class CronTaskDispatcher:
    async def dispatch(self, task: CronTask) -> Process:
        """Start a cron task subprocess and return the process handle."""
        command = [sys.executable, "-m", "app.cron", task.name, *task.args]

        try:
            process = await asyncio.create_subprocess_exec(*command)
        except Exception:
            logger.exception("Failed to start cron subprocess (TASK: %s)", task.name)
            raise

        logger.info("Cron task subprocess started (TASK: %s, PID: %d)", task.name, process.pid)
        return process
