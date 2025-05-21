from typing import Any, Dict

from fastapi import APIRouter

from app.db.db import Database
from app.healthcarefinder.interface import HealthcareFinderAdapter
from app.healthcarefinder.zorgab.zorgab import ZorgABAdapter
from app.utils import resolve_instance

router = APIRouter()


@router.get(
    "/health",
    summary="Check the health of the application",
)
def health(
    db: Database = resolve_instance(Database),
    healthcare_finder_adapter: HealthcareFinderAdapter = resolve_instance(HealthcareFinderAdapter),
) -> dict[str, Any]:
    response: Dict[str, Any] = {
        "healthy": True,
        "externals": {
            "database": db.is_healthy(),
        },
    }

    if isinstance(healthcare_finder_adapter, ZorgABAdapter):
        zorgab_health = healthcare_finder_adapter.verify_connection()
        response["externals"]["zorgab"] = zorgab_health

    for health_status in response["externals"].values():
        if not health_status:
            response["healthy"] = False
            break

    return response
