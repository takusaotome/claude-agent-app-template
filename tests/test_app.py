"""Unit tests for app.py helper functions."""

from __future__ import annotations

import unittest

from app import _apply_stream_chunk


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
