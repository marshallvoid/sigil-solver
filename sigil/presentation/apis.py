from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from scalar_fastapi import get_scalar_api_reference
from starlette.responses import HTMLResponse

from sigil.presentation.routers.v1.captchas.routers import captchas_router

root_router = APIRouter()


@root_router.get("/")
async def root() -> JSONResponse:
    return JSONResponse(content={"success": True, "msg": "running"})


@root_router.get("/health")
async def health() -> JSONResponse:
    return JSONResponse(content={"status": "ok"})


@root_router.get("/scalar", include_in_schema=False)
async def scalar_html(request: Request) -> HTMLResponse:
    return get_scalar_api_reference(openapi_url=request.app.openapi_url, title=request.app.title)


api_v1_router = APIRouter(prefix="/api/v1", route_class=DishkaRoute)

api_v1_router.include_router(router=captchas_router)
