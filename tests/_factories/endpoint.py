from typing import Any

from faker import Faker

from app.db.models import Endpoint

faker = Faker()


def make_endpoint(data: dict[str, Any] | None = None) -> Endpoint:  # type: ignore[explicit-any]
    data = data or {}
    return Endpoint(
        id=data["id"] if "id" in data else faker.random_int(min=1),
        url=data["url"] if "url" in data else faker.url(),
    )
