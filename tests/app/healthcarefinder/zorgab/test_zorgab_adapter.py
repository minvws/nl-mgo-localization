from logging import Logger
from types import SimpleNamespace
from typing import Any, cast

import pytest
from fhir.resources.STU3.bundle import BundleEntry
from pytest_mock import MockerFixture
from requests.models import Response

from app.addressing.addressing_service import AddressingService
from app.fhir_uris import FHIR_NAMINGSYSTEM_AGB_Z, FHIR_STRUCTUREDEFINITION_GEOLOCATION
from app.healthcarefinder.models import SearchRequest
from app.healthcarefinder.zorgab.hydration_service import HydrationService
from app.healthcarefinder.zorgab.zorgab import ZorgABAdapter


def get_address() -> list[dict[str, Any]]:  # type: ignore[explicit-any]
    return [
        {
            "city": "Utrecht",
            "extension": [
                {
                    "url": "http://www.vzvz.nl/fhir/StructureDefinition/author",
                    "valueString": "URA:90000382",
                },
                {
                    "extension": [
                        {"url": "latitude", "valueDecimal": 121871},
                        {"url": "longitude", "valueDecimal": 487449},
                    ],
                    "url": FHIR_STRUCTUREDEFINITION_GEOLOCATION,
                },
            ],
            "line": ["Poststreet 1005"],
            "postalCode": "3528 BD",
            "text": "Poststreet 1005\r\n3528 BD Utrecht",
            "type": "physical",
            "use": "work",
        },
    ]


def get_identifier() -> list[dict[str, Any]]:  # type: ignore[explicit-any]
    return [
        {
            "extension": [
                {
                    "url": "http://www.vzvz.nl/fhir/StructureDefinition/author",
                    "valueString": "Vektis",
                }
            ],
            "system": FHIR_NAMINGSYSTEM_AGB_Z,
            "value": "71025100",
        }
    ]


def get_type() -> list[dict[str, Any]]:  # type: ignore[explicit-any]
    return [
        {
            "coding": [
                {
                    "code": "84",
                    "display": "Overige Artsen",
                    "system": "http://www.vzvz.nl/fhir/NamingSystem/vektis-zorgsoort",
                }
            ],
            "extension": [
                {
                    "url": "http://www.vzvz.nl/fhir/StructureDefinition/author",
                    "valueString": "Vektis",
                }
            ],
        }
    ]


def create_organization_json() -> dict[str, object]:
    return {
        "resourceType": "Organization",
        "id": "f001",
        "identifier": get_identifier(),
        "active": True,
        "name": "Acme Corporation",
        "address": get_address(),
        "type": get_type(),
    }


@pytest.fixture
def create_bundle_json() -> dict[str, object]:
    return {
        "resourceType": "Bundle",
        "type": "searchset",
        "entry": [{"resource": create_organization_json()}],
        "total": 1,
    }


def test_search_organizations(
    mocker: MockerFixture,
    create_bundle_json: dict[str, object],
) -> None:
    mock_response = mocker.Mock(spec=Response)
    mock_response.status_code = 200
    mock_response.json.return_value = create_bundle_json

    mock_get = mocker.patch("requests.Session.get")
    mock_get.return_value = mock_response

    addressing_service = mocker.Mock(spec=AddressingService)
    addressing_service.search_by_agb.return_value = None

    adapter = ZorgABAdapter(
        base_url="https://example.com",
        hydration_service=HydrationService(
            addressing_service=cast(AddressingService, addressing_service),
            logger=mocker.Mock(spec=Logger),
        ),
        logger=mocker.Mock(Logger),
        suppress_hydration_errors=False,
    )
    search = SearchRequest(name="foo", city="bar")

    adapter.search_organizations(search)

    mock_get.assert_called_once_with(
        "https://example.com/fhir/Organization",
        params="name=foo&address-city=bar",
    )


def test_verify_connection_success(mocker: MockerFixture) -> None:
    adapter = ZorgABAdapter(
        base_url="https://example.com/",
        hydration_service=mocker.Mock(),
        logger=mocker.Mock(Logger),
        suppress_hydration_errors=True,
    )

    mock_response = mocker.Mock(spec=Response)
    mock_response.status_code = 200
    session = cast(Any, adapter)._ZorgABAdapter__session  # type: ignore[explicit-any]
    mock_get = mocker.patch.object(session, "get", return_value=mock_response)

    assert adapter.verify_connection() is True
    mock_get.assert_called_once_with("https://example.com/fhir/Organization?name=huisarts&address-city=Amsterdam")


def test_verify_connection_failure_status(mocker: MockerFixture) -> None:
    adapter = ZorgABAdapter(
        base_url="https://example.com",
        hydration_service=mocker.Mock(),
        logger=mocker.Mock(Logger),
        suppress_hydration_errors=True,
    )

    mock_response = mocker.Mock(spec=Response)
    mock_response.status_code = 503
    session = cast(Any, adapter)._ZorgABAdapter__session  # type: ignore[explicit-any]
    mocker.patch.object(session, "get", return_value=mock_response)

    assert adapter.verify_connection() is False


def test_verify_connection_request_exception(mocker: MockerFixture) -> None:
    import requests

    adapter = ZorgABAdapter(
        base_url="https://example.com",
        hydration_service=mocker.Mock(),
        logger=mocker.Mock(Logger),
        suppress_hydration_errors=True,
    )

    session = cast(Any, adapter)._ZorgABAdapter__session  # type: ignore[explicit-any]
    mocker.patch.object(session, "get", side_effect=requests.RequestException("boom"))

    assert adapter.verify_connection() is False


def test_create_fhir_search_raises_when_missing_params() -> None:
    with pytest.raises(ValueError):
        ZorgABAdapter.create_fhir_search(SearchRequest(name="", city="Amsterdam"))


def test_search_organizations_hydration_error_bubbles_when_not_suppressed(mocker: MockerFixture) -> None:
    hydration_service = mocker.Mock()
    hydration_service.hydrate_to_organization.side_effect = RuntimeError("boom")

    adapter = ZorgABAdapter(
        base_url="http://test",
        hydration_service=hydration_service,
        logger=mocker.Mock(Logger),
        suppress_hydration_errors=False,
    )

    response = mocker.Mock()
    response.status_code = 200
    response.json.return_value = {"irrelevant": True}
    session = cast(Any, adapter)._ZorgABAdapter__session  # type: ignore[explicit-any]
    mocker.patch.object(session, "get", return_value=response)

    bundle = SimpleNamespace(total=1, entry=[{"resource": {"id": "org1"}}])
    mocker.patch("app.healthcarefinder.zorgab.zorgab.Bundle.model_validate", return_value=bundle)
    mocker.patch(
        "app.healthcarefinder.zorgab.zorgab.BundleEntry.model_validate",
        return_value=SimpleNamespace(resource={"id": "org1"}),
    )
    mocker.patch("app.healthcarefinder.zorgab.zorgab.FhirOrganization.model_validate", return_value=mocker.Mock())

    with pytest.raises(RuntimeError):
        adapter.search_organizations(SearchRequest(name="foo", city="bar"))


def test_search_organizations_raw_fhir_returns_bundle_entries(
    mocker: MockerFixture,
    create_bundle_json: dict[str, object],
) -> None:
    mock_response = mocker.Mock(spec=Response)
    mock_response.status_code = 200
    mock_response.json.return_value = create_bundle_json

    mock_get = mocker.patch("requests.Session.get")
    mock_get.return_value = mock_response

    addressing_service = mocker.Mock(spec=AddressingService)
    addressing_service.search_by_agb.return_value = None

    adapter = ZorgABAdapter(
        base_url="https://example.com",
        hydration_service=HydrationService(
            addressing_service=cast(AddressingService, addressing_service),
            logger=mocker.Mock(spec=Logger),
        ),
        logger=mocker.Mock(Logger),
        suppress_hydration_errors=False,
    )
    search = SearchRequest(name="foo", city="bar")

    result = adapter.search_organizations_raw_fhir(search)

    assert result is not None
    assert result.entry is not None
    entry = BundleEntry.model_validate(result.entry[0])
    assert entry.fullUrl == "https://example.com/fhir/Organization/f001"
