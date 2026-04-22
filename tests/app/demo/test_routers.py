import pytest
from faker import Faker
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from app.addressing.services import EndpointJWEWrapper
from tests.utils import configure_bindings

faker = Faker()


@pytest.fixture
def non_encrypting_client(test_client: TestClient, mocker: MockerFixture) -> TestClient:
    """
    Returns a test client that does not perform actual encryption, for testing purposes.
    """
    mock_endpoint_jwe_wrapper = mocker.Mock(spec=EndpointJWEWrapper)
    mock_endpoint_jwe_wrapper.wrap.side_effect = lambda url: f"wrapped:{url}"

    configure_bindings(bindings_override=lambda binder: binder.bind(EndpointJWEWrapper, mock_endpoint_jwe_wrapper))

    return test_client


@pytest.mark.parametrize(
    "expected_name",
    [
        "Ziekenhuis Nieuw Juinen",
        "Huisartspraktijk Heideroosje",
        "RIVM",
        "Fysiotherapiepraktijk De Toekomst",
        "Apotheek Aanstalten",
        "Verpleeghuis Tante Bianca",
        "J. Foudrainekliniek",
    ],
)
def test_it_can_get_the_demo_healthcare_organizations_from_the_demo_endpoint(
    non_encrypting_client: TestClient,
    expected_name: str,
) -> None:
    response = non_encrypting_client.post("/localization/organization/search-demo")
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
            "J. Foudrainekliniek",
            [
                {"name": "Basisgegevens GGZ", "id": "50"},
            ],
        ),
        (
            "Verpleeghuis Tante Bianca",
            [
                {"name": "Basisgegevens Langdurige Zorg", "id": "61"},
            ],
        ),
    ],
)
def test_organizations_have_correct_data_services(
    non_encrypting_client: TestClient, display_name: str, expected_data_services: list[dict[str, str]]
) -> None:
    response = non_encrypting_client.post("/localization/organization/search-demo")
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
            assert role["resource_endpoint"].startswith("wrapped:")


def test_tante_bianca_has_signed_data_service_61_url(non_encrypting_client: TestClient) -> None:
    response = non_encrypting_client.post("/localization/organization/search-demo")
    assert response.status_code == 200

    tante_bianca = next(
        (org for org in response.json()["organizations"] if org["display_name"] == "Verpleeghuis Tante Bianca"),
        None,
    )

    assert tante_bianca is not None, "Verpleeghuis Tante Bianca should be present in the demo organizations"

    data_service_61 = next(
        (service for service in tante_bianca["data_services"] if service["id"] == "61"),
        None,
    )

    assert data_service_61 is not None, "Verpleeghuis Tante Bianca should have data service with id '61'"
    assert len(data_service_61["roles"]) > 0, "Data service 61 should have at least one role"

    for role in data_service_61["roles"]:
        assert role["resource_endpoint"].startswith("wrapped:"), (
            f"Role '{role.get('name', 'unknown')}' should have an enveloped URL"
        )
