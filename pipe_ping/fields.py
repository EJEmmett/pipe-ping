from typing import TYPE_CHECKING, Annotated

from pydantic import BeforeValidator

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import LiteralString


def _split_parser(
    sep: "LiteralString",
) -> "Callable[[str | object], list[str] | object]":
    def parse_split_string(v: str | object) -> list[str] | object:
        if isinstance(v, str):
            if not v:
                return []

            return [item.strip() for item in v.split(sep) if item.strip()]
        return v

    return parse_split_string


CommaSeparatedList = Annotated[list[str], BeforeValidator(_split_parser(","))]
