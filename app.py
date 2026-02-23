"""Minimal Streamlit chat UI powered by Claude Agent SDK."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

import streamlit as st
from agent.async_bridge import AsyncBridge
from agent.client import ClaudeChatAgent
from agent.sanitizer import sanitize
from config.settings import (
    APP_ICON,
    APP_LOG_FORMAT,
    APP_LOG_LEVEL,
    APP_TITLE,
    PROJECT_ROOT,
    UI_LOCALE,
    get_auth_description,
    validate_runtime_environment,
)

logger = logging.getLogger(__name__)
_LOGGING_CONFIGURED = False


_TOOL_LABELS: dict[str, dict[str, str]] = {
    "en": {
        "Write": "Writing file",
        "Edit": "Editing file",
        "Read": "Reading file",
        "Bash": "Running command",
        "Grep": "Searching code",
        "Glob": "Finding files",
        "LS": "Listing directory",
        "WebFetch": "Fetching web content",
        "TodoRead": "Reading task list",
        "TodoWrite": "Updating task list",
    },
    "ja": {
        "Write": "ファイル書き込み",
        "Edit": "ファイル編集",
        "Read": "ファイル読み取り",
        "Bash": "コマンド実行",
        "Grep": "コード検索",
        "Glob": "ファイル探索",
        "LS": "ディレクトリ一覧",
        "WebFetch": "Web取得",
        "TodoRead": "タスク読込",
        "TodoWrite": "タスク更新",
    },
}

_TEXTS: dict[str, dict[str, str]] = {
    "en": {
        "sidebar_title": "Project Config",
        "sidebar_project": "Project: `{project}`",
        "sidebar_auth": "Auth: `{auth}`",
        "clear_chat": "Clear chat",
        "config_issue": "Configuration issue detected.",
        "prompt_placeholder": "Type your message...",
        "thinking": "Thinking...",
        "running_tool": "Running {label}...",
        "chat_error": (
            "Error: chat request failed. Check authentication and network settings. "
            "Details: {details}"
        ),
        "no_response": "(No response)",
    },
    "ja": {
        "sidebar_title": "プロジェクト設定",
        "sidebar_project": "プロジェクト: `{project}`",
        "sidebar_auth": "認証: `{auth}`",
        "clear_chat": "チャットをクリア",
        "config_issue": "設定エラーを検出しました。",
        "prompt_placeholder": "メッセージを入力...",
        "thinking": "考え中...",
        "running_tool": "{label} を実行中...",
        "chat_error": (
            "エラー: チャットリクエストに失敗しました。認証とネットワーク設定を確認してください。"
            " 詳細: {details}"
        ),
        "no_response": "(応答なし)",
    },
}

_CUSTOM_CSS = """
<style>
[data-testid="stChatMessage"] h1 { font-size: 1.4rem !important; }
[data-testid="stChatMessage"] h2 { font-size: 1.2rem !important; }
[data-testid="stChatMessage"] h3 { font-size: 1.05rem !important; }
[data-testid="stChatMessage"] p { margin-bottom: 0.4em !important; }
.stMainBlockContainer { padding-top: 1.5rem !important; }
[data-testid="stStatusWidget"] { display: none !important; }
</style>
"""

_IME_FIX_JS = """
<script>
(function() {
    var VERSION = 4;
    var doc = window.parent.document;
    if (doc._imeFixCleanup) doc._imeFixCleanup();
    if (doc._imeFixVersion === VERSION) return;
    doc._imeFixVersion = VERSION;

    var composing = false;
    var compositionStartedAt = 0;
    var lastComposedAt = 0;
    var JUST_COMPOSED_WINDOW_MS = 320;
    var COMPOSITION_STALE_MS = 5000;

    function nowMs() {
        return (window.performance && window.performance.now)
            ? window.performance.now() : Date.now();
    }
    function isChatInput(e) {
        return e.target && e.target.closest &&
               e.target.closest('[data-testid="stChatInput"]');
    }
    function onCompositionStart(e) {
        if (!isChatInput(e)) return;
        composing = true;
        compositionStartedAt = nowMs();
    }
    function onCompositionEnd(e) {
        if (!isChatInput(e)) return;
        var text = (typeof e.data === 'string') ? e.data : '';
        if (text.length > 0) { lastComposedAt = nowMs(); }
        composing = false;
    }
    function onFocusout(e) {
        if (!isChatInput(e)) return;
        composing = false;
    }
    function onKeydown(e) {
        if (e.key !== 'Enter' || e.shiftKey || !isChatInput(e)) return;
        var now = nowMs();
        if (composing && (now - compositionStartedAt) > COMPOSITION_STALE_MS) {
            composing = false;
        }
        var keyCode = e.keyCode || e.which || 0;
        var imeProcessKey = keyCode === 229 || e.key === 'Process';
        var recentlyComposed = (now - lastComposedAt) < JUST_COMPOSED_WINDOW_MS;
        if (imeProcessKey || composing || recentlyComposed) {
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation();
            if (recentlyComposed) { lastComposedAt = 0; }
        }
    }

    doc.addEventListener('compositionstart', onCompositionStart, true);
    doc.addEventListener('compositionend', onCompositionEnd, true);
    doc.addEventListener('focusout', onFocusout, true);
    doc.addEventListener('keydown', onKeydown, true);

    doc._imeFixCleanup = function() {
        doc.removeEventListener('compositionstart', onCompositionStart, true);
        doc.removeEventListener('compositionend', onCompositionEnd, true);
        doc.removeEventListener('focusout', onFocusout, true);
        doc.removeEventListener('keydown', onKeydown, true);
        composing = false;
        lastComposedAt = 0;
        delete doc._imeFixVersion;
    };
})();
</script>
"""


class _JsonFormatter(logging.Formatter):
    """Minimal JSON log formatter for production-friendly logs."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def _configure_logging() -> None:
    """Configure root logger once based on environment settings."""
    global _LOGGING_CONFIGURED
    root = logging.getLogger()
    if _LOGGING_CONFIGURED:
        return

    handler = logging.StreamHandler()
    if APP_LOG_FORMAT == "json":
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, APP_LOG_LEVEL, logging.INFO))
    _LOGGING_CONFIGURED = True


def _tool_status_label(tool_name: str) -> str:
    """Convert an SDK tool name to a user-friendly label."""
    short = tool_name.split("__")[-1] if "__" in tool_name else tool_name
    localized = _TOOL_LABELS.get(UI_LOCALE, _TOOL_LABELS["en"])
    return localized.get(short, short)


def _msg(key: str, **kwargs: Any) -> str:
    """Return a localized UI message."""
    localized = _TEXTS.get(UI_LOCALE, _TEXTS["en"])
    template = localized.get(key, _TEXTS["en"].get(key, key))
    return template.format(**kwargs)


def _apply_stream_chunk(final_text_parts: list[str], chunk: dict[str, str]) -> bool:
    """Append text/error chunks to the assistant response buffer."""
    ctype = chunk.get("type")
    content = chunk.get("content", "")
    if ctype in {"text_delta", "text"} and content:
        final_text_parts.append(content)
        return True
    if ctype == "error":
        final_text_parts.append(f"\n\nError: {content}")
        return True
    return False


def _initialize_session_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "bridge" not in st.session_state:
        st.session_state.bridge = AsyncBridge()
    if "agent" not in st.session_state:
        st.session_state.agent = ClaudeChatAgent(project_root=PROJECT_ROOT)


async def _stream_response(
    agent: ClaudeChatAgent,
    prompt: str,
    status_placeholder: Any,
    response_placeholder: Any,
) -> str:
    """Fetch and progressively render a single assistant response."""
    final_text_parts: list[str] = []

    async for chunk in agent.send_message_streaming(prompt):
        ctype = chunk.get("type")
        content = sanitize(chunk.get("content", ""))

        if _apply_stream_chunk(final_text_parts, {"type": ctype or "", "content": content}):
            status_placeholder.empty()
            response_placeholder.markdown(sanitize("".join(final_text_parts)) + " ▌")
        elif ctype == "tool_use":
            label = _tool_status_label(content)
            status_placeholder.status(_msg("running_tool", label=label), state="running")
        elif ctype == "tool_result":
            status_placeholder.status(_msg("thinking"), state="running")

    if not final_text_parts:
        final_text_parts.append(_msg("no_response"))

    status_placeholder.empty()
    return sanitize("".join(final_text_parts))


def _inject_static_assets() -> None:
    st.markdown(_CUSTOM_CSS, unsafe_allow_html=True)
    st.components.v1.html(_IME_FIX_JS, height=0)


def render_app() -> None:
    """Render the Streamlit chat app."""
    _configure_logging()
    st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout="wide")
    _inject_static_assets()
    _initialize_session_state()

    with st.sidebar:
        st.subheader(_msg("sidebar_title"))
        st.caption(_msg("sidebar_project", project=PROJECT_ROOT.name))
        st.caption(_msg("sidebar_auth", auth=get_auth_description()))
        if st.button(_msg("clear_chat"), use_container_width=True):
            st.session_state.messages = []
            st.rerun()

    runtime_errors = validate_runtime_environment()
    if runtime_errors:
        st.error(_msg("config_issue"))
        for error in runtime_errors:
            st.caption(error)

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input(_msg("prompt_placeholder"), disabled=bool(runtime_errors))
    if not prompt:
        return

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        status_placeholder = st.empty()
        response_placeholder = st.empty()
        status_placeholder.status(_msg("thinking"), state="running")

        try:
            response_text = st.session_state.bridge.run(
                _stream_response(
                    agent=st.session_state.agent,
                    prompt=prompt,
                    status_placeholder=status_placeholder,
                    response_placeholder=response_placeholder,
                )
            )
        except Exception as exc:
            logger.exception("Chat request failed")
            response_text = _msg("chat_error", details=exc)
        finally:
            status_placeholder.empty()

        response_placeholder.markdown(response_text)

    st.session_state.messages.append({"role": "assistant", "content": response_text})


if __name__ == "__main__":
    render_app()
