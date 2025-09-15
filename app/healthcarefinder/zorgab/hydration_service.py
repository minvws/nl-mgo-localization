from logging import Logger
from typing import Any, List, Tuple
from uuid import uuid4

from fhir.resources.STU3.address import Address as FhirAddress
from fhir.resources.STU3.codeableconcept import CodeableConcept
from fhir.resources.STU3.coding import Coding
from fhir.resources.STU3.identifier import Identifier
from fhir.resources.STU3.organization import Organization as FhirOrganization
from pydantic import ValidationError

from app.addressing.addressing_service import AddressingService
from app.addressing.models import ZalSearchResponseEntry
from app.healthcarefinder.models import Address, CType, GeoLocation, Identification, Organization

DEFINITION_GEOLOCATION = "hl7.org/fhir/StructureDefinition/geolocation"


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
            display_name=fhir_organization.name,  # type: ignore[arg-type] # always present since 'name' is a mandatory search field
            identification=str(identification),
            addresses=[],
            types=[],
            data_services=data_service_entry.dataservices if data_service_entry else [],
        )

        self._get_organization_types(fhir_organization, load_organization)

        self._get_organization_addresses(fhir_organization, load_organization)

        return load_organization

    def _get_organization_identifier(self, fhir_org: FhirOrganization) -> Tuple[ZalSearchResponseEntry | None, str]:
        identifier_type = None
        identifier_value = None
        data_service_entry = None

        if fhir_org.identifier is None:
            # fallback to a random uuid (temporary fix to avoid a crash in the api):
            random_uuid = str(uuid4())
            self.__logger.warning(
                "No identifier found in FHIR Organization. Generated random uuid '%s' for identifier to avoid a crash.",
                random_uuid,
            )
            return data_service_entry, random_uuid

        for obj in fhir_org.identifier:
            identifier = Identifier.model_validate(obj)

            if identifier.value is None or identifier.system is None:
                continue

            identifier_value = identifier.value

            if identifier.system == "http://fhir.nl/fhir/NamingSystem/agb-z":
                identifier_type = "agb-z"
                data_service_entry = self.__addressing_service.search_by_agb(identifier_value)
            elif identifier.system == "http://fhir.nl/fhir/NamingSystem/ura":
                identifier_type = "ura"
                data_service_entry = self.__addressing_service.search_by_ura(identifier_value)
            elif identifier.system == "http://www.medmij.nl/id/medmijnaam":
                identifier_type = "medmij"
                data_service_entry = self.__addressing_service.search_by_medmij_name(identifier_value)
            elif identifier.system == "http://www.vzvz.nl/fhir/NamingSystem/kvk":
                identifier_type = "kvk"
                data_service_entry = self.__addressing_service.search_by_kvk(identifier_value)
            # @todo: HRN is not yet supported in the FHIR Organization resource

        identification = Identification(identification_type=identifier_type, identification_value=identifier_value)

        return data_service_entry, str(identification)

    def _get_organization_addresses(self, fhir_org: FhirOrganization, load_org: Organization) -> None:
        if fhir_org.address is None:
            return

        for addr_entry in fhir_org.address:
            fhir_address = FhirAddress.model_validate(addr_entry)

            geo = None

            if fhir_address.extension:
                geo_ext = self._find_extension(fhir_address.extension, DEFINITION_GEOLOCATION)
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
                    city=fhir_address.city,  # type: ignore[arg-type] # always present since 'city' is a mandatory search field
                    country=fhir_address.country,
                    geolocation=geo,
                    postalcode=fhir_address.postalCode,
                )
            )

    def _get_organization_types(self, fhir_org: FhirOrganization, load_organization: Organization) -> None:
        if fhir_org.type is None:
            return

        for type_entry in fhir_org.type:
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

    def _find_extension(self, extensions: List[Any], url: str) -> Any | None:
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
