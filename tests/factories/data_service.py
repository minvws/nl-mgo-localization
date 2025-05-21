from typing import Any

from faker import Faker

from app.db.models import DataService, Endpoint
from app.db.repositories import DataServiceRepository, EndpointRepository

from .organisation import make_organisation

faker = Faker()


def make_endpoint(data: dict[str, Any] | None = None) -> Endpoint:
    data = data or {}
    return Endpoint(
        id=data.get("id", faker.random_int(min=1)),
        url=data.get("url", faker.word()),
        signature=data.get("signature", faker.url()),
    )


def make_dataservice(data: dict[str, Any] | None = None) -> DataService:
    data = data or {}
    return DataService(
        id=data.get("id", faker.random_int(min=1)),
        organisation_id=(data.get("organisation") or make_organisation()).id,
        external_id=data.get("external_id", faker.word()),
        name=data.get("name", faker.word()),
        interface_versions=data.get("interface_versions", faker.random_int(min=1)),
        auth_endpoint_id=(data.get("auth_endpoint") or make_endpoint()).id,
        token_endpoint_id=(data.get("token_endpoint") or make_endpoint()).id,
    )


def create_dataservice(
    dataservice_repository: DataServiceRepository,
    endpoint_repository: EndpointRepository,
    data: dict[str, Any] | None = None,
) -> DataService:
    data = data or {}

    organisation = data["organisation"]
    auth_endpoint = make_endpoint() if "auth_endpoint" not in data else data["auth_endpoint"]
    token_endpoint = make_endpoint() if "token_endpoint" not in data else data["token_endpoint"]

    endpoint_repository.create(
        url=auth_endpoint.url,
        signature=auth_endpoint.signature,
        persist=True,
    )

    endpoint_repository.create(
        url=token_endpoint.url,
        signature=token_endpoint.signature,
        persist=True,
    )

    dataservice = make_dataservice(data)

    dataservice_repository.create(
        organisation_id=organisation.id,
        external_id=dataservice.external_id,
        name=dataservice.name,
        interface_versions=[dataservice.interface_versions],
        auth_endpoint_id=auth_endpoint.id,
        token_endpoint_id=token_endpoint.id,
        persist=True,
    )

    return dataservice
