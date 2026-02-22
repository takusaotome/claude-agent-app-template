"""Minimal Claude Agent SDK client wrapper for chat streaming."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
)
from claude_agent_sdk.types import StreamEvent

from config.settings import (
    DEFAULT_MODEL,
    DEFAULT_PERMISSION_MODE,
    MCP_CONFIG_PATH,
    SETTING_SOURCES,
)


class ClaudeChatAgent:
    """Stateful chat client for Streamlit sessions."""

    def __init__(
        self,
        project_root: Path,
        model: str | None = None,
        permission_mode: str | None = None,
    ) -> None:
        self.project_root = project_root
        self.model = model or DEFAULT_MODEL
        self.permission_mode = permission_mode or DEFAULT_PERMISSION_MODE
        self._client: ClaudeSDKClient | None = None
        self._connected = False

    def _build_options(self) -> ClaudeAgentOptions:
        mcp_config: dict | str = {}
        if MCP_CONFIG_PATH.exists():
            mcp_config = str(MCP_CONFIG_PATH)

        return ClaudeAgentOptions(
            model=self.model,
            permission_mode=self.permission_mode,
            cwd=str(self.project_root),
            setting_sources=SETTING_SOURCES,
            include_partial_messages=True,
            mcp_servers=mcp_config,
        )

    async def connect(self) -> None:
        if self._connected:
            return
        options = self._build_options()
        self._client = ClaudeSDKClient(options)
        await self._client.connect()
        self._connected = True

    async def disconnect(self) -> None:
        if self._client and self._connected:
            await self._client.disconnect()
        self._client = None
        self._connected = False

    async def send_message_streaming(self, user_message: str) -> AsyncIterator[dict]:
        if not self._client or not self._connected:
            await self.connect()

        assert self._client is not None
        await self._client.query(user_message)

        async for message in self._client.receive_response():
            if isinstance(message, StreamEvent):
                event = message.event
                if event.get("type") == "content_block_delta":
                    delta = event.get("delta", {})
                    if delta.get("type") == "text_delta":
                        text = delta.get("text", "")
                        if text:
                            yield {"type": "text_delta", "content": text}

            elif isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        yield {"type": "text", "content": block.text}

            elif isinstance(message, ResultMessage):
                if message.is_error:
                    yield {"type": "error", "content": message.result or "Unknown error"}
                else:
                    yield {"type": "done", "content": message.session_id}
