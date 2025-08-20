from dishka import AsyncContainer, make_async_container

from sigil.core.config.settings import Settings
from sigil.core.providers.configs import ConfigsProvider
from sigil.core.providers.services import ServicesProvider


def make_container(settings: Settings) -> AsyncContainer:
    container = make_async_container(
        ConfigsProvider(settings=settings),
        ServicesProvider(),
    )

    return container
