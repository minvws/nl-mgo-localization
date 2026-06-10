from fastapi import APIRouter, Response

from app.constants import APP_NAME

router = APIRouter()


@router.get("/")
def get_service_name() -> Response:
    return Response(APP_NAME)
