"""Unit tests for AsyncBridge."""

from __future__ import annotations

import asyncio
import unittest

from agent.async_bridge import AsyncBridge


class AsyncBridgeTests(unittest.TestCase):
    """Behavior tests for the Streamlit async bridge."""

    def test_run_returns_coroutine_result(self) -> None:
        bridge = AsyncBridge()

        async def _hello() -> str:
            return "ok"

        try:
            self.assertEqual(bridge.run(_hello()), "ok")
        finally:
            bridge.shutdown()

    def test_run_times_out(self) -> None:
        bridge = AsyncBridge()

        async def _slow() -> None:
            await asyncio.sleep(0.05)

        try:
            with self.assertRaises(asyncio.TimeoutError):
                bridge.run(_slow(), timeout=0.001)
        finally:
            bridge.shutdown()

    def test_run_after_shutdown_raises_runtime_error(self) -> None:
        bridge = AsyncBridge()
        bridge.shutdown()

        async def _noop() -> None:
            return None

        coro = _noop()
        try:
            with self.assertRaises(RuntimeError):
                bridge.run(coro)
        finally:
            coro.close()

    def test_shutdown_is_idempotent(self) -> None:
        bridge = AsyncBridge()
        bridge.shutdown()
        # Second shutdown should not raise.
        bridge.shutdown()

    def test_run_preserves_return_type(self) -> None:
        bridge = AsyncBridge()

        async def _number() -> int:
            return 42

        try:
            result = bridge.run(_number())
            self.assertIsInstance(result, int)
            self.assertEqual(result, 42)
        finally:
            bridge.shutdown()

    def test_run_propagates_exception(self) -> None:
        bridge = AsyncBridge()

        async def _fail() -> None:
            raise ValueError("boom")

        try:
            with self.assertRaises(ValueError) as ctx:
                bridge.run(_fail())
            self.assertEqual(str(ctx.exception), "boom")
        finally:
            bridge.shutdown()

    def test_sequential_runs_on_same_bridge(self) -> None:
        bridge = AsyncBridge()

        async def _add(a: int, b: int) -> int:
            return a + b

        try:
            self.assertEqual(bridge.run(_add(1, 2)), 3)
            self.assertEqual(bridge.run(_add(10, 20)), 30)
        finally:
            bridge.shutdown()
