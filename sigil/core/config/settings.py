from functools import lru_cache
from typing import Optional, Tuple, Type

from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    DotEnvSettingsSource,
    EnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)


class BaseAISettings(BaseSettings):
    api_key: Optional[str] = None
    model: Optional[str] = None
    temperature: float = 0.8
    max_retries: int = 2


class OpenAISettings(BaseAISettings):
    model: str = "o3"


class AnthropicSettings(BaseAISettings):
    model: str = "claude-opus-4-1-20250805"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=True,
        str_to_upper=True,
        extra="ignore",
        env_file=".env",
        env_prefix="SIGIL_",
        env_file_encoding="utf-8",
    )

    secret_key: str = "secret_key"
    debug: bool = False

    openai_settings: OpenAISettings = Field(default_factory=OpenAISettings, alias="openai")
    anthropic_settings: AnthropicSettings = Field(default_factory=AnthropicSettings, alias="anthropic")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        source = [
            init_settings,
            file_secret_settings,
            EnvSettingsSource(settings_cls=settings_cls),
            DotEnvSettingsSource(settings_cls=settings_cls, env_file=".env"),
        ]

        return (*source,)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
