import pytest
from faker import Faker
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from app.addressing.constants import SIGNATURE_PARAM_NAME

faker = Faker()


@pytest.fixture()
def patches(mocker: MockerFixture) -> None:
    mocker.patch("app.addressing.signing_service.SigningService.generate_signature", return_value=faker.sha256())
    mocker.patch("app.addressing.signing_service.SigningService.ensure_private_key_loaded", return_value=None)
    mocker.patch("app.addressing.signing_service.KeyRepository.load_private_key", return_value=faker.sha256())


@pytest.mark.parametrize(
    "expected_name",
    [
        "Ziekenhuis Nieuw Juinen",
        "Huisartspraktijk Heideroosje",
        "RIVM",
        "Fysiotherapiepraktijk De Toekomst",
        "Apotheek Aanstalten",
        "Tante Bianca",
    ],
)
def test_it_can_get_the_demo_healthcare_providers_from_the_demo_endpoint(
    test_client: TestClient, expected_name: str, patches: None
) -> None:
    response = test_client.post("/localization/organization/search-demo")
    assert response.status_code == 200

    assert any(organisation["display_name"] == expected_name for organisation in response.json()["organizations"])


@pytest.mark.parametrize(
    "display_name, expected_data_services",
    [
        (
            "Ziekenhuis Nieuw Juinen",
            [
                {"name": "Basisgegevens Zorg", "id": "48"},
                {"name": "Documenten", "id": "51"},
            ],
        ),
        (
            "Huisartspraktijk Heideroosje",
            [
                {"name": "Huisartsgegevens", "id": "49"},
                {"name": "Documenten", "id": "51"},
            ],
        ),
        (
            "RIVM",
            [
                {"name": "Vaccinatiegegevens", "id": "63"},
            ],
        ),
        ("Fysiotherapiepraktijk De Toekomst", []),
        ("Apotheek Aanstalten", []),
        (
            "Tante Bianca",
            [
                {"name": "Basisgegevens Langdurige Zorg", "id": "61"},
            ],
        ),
    ],
)
def test_organizations_have_correct_data_services(
    test_client: TestClient, display_name: str, expected_data_services: list[dict[str, str]], patches: None
) -> None:
    response = test_client.post("/localization/organization/search-demo")
    assert response.status_code == 200

    organisation = next(
        (org for org in response.json()["organizations"] if org["display_name"] == display_name),
        None,
    )

    assert organisation is not None
    assert "data_services" in organisation

    data_services = organisation["data_services"]
    assert len(data_services) == len(expected_data_services)

    for expected_service in expected_data_services:
        assert any(
            data_service["name"] == expected_service["name"] and data_service["id"] == expected_service["id"]
            for data_service in data_services
        )

    for data_service in data_services:
        for role in data_service["roles"]:
            assert SIGNATURE_PARAM_NAME in role["resource_endpoint"]


def test_tante_bianca_has_signed_data_service_61_url(test_client: TestClient, patches: None) -> None:
    response = test_client.post("/localization/organization/search-demo")
    assert response.status_code == 200

    tante_bianca = next(
        (org for org in response.json()["organizations"] if org["display_name"] == "Tante Bianca"),
        None,
    )

    assert tante_bianca is not None, "Tante Bianca should be present in the demo organizations"

    data_service_61 = next(
        (service for service in tante_bianca["data_services"] if service["id"] == "61"),
        None,
    )

    assert data_service_61 is not None, "Tante Bianca should have data service with id '61'"
    assert len(data_service_61["roles"]) > 0, "Data service 61 should have at least one role"

    for role in data_service_61["roles"]:
        assert SIGNATURE_PARAM_NAME in role["resource_endpoint"], (
            f"Role '{role.get('name', 'unknown')}' should have a signed URL containing '{SIGNATURE_PARAM_NAME}'"
        )
