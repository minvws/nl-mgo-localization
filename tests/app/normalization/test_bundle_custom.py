import pytest
from fhir.resources.STU3.bundle import Bundle, BundleEntry
from fhir.resources.STU3.organization import Organization

from app.fhir_uris import FHIR_STRUCTUREDEFINITION_GEOLOCATION
from app.normalization.bundle import BundleNormalizer


def make_organization(
    organization_id: str,
    name: str,
    city: str,
    postal_code: str,
    x_coordinate: float | None = None,
    y_coordinate: float | None = None,
) -> Organization:
    org_dict = {
        "resourceType": "Organization",
        "id": organization_id,
        "type": [{"coding": [{"display": "Huisartsen"}]}],
        "name": name,
        "address": [
            {
                "line": ["Mainstreet 1"],
                "city": city,
                "postalCode": postal_code,
                "extension": (
                    [
                        {
                            "url": FHIR_STRUCTUREDEFINITION_GEOLOCATION,
                            "extension": [
                                {"url": "latitude", "valueDecimal": x_coordinate},
                                {"url": "longitude", "valueDecimal": y_coordinate},
                            ],
                        }
                    ]
                    if x_coordinate is not None and y_coordinate is not None
                    else []
                ),
            }
        ],
    }

    return Organization.model_validate(org_dict)


def _make_bundle(organizations: list[Organization]) -> Bundle:
    entries = [BundleEntry(resource=organization) for organization in organizations]
    return Bundle(type="collection", entry=entries)


@pytest.mark.usefixtures("test_client")
def test_bundles_with_duplicate_entries_not_be_deduplicated() -> None:
    bundle_normalizer = BundleNormalizer()

    # Custom top-level list with mixed list/dict values and duplicates
    organization_alpha = make_organization("A", "Huisartsenpraktijk Alpha", "UTRECHT", "3511AA", 122000.0, 480000.0)
    organization_beta = make_organization("B", "Huisartsenpraktijk Beta", "AMSTERDAM", "1011AB")
    organization_beta_duplicate = make_organization("B", "Huisartsenpraktijk Beta", "AMSTERDAM", "1011AB")

    bundle = _make_bundle([organization_alpha, organization_beta, organization_beta_duplicate])
    normalized_bundle = bundle_normalizer.normalize(bundle)

    # Three results: duplicates are not removed as the input resources are already de-duplicated
    assert len(normalized_bundle) == 3

    organization_ids = [organization["id"] for organization in normalized_bundle]
    assert organization_ids.count("A") == 1  # raw id retained when no identifiers present
    # Duplicate resource id 'B' should appear twice in the normalized output
    assert organization_ids.count("B") == 2
