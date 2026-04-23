from functools import lru_cache
from typing import TYPE_CHECKING, Annotated

from pydantic import BeforeValidator
from pydantic_settings import BaseSettings, SettingsConfigDict

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import LiteralString


def _split_parser(
    sep: "LiteralString",
) -> "Callable[[str | object], list[str] | object]":
    def parse_split_string(v: str | object) -> list[str] | object:
        if isinstance(v, str):
            if not v:
                return None

            return [item.strip() for item in v.split(sep) if item.strip()]
        return v

    return parse_split_string


CommaSeparatedList = Annotated[list[str], BeforeValidator(_split_parser(","))]


class PipePingSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PIPE_PING_",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    watch_repos: CommaSeparatedList | None = None
    poll_interval_seconds: int = 60


@lru_cache(maxsize=1)
def get_settings() -> PipePingSettings:
    return PipePingSettings()
