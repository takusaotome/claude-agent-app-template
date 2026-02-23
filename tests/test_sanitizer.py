"""Unit tests for output sanitizer."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from agent.sanitizer import sanitize


class SanitizerTests(unittest.TestCase):
    """Security-focused tests for output redaction."""

    def test_redacts_anthropic_api_key(self) -> None:
        raw = "API key: sk-ant-ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"
        cleaned = sanitize(raw)
        self.assertNotIn("sk-ant-", cleaned)
        self.assertIn("[REDACTED_API_KEY]", cleaned)

    def test_redacts_long_token(self) -> None:
        raw = "token=ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890abcd"
        cleaned = sanitize(raw)
        self.assertIn("[REDACTED_TOKEN]", cleaned)

    def test_redacts_claude_internal_path(self) -> None:
        raw = ".claude/projects/demo/tool-results/abc123/result.json"
        cleaned = sanitize(raw)
        self.assertEqual(cleaned, "[internal-path]")

    def test_converts_project_absolute_path_to_relative(self) -> None:
        raw = "/Users/alice/work/app/scripts/demo.py"
        with patch("agent.sanitizer.os.getcwd", return_value="/Users/alice/work/app"):
            with patch("agent.sanitizer._HOME", "/Users/alice"):
                cleaned = sanitize(raw)
        self.assertEqual(cleaned, "scripts/demo.py")

    def test_redacts_home_path(self) -> None:
        raw = "/Users/alice/.ssh/id_rsa"
        with patch("agent.sanitizer._HOME", "/Users/alice"):
            cleaned = sanitize(raw)
        self.assertEqual(cleaned, "~/.ssh/id_rsa")

    def test_redacts_non_project_system_path(self) -> None:
        raw = "/etc/passwd"
        cleaned = sanitize(raw)
        self.assertEqual(cleaned, "[redacted-path]")
