import logging
from argparse import Namespace

import inject
from fhir.resources.STU3.bundle import Bundle

from app.cron.arg_types import ListType
from app.cron.utils import SubParsers
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

logger = logging.getLogger(__name__)


class UpdateSearchIndexCommand:
    NAME: str = "search-index:update"

    @inject.autoparams(
        "zorgab_scraper",
        "bundle_normalizer",
        "search_index_repository",
        "encrypted_endpoint_provider",
        "encrypted_endpoints_repository",
        "mock_organizations_merger",
    )
    def __init__(
        self,
        zorgab_scraper: ZorgabScraper,
        bundle_normalizer: BundleNormalizer,
        search_index_repository: SearchIndexRepository,
        encrypted_endpoint_provider: EncryptedEndpointProvider,
        encrypted_endpoints_repository: EncryptedEndpointsRepository,
        mock_organizations_merger: MockOrganizationsMerger,
    ) -> None:
        """
        Command to update the search index with organization data from ZorgAB.
        Scrapes and normalizes organizations into a format suitable for a search index.
        The output file is written to a static mount folder to serve it to clients.
        """
        self.__zorgab_scraper = zorgab_scraper
        self.__bundle_normalizer = bundle_normalizer
        self.__search_index_repository = search_index_repository
        self.__encrypted_endpoint_provider = encrypted_endpoint_provider
        self.__encrypted_endpoints_repository = encrypted_endpoints_repository
        self.__mock_organizations_merger = mock_organizations_merger

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

    def run(self, args: Namespace) -> int:
        logger.info("Search index update started")

        try:
            bundle_with_organizations = self.__scrape_organizations(
                args.scrape_limit,
                args.scrape_workers,
                args.scrape_sources,
            )

            normalized_organizations = self.__normalize_bundle(bundle_with_organizations)

            logger.info("Applying optional mock organization merge")

            merged_organizations = self.__mock_organizations_merger.merge(normalized_organizations)

            logger.info(
                "Organization payload prepared (normalized=%d, final=%d)",
                len(normalized_organizations),
                len(merged_organizations),
            )

            logger.info("Exporting encrypted endpoints for search index")
            encrypted_endpoints = self.__encrypted_endpoint_provider.get_all()
            logger.info("Encrypted endpoints export completed successfully")

            self.__save_search_index(SearchIndex(entries=merged_organizations))
            self.__save_encrypted_endpoints(encrypted_endpoints)
        except Exception:
            logger.exception("Search index update failed")
            return 1

        logger.info("Search index update completed successfully")
        return 0

    def __scrape_organizations(
        self,
        scrape_limit: int,
        scrape_workers: int,
        identifier_sources: list[IdentifierSource],
    ) -> Bundle:
        logger.info(
            "Scraping organizations from ZorgAB (limit=%d, workers=%d, sources=%s)",
            scrape_limit,
            scrape_workers,
            [identifier_source.value for identifier_source in identifier_sources],
        )

        try:
            bundle = self.__zorgab_scraper.run(scrape_limit, scrape_workers, identifier_sources)
        except Exception:
            logger.exception(
                "Scraping organizations from ZorgAB failed (limit=%d, workers=%d, sources=%s)",
                scrape_limit,
                scrape_workers,
                [identifier_source.value for identifier_source in identifier_sources],
            )
            raise

        logger.info("Scraping completed successfully (organizations=%d)", bundle.total)
        return bundle

    def __normalize_bundle(self, bundle: Bundle) -> list[NormalizedOrganization]:
        logger.info("Normalizing scraped bundle")

        try:
            normalized_organizations = self.__bundle_normalizer.normalize(bundle)
        except Exception:
            logger.exception("Bundle normalization failed")
            raise

        logger.info(
            "Bundle normalization completed successfully (organizations=%d)",
            len(normalized_organizations),
        )
        return normalized_organizations

    def __save_search_index(self, search_index: SearchIndex) -> None:
        logger.info("Saving search index")

        try:
            self.__search_index_repository.save(search_index)
        except Exception:
            logger.exception("Saving search index failed")
            raise

        logger.info("Search index saved successfully")

    def __save_encrypted_endpoints(self, encrypted_endpoints: dict[int, str]) -> None:
        logger.info("Saving encrypted endpoints")

        try:
            self.__encrypted_endpoints_repository.save(encrypted_endpoints)
        except Exception:
            logger.exception("Saving encrypted endpoints failed")
            raise

        logger.info("Encrypted endpoints saved successfully")
