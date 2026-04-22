from dataclasses import dataclass

from app.normalization.models import NormalizedOrganization


@dataclass(slots=True)
class SearchIndex:
    entries: list[NormalizedOrganization]
