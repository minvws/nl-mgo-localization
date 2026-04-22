from logging import Logger

import inject
from fhir.resources.STU3.bundle import Bundle, BundleEntry
from fhir.resources.STU3.identifier import Identifier as FhirIdentifier
from fhir.resources.STU3.organization import Organization as FhirOrganization

from app.addressing.models import IdentificationType
from app.fhir_uris import FHIR_NAMINGSYSTEM_AGB_Z, FHIR_NAMINGSYSTEM_URA
from app.healthcarefinder.models import SearchRequest
from app.zorgab_scraper.models import Identifier, ScrapeResult


class OrganizationDeduplicator:
    @inject.autoparams("logger")
    def __init__(self, logger: Logger) -> None:
        self.__logger = logger
        self.__seen_resource_keys: set[str] = set()
        self.__seen_normalized_identifier_keys: set[str] = set()

    def reset(self) -> None:
        self.__seen_resource_keys.clear()
        self.__seen_normalized_identifier_keys.clear()

    def should_include(self, fhir_organization: FhirOrganization, bundle_entry: BundleEntry) -> bool:
        """Decide if an organization should be kept in the merged bundle.

        Deduplication uses two distinct key types:
        - Resource deduplication key: `Organization.id` (or `BundleEntry.fullUrl` fallback)
          to detect exact duplicate resources.
        - Normalized identifier keys: `agb:<value>` and `ura:<value>` to detect the same
          real-world organization returned through different lookups (e.g. AGB vs URA)
          or with different FHIR resource IDs.
        """
        deduplication_key = fhir_organization.id or bundle_entry.fullUrl
        if not deduplication_key:
            return False

        if deduplication_key in self.__seen_resource_keys:
            return False

        normalized_identifier_keys = self.__collect_normalized_identifier_keys(fhir_organization)
        duplicate_identifier_key = self.__find_seen_identifier(normalized_identifier_keys)

        if duplicate_identifier_key is not None:
            self.__logger.debug(
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
                self.__logger.warning("Unknown identifier format for %s: %s", fhir_organization.id, identifier_object)
                continue

            if identifier.system == FHIR_NAMINGSYSTEM_AGB_Z and identifier.value:
                normalized_identifier_keys.append(f"agb:{identifier.value}")

            if identifier.system == FHIR_NAMINGSYSTEM_URA and identifier.value:
                normalized_identifier_keys.append(f"ura:{identifier.value}")

        return normalized_identifier_keys


class ZorgabBundleFactory:
    @inject.autoparams("logger", "organization_deduplicator")
    def __init__(
        self,
        logger: Logger,
        organization_deduplicator: OrganizationDeduplicator,
    ) -> None:
        self.__logger = logger
        self.__organization_deduplicator = organization_deduplicator

    def create(self, result: ScrapeResult) -> Bundle:
        """Merge scraped bundles and deduplicate organizations in output.

        This is the second deduplication layer: it removes duplicate organizations that
        can still appear even after identifier-level deduplication (for example when both
        AGB and URA lookups resolve to the same organization).
        """
        unique_entries: list[BundleEntry] = []
        self.__organization_deduplicator.reset()

        for bundle in result.bundles:
            if not bundle.entry:
                continue

            for entry in bundle.entry:
                try:
                    bundle_entry = BundleEntry.model_validate(entry)
                except Exception:
                    self.__logger.warning("Unknown resource type for %s", type(entry))
                    continue

                try:
                    fhir_organization = FhirOrganization.model_validate(bundle_entry.resource)
                    if not self.__organization_deduplicator.should_include(fhir_organization, bundle_entry):
                        continue
                    unique_entries.append(bundle_entry)

                except Exception as exc:
                    self.__logger.warning(
                        "Failed to process organization %s: %s",
                        bundle_entry.fullUrl or "unknown",
                        exc,
                    )

        return Bundle(type="collection", entry=unique_entries, total=len(unique_entries))


class SearchRequestFactory:
    @staticmethod
    def create_for_identifier(identifier: Identifier) -> SearchRequest | None:
        """Create a search request for the given identifier."""
        if identifier.type == IdentificationType.ura:
            return SearchRequest(ura=identifier.value)
        if identifier.type == IdentificationType.agbz:
            return SearchRequest(agb=identifier.value)
        return None
