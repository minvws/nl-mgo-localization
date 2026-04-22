import logging

import inject
from fhir.resources.STU3.bundle import Bundle

from app.zorgab_scraper.config import IdentifierSource
from app.zorgab_scraper.factories import ZorgabBundleFactory
from app.zorgab_scraper.services import IdentifierProvider, ZorgabScrapeExecutor

logger = logging.getLogger(__name__)


class ZorgabScraper:
    @inject.autoparams("executor", "identifier_provider", "bundle_factory")
    def __init__(
        self,
        executor: ZorgabScrapeExecutor,
        identifier_provider: IdentifierProvider,
        bundle_factory: ZorgabBundleFactory,
    ) -> None:
        self.__executor = executor
        self.__identifier_provider = identifier_provider
        self.__bundle_factory = bundle_factory

    def run(
        self,
        scrape_limit: int | None,
        workers: int,
        identifier_sources: list[IdentifierSource],
    ) -> Bundle:
        if not scrape_limit:
            logger.info("No scrape limit configured; scraping full dataset")

        identifiers = self.__identifier_provider.get_identifiers(
            identifier_sources=identifier_sources,
            limit=scrape_limit,
        )
        workers = max(1, workers)
        result = self.__executor.execute(identifiers=identifiers, workers=workers)

        logger.info(
            "Successfully scraped %d bundles for %d identifiers, from which: %d not found and %d errors",
            len(result.bundles),
            len(identifiers),
            len(result.not_found),
            len(result.errors),
        )

        if result.not_found:
            logger.debug("Summary of not found organizations: %s", ", ".join(result.not_found))

        if result.errors:
            logger.warning("Summary of errors: %s", "; ".join(result.errors))

        bundle = self.__bundle_factory.create(result)
        logger.info("Merged %d bundles into a single bundle with %d organizations", len(result.bundles), bundle.total)

        return bundle
