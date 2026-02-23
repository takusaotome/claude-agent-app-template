"""Unit tests for app.py helper functions."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from app import (
    _apply_stream_chunk,
    _build_prompt_context,
    _cleanup_uploads_on_startup_once,
    _msg,
    _tool_status_label,
)


class ApplyStreamChunkTests(unittest.TestCase):
    """Validates the stream chunk buffering logic."""

    def test_text_delta_appended_to_buffer(self) -> None:
        parts: list[str] = []
        result = _apply_stream_chunk(parts, {"type": "text_delta", "content": "Hi"})
        self.assertTrue(result)
        self.assertEqual(parts, ["Hi"])

    def test_text_appended_to_buffer(self) -> None:
        parts: list[str] = []
        result = _apply_stream_chunk(parts, {"type": "text", "content": "Hello"})
        self.assertTrue(result)
        self.assertEqual(parts, ["Hello"])

    def test_error_appended_with_prefix(self) -> None:
        parts: list[str] = []
        result = _apply_stream_chunk(parts, {"type": "error", "content": "Timeout"})
        self.assertTrue(result)
        self.assertEqual(parts, ["\n\nError: Timeout"])

    def test_done_chunk_is_ignored(self) -> None:
        parts: list[str] = []
        result = _apply_stream_chunk(parts, {"type": "done", "content": "sid"})
        self.assertFalse(result)
        self.assertEqual(parts, [])

    def test_empty_content_is_ignored(self) -> None:
        parts: list[str] = []
        result = _apply_stream_chunk(parts, {"type": "text_delta", "content": ""})
        self.assertFalse(result)
        self.assertEqual(parts, [])

    def test_missing_content_key_is_safe(self) -> None:
        parts: list[str] = []
        result = _apply_stream_chunk(parts, {"type": "text_delta"})
        self.assertFalse(result)
        self.assertEqual(parts, [])

    def test_multiple_chunks_accumulate(self) -> None:
        parts: list[str] = []
        _apply_stream_chunk(parts, {"type": "text_delta", "content": "Hel"})
        _apply_stream_chunk(parts, {"type": "text_delta", "content": "lo"})
        self.assertEqual(parts, ["Hel", "lo"])

    def test_tool_status_label_english(self) -> None:
        with patch("app.UI_LOCALE", "en"):
            self.assertEqual(_tool_status_label("Bash"), "Running command")
            self.assertEqual(_tool_status_label("core__Write"), "Writing file")

    def test_tool_status_label_japanese(self) -> None:
        with patch("app.UI_LOCALE", "ja"):
            self.assertEqual(_tool_status_label("Bash"), "コマンド実行")

    def test_message_localization(self) -> None:
        with patch("app.UI_LOCALE", "ja"):
            self.assertEqual(_msg("clear_chat"), "チャットをクリア")

    def test_build_prompt_context_without_knowledge_or_attachments(self) -> None:
        with patch("app.KNOWLEDGE_ENABLED", False):
            with patch("app.ATTACHMENTS_ENABLED", False):
                prompt, warnings, attachment_names = _build_prompt_context(
                    "hello",
                    [],
                    attachment_session_id="test-session",
                )

        self.assertIn("[USER_MESSAGE]", prompt)
        self.assertIn("hello", prompt)
        self.assertEqual(warnings, [])
        self.assertEqual(attachment_names, [])


class StartupUploadCleanupTests(unittest.TestCase):
    """Behavior tests for startup-time upload cleanup."""

    def test_startup_cleanup_runs_once(self) -> None:
        with patch("app.ATTACHMENTS_ENABLED", True):
            with patch("app._UPLOADS_CLEANED_AT_STARTUP", False):
                with patch("app.cleanup_all_uploads") as mock_cleanup:
                    _cleanup_uploads_on_startup_once()
                    _cleanup_uploads_on_startup_once()
        self.assertEqual(mock_cleanup.call_count, 1)

    def test_startup_cleanup_is_skipped_when_attachments_disabled(self) -> None:
        with patch("app.ATTACHMENTS_ENABLED", False):
            with patch("app._UPLOADS_CLEANED_AT_STARTUP", False):
                with patch("app.cleanup_all_uploads") as mock_cleanup:
                    _cleanup_uploads_on_startup_once()
        mock_cleanup.assert_not_called()
