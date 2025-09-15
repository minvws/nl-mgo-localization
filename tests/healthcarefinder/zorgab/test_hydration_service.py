from logging import Logger
from typing import Any, Dict, List, cast

import pytest
from faker import Faker
from fhir.resources.STU3.organization import Organization as FhirOrganization
from pytest_mock import MockerFixture

from app.addressing.addressing_service import AddressingService
from app.addressing.mock.mock_adapter import AddressingMockAdapter
from app.addressing.models import ZalDataServiceResponse, ZalSearchResponseEntry
from app.healthcarefinder.models import Organization as LoadOrganization
from app.healthcarefinder.zorgab.hydration_service import HydrationService


def __get_address() -> List[Dict[str, Any]]:
    return [
        {
            "city": "Utrecht",
            "extension": [
                {"url": "http://www.vzvz.nl/fhir/StructureDefinition/author", "valueString": "URA:90000382"},
                {
                    "extension": [
                        {"url": "latitude", "valueDecimal": 121871},
                        {"url": "longitude", "valueDecimal": 487449},
                    ],
                    "url": "https://hl7.org/fhir/StructureDefinition/geolocation",
                },
            ],
            "line": ["Poststreet 1005"],
            "postalCode": "3528 BD",
            "text": "Poststreet 1005\r\n3528 BD Utrecht",
            "type": "physical",
            "use": "work",
        },
    ]


def __get_address_with_empty_extension() -> List[Dict[str, Any]]:
    return [
        {
            "city": "Utrecht",
            "extension": [],
            "line": ["Poststreet 1005"],
            "postalCode": "3528 BD",
            "text": "Poststreet 1005\r\n3528 BD Utrecht",
            "type": "physical",
            "use": "work",
        },
    ]


def __get_identifier() -> List[Dict[str, Any]]:
    return [
        {
            "extension": [{"url": "http://www.vzvz.nl/fhir/StructureDefinition/author", "valueString": "Vektis"}],
            "system": "http://fhir.nl/fhir/NamingSystem/agb-z",
            "value": "71025100",
        }
    ]


def __get_type() -> List[Dict[str, Any]]:
    return [
        {
            "coding": [
                {
                    "code": "84",
                    "display": "Overige Artsen",
                    "system": "http://www.vzvz.nl/fhir/NamingSystem/vektis-zorgsoort",
                }
            ],
            "extension": [{"url": "http://www.vzvz.nl/fhir/StructureDefinition/author", "valueString": "Vektis"}],
        }
    ]


def __get_valueless_type() -> List[Dict[str, Any]]:
    return [
        {
            "coding": [
                {
                    "code": None,
                    "display": None,
                    "system": None,
                }
            ],
            "extension": [{"url": "http://www.vzvz.nl/fhir/StructureDefinition/author", "valueString": "Vektis"}],
        }
    ]


@pytest.fixture
def create_fhir_organization_full() -> FhirOrganization:
    data = {
        "id": "f001",
        "identifier": __get_identifier(),
        "active": True,
        "name": "Acme Corporation",
        "address": __get_address(),
        "type": __get_type(),
    }
    return FhirOrganization.model_validate(data)


@pytest.fixture
def create_fhir_organization_without_address() -> FhirOrganization:
    data = {
        "id": "f001",
        "identifier": __get_identifier(),
        "active": True,
        "name": "Acme Corporation",
    }
    return FhirOrganization.model_validate(data)


@pytest.fixture
def create_fhir_organization_without_identifier() -> FhirOrganization:
    data = {
        "id": "f001",
        "active": True,
        "name": "Acme Corporation",
    }
    return FhirOrganization.model_validate(data)


@pytest.fixture
def create_fhir_organization_with_valueless_type() -> FhirOrganization:
    data = {
        "id": "f001",
        "identifier": __get_identifier(),
        "active": True,
        "name": "Acme Corporation",
        "address": __get_address(),
        "type": __get_valueless_type(),
    }
    return FhirOrganization.model_validate(data)


def test_hydrate_to_organization(mocker: MockerFixture, create_fhir_organization_full: FhirOrganization) -> None:
    hydration_service = HydrationService(
        addressing_service=cast(AddressingService, AddressingMockAdapter()),
        logger=mocker.Mock(spec=Logger),
    )
    org = hydration_service.hydrate_to_organization(create_fhir_organization_full)

    assert isinstance(org, LoadOrganization)
    assert org.display_name == "Acme Corporation"
    assert isinstance(org.data_services[0], ZalDataServiceResponse)


def test_hydrate_to_organization_missing_address(
    mocker: MockerFixture, create_fhir_organization_without_address: FhirOrganization
) -> None:
    hydration_service = HydrationService(
        addressing_service=cast(AddressingService, AddressingMockAdapter()),
        logger=mocker.Mock(spec=Logger),
    )
    org = hydration_service.hydrate_to_organization(create_fhir_organization_without_address)

    assert isinstance(org, LoadOrganization)
    assert org.display_name == "Acme Corporation"
    assert len(org.addresses) == 0
    assert isinstance(org.data_services[0], ZalDataServiceResponse)


def test_hydrate_to_organization_temporarily_uses_random_uuid_for_missing_identifier(
    mocker: MockerFixture,
    faker: Faker,
    create_fhir_organization_without_identifier: FhirOrganization,
) -> None:
    addressing_mock_adapter = AddressingMockAdapter(
        sign_endpoints=False,
        mock_base_url="http://mock-base-url",
        signing_service=mocker.Mock(),
    )

    random_uuid = faker.uuid4()
    mocker.patch("app.healthcarefinder.zorgab.hydration_service.uuid4", return_value=random_uuid)
    mock_logger = mocker.Mock(spec=Logger)
    hydration_service = HydrationService(
        addressing_service=cast(AddressingService, addressing_mock_adapter),
        logger=mock_logger,
    )

    org = hydration_service.hydrate_to_organization(create_fhir_organization_without_identifier)

    assert org.identification == random_uuid
    mock_logger.warning.assert_called_once_with(
        "No identifier found in FHIR Organization. Generated random uuid '%s' for identifier to avoid a crash.",
        random_uuid,
    )


def test_hydrate_to_organization_no_matching_organization(
    mocker: MockerFixture, create_fhir_organization_full: FhirOrganization
) -> None:
    addressing_service = mocker.Mock(AddressingService)
    addressing_service.search_by_agb.return_value = None

    hydration_service = HydrationService(
        addressing_service=addressing_service,
        logger=mocker.Mock(spec=Logger),
    )
    org = hydration_service.hydrate_to_organization(create_fhir_organization_full)

    assert isinstance(org, LoadOrganization)
    assert org.medmij_id is None


def test_hydrate_to_organization_matching_organization(
    mocker: MockerFixture, create_fhir_organization_full: FhirOrganization
) -> None:
    fake = Faker()
    addressing_service = mocker.Mock(AddressingService)
    fake_medmij_id = fake.email()

    addressing_service.search_by_agb.return_value = ZalSearchResponseEntry(
        medmij_id=fake_medmij_id,
        dataservices=[],
        organization_type="test_type",
        id_type=str(fake.word()),
        id_value=str(fake.unique.random_number(digits=8, fix_len=True)),
    )

    hydration_service = HydrationService(
        addressing_service=addressing_service,
        logger=mocker.Mock(spec=Logger),
    )
    org = hydration_service.hydrate_to_organization(create_fhir_organization_full)

    assert isinstance(org, LoadOrganization)
    assert org.medmij_id == fake_medmij_id


def test_hydrate_to_organization_handles_type_without_values(
    mocker: MockerFixture, create_fhir_organization_with_valueless_type: FhirOrganization
) -> None:
    hydration_service = HydrationService(
        addressing_service=cast(AddressingService, AddressingMockAdapter()),
        logger=mocker.Mock(spec=Logger),
    )
    org = hydration_service.hydrate_to_organization(create_fhir_organization_with_valueless_type)

    assert isinstance(org, LoadOrganization)
    assert len(org.types) == 1
    assert org.types[0].code == ""
    assert org.types[0].display_name == ""
    assert org.types[0].type == ""


def test_hydrate_to_organization_with_empty_address_extension(mocker: MockerFixture) -> None:
    data = {
        "id": "f001",
        "identifier": __get_identifier(),
        "active": True,
        "name": "Acme Corporation",
        "address": __get_address_with_empty_extension(),
        "type": __get_type(),
    }
    fhir_org = FhirOrganization.model_validate(data)
    addressing_service = mocker.Mock(AddressingService)
    addressing_service.search_by_agb.return_value = ZalSearchResponseEntry(
        medmij_id="mock@medmij",
        dataservices=[
            ZalDataServiceResponse(
                id="1", name="Test", interface_versions=["1"], auth_endpoint="auth", token_endpoint="token", roles=[]
            )
        ],
        organization_type="test_type",
        id_type="agb-z",
        id_value="71025100",
    )
    hydration_service = HydrationService(
        addressing_service=addressing_service,
        logger=mocker.Mock(spec=Logger),
    )
    org = hydration_service.hydrate_to_organization(fhir_org)
    assert isinstance(org, LoadOrganization)
    assert org.display_name == "Acme Corporation"
    assert len(org.addresses) == 1
    assert org.addresses[0].geolocation is None
