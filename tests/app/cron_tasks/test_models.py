import pytest

from app.cron_tasks.models import CronTask


class TestCronTask:
    @pytest.mark.parametrize(
        "command, expected",
        [
            (
                "task-single -x",
                CronTask(name="task-single", args=["-x"]),
            ),
            (
                "task-double --verbose --output=out.txt",
                CronTask(name="task-double", args=["--verbose", "--output=out.txt"]),
            ),
            (
                "task-with-spaces  --dry-run",
                CronTask(name="task-with-spaces", args=["--dry-run"]),
            ),
        ],
        ids=[
            "single_task_single_dash",
            "single_task_double_dash",
            "ignores_empty_lines_with_args",
        ],
    )
    def test_cron_task_from_command(self, command: str, expected: CronTask) -> None:
        cron_task = CronTask.from_command(command)
        assert isinstance(cron_task, CronTask)
        assert cron_task == expected

    def test_cron_task_from_command_with_invalid_argument_raises_error(self) -> None:
        invalid_command: str = 'test_task unclosed "quote'
        with pytest.raises(ValueError, match="Invalid cron command 'test_task unclosed \"quote': No closing quotation"):
            CronTask.from_command(invalid_command)

    def test_cron_task_from_empty_command_raises_error(self) -> None:
        with pytest.raises(ValueError, match="Cron command cannot be empty"):
            CronTask.from_command("")
