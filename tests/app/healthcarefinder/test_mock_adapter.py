import json
from logging import Logger

import faker
from pytest_mock import MockerFixture

from app.healthcarefinder.mock.adapter import MockHealthcareFinderAdapter
from app.healthcarefinder.models import SearchRequest, SearchResponse
from app.healthcarefinder.zorgab_mock.zorgab_mock import ZorgABMockHydrationAdapter


def test_enveloped_mock_url_is_returned_from_mock_adapter(mocker: MockerFixture) -> None:
    endpoint_jwe_wrapper = mocker.MagicMock()
    endpoint_jwe_wrapper.wrap.side_effect = lambda url: f"wrapped:{url}"

    config = mocker.MagicMock()
    config.app.mock_base_url = "http://localhost:8002"

    adapter = MockHealthcareFinderAdapter(
        endpoint_jwe_wrapper=endpoint_jwe_wrapper,
        logger=mocker.Mock(Logger),
        config=config,
    )
    searchresponse: SearchResponse = adapter.search_organizations(search=SearchRequest(name="test", city="test"))

    for organization in searchresponse.organizations:
        assert organization.data_services is not None
        for data_service in organization.data_services:
            assert data_service.auth_endpoint.startswith("wrapped:")
            assert data_service.token_endpoint.startswith("wrapped:")
            for role in data_service.roles:
                assert role.resource_endpoint.startswith("wrapped:")

    assert endpoint_jwe_wrapper.wrap.called


def test_hydration_adapter_uses_mock_response_json_file_to_hydrate_response_model(
    mocker: MockerFixture,
) -> None:
    generator = faker.Faker()
    organization_name = generator.company()

    json = TEST_JSON
    json = json.replace("Apotheek Janssen", organization_name)

    mocker.patch(
        "app.healthcarefinder.zorgab_mock.zorgab_mock.ZorgABMockHydrationAdapter._get_json_mock_response",
        return_value=json,
    )

    adapter = ZorgABMockHydrationAdapter(
        logger=mocker.Mock(Logger),
    )
    response = adapter.search_organizations(search=SearchRequest(name="test", city="test"))

    assert response is not None
    assert response.organizations is not None
    assert len(response.organizations) == 1
    assert response.organizations[0].display_name == organization_name
    assert response.organizations[0].addresses is not None


def test_hydration_adapter_address_is_none_when_address_is_none_in_mock_response(
    mocker: MockerFixture,
) -> None:
    adapter = ZorgABMockHydrationAdapter(
        logger=mocker.Mock(Logger),
    )

    mocker.patch(
        "app.healthcarefinder.zorgab_mock.zorgab_mock.ZorgABMockHydrationAdapter._get_json_mock_response",
        return_value=TEST_JSON,
    )

    response = adapter.search_organizations(search=SearchRequest(name="test", city="test"))

    assert response is not None
    assert response.organizations is not None
    assert len(response.organizations) == 1
    assert response.organizations[0].addresses == []


def test_hydration_adapter_hydrates_address(
    mocker: MockerFixture,
) -> None:
    adapter = ZorgABMockHydrationAdapter(
        logger=mocker.Mock(Logger),
    )

    test_json_data = json.loads(TEST_JSON)
    test_json_address_data = json.loads(TEST_JSON_ADDRESS)

    if isinstance(test_json_data, list) and len(test_json_data) > 0:
        test_json_data[0]["addresses"] = test_json_address_data

    mocker.patch(
        "app.healthcarefinder.zorgab_mock.zorgab_mock.ZorgABMockHydrationAdapter._get_json_mock_response",
        return_value=json.dumps(test_json_data, indent=2),
    )

    response = adapter.search_organizations(search=SearchRequest(name="test", city="test"))

    assert response is not None
    assert response.organizations is not None
    assert len(response.organizations) == 1
    assert response.organizations[0].addresses[0].city == test_json_address_data[0]["city"]


def test_hydration_adapter_returns_none_when_mock_has_no_organizations(mocker: MockerFixture) -> None:
    mocker.patch(
        "app.healthcarefinder.zorgab_mock.zorgab_mock.ZorgABMockHydrationAdapter._get_json_mock_response",
        return_value="[]",
    )

    adapter = ZorgABMockHydrationAdapter(
        logger=mocker.Mock(Logger),
    )

    assert adapter.search_organizations(search=SearchRequest(name="test", city="test")) is None


def test_hydration_adapter_can_read_default_mock_file(mocker: MockerFixture) -> None:
    adapter = ZorgABMockHydrationAdapter(
        logger=mocker.Mock(Logger),
    )

    response = adapter.search_organizations(search=SearchRequest(name="test", city="test"))

    assert response is not None
    assert len(response.organizations) >= 1
    assert response.organizations[0].display_name == "Apotheek Janssen"
    assert response.organizations[0].addresses
    assert response.organizations[0].addresses[0].city


TEST_JSON: str = """
[
  {
    "_self": "/organizations/1",
    "_className": "CSC.HPD.Organization",
    "_id": "1",
    "addresses": [
    ],
    "applicationIds": [
      "12345678"
    ],
    "attachments": null,
    "author": "Vektis",
    "comment": null,
    "credentials": null,
    "displayName": "Apotheek Janssen",
    "electronicServices": [
      {
        "_className": "CSC.HPD.LSP.Application",
        "active": true,
        "address": "janssen.voorbeeld.nl",
        "applicationId": "12345678",
        "author": "LSP",
        "conformances": [
          {
            "interactionId": "COMT_IN113113NL",
            "receive": true,
            "send": true
          }
        ],
        "description": null,
        "index": "1",
        "status": "active",
        "systemRoles": [
          "AllPurpose"
        ],
        "timestamp": "2020-08-24 13:48:56.726"
      }
    ],
    "identifications": [
      {
        "active": true,
        "author": "UZI",
        "description": null,
        "index": "1",
        "timestamp": "2020-11-03 12:49:40.265",
        "type": "URA",
        "value": "12345678"
      }
    ],
    "names": [
      {
        "active": true,
        "author": "Vektis",
        "fullName": "Apotheek Janssen",
        "index": "1",
        "preferred": false,
        "timestamp": "2020-11-03 12:49:40.265",
        "type": "Display"
      }
    ],
    "speciality": null,
    "telecoms": [
      {
        "active": true,
        "author": "Vektis",
        "index": "1",
        "name": "Algemeen",
        "preferred": false,
        "timestamp": "2020-08-24 13:39:19.313",
        "type": "Phone",
        "value": "012-3456789"
      }
    ],
    "timestamp": "2020-11-03 12:49:40.265",
    "type": null,
    "types": [
      {
        "active": true,
        "author": "Vektis",
        "code": "02",
        "displayName": "Apothekers",
        "index": "1",
        "timestamp": "2020-11-03 12:49:40.265",
        "type": "Vektis Zorgsoort"
      },
      {
        "active": true,
        "author": "VZVZ",
        "code": "Z001",
        "displayName": "Apotheek",
        "index": "2",
        "timestamp": "2020-11-03 12:49:40.265",
        "type": "VZVZ"
      },
      {
        "active": true,
        "author": "VZVZ",
        "code": "J8",
        "displayName": "Openbare apotheek",
        "index": "3",
        "timestamp": "2020-11-03 12:49:40.265",
        "type": "NICTIZ"
      }
    ],
    "ura": "12345678"
  }
]
"""

TEST_JSON_ADDRESS: str = """
[
    {
        "city": "Utrecht",
        "extension": [
            {
                "url": "http://www.vzvz.nl/fhir/StructureDefinition/author",
                "valueString": "URA:00002727"
            }
        ],
        "line": [
            "Orteliuslaan 1004"
        ],
        "postalCode": "3528 BD",
        "text": "Orteliuslaan 1004\\r\\n3528 BD Utrecht",
        "type": "physical",
        "use": "work"
    }
]
"""
