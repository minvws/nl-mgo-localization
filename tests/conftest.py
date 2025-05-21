from typing import Generator

import inject
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.db import Database
from app.db.db_session import DbSession
from app.db.repositories import (
    DataServiceRepository,
    EndpointRepository,
    IdentifyingFeatureRepository,
    OrganisationRepository,
    SystemRoleRepository,
)
from app.main import create_fastapi_app
from tests.utils import clear_bindings, configure_bindings


@pytest.fixture()
def test_client() -> Generator[TestClient, None, None]:
    configure_bindings()
    yield TestClient(create_fastapi_app())
    clear_bindings()


@pytest.fixture(scope="function")
def db_wrapper(test_client: TestClient) -> Generator[Database, None, None]:
    database: Database = inject.instance(Database)
    database.generate_tables()
    yield database
    database.drop_tables()


@pytest.fixture(scope="function")
def db_session(db_wrapper: Database) -> Generator[DbSession, None, None]:
    session = db_wrapper.get_db_session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


""" Repository fixtures"""


@pytest.fixture(scope="function")
def organisation_repository(db_session: Session) -> OrganisationRepository:
    return OrganisationRepository(db_session)


@pytest.fixture(scope="function")
def identifying_feature_repository(db_session: Session) -> IdentifyingFeatureRepository:
    return IdentifyingFeatureRepository(db_session)


@pytest.fixture(scope="function")
def data_service_repository(db_session: Session) -> DataServiceRepository:
    return DataServiceRepository(db_session)


@pytest.fixture(scope="function")
def system_role_repository(db_session: Session) -> SystemRoleRepository:
    return SystemRoleRepository(db_session)


@pytest.fixture(scope="function")
def endpoint_repository(db_session: Session) -> EndpointRepository:
    return EndpointRepository(db_session)
