from typing import Any

from faker import Faker

from app.db.models import SystemRole

from .endpoint import make_endpoint

faker = Faker()


def make_system_role(data: dict[str, Any] | None = None) -> SystemRole:  # type: ignore[explicit-any]
    data = data or {}
    return SystemRole(
        id=data.get("id", faker.random_int(min=1)),
        code=data.get("code", faker.word()),
        resource_endpoint=(data.get("resource_endpoint") or make_endpoint()),
    )
