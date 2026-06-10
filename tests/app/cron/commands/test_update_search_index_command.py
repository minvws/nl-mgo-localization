import argparse
import logging
from argparse import Namespace

import pytest
from fhir.resources.STU3.organization import Organization
from pytest import LogCaptureFixture
from pytest_mock import MockerFixture

from app.cron.commands.update_search_index_command import UpdateSearchIndexCommand
from app.normalization.models import NormalizedOrganization
from app.normalization.organization_normalizer import OrganizationNormalizer
from app.search_indexation.repositories import EncryptedEndpointsRepository, SearchIndexStreamRepository
from app.search_indexation.services import EncryptedEndpointProvider
from app.zorgab_scraper.config import IdentifierSource
from app.zorgab_scraper.models import OrganizationBundleEntry
from app.zorgab_scraper.scraper import ZorgabScraper
from tests.utils import assert_captured_logs


@pytest.fixture()
def bundle_entry() -> OrganizationBundleEntry:
    return OrganizationBundleEntry(full_url="urn:uuid:org-123", resource=Organization())


@pytest.fixture()
def normalized_organization() -> NormalizedOrganization:
    return {"id": "urn:uuid:org-123", "name": "Org 1"}


class TestUpdateSearchIndexCommand:
    def test_happy_path(
        self,
        bundle_entry: OrganizationBundleEntry,
        normalized_organization: NormalizedOrganization,
        caplog: LogCaptureFixture,
        mocker: MockerFixture,
    ) -> None:
        mock_scraper = mocker.Mock(spec=ZorgabScraper)
        mock_normalizer = mocker.Mock(spec=OrganizationNormalizer)
        mock_repository = mocker.Mock(spec=SearchIndexStreamRepository)
        mock_endpoint_provider = mocker.Mock(spec=EncryptedEndpointProvider)
        mock_encrypted_endpoints_repository = mocker.Mock(spec=EncryptedEndpointsRepository)

        mock_scraper.run.return_value = iter([bundle_entry])
        mock_normalizer.normalize.return_value = normalized_organization
        mock_endpoint_provider.get_all.return_value = {"org-123": "encrypted-url-123"}
        mock_repository.save.side_effect = lambda orgs: list(orgs)

        args = Namespace(
            scrape_limit=0,
            scrape_workers=4,
            scrape_sources=[IdentifierSource.zakl_xml, IdentifierSource.agb_csv],
        )
        caplog.set_level(logging.INFO, logger="app.cron.commands.update_search_index_command")

        command = UpdateSearchIndexCommand(
            zorgab_scraper=mock_scraper,
            organization_normalizer=mock_normalizer,
            search_index_repository=mock_repository,
            encrypted_endpoint_provider=mock_endpoint_provider,
            encrypted_endpoints_repository=mock_encrypted_endpoints_repository,
        )
        command.run(args)

        assert_captured_logs(
            caplog,
            [
                ("Search index update started", logging.INFO),
                (
                    "Scraping organizations from ZorgAB (limit=0, workers=4, sources=['zakl_xml', 'agb_csv'])",
                    logging.INFO,
                ),
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
        mock_normalizer.normalize.assert_called_once_with(bundle_entry.resource)
        mock_repository.save.assert_called_once()
        mock_encrypted_endpoints_repository.save.assert_called_once_with({"org-123": "encrypted-url-123"})
        mock_endpoint_provider.get_all.assert_called_once()

    def test_scraper_failure(self, caplog: LogCaptureFixture, mocker: MockerFixture) -> None:
        mock_scraper = mocker.Mock(spec=ZorgabScraper)
        mock_normalizer = mocker.Mock(spec=OrganizationNormalizer)
        mock_repository = mocker.Mock(spec=SearchIndexStreamRepository)
        mock_endpoint_provider = mocker.Mock(spec=EncryptedEndpointProvider)
        mock_encrypted_endpoints_repository = mocker.Mock(spec=EncryptedEndpointsRepository)

        mock_scraper.run.side_effect = Exception("Scraper failed")

        args = Namespace(
            scrape_limit=0,
            scrape_workers=4,
            scrape_sources=[IdentifierSource.zakl_xml, IdentifierSource.agb_csv],
        )
        caplog.set_level(logging.INFO, logger="app.cron.commands.update_search_index_command")

        command = UpdateSearchIndexCommand(
            zorgab_scraper=mock_scraper,
            organization_normalizer=mock_normalizer,
            search_index_repository=mock_repository,
            encrypted_endpoint_provider=mock_endpoint_provider,
            encrypted_endpoints_repository=mock_encrypted_endpoints_repository,
        )

        with pytest.raises(Exception, match="Scraper failed"):
            command.run(args)

        assert_captured_logs(
            caplog,
            [
                ("Search index update started", logging.INFO),
                (
                    "Scraping organizations from ZorgAB (limit=0, workers=4, sources=['zakl_xml', 'agb_csv'])",
                    logging.INFO,
                ),
                (
                    "Scraping organizations from ZorgAB failed (limit=0, workers=4, sources=['zakl_xml', 'agb_csv'])",
                    logging.ERROR,
                ),
            ],
        )

        mock_scraper.run.assert_called_once_with(args.scrape_limit, args.scrape_workers, args.scrape_sources)
        mock_normalizer.normalize.assert_not_called()
        mock_repository.save.assert_not_called()
        mock_encrypted_endpoints_repository.save.assert_not_called()
        mock_endpoint_provider.get_all.assert_not_called()

    def test_normalization_failure(
        self,
        bundle_entry: OrganizationBundleEntry,
        caplog: LogCaptureFixture,
        mocker: MockerFixture,
    ) -> None:
        mock_scraper = mocker.Mock(spec=ZorgabScraper)
        mock_normalizer = mocker.Mock(spec=OrganizationNormalizer)
        mock_repository = mocker.Mock(spec=SearchIndexStreamRepository)
        mock_endpoint_provider = mocker.Mock(spec=EncryptedEndpointProvider)
        mock_encrypted_endpoints_repository = mocker.Mock(spec=EncryptedEndpointsRepository)

        mock_scraper.run.return_value = iter([bundle_entry])
        mock_normalizer.normalize.side_effect = Exception("Normalization failed")
        mock_repository.save.side_effect = lambda orgs: list(orgs)

        args = Namespace(
            scrape_limit=0,
            scrape_workers=4,
            scrape_sources=[IdentifierSource.zakl_xml, IdentifierSource.agb_csv],
        )
        caplog.set_level(logging.INFO, logger="app.cron.commands.update_search_index_command")

        command = UpdateSearchIndexCommand(
            zorgab_scraper=mock_scraper,
            organization_normalizer=mock_normalizer,
            search_index_repository=mock_repository,
            encrypted_endpoint_provider=mock_endpoint_provider,
            encrypted_endpoints_repository=mock_encrypted_endpoints_repository,
        )
        with pytest.raises(Exception, match="Normalization failed"):
            command.run(args)

        assert_captured_logs(
            caplog,
            [
                ("Search index update started", logging.INFO),
                (
                    "Scraping organizations from ZorgAB (limit=0, workers=4, sources=['zakl_xml', 'agb_csv'])",
                    logging.INFO,
                ),
                ("Saving search index", logging.INFO),
            ],
        )

        mock_scraper.run.assert_called_once_with(args.scrape_limit, args.scrape_workers, args.scrape_sources)
        mock_normalizer.normalize.assert_called_once_with(bundle_entry.resource)
        mock_repository.save.assert_called_once()
        mock_encrypted_endpoints_repository.save.assert_not_called()
        mock_endpoint_provider.get_all.assert_not_called()

    def test_persistence_failure(
        self,
        bundle_entry: OrganizationBundleEntry,
        normalized_organization: NormalizedOrganization,
        caplog: LogCaptureFixture,
        mocker: MockerFixture,
    ) -> None:
        mock_scraper = mocker.Mock(spec=ZorgabScraper)
        mock_normalizer = mocker.Mock(spec=OrganizationNormalizer)
        mock_repository = mocker.Mock(spec=SearchIndexStreamRepository)
        mock_endpoint_provider = mocker.Mock(spec=EncryptedEndpointProvider)
        mock_encrypted_endpoints_repository = mocker.Mock(spec=EncryptedEndpointsRepository)

        mock_scraper.run.return_value = iter([bundle_entry])
        mock_normalizer.normalize.return_value = normalized_organization
        mock_repository.save.side_effect = Exception("Persistence failure")

        args = Namespace(
            scrape_limit=0,
            scrape_workers=4,
            scrape_sources=[IdentifierSource.zakl_xml, IdentifierSource.agb_csv],
        )
        caplog.set_level(logging.INFO, logger="app.cron.commands.update_search_index_command")

        command = UpdateSearchIndexCommand(
            zorgab_scraper=mock_scraper,
            organization_normalizer=mock_normalizer,
            search_index_repository=mock_repository,
            encrypted_endpoint_provider=mock_endpoint_provider,
            encrypted_endpoints_repository=mock_encrypted_endpoints_repository,
        )

        with pytest.raises(Exception, match="Persistence failure"):
            command.run(args)

        assert_captured_logs(
            caplog,
            [
                ("Search index update started", logging.INFO),
                (
                    "Scraping organizations from ZorgAB (limit=0, workers=4, sources=['zakl_xml', 'agb_csv'])",
                    logging.INFO,
                ),
                ("Saving search index", logging.INFO),
            ],
        )

        mock_scraper.run.assert_called_once_with(args.scrape_limit, args.scrape_workers, args.scrape_sources)
        mock_repository.save.assert_called_once()
        mock_encrypted_endpoints_repository.save.assert_not_called()
        mock_endpoint_provider.get_all.assert_not_called()

    def test_encrypted_endpoints_save_failure(
        self,
        bundle_entry: OrganizationBundleEntry,
        normalized_organization: NormalizedOrganization,
        caplog: LogCaptureFixture,
        mocker: MockerFixture,
    ) -> None:
        mock_scraper = mocker.Mock(spec=ZorgabScraper)
        mock_normalizer = mocker.Mock(spec=OrganizationNormalizer)
        mock_repository = mocker.Mock(spec=SearchIndexStreamRepository)
        mock_endpoint_provider = mocker.Mock(spec=EncryptedEndpointProvider)
        mock_encrypted_endpoints_repository = mocker.Mock(spec=EncryptedEndpointsRepository)

        mock_scraper.run.return_value = iter([bundle_entry])
        mock_normalizer.normalize.return_value = normalized_organization
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
            organization_normalizer=mock_normalizer,
            search_index_repository=mock_repository,
            encrypted_endpoint_provider=mock_endpoint_provider,
            encrypted_endpoints_repository=mock_encrypted_endpoints_repository,
        )

        with pytest.raises(Exception, match="Save failure"):
            command.run(args)

        assert_captured_logs(
            caplog,
            [
                ("Search index update started", logging.INFO),
                (
                    "Scraping organizations from ZorgAB (limit=0, workers=4, sources=['zakl_xml', 'agb_csv'])",
                    logging.INFO,
                ),
                ("Saving search index", logging.INFO),
                ("Search index saved successfully", logging.INFO),
                ("Exporting encrypted endpoints for search index", logging.INFO),
                ("Encrypted endpoints export completed successfully", logging.INFO),
                ("Saving encrypted endpoints", logging.INFO),
                ("Saving encrypted endpoints failed", logging.ERROR),
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
