from typing import Any

from faker import Faker

from app.db.models import DataService
from app.db.repositories import DataServiceRepository, DbEndpointRepository

from .endpoint import make_endpoint
from .organisation import make_organisation
from .system_role import make_system_role

faker = Faker()


def make_dataservice(data: dict[str, Any] | None = None) -> DataService:  # type: ignore[explicit-any]
    data = data or {}

    data_service = DataService(
        id=data.get("id", faker.random_int(min=1)),
        organisation_id=(data.get("organisation") or make_organisation()).id,
        external_id=data.get("external_id", faker.word()),
        name=data.get("name", faker.word()),
        interface_versions=data.get("interface_versions", faker.random_int(min=1)),
        auth_endpoint=(data.get("auth_endpoint") or make_endpoint()),
        token_endpoint=(data.get("token_endpoint") or make_endpoint()),
    )

    roles = data.get("roles", [make_system_role()])
    for role in roles:
        role.data_service = data_service

    data_service.roles = roles

    return data_service


def create_dataservice(  # type: ignore[explicit-any]
    dataservice_repository: DataServiceRepository,
    endpoint_repository: DbEndpointRepository,
    data: dict[str, Any] | None = None,
) -> DataService:
    data = data or {}

    organisation = data["organisation"]
    auth_endpoint = make_endpoint() if "auth_endpoint" not in data else data["auth_endpoint"]
    token_endpoint = make_endpoint() if "token_endpoint" not in data else data["token_endpoint"]

    auth_endpoint_id = endpoint_repository.create(url=auth_endpoint.url, persist=True).id
    token_endpoint_id = endpoint_repository.create(url=token_endpoint.url, persist=True).id

    dataservice = make_dataservice(data)

    dataservice_repository.create(
        organisation_id=organisation.id,
        external_id=dataservice.external_id,
        name=dataservice.name,
        interface_versions=[dataservice.interface_versions],
        auth_endpoint_id=auth_endpoint_id,
        token_endpoint_id=token_endpoint_id,
        persist=True,
    )

    return dataservice
