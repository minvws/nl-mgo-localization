from typing import Generator

import inject
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.db import Database
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
def db_session(db_wrapper: Database) -> Generator[Session, None, None]:
    session = Session(db_wrapper.engine)
    yield session
    session.rollback()
    session.close()


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


""" Repository fixtures"""


@pytest.fixture(scope="function")
def organisation_repository(db_session: Session) -> OrganisationRepository:
    repository: OrganisationRepository = OrganisationRepository(db_session)
    return repository


@pytest.fixture(scope="function")
def identifying_feature_repository(db_session: Session) -> IdentifyingFeatureRepository:
    repository: IdentifyingFeatureRepository = IdentifyingFeatureRepository(db_session)
    return repository


@pytest.fixture(scope="function")
def data_service_repository(db_session: Session) -> DataServiceRepository:
    repository: DataServiceRepository = DataServiceRepository(db_session)
    return repository


@pytest.fixture(scope="function")
def system_role_repository(db_session: Session) -> SystemRoleRepository:
    repository: SystemRoleRepository = SystemRoleRepository(db_session)
    return repository


@pytest.fixture(scope="function")
def endpoint_repository(db_session: Session) -> EndpointRepository:
    repository: EndpointRepository = EndpointRepository(db_session)
    return repository
