import logging
from collections import deque
from collections.abc import Iterator, Sequence
from concurrent.futures import Future, ThreadPoolExecutor
from threading import Lock

import inject
from fhir.resources.STU3.identifier import Identifier as FhirIdentifier
from fhir.resources.STU3.organization import Organization as FhirOrganization

from app.fhir_uris import FHIR_NAMINGSYSTEM_AGB_Z, FHIR_NAMINGSYSTEM_URA
from app.healthcarefinder.interface import HealthcareFinderAdapter

from .config import IdentifierSource
from .factories import SearchRequestFactory
from .models import Identifier, OrganizationBundleEntry, ScrapeResult
from .repositories import IdentifierRepository

logger = logging.getLogger(__name__)


class IdentifierProvider:
    @inject.autoparams("repositories")
    def __init__(self, repositories: dict[IdentifierSource, IdentifierRepository]) -> None:
        self.__repositories: dict[IdentifierSource, IdentifierRepository] = repositories

    def get_identifiers(self, identifier_sources: list[IdentifierSource], limit: int | None = None) -> list[Identifier]:
        """Collect identifiers from configured sources and deduplicate request tokens.

        This is the first deduplication layer: it removes duplicate `type:value` identifiers
        before scraping so we do not perform the same lookup multiple times.

        A second deduplication layer exists later in bundle merging, because different
        identifier lookups (for example AGB and URA) can still return the same organization.
        """
        if not identifier_sources:
            raise ValueError("At least one identifier source is required")

        seen: set[Identifier] = set()  # set enforces deduplication
        seen_count: int = 0
        max_items = limit if limit and limit > 0 else None

        logger.info("Started to extract identifiers from sources...")

        for identifier_source in identifier_sources:
            repository = self.__repositories.get(identifier_source)

            if repository is None:
                raise ValueError(f"No repository found for source: {identifier_source}")

            identifiers = repository.get_identifiers(limit=None)

            for identifier in identifiers:
                if identifier in seen:
                    logger.debug(
                        "Identifier already seen and skipped: %s:%s",
                        identifier.type,
                        identifier.value,
                    )
                    continue

                if max_items is not None and seen_count >= max_items:
                    break

                seen.add(identifier)
                seen_count += 1

            if max_items is not None and seen_count >= max_items:
                break

        if max_items is not None and seen_count >= max_items:
            logger.info("Extracted a limited amount of identifiers to first %d (combined)", max_items)
        else:
            logger.info("Extracted a total of %d identifiers from %d sources", seen_count, len(identifier_sources))

        return list(seen)


class ZorgabScrapeExecutor:
    @inject.autoparams("healthcare_finder")
    def __init__(self, healthcare_finder: HealthcareFinderAdapter) -> None:
        self.__healthcare_finder = healthcare_finder

    def __filter_valid_identifiers(self, identifiers: Sequence[Identifier]) -> list[Identifier]:
        return [
            identifier
            for identifier in identifiers
            if SearchRequestFactory.create_for_identifier(identifier) is not None
        ]

    def execute(self, identifiers: Sequence[Identifier], workers: int) -> ScrapeResult:
        """
        Method responsible for executing the entire scrape process.
        It validates identifiers it received to ensure only supported types are used (agb and ura).
        Then it performs concurrent searches for organizations using the HealthcareFinderAdapter.
        Finally, it collects the results into a ScrapeResult object.
        """
        if not identifiers:
            raise ValueError("No identifiers to scrape")

        valid_identifiers = self.__filter_valid_identifiers(identifiers)

        if not valid_identifiers:
            raise ValueError("No supported identifiers to scrape")

        max_workers = max(1, min(workers, len(valid_identifiers)))

        logger.info(
            "Started scraping zorgab for %d identifiers using %d workers. This may take a while...",
            len(identifiers),
            workers,
        )

        not_found: list[str] = []
        errors: list[str] = []
        lock = Lock()

        def make_search_organizations_request(identifier: Identifier) -> list[OrganizationBundleEntry]:
            search = SearchRequestFactory.create_for_identifier(identifier)
            assert search is not None

            try:
                raw_fhir = self.__healthcare_finder.search_organizations_raw_fhir(search)

                if not raw_fhir or not raw_fhir.entry:
                    logger.debug("No organizations found for %s", identifier.token().upper())

                    with lock:
                        not_found.append(identifier.token().upper())

                    return []

                result_count = len(raw_fhir.entry)

                if result_count > 1:
                    logger.debug(
                        "Multiple organizations returned for %s: %d",
                        identifier.token().upper(),
                        result_count,
                    )

                return [
                    OrganizationBundleEntry(full_url=entry.fullUrl, resource=entry.resource)
                    for entry in raw_fhir.entry
                    if isinstance(entry.resource, FhirOrganization)
                ]
            except Exception as exc:
                logger.exception("Error searching for %s", identifier.token().upper())
                with lock:
                    errors.append(f"{identifier.token().upper()}: {exc}")
                return []

        def stream_bundle_entries_from_zorgab() -> Iterator[OrganizationBundleEntry]:
            window = max_workers * 2
            pending: deque[Future[list[OrganizationBundleEntry]]] = deque()

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                for identifier in valid_identifiers:
                    pending.append(executor.submit(make_search_organizations_request, identifier))

                    if len(pending) >= window:
                        yield from pending.popleft().result()

                while pending:
                    yield from pending.popleft().result()

        return ScrapeResult(bundle_entries=stream_bundle_entries_from_zorgab(), not_found=not_found, errors=errors)


class OrganizationDeduplicator:
    def __init__(self) -> None:
        self.__seen_resource_keys: set[str] = set()
        self.__seen_normalized_identifier_keys: set[str] = set()

    def reset(self) -> None:
        self.__seen_resource_keys.clear()
        self.__seen_normalized_identifier_keys.clear()

    def should_include(self, organization_bundle_entry: OrganizationBundleEntry) -> bool:
        """Decide if an organization should be kept in the merged bundle.

        Deduplication uses two distinct key types:
        - Resource deduplication key: `Organization.id` (or `BundleEntry.fullUrl` fallback)
          to detect exact duplicate resources.
        - Normalized identifier keys: `agb:<value>` and `ura:<value>` to detect the same
          real-world organization returned through different lookups (e.g. AGB vs URA)
          or with different FHIR resource IDs.
        """

        fhir_organization = organization_bundle_entry.resource
        deduplication_key = fhir_organization.id or organization_bundle_entry.full_url

        if not deduplication_key:
            return False

        if deduplication_key in self.__seen_resource_keys:
            return False

        normalized_identifier_keys = self.__collect_normalized_identifier_keys(fhir_organization)
        duplicate_identifier_key = self.__find_seen_identifier(normalized_identifier_keys)

        if duplicate_identifier_key is not None:
            logger.debug(
                "Skipping duplicate organization with normalized ID: %s (FHIR ID: %s)",
                duplicate_identifier_key,
                fhir_organization.id,
            )

            self.__remember(deduplication_key, normalized_identifier_keys)

            return False

        self.__remember(deduplication_key, normalized_identifier_keys)

        return True

    def __remember(self, resource_key: str, normalized_identifier_keys: list[str]) -> None:
        self.__seen_resource_keys.add(resource_key)

        for normalized_identifier_key in normalized_identifier_keys:
            self.__seen_normalized_identifier_keys.add(normalized_identifier_key)

    def __find_seen_identifier(self, normalized_identifier_keys: list[str]) -> str | None:
        for normalized_identifier_key in normalized_identifier_keys:
            if normalized_identifier_key in self.__seen_normalized_identifier_keys:
                return normalized_identifier_key

        return None

    def __collect_normalized_identifier_keys(self, fhir_organization: FhirOrganization) -> list[str]:
        normalized_identifier_keys: list[str] = []

        if not fhir_organization.identifier:
            return normalized_identifier_keys

        for identifier_object in fhir_organization.identifier:
            try:
                identifier = FhirIdentifier.model_validate(identifier_object)
            except Exception:
                logger.warning("Unknown identifier format for %s: %s", fhir_organization.id, identifier_object)
                continue

            if identifier.system == FHIR_NAMINGSYSTEM_AGB_Z and identifier.value:
                normalized_identifier_keys.append(f"agb:{identifier.value}")

            if identifier.system == FHIR_NAMINGSYSTEM_URA and identifier.value:
                normalized_identifier_keys.append(f"ura:{identifier.value}")

        return normalized_identifier_keys
