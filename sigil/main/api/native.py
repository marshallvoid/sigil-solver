from sigil.core.config.settings import get_settings
from sigil.core.providers.factory import make_container
from sigil.main.api.factory import APIFactory

settings = get_settings()
container = make_container(settings=settings)
factory = APIFactory(container=container, settings=settings)
app = factory.make()


if __name__ == "__main__":
    factory.run(app=app, host="0.0.0.0", port=8000)
