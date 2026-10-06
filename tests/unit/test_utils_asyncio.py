from pipe_ping.utils.asyncio import ensure_async_call


async def test_ensure_async_call_with_coroutine():
    async def async_fn(x: int) -> int:
        return x * 2

    result = await ensure_async_call(async_fn, 5)
    assert result == 10


async def test_ensure_async_call_with_sync_function():
    def sync_fn(x: int) -> int:
        return x * 2

    result = await ensure_async_call(sync_fn, 5)
    assert result == 10


async def test_ensure_async_call_async_kwargs():
    async def async_fn(x: int, multiplier: int = 1) -> int:
        return x * multiplier

    result = await ensure_async_call(async_fn, 5, multiplier=3)
    assert result == 15


async def test_ensure_async_call_sync_kwargs():
    def sync_fn(x: int, multiplier: int = 1) -> int:
        return x * multiplier

    result = await ensure_async_call(sync_fn, 5, multiplier=3)
    assert result == 15


async def test_ensure_async_call_returns_none():
    async def no_return() -> None:
        pass

    result = await ensure_async_call(no_return)
    assert result is None
