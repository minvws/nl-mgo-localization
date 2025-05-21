import inject

from app.healthcarefinder.interface import HealthcareFinderAdapter
from app.healthcarefinder.mock.adapter import MockHealthcareFinderAdapter
from app.healthcarefinder.models import SearchRequest, SearchResponse


class HealthcareFinder:
    @inject.autoparams()
    def __init__(
        self,
        adapter: HealthcareFinderAdapter,
        mock_adapter: MockHealthcareFinderAdapter,
        allow_search_bypass: bool,
    ) -> None:
        self.__adapter: HealthcareFinderAdapter = adapter
        self.__mock_adapter: MockHealthcareFinderAdapter = mock_adapter
        self.__allow_search_bypass = allow_search_bypass

    def search_organizations(self, search: SearchRequest) -> SearchResponse | None:
        if self.__allow_search_bypass and self.__is_search_bypass_requested(search=search):
            return self.__mock_adapter.search_organizations(search=search)

        return self.__adapter.search_organizations(search=search)

    def __is_search_bypass_requested(self, search: SearchRequest) -> bool:
        return search.name == "test" and search.city == "test"
