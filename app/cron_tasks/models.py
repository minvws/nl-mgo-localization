import shlex
from dataclasses import dataclass
from typing import Sequence

from typing_extensions import Self


@dataclass(frozen=True)
class CronTask:
    """Represents a task that runs via `python -m app.cron <name>`."""

    name: str
    args: Sequence[str] = ()

    @classmethod
    def from_command(cls, command: str) -> Self:
        try:
            parts = shlex.split(command)
        except ValueError as exc:
            raise ValueError(f"Invalid cron command {command!r}: {exc}") from exc

        if not parts:
            raise ValueError("Cron command cannot be empty")

        return cls(name=parts[0], args=parts[1:])


@dataclass(frozen=True)
class CronCommands:
    commands: list[str]

    def to_cron_tasks(self) -> list[CronTask]:
        return [CronTask.from_command(command) for command in self.commands]
