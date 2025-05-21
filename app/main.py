from typing import Any

import inject
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.bindings import configure_bindings
from app.config.factories import get_config
from app.constants import APP_NAME
from app.demo.routers import router as demo_router
from app.docs.routers import router as docs_router
from app.path import project_root
from app.routers.default import router as default_router
from app.routers.health import router as health_router
from app.routers.location import router as location_router
from app.version.models import VersionInfo


def get_uvicorn_params() -> dict[str, Any]:
    config = get_config(config_file="app.conf")
    kwargs = {
        "host": config.uvicorn.host,
        "port": config.uvicorn.port,
        "reload": config.uvicorn.reload,
    }
    if config.uvicorn.use_ssl:
        ssl_keyfile = (
            config.uvicorn.ssl_base_dir + "/" + config.uvicorn.ssl_key_file
            if config.uvicorn.ssl_base_dir and config.uvicorn.ssl_key_file
            else None
        )
        ssl_certfile = (
            config.uvicorn.ssl_base_dir + "/" + config.uvicorn.ssl_cert_file
            if config.uvicorn.ssl_base_dir and config.uvicorn.ssl_cert_file
            else None
        )

        if ssl_keyfile:
            kwargs["ssl_keyfile"] = ssl_keyfile
        if ssl_certfile:
            kwargs["ssl_certfile"] = ssl_certfile

    return kwargs


def create_app() -> None:
    uvicorn.run("app.main:create_fastapi_app", **get_uvicorn_params())


def create_fastapi_app() -> FastAPI:
    if not inject.is_configured():
        config = get_config(config_file="app.conf")
        inject.configure(lambda binder: configure_bindings(binder=binder, config=config))

    version_info: VersionInfo = inject.instance(VersionInfo)

    app = FastAPI(
        title=APP_NAME,
        docs_url=None,
        redoc_url=None,
        version=version_info.version,
    )

    app.mount("/static", StaticFiles(directory=project_root("static")), name="static")

    routers = [
        demo_router,
        default_router,
        health_router,
        location_router,
        docs_router,
    ]

    for router in routers:
        app.include_router(router)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app


if __name__ == "__main__":
    create_app()
