"""Unit tests for ClaudeChatAgent."""

from __future__ import annotations

import asyncio
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import agent.client as client_module


class FakeStreamEvent:
    def __init__(self, event: dict) -> None:
        self.event = event


class FakeTextBlock:
    def __init__(self, text: str) -> None:
        self.text = text


class FakeAssistantMessage:
    def __init__(self, content: list[FakeTextBlock]) -> None:
        self.content = content


class FakeResultMessage:
    def __init__(
        self,
        *,
        is_error: bool = False,
        result: str = "",
        subtype: str = "result_error",
        session_id: str = "session-1",
    ) -> None:
        self.is_error = is_error
        self.result = result
        self.subtype = subtype
        self.session_id = session_id


class FakeToolResultBlock:
    def __init__(
        self,
        *,
        content: str | list[dict] | None = None,
        is_error: bool | None = None,
    ) -> None:
        self.tool_use_id = "tool-1"
        self.content = content
        self.is_error = is_error


class FakeUserMessage:
    def __init__(self, content: list[FakeToolResultBlock]) -> None:
        self.content = content


class FakeSDKClient:
    response_scenarios: list[list[object]] = []
    connect_failures = 0
    query_failures = 0
    query_history: list[str] = []

    def __init__(self, options) -> None:
        del options  # Not needed in tests.
        if type(self).response_scenarios:
            self._responses = list(type(self).response_scenarios.pop(0))
        else:
            self._responses = []

    @classmethod
    def reset(cls) -> None:
        cls.response_scenarios = []
        cls.connect_failures = 0
        cls.query_failures = 0
        cls.query_history = []

    async def connect(self) -> None:
        if type(self).connect_failures > 0:
            type(self).connect_failures -= 1
            raise RuntimeError("connect failure")

    async def disconnect(self) -> None:
        return None

    async def query(self, user_message: str) -> None:
        type(self).query_history.append(user_message)
        if type(self).query_failures > 0:
            type(self).query_failures -= 1
            raise RuntimeError("query failure")

    async def receive_response(self):
        for response in self._responses:
            yield response


class ClaudeChatAgentTests(unittest.TestCase):
    """Covers streaming, retries, and fallback behavior."""

    def setUp(self) -> None:
        FakeSDKClient.reset()

    def _collect_chunks(
        self,
        agent: client_module.ClaudeChatAgent,
        message: str = "hello",
    ) -> list[client_module.StreamChunk]:
        async def _run() -> list[client_module.StreamChunk]:
            chunks: list[client_module.StreamChunk] = []
            async for chunk in agent.send_message_streaming(message):
                chunks.append(chunk)
            return chunks

        return asyncio.run(_run())

    def _patch_dependencies(self):
        return patch.multiple(
            client_module,
            ClaudeSDKClient=FakeSDKClient,
            StreamEvent=FakeStreamEvent,
            AssistantMessage=FakeAssistantMessage,
            TextBlock=FakeTextBlock,
            ResultMessage=FakeResultMessage,
            UserMessage=FakeUserMessage,
            ToolResultBlock=FakeToolResultBlock,
        )

    def test_prefers_text_deltas_over_final_assistant_message(self) -> None:
        FakeSDKClient.response_scenarios = [
            [
                FakeStreamEvent(
                    {
                        "type": "content_block_delta",
                        "delta": {"type": "text_delta", "text": "Hel"},
                    }
                ),
                FakeStreamEvent(
                    {
                        "type": "content_block_delta",
                        "delta": {"type": "text_delta", "text": "lo"},
                    }
                ),
                FakeAssistantMessage([FakeTextBlock("Hello")]),
                FakeResultMessage(session_id="sid-1"),
            ]
        ]

        with self._patch_dependencies():
            agent = client_module.ClaudeChatAgent(
                project_root=Path("."),
                max_retries=0,
                retry_backoff_seconds=0,
            )
            chunks = self._collect_chunks(agent)

        self.assertEqual(
            chunks,
            [
                {"type": "text_delta", "content": "Hel"},
                {"type": "text_delta", "content": "lo"},
                {"type": "done", "content": "sid-1"},
            ],
        )

    def test_uses_assistant_text_when_no_deltas_present(self) -> None:
        FakeSDKClient.response_scenarios = [
            [FakeAssistantMessage([FakeTextBlock("Hello")]), FakeResultMessage(session_id="sid-2")]
        ]

        with self._patch_dependencies():
            agent = client_module.ClaudeChatAgent(
                project_root=Path("."),
                max_retries=0,
                retry_backoff_seconds=0,
            )
            chunks = self._collect_chunks(agent)

        self.assertEqual(
            chunks,
            [
                {"type": "text", "content": "Hello"},
                {"type": "done", "content": "sid-2"},
            ],
        )

    def test_retries_after_transient_query_failure(self) -> None:
        FakeSDKClient.query_failures = 1
        FakeSDKClient.response_scenarios = [
            [],
            [FakeAssistantMessage([FakeTextBlock("Recovered")]), FakeResultMessage()],
        ]

        with self._patch_dependencies():
            agent = client_module.ClaudeChatAgent(
                project_root=Path("."),
                max_retries=1,
                retry_backoff_seconds=0,
            )
            chunks = self._collect_chunks(agent)

        self.assertEqual(FakeSDKClient.query_history, ["hello", "hello"])
        self.assertEqual(
            chunks,
            [
                {"type": "text", "content": "Recovered"},
                {"type": "done", "content": "session-1"},
            ],
        )

    def test_returns_error_chunk_after_retry_exhaustion(self) -> None:
        FakeSDKClient.query_failures = 5
        FakeSDKClient.response_scenarios = [[], []]

        with self._patch_dependencies():
            agent = client_module.ClaudeChatAgent(
                project_root=Path("."),
                max_retries=1,
                retry_backoff_seconds=0,
            )
            chunks = self._collect_chunks(agent)

        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0]["type"], "error")
        self.assertIn("Request failed after 2 attempt(s).", chunks[0]["content"])

    def test_error_result_message_yields_error_chunk(self) -> None:
        FakeSDKClient.response_scenarios = [[FakeResultMessage(is_error=True, result="SDK Error")]]

        with self._patch_dependencies():
            agent = client_module.ClaudeChatAgent(
                project_root=Path("."),
                max_retries=0,
                retry_backoff_seconds=0,
            )
            chunks = self._collect_chunks(agent)

        self.assertEqual(
            chunks,
            [{"type": "error", "content": "SDK Error | subtype=result_error"}],
        )

    def test_error_result_without_result_includes_subtype(self) -> None:
        FakeSDKClient.response_scenarios = [
            [FakeResultMessage(is_error=True, result="", subtype="permission_denied")]
        ]

        with self._patch_dependencies():
            agent = client_module.ClaudeChatAgent(
                project_root=Path("."),
                max_retries=0,
                retry_backoff_seconds=0,
            )
            chunks = self._collect_chunks(agent)

        self.assertEqual(
            chunks,
            [{"type": "error", "content": "subtype=permission_denied"}],
        )

    def test_tool_result_error_detail_is_propagated_to_final_error(self) -> None:
        FakeSDKClient.response_scenarios = [
            [
                FakeUserMessage(
                    [
                        FakeToolResultBlock(
                            content="AxiosError: Request failed with status code 403",
                            is_error=True,
                        )
                    ]
                ),
                FakeResultMessage(is_error=True, result="", subtype="result_error"),
            ]
        ]

        with self._patch_dependencies():
            agent = client_module.ClaudeChatAgent(
                project_root=Path("."),
                max_retries=0,
                retry_backoff_seconds=0,
            )
            chunks = self._collect_chunks(agent)

        self.assertEqual(
            chunks,
            [
                {
                    "type": "tool_result",
                    "content": "error: AxiosError: Request failed with status code 403",
                },
                {
                    "type": "error",
                    "content": (
                        "subtype=result_error | "
                        "tool=AxiosError: Request failed with status code 403"
                    ),
                },
            ],
        )

    def test_require_client_raises_when_not_connected(self) -> None:
        with self._patch_dependencies():
            agent = client_module.ClaudeChatAgent(
                project_root=Path("."),
                max_retries=0,
            )

        with self.assertRaises(RuntimeError) as ctx:
            agent._require_client()
        self.assertIn("not connected", str(ctx.exception))

    def test_default_parameters_applied(self) -> None:
        with self._patch_dependencies():
            agent = client_module.ClaudeChatAgent(project_root=Path("."))

        self.assertEqual(agent.model, client_module.DEFAULT_MODEL)
        self.assertEqual(agent.permission_mode, client_module.DEFAULT_PERMISSION_MODE)
        self.assertEqual(agent.max_retries, client_module.DEFAULT_MAX_RETRIES)

    def test_negative_max_retries_clamped_to_zero(self) -> None:
        with self._patch_dependencies():
            agent = client_module.ClaudeChatAgent(
                project_root=Path("."),
                max_retries=-3,
            )

        self.assertEqual(agent.max_retries, 0)

    def test_disconnect_resets_state(self) -> None:
        FakeSDKClient.response_scenarios = [[FakeResultMessage(session_id="sid-x")]]

        with self._patch_dependencies():
            agent = client_module.ClaudeChatAgent(
                project_root=Path("."),
                max_retries=0,
                retry_backoff_seconds=0,
            )
            self._collect_chunks(agent)
            self.assertTrue(agent._connected)

            asyncio.run(agent.disconnect())
            self.assertFalse(agent._connected)
            self.assertIsNone(agent._client)

    def test_connect_is_idempotent(self) -> None:
        FakeSDKClient.response_scenarios = [[]]

        with self._patch_dependencies():
            agent = client_module.ClaudeChatAgent(
                project_root=Path("."),
                max_retries=0,
                retry_backoff_seconds=0,
            )

            async def _run() -> None:
                await agent.connect()
                first_client = agent._client
                await agent.connect()
                self.assertIs(agent._client, first_client)

            asyncio.run(_run())

    def test_connect_failure_resets_state(self) -> None:
        FakeSDKClient.connect_failures = 1
        FakeSDKClient.response_scenarios = [[]]

        with self._patch_dependencies():
            agent = client_module.ClaudeChatAgent(
                project_root=Path("."),
                max_retries=0,
                retry_backoff_seconds=0,
            )

            async def _run() -> None:
                with self.assertRaises(RuntimeError):
                    await agent.connect()
                self.assertIsNone(agent._client)
                self.assertFalse(agent._connected)

            asyncio.run(_run())

    def test_build_options_respects_sdk_sandbox_flag(self) -> None:
        with patch.object(
            client_module,
            "ClaudeAgentOptions",
            side_effect=lambda **kwargs: SimpleNamespace(**kwargs),
        ):
            with patch.object(client_module, "SDK_SANDBOX_ENABLED", True):
                agent = client_module.ClaudeChatAgent(project_root=Path("."))
                options = agent._build_options()

        self.assertEqual(options.sandbox, {"enabled": True})

    def test_unknown_message_class_is_silently_skipped(self) -> None:
        """Messages of an unrecognized type are logged but not yielded."""

        class UnknownMessage:
            pass

        FakeSDKClient.response_scenarios = [
            [UnknownMessage(), FakeResultMessage(session_id="sid-u")]
        ]

        with self._patch_dependencies():
            agent = client_module.ClaudeChatAgent(
                project_root=Path("."),
                max_retries=0,
                retry_backoff_seconds=0,
            )
            chunks = self._collect_chunks(agent)

        self.assertEqual(
            chunks,
            [{"type": "done", "content": "sid-u"}],
        )

    def test_ignored_stream_event_types_produce_no_chunks(self) -> None:
        """StreamEvent types like 'ping' and 'message_start' are silently ignored."""
        FakeSDKClient.response_scenarios = [
            [
                FakeStreamEvent({"type": "ping"}),
                FakeStreamEvent({"type": "message_start"}),
                FakeStreamEvent({"type": "content_block_start"}),
                FakeStreamEvent({"type": "content_block_stop"}),
                FakeStreamEvent({"type": "message_delta"}),
                FakeStreamEvent({"type": "message_stop"}),
                FakeResultMessage(session_id="sid-i"),
            ]
        ]

        with self._patch_dependencies():
            agent = client_module.ClaudeChatAgent(
                project_root=Path("."),
                max_retries=0,
                retry_backoff_seconds=0,
            )
            chunks = self._collect_chunks(agent)

        self.assertEqual(
            chunks,
            [{"type": "done", "content": "sid-i"}],
        )
