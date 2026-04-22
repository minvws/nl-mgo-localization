import logging
from typing import TypeAlias

import inject

from app.addressing.services import EndpointJWEWrapper
from app.db.repositories import EndpointRepository
from app.normalization.models import NormalizedOrganization
from app.search_indexation.repositories import MockOrganizationsFileRepo

logger = logging.getLogger(__name__)


EncryptedEndpoints: TypeAlias = dict[int, str]


class EncryptedEndpointProvider:
    @inject.autoparams("endpoint_repository", "endpoint_jwe_wrapper")
    def __init__(self, endpoint_repository: EndpointRepository, endpoint_jwe_wrapper: EndpointJWEWrapper) -> None:
        self.endpoint_repository = endpoint_repository
        self.endpoint_jwe_wrapper = endpoint_jwe_wrapper

    def get_all(
        self,
    ) -> EncryptedEndpoints:
        logger.info("Starting encrypted endpoint export")
        endpoints = self.endpoint_repository.find_all()
        logger.debug("Found %s endpoints to encrypt", len(endpoints))
        encrypted_endpoints: EncryptedEndpoints = {}

        for endpoint in endpoints:
            try:
                encrypted_endpoint = self.endpoint_jwe_wrapper.wrap(endpoint.url)
                encrypted_endpoints[endpoint.id] = encrypted_endpoint
            except Exception as e:
                raise RuntimeError(f"Failed to encrypt endpoint id={endpoint.id}") from e

        return encrypted_endpoints


class MockOrganizationsMerger:
    @inject.autoparams("mock_organizations_file_repo")
    def __init__(
        self, should_include_mock_organizations: bool, mock_organizations_file_repo: MockOrganizationsFileRepo
    ) -> None:
        self.__should_include_mock_organizations = should_include_mock_organizations
        self.__mock_organizations_file_repo = mock_organizations_file_repo

    def merge(self, organizations: list[NormalizedOrganization]) -> list[NormalizedOrganization]:
        if not self.__should_include_mock_organizations:
            logger.debug("Skipping merging of mock organizations as per configuration")
            return organizations

        mock_organizations = self.__mock_organizations_file_repo.read_mock_organizations()

        existing_ids = {organization["id"] for organization in organizations}
        duplicate_ids = sorted(existing_ids.intersection({organization["id"] for organization in mock_organizations}))

        if duplicate_ids:
            raise RuntimeError(f"Duplicate organization ids between normalized and mock: {duplicate_ids}")

        logger.info("Merging mock organizations (base=%d, mock=%d)", len(organizations), len(mock_organizations))

        return [*organizations, *mock_organizations]
