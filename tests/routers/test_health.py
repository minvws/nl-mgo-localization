from fastapi.testclient import TestClient
from inject import Binder
from pytest_mock import MockerFixture

from app.db.db import Database
from app.healthcarefinder.interface import HealthcareFinderAdapter
from app.healthcarefinder.zorgab.zorgab import ZorgABAdapter
from tests.utils import configure_bindings


def test_health_endpoint_with_healthy_database(test_client: TestClient, mocker: MockerFixture) -> None:
    db = mocker.MagicMock(Database)
    db.is_healthy.return_value = True

    def bindings_override(binder: Binder) -> Binder:
        binder.bind(Database, db)
        binder.bind(HealthcareFinderAdapter, mocker.MagicMock(HealthcareFinderAdapter))

        return binder

    configure_bindings(bindings_override)

    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "healthy": True,
        "externals": {
            "database": True,
        },
    }


def test_health_endpoint_with_unhealthy_database(test_client: TestClient, mocker: MockerFixture) -> None:
    db = mocker.MagicMock(Database)
    db.is_healthy.return_value = False

    def bindings_override(binder: Binder) -> Binder:
        binder.bind(Database, db)
        binder.bind(HealthcareFinderAdapter, mocker.MagicMock(HealthcareFinderAdapter))

        return binder

    configure_bindings(bindings_override)

    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "healthy": False,
        "externals": {
            "database": False,
        },
    }


def test_health_endpoint_with_zorgab_healthy(test_client: TestClient, mocker: MockerFixture) -> None:
    db = mocker.MagicMock(Database)
    db.is_healthy.return_value = True

    zorgab = mocker.MagicMock(ZorgABAdapter)
    zorgab.verify_connection.return_value = True

    def bindings_override(binder: Binder) -> Binder:
        binder.bind(Database, db)
        binder.bind(HealthcareFinderAdapter, zorgab)
        return binder

    configure_bindings(bindings_override)

    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "healthy": True,
        "externals": {
            "database": True,
            "zorgab": True,
        },
    }


def test_health_endpoint_with_zorgab_unhealthy(test_client: TestClient, mocker: MockerFixture) -> None:
    db = mocker.MagicMock(Database)
    db.is_healthy.return_value = True

    zorgab = mocker.MagicMock(ZorgABAdapter)
    zorgab.verify_connection.return_value = False

    def bindings_override(binder: Binder) -> Binder:
        binder.bind(Database, db)
        binder.bind(HealthcareFinderAdapter, zorgab)
        return binder

    configure_bindings(bindings_override)

    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "healthy": False,
        "externals": {
            "database": True,
            "zorgab": False,
        },
    }


def test_health_endpoint_with_everything_unhealty(test_client: TestClient, mocker: MockerFixture) -> None:
    db = mocker.MagicMock(Database)
    db.is_healthy.return_value = False

    zorgab = mocker.MagicMock(ZorgABAdapter)
    zorgab.verify_connection.return_value = False

    def bindings_override(binder: Binder) -> Binder:
        binder.bind(Database, db)
        binder.bind(HealthcareFinderAdapter, zorgab)

        return binder

    configure_bindings(bindings_override)
    response = test_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "healthy": False,
        "externals": {
            "database": False,
            "zorgab": False,
        },
    }
