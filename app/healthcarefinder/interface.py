from typing import Protocol

from fhir.resources.STU3.bundle import Bundle

from app.healthcarefinder.models import SearchRequest, SearchResponse


class HealthcareFinderAdapter(Protocol):
    def search_organizations(self, search: SearchRequest) -> SearchResponse | None: ...
    def search_organizations_raw_fhir(self, search: SearchRequest) -> Bundle | None: ...
