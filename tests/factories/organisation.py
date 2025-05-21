from typing import Any

from faker import Faker

from app.db.models import Organisation
from app.db.repositories import OrganisationRepository
from app.zal_importer.enums import OrganisationType

faker = Faker()


def make_organisation(data: dict[str, Any] | None = None) -> Organisation:
    data = data or {}
    return Organisation(
        id=data["id"] if "id" in data else faker.random_int(min=1),
        name=data["name"] if "name" in data else faker.company(),
        type=data["type"] if "type" in data else faker.random_element(elements=[e for e in OrganisationType]),
        import_ref=data["import_ref"] if "import_ref" in data else faker.numerify("%##############%%%"),
    )


def create_organisation(repo: OrganisationRepository, data: dict[str, Any] | None = None) -> Organisation:
    data = data or {}
    organisation = make_organisation(data)
    repo.create(
        name=organisation.name,
        type=organisation.type,
        import_ref=organisation.import_ref,
        persist=True,
    )

    return organisation
