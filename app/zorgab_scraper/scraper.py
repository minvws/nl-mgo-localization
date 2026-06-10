import logging
from collections.abc import Iterator

import inject

from .config import IdentifierSource
from .models import OrganizationBundleEntry
from .services import IdentifierProvider, OrganizationDeduplicator, ZorgabScrapeExecutor

logger = logging.getLogger(__name__)


class ZorgabScraper:
    @inject.autoparams("executor", "identifier_provider", "organization_deduplicator")
    def __init__(
        self,
        executor: ZorgabScrapeExecutor,
        identifier_provider: IdentifierProvider,
        organization_deduplicator: OrganizationDeduplicator,
    ) -> None:
        self.__executor = executor
        self.__identifier_provider = identifier_provider
        self.__organization_deduplicator = organization_deduplicator

    def run(
        self,
        scrape_limit: int | None,
        workers: int,
        identifier_sources: list[IdentifierSource],
    ) -> Iterator[OrganizationBundleEntry]:
        if not scrape_limit:
            logger.info("No scrape limit configured; scraping full dataset")

        identifiers = self.__identifier_provider.get_identifiers(
            identifier_sources=identifier_sources,
            limit=scrape_limit,
        )
        workers = max(1, workers)
        result = self.__executor.execute(identifiers=identifiers, workers=workers)

        found_count = 0
        self.__organization_deduplicator.reset()

        for organization_bundle_entry in result.bundle_entries:
            if not self.__organization_deduplicator.should_include(organization_bundle_entry):
                continue

            found_count += 1

            yield organization_bundle_entry

        logger.info(
            "Streaming scrape completed: %d deduplicated organizations from %d identifiers, %d not found, %d errors",
            found_count,
            len(identifiers),
            len(result.not_found),
            len(result.errors),
        )

        if result.not_found:
            logger.debug("Summary of not found organizations: %s", ", ".join(result.not_found))

        if result.errors:
            logger.warning("Summary of errors: %s", "; ".join(result.errors))
