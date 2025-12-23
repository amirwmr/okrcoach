from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator

import psycopg
from django.conf import settings


class _AsyncConnectionWrapper:
    """
    Lightweight connection manager to provide an asyncpg-like acquire API
    without adding extra dependencies.
    """

    def __init__(self, dsn: str):
        self._dsn = dsn

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[psycopg.AsyncConnection]:
        conn = await psycopg.AsyncConnection.connect(self._dsn)
        try:
            yield conn
        finally:
            await conn.close()


_pool_lock = asyncio.Lock()
_pool: _AsyncConnectionWrapper | None = None


async def get_asyncpg_pool() -> _AsyncConnectionWrapper | None:
    """
    Lazily build a connection wrapper using ASYNC_DATABASE_URL.
    Returns None when async DB settings are not provided.
    """

    global _pool
    if _pool is not None:
        return _pool

    dsn = getattr(settings, "ASYNC_DATABASE_URL", None)
    if not dsn:
        return None

    async with _pool_lock:
        if _pool is None:
            _pool = _AsyncConnectionWrapper(dsn)
    return _pool
