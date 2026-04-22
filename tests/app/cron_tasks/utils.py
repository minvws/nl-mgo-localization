from asyncio.subprocess import Process

from pytest_mock import MockerFixture, MockType


def make_process_mock(
    mocker: MockerFixture,
    pid: int = 1234,
    wait_side_effect: list[object] | None = None,
) -> MockType:
    process: MockType = mocker.AsyncMock(spec=Process)
    process.pid = pid
    process.terminate = mocker.MagicMock()
    process.kill = mocker.MagicMock()
    process.wait = mocker.AsyncMock(side_effect=wait_side_effect or [0])

    return process
