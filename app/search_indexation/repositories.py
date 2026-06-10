import logging
from collections.abc import Iterator
from os import fsync, makedirs, path, replace, unlink
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import List, Protocol, TypeAlias, cast

import inject
import orjson

from app.db.models import Endpoint
from app.db.repositories import DbEndpointRepository, EndpointRepository
from app.normalization.models import NormalizedOrganization
from app.search_indexation.writer import AtomicFileWriter

logger = logging.getLogger(__name__)


EncryptedEndpoints: TypeAlias = dict[int, str]


class SearchIndexStreamRepository(Protocol):
    def save(self, normalized_organizations: Iterator[NormalizedOrganization]) -> None: ...


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


class MockOrganizationRepository:
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
        mock_organization_repository: MockOrganizationRepository,
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


class FilesystemSearchIndexStreamRepository(SearchIndexStreamRepository):
    def __init__(self, output_path: Path, temp_path: Path) -> None:
        self.__output_path = output_path
        self.__temp_path = temp_path

    def save(self, normalized_organizations: Iterator[NormalizedOrganization]) -> None:
        count = 0
        tmp_file_path: str | None = None

        makedirs(self.__temp_path, exist_ok=True)
        makedirs(self.__output_path.parent, exist_ok=True)

        try:
            with NamedTemporaryFile("wb", dir=self.__temp_path, prefix="search_index_", delete=False) as tmp_file:
                tmp_file_path = tmp_file.name
                tmp_file.write(b"[")
                first = True

                for normalized_organization in normalized_organizations:
                    if not first:
                        tmp_file.write(b",")

                    tmp_file.write(orjson.dumps(normalized_organization))

                    count += 1
                    first = False

                tmp_file.write(b"]")
                tmp_file.flush()

                fsync(tmp_file.fileno())

            replace(tmp_file_path, self.__output_path)
            tmp_file_path = None

            logger.debug("SearchIndex written successfully to %s (%d entries)", self.__output_path, count)

        except Exception:
            logger.exception("Failed to persist SearchIndex to %s", self.__output_path)

            raise

        finally:
            if tmp_file_path and path.exists(tmp_file_path):
                try:
                    unlink(tmp_file_path)
                except Exception:
                    logger.debug("Failed to clean up temp file %s", tmp_file_path)

                tmp_file_path = None


class MockOrganizationMergerDecorator(SearchIndexStreamRepository):
    @inject.autoparams("mock_organizations_repository")
    def __init__(
        self,
        decorated: SearchIndexStreamRepository,
        mock_organizations_repository: MockOrganizationRepository,
    ) -> None:
        self.__decorated = decorated
        self.__mock_organizations_repository = mock_organizations_repository

    def save(self, normalized_organizations: Iterator[NormalizedOrganization]) -> None:
        self.__decorated.save(
            self.__get_unique_normalized_and_mocked_organizations(normalized_organizations),
        )

    def __get_unique_normalized_and_mocked_organizations(
        self, normalized_organizations: Iterator[NormalizedOrganization]
    ) -> Iterator[NormalizedOrganization]:
        seen_ids: set[str | None] = set()

        for normalized_organization in normalized_organizations:
            seen_ids.add(normalized_organization["id"])

            yield normalized_organization

        for mock_organization in self.__mock_organizations_repository.read_mock_organizations():
            if mock_organization.get("id") in seen_ids:
                raise RuntimeError(
                    "Duplicate organization id between normalized organizations and mock organizations: %s"
                    % mock_organization.get("id"),
                )

            yield mock_organization
