from argparse import Namespace
from dataclasses import dataclass
from pathlib import Path

import inject
import orjson
import pytest
from pytest_mock import MockerFixture

from app.config.models import Config, HealthcareAdapterType
from app.cron.commands.update_search_index_command import UpdateSearchIndexCommand
from app.db.repositories import (
    DataServiceRepository,
    DbEndpointRepository,
    IdentifyingFeatureRepository,
    OrganisationRepository,
    SystemRoleRepository,
)
from app.normalization.models import NormalizedOrganization
from app.search_indexation.constants import ENCRYPTED_ENDPOINTS_OUTPUT_FILENAME, SEARCH_INDEX_OUTPUT_FILENAME
from app.search_indexation.repositories import (
    EncryptedEndpointsFileRepository,
    EncryptedEndpointsRepository,
    SearchIndexFileRepository,
    SearchIndexRepository,
)
from app.zal_importer.enums import IdentifyingFeatureType, OrganisationType
from app.zorgab_scraper.config import IdentifierSource, ZorgABScraperConfig
from tests.utils import configure_bindings


@dataclass(slots=True)
class SearchIndexOutput:
    organizations: list[NormalizedOrganization]
    endpoints: dict[str, str]


SEARCH_INDEX_SCENARIOS = ["basic", "missing_address", "aliases", "geolocation"]
REAL_AND_MOCKED_ORGANIZATIONS_SCENARIO = "real_and_mocked_organizations"
MOCK_ORGANIZATION_IDS = {"agb:99999997", "agb:99999998"}
MOCK_ENDPOINT_IDS = {"9999999990000001", "9999999990000002", "9999999990000003"}


class TestUpdateSearchIndexCommandFunctional:
    @pytest.fixture
    def paths(self, tmp_path: Path) -> dict[str, Path]:
        resources_dir = Path(__file__).parents[3] / "_resources"

        return {
            "snapshots_dir": resources_dir / "snapshots",
            "identifier_sources_dir": resources_dir / "identifier_sources",
            "stubs_dir": resources_dir / "stubs",
            "mock_organizations_dir": resources_dir / "mock_organizations",
            "output_dir": tmp_path,
            "temp_dir": tmp_path / "search-index-tmp",
            "endpoints_output_file": tmp_path / ENCRYPTED_ENDPOINTS_OUTPUT_FILENAME,
            "output_file": tmp_path / SEARCH_INDEX_OUTPUT_FILENAME,
        }

    @pytest.fixture
    def mock_addressing_with_clashing_database_endpoint_id(
        self, config: Config, paths: dict[str, Path], configure_app: None
    ) -> None:
        mock_addressing_path = paths["temp_dir"] / "mock-addressing-clash.json"
        mock_addressing_path.parent.mkdir(parents=True, exist_ok=True)
        mock_addressing_path.write_bytes(
            orjson.dumps(
                {
                    "1": "https://clashing-mock.url/resource",
                    "9999999990000002": "https://dva-mock.url/token",
                    "9999999990000003": "https://dva-mock.url/resource",
                }
            )
        )

        config.search_indexation.mock_addressing_path = mock_addressing_path

    @pytest.fixture()
    def include_mock_organizations(self, config: Config) -> None:
        config.search_indexation.include_mock_organizations = True

    @pytest.fixture()
    def configure_app(self, config: Config, paths: dict[str, Path]) -> None:
        config.app.healthcare_adapter = HealthcareAdapterType.zorgab
        config.app.mock_base_url = "https://dva-mock.url"

        config.zorgab_scraper = ZorgABScraperConfig(
            zakl_path=paths["identifier_sources_dir"] / "zakl_dummy.xml",
            agb_csv_path=paths["identifier_sources_dir"] / "agb_dummy.csv",
        )

        config.search_indexation.mock_organizations_path = paths["mock_organizations_dir"] / "mock-organizations.json"
        config.search_indexation.mock_addressing_path = paths["mock_organizations_dir"] / "mock-addressing.json"

        def bindings_override(binder: inject.Binder) -> None:
            binder.bind_to_constructor(
                SearchIndexRepository,
                lambda: SearchIndexFileRepository(
                    output_path=paths["output_dir"] / SEARCH_INDEX_OUTPUT_FILENAME,
                    temp_path=paths["temp_dir"],
                ),
            )
            binder.bind_to_constructor(
                EncryptedEndpointsRepository,
                lambda: EncryptedEndpointsFileRepository(
                    output_path=paths["output_dir"] / ENCRYPTED_ENDPOINTS_OUTPUT_FILENAME,
                    temp_path=paths["temp_dir"],
                ),
            )

        configure_bindings(config=config, bindings_override=bindings_override)

    @pytest.fixture()
    def seed_db(
        self,
        organisation_repository: OrganisationRepository,
        identifying_feature_repository: IdentifyingFeatureRepository,
        endpoint_repository: DbEndpointRepository,
        data_service_repository: DataServiceRepository,
        system_role_repository: SystemRoleRepository,
    ) -> None:
        """Seed the database with one organisation per scenario, each with 3 endpoints.

        Seeding order is deterministic so that auto-increment IDs in the snapshot are stable:
          • basic        dataservice 48 (AGB 11111111) → auth=1,  token=2,  resource=3
          • aliases      dataservice 49 (URA 12345678) → auth=4,  token=5,  resource=6
          • missing_addr dataservice 51 (AGB 87654321) → auth=7,  token=8,  resource=9
          • geolocation  dataservice 63 (AGB 99999999) → auth=10, token=11, resource=12
        """
        import_reference = "test-import-2024"

        organizations = [
            ("basic-org", OrganisationType.ZA, IdentifyingFeatureType.AGB, "11111111", "48"),
            ("aliases-org", OrganisationType.ZA, IdentifyingFeatureType.URA, "12345678", "49"),
            (
                "missing-address-org",
                OrganisationType.ZA,
                IdentifyingFeatureType.AGB,
                "87654321",
                "51",
            ),
            ("geolocation-org", OrganisationType.ZA, IdentifyingFeatureType.AGB, "99999999", "63"),
        ]

        for (
            name,
            organization_type,
            identifying_feature_type,
            identifying_feature_value,
            data_service_external_id,
        ) in organizations:
            organization = organisation_repository.create(
                name=name, type=organization_type, import_ref=import_reference, persist=True
            )

            identifying_feature_repository.create(
                organisation_id=organization.id,
                type=identifying_feature_type,
                value=identifying_feature_value,
                import_ref=import_reference,
                persist=True,
            )

            auth_endpoint = endpoint_repository.create(url=f"https://{name}.example.com/auth", persist=True)
            token_endpoint = endpoint_repository.create(url=f"https://{name}.example.com/token", persist=True)
            resource_endpoint = endpoint_repository.create(url=f"https://{name}.example.com/resource", persist=True)

            dataservice = data_service_repository.create(
                organisation_id=organization.id,
                external_id=data_service_external_id,
                name=f"{name} data service",
                auth_endpoint_id=auth_endpoint.id,
                token_endpoint_id=token_endpoint.id,
                persist=True,
            )

            system_role_repository.create(
                data_service_id=dataservice.id,
                code=f"{name}-B-FHIR",
                resource_endpoint_id=resource_endpoint.id,
                persist=True,
            )

    def _execute_command_with_mocked_zorgab(
        self, paths: dict[str, Path], scenario_name: str, mocker: MockerFixture
    ) -> SearchIndexOutput:
        payload = orjson.loads((paths["stubs_dir"] / f"zorgab_search_bundle_{scenario_name}.json").read_bytes())

        response = mocker.MagicMock(status_code=200)
        response.json.return_value = payload

        session = mocker.MagicMock()
        session.get.return_value = response

        mocker.patch("app.healthcarefinder.zorgab.zorgab.requests.Session", return_value=session)

        command = UpdateSearchIndexCommand()

        exit_code = command.run(
            Namespace(
                scrape_limit=10,
                scrape_workers=2,
                scrape_sources=[IdentifierSource.zakl_xml, IdentifierSource.agb_csv],
            )
        )

        assert exit_code == 0

        organizations = sorted(
            orjson.loads(paths["output_file"].read_bytes()),
            key=lambda org: str(org.get("id", "")),
        )

        endpoints: dict[str, str] = orjson.loads(paths["endpoints_output_file"].read_bytes())
        return SearchIndexOutput(organizations=organizations, endpoints=endpoints)

    @pytest.mark.parametrize("scenario", SEARCH_INDEX_SCENARIOS)
    @pytest.mark.usefixtures("configure_app", "seed_db")
    def test_search_index_scenario_matches_snapshot(
        self,
        paths: dict[str, Path],
        scenario: str,
        mocker: MockerFixture,
        endpoint_repository: DbEndpointRepository,
    ) -> None:
        output = self._execute_command_with_mocked_zorgab(paths, scenario, mocker)

        snapshot = sorted(
            orjson.loads((paths["snapshots_dir"] / f"search-index-{scenario}.json").read_bytes()),
            key=lambda org: str(org.get("id", "")),
        )
        assert output.organizations == snapshot
        assert set(output.endpoints.keys()) == {str(e.id) for e in endpoint_repository.find_all()}

    @pytest.mark.usefixtures("include_mock_organizations", "configure_app", "seed_db")
    def test_mock_organizations_included_when_flag_enabled(
        self,
        paths: dict[str, Path],
        mocker: MockerFixture,
        endpoint_repository: DbEndpointRepository,
    ) -> None:
        output = self._execute_command_with_mocked_zorgab(paths, REAL_AND_MOCKED_ORGANIZATIONS_SCENARIO, mocker)

        snapshot = sorted(
            orjson.loads(
                (paths["snapshots_dir"] / f"search-index-{REAL_AND_MOCKED_ORGANIZATIONS_SCENARIO}.json").read_bytes()
            ),
            key=lambda org: str(org.get("id", "")),
        )

        organization_ids = {organization["id"] for organization in output.organizations}
        database_endpoint_ids = {str(endpoint.id) for endpoint in endpoint_repository.find_all()}

        assert output.organizations == snapshot
        assert "agb:11111111" in organization_ids
        assert organization_ids >= MOCK_ORGANIZATION_IDS

        #  compare the set of endpoint IDs in the output with the union of database endpoint IDs and mock endpoint IDs
        assert set(output.endpoints.keys()) == database_endpoint_ids | MOCK_ENDPOINT_IDS

        interoplab = next(o for o in output.organizations if o["id"] == "agb:99999997")
        assert interoplab["name"] == "Interoplab Hospital"
        assert interoplab["data_services"][0]["resource_endpoint"] == "9999999990000003"

        no_dataservice = next(o for o in output.organizations if o["id"] == "agb:99999998")
        assert no_dataservice.get("data_services") == []

        # Verify mock endpoint URLs are JWE-encrypted, not stored as plaintext
        for endpoint_id in MOCK_ENDPOINT_IDS:
            assert not output.endpoints[endpoint_id].startswith("https://")

    @pytest.mark.usefixtures(
        "include_mock_organizations", "mock_addressing_with_clashing_database_endpoint_id", "configure_app", "seed_db"
    )
    def test_when_clashing_ids_mock_organizations_take_precedence_over_database_organizations(
        self, paths: dict[str, Path], mocker: MockerFixture, endpoint_repository: DbEndpointRepository
    ) -> None:
        """Clashing id is 1"""

        output = self._execute_command_with_mocked_zorgab(paths, REAL_AND_MOCKED_ORGANIZATIONS_SCENARIO, mocker)
        actual_organization_ids = {organization["id"] for organization in output.organizations}

        database_endpoint_ids = {str(endpoint.id) for endpoint in endpoint_repository.find_all()}
        expected_endpoint_ids = database_endpoint_ids | {"9999999990000002", "9999999990000003"}

        assert actual_organization_ids >= MOCK_ORGANIZATION_IDS
        assert set(output.endpoints.keys()) == expected_endpoint_ids
        assert len(output.endpoints) == len(expected_endpoint_ids)
        assert "1" in output.endpoints

        for endpoint_id in expected_endpoint_ids:
            assert not output.endpoints[endpoint_id].startswith("https://")
