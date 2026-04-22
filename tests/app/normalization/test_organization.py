from typing import Any, Generator

import pytest
from fhir.resources.STU3.bundle import Bundle, BundleEntry
from fhir.resources.STU3.organization import Organization
from pydantic import ValidationError
from pytest_mock import MockerFixture
from sqlalchemy.orm import Session

from app.db.models import DataService, Endpoint, IdentifyingFeature, Organisation, SystemRole
from app.fhir_uris import (
    FHIR_NAMINGSYSTEM_AGB_Z,
    FHIR_NAMINGSYSTEM_URA,
    FHIR_STRUCTUREDEFINITION_GEOLOCATION,
)
from app.normalization.bundle import BundleNormalizer
from app.normalization.decorators import CreateSearchBlobFieldPostProcessor
from app.normalization.fields import extract_care_type, extract_geo_lat, extract_geo_lng
from app.normalization.models import NormalizedOrganization
from app.normalization.organization_normalizer import (
    OrganizationNormalizer,
)
from app.normalization.utils import find_physical_address
from app.zal_importer.enums import IdentifyingFeatureType, OrganisationType
from tests.utils import clear_bindings, configure_bindings


@pytest.fixture(autouse=True)
def configure_injector() -> Generator[None, None, None]:
    """Ensure dependency injection is configured for normalization tests.

    This allows running this module standalone without relying on other test fixtures.
    """
    configure_bindings()
    yield
    clear_bindings()


@pytest.fixture
def bundle_normalizer() -> BundleNormalizer:
    return BundleNormalizer()  # type: ignore[no-any-return]


class DummyGeo:
    def convert_dutch_grid_to_wgs84(self, dutch_grid_coordinates: dict[str, float]) -> tuple[float, float]:
        return 0.0, 0.0


@pytest.fixture
def dummy_geo() -> DummyGeo:
    return DummyGeo()


ORG_15196_AGB_CODE = "01057739"
ORG_621791_AGB_CODE = "01054044"
ENDPOINT_TEMPLATE = "https://data.service/%s/%s"

raw_bundle = {
    "resourceType": "Bundle",
    "type": "collection",
    "entry": [
        {
            "resource": {
                "resourceType": "Organization",
                "id": "15196",
                "identifier": [{"system": FHIR_NAMINGSYSTEM_AGB_Z, "value": ORG_15196_AGB_CODE}],
                "type": [{"coding": [{"display": "Huisartsen"}]}],
                "name": "Huisartsenpraktijk Wauters en Winkel",
                "alias": [
                    "HUISARTSENPRAKTIJK WINKEL EN WAUTERS",
                    "Huisartsenpraktijk Wauters en Winkel",
                    "Huisarts J.C. Wauters",
                    "Huisarts M.F. Winkel",
                ],
                "address": [
                    {
                        "line": ["Regentenstraat 21"],
                        "city": "RIJEN",
                        "postalCode": "5121CM",
                        "extension": [
                            {
                                "url": FHIR_STRUCTUREDEFINITION_GEOLOCATION,
                                "extension": [
                                    {"url": "latitude", "valueDecimal": 122164.746},
                                    {"url": "longitude", "valueDecimal": 400181.265},
                                ],
                            }
                        ],
                    }
                ],
            }
        },
        {
            "resource": {
                "resourceType": "Organization",
                "id": "621791",
                "identifier": [
                    {"system": FHIR_NAMINGSYSTEM_URA, "value": "00061434"},
                    {"system": FHIR_NAMINGSYSTEM_AGB_Z, "value": ORG_621791_AGB_CODE},
                ],
                "type": [
                    {"coding": [{"display": "Huisartspraktijk (zelfstandig of groepspraktijk)"}]},
                    {"coding": [{"display": "Huisartsenpraktijk"}]},
                ],
                "name": "Huisarts C.B. Steendijk",
                "address": [{"line": ["J.C. van Andelweg 2-A"], "city": "ST. WILLEBROD", "postalCode": "7951 DT"}],
            }
        },
    ],
}

bundle = Bundle.model_validate(raw_bundle, strict=True)


@pytest.fixture
def populate_db_with_mock_data(db_session: Session) -> None:
    # Organization with FHIR ID 15196
    db_session.add(org_15196 := Organisation(name="fhir_15196", type=OrganisationType.ZA, import_ref="1"))
    db_session.flush()

    db_session.add(
        IdentifyingFeature(
            type=IdentifyingFeatureType.AGB, value=ORG_15196_AGB_CODE, organisation_id=org_15196.id, import_ref="1"
        )
    )

    db_session.add(auth_15196 := Endpoint(url=ENDPOINT_TEMPLATE % ("auth", "15196")))
    db_session.add(token_15196 := Endpoint(url=ENDPOINT_TEMPLATE % ("token", "15196")))
    db_session.add(resource_15196 := Endpoint(url=ENDPOINT_TEMPLATE % ("resource", "15196")))
    db_session.flush()

    db_session.add(
        ds_15196 := DataService(
            external_id="48",
            organisation_id=org_15196.id,
            auth_endpoint_id=auth_15196.id,
            token_endpoint_id=token_15196.id,
        )
    )
    db_session.flush()

    db_session.add(
        SystemRole(data_service_id=ds_15196.id, code="MM-2.1-BZB-FHIR", resource_endpoint_id=resource_15196.id)
    )
    db_session.flush()

    # Organization with FHIR ID 621791
    db_session.add(org_621791 := Organisation(name="fhir_621791", type=OrganisationType.ZA, import_ref="1"))
    db_session.flush()

    db_session.add(
        IdentifyingFeature(
            type=IdentifyingFeatureType.AGB, value=ORG_621791_AGB_CODE, organisation_id=org_621791.id, import_ref="1"
        )
    )

    db_session.add(auth_621791 := Endpoint(url=ENDPOINT_TEMPLATE % ("auth", "621791")))
    db_session.add(token_621791 := Endpoint(url=ENDPOINT_TEMPLATE % ("token", "621791")))
    db_session.add(resource_621791 := Endpoint(url=ENDPOINT_TEMPLATE % ("resource", "621791")))
    db_session.flush()

    db_session.add(
        ds_621791 := DataService(
            external_id="51",
            organisation_id=org_621791.id,
            auth_endpoint_id=auth_621791.id,
            token_endpoint_id=token_621791.id,
        )
    )
    db_session.flush()

    db_session.add(
        SystemRole(data_service_id=ds_621791.id, code="MM-2.1-BZB-FHIR", resource_endpoint_id=resource_621791.id)
    )
    db_session.flush()


@pytest.mark.usefixtures("populate_db_with_mock_data")
def test_bundle_normalization(bundle_normalizer: BundleNormalizer) -> None:
    result = bundle_normalizer.normalize(bundle)

    assert len(result) == 2
    assert result[0]["id"] == "agb:01057739"
    assert result[1]["id"] == "ura:00061434"
    assert result[0]["name"] == "Huisartsenpraktijk Wauters en Winkel"
    assert "rijen" in result[0]["city"]
    assert "st. willebrod" in result[1]["city"]
    assert isinstance(result[0]["geo_lat"], float) or result[0]["geo_lat"] is None
    assert isinstance(result[0]["geo_lng"], float) or result[0]["geo_lng"] is None

    # Should remove '(zelfstandig of groepspraktijk)' from care_type
    assert result[1]["care_type"] == "Huisartspraktijk"

    first_search_blob = result[0]["search_blob"]
    assert "Huisartsen" in first_search_blob
    assert "Wauters en Winkel" in first_search_blob
    assert "huisarts mf winkel" in first_search_blob
    assert "rijen" in first_search_blob
    assert "huisartsenpraktijk winkel en wauters" in first_search_blob.lower()
    assert "5121CM" in first_search_blob
    assert "Regentenstraat 21" in first_search_blob

    second_search_blob = result[1]["search_blob"]
    assert "Huisartspraktijk" in second_search_blob
    assert "CB Steendijk" in second_search_blob
    assert "st willebrod" in second_search_blob
    assert "7951DT" in second_search_blob
    assert "JC van Andelweg 2-A" in second_search_blob

    # Normalized data service endpoints
    assert "data_services" in result[0]
    data_service = result[0]["data_services"][0]

    # Check if all chars are digits
    assert data_service["id"] == "48"
    assert "auth_endpoint" in data_service and isinstance(data_service["auth_endpoint"], str)
    assert "token_endpoint" in data_service and isinstance(data_service["token_endpoint"], str)
    assert "resource_endpoint" in data_service and isinstance(data_service["resource_endpoint"], str)

    """
    Even though the second organization in the bundle has a AGB code corresponding to a database record,
    only the first identifying feature is used, which is the URA code, thus `data_services` is omitted.
    """
    assert "data_services" not in result[1]


def test_create_search_blob_field_uses_pipe_separator() -> None:
    normalized_organization: NormalizedOrganization = {
        "care_type": "Type",
        "name": "Name",
        "city": "City",
        "aliases": ["alias1", "alias2"],
        "postal_code": "1234AB",
        "address": "Street 1",
    }

    CreateSearchBlobFieldPostProcessor()(normalized_organization)

    expected = "Type Name City | alias1 | alias2 | 1234AB | Street 1"
    assert normalized_organization["search_blob"] == expected


def test_extractors_handling_defaults() -> None:
    organization_data: dict[str, Any] = {  # type: ignore[explicit-any]
        "resourceType": "Organization",
        "id": "123",
        # Missing name -> name should become empty string
        # Missing alias -> aliases should become empty list
        "type": [],  # care_type -> ""
        "address": [{}],
    }

    fhir_organization = Organization.model_validate(organization_data)
    normalized_organization = OrganizationNormalizer().normalize(fhir_organization)
    assert normalized_organization["id"] == "123"
    assert normalized_organization["name"] == ""
    assert normalized_organization["care_type"] == ""
    assert normalized_organization["city"] == ""
    assert normalized_organization["postal_code"] == ""
    assert normalized_organization["address"] is None
    assert normalized_organization["geo_lat"] is None and normalized_organization["geo_lng"] is None


@pytest.mark.usefixtures("db_session")
def test_normalize_returns_complete_normalized_organization() -> None:
    organization = Organization.model_validate(
        {
            "resourceType": "Organization",
            "id": "01057739",
            "identifier": [{"system": FHIR_NAMINGSYSTEM_AGB_Z, "value": "01057739"}],
            "type": [{"coding": [{"display": "Huisartspraktijk"}]}],
            "name": "Huisartsenpraktijk Wauters en Winkel",
            "alias": ["HUISARTSENPRAKTIJK WINKEL EN WAUTERS"],
            "address": [
                {
                    "line": ["Regentenstraat 21"],
                    "city": "RIJEN",
                    "postalCode": "5121CM",
                    "extension": [
                        {
                            "url": FHIR_STRUCTUREDEFINITION_GEOLOCATION,
                            "extension": [
                                {"url": "latitude", "valueDecimal": 122164.746},
                                {"url": "longitude", "valueDecimal": 400181.265},
                            ],
                        }
                    ],
                }
            ],
        }
    )

    normalized_organization = OrganizationNormalizer().normalize(organization)

    optional_fields = ["data_services", "aliases", "medmij_id"]
    nullable_fields = ["address", "geo_lat", "geo_lng"]
    for field in NormalizedOrganization.__annotations__:
        if field in optional_fields:
            # Optional fields may not be present
            continue

        assert field in normalized_organization

        if field in nullable_fields:
            # Nullable fields must at least be present, value may be None
            continue

        value = normalized_organization[field]  # type: ignore[literal-required]
        assert value is not None, f"Expected field '{field}' to have a value"


@pytest.mark.usefixtures("db_session")
def test_normalize_with_duplicate_aliases_should_not_be_duplicate_in_search_blob() -> None:
    organization = Organization.model_validate(
        {
            "resourceType": "Organization",
            "id": "01057739",
            "identifier": [{"system": FHIR_NAMINGSYSTEM_AGB_Z, "value": "01057739"}],
            "type": [{"coding": [{"display": "Huisartspraktijk"}]}],
            "name": "Huisartsenpraktijk Wauters en Winkel",
            "alias": [
                "Huisarts J.C. Wauters",
                "Huisarts J.C. Wauters",
                "HUISARTSENPRAKTIJK WAUTERS EN WINKEL",
                "Huisartsenpraktijk Wauters en Winkel",
            ],
            "address": [
                {
                    "line": ["Regentenstraat 21"],
                    "city": "RIJEN",
                    "postalCode": "5121CM",
                }
            ],
        }
    )

    normalized_organization = OrganizationNormalizer().normalize(organization)

    assert normalized_organization["search_blob"].count("huisarts jc wauters") == 1
    assert normalized_organization["search_blob"].lower().count("huisartsenpraktijk wauters en winkel") == 1


def _make_bundle(organizations: list[Organization], total: int | None = None) -> Bundle:
    entries = [BundleEntry(resource=organization) for organization in organizations]
    return Bundle(type="collection", entry=entries, total=total)


def _make_organization(
    organization_id: str | None,
    name: str,
    city: str,
    postal_code: str,
    x_coordinate: float | None = None,
    y_coordinate: float | None = None,
) -> Organization:
    org_dict: dict[str, Any] = {  # type: ignore[explicit-any]
        "resourceType": "Organization",
        **({"id": organization_id} if organization_id is not None else {}),
        "name": name,
        "type": [{"coding": [{"display": "Huisartsen"}]}],
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


@pytest.mark.usefixtures("db_session")
def test_bundle_normalizer_measures_progress(bundle_normalizer: BundleNormalizer) -> None:
    alpha_organization = _make_organization("A", "Alpha", "UTRECHT", "3511AA")
    beta_organization = _make_organization(None, "Beta", "AMSTERDAM", "1011 AB")  # no id -> enumerated key path

    bundle = _make_bundle([alpha_organization, beta_organization])

    calls: list[tuple[int, int]] = []

    def progress(processed_count: int, total: int) -> None:
        calls.append((processed_count, total))

    results = bundle_normalizer.normalize(bundle, progress_callback=progress)

    # Two organizations processed (A and enumerated for bundle_b), progress called twice
    assert len(results) == 2
    assert calls and calls[-1][0] == 2 and calls[-1][1] >= 2


@pytest.mark.usefixtures("db_session")
def test_bundle_normalizer_returns_empty_when_bundle_has_no_entries(bundle_normalizer: BundleNormalizer) -> None:
    bundle = Bundle(type="collection", entry=None)
    result = bundle_normalizer.normalize(bundle)
    assert len(result) == 0


def test_extract_geo_lng_none_paths_without_injection(dummy_geo: DummyGeo) -> None:
    organization_without_address = Organization.model_validate({"resourceType": "Organization", "id": "X"})
    organization_with_empty_address = Organization.model_validate(
        {"resourceType": "Organization", "id": "Y", "address": []}
    )
    assert extract_geo_lng(organization_without_address, dummy_geo) is None
    assert extract_geo_lng(organization_with_empty_address, dummy_geo) is None


def test_extract_geo_lat_none_paths_without_injection(dummy_geo: DummyGeo) -> None:
    organization_without_address = Organization.model_validate({"resourceType": "Organization", "id": "X"})
    organization_with_empty_address = Organization.model_validate(
        {"resourceType": "Organization", "id": "Y", "address": []}
    )
    assert extract_geo_lat(organization_without_address, dummy_geo) is None
    assert extract_geo_lat(organization_with_empty_address, dummy_geo) is None


def test_extract_city_postal_address_with_non_list_address() -> None:
    with pytest.raises(ValidationError):
        Organization.model_validate({"resourceType": "Organization", "id": "X", "address": {}})


def test_extract_care_type_with_none_display() -> None:
    organization = Organization.model_validate(
        {
            "resourceType": "Organization",
            "id": "X",
            "type": [{"coding": [{"display": None}]}],
        }
    )
    assert extract_care_type(organization) == ""


def test_first_address_prefers_physical_type() -> None:
    organization = Organization.model_validate(
        {
            "resourceType": "Organization",
            "id": "P",
            "address": [
                {"type": "Postal", "city": "Alpha", "line": ["Alpha 1"]},
                {"type": "Physical", "city": "Bravo", "line": ["Bravo 2"]},
            ],
        }
    )

    address = find_physical_address(organization)

    assert address is not None
    assert address["city"] == "Bravo"


def test_first_address_fallback_to_first_when_physical_missing() -> None:
    organization = Organization.model_validate(
        {
            "resourceType": "Organization",
            "id": "F",
            "address": [
                {"type": "Postal", "city": "Alpha", "line": ["Alpha 1"]},
                {"type": "Practice", "city": "Bravo", "line": ["Bravo 2"]},
            ],
        }
    )

    address = find_physical_address(organization)

    assert address is not None
    assert address["city"] == "Alpha"


@pytest.mark.usefixtures("db_session")
def test_fhir_bundle_progress_callback_is_called(mocker: MockerFixture, bundle_normalizer: BundleNormalizer) -> None:
    raw_bundle: dict[str, Any] = {  # type: ignore[explicit-any]
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [
            {"resource": {"resourceType": "Organization", "id": "X1", "name": "One"}},
            {"resource": {"resourceType": "Organization", "id": "X2", "name": "Two"}},
        ],
    }

    bundle = Bundle.model_validate(raw_bundle)

    progress = mocker.Mock()

    normalized_bundle = bundle_normalizer.normalize(bundle, progress_callback=progress)
    assert len(normalized_bundle) == 2

    assert progress.call_count == 2

    progress.assert_has_calls(
        [
            mocker.call(1, 2),
            mocker.call(2, 2),
        ]
    )


@pytest.mark.usefixtures("db_session")
def test_organization_normalizer_accepts_fhir_model_input() -> None:
    organization = Organization.model_validate(
        {
            "resourceType": "Organization",
            "id": "15196",
            "identifier": [{"system": FHIR_NAMINGSYSTEM_AGB_Z, "value": "01057739"}],
            "type": [{"coding": [{"display": "Huisartspraktijk (zelfstandig of groepspraktijk)"}]}],
            "name": "Huisartsenpraktijk Wauters en Winkel",
            "alias": ["HUISARTSENPRAKTIJK WINKEL EN WAUTERS"],
            "address": [{"line": ["Regentenstraat 21"], "city": "RIJEN", "postalCode": "5121CM"}],
        }
    )

    normalized_organization = OrganizationNormalizer().normalize(organization)
    assert normalized_organization["id"] == "agb:01057739"
    assert normalized_organization["care_type"] == "Huisartspraktijk"
    assert "rijen" in normalized_organization["city"]


def test_bundle_total_is_logged(mocker: MockerFixture, bundle_normalizer: BundleNormalizer) -> None:
    organizations = [
        _make_organization("a", "Clinic A", "AMSTERDAM", "1111AA"),
        _make_organization("b", "Clinic B", "UTRECHT", "2222BB"),
    ]
    bundle_total = 100
    bundle_with_total = _make_bundle(organizations, total=bundle_total)
    logger_patch = mocker.patch("app.normalization.bundle.logger")
    bundle_normalizer.normalize(bundle_with_total)
    logger_patch.info.assert_any_call("Normalizing a bundle with %d resources...", bundle_total)
