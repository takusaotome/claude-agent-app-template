"""Unit tests for app.py helper functions."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from agent.attachments import AttachmentPersistResult, StoredAttachment
from app import (
    _apply_stream_chunk,
    _build_prompt_context,
    _cleanup_uploads_on_startup_once,
    _consume_rate_limit,
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

    def test_build_prompt_context_with_knowledge_and_attachments(self) -> None:
        with (
            patch("app.KNOWLEDGE_ENABLED", True),
            patch("app.ATTACHMENTS_ENABLED", True),
            patch("app.resolve_knowledge_dir", return_value=Path(".")),
            patch(
                "app.list_knowledge_markdown_files",
                return_value=["knowledge/guide.md"],
            ),
            patch("app.search_knowledge_markdown", return_value=[]),
            patch(
                "app.build_knowledge_preamble",
                return_value="[KNOWLEDGE]\n- knowledge/guide.md",
            ),
            patch(
                "app.persist_attachments",
                return_value=AttachmentPersistResult(
                    attachments=[
                        StoredAttachment(
                            filename="note.txt",
                            relative_path="uploads/session-1/note.txt",
                            size_bytes=4,
                        )
                    ],
                    warnings=["attachment warning"],
                ),
            ),
        ):
            prompt, warnings, attachment_names = _build_prompt_context(
                "hello",
                [object()],
                attachment_session_id="session-1",
            )

        self.assertIn("[KNOWLEDGE]", prompt)
        self.assertIn("[ATTACHMENTS]", prompt)
        self.assertIn("uploads/session-1/note.txt", prompt)
        self.assertEqual(warnings, ["attachment warning"])
        self.assertEqual(attachment_names, ["note.txt"])

    def test_build_prompt_context_surfaces_knowledge_error(self) -> None:
        with (
            patch("app.KNOWLEDGE_ENABLED", True),
            patch("app.ATTACHMENTS_ENABLED", False),
            patch("app.resolve_knowledge_dir", side_effect=ValueError("invalid knowledge dir")),
        ):
            prompt, warnings, attachment_names = _build_prompt_context(
                "hello",
                [],
                attachment_session_id="session-1",
            )

        self.assertIn("[USER_MESSAGE]", prompt)
        self.assertEqual(attachment_names, [])
        self.assertTrue(warnings)
        self.assertIn("invalid knowledge dir", warnings[0])

    def test_build_prompt_context_surfaces_attachment_error(self) -> None:
        with (
            patch("app.KNOWLEDGE_ENABLED", False),
            patch("app.ATTACHMENTS_ENABLED", True),
            patch("app.persist_attachments", side_effect=ValueError("invalid uploads dir")),
        ):
            prompt, warnings, attachment_names = _build_prompt_context(
                "hello",
                [object()],
                attachment_session_id="session-1",
            )

        self.assertIn("[USER_MESSAGE]", prompt)
        self.assertEqual(attachment_names, [])
        self.assertTrue(warnings)
        self.assertIn("invalid uploads dir", warnings[0])


class RateLimitTests(unittest.TestCase):
    """Behavior tests for minute-level request limiting."""

    def test_consume_rate_limit_allows_and_appends_timestamp(self) -> None:
        updated, limited, retry = _consume_rate_limit(
            100.0,
            [10.0, 39.0],
            limit=3,
        )

        self.assertFalse(limited)
        self.assertEqual(retry, 0)
        self.assertEqual(updated, [100.0])

    def test_consume_rate_limit_blocks_at_limit(self) -> None:
        updated, limited, retry = _consume_rate_limit(
            100.0,
            [50.0, 70.0, 80.0],
            limit=3,
        )

        self.assertTrue(limited)
        self.assertEqual(updated, [50.0, 70.0, 80.0])
        self.assertEqual(retry, 10)


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
