from pathlib import Path

import orjson
import pytest
from pytest_mock import MockerFixture

from app.db.models import Endpoint
from app.normalization.models import NormalizedOrganization
from app.search_indexation.models import SearchIndex
from app.search_indexation.repositories import (
    EncryptedEndpointsFileRepository,
    MockEndpointsRepository,
    MockOrganizationsFileRepo,
    SearchIndexFileRepository,
)
from app.search_indexation.writer import AtomicFileWriter


class TestSearchIndexFileRepository:
    @pytest.fixture
    def search_index(self) -> SearchIndex:
        entries: list[NormalizedOrganization] = [
            {"id": "1", "name": "Org 1"},
            {"id": "2", "name": "Org 2"},
            {"id": "3", "name": "Org 3"},
        ]

        return SearchIndex(entries)

    def test_save_calls_writer_with_expected_arguments(
        self,
        tmp_path: Path,
        search_index: SearchIndex,
        mocker: MockerFixture,
    ) -> None:
        temp_dir = tmp_path / "search-index"
        target_file = tmp_path / "index.json"
        file_writer = mocker.Mock(spec=AtomicFileWriter)

        repo = SearchIndexFileRepository(output_path=target_file, temp_path=temp_dir, file_writer=file_writer)
        repo.save(search_index)

        file_writer.write.assert_called_once_with(
            orjson.dumps(search_index.entries),
            output_path=target_file,
            temp_path=temp_dir,
            prefix="search_index_",
        )

    def test_save_propagates_writer_exception(
        self,
        tmp_path: Path,
        search_index: SearchIndex,
        mocker: MockerFixture,
    ) -> None:
        temp_dir = tmp_path / "search-index"
        target_file = tmp_path / "index.json"
        file_writer = mocker.Mock(spec=AtomicFileWriter)
        file_writer.write.side_effect = RuntimeError("writer failed")

        repo = SearchIndexFileRepository(output_path=target_file, temp_path=temp_dir, file_writer=file_writer)

        with pytest.raises(RuntimeError, match="writer failed"):
            repo.save(search_index)


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

        repo = MockOrganizationsFileRepo(
            mock_addressing_path=mock_file, mock_organizations_path=tmp_path / "mock-organizations.json"
        )

        assert repo.get_unique_mock_endpoints() == {9999999990000001: "https://mock.example/resource"}

    def test_get_unique_mock_endpoints_rejects_colliding_numeric_ids(self, tmp_path: Path) -> None:
        mock_file = tmp_path / "mock-addressing.json"
        mock_file.write_bytes(orjson.dumps({"1": "https://a.example", "01": "https://b.example"}))

        repo = MockOrganizationsFileRepo(
            mock_addressing_path=mock_file, mock_organizations_path=tmp_path / "mock-organizations.json"
        )

        with pytest.raises(RuntimeError, match="Duplicate endpoint id"):
            repo.get_unique_mock_endpoints()

    def test_read_mock_organizations_requires_id_field(self, tmp_path: Path) -> None:
        mock_file = tmp_path / "mock-organizations.json"
        mock_file.write_bytes(orjson.dumps([{"name": "Missing id"}]))

        repo = MockOrganizationsFileRepo(
            mock_addressing_path=tmp_path / "mock-addressing.json", mock_organizations_path=mock_file
        )

        with pytest.raises(ValueError, match="missing 'id' field"):
            repo.read_mock_organizations()

    def test_read_mock_organizations_raises_when_file_not_found(self, tmp_path: Path) -> None:
        repo = MockOrganizationsFileRepo(
            mock_organizations_path=tmp_path / "nonexistent.json",
            mock_addressing_path=tmp_path / "mock-addressing.json",
        )

        with pytest.raises(FileNotFoundError, match="Mock organizations file not found"):
            repo.read_mock_organizations()

    def test_read_mock_organizations_raises_when_payload_not_list(self, tmp_path: Path) -> None:
        mock_file = tmp_path / "mock-organizations.json"
        mock_file.write_bytes(orjson.dumps({"id": "not-a-list"}))

        repo = MockOrganizationsFileRepo(
            mock_organizations_path=mock_file,
            mock_addressing_path=tmp_path / "mock-addressing.json",
        )

        with pytest.raises(ValueError, match="Expected mock organizations JSON array"):
            repo.read_mock_organizations()

    def test_read_mock_organizations_returns_valid_list(self, tmp_path: Path) -> None:
        mock_file = tmp_path / "mock-organizations.json"
        orgs = [{"id": "agb:1", "name": "Org 1"}, {"id": "agb:2", "name": "Org 2"}]
        mock_file.write_bytes(orjson.dumps(orgs))

        repo = MockOrganizationsFileRepo(
            mock_organizations_path=mock_file,
            mock_addressing_path=tmp_path / "mock-addressing.json",
        )

        assert repo.read_mock_organizations() == orgs

    def test_get_unique_mock_endpoints_raises_when_file_not_found(self, tmp_path: Path) -> None:
        repo = MockOrganizationsFileRepo(
            mock_organizations_path=tmp_path / "mock-organizations.json",
            mock_addressing_path=tmp_path / "nonexistent.json",
        )

        with pytest.raises(FileNotFoundError, match="Mock addressing file not found"):
            repo.get_unique_mock_endpoints()

    def test_get_unique_mock_endpoints_raises_when_payload_not_dict(self, tmp_path: Path) -> None:
        mock_file = tmp_path / "mock-addressing.json"
        mock_file.write_bytes(orjson.dumps(["not-a-dict"]))

        repo = MockOrganizationsFileRepo(
            mock_organizations_path=tmp_path / "mock-organizations.json",
            mock_addressing_path=mock_file,
        )

        with pytest.raises(ValueError, match="Expected mock addressing JSON object"):
            repo.get_unique_mock_endpoints()

    def test_get_unique_mock_endpoints_raises_when_url_is_empty(self, tmp_path: Path) -> None:
        mock_file = tmp_path / "mock-addressing.json"
        mock_file.write_bytes(orjson.dumps({"1": ""}))

        repo = MockOrganizationsFileRepo(
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

        mock_organization_repository = mocker.Mock(spec=MockOrganizationsFileRepo)
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
