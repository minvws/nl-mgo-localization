import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

import inject
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.benchmark.router import router as benchmark_router
from app.bindings import configure_bindings
from app.config.factories import get_config
from app.config.models import Config
from app.constants import APP_NAME
from app.cron_tasks import CronCommands, CronTaskOrchestrator
from app.demo.routers import router as demo_router
from app.docs.routers import router as docs_router
from app.path import project_root
from app.routers.default import router as default_router
from app.routers.health import router as health_router
from app.routers.location import router as location_router
from app.version.models import VersionInfo

logger = logging.getLogger(__name__)


def get_uvicorn_config() -> dict[str, Any]:  # type: ignore[explicit-any]
    config = get_config(config_file="app.conf")
    uvicorn_kwargs = {
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
            uvicorn_kwargs["ssl_keyfile"] = ssl_keyfile
        if ssl_certfile:
            uvicorn_kwargs["ssl_certfile"] = ssl_certfile

    return uvicorn_kwargs


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    config = inject.instance(Config)
    cron_commands = CronCommands(config.app.on_startup_cron_commands)

    cron_task_orchestrator = inject.instance(CronTaskOrchestrator)
    cron_task_orchestrator.start(cron_commands.to_cron_tasks())

    app.state.cron_tasks = cron_task_orchestrator.orchestrated_tasks

    try:
        yield
    finally:
        await cron_task_orchestrator.stop()


def run_uvicorn() -> None:
    uvicorn.run("app.main:create_fastapi_app", **get_uvicorn_config())


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
        lifespan=lifespan,
    )

    app.mount("/static", StaticFiles(directory=project_root("static")), name="static")

    routers = [
        demo_router,
        default_router,
        health_router,
        location_router,
        docs_router,
        benchmark_router,
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
    run_uvicorn()
