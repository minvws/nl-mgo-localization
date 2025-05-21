from enum import Enum

from pytest import raises
from pytest_mock import MockerFixture

from app.zal_importer.enums import ImportType
from app.zal_importer.factories import OrganisationImporterFactory
from app.zal_importer.importers import (
    OrganisationJoinListImporter,
    OrganisationListImporter,
)


class TestImporterFactory:
    def test_create_importer_returns_organisation_list_importer(self, mocker: MockerFixture) -> None:
        importer = OrganisationImporterFactory.create_importer(ImportType.LIST)

        assert isinstance(importer, OrganisationListImporter)

    def test_create_importer_returns_organisation_join_list_importer(self, mocker: MockerFixture) -> None:
        importer = OrganisationImporterFactory.create_importer(ImportType.JOIN_LIST)

        assert isinstance(importer, OrganisationJoinListImporter)

    def test_create_importer_fails_when_importer_type_implementation_is_missing(self, mocker: MockerFixture) -> None:
        mock_import_type = mocker.patch(
            "app.zal_importer.enums.ImportType",
            return_value=Enum(
                "ImportType",
                {
                    "LIST": "LIST",
                    "JOIN_LIST": "JOIN_LIST",
                    "UNMAPPED_VALUE": "UNMAPPED_VALUE",
                },
            ),
        )

        with raises(ValueError, match=r"No importer found for import type '.+'"):
            OrganisationImporterFactory.create_importer(mock_import_type.UNMAPPED_VALUE)
