from dishka import Provider, Scope, provide

from sigil.core.config.settings import Settings


class ConfigsProvider(Provider):
    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self._settings = settings

    @provide(scope=Scope.APP)
    def settings(self) -> Settings:
        return self._settings
