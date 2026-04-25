from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class PipePingSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PIPE_PING_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    poll_interval_seconds: int = 60


@lru_cache(maxsize=1)
def get_settings() -> PipePingSettings:
    return PipePingSettings()
