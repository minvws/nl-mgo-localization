import inject

from .dispatcher import CronTaskDispatcher
from .models import CronTask
from .supervisor import CronTaskSupervisor


class CronTaskRunner:
    """Executes a CronTask as a subprocess, handling its dispatch and supervision."""

    @inject.autoparams("dispatcher", "supervisor")
    def __init__(self, dispatcher: CronTaskDispatcher, supervisor: CronTaskSupervisor) -> None:
        self.__dispatcher = dispatcher
        self.__supervisor = supervisor

    async def run(self, task: CronTask) -> None:
        process = await self.__dispatcher.dispatch(task)
        await self.__supervisor.supervise(task, process)
