from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter

from sigil.presentation.routers.v1.captchas.views import solve_slide_captcha

captchas_router = APIRouter(
    prefix="/captchas",
    tags=["captchas"],
    route_class=DishkaRoute,
)

captchas_router.add_api_route(
    path="/slide",
    methods=["POST"],
    endpoint=solve_slide_captcha,
)
