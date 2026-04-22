from typing import Iterable

from fhir.resources.STU3.bundle import Bundle
from fhir.resources.STU3.fhirtypes import ResourceType


class BundleIterator:
    """Iterates over resources in a FHIR STU3 Bundle."""

    def __init__(self, bundle: Bundle) -> None:
        self.bundle = bundle

    def count_resources(self) -> int:
        return sum(1 for _ in self.iterate_resources())

    def iterate_resources(self) -> Iterable[ResourceType]:
        for entry in self.bundle.entry or []:
            if entry.resource is not None:
                yield entry.resource
