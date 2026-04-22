from fhir.resources.STU3.bundle import Bundle
from pytest_mock import MockerFixture

from app.addressing.models import IdentificationType
from app.zorgab_scraper.config import IdentifierSource
from app.zorgab_scraper.models import Identifier, ScrapeResult
from app.zorgab_scraper.scraper import ZorgabScraper
from app.zorgab_scraper.services import IdentifierProvider, ZorgabScrapeExecutor


class TestZorgabScraper:
    def test_run_logs_summaries_for_not_found_and_errors(self, mocker: MockerFixture) -> None:
        identifier_provider = mocker.Mock()
        executor = mocker.Mock()
        logger = mocker.Mock()
        bundle_factory = mocker.Mock()
        scraper = ZorgabScraper(
            identifier_provider=identifier_provider,
            executor=executor,
            bundle_factory=bundle_factory,
        )
        identifier_provider.get_identifiers.return_value = [Identifier(IdentificationType.ura, "123")]
        executor.execute.return_value = ScrapeResult(bundles=[], not_found=["URA:123"], errors=["boom"])
        bundle_factory.create.return_value = Bundle(type="collection", entry=[])

        logger = mocker.patch("app.zorgab_scraper.scraper.logger")

        identifier_sources = [IdentifierSource.zakl_xml]
        result = scraper.run(scrape_limit=5, workers=0, identifier_sources=identifier_sources)

        assert result == bundle_factory.create.return_value
        identifier_provider.get_identifiers.assert_called_once_with(identifier_sources=identifier_sources, limit=5)
        executor.execute.assert_called_once_with(
            identifiers=identifier_provider.get_identifiers.return_value, workers=1
        )
        bundle_factory.create.assert_called_once_with(executor.execute.return_value)
        logger.info.assert_any_call(
            "Successfully scraped %d bundles for %d identifiers, from which: %d not found and %d errors",
            0,  # bundles
            1,  # identifiers
            1,  # not found
            1,  # errors
        )
        logger.debug.assert_any_call("Summary of not found organizations: %s", "URA:123")
        logger.warning.assert_called_once_with("Summary of errors: %s", "boom")

    def test_run_logs_success_without_not_found_or_errors(self, mocker: MockerFixture) -> None:
        identifier_provider = mocker.Mock()
        executor = mocker.Mock()

        logger = mocker.patch("app.zorgab_scraper.scraper.logger")

        bundle_factory = mocker.Mock()
        scraper = ZorgabScraper(
            identifier_provider=identifier_provider,
            executor=executor,
            bundle_factory=bundle_factory,
        )
        identifier_provider.get_identifiers.return_value = [Identifier(IdentificationType.ura, "123")]
        executor.execute.return_value = ScrapeResult(bundles=[], not_found=[], errors=[])
        bundle_factory.create.return_value = Bundle(type="collection", entry=[])

        identifier_sources = [IdentifierSource.zakl_xml]
        result = scraper.run(scrape_limit=5, workers=1, identifier_sources=identifier_sources)

        assert result == bundle_factory.create.return_value
        identifier_provider.get_identifiers.assert_called_once_with(identifier_sources=identifier_sources, limit=5)
        bundle_factory.create.assert_called_once_with(executor.execute.return_value)

        logger.info.assert_any_call(
            "Successfully scraped %d bundles for %d identifiers, from which: %d not found and %d errors",
            0,  # bundles
            1,  # identifiers
            0,  # not found
            0,  # errors
        )

        logger.warning.assert_not_called()

    def test_scraper_logs_when_it_starts_scraping_without_scrape_limit(self, mocker: MockerFixture) -> None:
        identifier_provider = mocker.Mock(spec=IdentifierProvider)
        identifier_provider.get_identifiers.return_value = [Identifier(IdentificationType.ura, "123")]

        executor = mocker.Mock(spec=ZorgabScrapeExecutor)
        executor.execute.return_value = ScrapeResult(bundles=[], not_found=[], errors=[])

        bundle = Bundle(type="collection", entry=[])
        bundle_factory = mocker.Mock()
        bundle_factory.create.return_value = bundle

        logger = mocker.patch("app.zorgab_scraper.scraper.logger")

        scraper = ZorgabScraper(
            identifier_provider=identifier_provider,
            executor=executor,
            bundle_factory=bundle_factory,
        )
        actual_bundle = scraper.run(scrape_limit=None, workers=1, identifier_sources=list(IdentifierSource))
        assert actual_bundle is bundle

        logger.info.assert_any_call("No scrape limit configured; scraping full dataset")
