import asyncio
import inspect
from typing import TYPE_CHECKING, Any, overload

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine


@overload
async def ensure_async_call[**P, RT](
    fn: "Callable[P, Coroutine[Any, Any, RT]]", *args: P.args, **kwargs: P.kwargs
) -> RT: ...


@overload
async def ensure_async_call[**P, RT](
    fn: "Callable[P, RT]", *args: P.args, **kwargs: P.kwargs
) -> RT: ...


async def ensure_async_call(fn: "Callable[..., Any]", *args: Any, **kwargs: Any) -> Any:
    """Call *fn* as a coroutine, or run it in a thread if it is synchronous, preventing it from blocking the event loop."""  # noqa: E501
    if inspect.iscoroutinefunction(fn):
        return await fn(*args, **kwargs)

    return await asyncio.to_thread(fn, *args, **kwargs)
