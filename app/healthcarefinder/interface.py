from typing import Protocol

from app.healthcarefinder.models import SearchRequest, SearchResponse


class HealthcareFinderAdapter(Protocol):
    def search_organizations(self, search: SearchRequest) -> SearchResponse | None: ...
