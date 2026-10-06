from functools import lru_cache
from pathlib import Path

from platformdirs import user_data_dir, user_log_dir
from pydantic import BaseModel, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class StructuredLoggingSettings(BaseModel):
    path: str = str(Path(user_log_dir("pipe-ping")) / "pipe_ping.log")
    max_bytes: int = 10485760
    backup_count: int = 5


class GitHubSettings(BaseModel):
    token: SecretStr | None = None
    repos: list[str] = []
    api_url: str = "https://api.github.com"
    runs_per_repo: int = 20


class SqliteSettings(BaseModel):
    path: str = str(Path(user_data_dir("pipe-ping")) / "pipe_ping.db")


class PipePingSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PIPE_PING_",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    structured_logging: StructuredLoggingSettings = StructuredLoggingSettings()
    github: GitHubSettings = GitHubSettings()
    sqlite: SqliteSettings = SqliteSettings()


@lru_cache(maxsize=1)
def get_settings() -> PipePingSettings:
    return PipePingSettings()
