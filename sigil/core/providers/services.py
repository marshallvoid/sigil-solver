from dishka import Provider, Scope, provide

from sigil.services.recognizer import RecognizerService


class ServicesProvider(Provider):
    @provide(scope=Scope.APP)
    def get_recognizer(self) -> RecognizerService:
        return RecognizerService()
