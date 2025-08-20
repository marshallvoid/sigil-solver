import typer

from sigil.core.async_typer import AsyncTyper
from sigil.core.config.settings import get_settings
from sigil.core.providers.factory import make_container
from sigil.main.api.app import run_api


class CLIFactory:
    def make(self) -> typer.Typer:
        settings = get_settings()
        container = make_container(settings=settings)

        app = AsyncTyper(
            rich_markup_mode="rich",
            context_settings={
                "obj": {
                    "container": container,
                    "settings": settings,
                },
            },
        )

        self.add_api_command(app=app)

        return app

    def add_api_command(self, app: AsyncTyper) -> None:
        @app.command(name="api")
        def api(
            ctx: typer.Context,
            host: str = typer.Option(
                "0.0.0.0",
                "--host",
                "-h",
                help="Host to run the API Sever",
            ),
            port: int = typer.Option(
                8000,
                "--port",
                "-p",
                help="Port to run the API Sever",
            ),
        ) -> None:
            """[green]Run[/green] api."""
            ctx_container = ctx.obj.get("container")
            ctx_settings = ctx.obj.get("settings")
            run_api(settings=ctx_settings, container=ctx_container, host=host, port=port)
