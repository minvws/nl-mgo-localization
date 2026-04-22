import argparse
import logging
from argparse import Namespace

import pytest
from fhir.resources.STU3.bundle import Bundle, BundleEntry
from fhir.resources.STU3.organization import Organization
from pytest import LogCaptureFixture
from pytest_mock import MockerFixture

from app.cron.commands.update_search_index_command import UpdateSearchIndexCommand
from app.normalization.bundle import BundleNormalizer
from app.normalization.models import NormalizedOrganization
from app.search_indexation.models import SearchIndex
from app.search_indexation.repositories import EncryptedEndpointsRepository, SearchIndexRepository
from app.search_indexation.services import (
    EncryptedEndpointProvider,
    MockOrganizationsMerger,
)
from app.zorgab_scraper.config import IdentifierSource
from app.zorgab_scraper.scraper import ZorgabScraper
from tests.utils import assert_captured_logs


@pytest.fixture()
def bundle() -> Bundle:
    organization = Organization()
    bundle_entry = BundleEntry(fullUrl="urn:uuid:org-123", resource=organization)
    return Bundle(type="collection", entry=[bundle_entry], total=1)


@pytest.fixture()
def normalized_organizations() -> list[NormalizedOrganization]:
    return [
        {"id": "urn:uuid:org-123", "name": "Org 1"},
    ]


class TestUpdateSearchIndexCommand:
    def test_happy_path(
        self,
        bundle: Bundle,
        normalized_organizations: list[NormalizedOrganization],
        caplog: LogCaptureFixture,
        mocker: MockerFixture,
    ) -> None:
        mock_scraper = mocker.Mock(spec=ZorgabScraper)
        mock_normalizer = mocker.Mock(spec=BundleNormalizer)
        mock_repository = mocker.Mock(spec=SearchIndexRepository)
        mock_endpoint_provider = mocker.Mock(spec=EncryptedEndpointProvider)
        mock_encrypted_endpoints_repository = mocker.Mock(spec=EncryptedEndpointsRepository)
        mock_organizations_merger = mocker.Mock(spec=MockOrganizationsMerger)
        mock_endpoint_provider.get_all.return_value = {"org-123": "encrypted-url-123"}
        mock_organizations_merger.merge.return_value = normalized_organizations

        mock_scraper.run.return_value = bundle
        mock_normalizer.normalize.return_value = normalized_organizations

        args = Namespace(
            scrape_limit=0,
            scrape_workers=4,
            scrape_sources=[IdentifierSource.zakl_xml, IdentifierSource.agb_csv],
        )
        caplog.set_level(logging.INFO, logger="app.cron.commands.update_search_index_command")

        command = UpdateSearchIndexCommand(
            zorgab_scraper=mock_scraper,
            bundle_normalizer=mock_normalizer,
            search_index_repository=mock_repository,
            encrypted_endpoint_provider=mock_endpoint_provider,
            encrypted_endpoints_repository=mock_encrypted_endpoints_repository,
            mock_organizations_merger=mock_organizations_merger,
        )
        exit_code = command.run(args)
        assert exit_code == 0

        assert_captured_logs(
            caplog,
            [
                ("Search index update started", logging.INFO),
                (
                    "Scraping organizations from ZorgAB (limit=0, workers=4, sources=['zakl_xml', 'agb_csv'])",
                    logging.INFO,
                ),
                ("Scraping completed successfully (organizations=1)", logging.INFO),
                ("Normalizing scraped bundle", logging.INFO),
                ("Bundle normalization completed successfully (organizations=1)", logging.INFO),
                ("Saving search index", logging.INFO),
                ("Search index saved successfully", logging.INFO),
                ("Exporting encrypted endpoints for search index", logging.INFO),
                ("Encrypted endpoints export completed successfully", logging.INFO),
                ("Saving encrypted endpoints", logging.INFO),
                ("Encrypted endpoints saved successfully", logging.INFO),
                ("Search index update completed successfully", logging.INFO),
            ],
        )

        mock_scraper.run.assert_called_once_with(args.scrape_limit, args.scrape_workers, args.scrape_sources)
        mock_normalizer.normalize.assert_called_once_with(bundle)
        mock_repository.save.assert_called_once_with(SearchIndex(normalized_organizations))
        mock_encrypted_endpoints_repository.save.assert_called_once_with({"org-123": "encrypted-url-123"})
        mock_endpoint_provider.get_all.assert_called_once()

    def test_scraper_failure(self, caplog: LogCaptureFixture, mocker: MockerFixture) -> None:
        mock_scraper = mocker.Mock(spec=ZorgabScraper)
        mock_normalizer = mocker.Mock(spec=BundleNormalizer)
        mock_repository = mocker.Mock(spec=SearchIndexRepository)
        mock_endpoint_provider = mocker.Mock(spec=EncryptedEndpointProvider)
        mock_encrypted_endpoints_repository = mocker.Mock(spec=EncryptedEndpointsRepository)
        mock_organizations_merger = mocker.Mock(spec=MockOrganizationsMerger)

        mock_scraper.run.side_effect = Exception("Scraper failed")

        args = Namespace(
            scrape_limit=0,
            scrape_workers=4,
            scrape_sources=[IdentifierSource.zakl_xml, IdentifierSource.agb_csv],
        )
        caplog.set_level(logging.INFO, logger="app.cron.commands.update_search_index_command")

        command = UpdateSearchIndexCommand(
            zorgab_scraper=mock_scraper,
            bundle_normalizer=mock_normalizer,
            search_index_repository=mock_repository,
            encrypted_endpoint_provider=mock_endpoint_provider,
            encrypted_endpoints_repository=mock_encrypted_endpoints_repository,
            mock_organizations_merger=mock_organizations_merger,
        )

        exit_code = command.run(args)
        assert exit_code == 1

        assert_captured_logs(
            caplog,
            [
                (
                    "Search index update started",
                    logging.INFO,
                ),
                (
                    "Scraping organizations from ZorgAB (limit=0, workers=4, sources=['zakl_xml', 'agb_csv'])",
                    logging.INFO,
                ),
                (
                    "Scraping organizations from ZorgAB failed (limit=0, workers=4, sources=['zakl_xml', 'agb_csv'])",
                    logging.ERROR,
                ),
                (
                    "Search index update failed",
                    logging.ERROR,
                ),
            ],
        )

        mock_scraper.run.assert_called_once_with(args.scrape_limit, args.scrape_workers, args.scrape_sources)
        mock_normalizer.normalize.assert_not_called()
        mock_repository.save.assert_not_called()
        mock_encrypted_endpoints_repository.save.assert_not_called()
        mock_endpoint_provider.get_all.assert_not_called()

    def test_normalization_failure(self, bundle: Bundle, caplog: LogCaptureFixture, mocker: MockerFixture) -> None:
        mock_scraper = mocker.Mock(spec=ZorgabScraper)
        mock_normalizer = mocker.Mock(spec=BundleNormalizer)
        mock_repository = mocker.Mock(spec=SearchIndexRepository)
        mock_endpoint_provider = mocker.Mock(spec=EncryptedEndpointProvider)
        mock_encrypted_endpoints_repository = mocker.Mock(spec=EncryptedEndpointsRepository)
        mock_organizations_merger = mocker.Mock(spec=MockOrganizationsMerger)

        mock_scraper.run.return_value = bundle
        mock_normalizer.normalize.side_effect = Exception("Normalization failed")

        args = Namespace(
            scrape_limit=0,
            scrape_workers=4,
            scrape_sources=[IdentifierSource.zakl_xml, IdentifierSource.agb_csv],
        )
        caplog.set_level(logging.INFO, logger="app.cron.commands.update_search_index_command")

        command = UpdateSearchIndexCommand(
            zorgab_scraper=mock_scraper,
            bundle_normalizer=mock_normalizer,
            search_index_repository=mock_repository,
            encrypted_endpoint_provider=mock_endpoint_provider,
            encrypted_endpoints_repository=mock_encrypted_endpoints_repository,
            mock_organizations_merger=mock_organizations_merger,
        )
        exit_code = command.run(args)
        assert exit_code == 1

        assert_captured_logs(
            caplog,
            [
                ("Search index update started", logging.INFO),
                ("Scraping completed successfully (organizations=1)", logging.INFO),
                ("Bundle normalization failed", logging.ERROR),
                ("Search index update failed", logging.ERROR),
            ],
        )

        mock_scraper.run.assert_called_once_with(args.scrape_limit, args.scrape_workers, args.scrape_sources)
        mock_normalizer.normalize.assert_called_once_with(bundle)
        mock_repository.save.assert_not_called()
        mock_encrypted_endpoints_repository.save.assert_not_called()
        mock_endpoint_provider.get_all.assert_not_called()

    def test_persistence_failure(
        self,
        bundle: Bundle,
        normalized_organizations: list[NormalizedOrganization],
        caplog: LogCaptureFixture,
        mocker: MockerFixture,
    ) -> None:
        mock_scraper = mocker.Mock(spec=ZorgabScraper)
        mock_normalizer = mocker.Mock(spec=BundleNormalizer)
        mock_repository = mocker.Mock(spec=SearchIndexRepository)
        mock_endpoint_provider = mocker.Mock(spec=EncryptedEndpointProvider)
        mock_encrypted_endpoints_repository = mocker.Mock(spec=EncryptedEndpointsRepository)
        mock_organizations_merger = mocker.Mock(spec=MockOrganizationsMerger)

        mock_scraper.run.return_value = bundle
        mock_normalizer.normalize.return_value = normalized_organizations
        mock_organizations_merger.merge.return_value = normalized_organizations
        mock_endpoint_provider.get_all.return_value = {"org-123": "encrypted-url-123"}
        mock_repository.save.side_effect = Exception("Persistence failure")

        args = Namespace(
            scrape_limit=0,
            scrape_workers=4,
            scrape_sources=[IdentifierSource.zakl_xml, IdentifierSource.agb_csv],
        )
        caplog.set_level(logging.INFO, logger="app.cron.commands.update_search_index_command")

        command = UpdateSearchIndexCommand(
            zorgab_scraper=mock_scraper,
            bundle_normalizer=mock_normalizer,
            search_index_repository=mock_repository,
            encrypted_endpoint_provider=mock_endpoint_provider,
            encrypted_endpoints_repository=mock_encrypted_endpoints_repository,
            mock_organizations_merger=mock_organizations_merger,
        )

        exit_code = command.run(args)
        assert exit_code == 1

        assert_captured_logs(
            caplog,
            [
                ("Search index update started", logging.INFO),
                ("Scraping completed successfully (organizations=1)", logging.INFO),
                ("Bundle normalization completed successfully (organizations=1)", logging.INFO),
                ("Saving search index", logging.INFO),
                ("Saving search index failed", logging.ERROR),
                ("Search index update failed", logging.ERROR),
            ],
        )

        mock_scraper.run.assert_called_once_with(args.scrape_limit, args.scrape_workers, args.scrape_sources)
        mock_normalizer.normalize.assert_called_once_with(bundle)
        mock_repository.save.assert_called_once()
        mock_encrypted_endpoints_repository.save.assert_not_called()
        mock_endpoint_provider.get_all.assert_called_once()

    def test_encrypted_endpoints_save_failure(
        self,
        bundle: Bundle,
        normalized_organizations: list[NormalizedOrganization],
        caplog: LogCaptureFixture,
        mocker: MockerFixture,
    ) -> None:
        mock_scraper = mocker.Mock(spec=ZorgabScraper)
        mock_normalizer = mocker.Mock(spec=BundleNormalizer)
        mock_repository = mocker.Mock(spec=SearchIndexRepository)
        mock_endpoint_provider = mocker.Mock(spec=EncryptedEndpointProvider)
        mock_encrypted_endpoints_repository = mocker.Mock(spec=EncryptedEndpointsRepository)
        mock_organizations_merger = mocker.Mock(spec=MockOrganizationsMerger)

        mock_scraper.run.return_value = bundle
        mock_normalizer.normalize.return_value = normalized_organizations
        mock_organizations_merger.merge.return_value = normalized_organizations
        mock_endpoint_provider.get_all.return_value = {"org-123": "encrypted-url-123"}
        mock_encrypted_endpoints_repository.save.side_effect = Exception("Save failure")

        args = Namespace(
            scrape_limit=0,
            scrape_workers=4,
            scrape_sources=[IdentifierSource.zakl_xml, IdentifierSource.agb_csv],
        )
        caplog.set_level(logging.INFO, logger="app.cron.commands.update_search_index_command")

        command = UpdateSearchIndexCommand(
            zorgab_scraper=mock_scraper,
            bundle_normalizer=mock_normalizer,
            search_index_repository=mock_repository,
            encrypted_endpoint_provider=mock_endpoint_provider,
            encrypted_endpoints_repository=mock_encrypted_endpoints_repository,
            mock_organizations_merger=mock_organizations_merger,
        )

        exit_code = command.run(args)
        assert exit_code == 1

        assert_captured_logs(
            caplog,
            [
                ("Search index update started", logging.INFO),
                ("Saving search index", logging.INFO),
                ("Search index saved successfully", logging.INFO),
                ("Saving encrypted endpoints", logging.INFO),
                ("Saving encrypted endpoints failed", logging.ERROR),
                ("Search index update failed", logging.ERROR),
            ],
        )

        mock_encrypted_endpoints_repository.save.assert_called_once()
        mock_repository.save.assert_called_once()

    def test_init_arguments(self) -> None:
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()

        UpdateSearchIndexCommand.init_arguments(subparsers)

        args = parser.parse_args(
            [
                UpdateSearchIndexCommand.NAME,
                "--scrape-limit",
                "10",
                "--scrape-workers",
                "2",
            ]
        )

        assert args.scrape_limit == 10
        assert args.scrape_workers == 2
