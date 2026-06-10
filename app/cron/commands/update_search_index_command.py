import logging
from argparse import Namespace
from collections.abc import Iterator

import inject

from app.cron.arg_types import ListType
from app.cron.utils import SubParsers
from app.normalization.models import NormalizedOrganization
from app.normalization.organization_normalizer import OrganizationNormalizer
from app.search_indexation.repositories import EncryptedEndpointsRepository, SearchIndexStreamRepository
from app.search_indexation.services import (
    EncryptedEndpointProvider,
)
from app.zorgab_scraper.config import IdentifierSource
from app.zorgab_scraper.models import OrganizationBundleEntry
from app.zorgab_scraper.scraper import ZorgabScraper

logger = logging.getLogger(__name__)


class UpdateSearchIndexCommand:
    NAME: str = "search-index:update"

    @inject.autoparams(
        "zorgab_scraper",
        "organization_normalizer",
        "search_index_repository",
        "encrypted_endpoint_provider",
        "encrypted_endpoints_repository",
        "mock_organizations_merger",
    )
    def __init__(
        self,
        zorgab_scraper: ZorgabScraper,
        organization_normalizer: OrganizationNormalizer,
        search_index_repository: SearchIndexStreamRepository,
        encrypted_endpoint_provider: EncryptedEndpointProvider,
        encrypted_endpoints_repository: EncryptedEndpointsRepository,
    ) -> None:
        """
        Command to update the search index with organization data from ZorgAB.
        Scrapes and normalizes organizations into a format suitable for a search index.
        The output file is written to a static mount folder to serve it to clients.
        """
        self.__zorgab_scraper = zorgab_scraper
        self.__organization_normalizer = organization_normalizer
        self.__search_index_repository = search_index_repository
        self.__encrypted_endpoint_provider = encrypted_endpoint_provider
        self.__encrypted_endpoints_repository = encrypted_endpoints_repository

    @staticmethod
    def init_arguments(subparser: SubParsers) -> None:
        parser = subparser.add_parser(
            UpdateSearchIndexCommand.NAME,
            help="Scrape organization data from ZorgAB, normalize it, and update the search index",
        )
        parser.add_argument(
            "--scrape-limit",
            "-l",
            type=int,
            default=0,
            help="Maximum number of identifiers to process for scraping; 0 or negative for no limit",
        )
        parser.add_argument(
            "--scrape-workers",
            "-w",
            type=int,
            default=4,
            help="Number of concurrent workers to use for scraping; set to 1 for sequential processing",
        )
        parser.add_argument(
            "--scrape-sources",
            "-s",
            type=ListType(IdentifierSource),
            default=list(IdentifierSource),
            help="Comma-separated list of identifier sources to use for scraping",
        )

    def run(self, args: Namespace) -> None:
        logger.info("Search index update started")

        bundle_entries = self.__scrape_organizations(
            args.scrape_limit,
            args.scrape_workers,
            args.scrape_sources,
        )

        normalized_organizations = self.__normalize_entries(bundle_entries)

        self.__save_search_index(normalized_organizations)

        logger.info("Exporting encrypted endpoints for search index")
        encrypted_endpoints = self.__encrypted_endpoint_provider.get_all()
        logger.info("Encrypted endpoints export completed successfully")

        self.__save_encrypted_endpoints(encrypted_endpoints)

        logger.info("Search index update completed successfully")

    def __scrape_organizations(
        self,
        scrape_limit: int,
        scrape_workers: int,
        identifier_sources: list[IdentifierSource],
    ) -> Iterator[OrganizationBundleEntry]:
        logger.info(
            "Scraping organizations from ZorgAB (limit=%d, workers=%d, sources=%s)",
            scrape_limit,
            scrape_workers,
            [identifier_source.value for identifier_source in identifier_sources],
        )

        try:
            bundle_entries = self.__zorgab_scraper.run(scrape_limit, scrape_workers, identifier_sources)
        except Exception:
            logger.exception(
                "Scraping organizations from ZorgAB failed (limit=%d, workers=%d, sources=%s)",
                scrape_limit,
                scrape_workers,
                [identifier_source.value for identifier_source in identifier_sources],
            )
            raise

        return bundle_entries

    def __normalize_entries(
        self, bundle_entries: Iterator[OrganizationBundleEntry]
    ) -> Iterator[NormalizedOrganization]:
        for entry in bundle_entries:
            logger.debug("Normalizing organization with entry fullUrl=%s", entry.full_url)

            yield self.__organization_normalizer.normalize(entry.resource)

    def __save_search_index(self, normalized_organizations: Iterator[NormalizedOrganization]) -> None:
        logger.info("Saving search index")

        self.__search_index_repository.save(normalized_organizations)

        logger.info("Search index saved successfully")

    def __save_encrypted_endpoints(self, encrypted_endpoints: dict[int, str]) -> None:
        logger.info("Saving encrypted endpoints")

        try:
            self.__encrypted_endpoints_repository.save(encrypted_endpoints)
        except Exception:
            logger.exception("Saving encrypted endpoints failed")
            raise

        logger.info("Encrypted endpoints saved successfully")
