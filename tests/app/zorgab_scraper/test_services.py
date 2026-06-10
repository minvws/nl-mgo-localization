from fhir.resources.STU3.organization import Organization as FhirOrganization
from pytest_mock import MockerFixture

from app.zorgab_scraper.models import OrganizationBundleEntry
from app.zorgab_scraper.services import OrganizationDeduplicator


class TestOrganizationDeduplicator:
    def test_should_include_ignores_invalid_identifier_payload_items(self, mocker: MockerFixture) -> None:
        logger = mocker.patch("app.zorgab_scraper.services.logger")
        deduplicator = OrganizationDeduplicator()
        invalid_identifier = object()

        organization = FhirOrganization.model_construct(
            id="dedup-org-1",
            identifier=[invalid_identifier],  # type: ignore[list-item]
        )
        bundle_entry = OrganizationBundleEntry(
            full_url="https://example.com/Organization/dedup-org-1",
            resource=organization,
        )

        assert deduplicator.should_include(bundle_entry) is True
        logger.warning.assert_called_once_with(
            "Unknown identifier format for %s: %s",
            "dedup-org-1",
            invalid_identifier,
        )
