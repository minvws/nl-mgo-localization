import io

from pytest_mock import MockerFixture

from app.cron.utils import print_progress_bar


def test_print_progress_bar(mocker: MockerFixture) -> None:
    mock_stdout = io.StringIO()
    mocker.patch("sys.stdout", new=mock_stdout)

    print_progress_bar(0, 100)
    assert "\rProgress: [----------------------------------------] 0/100" in mock_stdout.getvalue()

    mock_stdout.truncate(0)
    mock_stdout.seek(0)
    print_progress_bar(50, 100)
    assert "\rProgress: [####################--------------------] 50/100" in mock_stdout.getvalue()

    mock_stdout.truncate(0)
    mock_stdout.seek(0)
    print_progress_bar(100, 100)
    assert "\rProgress: [########################################] 100/100" in mock_stdout.getvalue()

    mock_stdout.truncate(0)
    mock_stdout.seek(0)
    print_progress_bar(0, 0)
    assert "\rProgress: [########################################] 1/1" in mock_stdout.getvalue()
