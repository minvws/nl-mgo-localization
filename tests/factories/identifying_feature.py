from typing import Any

from faker import Faker

from app.db.models import IdentifyingFeature
from app.db.repositories import IdentifyingFeatureRepository

from .organisation import make_organisation

faker = Faker()


def make_identifying_feature(data: dict[str, Any]) -> IdentifyingFeature:
    organisation = make_organisation() if "organisation" not in data else data["organisation"]

    return IdentifyingFeature(
        id=data["id"] if "id" in data else faker.random_int(min=1),
        organisation_id=organisation.id,
        type=data["type"] if "type" in data else faker.word(),
        value=data["value"] if "value" in data else faker.word(),
        import_ref=organisation.import_ref,
    )


def create_identifying_feature(
    data: dict[str, Any], identifying_feature_repository: IdentifyingFeatureRepository
) -> IdentifyingFeature:
    identifying_feature: IdentifyingFeature = (
        make_identifying_feature(data) if "identifying_feature" not in data else data["identifying_feature"]
    )

    identifying_feature_repository.create(
        organisation_id=identifying_feature.organisation_id,
        type=identifying_feature.type,
        value=identifying_feature.value,
        import_ref=identifying_feature.import_ref,
        persist=True,
    )

    return identifying_feature
