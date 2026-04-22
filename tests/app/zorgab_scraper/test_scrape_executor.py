import pytest
from fhir.resources.STU3.bundle import Bundle, BundleEntry
from fhir.resources.STU3.organization import Organization as FhirOrganization
from pytest_mock import MockerFixture

from app.addressing.models import IdentificationType
from app.zorgab_scraper.models import Identifier
from app.zorgab_scraper.services import ZorgabScrapeExecutor


class TestZorgabScrapeExecutor:
    def test_execute_returns_empty_result_when_no_identifiers(self, mocker: MockerFixture) -> None:
        adapter = mocker.Mock()
        executor = ZorgabScrapeExecutor(healthcare_finder=adapter)

        with pytest.raises(ValueError, match="No identifiers to scrape"):
            executor.execute(identifiers=[], workers=5)

        adapter.search_organizations_raw_fhir.assert_not_called()

    def test_execute_returns_payload_for_successful_response(self, mocker: MockerFixture) -> None:
        adapter = mocker.Mock()
        executor = ZorgabScrapeExecutor(healthcare_finder=adapter)
        identifiers = [Identifier(IdentificationType.ura, "123")]
        entry = BundleEntry(
            fullUrl="https://example.com/Organization/org-123",
            resource=FhirOrganization(id="org-123", name="Test Org"),
        )
        bundle = Bundle(type="collection", entry=[entry])
        adapter.search_organizations_raw_fhir.return_value = bundle

        result = executor.execute(identifiers=identifiers, workers=1)

        assert bundle in result.bundles
        assert result.not_found == []
        assert result.errors == []

    def test_execute_uses_agb_identifier_in_search_request(self, mocker: MockerFixture) -> None:
        adapter = mocker.Mock()
        executor = ZorgabScrapeExecutor(healthcare_finder=adapter)
        identifiers = [Identifier(IdentificationType.agbz, "456")]
        adapter.search_organizations_raw_fhir.return_value = None

        result = executor.execute(identifiers=identifiers, workers=1)

        search_request = adapter.search_organizations_raw_fhir.call_args.args[0]
        assert search_request.agb == "456"
        assert result.bundles == []
        assert result.not_found == ["AGB-Z:456"]

    def test_execute_records_not_found_when_response_missing(self, mocker: MockerFixture) -> None:
        adapter = mocker.Mock()
        logger = mocker.patch("app.zorgab_scraper.services.logger")

        executor = ZorgabScrapeExecutor(healthcare_finder=adapter)
        identifiers = [Identifier(IdentificationType.ura, "789")]

        adapter.search_organizations_raw_fhir.return_value = None

        result = executor.execute(identifiers=identifiers, workers=1)

        assert result.bundles == []
        assert result.not_found == ["URA:789"]
        assert result.errors == []
        logger.debug.assert_any_call("No organizations found for %s", "URA:789")

    def test_execute_records_errors_when_adapter_raises(self, mocker: MockerFixture) -> None:
        adapter = mocker.Mock()
        logger = mocker.patch("app.zorgab_scraper.services.logger")
        executor = ZorgabScrapeExecutor(healthcare_finder=adapter)
        identifiers = [Identifier(IdentificationType.ura, "999")]

        adapter.search_organizations_raw_fhir.side_effect = Exception("boom")

        result = executor.execute(identifiers=identifiers, workers=2)

        assert result.bundles == []
        assert result.not_found == []
        assert result.errors == ["URA:999: boom"]
        logger.exception.assert_called_once()

    def test_execute_logs_multiple_organizations_when_raw_fhir_has_multiple_entries(
        self, mocker: MockerFixture
    ) -> None:
        adapter = mocker.Mock()
        logger = mocker.patch("app.zorgab_scraper.services.logger")
        executor = ZorgabScrapeExecutor(healthcare_finder=adapter)
        identifiers = [Identifier(IdentificationType.ura, "123")]

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
        adapter.search_organizations_raw_fhir.return_value = bundle

        executor.execute(identifiers=identifiers, workers=1)

        logger.debug.assert_any_call("Multiple organizations returned for %s: %d", "URA:123", 2)

    def test_execute_does_not_log_multiple_when_single_result(self, mocker: MockerFixture) -> None:
        adapter = mocker.Mock()
        logger = mocker.patch("app.zorgab_scraper.services.logger")
        executor = ZorgabScrapeExecutor(healthcare_finder=adapter)
        identifiers = [Identifier(IdentificationType.ura, "555")]
        entry = BundleEntry(
            fullUrl="https://example.com/Organization/org1",
            resource=FhirOrganization(id="org1", name="One"),
        )
        bundle = Bundle(type="collection", entry=[entry])
        adapter.search_organizations_raw_fhir.return_value = bundle

        result = executor.execute(identifiers=identifiers, workers=1)

        assert bundle in result.bundles
        assert result.not_found == []
        assert result.errors == []
        assert not any("Multiple organizations" in str(call) for call in logger.debug.call_args_list)

    def test_execute_skips_unsupported_identifier_type(self, mocker: MockerFixture) -> None:
        adapter = mocker.Mock()
        executor = ZorgabScrapeExecutor(healthcare_finder=adapter)
        identifiers = [Identifier(IdentificationType.kvk, "kvk-1"), Identifier(IdentificationType.kvk, "kvk-2")]

        with pytest.raises(ValueError, match="No supported identifiers to scrape"):
            executor.execute(identifiers=identifiers, workers=2)

        adapter.search_organizations_raw_fhir.assert_not_called()
