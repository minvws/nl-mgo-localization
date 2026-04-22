import logging
from pathlib import Path
from typing import List, Protocol, TypeAlias, cast

import inject
import orjson

from app.db.models import Endpoint
from app.db.repositories import DbEndpointRepository, EndpointRepository
from app.normalization.models import NormalizedOrganization
from app.search_indexation.writer import AtomicFileWriter

from .models import SearchIndex

logger = logging.getLogger(__name__)


EncryptedEndpoints: TypeAlias = dict[int, str]


class SearchIndexRepository(Protocol):
    def save(self, search_index: SearchIndex) -> None: ...


class SearchIndexFileRepository(SearchIndexRepository):
    @inject.autoparams("output_path", "temp_path", "file_writer")
    def __init__(self, output_path: Path, temp_path: Path, file_writer: AtomicFileWriter) -> None:
        self.__output_path = output_path
        self.__temp_path = temp_path
        self.__writer = file_writer

    def save(self, search_index: SearchIndex) -> None:
        logger.debug("Writing search index to disk %s", self.__output_path)

        try:
            data = orjson.dumps(search_index.entries)
            self.__writer.write(
                data,
                output_path=self.__output_path,
                temp_path=self.__temp_path,
                prefix="search_index_",
            )

            logger.debug(
                "SearchIndex written successfully to %s (%d entries)",
                self.__output_path,
                len(search_index.entries),
            )
        except Exception:
            logger.exception("Failed to persist SearchIndex to %s", self.__output_path)
            raise


class EncryptedEndpointsRepository(Protocol):
    def save(self, endpoints: EncryptedEndpoints) -> None: ...


class EncryptedEndpointsFileRepository(EncryptedEndpointsRepository):
    @inject.autoparams("output_path", "temp_path", "file_writer")
    def __init__(self, output_path: Path, temp_path: Path, file_writer: AtomicFileWriter) -> None:
        self.__output_path = output_path
        self.__temp_path = temp_path
        self.__writer = file_writer

    def save(self, endpoints: EncryptedEndpoints) -> None:
        logger.debug("Writing encrypted endpoints to disk %s", self.__output_path)

        try:
            data = orjson.dumps(
                endpoints,
                option=orjson.OPT_NON_STR_KEYS,
            )
            self.__writer.write(
                data,
                output_path=self.__output_path,
                temp_path=self.__temp_path,
                prefix="encrypted_endpoints_",
            )

            logger.debug(
                "Encrypted endpoints written successfully to %s (%d endpoints)",
                self.__output_path,
                len(endpoints),
            )
        except Exception:
            logger.exception("Failed to persist encrypted endpoints to %s", self.__output_path)
            raise


class MockOrganizationsFileRepo:
    def __init__(self, mock_organizations_path: Path, mock_addressing_path: Path) -> None:
        self.__mock_organizations_path = mock_organizations_path
        self.__mock_addressing_path = mock_addressing_path

    def read_mock_organizations(self) -> list[NormalizedOrganization]:
        if not self.__mock_organizations_path.exists() or not self.__mock_organizations_path.is_file():
            raise FileNotFoundError(f"Mock organizations file not found: {self.__mock_organizations_path}")

        payload = orjson.loads(self.__mock_organizations_path.read_bytes())

        if not isinstance(payload, list):
            raise ValueError(f"Expected mock organizations JSON array in {self.__mock_organizations_path}")

        for idx, org in enumerate(payload):
            if not isinstance(org, dict) or "id" not in org:
                raise ValueError(f"Invalid mock organization at index {idx}: missing 'id' field")

        return cast(list[NormalizedOrganization], payload)

    def get_unique_mock_endpoints(self) -> dict[int, str]:
        if not self.__mock_addressing_path.exists() or not self.__mock_addressing_path.is_file():
            raise FileNotFoundError(f"Mock addressing file not found: {self.__mock_addressing_path}")

        payload = orjson.loads(self.__mock_addressing_path.read_bytes())

        if not isinstance(payload, dict):
            raise ValueError(f"Expected mock addressing JSON object in {self.__mock_addressing_path}")

        endpoints: dict[int, str] = {}

        for raw_id, raw_url in payload.items():
            endpoint_id = int(raw_id)

            if endpoint_id in endpoints:
                raise RuntimeError(
                    f"Duplicate endpoint id in mock addressing file {self.__mock_addressing_path}: {endpoint_id}"
                )

            if not isinstance(raw_url, str) or not raw_url:
                raise RuntimeError(f"Invalid mock endpoint URL for id {raw_id} in {self.__mock_addressing_path}")

            endpoints[endpoint_id] = raw_url

        return endpoints


class MockEndpointsRepository(EndpointRepository):
    """
    Repository that decorates another EndpointRepository
    appending mock endpoints to the output of the decorated repository.
    """

    @inject.autoparams("endpoint_repository", "mock_organization_repository")
    def __init__(
        self,
        dva_mock_url: str,
        endpoint_repository: DbEndpointRepository,
        mock_organization_repository: MockOrganizationsFileRepo,
    ) -> None:
        self.endpoint_repository = endpoint_repository
        self.mock_organization_repository = mock_organization_repository
        self.__dva_mock_url = dva_mock_url

    def find_all(self) -> List[Endpoint]:
        logger.debug("Fetching endpoints from database and mock organizations")
        database_endpoints = self.endpoint_repository.find_all()
        raw_mock_endpoints = self.mock_organization_repository.get_unique_mock_endpoints()
        mock_endpoints = self.__replace_mock_placeholders(raw_mock_endpoints)

        combined_endpoints = database_endpoints + [
            Endpoint(id=endpoint_id, url=url) for endpoint_id, url in mock_endpoints.items()
        ]

        logger.info(
            "Fetched %d endpoints from database and %d mock endpoints, total %d endpoints",
            len(database_endpoints),
            len(mock_endpoints),
            len(combined_endpoints),
        )

        return combined_endpoints

    def __replace_mock_placeholders(self, endpoints: dict[int, str]) -> dict[int, str]:
        for endpoint_id, url in endpoints.items():
            if "{{DVA_MOCK_URL}}" in url:
                endpoints[endpoint_id] = url.replace("{{DVA_MOCK_URL}}", self.__dva_mock_url)

        return endpoints
