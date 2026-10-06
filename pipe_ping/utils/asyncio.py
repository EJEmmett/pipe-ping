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
    """Await *fn*, running it in a worker thread if it is synchronous."""
    if inspect.iscoroutinefunction(fn):
        return await fn(*args, **kwargs)

    return await asyncio.to_thread(fn, *args, **kwargs)
