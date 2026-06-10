from collections.abc import Iterator
from dataclasses import dataclass

from fhir.resources.STU3.organization import Organization

from app.addressing.models import IdentificationType


@dataclass(frozen=True)
class OrganizationBundleEntry:
    full_url: str | None
    resource: Organization


@dataclass(frozen=True)
class Identifier:
    type: IdentificationType
    value: str

    def token(self) -> str:
        return f"{self.type.value}:{self.value}"


@dataclass
class ScrapeResult:
    bundle_entries: Iterator[OrganizationBundleEntry]
    not_found: list[str]
    errors: list[str]
    filename: str | None = None
