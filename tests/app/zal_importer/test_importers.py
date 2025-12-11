from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from xml.etree.ElementTree import Element, fromstring

from pytest import FixtureRequest, fixture, mark, raises
from pytest_mock import MockerFixture, MockType

from app.db.models import (
    DataService,
    Endpoint,
    Organisation,
)
from app.xml.exceptions import CouldNotTraverse
from app.xml.services import ElementTraverser
from app.zal_importer.enums import IdentifyingFeatureType, OrganisationType
from app.zal_importer.exceptions import CouldNotImportOrganisations
from app.zal_importer.importers import (
    OrganisationJoinListImporter,
    OrganisationListImporter,
)

IMPORT_REF = "1620148431000009"
JOIN_IMPORT_REF = "1620148431000013"
ORGANISATION_NAMES = ["umcharderwijk@medmij", "radiologencentraalflevoland@medmij"]
TEST_URLS = [
    "https://medmij.za982.xisbridge.net/oauth/authorize",
    "https://medmij.xisbridge.net/oauth/token",
    "https://medmij.za982.xisbridge.net/fhir",
    "https://78834.umcharderwijk.nl/oauth/authorize",
    "https://78834.umcharderwijk.nl/oauth/token",
    "https://78834.umcharderwijk.nl/pdfa",
    "https://78834.umcharderwijk.nl/pdfa",
    "https://medmij.za983.xisbridge.net/oauth/authorize",
    "https://medmij.xisbridge.net/oauth/token",
    "https://rcf-rso.nl/rcf/fhir-stu3",
]


@dataclass
class OrganisationListMocks:
    importer: OrganisationListImporter
    organisation_repository: MockType
    data_service_repository: MockType
    system_role_repository: MockType
    endpoint_repository: MockType
    signing_service: MockType | None = None


@dataclass
class OrganisationJoinListMocks:
    importer: OrganisationJoinListImporter
    organisation_repository: MockType
    data_service_repository: MockType
    identifying_feature_repository: MockType


def _create_mock_repositories(mocker: MockerFixture) -> tuple[MockType, MockType, MockType, MockType]:
    mock_organisation_repo = mocker.Mock()
    mock_data_service_repo = mocker.Mock()
    mock_system_role_repo = mocker.Mock()
    mock_endpoint_repo = mocker.Mock()

    mock_organisation_repo.has_one_by_import_ref.return_value = False

    return mock_organisation_repo, mock_data_service_repo, mock_system_role_repo, mock_endpoint_repo


def _load_xml_file(filename: str) -> ElementTraverser:
    with open(Path(__file__).parent / filename, "r") as xml_file:
        return ElementTraverser(fromstring(xml_file.read()))


def _create_test_organisations() -> list[Organisation]:
    return [Organisation(id=123), Organisation(id=456)]


def _create_test_data_services() -> list[DataService]:
    return [DataService(id=123), DataService(id=456), DataService(id=789)]


def _create_test_endpoints() -> list[Endpoint]:
    return [Endpoint(id=i) for i in range(10, 20)]


class TestOrganisationListImporter:
    @fixture
    def mocks(
        self,
        request: FixtureRequest,
        mocker: MockerFixture,
    ) -> OrganisationListMocks:
        mock_logger = mocker.Mock()
        mock_signing_service = mocker.Mock() if hasattr(request, "param") and request.param else None

        org_repo, data_repo, sys_repo, endpoint_repo = _create_mock_repositories(mocker)

        importer = OrganisationListImporter(
            organisation_repository=org_repo,
            data_service_repository=data_repo,
            system_role_repository=sys_repo,
            endpoint_repository=endpoint_repo,
            logger=mock_logger,
            signing_service=mock_signing_service,
        )

        return OrganisationListMocks(
            importer=importer,
            organisation_repository=org_repo,
            data_service_repository=data_repo,
            system_role_repository=sys_repo,
            endpoint_repository=endpoint_repo,
            signing_service=mock_signing_service,
        )

    @fixture
    def xml_traverser(self) -> ElementTraverser:
        return _load_xml_file("MedMij_Zorgaanbiederslijst_example.9.3.xml")

    def _setup_successful_processing_mocks(self, mocks: OrganisationListMocks) -> None:
        mocks.organisation_repository.create.side_effect = _create_test_organisations()
        mocks.data_service_repository.create.side_effect = _create_test_data_services()
        mocks.endpoint_repository.find_one_by_url.return_value = None
        mocks.endpoint_repository.create.side_effect = _create_test_endpoints()

    def _assert_organisation_creation(self, mocks: OrganisationListMocks, mocker: MockerFixture) -> None:
        mocks.organisation_repository.create.assert_has_calls(
            [
                mocker.call(
                    import_ref=IMPORT_REF,
                    name=ORGANISATION_NAMES[0],
                    type=OrganisationType.ZA,
                ),
                mocker.call(
                    import_ref=IMPORT_REF,
                    name=ORGANISATION_NAMES[1],
                    type=OrganisationType.ZA,
                ),
            ]
        )

    def _assert_data_service_creation(self, mocks: OrganisationListMocks, mocker: MockerFixture) -> None:
        expected_calls = [
            mocker.call(organisation_id=123, external_id="4", auth_endpoint_id=10, token_endpoint_id=11),
            mocker.call(organisation_id=123, external_id="6", auth_endpoint_id=13, token_endpoint_id=14),
            mocker.call(organisation_id=456, external_id="1", auth_endpoint_id=17, token_endpoint_id=18),
        ]
        mocks.data_service_repository.create.assert_has_calls(expected_calls)

    def _assert_system_role_creation(self, mocks: OrganisationListMocks, mocker: MockerFixture) -> None:
        expected_calls = [
            mocker.call(data_service_id=123, code="LAB-1.1-LRB-FHIR", resource_endpoint_id=12),
            mocker.call(data_service_id=456, code="MM-1.2-PLB-FHIR", resource_endpoint_id=15),
            mocker.call(data_service_id=456, code="MM-1.2-PDB-FHIR", resource_endpoint_id=16),
            mocker.call(data_service_id=789, code="MM-2.1-BZB-FHIR", resource_endpoint_id=19),
        ]
        mocks.system_role_repository.create.assert_has_calls(expected_calls)

    def _assert_endpoint_creation(self, mocks: OrganisationListMocks, mocker: MockerFixture) -> None:
        expected_calls = [mocker.call(url=url, signature=None) for url in TEST_URLS]
        mocks.endpoint_repository.create.assert_has_calls(expected_calls)

    def test_process_xml_successfully_processes_xml(
        self,
        mocker: MockerFixture,
        mocks: OrganisationListMocks,
        xml_traverser: ElementTraverser,
    ) -> None:
        self._setup_successful_processing_mocks(mocks)

        mocks.importer.process_xml(xml_traverser)

        self._assert_organisation_creation(mocks, mocker)
        self._assert_data_service_creation(mocks, mocker)
        self._assert_system_role_creation(mocks, mocker)
        self._assert_endpoint_creation(mocks, mocker)

    @mark.parametrize("mocks", [True], indirect=True)
    def test_process_xml_signs_endpoints_if_signing_service_is_provided(
        self,
        mocker: MockerFixture,
        mocks: OrganisationListMocks,
        xml_traverser: ElementTraverser,
    ) -> None:
        if mocks.signing_service is None:
            raise ValueError("Mock `SigningService` is required")

        signatures = [f"signature{i}" for i in range(1, 11)]
        mock_endpoints = [mocker.Mock() for _ in range(10)]

        mocks.signing_service.generate_signature.side_effect = signatures
        mocks.endpoint_repository.find_one_by_url.side_effect = mock_endpoints

        mocks.importer.process_xml(xml_traverser)

        expected_signature_calls = [mocker.call(url) for url in TEST_URLS]
        mocks.signing_service.generate_signature.assert_has_calls(expected_signature_calls)

        for endpoint, signature in zip(mock_endpoints, signatures, strict=True):
            assert endpoint.signature == signature

    def test_process_xml_fails_when_import_reference_already_exists(
        self,
        mocks: OrganisationListMocks,
        xml_traverser: ElementTraverser,
    ) -> None:
        mocks.organisation_repository.has_one_by_import_ref.return_value = True

        with raises(CouldNotImportOrganisations, match=r"Import reference '.+' already exists"):
            mocks.importer.process_xml(xml_traverser)

    @mark.parametrize(
        "field_name,invalid_value,expected_error",
        [
            ("Tijdstempel", "foobar", "Invalid isoformat string: 'foobar'"),
            ("Aanbiedertype", "foobar", "'foobar' is not a valid OrganisationType"),
        ],
    )
    def test_process_xml_fails_with_invalid_field_values(
        self,
        mocker: MockerFixture,
        mocks: OrganisationListMocks,
        xml_traverser: ElementTraverser,
        field_name: str,
        invalid_value: str,
        expected_error: str,
    ) -> None:
        if field_name == "Tijdstempel":
            mock_xml_traverser = mocker.Mock()
            mock_xml_traverser.get_nested_text.side_effect = lambda name: (
                invalid_value if name == field_name else "valid_value"
            )
            test_traverser = mock_xml_traverser
        else:
            original_get_nested_text = xml_traverser.get_nested_text

            def mock_field_value(name: str, root: Element | None = None) -> str:
                return invalid_value if name == field_name else original_get_nested_text(name, root)

            mocker.patch.object(xml_traverser, "get_nested_text", side_effect=mock_field_value)
            test_traverser = xml_traverser

        with raises(ValueError, match=expected_error):
            mocks.importer.process_xml(test_traverser)


class TestOrganisationJoinListImporter:
    @fixture
    def mocks(self, mocker: MockerFixture) -> OrganisationJoinListMocks:
        mock_logger = mocker.Mock()
        org_repo, data_repo, _, _ = _create_mock_repositories(mocker)
        mock_identifying_feature_repo = mocker.Mock()
        mock_identifying_feature_repo.has_one_by_import_ref.return_value = False

        importer = OrganisationJoinListImporter(
            organisation_repository=org_repo,
            data_service_repository=data_repo,
            identifying_feature_repository=mock_identifying_feature_repo,
            logger=mock_logger,
        )

        return OrganisationJoinListMocks(
            importer=importer,
            organisation_repository=org_repo,
            data_service_repository=data_repo,
            identifying_feature_repository=mock_identifying_feature_repo,
        )

    @fixture
    def xml_traverser(self) -> ElementTraverser:
        return _load_xml_file("MedMij_Zorgaanbiederskoppellijst_example.5.1.xml")

    def _setup_successful_join_processing_mocks(
        self, mocks: OrganisationJoinListMocks, mocker: MockerFixture
    ) -> tuple[MockType, MockType, MockType]:
        mocks.organisation_repository.find_one_by_name.side_effect = _create_test_organisations()

        data_service_123 = mocker.Mock()
        data_service_456 = mocker.Mock()
        data_service_789 = mocker.Mock()

        mocks.data_service_repository.find_one_by_organisation_and_external_id.side_effect = [
            data_service_123,
            data_service_456,
            data_service_789,
        ]

        data_service_123.name = "Meetwaarden vitale functies"
        data_service_123.interface_versions = '["1.4.0"]'
        data_service_456.name = "Verzamelen Documenten 1.0"
        data_service_456.interface_versions = '["1.4.0"]'
        data_service_789.name = "Basisgegevens zorg"
        data_service_789.interface_versions = '["1.3.0", "1.4.0"]'

        return data_service_123, data_service_456, data_service_789

    def _assert_identifying_feature_creation(self, mocks: OrganisationJoinListMocks, mocker: MockerFixture) -> None:
        expected_calls = [
            mocker.call(
                organisation_id=123,
                import_ref=JOIN_IMPORT_REF,
                type=IdentifyingFeatureType.AGB,
                value="90012345",
            ),
            mocker.call(
                organisation_id=456,
                import_ref=JOIN_IMPORT_REF,
                type=IdentifyingFeatureType.OIN,
                value="23885731954438865098",
            ),
            mocker.call(
                organisation_id=456,
                import_ref=JOIN_IMPORT_REF,
                type=IdentifyingFeatureType.URA,
                value="12345678",
            ),
        ]
        mocks.identifying_feature_repository.create.assert_has_calls(expected_calls)

    def test_process_xml_successfully_processes_xml(
        self,
        mocker: MockerFixture,
        mocks: OrganisationJoinListMocks,
        xml_traverser: ElementTraverser,
    ) -> None:
        data_service_123, data_service_456, data_service_789 = self._setup_successful_join_processing_mocks(
            mocks, mocker
        )

        mocks.importer.process_xml(xml_traverser)

        self._assert_identifying_feature_creation(mocks, mocker)

        assert data_service_123.name == "Meetwaarden vitale functies"
        assert data_service_123.interface_versions == '["1.4.0"]'
        assert data_service_456.name == "Verzamelen Documenten 1.0"
        assert data_service_456.interface_versions == '["1.4.0"]'
        assert data_service_789.name == "Basisgegevens zorg"
        assert data_service_789.interface_versions == '["1.3.0", "1.4.0"]'

    def test_process_xml_fails_when_import_reference_already_exists(
        self,
        mocks: OrganisationJoinListMocks,
        xml_traverser: ElementTraverser,
    ) -> None:
        mocks.identifying_feature_repository.has_one_by_import_ref.return_value = True

        with raises(CouldNotImportOrganisations, match=r"Import reference '.+' already exists"):
            mocks.importer.process_xml(xml_traverser)

    def test_process_xml_fails_when_timestamp_is_invalid(
        self,
        mocker: MockerFixture,
        mocks: OrganisationJoinListMocks,
        xml_traverser: ElementTraverser,
    ) -> None:
        def mock_invalid_timestamp(name: str, root: Element | None = None) -> str:
            return "foobar" if name == "Tijdstempel" else "valid_value"

        mock_xml_traverser = mocker.Mock()
        mock_xml_traverser.get_nested_text.side_effect = mock_invalid_timestamp

        with raises(ValueError, match="Invalid isoformat string: 'foobar'"):
            mocks.importer.process_xml(mock_xml_traverser)

    @mark.parametrize(
        "empty_element,expected_error",
        [
            (True, "Element 'AGB' contains no text"),
            (False, "'FooBar' is not a valid IdentifyingFeatureType"),
        ],
    )
    def test_process_xml_fails_with_invalid_identifying_feature_type(
        self,
        mocker: MockerFixture,
        mocks: OrganisationJoinListMocks,
        xml_traverser: ElementTraverser,
        empty_element: bool,
        expected_error: str,
    ) -> None:
        og_xml_traverser = deepcopy(xml_traverser)

        def mock_invalid_identifying_feature_type(root: Element | None = None) -> Element:
            if root is not None and root.tag.endswith("IdentificerendKenmerk"):
                if empty_element:
                    return Element("AGB")
                else:
                    element = Element("FooBar")
                    element.text = "90012345"
                    return element
            return og_xml_traverser.get_child_element(root)

        mocker.patch.object(
            xml_traverser,
            "get_child_element",
            side_effect=mock_invalid_identifying_feature_type,
        )

        exception_type = CouldNotTraverse if empty_element else ValueError
        with raises(exception_type, match=expected_error):
            mocks.importer.process_xml(xml_traverser)

    @mark.parametrize(
        "missing_entity,expected_call_count",
        [
            ("organisation", 2),
            ("data_service", 0),
        ],
    )
    def test_process_xml_skips_when_entity_not_found(
        self,
        mocker: MockerFixture,
        mocks: OrganisationJoinListMocks,
        xml_traverser: ElementTraverser,
        missing_entity: str,
        expected_call_count: int,
    ) -> None:
        if missing_entity == "organisation":
            mocks.organisation_repository.find_one_by_name.return_value = None
        else:
            mocks.organisation_repository.find_one_by_name.side_effect = _create_test_organisations()
            mocks.data_service_repository.find_one_by_organisation_and_external_id.return_value = None

        if missing_entity == "data_service":
            spy = mocker.spy(mocks.importer, "_OrganisationJoinListImporter__extract_interface_versions")

        mocks.importer.process_xml(xml_traverser)

        if missing_entity == "organisation":
            assert mocks.organisation_repository.find_one_by_name.call_count == expected_call_count
            mocks.identifying_feature_repository.create.assert_not_called()
            mocks.data_service_repository.find_one_by_organisation_and_external_id.assert_not_called()
        else:
            spy.assert_not_called()
