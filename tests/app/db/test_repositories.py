import json
from base64 import b64encode
from datetime import datetime
from os import urandom
from typing import Generator, List

from faker import Faker
from pytest import fixture, mark

from app.db.models import Base, DataService, Endpoint, IdentifyingFeature, Organisation
from app.db.repositories import (
    BaseRepository,
    DataServiceRepository,
    EndpointRepository,
    IdentifyingFeatureRepository,
    OrganisationRepository,
    SystemRoleRepository,
    repository,
    repository_registry,
)
from app.zal_importer.enums import IdentifyingFeatureType, OrganisationType


def create_organisation(
    repository: OrganisationRepository,
    faker: Faker,
    name: str | None = None,
    type: OrganisationType | None = None,
    import_ref: str | None = None,
) -> tuple[str, OrganisationType, str, Organisation]:
    return (
        name := name or faker.word(),
        type := type or faker.random_element(elements=[e for e in OrganisationType]),
        import_ref := import_ref or faker.numerify("%##############%%%"),
        repository.create(name=name, type=type, import_ref=import_ref, persist=False),
    )


def create_identifying_feature(
    repository: IdentifyingFeatureRepository,
    faker: Faker,
    organisation_id: int,
    type: IdentifyingFeatureType | None = None,
    value: str | None = None,
    import_ref: str | None = None,
) -> tuple[IdentifyingFeatureType, str, str, IdentifyingFeature]:
    return (
        type := type or faker.random_element(elements=[e for e in IdentifyingFeatureType]),
        value := value or faker.numerify("########"),
        import_ref := import_ref or faker.numerify("%##############%%%"),
        repository.create(
            organisation_id=organisation_id,
            type=type,
            value=value,
            import_ref=import_ref,
            persist=False,
        ),
    )


def create_data_service(
    repository: DataServiceRepository,
    faker: Faker,
    organisation_id: int,
    auth_endpoint_id: int,
    token_endpoint_id: int,
    external_id: str | None = None,
    name: str | None = None,
    interface_versions: List[str] | None = None,
) -> tuple[str, str, List[str], DataService]:
    return (
        external_id := external_id or faker.numerify("%%"),
        name := name or faker.word(),
        interface_versions := interface_versions or [faker.numerify("#.#.#")],
        repository.create(
            organisation_id=organisation_id,
            external_id=external_id,
            auth_endpoint_id=auth_endpoint_id,
            token_endpoint_id=token_endpoint_id,
            name=name,
            interface_versions=interface_versions,
            persist=False,
        ),
    )


def create_endpoint(
    repository: EndpointRepository,
    faker: Faker,
    url: str | None = None,
    signature: str | None = None,
) -> tuple[str, str, Endpoint]:
    return (
        url := url or faker.url(),
        signature := signature or b64encode(urandom(32)).decode("utf-8"),
        repository.create(url=url, signature=signature, persist=False),
    )


@mark.usefixtures("organisation_repository", "identifying_feature_repository")
class TestOrganisationRepository:
    def test_create_stores_organisation(self, organisation_repository: OrganisationRepository, faker: Faker) -> None:
        name, type, import_ref, result = create_organisation(organisation_repository, faker)

        assert result.id > 0
        assert result.name == name
        assert result.type == type
        assert result.import_ref == import_ref

    def test_find_one_by_name_returns_matching_organisation(
        self,
        organisation_repository: OrganisationRepository,
        faker: Faker,
    ) -> None:
        name = faker.word()
        organisation = create_organisation(organisation_repository, faker, name=name)[3]

        result = organisation_repository.find_one_by_name(name)

        assert result is not None
        assert result.id == organisation.id

    def test_find_one_by_name_returns_latest_imported_organisation_by_timestamp(
        self,
        organisation_repository: OrganisationRepository,
        faker: Faker,
    ) -> None:
        now = int(datetime.now().timestamp())
        minute_ago = now - 60
        serial_number = "5"
        name = faker.word()
        latest_imported_organisation = create_organisation(
            organisation_repository,
            faker,
            name=name,
            import_ref=f"{now}{serial_number.zfill(6)}",
        )[3]
        create_organisation(
            organisation_repository,
            faker,
            name=name,
            import_ref=f"{minute_ago}{serial_number.zfill(6)}",
        )

        result = organisation_repository.find_one_by_name(name)

        assert result is not None
        assert result.id == latest_imported_organisation.id

    def test_find_one_by_name_returns_latest_imported_organisation_by_serial_number(
        self,
        organisation_repository: OrganisationRepository,
        faker: Faker,
    ) -> None:
        now = int(datetime.now().timestamp())
        name = faker.word()
        latest_imported_organisation = create_organisation(
            organisation_repository,
            faker,
            name=name,
            import_ref=f"{now}{'10'.zfill(6)}",
        )[3]
        create_organisation(
            organisation_repository,
            faker,
            name=name,
            import_ref=f"{now}{'9'.zfill(6)}",
        )

        result = organisation_repository.find_one_by_name(name)

        assert result is not None
        assert result.id == latest_imported_organisation.id

    def test_find_one_by_name_returns_none_when_organisation_is_not_found(
        self, organisation_repository: OrganisationRepository, faker: Faker
    ) -> None:
        now = int(datetime.now().timestamp())
        latest_organisation_name = "foo"
        outdated_organisation_name = "bar"
        create_organisation(
            organisation_repository,
            faker,
            name=latest_organisation_name,
            import_ref=f"{now}{'10'.zfill(6)}",
        )
        create_organisation(
            organisation_repository,
            faker,
            name=outdated_organisation_name,
            import_ref=f"{now}{'9'.zfill(6)}",
        )

        result = organisation_repository.find_one_by_name(outdated_organisation_name)

        assert result is None

    def test_find_one_by_identifying_feature_returns_matching_organisation(
        self,
        organisation_repository: OrganisationRepository,
        identifying_feature_repository: IdentifyingFeatureRepository,
        faker: Faker,
    ) -> None:
        organisation = create_organisation(repository=organisation_repository, faker=faker)[3]
        type, value, _, _ = create_identifying_feature(
            repository=identifying_feature_repository,
            faker=faker,
            organisation_id=organisation.id,
        )

        result = organisation_repository.find_one_by_identifying_feature(type, value)

        assert result is not None
        assert result.id == organisation.id

    def test_find_one_by_identifying_feature_returns_none_when_type_does_not_match(
        self,
        organisation_repository: OrganisationRepository,
        identifying_feature_repository: IdentifyingFeatureRepository,
        faker: Faker,
    ) -> None:
        organisation = create_organisation(repository=organisation_repository, faker=faker)[3]
        value = create_identifying_feature(
            repository=identifying_feature_repository,
            faker=faker,
            organisation_id=organisation.id,
            type=IdentifyingFeatureType.HRN,
        )[1]

        result = organisation_repository.find_one_by_identifying_feature(IdentifyingFeatureType.AGB, value)

        assert result is None

    def test_find_one_by_identifying_feature_returns_none_when_value_does_not_match(
        self,
        organisation_repository: OrganisationRepository,
        identifying_feature_repository: IdentifyingFeatureRepository,
        faker: Faker,
    ) -> None:
        organisation = create_organisation(repository=organisation_repository, faker=faker)[3]
        type = create_identifying_feature(
            repository=identifying_feature_repository,
            faker=faker,
            organisation_id=organisation.id,
            value="123",
        )[0]

        result = organisation_repository.find_one_by_identifying_feature(type, "456")

        assert result is None

    def test_import_ref_exists_returns_true_when_exists(
        self,
        organisation_repository: OrganisationRepository,
        faker: Faker,
    ) -> None:
        import_ref = create_organisation(repository=organisation_repository, faker=faker)[2]

        assert organisation_repository.has_one_by_import_ref(import_ref)

    def test_import_ref_exists_returns_false_when_non_existing(
        self,
        organisation_repository: OrganisationRepository,
        faker: Faker,
    ) -> None:
        create_organisation(repository=organisation_repository, faker=faker)

        assert not organisation_repository.has_one_by_import_ref("nonexisting")

    def test_get_import_refs(
        self,
        organisation_repository: OrganisationRepository,
        faker: Faker,
    ) -> None:
        organisation_import_ref = create_organisation(organisation_repository, faker)[2]
        organisation_2_import_ref = create_organisation(organisation_repository, faker)[2]

        result = organisation_repository.get_import_refs()

        assert organisation_import_ref in result
        assert organisation_2_import_ref in result
        assert result == sorted(result, reverse=True)

    def test_count_for_import_ref_returns_correct_count(
        self,
        organisation_repository: OrganisationRepository,
        faker: Faker,
    ) -> None:
        import_ref = create_organisation(repository=organisation_repository, faker=faker)[2]
        create_organisation(repository=organisation_repository, faker=faker, import_ref=import_ref)

        count = organisation_repository.count_by_import_ref(import_ref)

        assert count == 2

    def test_delete_by_import_refs_deletes_correctly(
        self,
        organisation_repository: OrganisationRepository,
        faker: Faker,
    ) -> None:
        import_ref_1 = create_organisation(repository=organisation_repository, faker=faker)[2]
        import_ref_2 = create_organisation(repository=organisation_repository, faker=faker)[2]

        organisation_repository.delete_by_import_refs([import_ref_1, import_ref_2])

        assert organisation_repository.count_by_import_ref(import_ref_1) == 0
        assert organisation_repository.count_by_import_ref(import_ref_2) == 0


@mark.usefixtures("organisation_repository", "data_service_repository", "endpoint_repository")
class TestDataServiceRepository:
    def test_create_stores_data_service(
        self,
        organisation_repository: OrganisationRepository,
        data_service_repository: DataServiceRepository,
        endpoint_repository: EndpointRepository,
        faker: Faker,
    ) -> None:
        organisation = create_organisation(organisation_repository, faker)[3]
        auth_endpoint = create_endpoint(endpoint_repository, faker)[2]
        token_endpoint = create_endpoint(endpoint_repository, faker)[2]
        (
            external_id,
            name,
            interface_versions,
            result,
        ) = create_data_service(data_service_repository, faker, organisation.id, auth_endpoint.id, token_endpoint.id)

        assert result.id > 0
        assert result.organisation_id == organisation.id
        assert result.name == name
        assert result.external_id == external_id
        assert result.auth_endpoint_id == auth_endpoint.id
        assert result.token_endpoint_id == token_endpoint.id
        assert result.name == name
        assert result.interface_versions == json.dumps(interface_versions)

    def test_find_one_by_organisation_and_external_id_returns_matching_data_service(
        self,
        organisation_repository: OrganisationRepository,
        data_service_repository: DataServiceRepository,
        endpoint_repository: EndpointRepository,
        faker: Faker,
    ) -> None:
        organisation = create_organisation(organisation_repository, faker)[3]
        endpoint = create_endpoint(endpoint_repository, faker)[2]
        (
            external_id,
            _,
            _,
            data_service,
        ) = create_data_service(data_service_repository, faker, organisation.id, endpoint.id, endpoint.id)

        result = data_service_repository.find_one_by_organisation_and_external_id(organisation.id, external_id)

        assert result is not None
        assert result.id == data_service.id

    def test_find_one_by_organisation_and_external_id_returns_none_when_organisation_id_does_not_match(
        self,
        organisation_repository: OrganisationRepository,
        data_service_repository: DataServiceRepository,
        endpoint_repository: EndpointRepository,
        faker: Faker,
    ) -> None:
        organisation = create_organisation(organisation_repository, faker)[3]
        endpoint = create_endpoint(endpoint_repository, faker)[2]
        external_id = create_data_service(data_service_repository, faker, organisation.id, endpoint.id, endpoint.id)[0]

        result = data_service_repository.find_one_by_organisation_and_external_id(organisation.id + 1, external_id)

        assert result is None

    def test_find_one_by_organisation_and_external_id_returns_none_when_external_id_does_not_match(
        self,
        organisation_repository: OrganisationRepository,
        data_service_repository: DataServiceRepository,
        endpoint_repository: EndpointRepository,
        faker: Faker,
    ) -> None:
        organisation = create_organisation(organisation_repository, faker)[3]
        endpoint = create_endpoint(endpoint_repository, faker)[2]
        create_data_service(data_service_repository, faker, organisation.id, endpoint.id, endpoint.id)

        result = data_service_repository.find_one_by_organisation_and_external_id(
            organisation.id, faker.numerify("%%%")
        )

        assert result is None

    def test_find_all_returns_all_data_services_for_organisation(
        self,
        organisation_repository: OrganisationRepository,
        data_service_repository: DataServiceRepository,
        endpoint_repository: EndpointRepository,
        faker: Faker,
    ) -> None:
        target_organisation = create_organisation(organisation_repository, faker)[3]
        other_organisation = create_organisation(organisation_repository, faker)[3]
        endpoint = create_endpoint(endpoint_repository, faker)[2]
        target_data_service_0 = create_data_service(
            data_service_repository,
            faker,
            target_organisation.id,
            endpoint.id,
            endpoint.id,
        )[3]
        target_data_service_1 = create_data_service(
            data_service_repository, faker, target_organisation.id, endpoint.id, endpoint.id
        )[3]
        create_data_service(data_service_repository, faker, other_organisation.id, endpoint.id, endpoint.id)[3]
        create_data_service(data_service_repository, faker, other_organisation.id, endpoint.id, endpoint.id)[3]

        result = data_service_repository.find_all_by_organisation(target_organisation.id)

        assert len(result) == 2
        assert result[0].id == target_data_service_0.id
        assert result[1].id == target_data_service_1.id


@mark.usefixtures("organisation_repository", "data_service_repository", "system_role_repository", "endpoint_repository")
class TestSystemRoleRepository:
    def test_create_stores_system_role(
        self,
        organisation_repository: OrganisationRepository,
        data_service_repository: DataServiceRepository,
        system_role_repository: SystemRoleRepository,
        endpoint_repository: EndpointRepository,
        faker: Faker,
    ) -> None:
        organisation = create_organisation(organisation_repository, faker)[3]
        auth_endpoint = create_endpoint(endpoint_repository, faker)[2]
        token_endpoint = create_endpoint(endpoint_repository, faker)[2]
        resource_endpoint = create_endpoint(endpoint_repository, faker)[2]
        data_service = create_data_service(
            data_service_repository, faker, organisation.id, auth_endpoint.id, token_endpoint.id
        )[3]
        code = faker.lexify("??-???-??")

        result = system_role_repository.create(
            data_service_id=data_service.id,
            code=code,
            resource_endpoint_id=resource_endpoint.id,
            persist=False,
        )

        assert result.id > 0
        assert result.data_service_id == data_service.id
        assert result.code == code
        assert result.resource_endpoint_id == resource_endpoint.id


@mark.usefixtures("organisation_repository", "identifying_feature_repository")
class TestIdentifyingFeatureRepository:
    def test_create_stores_identifying_feature(
        self,
        organisation_repository: OrganisationRepository,
        identifying_feature_repository: IdentifyingFeatureRepository,
        faker: Faker,
    ) -> None:
        organisation = create_organisation(organisation_repository, faker)[3]

        type, value, import_ref, result = create_identifying_feature(
            identifying_feature_repository, faker, organisation.id
        )

        assert result.id > 0
        assert result.organisation_id == organisation.id
        assert result.type == type
        assert result.value == value
        assert result.import_ref == import_ref

    def test_import_ref_exists_returns_true_when_exists(
        self,
        organisation_repository: OrganisationRepository,
        identifying_feature_repository: IdentifyingFeatureRepository,
        faker: Faker,
    ) -> None:
        organisation = create_organisation(organisation_repository, faker)[3]
        import_ref = create_identifying_feature(
            repository=identifying_feature_repository,
            faker=faker,
            organisation_id=organisation.id,
        )[2]

        assert identifying_feature_repository.has_one_by_import_ref(import_ref)

    def test_import_ref_exists_returns_false_when_non_existing(
        self,
        organisation_repository: OrganisationRepository,
        identifying_feature_repository: IdentifyingFeatureRepository,
        faker: Faker,
    ) -> None:
        organisation = create_organisation(organisation_repository, faker)[3]
        create_identifying_feature(
            repository=identifying_feature_repository,
            faker=faker,
            organisation_id=organisation.id,
        )

        assert not identifying_feature_repository.has_one_by_import_ref("nonexisting")


@mark.usefixtures("endpoint_repository")
class TestEndpointRepository:
    def test_create_stores_endpoint(
        self,
        endpoint_repository: EndpointRepository,
        faker: Faker,
    ) -> None:
        url, signature, result = create_endpoint(endpoint_repository, faker)

        assert result.id > 0
        assert result.url == url
        assert result.signature == signature

    def test_find_one_by_url_returns_matching_endpoint(
        self,
        endpoint_repository: EndpointRepository,
        faker: Faker,
    ) -> None:
        url, _, endpoint = create_endpoint(endpoint_repository, faker)

        result = endpoint_repository.find_one_by_url(url)

        assert result is not None
        assert result.id == endpoint.id

    def test_find_one_by_url_returns_none_if_no_matching_url(
        self,
        endpoint_repository: EndpointRepository,
        faker: Faker,
    ) -> None:
        create_endpoint(endpoint_repository, faker, "foo")

        result = endpoint_repository.find_one_by_url("bar")

        assert result is None

    def test_find_all_returns_all_endpoints(self, endpoint_repository: EndpointRepository, faker: Faker) -> None:
        create_endpoint(endpoint_repository, faker)
        create_endpoint(endpoint_repository, faker)
        create_endpoint(endpoint_repository, faker)

        results = endpoint_repository.find_all()

        assert len(results) == 3


class TestRepositoryDecorator:
    @fixture(autouse=True)
    def reset_repository_registry(self) -> Generator[None, None, None]:
        original_registry = dict(repository_registry)
        yield
        repository_registry.clear()
        repository_registry.update(original_registry)

    def test_repository_decorator_registers_correctly(self) -> None:
        class MockRepository(BaseRepository):
            pass

        @repository(Base)
        class TestRepo(MockRepository):
            pass

        assert repository_registry.get(Base) == TestRepo
