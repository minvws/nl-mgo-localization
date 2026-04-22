import json
from logging import getLogger
from pathlib import Path

import pytest
from fhir.resources.STU3.bundle import Bundle, BundleEntry
from fhir.resources.STU3.organization import Organization as FhirOrganization
from pytest import LogCaptureFixture
from pytest_mock import MockerFixture

from app.addressing.models import IdentificationType
from app.fhir_uris import FHIR_NAMINGSYSTEM_AGB_Z, FHIR_NAMINGSYSTEM_URA
from app.zorgab_scraper.factories import OrganizationDeduplicator, SearchRequestFactory, ZorgabBundleFactory
from app.zorgab_scraper.models import Identifier, ScrapeResult


class TestZorgabBundleFactory:
    def test_bundle_factory_skips_empty_bundle_entries(self, mocker: MockerFixture) -> None:
        logger = mocker.Mock()
        factory = ZorgabBundleFactory(logger, OrganizationDeduplicator(logger))
        result = ScrapeResult(bundles=[Bundle(type="collection", entry=[])], not_found=[], errors=[])

        bundle = factory.create(result)

        assert bundle.entry == []
        logger.warning.assert_not_called()

    def test_bundle_factory_skips_entries_without_deduplication_key(self, mocker: MockerFixture) -> None:
        logger = mocker.Mock()
        factory = ZorgabBundleFactory(logger, OrganizationDeduplicator(logger))
        bundle = Bundle(
            type="collection",
            entry=[BundleEntry(resource=FhirOrganization(name="No ID"))],
        )
        result = ScrapeResult(bundles=[bundle], not_found=[], errors=[])

        bundle = factory.create(result)

        assert bundle.entry == []
        logger.warning.assert_not_called()

    def test_bundle_factory_logs_unknown_entry_type(self, mocker: MockerFixture) -> None:
        logger = mocker.Mock()
        factory = ZorgabBundleFactory(logger, OrganizationDeduplicator(logger))
        # model_construct bypasses FHIR validation so we can simulate a corrupted entry type.
        invalid_bundle = Bundle.model_construct(type="collection", entry=[object()])  # type: ignore[list-item]
        result = ScrapeResult(bundles=[invalid_bundle], not_found=[], errors=[])

        bundle = factory.create(result)

        assert bundle.entry == []
        logger.warning.assert_any_call("Unknown resource type for %s", object)

    def test_bundle_factory_logs_and_continues_on_exception(self, mocker: MockerFixture) -> None:
        logger = mocker.Mock()
        factory = ZorgabBundleFactory(logger, OrganizationDeduplicator(logger))

        bundle_entry = BundleEntry(
            fullUrl="https://example.com/Organization/org-1",
            resource=FhirOrganization(name="Test Org"),
        )

        bundle = Bundle(type="collection", entry=[bundle_entry])
        result = ScrapeResult(bundles=[bundle], not_found=[], errors=[])

        mocker.patch(
            "app.zorgab_scraper.factories.FhirOrganization.model_validate",
            side_effect=ValueError("Invalid organization data"),
        )

        bundle = factory.create(result)

        assert bundle.entry == []
        logger.warning.assert_any_call(
            "Failed to process organization %s: %s",
            "https://example.com/Organization/org-1",
            mocker.ANY,
        )

    def test_bundle_factory_deduplicates_by_id(self, mocker: MockerFixture) -> None:
        logger = mocker.Mock()
        factory = ZorgabBundleFactory(logger, OrganizationDeduplicator(logger))

        bundle = Bundle(
            type="collection",
            entry=[
                BundleEntry(
                    fullUrl="https://example.com/Organization/org-1",
                    resource=FhirOrganization(id="org-1", name="Org 1"),
                ),
                BundleEntry(
                    fullUrl="https://example.com/Organization/org-1-duplicate",
                    resource=FhirOrganization(id="org-1", name="Org 1 Duplicate"),
                ),
            ],
        )
        result = ScrapeResult(bundles=[bundle], not_found=[], errors=[])

        bundle = factory.create(result)

        assert bundle.total == 1
        entries = bundle.entry or []
        assert len(entries) == 1
        resource = entries[0].resource
        assert isinstance(resource, FhirOrganization)
        assert resource.id == "org-1"
        logger.warning.assert_not_called()

    @pytest.mark.parametrize(
        ("fixture_name", "expected_total", "expected_ids", "expected_log_keys"),
        [
            (
                "deduplication_bundle_agb_snapshot.json",
                2,
                ["fhir-123", "fhir-125"],
                ["agb:01057739"],
            ),
            (
                "deduplication_bundle_ura_snapshot.json",
                2,
                ["fhir-201", "fhir-203"],
                ["ura:00010001"],
            ),
            (
                "deduplication_bundle_mixed_snapshot.json",
                2,
                ["fhir-301", "fhir-304"],
                ["agb:02000001", "ura:00020001"],
            ),
        ],
    )
    def test_bundle_factory_deduplicates_by_normalized_identifier(
        self,
        caplog: LogCaptureFixture,
        fixture_name: str,
        expected_total: int,
        expected_ids: list[str],
        expected_log_keys: list[str],
    ) -> None:
        """
        Test that organizations with duplicate AGB/URA identifiers are deduplicated at the scraper level.

        Simulates ScrapeResult with same organization twice,
        potentially with different FHIR IDs but same identifying attribute (AGB/URA).
        Factory should keep first occurrence only.
        """

        logger = getLogger("app.zorgab_scraper.factories")
        factory = ZorgabBundleFactory(logger, OrganizationDeduplicator(logger))

        fixture_path = Path(__file__).parent / "fixtures" / fixture_name
        bundle = Bundle.model_validate(json.loads(fixture_path.read_text(encoding="utf-8")))
        result = ScrapeResult(bundles=[bundle], not_found=[], errors=[])

        with caplog.at_level("DEBUG", logger="app.zorgab_scraper.factories"):
            deduplicated_bundle = factory.create(result)

        assert deduplicated_bundle.total == expected_total
        deduplicated_entries = deduplicated_bundle.entry

        assert deduplicated_entries is not None
        assert len(deduplicated_entries) == expected_total

        actual_returned_ids: list[str] = []

        for entry in deduplicated_entries:
            resource = entry.resource
            assert isinstance(resource, FhirOrganization)
            assert resource.id is not None
            actual_returned_ids.append(resource.id)

        assert actual_returned_ids == expected_ids

        for expected_log_key in expected_log_keys:
            assert any(
                "Skipping duplicate organization with normalized ID" in record.message
                and expected_log_key in record.message
                for record in caplog.records
            )

    def test_bundle_factory_remembers_both_agb_and_ura_across_duplicate_paths(self, caplog: LogCaptureFixture) -> None:
        logger = getLogger("app.zorgab_scraper.factories")
        factory = ZorgabBundleFactory(logger, OrganizationDeduplicator(logger))

        bundle = Bundle(
            type="collection",
            entry=[
                BundleEntry(
                    fullUrl="https://example.com/Organization/org-a",
                    resource=FhirOrganization.model_validate(
                        {
                            "resourceType": "Organization",
                            "id": "fhir-a",
                            "name": "Org A",
                            "identifier": [
                                {
                                    "system": FHIR_NAMINGSYSTEM_AGB_Z,
                                    "value": "01000001",
                                }
                            ],
                        }
                    ),
                ),
                BundleEntry(
                    fullUrl="https://example.com/Organization/org-a-duplicate",
                    resource=FhirOrganization.model_validate(
                        {
                            "resourceType": "Organization",
                            "id": "fhir-a-dup",
                            "name": "Org A duplicate",
                            "identifier": [
                                {
                                    "system": FHIR_NAMINGSYSTEM_AGB_Z,
                                    "value": "01000001",
                                },
                                {
                                    "system": FHIR_NAMINGSYSTEM_URA,
                                    "value": "00000001",
                                },
                            ],
                        }
                    ),
                ),
                BundleEntry(
                    fullUrl="https://example.com/Organization/org-a-via-ura",
                    resource=FhirOrganization.model_validate(
                        {
                            "resourceType": "Organization",
                            "id": "fhir-a-via-ura",
                            "name": "Org A via URA",
                            "identifier": [
                                {
                                    "system": FHIR_NAMINGSYSTEM_URA,
                                    "value": "00000001",
                                }
                            ],
                        }
                    ),
                ),
            ],
        )
        result = ScrapeResult(bundles=[bundle], not_found=[], errors=[])

        with caplog.at_level("DEBUG", logger="app.zorgab_scraper.factories"):
            merged_bundle = factory.create(result)

        entries = merged_bundle.entry or []
        assert merged_bundle.total == 1
        assert len(entries) == 1

        resource = entries[0].resource
        assert isinstance(resource, FhirOrganization)
        assert resource.id == "fhir-a"

        assert any("agb:01000001" in record.message for record in caplog.records)
        assert any("ura:00000001" in record.message for record in caplog.records)


class TestSearchRequestFactory:
    def test_create_for_ura_identifier(self) -> None:
        identifier = Identifier(type=IdentificationType.ura, value="123456789")
        search_request = SearchRequestFactory.create_for_identifier(identifier)

        assert search_request is not None
        assert search_request.ura == "123456789"
        assert search_request.agb is None

    def test_create_for_agbz_identifier(self) -> None:
        identifier = Identifier(type=IdentificationType.agbz, value="987654321")
        search_request = SearchRequestFactory.create_for_identifier(identifier)

        assert search_request is not None
        assert search_request.agb == "987654321"
        assert search_request.ura is None

    def test_create_for_non_agb_or_ura_identifier_returns_none(self) -> None:
        identifier = Identifier(type=IdentificationType.kvk, value="555555555")
        search_request = SearchRequestFactory.create_for_identifier(identifier)

        assert search_request is None


class TestOrganizationDeduplicator:
    def test_should_include_ignores_invalid_identifier_payload_items(self, mocker: MockerFixture) -> None:
        logger = mocker.Mock()
        deduplicator = OrganizationDeduplicator(logger)
        invalid_identifier = object()

        organization_with_invalid_identifier_item = FhirOrganization.model_construct(
            id="dedup-org-1",
            identifier=[invalid_identifier],  # type: ignore[list-item]
        )
        bundle_entry = BundleEntry(
            fullUrl="https://example.com/Organization/dedup-org-1",
            resource=FhirOrganization(id="dedup-org-1", name="Organization 1"),
        )

        assert deduplicator.should_include(organization_with_invalid_identifier_item, bundle_entry) is True
        logger.warning.assert_called_once_with(
            "Unknown identifier format for %s: %s",
            "dedup-org-1",
            invalid_identifier,
        )
