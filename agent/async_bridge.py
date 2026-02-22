"""Persistent event-loop bridge for Streamlit + Claude SDK."""

from __future__ import annotations

import asyncio


class AsyncBridge:
    """Reusable event loop that survives Streamlit reruns."""

    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()

    def run(self, coro, timeout: float = 300):
        if self._loop.is_closed():
            raise RuntimeError("AsyncBridge loop is closed")
        asyncio.set_event_loop(self._loop)
        return self._loop.run_until_complete(asyncio.wait_for(coro, timeout=timeout))

    def shutdown(self) -> None:
        if self._loop.is_closed():
            return
        try:
            if not self._loop.is_running():
                pending = asyncio.all_tasks(self._loop)
                for task in pending:
                    task.cancel()
                if pending:
                    self._loop.run_until_complete(
                        asyncio.gather(*pending, return_exceptions=True)
                    )
                self._loop.close()
        except Exception:
            pass
