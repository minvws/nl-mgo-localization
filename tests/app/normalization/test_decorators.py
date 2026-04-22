from typing import Tuple, TypeAlias

import pytest
from faker import Faker
from pytest import fixture
from pytest_mock import MockerFixture, MockType

from app.db.models import DataService
from app.db.repositories import DataServiceRepository, OrganisationRepository
from app.normalization.decorators import (
    CreateSearchBlobFieldPostProcessor,
    DeduplicateAliasesPostProcessor,
    PopulateMedMijSpecificFields,
    RemoveEphemeralFields,
)
from app.normalization.models import NormalizedOrganization
from app.normalization.services import IdStringToIdentifyingFeatureConverter
from app.zal_importer.enums import IdentifyingFeatureType
from tests._factories import make_dataservice, make_endpoint, make_organisation, make_system_role

TestPopulateMedMijSpecificFieldsMockDependencies: TypeAlias = Tuple[MockType, MockType, MockType, MockType]


@fixture
def normalized_organization_id(faker: Faker) -> Tuple[IdentifyingFeatureType, str]:
    return faker.random_element(IdentifyingFeatureType), faker.numerify("######")


@fixture
def normalized_organization(
    faker: Faker, normalized_organization_id: Tuple[IdentifyingFeatureType, str]
) -> NormalizedOrganization:
    return {
        "id": f"{normalized_organization_id[0].value}:{normalized_organization_id[1]}",
        "care_type": faker.word(),
        "name": faker.word(),
        "city": faker.city(),
        "aliases": [faker.word() for _ in range(3)],
        "postal_code": faker.postcode(),
        "address": faker.street_address(),
    }


class TestPopulateMedMijSpecificFields:
    @fixture
    def mock_dependencies(self, mocker: MockerFixture) -> TestPopulateMedMijSpecificFieldsMockDependencies:
        mock_id_string_converter = mocker.Mock(spec=IdStringToIdentifyingFeatureConverter)
        mock_organization_repository = mocker.Mock(spec=OrganisationRepository)
        mock_data_service_repository = mocker.Mock(spec=DataServiceRepository)
        mock_logger = mocker.patch("app.normalization.decorators.logger")

        return mock_id_string_converter, mock_organization_repository, mock_data_service_repository, mock_logger

    def test_call_populates_data_services_with_external_id_and_endpoint_ids(
        self,
        normalized_organization_id: Tuple[IdentifyingFeatureType, str],
        normalized_organization: NormalizedOrganization,
        mock_dependencies: TestPopulateMedMijSpecificFieldsMockDependencies,
    ) -> None:
        mock_id_string_converter, mock_organization_repository, mock_data_service_repository, _ = mock_dependencies

        providing_role_code = "MM-3.0-PDB-FHIR"
        providing_role_resource_endpoint = make_endpoint(
            {"id": 33, "url": "https://medmij-pgo.vzvz.nl/2.0.0/fhir/stu3/51"}
        )
        providing_role = make_system_role(
            {
                "code": providing_role_code,
                "resource_endpoint": providing_role_resource_endpoint,
            },
        )

        organization = make_organisation()
        data_service = make_dataservice(
            {
                "roles": [providing_role],
                "auth_endpoint": make_endpoint({"id": 11}),
                "token_endpoint": make_endpoint({"id": 22}),
            }
        )

        mock_id_string_converter.return_value = normalized_organization_id
        mock_organization_repository.find_one_by_identifying_feature.return_value = organization
        mock_data_service_repository.find_all_by_organisation.return_value = [data_service]

        decorator = PopulateMedMijSpecificFields(
            id_string_converter=mock_id_string_converter,
            organization_repository=mock_organization_repository,
            data_service_repository=mock_data_service_repository,
        )

        decorator(normalized_organization)

        assert "data_services" in normalized_organization
        normalized_data_service = normalized_organization["data_services"][0]
        id_to_assert = organization.name.split("@")[0]  # pop off @medmij suffix
        assert normalized_organization["medmij_id"] == id_to_assert

        assert normalized_data_service["id"] == data_service.external_id
        assert normalized_data_service["auth_endpoint"] == str(data_service.auth_endpoint.id)
        assert normalized_data_service["token_endpoint"] == str(data_service.token_endpoint.id)
        assert normalized_data_service["resource_endpoint"] == str(providing_role_resource_endpoint.id)

        mock_id_string_converter.assert_called_once_with(normalized_organization["id"])
        mock_organization_repository.find_one_by_identifying_feature.assert_called_once_with(
            normalized_organization_id[0],
            normalized_organization_id[1],
        )

        mock_data_service_repository.find_all_by_organisation.assert_called_once_with(organization.id)

    @pytest.mark.parametrize(
        ("organization_name", "expected_medmij_id"),
        [
            ("umcharderwijk@medmij", "umcharderwijk"),
            ("radiologencentraalflevoland@MeDmIj", "radiologencentraalflevoland"),
            ("organisatie-@medmij-middle", "organisatie-@medmij-middle"),
            ("organisatie-zonder-suffix", "organisatie-zonder-suffix"),
        ],
    )
    def test_call_sets_expected_medmij_id(
        self,
        organization_name: str,
        expected_medmij_id: str,
        normalized_organization_id: Tuple[IdentifyingFeatureType, str],
        normalized_organization: NormalizedOrganization,
        mock_dependencies: TestPopulateMedMijSpecificFieldsMockDependencies,
    ) -> None:
        mock_id_string_converter, mock_organization_repository, mock_data_service_repository, _ = mock_dependencies

        organization = make_organisation({"name": organization_name})
        data_service = make_dataservice(
            {
                "roles": [
                    make_system_role(
                        {
                            "code": "MM-3.0-PDB-FHIR",
                            "resource_endpoint": make_endpoint({"id": 33}),
                        }
                    )
                ],
                "auth_endpoint": make_endpoint({"id": 11}),
                "token_endpoint": make_endpoint({"id": 22}),
            }
        )

        mock_id_string_converter.return_value = normalized_organization_id
        mock_organization_repository.find_one_by_identifying_feature.return_value = organization
        mock_data_service_repository.find_all_by_organisation.return_value = [data_service]

        decorator = PopulateMedMijSpecificFields(
            id_string_converter=mock_id_string_converter,
            organization_repository=mock_organization_repository,
            data_service_repository=mock_data_service_repository,
        )

        decorator(normalized_organization)

        assert normalized_organization["medmij_id"] == expected_medmij_id

    def test_call_when_no_providing_role_exists_is_idle(
        self,
        normalized_organization_id: Tuple[IdentifyingFeatureType, str],
        normalized_organization: NormalizedOrganization,
        mock_dependencies: TestPopulateMedMijSpecificFieldsMockDependencies,
    ) -> None:
        mock_id_string_converter, mock_organization_repository, mock_data_service_repository, _ = mock_dependencies

        organization = make_organisation()
        non_providing_role = make_system_role(
            {
                "code": "SOME-OTHER-ROLE",
                "resource_endpoint": make_endpoint(),
            },
        )

        data_service = make_dataservice({"roles": [non_providing_role]})

        mock_id_string_converter.return_value = normalized_organization_id
        mock_organization_repository.find_one_by_identifying_feature.return_value = organization
        mock_data_service_repository.find_all_by_organisation.return_value = [data_service]

        decorator = PopulateMedMijSpecificFields(
            id_string_converter=mock_id_string_converter,
            organization_repository=mock_organization_repository,
            data_service_repository=mock_data_service_repository,
        )

        decorator(normalized_organization)

        assert "data_services" not in normalized_organization
        assert "medmij_id" not in normalized_organization

        mock_id_string_converter.assert_called_once_with(normalized_organization["id"])

    def test_call_when_identifying_feature_not_found_is_idle(
        self,
        normalized_organization: NormalizedOrganization,
        mock_dependencies: TestPopulateMedMijSpecificFieldsMockDependencies,
    ) -> None:
        mock_id_string_converter, mock_organization_repository, mock_data_service_repository, _ = mock_dependencies

        mock_id_string_converter.return_value = None

        decorator = PopulateMedMijSpecificFields(
            id_string_converter=mock_id_string_converter,
            organization_repository=mock_organization_repository,
            data_service_repository=mock_data_service_repository,
        )

        decorator(normalized_organization)

        assert "data_services" not in normalized_organization
        assert "medmij_id" not in normalized_organization

        mock_id_string_converter.assert_called_once_with(normalized_organization["id"])
        mock_organization_repository.find_one_by_identifying_feature.assert_not_called()
        mock_data_service_repository.find_all_by_organisation.assert_not_called()

    def test_call_when_organization_not_found_is_idle(
        self,
        faker: Faker,
        normalized_organization_id: Tuple[IdentifyingFeatureType, str],
        normalized_organization: NormalizedOrganization,
        mock_dependencies: TestPopulateMedMijSpecificFieldsMockDependencies,
    ) -> None:
        mock_id_string_converter, mock_organization_repository, mock_data_service_repository, mock_logger = (
            mock_dependencies
        )

        mock_id_string_converter.return_value = normalized_organization_id
        mock_organization_repository.find_one_by_identifying_feature.return_value = None

        decorator = PopulateMedMijSpecificFields(
            id_string_converter=mock_id_string_converter,
            organization_repository=mock_organization_repository,
            data_service_repository=mock_data_service_repository,
        )

        decorator(normalized_organization)

        assert "data_services" not in normalized_organization
        assert "medmij_id" not in normalized_organization

        mock_id_string_converter.assert_called_once_with(normalized_organization["id"])
        mock_organization_repository.find_one_by_identifying_feature.assert_called_once_with(
            *normalized_organization_id
        )
        mock_data_service_repository.find_all_by_organisation.assert_not_called()

    def test_call_when_data_service_without_roles_is_idle(
        self,
        mocker: MockerFixture,
        faker: Faker,
        normalized_organization_id: Tuple[IdentifyingFeatureType, str],
        normalized_organization: NormalizedOrganization,
        mock_dependencies: TestPopulateMedMijSpecificFieldsMockDependencies,
    ) -> None:
        mock_id_string_converter, mock_organization_repository, mock_data_service_repository, _ = mock_dependencies

        organization = make_organisation()
        mock_data_service = mocker.Mock(spec=DataService)
        mock_data_service.auth_endpoint = faker.url()
        mock_data_service.token_endpoint = faker.url()
        mock_data_service.roles = []

        mock_id_string_converter.return_value = normalized_organization_id
        mock_organization_repository.find_one_by_identifying_feature.return_value = organization
        mock_data_service_repository.find_all_by_organisation.return_value = [mock_data_service]

        decorator = PopulateMedMijSpecificFields(
            id_string_converter=mock_id_string_converter,
            organization_repository=mock_organization_repository,
            data_service_repository=mock_data_service_repository,
        )

        decorator(normalized_organization)

        assert "data_services" not in normalized_organization
        assert "medmij_id" not in normalized_organization

        mock_id_string_converter.assert_called_once_with(normalized_organization["id"])
        mock_organization_repository.find_one_by_identifying_feature.assert_called_once_with(
            *normalized_organization_id
        )

        mock_data_service_repository.find_all_by_organisation.assert_called_once_with(organization.id)


class TestRemoveEphemeralFields:
    def test_call_when_aliases_field_exists_removes_aliases(
        self, normalized_organization: NormalizedOrganization
    ) -> None:
        normalized_organization["aliases"] = ["alias1", "alias2"]
        decorator = RemoveEphemeralFields()

        decorator(normalized_organization)

        assert "aliases" not in normalized_organization

    def test_call_when_aliases_field_not_exists_is_idle(self, normalized_organization: NormalizedOrganization) -> None:
        del normalized_organization["aliases"]
        decorator = RemoveEphemeralFields()

        decorator(normalized_organization)

        # implicitly asserting no NameError is raised
        assert "aliases" not in normalized_organization


class TestDeduplicateAliasesPostProcessor:
    def test_call_removes_duplicates_and_name(self) -> None:
        normalized_organization_fragment: NormalizedOrganization = {
            "name": "Clinic",
            "aliases": [
                "clinic",
                "Alt",
                "ALT",
                "Another",
            ],
        }
        decorator = DeduplicateAliasesPostProcessor()

        decorator(normalized_organization_fragment)

        assert normalized_organization_fragment["aliases"] == ["Alt", "Another"]


class TestCreateSearchBlobFieldPostProcessor:
    def test_call_handles_missing_enrichment_fields(self, normalized_organization: NormalizedOrganization) -> None:
        normalized_organization_fragment: NormalizedOrganization = {
            "care_type": "Type",
            "name": "Name",
            "city": "City",
            # aliases missing, postal empty, address missing
        }
        expected_blob_start = "%s %s %s" % (
            normalized_organization_fragment["care_type"],
            normalized_organization_fragment["name"],
            normalized_organization_fragment["city"],
        )
        decorator = CreateSearchBlobFieldPostProcessor()

        decorator(normalized_organization_fragment)

        assert normalized_organization_fragment["search_blob"].startswith(expected_blob_start)
