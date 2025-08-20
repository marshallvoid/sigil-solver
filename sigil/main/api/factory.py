from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import uvicorn
from dishka import AsyncContainer
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from loguru import logger

from sigil.core.config.settings import Settings, get_settings
from sigil.core.logging import init_logger
from sigil.presentation.apis import api_v1_router, root_router
from sigil.presentation.exceptions import setup_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    init_logger(debug=app.debug)
    yield

    state = getattr(app, "state", None)
    if not state:
        return

    dishka_container = getattr(state, "dishka_container", None)
    if not dishka_container:
        return

    await dishka_container.close()
    logger.info("Dishka container closed")


class APIFactory:
    def __init__(self, container: AsyncContainer, settings: Optional[Settings] = None) -> None:
        self._settings = settings if settings else get_settings()
        self._container = container

    def make(self) -> FastAPI:
        app = FastAPI(
            lifespan=lifespan,
            title="Sigil Solver",
            description="Sigil Solver API",
            version="0.1.0",
            debug=self._settings.debug,
            swagger_ui_parameters={
                "defaultModelsExpandDepth": -1,
                "tagsSorter": "alpha",
                "displayRequestDuration": True,
            },
        )

        setup_dishka(container=self._container, app=app)
        setup_exception_handlers(app=app)

        app.include_router(router=root_router)
        app.include_router(router=api_v1_router)

        return app

    def run(self, app: FastAPI, host: str = "0.0.0.0", port: int = 8000) -> None:
        uvicorn.run(app=app, host=host, port=port)
