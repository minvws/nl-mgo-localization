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
