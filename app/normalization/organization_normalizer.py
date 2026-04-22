from typing import Any, Callable

from fhir.resources.STU3.organization import Organization as FhirOrganization

from .decorators import (
    CreateSearchBlobFieldPostProcessor,
    DeduplicateAliasesPostProcessor,
    NormalizedOrganizationDecorator,
    PopulateMedMijSpecificFields,
    RemoveEphemeralFields,
)
from .fields import (
    AddressNormalizer,
    AliasesNormalizer,
    CareTypeNormalizer,
    FieldNormalizer,
    LowerCaseArrayNormalizer,
    LowercaseNormalizer,
    PostalCodeNormalizer,
    StripNormalizer,
    extract_address,
    extract_aliases,
    extract_care_type,
    extract_city,
    extract_external_id,
    extract_geo_lat,
    extract_geo_lng,
    extract_name,
    extract_postal_code,
)
from .models import NormalizedOrganization


class OrganizationNormalizer:
    EXTRACTORS: dict[str, Callable[[FhirOrganization], list[str] | str | int | float | None]] = {
        "id": extract_external_id,
        "name": extract_name,
        "aliases": extract_aliases,
        "care_type": extract_care_type,
        "city": extract_city,
        "postal_code": extract_postal_code,
        "address": extract_address,
        "geo_lat": extract_geo_lat,
        "geo_lng": extract_geo_lng,
        # search_blob is being added during postprocessing
    }

    FIELD_NORMALIZER_CLASSES: dict[str, list[type[FieldNormalizer]]] = {
        "id": [],
        "name": [StripNormalizer],
        "aliases": [AliasesNormalizer, LowerCaseArrayNormalizer],
        "care_type": [StripNormalizer, CareTypeNormalizer],
        "city": [StripNormalizer, LowercaseNormalizer],
        "postal_code": [PostalCodeNormalizer],
        "address": [AddressNormalizer],
        "geo_lat": [],
        "geo_lng": [],
    }

    # Order matters: aliases must be deduplicated before search_blob is created,
    # otherwise duplicate aliases can be embedded in the search_blob.
    POST_PROCESSORS: list[type[NormalizedOrganizationDecorator]] = [
        DeduplicateAliasesPostProcessor,
        CreateSearchBlobFieldPostProcessor,
        PopulateMedMijSpecificFields,
        RemoveEphemeralFields,
    ]

    def __init__(self) -> None:
        self.FIELD_NORMALIZERS: dict[str, list[FieldNormalizer]] = {}
        for field, normalizer_classes in self.FIELD_NORMALIZER_CLASSES.items():
            self.FIELD_NORMALIZERS[field] = [cls(field) for cls in normalizer_classes]

    def normalize(self, fhir_organization: FhirOrganization) -> NormalizedOrganization:
        """Normalize a FHIR Organization into an Orama-ready dict."""

        normalized_organization: NormalizedOrganization = NormalizedOrganization()
        for field, normalizers in self.FIELD_NORMALIZERS.items():
            # Extraction step
            extracted_value = self.EXTRACTORS[field](fhir_organization)
            # Normalization pipeline
            normalized_value: Any = extracted_value  # type: ignore[explicit-any]
            for normalizer in normalizers:
                normalized_value = normalizer.normalize(normalized_value)
            normalized_organization[field] = normalized_value  # type: ignore[literal-required]

        self.postprocess(normalized_organization)

        return normalized_organization

    def postprocess(self, normalized_organization: NormalizedOrganization) -> None:
        for post_processor in self.POST_PROCESSORS:
            post_processor()(normalized_organization)
