from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.constants import APP_NAME

router = APIRouter()


@router.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html() -> HTMLResponse:
    """
    Serves a custom Swagger UI page that is identical to the default FastAPI
    documentation page, with the exception that some inline JavaScript is moved
    to an external file to comply with the strict Content Security Policy header
    which is set on server level.

    """
    return HTMLResponse(
        content=f"""
    <!DOCTYPE html>
    <html>
    <head>
        <link type="text/css" rel="stylesheet" href="/static/swagger-ui.css">
        <title>{APP_NAME} - Swagger UI</title>
    </head>
    <body>
        <div id="swagger-ui"></div>
        <script src="/static/swagger-ui-bundle.js"></script>
        <script src="/static/swagger-init-custom.js"></script>
    </body>
    </html>
    """
    )
