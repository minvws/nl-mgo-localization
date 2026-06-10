from collections.abc import Iterator
from pathlib import Path
from typing import Self

import orjson
import pytest
from pytest_mock import MockerFixture

from app.db.models import Endpoint
from app.normalization.models import NormalizedOrganization
from app.search_indexation.repositories import (
    EncryptedEndpointsFileRepository,
    FilesystemSearchIndexStreamRepository,
    MockEndpointsRepository,
    MockOrganizationMergerDecorator,
    MockOrganizationRepository,
    SearchIndexStreamRepository,
)
from app.search_indexation.writer import AtomicFileWriter


class FailingIterator(Iterator[NormalizedOrganization]):
    def __iter__(self) -> Self:
        return self

    def __next__(self) -> NormalizedOrganization:
        raise RuntimeError("stream error")


class TestFilesystemSearchIndexStreamRepository:
    def test_save_writes_json_array_to_output_path(
        self,
        tmp_path: Path,
    ) -> None:
        temp_dir = tmp_path / "tmp"
        output_file = tmp_path / "index.json"
        entries: list[NormalizedOrganization] = [
            {"id": "1", "name": "Org 1"},
            {"id": "2", "name": "Org 2"},
        ]

        repo = FilesystemSearchIndexStreamRepository(output_path=output_file, temp_path=temp_dir)
        repo.save(iter(entries))

        assert output_file.exists()
        result = orjson.loads(output_file.read_bytes())
        assert result == entries

    def test_save_replaces_existing_file(
        self,
        tmp_path: Path,
    ) -> None:
        temp_dir = tmp_path / "tmp"
        output_file = tmp_path / "index.json"
        output_file.write_bytes(b"old content")
        entries: list[NormalizedOrganization] = [{"id": "1", "name": "New"}]

        repo = FilesystemSearchIndexStreamRepository(output_path=output_file, temp_path=temp_dir)
        repo.save(iter(entries))

        result = orjson.loads(output_file.read_bytes())
        assert result == entries

    def test_save_writes_empty_array_when_no_entries(
        self,
        tmp_path: Path,
    ) -> None:
        temp_dir = tmp_path / "tmp"
        output_file = tmp_path / "index.json"

        repo = FilesystemSearchIndexStreamRepository(output_path=output_file, temp_path=temp_dir)
        repo.save(iter([]))

        result = orjson.loads(output_file.read_bytes())
        assert result == []

    def test_save_propagates_exception(
        self,
        tmp_path: Path,
    ) -> None:
        temp_dir = tmp_path / "tmp"
        output_file = tmp_path / "index.json"

        repo = FilesystemSearchIndexStreamRepository(output_path=output_file, temp_path=temp_dir)

        with pytest.raises(RuntimeError, match="stream error"):
            repo.save(FailingIterator())

    def test_save_cleans_up_temp_file_on_error(
        self,
        tmp_path: Path,
    ) -> None:
        temp_dir = tmp_path / "tmp"
        output_file = tmp_path / "index.json"

        repo = FilesystemSearchIndexStreamRepository(output_path=output_file, temp_path=temp_dir)

        with pytest.raises(RuntimeError):
            repo.save(FailingIterator())

        leftover = list(temp_dir.glob("search_index_*")) if temp_dir.exists() else []
        assert leftover == []


class TestMockOrganizationMergerDecorator:
    def test_save_appends_mock_orgs_not_in_main_stream(
        self,
        mocker: MockerFixture,
    ) -> None:
        inner = mocker.Mock(spec=SearchIndexStreamRepository)
        consumed: list[NormalizedOrganization] = []
        inner.save.side_effect = lambda orgs: consumed.extend(orgs)

        mock_org_repo = mocker.Mock(spec=MockOrganizationRepository)
        mock_org_repo.read_mock_organizations.return_value = [
            {"id": "mock-1", "name": "Mock Org"},
        ]

        repo = MockOrganizationMergerDecorator(
            decorated=inner,
            mock_organizations_repository=mock_org_repo,
        )
        repo.save(iter([{"id": "real-1", "name": "Real Org"}]))

        assert consumed == [
            {"id": "real-1", "name": "Real Org"},
            {"id": "mock-1", "name": "Mock Org"},
        ]

    def test_save_when_id_already_in_stream_raises_exception(
        self,
        mocker: MockerFixture,
    ) -> None:
        inner = mocker.Mock(spec=SearchIndexStreamRepository)
        consumed: list[NormalizedOrganization] = []
        expected_message = "Duplicate organization id between normalized organizations and mock organizations: dupe-id"
        inner.save.side_effect = lambda orgs: consumed.extend(orgs)

        mock_org_repo = mocker.Mock(spec=MockOrganizationRepository)
        mock_org_repo.read_mock_organizations.return_value = [
            {"id": "dupe-id", "name": "Mock Duplicate"},
        ]

        repo = MockOrganizationMergerDecorator(
            decorated=inner,
            mock_organizations_repository=mock_org_repo,
        )

        with pytest.raises(RuntimeError, match=expected_message):
            repo.save(iter([{"id": "dupe-id", "name": "Real Org"}]))


class TestEncryptedEndpointsFileRepository:
    def test_save_calls_writer_with_expected_arguments(
        self,
        tmp_path: Path,
        mocker: MockerFixture,
    ) -> None:
        temp_dir = tmp_path / "encrypted-endpoints"
        target_file = tmp_path / "endpoints.json"
        file_writer = mocker.Mock(spec=AtomicFileWriter)
        endpoints = {1: "encrypted-url-1", 2: "encrypted-url-2"}

        repo = EncryptedEndpointsFileRepository(output_path=target_file, temp_path=temp_dir, file_writer=file_writer)
        repo.save(endpoints)

        file_writer.write.assert_called_once_with(
            orjson.dumps(endpoints, option=orjson.OPT_NON_STR_KEYS),
            output_path=target_file,
            temp_path=temp_dir,
            prefix="encrypted_endpoints_",
        )

    def test_save_propagates_writer_exception(
        self,
        tmp_path: Path,
        mocker: MockerFixture,
    ) -> None:
        temp_dir = tmp_path / "encrypted-endpoints"
        target_file = tmp_path / "endpoints.json"
        file_writer = mocker.Mock(spec=AtomicFileWriter)
        file_writer.write.side_effect = RuntimeError("writer failed")

        repo = EncryptedEndpointsFileRepository(output_path=target_file, temp_path=temp_dir, file_writer=file_writer)

        with pytest.raises(RuntimeError, match="writer failed"):
            repo.save({1: "encrypted-url-1"})


class TestMockOrganizationsFileRepo:
    def test_get_unique_mock_endpoints_parses_string_keys_to_int(self, tmp_path: Path) -> None:
        mock_file = tmp_path / "mock-addressing.json"
        mock_file.write_bytes(orjson.dumps({"9999999990000001": "https://mock.example/resource"}))

        repo = MockOrganizationRepository(
            mock_addressing_path=mock_file, mock_organizations_path=tmp_path / "mock-organizations.json"
        )

        assert repo.get_unique_mock_endpoints() == {9999999990000001: "https://mock.example/resource"}

    def test_get_unique_mock_endpoints_rejects_colliding_numeric_ids(self, tmp_path: Path) -> None:
        mock_file = tmp_path / "mock-addressing.json"
        mock_file.write_bytes(orjson.dumps({"1": "https://a.example", "01": "https://b.example"}))

        repo = MockOrganizationRepository(
            mock_addressing_path=mock_file, mock_organizations_path=tmp_path / "mock-organizations.json"
        )

        with pytest.raises(RuntimeError, match="Duplicate endpoint id"):
            repo.get_unique_mock_endpoints()

    def test_read_mock_organizations_requires_id_field(self, tmp_path: Path) -> None:
        mock_file = tmp_path / "mock-organizations.json"
        mock_file.write_bytes(orjson.dumps([{"name": "Missing id"}]))

        repo = MockOrganizationRepository(
            mock_addressing_path=tmp_path / "mock-addressing.json", mock_organizations_path=mock_file
        )

        with pytest.raises(ValueError, match="missing 'id' field"):
            repo.read_mock_organizations()

    def test_read_mock_organizations_raises_when_file_not_found(self, tmp_path: Path) -> None:
        repo = MockOrganizationRepository(
            mock_organizations_path=tmp_path / "nonexistent.json",
            mock_addressing_path=tmp_path / "mock-addressing.json",
        )

        with pytest.raises(FileNotFoundError, match="Mock organizations file not found"):
            repo.read_mock_organizations()

    def test_read_mock_organizations_raises_when_payload_not_list(self, tmp_path: Path) -> None:
        mock_file = tmp_path / "mock-organizations.json"
        mock_file.write_bytes(orjson.dumps({"id": "not-a-list"}))

        repo = MockOrganizationRepository(
            mock_organizations_path=mock_file,
            mock_addressing_path=tmp_path / "mock-addressing.json",
        )

        with pytest.raises(ValueError, match="Expected mock organizations JSON array"):
            repo.read_mock_organizations()

    def test_read_mock_organizations_returns_valid_list(self, tmp_path: Path) -> None:
        mock_file = tmp_path / "mock-organizations.json"
        orgs = [{"id": "agb:1", "name": "Org 1"}, {"id": "agb:2", "name": "Org 2"}]
        mock_file.write_bytes(orjson.dumps(orgs))

        repo = MockOrganizationRepository(
            mock_organizations_path=mock_file,
            mock_addressing_path=tmp_path / "mock-addressing.json",
        )

        assert repo.read_mock_organizations() == orgs

    def test_get_unique_mock_endpoints_raises_when_file_not_found(self, tmp_path: Path) -> None:
        repo = MockOrganizationRepository(
            mock_organizations_path=tmp_path / "mock-organizations.json",
            mock_addressing_path=tmp_path / "nonexistent.json",
        )

        with pytest.raises(FileNotFoundError, match="Mock addressing file not found"):
            repo.get_unique_mock_endpoints()

    def test_get_unique_mock_endpoints_raises_when_payload_not_dict(self, tmp_path: Path) -> None:
        mock_file = tmp_path / "mock-addressing.json"
        mock_file.write_bytes(orjson.dumps(["not-a-dict"]))

        repo = MockOrganizationRepository(
            mock_organizations_path=tmp_path / "mock-organizations.json",
            mock_addressing_path=mock_file,
        )

        with pytest.raises(ValueError, match="Expected mock addressing JSON object"):
            repo.get_unique_mock_endpoints()

    def test_get_unique_mock_endpoints_raises_when_url_is_empty(self, tmp_path: Path) -> None:
        mock_file = tmp_path / "mock-addressing.json"
        mock_file.write_bytes(orjson.dumps({"1": ""}))

        repo = MockOrganizationRepository(
            mock_organizations_path=tmp_path / "mock-organizations.json",
            mock_addressing_path=mock_file,
        )

        with pytest.raises(RuntimeError, match="Invalid mock endpoint URL for id"):
            repo.get_unique_mock_endpoints()


class TestMockEndpointsRepository:
    def test_find_all_merges_endpoints_and_replaces_dva_mock_placeholder(
        self,
        mocker: MockerFixture,
    ) -> None:

        endpoint_repository = mocker.Mock()
        endpoint_repository.find_all.return_value = [
            Endpoint(id=1, url="https://db.example/auth"),
        ]

        mock_organization_repository = mocker.Mock(spec=MockOrganizationRepository)
        mock_organization_repository.get_unique_mock_endpoints.return_value = {
            2: "{{DVA_MOCK_URL}}/resource",
            3: "https://keep.example/token",
        }

        repository = MockEndpointsRepository(
            endpoint_repository=endpoint_repository,
            mock_organization_repository=mock_organization_repository,
            dva_mock_url="https://dva-mock.example",
        )

        result = repository.find_all()

        assert [(endpoint.id, endpoint.url) for endpoint in result] == [
            (1, "https://db.example/auth"),
            (2, "https://dva-mock.example/resource"),
            (3, "https://keep.example/token"),
        ]
        endpoint_repository.find_all.assert_called_once_with()
        mock_organization_repository.get_unique_mock_endpoints.assert_called_once_with()
