from dataclasses import dataclass

from fhir.resources.STU3.bundle import Bundle

from app.addressing.models import IdentificationType


@dataclass(frozen=True)
class Identifier:
    type: IdentificationType
    value: str

    def token(self) -> str:
        return f"{self.type.value}:{self.value}"


@dataclass
class ScrapeResult:
    bundles: list[Bundle]  # for each scraped organization, a single bundle is returned and we aggregate them here
    not_found: list[str]
    errors: list[str]
    filename: str | None = None
