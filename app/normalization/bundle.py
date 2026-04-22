import logging
from typing import Callable

import inject
from fhir.resources.STU3.bundle import Bundle
from fhir.resources.STU3.organization import Organization

from app.normalization.bundle_iterator import BundleIterator
from app.normalization.models import NormalizedOrganization
from app.normalization.organization_normalizer import OrganizationNormalizer

logger = logging.getLogger(__name__)


class BundleNormalizer:
    @inject.autoparams("organization_normalizer")
    def __init__(self, organization_normalizer: OrganizationNormalizer) -> None:
        self.__organization_normalizer = organization_normalizer

    def normalize(
        self,
        bundle: Bundle,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> list[NormalizedOrganization]:
        """Normalize all organization resources in a FHIR bundle.

        Iterates through the bundle, filters out non-organization resources,
        normalizes each organization, and optionally reports progress.

        Args:
            bundle: The FHIR bundle to normalize.
            progress_callback: Optional function called with (processed, total) counts.

        Returns:
            A list of normalized organization dictionaries ready to use as search index in Orama.
        """
        bundle_iterator = BundleIterator(bundle)

        results: list[NormalizedOrganization] = []
        processed_count = 0

        total_resources = bundle.total or bundle_iterator.count_resources()
        logger.info("Normalizing a bundle with %d resources...", total_resources)

        for resource in bundle_iterator.iterate_resources():
            if not isinstance(resource, Organization):
                logger.error("Skipped normalization of resource; resource is not an organisation")
                continue

            results.append(self.__organization_normalizer.normalize(resource))

            processed_count += 1
            if progress_callback:
                progress_callback(processed_count, total_resources)

        logger.info("Successfully normalized %s resources", total_resources)

        return results
