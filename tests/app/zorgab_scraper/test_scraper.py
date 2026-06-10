from collections.abc import Iterator

from pytest import fixture
from pytest_mock import MockerFixture

from app.addressing.models import IdentificationType
from app.zorgab_scraper.config import IdentifierSource
from app.zorgab_scraper.models import Identifier, OrganizationBundleEntry, ScrapeResult
from app.zorgab_scraper.scraper import ZorgabScraper
from app.zorgab_scraper.services import IdentifierProvider, OrganizationDeduplicator, ZorgabScrapeExecutor


class TestZorgabScraper:
    @fixture
    def empty_stream(self) -> Iterator[OrganizationBundleEntry]:
        return iter([])

    def test_run_logs_summaries_for_not_found_and_errors(
        self, mocker: MockerFixture, empty_stream: Iterator[OrganizationBundleEntry]
    ) -> None:
        identifier_provider = mocker.Mock()
        executor = mocker.Mock()
        organization_deduplicator = mocker.Mock(spec=OrganizationDeduplicator)
        organization_deduplicator.should_include.return_value = True
        scraper = ZorgabScraper(
            identifier_provider=identifier_provider,
            executor=executor,
            organization_deduplicator=organization_deduplicator,
        )
        identifier_provider.get_identifiers.return_value = [Identifier(IdentificationType.ura, "123")]
        executor.execute.return_value = ScrapeResult(
            bundle_entries=empty_stream, not_found=["URA:123"], errors=["boom"]
        )

        logger = mocker.patch("app.zorgab_scraper.scraper.logger")

        identifier_sources = [IdentifierSource.zakl_xml]
        result = list(scraper.run(scrape_limit=5, workers=0, identifier_sources=identifier_sources))

        assert result == []
        identifier_provider.get_identifiers.assert_called_once_with(identifier_sources=identifier_sources, limit=5)
        executor.execute.assert_called_once_with(
            identifiers=identifier_provider.get_identifiers.return_value, workers=1
        )
        logger.info.assert_any_call(
            "Streaming scrape completed: %d deduplicated organizations from %d identifiers, %d not found, %d errors",
            0,  # found
            1,  # identifiers
            1,  # not found
            1,  # errors
        )
        logger.debug.assert_any_call("Summary of not found organizations: %s", "URA:123")
        logger.warning.assert_called_once_with("Summary of errors: %s", "boom")

    def test_run_logs_success_without_not_found_or_errors(
        self, mocker: MockerFixture, empty_stream: Iterator[OrganizationBundleEntry]
    ) -> None:
        identifier_provider = mocker.Mock()
        executor = mocker.Mock()

        logger = mocker.patch("app.zorgab_scraper.scraper.logger")

        organization_deduplicator = mocker.Mock(spec=OrganizationDeduplicator)
        organization_deduplicator.should_include.return_value = True
        scraper = ZorgabScraper(
            identifier_provider=identifier_provider,
            executor=executor,
            organization_deduplicator=organization_deduplicator,
        )
        identifier_provider.get_identifiers.return_value = [Identifier(IdentificationType.ura, "123")]
        executor.execute.return_value = ScrapeResult(bundle_entries=empty_stream, not_found=[], errors=[])

        identifier_sources = [IdentifierSource.zakl_xml]
        result = list(scraper.run(scrape_limit=5, workers=1, identifier_sources=identifier_sources))

        assert result == []
        identifier_provider.get_identifiers.assert_called_once_with(identifier_sources=identifier_sources, limit=5)

        logger.info.assert_any_call(
            "Streaming scrape completed: %d deduplicated organizations from %d identifiers, %d not found, %d errors",
            0,  # found
            1,  # identifiers
            0,  # not found
            0,  # errors
        )

        logger.warning.assert_not_called()

    def test_scraper_logs_when_it_starts_scraping_without_scrape_limit(
        self, mocker: MockerFixture, empty_stream: Iterator[OrganizationBundleEntry]
    ) -> None:
        identifier_provider = mocker.Mock(spec=IdentifierProvider)
        identifier_provider.get_identifiers.return_value = [Identifier(IdentificationType.ura, "123")]

        executor = mocker.Mock(spec=ZorgabScrapeExecutor)
        executor.execute.return_value = ScrapeResult(bundle_entries=empty_stream, not_found=[], errors=[])

        organization_deduplicator = mocker.Mock(spec=OrganizationDeduplicator)
        organization_deduplicator.should_include.return_value = True

        logger = mocker.patch("app.zorgab_scraper.scraper.logger")

        scraper = ZorgabScraper(
            identifier_provider=identifier_provider,
            executor=executor,
            organization_deduplicator=organization_deduplicator,
        )
        result = list(scraper.run(scrape_limit=None, workers=1, identifier_sources=list(IdentifierSource)))
        assert result == []

        logger.info.assert_any_call("No scrape limit configured; scraping full dataset")
