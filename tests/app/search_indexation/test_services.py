from pathlib import Path

import orjson
import pytest
from pytest_mock import MockerFixture

from app.addressing.services import EndpointJWEWrapper
from app.db.models import Endpoint
from app.normalization.models import NormalizedOrganization
from app.search_indexation.repositories import MockOrganizationsFileRepo
from app.search_indexation.services import (
    EncryptedEndpointProvider,
    MockOrganizationsMerger,
)


class TestEncryptedEndpointProvider:
    def test_get_all_encrypts_all_endpoints(self, mocker: MockerFixture) -> None:
        endpoint_repository = mocker.Mock()
        endpoint_repository.find_all.return_value = [
            Endpoint(id=1, url="https://example.com/auth"),
            Endpoint(id=2, url="https://example.com/token"),
        ]
        endpoint_jwe_wrapper = mocker.Mock(spec=EndpointJWEWrapper)
        endpoint_jwe_wrapper.wrap.side_effect = lambda url: f"encrypted:{url}"

        provider = EncryptedEndpointProvider(
            endpoint_repository=endpoint_repository,
            endpoint_jwe_wrapper=endpoint_jwe_wrapper,
        )
        result = provider.get_all()

        assert result == {
            1: "encrypted:https://example.com/auth",
            2: "encrypted:https://example.com/token",
        }

    def test_get_all_raises_when_encryption_fails(self, mocker: MockerFixture) -> None:
        endpoint_repository = mocker.Mock()
        endpoint_repository.find_all.return_value = [
            Endpoint(id=42, url="https://fail.example.com"),
        ]
        endpoint_jwe_wrapper = mocker.Mock(spec=EndpointJWEWrapper)
        endpoint_jwe_wrapper.wrap.side_effect = Exception("encryption failure")

        provider = EncryptedEndpointProvider(
            endpoint_repository=endpoint_repository,
            endpoint_jwe_wrapper=endpoint_jwe_wrapper,
        )

        with pytest.raises(RuntimeError, match="Failed to encrypt endpoint id=42"):
            provider.get_all()


class TestMockOrganizationsMerger:
    def test_merge_flag_off_skips_mock_file(self, mocker: MockerFixture) -> None:
        organizations: list[NormalizedOrganization] = [{"id": "agb:1", "name": "Org 1"}]
        mocked_organizations = [
            {"id": "agb:2", "name": "Mock Org 2"},
            {"id": "agb:3", "name": "Mock Org 3"},
        ]
        mock_file_repo_mock = mocker.Mock(spec=MockOrganizationsFileRepo)
        mock_file_repo_mock.read_mock_organizations.return_value = mocked_organizations

        merger = MockOrganizationsMerger(
            should_include_mock_organizations=False, mock_organizations_file_repo=mock_file_repo_mock
        )

        result = merger.merge(organizations)

        assert mock_file_repo_mock.read_mock_organizations.call_count == 0
        assert result == organizations

    def test_merge_flag_on_adds_mock_and_omits_empty_data_services(self, mocker: MockerFixture) -> None:
        repo_mock = mocker.Mock(spec=MockOrganizationsFileRepo)
        repo_mock.read_mock_organizations.return_value = [
            {
                "id": "agb:2",
                "name": "Mock Org",
                "data_services": [
                    {
                        "id": "48",
                        "auth_endpoint": "7",
                        "token_endpoint": "8",
                        "resource_endpoint": "9999999990000001",
                    }
                ],
            },
            {
                "id": "agb:3",
                "name": "Mock Org Empty DS",
                "data_services": [],
            },
        ]

        organizations: list[NormalizedOrganization] = [{"id": "agb:1", "name": "Org 1"}]

        merger = MockOrganizationsMerger(True, mock_organizations_file_repo=repo_mock)
        result = merger.merge(organizations)

        assert [organization["id"] for organization in result] == ["agb:1", "agb:2", "agb:3"]
        assert result[1]["data_services"][0]["auth_endpoint"] == "7"
        assert result[1]["data_services"][0]["token_endpoint"] == "8"
        assert result[1]["data_services"][0]["resource_endpoint"] == "9999999990000001"
        assert result[2].get("data_services") == []

    def test_merge_duplicate_organization_id_raises(self, tmp_path: Path, mocker: MockerFixture) -> None:
        mock_file = tmp_path / "mock-organizations.json"
        mock_file.write_bytes(orjson.dumps([{"id": "agb:1", "name": "Mock Duplicate"}]))

        merger = MockOrganizationsMerger(
            True,
            mock_organizations_file_repo=mocker.Mock(
                spec=MockOrganizationsFileRepo,
                read_mock_organizations=lambda: [{"id": "agb:1", "name": "Mock Duplicate"}],
            ),
        )
        with pytest.raises(RuntimeError, match="Duplicate organization ids"):
            merger.merge([{"id": "agb:1", "name": "Org 1"}])
