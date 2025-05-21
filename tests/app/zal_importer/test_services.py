from typing import TypeAlias

import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture, MockType

from app.db.db import Database
from app.db.db_session import DbSession
from app.zal_importer.services import ExpiredImportsCleaner

MocksTypeAlias: TypeAlias = tuple[ExpiredImportsCleaner, MockType]


class TestExpiredImportsCleaner:
    @pytest.fixture
    def mocks(self, mocker: MockerFixture) -> MocksTypeAlias:
        mock_db = mocker.Mock(spec=Database)
        mock_db_session = mocker.Mock(spec=DbSession)
        mock_db.get_db_session.return_value = mock_db_session
        mock_organisation_repository = mocker.Mock()
        mock_db_session.get_repository.return_value = mock_organisation_repository

        return (
            ExpiredImportsCleaner(db=mock_db),
            mock_organisation_repository,
        )

    @pytest.mark.parametrize(
        "expiry_threshold, expected_deleted_refs",
        [
            (2, ["import_ref_3", "import_ref_4"]),
            (1, ["import_ref_2", "import_ref_3", "import_ref_4"]),
            (4, []),
        ],
    )
    def test_clean_expired_imports(
        self, test_client: TestClient, mocks: MocksTypeAlias, expiry_threshold: int, expected_deleted_refs: list[str]
    ) -> None:
        expired_imports_cleaner, mock_organisation_repository = mocks

        mock_organisation_repository.get_import_refs.return_value = [
            "import_ref_1",
            "import_ref_2",
            "import_ref_3",
            "import_ref_4",
        ]

        expired_imports_cleaner.clean_expired_imports(expiry_threshold=expiry_threshold)

        mock_organisation_repository.delete_by_import_refs.assert_called_once_with(expected_deleted_refs)

    def test_clean_expired_imports_counts_organisations_correctly(
        self, test_client: TestClient, mocks: MocksTypeAlias
    ) -> None:
        expired_imports_cleaner, mock_organisation_repository = mocks

        mock_organisation_repository.get_import_refs.return_value = [
            "import_ref_1",
            "import_ref_2",
            "import_ref_3",
            "import_ref_4",
        ]

        expired_imports_cleaner.clean_expired_imports(expiry_threshold=2)

        mock_organisation_repository.count_by_import_ref.assert_any_call("import_ref_3")
        mock_organisation_repository.count_by_import_ref.assert_any_call("import_ref_4")
