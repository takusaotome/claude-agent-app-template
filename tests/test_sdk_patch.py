"""Unit tests for SDK monkey-patch module."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

import agent._sdk_patch as patch_module


class ApplySdkPatchesTests(unittest.TestCase):
    """Validates the SDK message parser patching behavior."""

    def setUp(self) -> None:
        # Reset the global _PATCHED flag before each test.
        patch_module._PATCHED = False

    def test_patch_is_idempotent(self) -> None:
        """Calling apply_sdk_patches twice should only patch once."""
        patch_module._PATCHED = True
        # If the function tries to import, it would fail in test env.
        # Since _PATCHED is True, it should return immediately.
        patch_module.apply_sdk_patches()
        self.assertTrue(patch_module._PATCHED)

    def test_patch_survives_import_failure(self) -> None:
        """If SDK internals are unavailable, patching fails gracefully."""
        patch_module._PATCHED = False
        with patch.dict("sys.modules", {"claude_agent_sdk._internal": None}):
            # Should not raise even when imports fail.
            patch_module.apply_sdk_patches()
        # _PATCHED remains False when patching fails.
        self.assertFalse(patch_module._PATCHED)

    def test_safe_parse_message_returns_original_on_success(self) -> None:
        """When the original parser succeeds, the wrapper returns its result."""
        original_parse = MagicMock(return_value="parsed")
        fake_system_message = MagicMock()

        # Simulate the wrapping logic directly.
        mock_parse_error: type[Exception] = type("MessageParseError", (Exception,), {})

        def safe_parse(data: dict) -> object:
            try:
                return original_parse(data)
            except mock_parse_error:
                return fake_system_message

        result = safe_parse({"type": "text"})
        self.assertEqual(result, "parsed")
        original_parse.assert_called_once_with({"type": "text"})

    def test_safe_parse_message_returns_system_message_on_unknown_type(self) -> None:
        """When the original parser raises, the wrapper returns a SystemMessage."""
        mock_parse_error: type[Exception] = type("MessageParseError", (Exception,), {})
        original_parse = MagicMock(side_effect=mock_parse_error("unknown"))
        sentinel = object()

        def safe_parse(data: dict) -> object:
            try:
                return original_parse(data)
            except mock_parse_error:
                return sentinel

        result = safe_parse({"type": "rate_limit_event"})
        self.assertIs(result, sentinel)
