import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from faker import Faker
from pytest_mock import MockerFixture

from app.cron.commands.normalization_command import NormalizationCommand
from app.normalization.services import GzipCompressionSizeChecker


def make_minimal_bundle(num_orgs: int = 2) -> dict[str, Any]:  # type: ignore[explicit-any]
    entries = []
    for i in range(num_orgs):
        entries.append(
            {
                "resource": {
                    "resourceType": "Organization",
                    "id": f"org-{i}",
                    "name": f"Org {i}",
                }
            }
        )
    return {"resourceType": "Bundle", "type": "collection", "entry": entries}


def write_json(path: Path, data: Any) -> None:  # type: ignore[explicit-any]
    path.write_text(json.dumps(data), encoding="utf-8")


@pytest.mark.usefixtures("test_client")
class TestNormalizationCommand:
    def test_run_without_output_file_uses_default_name_and_handles_gzip_none(
        self,
        tmp_path: Path,
        mocker: MockerFixture,
    ) -> None:
        mock_gzip_checker = mocker.Mock(spec=GzipCompressionSizeChecker)
        input_path = tmp_path / "bundle.json"
        out_dir = tmp_path / "out"
        args = SimpleNamespace(input_file=str(input_path), output_folder=str(out_dir), output_file=None)
        cmd = NormalizationCommand(gzip_checker=mock_gzip_checker)

        write_json(input_path, make_minimal_bundle(2))
        out_dir.mkdir(parents=True, exist_ok=True)

        mock_gzip_checker.get_size_in_kb.return_value = None

        result = cmd.run(args)

        assert result == 0
        assert out_dir.exists() and out_dir.is_dir()
        files = list(out_dir.iterdir())
        assert len(files) == 1
        content = json.loads(files[0].read_text(encoding="utf-8"))
        assert isinstance(content, list)
        assert len(content) == 2

    def test_run_with_relative_output_file_and_small_gzip(
        self,
        tmp_path: Path,
        mocker: MockerFixture,
    ) -> None:
        mock_gzip_checker = mocker.Mock(spec=GzipCompressionSizeChecker)
        input_path = tmp_path / "bundle.json"
        out_dir = tmp_path / "nested" / "folder"
        args = SimpleNamespace(input_file=str(input_path), output_folder=str(out_dir), output_file="out.json")
        cmd = NormalizationCommand(gzip_checker=mock_gzip_checker)

        write_json(input_path, make_minimal_bundle(2))
        out_dir.mkdir(parents=True, exist_ok=True)

        mock_gzip_checker.get_size_in_kb.return_value = 500.0

        result = cmd.run(args)

        assert result == 0
        out_file = out_dir / "out.json"
        assert out_file.exists()
        content = json.loads(out_file.read_text(encoding="utf-8"))
        assert isinstance(content, list)
        assert len(content) == 2

    def test_run_with_absolute_output_file_and_large_gzip(
        self,
        tmp_path: Path,
        mocker: MockerFixture,
    ) -> None:
        mock_gzip_checker = mocker.Mock(spec=GzipCompressionSizeChecker)
        input_path = tmp_path / "bundle.json"
        out_dir = tmp_path / "any"
        out_file = tmp_path / "abs.json"
        args = SimpleNamespace(input_file=str(input_path), output_folder=str(out_dir), output_file=str(out_file))
        cmd = NormalizationCommand(gzip_checker=mock_gzip_checker)

        write_json(input_path, make_minimal_bundle(2))
        out_dir.mkdir(parents=True, exist_ok=True)

        mock_gzip_checker.get_size_in_kb.return_value = 2048.0

        result = cmd.run(args)

        assert result == 0
        assert out_file.exists()
        content = json.loads(out_file.read_text(encoding="utf-8"))
        assert isinstance(content, list)
        assert len(content) == 2

    def test_raises_file_not_found_when_output_directory_missing(
        self,
        tmp_path: Path,
    ) -> None:
        input_path = tmp_path / "bundle.json"
        missing_dir = tmp_path / "missing"
        args = SimpleNamespace(input_file=str(input_path), output_folder=str(missing_dir), output_file=None)

        write_json(input_path, make_minimal_bundle(1))

        with pytest.raises(FileNotFoundError):
            NormalizationCommand().run(args)

    def test_output_folder_when_not_provided_uses_config_path(
        self,
        tmp_path: Path,
        mocker: MockerFixture,
        faker: Faker,
    ) -> None:
        input_path = tmp_path / "bundle.json"
        custom_output_file = faker.file_name()
        args = SimpleNamespace(input_file=str(input_path), output_folder=None, output_file=custom_output_file)

        def mock_write_output_and_log(*args: Any, **_: Any) -> None:  # type: ignore[explicit-any]
            assert args[0].endswith(custom_output_file)

        write_json(input_path, make_minimal_bundle(1))

        mocker.patch(
            "app.cron.commands.normalization_command.NormalizationCommand._write_output_and_log",
            side_effect=mock_write_output_and_log,
        )
        mocker.patch(
            "app.cron.commands.normalization_command.NormalizationCommand._output_directory_exists", return_value=None
        )

        result = NormalizationCommand().run(args)

        assert result == 0

    def test_output_folder_when_override_provided_uses_override(
        self,
        tmp_path: Path,
        mocker: MockerFixture,
        faker: Faker,
    ) -> None:
        input_path = tmp_path / "bundle.json"
        custom_output_folder = faker.file_path()
        custom_output_file = faker.file_name()
        args = SimpleNamespace(
            input_file=str(input_path), output_folder=custom_output_folder, output_file=custom_output_file
        )

        def mock_write_output_and_log(*args: Any, **_: Any) -> None:  # type: ignore[explicit-any]
            assert args[0] == custom_output_folder + "/" + custom_output_file

        write_json(input_path, make_minimal_bundle(1))

        mocker.patch(
            "app.cron.commands.normalization_command.NormalizationCommand._write_output_and_log",
            side_effect=mock_write_output_and_log,
        )
        mocker.patch(
            "app.cron.commands.normalization_command.NormalizationCommand._output_directory_exists", return_value=None
        )

        result = NormalizationCommand().run(args)

        assert result == 0
