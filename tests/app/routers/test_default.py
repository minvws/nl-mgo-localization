from fastapi.testclient import TestClient

from app.constants import APP_NAME


def test_root_endpoint_returns_service_name(test_client: TestClient) -> None:
    response = test_client.get("/")

    assert response.status_code == 200
    assert response.text == APP_NAME
