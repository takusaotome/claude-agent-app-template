"""Persistent event loop bridge for Claude Agent SDK.

The SDK retains internal anyio task groups tied to the event loop
created during connect().  A new loop per call (asyncio.run / new_event_loop
+ close) breaks that invariant because the SDK's tasks reference the
destroyed loop.

This module keeps a single event loop alive across Streamlit reruns.
Coroutines are dispatched via run_until_complete() on the main thread,
which keeps the Streamlit ScriptRunContext available for UI updates.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Coroutine
from typing import Any, TypeVar

import nest_asyncio

nest_asyncio.apply()

logger = logging.getLogger(__name__)

T = TypeVar("T")


class AsyncBridge:
    """Reusable event loop that survives across Streamlit reruns."""

    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        logger.info("AsyncBridge: new event loop created")

    def run(self, coro: Coroutine[Any, Any, T], timeout: float = 300) -> T:
        """Run a coroutine on the persistent loop (blocks the calling thread)."""
        if self._loop.is_closed():
            self._loop = asyncio.new_event_loop()
            logger.info("AsyncBridge: recreated closed event loop")
        asyncio.set_event_loop(self._loop)
        return self._loop.run_until_complete(coro)

    @property
    def is_alive(self) -> bool:
        return not self._loop.is_closed()

    def shutdown(self) -> None:
        """Cancel pending tasks and close the loop."""
        if self._loop.is_closed():
            return
        try:
            if not self._loop.is_running():
                pending = asyncio.all_tasks(self._loop)
                for task in pending:
                    task.cancel()
                if pending:
                    self._loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        except Exception:
            pass
        try:
            if not self._loop.is_running():
                self._loop.close()
        except Exception:
            pass
        logger.info("AsyncBridge: event loop shut down")
