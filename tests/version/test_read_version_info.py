from json import JSONDecodeError

import inject
import pytest
from faker import Faker
from pydantic import ValidationError
from pytest_mock import MockerFixture

from app.main import create_fastapi_app
from app.version.models import VersionInfo
from app.version.services import read_version_info

invalid_version_info = [
    ("", JSONDecodeError),
    ("{}", ValidationError),
]

valid_version_info = [
    (
        '{"version": "", "git_ref": ""}',
        VersionInfo(version="", git_ref=""),
    ),
    (
        '{"version": "v0.0.0", "git_ref": "0000000000000000000000000"}',
        VersionInfo(version="v0.0.0", git_ref="0000000000000000000000000"),
    ),
]


@pytest.mark.parametrize("invalid_version_info, expected_exception", invalid_version_info)
def test_read_invalid_version_info(
    mocker: MockerFixture,
    invalid_version_info: str,
    expected_exception: type[Exception],
) -> None:
    mocker.patch("builtins.open", mocker.mock_open(read_data=invalid_version_info))

    with pytest.raises(Exception) as actual_exception:
        read_version_info()

    assert actual_exception.type == expected_exception


@pytest.mark.parametrize("valid_version_info, expected_result", valid_version_info)
def test_read_valid_version_info(
    mocker: MockerFixture,
    valid_version_info: str,
    expected_result: VersionInfo,
) -> None:
    mocker.patch("builtins.open", mocker.mock_open(read_data=valid_version_info))

    assert read_version_info() == expected_result


def test_app_version(faker: Faker) -> None:
    version = faker.numerify("v#.#.#")
    git_ref = faker.hexify("^^^^^^")

    def config_callable(binder: inject.Binder) -> None:
        binder.bind(VersionInfo, VersionInfo(version=version, git_ref=git_ref))

    inject.configure(clear=True, config=config_callable)

    assert create_fastapi_app().version == version
