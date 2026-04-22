from typing import Any

from fhir.resources.STU3.address import Address as FhirAddress
from fhir.resources.STU3.organization import Organization as FhirOrganization
from pydantic import ValidationError

from app.fhir_uris import FHIR_STRUCTUREDEFINITION_GEOLOCATION


def _as_float(value: Any) -> float | None:  # type: ignore[explicit-any]
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def extract_dutch_grid_coordinates(address: dict[str, Any] | None) -> dict[str, float] | None:  # type: ignore[explicit-any]
    if not isinstance(address, dict):
        return None

    extensions = address.get("extension")
    if not isinstance(extensions, list):
        return None

    geolocation_extension = next(
        (
            extension
            for extension in extensions
            if isinstance(extension, dict) and extension.get("url") == FHIR_STRUCTUREDEFINITION_GEOLOCATION
        ),
        None,
    )
    if not isinstance(geolocation_extension, dict):
        return None

    geo_extensions = geolocation_extension.get("extension", [])
    if not isinstance(geo_extensions, list):
        return None

    x: float | None = None
    y: float | None = None
    for geo_extention in geo_extensions:
        if not isinstance(geo_extention, dict):
            continue

        if geo_extention.get("url") == "latitude":
            x = _as_float(geo_extention.get("valueDecimal"))
        elif geo_extention.get("url") == "longitude":
            y = _as_float(geo_extention.get("valueDecimal"))

    if x is not None and y is not None:
        return {"x": x, "y": y}
    return None


def remove_initial_separator_dots(text: str) -> str:
    return text.replace(".", "")


def find_physical_address(fhir_organization: FhirOrganization) -> dict[str, Any] | None:  # type: ignore[explicit-any]
    if not fhir_organization.address:
        return None

    first_valid_address: FhirAddress | None = None

    for address_data in fhir_organization.address:
        try:
            address = FhirAddress.model_validate(address_data)
        except ValidationError:
            continue

        if first_valid_address is None:
            first_valid_address = address

        address_type = address.type
        normalized_type = None
        if isinstance(address_type, str):
            normalized_type = address_type.lower()
        elif address_type is not None:
            normalized_type = str(address_type).lower()

        if normalized_type == "physical":
            return address.model_dump(by_alias=True, exclude_none=True)

    if first_valid_address is None:
        return None

    return first_valid_address.model_dump(by_alias=True, exclude_none=True)
