"""Minimal Streamlit chat UI powered by Claude Agent SDK."""

from __future__ import annotations

import logging
from typing import Any

import streamlit as st
from agent.async_bridge import AsyncBridge
from agent.client import ClaudeChatAgent
from agent.sanitizer import sanitize
from config.settings import (
    APP_ICON,
    APP_TITLE,
    CLAUDE_DIR,
    PROJECT_ROOT,
    get_auth_description,
    validate_runtime_environment,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


_TOOL_LABELS: dict[str, str] = {
    "Write": "ファイル作成中",
    "Edit": "ファイル編集中",
    "Read": "ファイル読み込み中",
    "Bash": "コマンド実行中",
    "Grep": "コード検索中",
    "Glob": "ファイル検索中",
    "LS": "ディレクトリ一覧取得中",
    "WebFetch": "Web取得中",
    "TodoRead": "タスク確認中",
    "TodoWrite": "タスク更新中",
}


def _tool_status_label(tool_name: str) -> str:
    """Convert an SDK tool name to a user-friendly Japanese label."""
    short = tool_name.split("__")[-1] if "__" in tool_name else tool_name
    return _TOOL_LABELS.get(short, short)


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
            response_placeholder.markdown(sanitize("".join(final_text_parts)) + " \u258c")

        elif ctype == "tool_use":
            label = _tool_status_label(content)
            status_placeholder.status(f"\U0001f527 {label}...", state="running")

        elif ctype == "tool_result":
            status_placeholder.status("\u2705 完了", state="complete")

    if not final_text_parts:
        final_text_parts.append("(No response)")

    status_placeholder.empty()
    return sanitize("".join(final_text_parts))


st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout="wide")

# --- Custom CSS ---
_CUSTOM_CSS = """
<style>
[data-testid="stChatMessage"] h1 { font-size: 1.4rem !important; }
[data-testid="stChatMessage"] h2 { font-size: 1.2rem !important; }
[data-testid="stChatMessage"] h3 { font-size: 1.05rem !important; }
[data-testid="stChatMessage"] p { margin-bottom: 0.4em !important; }
/* Reduce top padding for cleaner initial look */
.stMainBlockContainer { padding-top: 1.5rem !important; }
</style>
"""
st.markdown(_CUSTOM_CSS, unsafe_allow_html=True)

# --- IME Composition Fix (Safari + Chrome) ---
# Safari fires compositionend BEFORE keydown for the confirming Enter,
# so IME can look "inactive" by keydown time.  A short "recently composed"
# window catches that case.  keyCode 229 / key "Process" covers Chrome.
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
st.components.v1.html(_IME_FIX_JS, height=0)

if "messages" not in st.session_state:
    st.session_state.messages = []
if "bridge" not in st.session_state:
    st.session_state.bridge = AsyncBridge()
if "agent" not in st.session_state:
    st.session_state.agent = ClaudeChatAgent(project_root=PROJECT_ROOT)

with st.sidebar:
    st.subheader("Project Config")
    st.caption(f"Project: `{PROJECT_ROOT}`")
    st.caption(f"Claude config: `{CLAUDE_DIR}`")
    st.caption(f"Auth: `{get_auth_description()}`")

    if st.button("Clear chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

runtime_errors = validate_runtime_environment()
if runtime_errors:
    st.error("Configuration issue detected.")
    for error in runtime_errors:
        st.caption(error)

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

prompt = st.chat_input("Type your message...", disabled=bool(runtime_errors))
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        status_placeholder = st.empty()
        response_placeholder = st.empty()

        status_placeholder.status("考え中...", state="running")

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
            response_text = (
                "Error: chat request failed. Check authentication and network settings. "
                f"Details: {exc}"
            )
        finally:
            status_placeholder.empty()

        response_placeholder.markdown(response_text)

    st.session_state.messages.append({"role": "assistant", "content": response_text})
