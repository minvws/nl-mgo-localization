from copy import deepcopy
from pathlib import Path
from typing import Type, TypeAlias
from xml.etree.ElementTree import Element, fromstring

from pytest import FixtureRequest, fixture, mark, raises
from pytest_mock import MockerFixture, MockType

from app.db.models import (
    Base,
    DataService,
    Endpoint,
    IdentifyingFeature,
    Organisation,
    SystemRole,
)
from app.xml.exceptions import CouldNotTraverse
from app.xml.services import ElementTraverser
from app.zal_importer.enums import IdentifyingFeatureType, OrganisationType
from app.zal_importer.exceptions import CouldNotImportOrganisations
from app.zal_importer.importers import (
    OrganisationJoinListImporter,
    OrganisationListImporter,
)

OrganisationListImporterMocksType: TypeAlias = tuple[
    OrganisationListImporter, MockType, MockType, MockType, MockType, MockType | None
]


class TestOrganisationListImporter:
    @fixture
    def mocks(
        self,
        request: FixtureRequest,
        mocker: MockerFixture,
    ) -> OrganisationListImporterMocksType:
        """
        :return: A tuple containing:
            - importer
            - mock_organisation_repository
            - mock_data_service_repository
            - mock_system_role_repository
            - mock_endpoint_repository
            - mock_signing_service
        """
        mock_db = mocker.Mock()
        mock_db_session = mocker.Mock()
        mock_signing_service = mocker.Mock() if hasattr(request, "param") and request.param else None
        mock_organisation_repository = mocker.Mock()
        mock_data_service_repository = mocker.Mock()
        mock_system_role_repository = mocker.Mock()
        mock_endpoint_repository = mocker.Mock()

        def get_repository_mock_by_class(arg: Type[Base]) -> MockType:
            arg_to_mock: dict[Type[Base], MockType] = {
                Organisation: mock_organisation_repository,
                DataService: mock_data_service_repository,
                SystemRole: mock_system_role_repository,
                Endpoint: mock_endpoint_repository,
            }

            if arg not in arg_to_mock:
                raise ValueError(f"Unknown class: {arg}")

            return arg_to_mock[arg]

        mock_db.get_db_session.return_value = mock_db_session
        mock_db_session.get_repository.side_effect = get_repository_mock_by_class
        mock_organisation_repository.has_one_by_import_ref.return_value = False

        importer: OrganisationListImporter = OrganisationListImporter(db=mock_db, signing_service=mock_signing_service)

        return (
            importer,
            mock_organisation_repository,
            mock_data_service_repository,
            mock_system_role_repository,
            mock_endpoint_repository,
            mock_signing_service,
        )

    @fixture
    def xml_traverser(self) -> ElementTraverser:
        with open(Path(__file__).parent / "MedMij_Zorgaanbiederslijst_example.9.3.xml", "r") as example_xml_file:
            example_xml = example_xml_file.read()

        return ElementTraverser(fromstring(example_xml))

    def test_process_xml_successfully_processes_xml(
        self,
        mocker: MockerFixture,
        mocks: OrganisationListImporterMocksType,
        xml_traverser: ElementTraverser,
    ) -> None:
        (
            importer,
            mock_organisation_repository,
            mock_data_service_repository,
            mock_system_role_repository,
            mock_endpoint_repository,
            _,
        ) = mocks

        mock_organisation_repository.create.side_effect = [
            Organisation(id=123),
            Organisation(id=456),
        ]
        mock_data_service_repository.create.side_effect = [
            DataService(id=123),
            DataService(id=456),
            DataService(id=789),
        ]
        mock_endpoint_repository.find_one_by_url.return_value = None
        mock_endpoint_repository.create.side_effect = [
            Endpoint(id=10),
            Endpoint(id=11),
            Endpoint(id=12),
            Endpoint(id=13),
            Endpoint(id=14),
            Endpoint(id=15),
            Endpoint(id=16),
            Endpoint(id=17),
            Endpoint(id=18),
            Endpoint(id=19),
        ]

        importer.process_xml(xml_traverser)

        mock_organisation_repository.create.assert_has_calls(
            [
                mocker.call(
                    import_ref="1620148431000009",
                    name="umcharderwijk@medmij",
                    type=OrganisationType.ZA,
                ),
                mocker.call(
                    import_ref="1620148431000009",
                    name="radiologencentraalflevoland@medmij",
                    type=OrganisationType.ZA,
                ),
            ]
        )

        mock_data_service_repository.create.assert_has_calls(
            [
                mocker.call(
                    organisation_id=123,
                    external_id="4",
                    auth_endpoint_id=10,
                    token_endpoint_id=11,
                ),
                mocker.call(
                    organisation_id=123,
                    external_id="6",
                    auth_endpoint_id=13,
                    token_endpoint_id=14,
                ),
                mocker.call(
                    organisation_id=456,
                    external_id="1",
                    auth_endpoint_id=17,
                    token_endpoint_id=18,
                ),
            ]
        )

        mock_system_role_repository.create.assert_has_calls(
            [
                mocker.call(
                    data_service_id=123,
                    code="LAB-1.1-LRB-FHIR",
                    resource_endpoint_id=12,
                ),
                mocker.call(
                    data_service_id=456,
                    code="MM-1.2-PLB-FHIR",
                    resource_endpoint_id=15,
                ),
                mocker.call(
                    data_service_id=456,
                    code="MM-1.2-PDB-FHIR",
                    resource_endpoint_id=16,
                ),
                mocker.call(
                    data_service_id=789,
                    code="MM-2.1-BZB-FHIR",
                    resource_endpoint_id=19,
                ),
            ]
        )

        mock_endpoint_repository.create.assert_has_calls(
            [
                mocker.call(url="https://medmij.za982.xisbridge.net/oauth/authorize", signature=None),
                mocker.call(url="https://medmij.xisbridge.net/oauth/token", signature=None),
                mocker.call(url="https://medmij.za982.xisbridge.net/fhir", signature=None),
                mocker.call(url="https://78834.umcharderwijk.nl/oauth/authorize", signature=None),
                mocker.call(url="https://78834.umcharderwijk.nl/oauth/token", signature=None),
                mocker.call(url="https://78834.umcharderwijk.nl/pdfa", signature=None),
                mocker.call(url="https://78834.umcharderwijk.nl/pdfa", signature=None),
                mocker.call(url="https://medmij.za983.xisbridge.net/oauth/authorize", signature=None),
                mocker.call(url="https://medmij.xisbridge.net/oauth/token", signature=None),
                mocker.call(url="https://rcf-rso.nl/rcf/fhir-stu3", signature=None),
            ]
        )

    @mark.parametrize("mocks", [True], indirect=True)
    def test_process_xml_signs_endpoints_if_signing_service_is_provided(
        self,
        mocker: MockerFixture,
        mocks: OrganisationListImporterMocksType,
        xml_traverser: ElementTraverser,
    ) -> None:
        (importer, _, _, _, mock_endpoint_repository, mock_signing_service) = mocks

        if mock_signing_service is None:
            raise ValueError("Mock `SigningService` is required")

        mock_signing_service.generate_signature.side_effect = [
            "signature1",
            "signature2",
            "signature3",
            "signature4",
            "signature5",
            "signature6",
            "signature7",
            "signature8",
            "signature9",
            "signature10",
        ]
        mock_endpoint_repository.find_one_by_url.side_effect = [
            auth_endpoint_1 := mocker.Mock(),
            token_endpoint_1 := mocker.Mock(),
            resource_endpoint_1 := mocker.Mock(),
            auth_endpoint_2 := mocker.Mock(),
            token_endpoint_2 := mocker.Mock(),
            resource_endpoint_2 := mocker.Mock(),
            resource_endpoint_3 := mocker.Mock(),
            auth_endpoint_3 := mocker.Mock(),
            token_endpoint_3 := mocker.Mock(),
            resource_endpoint_4 := mocker.Mock(),
        ]

        importer.process_xml(xml_traverser)

        mock_signing_service.generate_signature.assert_has_calls(
            [
                mocker.call("https://medmij.za982.xisbridge.net/oauth/authorize"),
                mocker.call("https://medmij.xisbridge.net/oauth/token"),
                mocker.call("https://medmij.za982.xisbridge.net/fhir"),
                mocker.call("https://78834.umcharderwijk.nl/oauth/authorize"),
                mocker.call("https://78834.umcharderwijk.nl/oauth/token"),
                mocker.call("https://78834.umcharderwijk.nl/pdfa"),
                mocker.call("https://78834.umcharderwijk.nl/pdfa"),
                mocker.call("https://medmij.za983.xisbridge.net/oauth/authorize"),
                mocker.call("https://medmij.xisbridge.net/oauth/token"),
                mocker.call("https://rcf-rso.nl/rcf/fhir-stu3"),
            ]
        )

        assert auth_endpoint_1.signature == "signature1"
        assert token_endpoint_1.signature == "signature2"
        assert resource_endpoint_1.signature == "signature3"
        assert auth_endpoint_2.signature == "signature4"
        assert token_endpoint_2.signature == "signature5"
        assert resource_endpoint_2.signature == "signature6"
        assert resource_endpoint_3.signature == "signature7"
        assert auth_endpoint_3.signature == "signature8"
        assert token_endpoint_3.signature == "signature9"
        assert resource_endpoint_4.signature == "signature10"

    def test_process_xml_fails_when_import_reference_already_exists(
        self,
        mocks: OrganisationListImporterMocksType,
        xml_traverser: ElementTraverser,
    ) -> None:
        (
            importer,
            mock_organisation_repository,
            _,
            _,
            _,
            _,
        ) = mocks

        mock_organisation_repository.has_one_by_import_ref.return_value = True

        with raises(CouldNotImportOrganisations, match=r"Import reference '.+' already exists"):
            importer.process_xml(xml_traverser)

    def test_process_xml_fails_when_timestamp_is_invalid(
        self,
        mocker: MockerFixture,
        mocks: OrganisationListImporterMocksType,
        xml_traverser: ElementTraverser,
    ) -> None:
        (importer, _, _, _, _, _) = mocks

        def mock_invalid_timestamp(name: str, root: Element | None = None) -> str:
            return "foobar" if name == "Tijdstempel" else xml_traverser.get_nested_text(name, root)

        mock_xml_traverser = mocker.Mock()
        mock_xml_traverser.get_nested_text.side_effect = mock_invalid_timestamp

        with raises(ValueError, match="Invalid isoformat string: 'foobar'"):
            importer.process_xml(mock_xml_traverser)

    def test_process_xml_fails_when_organisation_type_is_invalid(
        self,
        mocker: MockerFixture,
        mocks: OrganisationListImporterMocksType,
        xml_traverser: ElementTraverser,
    ) -> None:
        (importer, _, _, _, _, _) = mocks
        og_xml_traverser = deepcopy(xml_traverser)

        def mock_invalid_organisation_type(name: str, root: Element | None = None) -> str:
            return "foobar" if name == "Aanbiedertype" else og_xml_traverser.get_nested_text(name, root)

        mocker.patch.object(xml_traverser, "get_nested_text", side_effect=mock_invalid_organisation_type)

        with raises(ValueError, match="'foobar' is not a valid OrganisationType"):
            importer.process_xml(xml_traverser)


class TestOrganisationJoinListImporter:
    @fixture
    def mocks(self, mocker: MockerFixture) -> tuple[OrganisationJoinListImporter, MockType, MockType, MockType]:
        """
        :return: A tuple containing:
            - importer
            - mock_organisation_repository
            - mock_data_service_repository
            - mock_identifying_feature_repository
        """
        mock_db = mocker.Mock()
        mock_db_session = mocker.Mock()
        mock_organisation_repository = mocker.Mock()
        mock_data_service_repository = mocker.Mock()
        mock_identifying_feature_repository = mocker.Mock()

        def get_repository_mock_by_class(arg: Type[Base]) -> MockType:
            arg_to_mock: dict[Type[Base], MockType] = {
                Organisation: mock_organisation_repository,
                DataService: mock_data_service_repository,
                IdentifyingFeature: mock_identifying_feature_repository,
            }

            if arg not in arg_to_mock:
                raise ValueError(f"Unknown class: {arg}")

            return arg_to_mock[arg]

        mock_db.get_db_session.return_value = mock_db_session
        mock_db_session.get_repository.side_effect = get_repository_mock_by_class
        mock_identifying_feature_repository.has_one_by_import_ref.return_value = False

        importer: OrganisationJoinListImporter = OrganisationJoinListImporter(db=mock_db)

        return (
            importer,
            mock_organisation_repository,
            mock_data_service_repository,
            mock_identifying_feature_repository,
        )

    @fixture
    def xml_traverser(self) -> ElementTraverser:
        with open(
            Path(__file__).parent / "MedMij_Zorgaanbiederskoppellijst_example.5.1.xml",
            "r",
        ) as example_xml_file:
            example_xml = example_xml_file.read()

        return ElementTraverser(fromstring(example_xml))

    def test_process_xml_successfully_processes_xml(
        self,
        mocker: MockerFixture,
        mocks: tuple[OrganisationJoinListImporter, MockType, MockType, MockType],
        xml_traverser: ElementTraverser,
    ) -> None:
        (
            importer,
            mock_organisation_repository,
            mock_data_service_repository,
            mock_identifying_feature_repository,
        ) = mocks

        mock_organisation_repository.find_one_by_name.side_effect = [
            Organisation(id=123),
            Organisation(id=456),
        ]
        mock_data_service_repository.find_one_by_organisation_and_external_id.side_effect = [
            data_service_123 := mocker.Mock(),
            data_service_456 := mocker.Mock(),
            data_service_789 := mocker.Mock(),
        ]

        importer.process_xml(xml_traverser)

        mock_identifying_feature_repository.create.assert_has_calls(
            [
                mocker.call(
                    organisation_id=123,
                    import_ref="1620148431000013",
                    type=IdentifyingFeatureType.AGB,
                    value="90012345",
                ),
                mocker.call(
                    organisation_id=456,
                    import_ref="1620148431000013",
                    type=IdentifyingFeatureType.OIN,
                    value="23885731954438865098",
                ),
                mocker.call(
                    organisation_id=456,
                    import_ref="1620148431000013",
                    type=IdentifyingFeatureType.URA,
                    value="12345678",
                ),
            ]
        )

        assert data_service_123.name == "Meetwaarden vitale functies"
        assert data_service_123.interface_versions == '["1.4.0"]'
        assert data_service_456.name == "Verzamelen Documenten 1.0"
        assert data_service_456.interface_versions == '["1.4.0"]'
        assert data_service_789.name == "Basisgegevens zorg"
        assert data_service_789.interface_versions == '["1.3.0", "1.4.0"]'

    def test_process_xml_fails_when_import_reference_already_exists(
        self,
        mocks: tuple[OrganisationJoinListImporter, MockType, MockType, MockType],
        xml_traverser: ElementTraverser,
    ) -> None:
        (
            importer,
            _,
            _,
            mock_identifying_feature_repository,
        ) = mocks

        mock_identifying_feature_repository.has_one_by_import_ref.return_value = True

        with raises(CouldNotImportOrganisations, match=r"Import reference '.+' already exists"):
            importer.process_xml(xml_traverser)

    def test_process_xml_fails_when_timestamp_is_invalid(
        self,
        mocker: MockerFixture,
        mocks: tuple[OrganisationJoinListImporter, MockType, MockType, MockType],
        xml_traverser: ElementTraverser,
    ) -> None:
        (importer, _, _, _) = mocks

        def mock_invalid_timestamp(name: str, root: Element | None = None) -> str:
            return "foobar" if name == "Tijdstempel" else xml_traverser.get_nested_text(name, root)

        mock_xml_traverser = mocker.Mock()
        mock_xml_traverser.get_nested_text.side_effect = mock_invalid_timestamp

        with raises(ValueError, match="Invalid isoformat string: 'foobar'"):
            importer.process_xml(mock_xml_traverser)

    def test_process_xml_fails_when_identifying_feature_type_is_empty(
        self,
        mocker: MockerFixture,
        mocks: tuple[OrganisationJoinListImporter, MockType, MockType, MockType],
        xml_traverser: ElementTraverser,
    ) -> None:
        (importer, _, _, _) = mocks
        og_xml_traverser = deepcopy(xml_traverser)

        def mock_invalid_identifying_feature_type(
            root: Element | None = None,
        ) -> Element:
            return (
                Element("AGB")
                if root is not None and root.tag.endswith("IdentificerendKenmerk")
                else og_xml_traverser.get_child_element(root)
            )

        mocker.patch.object(
            xml_traverser,
            "get_child_element",
            side_effect=mock_invalid_identifying_feature_type,
        )

        with raises(CouldNotTraverse, match="Element 'AGB' contains no text"):
            importer.process_xml(xml_traverser)

    def test_process_xml_fails_when_identifying_feature_type_is_invalid(
        self,
        mocker: MockerFixture,
        mocks: tuple[OrganisationJoinListImporter, MockType, MockType, MockType],
        xml_traverser: ElementTraverser,
    ) -> None:
        (importer, _, _, _) = mocks
        og_xml_traverser = deepcopy(xml_traverser)

        def mock_invalid_identifying_feature_type(
            root: Element | None = None,
        ) -> Element:
            element = Element("FooBar")
            element.text = "90012345"

            return (
                element
                if root is not None and root.tag.endswith("IdentificerendKenmerk")
                else og_xml_traverser.get_child_element(root)
            )

        mocker.patch.object(
            xml_traverser,
            "get_child_element",
            side_effect=mock_invalid_identifying_feature_type,
        )

        with raises(ValueError, match="'FooBar' is not a valid IdentifyingFeatureType"):
            importer.process_xml(xml_traverser)

    def test_process_xml_skips_when_organisation_is_not_found(
        self,
        mocks: tuple[OrganisationJoinListImporter, MockType, MockType, MockType],
        xml_traverser: ElementTraverser,
    ) -> None:
        (
            importer,
            mock_organisation_repository,
            mock_data_service_repository,
            mock_identifying_feature_repository,
        ) = mocks

        mock_organisation_repository.find_one_by_name.return_value = None

        importer.process_xml(xml_traverser)

        assert mock_organisation_repository.find_one_by_name.call_count == 2
        mock_identifying_feature_repository.create.assert_not_called()
        mock_data_service_repository.find_one_by_organisation_and_external_id.assert_not_called()

    def test_process_xml_skips_when_data_service_is_not_found(
        self,
        mocker: MockerFixture,
        mocks: tuple[OrganisationJoinListImporter, MockType, MockType, MockType],
        xml_traverser: ElementTraverser,
    ) -> None:
        (importer, _, mock_data_service_repository, _) = mocks
        spy = mocker.spy(importer, "_OrganisationJoinListImporter__extract_interface_versions")

        mock_data_service_repository.find_one_by_organisation_and_external_id.return_value = None

        importer.process_xml(xml_traverser)

        spy.assert_not_called()
