from logging import Logger
from typing import Any, Callable, List, Tuple
from uuid import uuid4

from fhir.resources.STU3.address import Address as FhirAddress
from fhir.resources.STU3.codeableconcept import CodeableConcept
from fhir.resources.STU3.coding import Coding
from fhir.resources.STU3.identifier import Identifier
from fhir.resources.STU3.organization import Organization as FhirOrganization
from pydantic import ValidationError

from app.addressing.addressing_service import AddressingService
from app.addressing.models import ZalSearchResponseEntry
from app.fhir_uris import (
    FHIR_NAMINGSYSTEM_AGB_Z,
    FHIR_NAMINGSYSTEM_URA,
    FHIR_STRUCTUREDEFINITION_GEOLOCATION,
    MEDMIJ_ID_MEDMIJNAAM,
    VZVZ_NAMINGSYSTEM_KVK,
)
from app.healthcarefinder.models import Address, CType, GeoLocation, Identification, Organization


class HydrationService:
    def __init__(self, addressing_service: AddressingService, logger: Logger):
        self.__addressing_service = addressing_service
        self.__logger = logger

    def hydrate_to_organization(self, fhir_organization: FhirOrganization) -> Organization:
        """
        Hydrate a FHIR Organization to a Organization object

        :param fhir_organization: A FHIR Organization object
        :return: A custom (non-FHIR) Organization object or none if the entry is not an organization
        :raises: ValidationError
        """

        data_service_entry, identification = self._get_organization_identifier(fhir_organization)

        load_organization = Organization(
            medmij_id=data_service_entry.medmij_id if data_service_entry else None,
            display_name=fhir_organization.name,
            identification=str(identification),
            addresses=[],
            types=[],
            data_services=data_service_entry.dataservices if data_service_entry else [],
        )

        self._get_organization_types(fhir_organization, load_organization)

        self._get_organization_addresses(fhir_organization, load_organization)

        return load_organization

    def _get_organization_identifier(
        self, fhir_organization: FhirOrganization
    ) -> Tuple[ZalSearchResponseEntry | None, str]:
        # Preferred order of identifier systems
        preferred_systems: list[tuple[str, str, Callable[[str], ZalSearchResponseEntry | None]]] = [
            ("agb-z", FHIR_NAMINGSYSTEM_AGB_Z, self.__addressing_service.search_by_agb),
            ("ura", FHIR_NAMINGSYSTEM_URA, self.__addressing_service.search_by_ura),
            ("medmij", MEDMIJ_ID_MEDMIJNAAM, self.__addressing_service.search_by_medmij_name),
            ("kvk", VZVZ_NAMINGSYSTEM_KVK, self.__addressing_service.search_by_kvk),
        ]

        system_to_identifier = self._build_identifier_lookup(fhir_organization)
        if not system_to_identifier:
            # Fallback to a random UUID (the clients expect an identifier that is not present in the FHIR response):
            return None, str(uuid4())

        identifier_type = None
        identifier_value = None
        data_service_entry = None

        for type_key, system_url, search_fn in preferred_systems:
            preferred_identifier = system_to_identifier.get(system_url)
            if preferred_identifier is None or preferred_identifier.value is None:
                continue
            identifier_type = type_key
            identifier_value = preferred_identifier.value
            data_service_entry = search_fn(identifier_value)

            if data_service_entry is not None:
                break

        # If no preferred identifier found, fallback to UUID
        if identifier_type is None or identifier_value is None:
            return None, str(uuid4())

        identification = Identification(identification_type=identifier_type, identification_value=identifier_value)
        return data_service_entry, str(identification)

    def _build_identifier_lookup(self, fhir_organization: FhirOrganization) -> dict[str, Identifier]:
        if fhir_organization.identifier is None:
            return {}

        # Build a lookup of system -> identifier
        system_to_identifier: dict[str, Identifier] = {}
        for obj in fhir_organization.identifier:
            parsed_identifier = Identifier.model_validate(obj)
            if parsed_identifier.value is None or parsed_identifier.system is None:
                continue
            system_to_identifier[parsed_identifier.system] = parsed_identifier

        return system_to_identifier

    def _get_organization_addresses(self, fhir_organization: FhirOrganization, load_org: Organization) -> None:
        if fhir_organization.address is None:
            return

        for addr_entry in fhir_organization.address:
            fhir_address = FhirAddress.model_validate(addr_entry)

            geo = None

            if fhir_address.extension:
                geo_ext = self._find_extension(fhir_address.extension, FHIR_STRUCTUREDEFINITION_GEOLOCATION)
                if geo_ext:
                    lat = self._find_extension(geo_ext.extension, "latitude")
                    lon = self._find_extension(geo_ext.extension, "longitude")
                    if lat is not None and lon is not None:
                        geo = GeoLocation(latitude=lat.valueDecimal, longitude=lon.valueDecimal)

            load_org.addresses.append(
                Address(
                    active=True,
                    address=fhir_address.text,
                    lines=[str(line) for line in fhir_address.line or []],
                    city=fhir_address.city or None,
                    country=fhir_address.country,
                    geolocation=geo,
                    postalcode=fhir_address.postalCode,
                )
            )

    def _get_organization_types(self, fhir_organization: FhirOrganization, load_organization: Organization) -> None:
        if fhir_organization.type is None:
            return

        for type_entry in fhir_organization.type:
            try:
                cc_entry = CodeableConcept.model_validate(type_entry)
                if cc_entry.coding is None or len(cc_entry.coding) == 0:
                    continue
                coding = Coding.model_validate(cc_entry.coding[0])
            except ValidationError as e:
                raise e

            load_organization.types.append(
                CType(
                    code=coding.code or "",
                    display_name=coding.display or coding.code or "",
                    type=coding.system or "",
                )
            )

    def _find_extension(self, extensions: List[Any], url: str) -> Any | None:  # type: ignore[explicit-any]
        """
        Find an extension by URL in a list of extensions.

        :param extension: The list of extensions to search in.
        :param url: The url we want to match.
        :return: The matching extension, or None if not found.
        """
        for ext in extensions:
            # BEGIN-NOSCAN
            stripped_url = ext.url.replace("http://", "").replace("https://", "")
            # END-NOSCAN
            if stripped_url == url:
                return ext
        return None


class HydrationError(Exception):
    """
    Raised when an error occurs while trying to hydrate a FHIR resource to a custom object.
    """

    pass
