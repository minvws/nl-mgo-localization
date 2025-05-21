from logging import Logger
from typing import Any, Dict, List, cast

import pytest
from pytest_mock import MockerFixture
from requests.models import Response

from app.addressing.addressing_service import AddressingService
from app.addressing.mock.mock_adapter import AddressingMockAdapter
from app.healthcarefinder.models import SearchRequest
from app.healthcarefinder.zorgab.hydration_service import HydrationService
from app.healthcarefinder.zorgab.zorgab import ZorgABAdapter


def get_address() -> List[Dict[str, Any]]:
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
                    "url": "http://hl7.org/fhir/StructureDefinition/geolocation",
                },
            ],
            "line": ["Poststreet 1005"],
            "postalCode": "3528 BD",
            "text": "Poststreet 1005\r\n3528 BD Utrecht",
            "type": "physical",
            "use": "work",
        },
    ]


def get_identifier() -> List[Dict[str, Any]]:
    return [
        {
            "extension": [
                {
                    "url": "http://www.vzvz.nl/fhir/StructureDefinition/author",
                    "valueString": "Vektis",
                }
            ],
            "system": "http://fhir.nl/fhir/NamingSystem/agb-z",
            "value": "71025100",
        }
    ]


def get_type() -> List[Dict[str, Any]]:
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

    adapter = ZorgABAdapter(
        base_url="https://example.com",
        hydration_service=HydrationService(
            addressing_service=cast(AddressingService, AddressingMockAdapter()),
        ),
        logger=mocker.Mock(Logger),
    )
    search = SearchRequest(name="foo", city="bar")

    adapter.search_organizations(search)

    mock_get.assert_called_once_with(
        "https://example.com/fhir/Organization",
        params="name=foo&address-city=bar",
    )
