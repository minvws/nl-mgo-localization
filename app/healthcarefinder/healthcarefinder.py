import inject

from .interface import HealthcareFinderAdapter
from .mock.adapter import MockHealthcareFinderAdapter
from .models import SearchRequest, SearchResponse


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
        if self.__allow_search_bypass and self.__is_search_bypass_requested(search):
            return self.__mock_adapter.search_organizations(search=search)
        return self.__adapter.search_organizations(search=search)

    def __is_search_bypass_requested(self, search: SearchRequest) -> bool:
        name = search.name
        city = search.city

        if name is None or city is None:
            return False

        return name.lower() == "test" and city.lower() == "test"
