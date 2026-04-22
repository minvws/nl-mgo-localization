import re
from abc import ABC, abstractmethod
from typing import Any, List

import inject
from fhir.resources.STU3.address import Address as FhirAddress
from fhir.resources.STU3.codeableconcept import CodeableConcept
from fhir.resources.STU3.coding import Coding
from fhir.resources.STU3.identifier import Identifier
from fhir.resources.STU3.organization import Organization as FhirOrganization

from app.fhir_uris import FHIR_NAMINGSYSTEM_AGB_Z, FHIR_NAMINGSYSTEM_URA
from app.normalization.services import GeoCoordinateService
from app.normalization.utils import extract_dutch_grid_coordinates, find_physical_address


class FieldNormalizer(ABC):
    def __init__(self, field: str) -> None:
        self.field = field

    @abstractmethod
    def normalize(self, value: Any) -> Any: ...  # type: ignore[explicit-any]


class StripNormalizer(FieldNormalizer):
    def normalize(self, value: Any) -> Any:  # type: ignore[explicit-any]
        if isinstance(value, str):
            return value.strip()

        return value


class LowercaseNormalizer(FieldNormalizer):
    def normalize(self, value: Any) -> Any:  # type: ignore[explicit-any]
        if isinstance(value, str):
            return value.lower()

        return value


class LowerCaseArrayNormalizer(FieldNormalizer):
    def normalize(self, value: Any) -> Any:  # type: ignore[explicit-any]
        if isinstance(value, list):
            return [element.lower() if isinstance(element, str) else element for element in value]

        return value


class AliasesNormalizer(FieldNormalizer):
    def __init__(self, field: str = "aliases") -> None:
        super().__init__(field)

    def normalize(self, value: list[str | None] | None) -> list[str]:
        if not value:
            return []

        return [alias.strip() for alias in value if isinstance(alias, str) and alias.strip()]


class PostalCodeNormalizer(FieldNormalizer):
    def __init__(self, field: str = "postal_code") -> None:
        super().__init__(field)

    def normalize(self, value: str) -> str:
        return self._clean(value)

    def _clean(self, value: str) -> str:
        return re.sub(r"\s+", "", value.strip())


class AddressNormalizer(FieldNormalizer):
    def normalize(self, value: List[Any]) -> Any:  # type: ignore[explicit-any]
        if isinstance(value, list) and value:
            return " ".join(self._clean(address) for address in value if address)

        return None

    def _clean(self, address_value: str) -> str:
        return address_value.strip()


class CareTypeNormalizer(FieldNormalizer):
    def __init__(self, field: str) -> None:
        super().__init__(field)

    def normalize(self, value: str) -> str:
        return value.replace("(zelfstandig of groepspraktijk)", "").strip()


def extract_external_id(fhir_organization: FhirOrganization) -> str | None:
    if fhir_organization.identifier:
        for obj in fhir_organization.identifier:
            identifier = Identifier.model_validate(obj)

            if identifier.system == FHIR_NAMINGSYSTEM_AGB_Z and identifier.value:
                return f"agb:{identifier.value}"

            if identifier.system == FHIR_NAMINGSYSTEM_URA and identifier.value:
                return f"ura:{identifier.value}"

    return fhir_organization.id


def extract_name(fhir_organization: FhirOrganization) -> str:
    return str(fhir_organization.name) if fhir_organization.name is not None else ""


def extract_aliases(fhir_organization: FhirOrganization) -> list[str]:
    # FHIR resources may contain nulls in arrays; ignore those for a clean list[str].
    return [alias for alias in (fhir_organization.alias or []) if alias is not None]


def extract_care_type(fhir_organization: FhirOrganization) -> str:
    for type_element in fhir_organization.type or []:
        codable_concept = CodeableConcept.model_validate(type_element)

        for coding_object in codable_concept.coding or []:
            coding = Coding.model_validate(coding_object)

            if coding.display is not None:
                return str(object=coding.display)

    return ""


def extract_city(fhir_organization: FhirOrganization) -> str:
    if not fhir_organization.address:
        return ""
    address = FhirAddress.model_validate(fhir_organization.address[0])

    return str(address.city) if address.city is not None else ""


def extract_postal_code(fhir_organization: FhirOrganization) -> str:
    if not fhir_organization.address:
        return ""

    address = FhirAddress.model_validate(fhir_organization.address[0])

    return str(address.postalCode) if address.postalCode is not None else ""


def extract_address(fhir_organization: FhirOrganization) -> List[Any]:  # type: ignore[explicit-any]
    if not fhir_organization.address:
        return []

    address = FhirAddress.model_validate(fhir_organization.address[0])

    return list(address.line or [])


@inject.autoparams("geo_service")
def extract_geo_lat(fhir_organization: FhirOrganization, geo_service: GeoCoordinateService) -> float | None:
    geo = find_physical_address(fhir_organization)
    dutch_grid_coordinates = extract_dutch_grid_coordinates(geo)

    if dutch_grid_coordinates is not None:
        latitude, _ = geo_service.convert_dutch_grid_to_wgs84(dutch_grid_coordinates)
        return latitude

    return None


@inject.autoparams("geo_service")
def extract_geo_lng(fhir_organization: FhirOrganization, geo_service: GeoCoordinateService) -> float | None:
    geo = find_physical_address(fhir_organization)
    dutch_grid_coordinates = extract_dutch_grid_coordinates(geo)

    if dutch_grid_coordinates is not None:
        _, longitude = geo_service.convert_dutch_grid_to_wgs84(dutch_grid_coordinates)
        return longitude

    return None
