from dishka import make_container, Provider, provide, Scope

from recognizer import Recognizer


class RecognizerProvider(Provider):
    @provide(scope=Scope.APP)
    def get_recognizer(self) -> Recognizer:
        return Recognizer()
