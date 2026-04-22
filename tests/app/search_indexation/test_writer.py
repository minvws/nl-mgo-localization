from pathlib import Path

import orjson
import pytest
from pytest_mock import MockerFixture

from app.search_indexation.writer import AtomicFileWriter


class TestAtomicFileWriter:
    def test_write_writes_real_file_and_temp_dir_exists(self, tmp_path: Path) -> None:
        temp_dir = tmp_path / "search-index"
        target_file = tmp_path / "index.json"
        writer = AtomicFileWriter()

        payload = [{"id": "1", "name": "Org 1"}, {"id": "2", "name": "Org 2"}]

        writer.write(
            orjson.dumps(payload),
            output_path=target_file,
            temp_path=temp_dir,
            prefix="search_index_",
        )

        assert temp_dir.exists() and temp_dir.is_dir()
        assert target_file.exists() and target_file.is_file()
        assert orjson.loads(target_file.read_bytes()) == payload
        assert list(temp_dir.glob("search_index_*")) == []

    def test_write_overwrites_existing_file(self, tmp_path: Path) -> None:
        temp_dir = tmp_path / "search-index"
        target_file = tmp_path / "index.json"
        target_file.write_text("old content")
        writer = AtomicFileWriter()

        payload = [{"id": "3", "name": "Org 3"}]

        writer.write(
            orjson.dumps(payload),
            output_path=target_file,
            temp_path=temp_dir,
            prefix="search_index_",
        )

        assert orjson.loads(target_file.read_bytes()) == payload

    def test_write_creates_target_directory_if_missing(self, tmp_path: Path) -> None:
        temp_dir = tmp_path / "search-index"
        nested_dir = tmp_path / "nested" / "dir"
        target_file = nested_dir / "index.json"
        writer = AtomicFileWriter()

        writer.write(b"[]", output_path=target_file, temp_path=temp_dir, prefix="search_index_")

        assert nested_dir.exists() and nested_dir.is_dir()
        assert target_file.exists() and target_file.is_file()

    def test_write_propagates_error(self, tmp_path: Path, mocker: MockerFixture) -> None:
        temp_dir = tmp_path / "temp"
        target_file = tmp_path / "index.json"
        writer = AtomicFileWriter()

        mocker.patch("app.search_indexation.writer.os.replace", side_effect=PermissionError("denied"))

        with pytest.raises(PermissionError, match="denied"):
            writer.write(b"[]", output_path=target_file, temp_path=temp_dir, prefix="search_index_")

    def test_failed_temp_file_cleanup_logs_error(self, tmp_path: Path, mocker: MockerFixture) -> None:
        temp_dir = tmp_path / "temp"
        target_file = tmp_path / "index.json"
        writer = AtomicFileWriter()

        mocker.patch("app.search_indexation.writer.os.replace", side_effect=Exception("replace failed"))
        mocker.patch("app.search_indexation.writer.os.unlink", side_effect=OSError("cannot delete"))
        mock_logger = mocker.patch("app.search_indexation.writer.logger")

        with pytest.raises(Exception, match="replace failed"):
            writer.write(b"[]", output_path=target_file, temp_path=temp_dir, prefix="search_index_")

        mock_logger.warning.assert_any_call("Failed to cleanup temporary file %s", mocker.ANY, exc_info=True)
