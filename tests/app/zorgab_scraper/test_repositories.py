import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from fhir.resources.STU3.bundle import Bundle, BundleEntry
from fhir.resources.STU3.organization import Organization as FhirOrganization
from freezegun import freeze_time
from pytest_mock import MockerFixture

from app.zorgab_scraper.config import ZorgABScraperConfig
from app.zorgab_scraper.repositories import ZorgABJsonFileRepository


@pytest.fixture
def domain_config(tmp_path: Path) -> ZorgABScraperConfig:
    return ZorgABScraperConfig(
        results_base_dir=tmp_path,
    )


class TestZorgabJsonResultWriter:
    @freeze_time("2024-01-02 03:04:05")
    def test_write_creates_timestamped_filename_and_collection_bundle(
        self, domain_config: ZorgABScraperConfig, mocker: MockerFixture, test_client: TestClient
    ) -> None:
        logger = mocker.Mock()
        writer = ZorgABJsonFileRepository(logger=logger, domain_config=domain_config)
        bundle = Bundle(type="collection", entry=[])

        filename = writer.write(bundle)

        assert filename.endswith("20240102030405_zorgab_scrape_results.json")
        saved = json.loads(Path(filename).read_text(encoding="utf-8"))
        assert saved["type"] == "collection"

    def test_write_serializes_bundle_entries(
        self, domain_config: ZorgABScraperConfig, mocker: MockerFixture, test_client: TestClient
    ) -> None:
        logger = mocker.Mock()
        writer = ZorgABJsonFileRepository(logger=logger, domain_config=domain_config)
        bundle = Bundle(
            type="collection",
            entry=[
                BundleEntry(
                    fullUrl="https://example.com/Organization/org-1",
                    resource=FhirOrganization(id="org-1", name="Org 1"),
                ),
                BundleEntry(
                    fullUrl="https://example.com/Organization/org-2",
                    resource=FhirOrganization(id="org-2", name="Org 2"),
                ),
            ],
        )

        filename = writer.write(bundle)

        saved = json.loads(Path(filename).read_text(encoding="utf-8"))
        full_urls = {entry.get("fullUrl") for entry in saved["entry"]}
        assert len(saved["entry"]) == 2
        assert "https://example.com/Organization/org-1" in full_urls
        assert "https://example.com/Organization/org-2" in full_urls

    def test_write_accepts_bundle_entries(
        self, domain_config: ZorgABScraperConfig, mocker: MockerFixture, test_client: TestClient
    ) -> None:
        logger = mocker.Mock()
        writer = ZorgABJsonFileRepository(logger=logger, domain_config=domain_config)
        result = Bundle(
            type="collection",
            entry=[
                BundleEntry(resource=FhirOrganization(id="1", name="One")),
                BundleEntry(resource=FhirOrganization(id="2", name="Two")),
            ],
        )

        filename = writer.write(result)

        saved = json.loads(Path(filename).read_text(encoding="utf-8"))
        names = {entry.get("resource", {}).get("name") for entry in saved["entry"]}
        assert "One" in names
        assert "Two" in names

    def test_write_handles_empty_payloads(
        self, domain_config: ZorgABScraperConfig, mocker: MockerFixture, test_client: TestClient
    ) -> None:
        logger = mocker.Mock()
        writer = ZorgABJsonFileRepository(logger=logger, domain_config=domain_config)
        result = Bundle(type="collection", entry=[])

        filename = writer.write(result)

        saved = json.loads(Path(filename).read_text(encoding="utf-8"))
        assert saved["entry"] == []
