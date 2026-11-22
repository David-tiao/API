from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator


class RequestGate:
    """Global concurrency and request-rate gate shared by HTTP and browser phases."""

    def __init__(self, max_concurrency: int = 8, max_rps: float = 20.0):
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._rate_lock = asyncio.Lock()
        self._interval = 1.0 / max(max_rps, 0.1)
        self._last_request = 0.0

    async def throttle(self) -> None:
        """Charge a redirect hop without acquiring a second concurrency slot."""
        async with self._rate_lock:
            now = time.monotonic()
            wait_for = self._interval - (now - self._last_request)
            if wait_for > 0:
                await asyncio.sleep(wait_for)
            self._last_request = time.monotonic()

    async def acquire(self) -> None:
        await self._semaphore.acquire()
        try:
            await self.throttle()
        except BaseException:
            self._semaphore.release()
            raise

    def release(self) -> None:
        self._semaphore.release()

    @asynccontextmanager
    async def slot(self) -> AsyncIterator[None]:
        await self.acquire()
        try:
            yield
        finally:
            self.release()
