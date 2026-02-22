"""Minimal Streamlit chat UI powered by Claude Agent SDK."""

from __future__ import annotations

import logging

import streamlit as st

from agent.async_bridge import AsyncBridge
from agent.client import ClaudeChatAgent
from config.settings import APP_ICON, APP_TITLE, CLAUDE_DIR, PROJECT_ROOT

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout="wide")
st.title(APP_TITLE)

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

    if st.button("Clear chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

prompt = st.chat_input("Type your message...")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        final_text_parts: list[str] = []

        async def _stream() -> str:
            async for chunk in st.session_state.agent.send_message_streaming(prompt):
                ctype = chunk.get("type")
                content = chunk.get("content", "")

                if ctype in {"text_delta", "text"}:
                    final_text_parts.append(content)
                    placeholder.markdown("".join(final_text_parts))
                elif ctype == "error":
                    final_text_parts.append(f"\n\nError: {content}")
                    placeholder.markdown("".join(final_text_parts))

            if not final_text_parts:
                final_text_parts.append("(No response)")
                placeholder.markdown(final_text_parts[0])
            return "".join(final_text_parts)

        try:
            response_text = st.session_state.bridge.run(_stream())
        except Exception as exc:
            logger.exception("Chat request failed")
            response_text = f"Error: {exc}"
            placeholder.markdown(response_text)

    st.session_state.messages.append({"role": "assistant", "content": response_text})
