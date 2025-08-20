from dishka import AsyncContainer

from sigil.core.config.settings import Settings
from sigil.main.api.factory import APIFactory


def run_api(settings: Settings, container: AsyncContainer, host: str = "0.0.0.0", port: int = 8000) -> None:
    factory = APIFactory(container=container, settings=settings)
    app = factory.make()
    factory.run(app=app, host=host, port=port)
