import logging
from typing import Protocol

from inject import autoparams

from app.db.models import DataService
from app.db.repositories import DataServiceRepository, OrganisationRepository
from app.normalization.models import NormalizedDataService, NormalizedOrganization
from app.normalization.services import IdStringToIdentifyingFeatureConverter
from app.normalization.utils import remove_initial_separator_dots

logger = logging.getLogger(__name__)


class NormalizedOrganizationDecorator(Protocol):
    def __call__(self, normalized_organization: NormalizedOrganization) -> None: ...


class DeduplicateAliasesPostProcessor(NormalizedOrganizationDecorator):
    def __call__(self, normalized_organization: NormalizedOrganization) -> None:
        name = normalized_organization.get("name", "")
        aliases = normalized_organization.get("aliases", [])
        name_lower = name.lower()

        seen_aliases = set()
        filtered_aliases = []

        for alias in aliases:
            alias_lower = alias.lower()

            if alias_lower == name_lower:
                continue

            if alias_lower in seen_aliases:
                continue

            seen_aliases.add(alias_lower)
            filtered_aliases.append(alias)

        normalized_organization["aliases"] = filtered_aliases


class CreateSearchBlobFieldPostProcessor(NormalizedOrganizationDecorator):
    def __call__(self, normalized_organization: NormalizedOrganization) -> None:
        """
        Build the search_blob field from care_type, name, city, aliases, postal_code, address.
        "Hot Zone": Type + Name + City
        "Enrichment": Aliases, Postal code, Address
        The pipe separates terms in the enrichment to prevent false positives.
        """
        care_type = normalized_organization.get("care_type", "")
        name = normalized_organization.get("name", "")
        city = normalized_organization.get("city", "")
        hot_zone = remove_initial_separator_dots(f"{care_type} {name} {city}").strip()
        enrichment_items: list[str] = []

        aliases = normalized_organization.get("aliases", [])
        if aliases:
            enrichment_items.extend(remove_initial_separator_dots(str(alias)) for alias in aliases)

        postal_code = normalized_organization.get("postal_code", "")
        if postal_code:
            enrichment_items.append(postal_code)

        address = normalized_organization.get("address", "")
        if address:
            enrichment_items.append(remove_initial_separator_dots(address))

        enrichment = " | ".join(enrichment_item for enrichment_item in enrichment_items if enrichment_item)
        normalized_organization["search_blob"] = f"{hot_zone} | {enrichment}".strip()


class PopulateMedMijSpecificFields(NormalizedOrganizationDecorator):
    @autoparams()
    def __init__(
        self,
        id_string_converter: IdStringToIdentifyingFeatureConverter,
        organization_repository: OrganisationRepository,
        data_service_repository: DataServiceRepository,
    ) -> None:
        self.__id_string_converter = id_string_converter
        self.__organization_repository = organization_repository
        self.__data_service_repository = data_service_repository

    def __call__(self, normalized_organization: NormalizedOrganization) -> None:
        identifying_feature_tuple = self.__id_string_converter(normalized_organization.get("id"))

        if identifying_feature_tuple is None:
            return

        organization = self.__organization_repository.find_one_by_identifying_feature(*identifying_feature_tuple)

        if organization is None:
            logger.debug("No organization for identifying feature type '%s' and value '%s'", *identifying_feature_tuple)

            return

        data_services: list[NormalizedDataService] = [
            normalized_data_service
            for data_service in self.__data_service_repository.find_all_by_organisation(organization.id)
            if (normalized_data_service := self.__extract_data_service_endpoint_references(data_service)) is not None
        ]

        if len(data_services) > 0:
            normalized_organization["data_services"] = data_services
            normalized_organization["medmij_id"] = self._remove_medmij_suffix(organization.name)

    @staticmethod
    def _remove_medmij_suffix(text: str) -> str:
        suffix = "@medmij"
        if text.lower().endswith(suffix):
            return text[: -len(suffix)]

        return text

    def __extract_data_service_endpoint_references(self, data_service: DataService) -> NormalizedDataService | None:
        providing_role = next(
            (role for role in data_service.roles if role.is_providing_role()),
            None,
        )

        if providing_role is None:
            return None

        normalized_data_service: NormalizedDataService = {
            "id": data_service.external_id,
            "auth_endpoint": str(data_service.auth_endpoint.id),
            "token_endpoint": str(data_service.token_endpoint.id),
            "resource_endpoint": str(providing_role.resource_endpoint.id),
        }

        return normalized_data_service


class RemoveEphemeralFields(NormalizedOrganizationDecorator):
    def __call__(self, normalized_organization: NormalizedOrganization) -> None:
        if "aliases" in normalized_organization:
            del normalized_organization["aliases"]
