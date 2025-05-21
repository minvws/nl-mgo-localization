from fastapi import APIRouter, HTTPException

from app.healthcarefinder.healthcarefinder import HealthcareFinder
from app.healthcarefinder.models import SearchRequest, SearchResponse
from app.healthcarefinder.zorgab.hydration_service import HydrationError
from app.healthcarefinder.zorgab.zorgab import ApiError, BadSearchParams
from app.utils import resolve_instance

router = APIRouter()


@router.post(
    "/localization/organization/search",
    summary="Search for organizations based on the search parameters",
    tags=["localization"],
)
def read_item(
    search: SearchRequest,
    finder: HealthcareFinder = resolve_instance(HealthcareFinder),
) -> SearchResponse:
    """
    Returns a list of organizations based on the search parameters
    """
    try:
        organization_list = finder.search_organizations(search)
        if organization_list is None:
            raise HTTPException(status_code=404, detail="No organizations found")

    except BadSearchParams:
        raise HTTPException(status_code=400, detail="Bad search parameters") from BadSearchParams
    except ApiError:
        raise HTTPException(
            status_code=500,
            detail="Error while processing your request. Please try again later",
        ) from ApiError
    except HydrationError:
        raise HTTPException(status_code=500, detail="Error while processing your request") from HydrationError

    return organization_list
