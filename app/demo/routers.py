from fastapi import APIRouter

from app.demo.services import DemoHealthCareFinderAdapter
from app.healthcarefinder.healthcarefinder import HealthcareFinder
from app.healthcarefinder.models import SearchRequest, SearchResponse

router = APIRouter()


@router.post("/localization/organization/search-demo")
def demo_healthcare_providers() -> SearchResponse | None:
    healthcare_finder = HealthcareFinder(DemoHealthCareFinderAdapter())
    # actual values are not important here as we return a static set
    search_request = SearchRequest(city="Den Haag", name="Ziekenhuis de ziekenboeg")
    response: SearchResponse | None = healthcare_finder.search_organizations(search_request)
    return response
