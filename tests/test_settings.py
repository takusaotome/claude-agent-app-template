"""Unit tests for application settings."""

from __future__ import annotations

import importlib
import os
import unittest
from unittest.mock import patch

import config.settings as settings_module


class SettingsTests(unittest.TestCase):
    """Validates env var parsing and runtime validation."""

    def _reload_settings(self):
        with patch.dict(os.environ, {"PYTHON_DOTENV_DISABLED": "1"}, clear=False):
            return importlib.reload(settings_module)

    def test_validation_reports_missing_api_key(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            settings = self._reload_settings()
            # Override values that load_dotenv may have restored from .env.
            settings.ANTHROPIC_API_KEY = ""
            errors = settings.validate_runtime_environment()

        self.assertTrue(errors)
        self.assertIn("ANTHROPIC_API_KEY", errors[0])

    def test_setting_sources_are_trimmed_and_empty_values_removed(self) -> None:
        with patch.dict(
            os.environ,
            {
                "ANTHROPIC_API_KEY": "dummy",
                "CLAUDE_SETTING_SOURCES": " project, local ,,user ",
            },
            clear=True,
        ):
            settings = self._reload_settings()

        self.assertEqual(settings.SETTING_SOURCES, ["project", "local", "user"])
        self.assertEqual(settings.validate_runtime_environment(), [])

    def test_permission_mode_defaults_to_safer_mode(self) -> None:
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "dummy"}, clear=True):
            settings = self._reload_settings()

        self.assertEqual(settings.DEFAULT_PERMISSION_MODE, "default")

    def test_ui_locale_defaults_to_english(self) -> None:
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "dummy"}, clear=True):
            settings = self._reload_settings()

        self.assertEqual(settings.UI_LOCALE, "en")

    def test_ui_locale_accepts_japanese(self) -> None:
        with patch.dict(
            os.environ,
            {"ANTHROPIC_API_KEY": "dummy", "APP_LOCALE": "ja"},
            clear=True,
        ):
            settings = self._reload_settings()

        self.assertEqual(settings.UI_LOCALE, "ja")

    def test_log_settings_defaults(self) -> None:
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "dummy"}, clear=True):
            settings = self._reload_settings()

        self.assertEqual(settings.APP_LOG_FORMAT, "text")
        self.assertEqual(settings.APP_LOG_LEVEL, "INFO")

    def test_log_settings_parse_custom_values(self) -> None:
        with patch.dict(
            os.environ,
            {
                "ANTHROPIC_API_KEY": "dummy",
                "APP_LOG_FORMAT": "json",
                "APP_LOG_LEVEL": "warning",
            },
            clear=True,
        ):
            settings = self._reload_settings()

        self.assertEqual(settings.APP_LOG_FORMAT, "json")
        self.assertEqual(settings.APP_LOG_LEVEL, "WARNING")

    def test_sdk_sandbox_defaults_to_disabled(self) -> None:
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "dummy"}, clear=True):
            settings = self._reload_settings()

        self.assertFalse(settings.SDK_SANDBOX_ENABLED)

    def test_sdk_sandbox_can_be_enabled(self) -> None:
        with patch.dict(
            os.environ,
            {"ANTHROPIC_API_KEY": "dummy", "CLAUDE_SDK_SANDBOX_ENABLED": "true"},
            clear=True,
        ):
            settings = self._reload_settings()

        self.assertTrue(settings.SDK_SANDBOX_ENABLED)

    def test_attachments_and_knowledge_defaults(self) -> None:
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "dummy"}, clear=True):
            settings = self._reload_settings()

        self.assertTrue(settings.ATTACHMENTS_ENABLED)
        self.assertEqual(settings.ATTACHMENTS_MAX_FILE_MB, 5)
        self.assertEqual(settings.ATTACHMENTS_ALLOWED_EXTENSIONS, ("txt", "md", "csv", "json"))
        self.assertEqual(settings.ATTACHMENTS_STORAGE_DIR, "uploads")
        self.assertTrue(settings.KNOWLEDGE_ENABLED)
        self.assertEqual(settings.KNOWLEDGE_DIR, "knowledge")
        self.assertEqual(settings.KNOWLEDGE_MAX_HITS, 8)
        self.assertEqual(settings.CONTEXT_MAX_CHARS, 12000)

    def test_context_related_settings_parse_custom_values(self) -> None:
        with patch.dict(
            os.environ,
            {
                "ANTHROPIC_API_KEY": "dummy",
                "ATTACHMENTS_ENABLED": "false",
                "ATTACHMENTS_MAX_FILE_MB": "3",
                "ATTACHMENTS_ALLOWED_EXT": "md,txt",
                "ATTACHMENTS_STORAGE_DIR": "custom_uploads",
                "KNOWLEDGE_ENABLED": "false",
                "KNOWLEDGE_DIR": "knowledge_custom",
                "KNOWLEDGE_MAX_HITS": "5",
                "CONTEXT_MAX_CHARS": "9000",
            },
            clear=True,
        ):
            settings = self._reload_settings()

        self.assertFalse(settings.ATTACHMENTS_ENABLED)
        self.assertEqual(settings.ATTACHMENTS_MAX_FILE_MB, 3)
        self.assertEqual(settings.ATTACHMENTS_ALLOWED_EXTENSIONS, ("md", "txt"))
        self.assertEqual(settings.ATTACHMENTS_STORAGE_DIR, "custom_uploads")
        self.assertFalse(settings.KNOWLEDGE_ENABLED)
        self.assertEqual(settings.KNOWLEDGE_DIR, "knowledge_custom")
        self.assertEqual(settings.KNOWLEDGE_MAX_HITS, 5)
        self.assertEqual(settings.CONTEXT_MAX_CHARS, 9000)

    def test_custom_model_is_respected(self) -> None:
        with patch.dict(
            os.environ,
            {"ANTHROPIC_API_KEY": "dummy", "CLAUDE_MODEL": "claude-opus-4-6"},
            clear=True,
        ):
            settings = self._reload_settings()

        self.assertEqual(settings.DEFAULT_MODEL, "claude-opus-4-6")

    def test_default_model_when_env_not_set(self) -> None:
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "dummy"}, clear=True):
            settings = self._reload_settings()

        self.assertEqual(settings.DEFAULT_MODEL, "claude-sonnet-4-5-20250929")

    def test_retry_settings_parsed_from_env(self) -> None:
        with patch.dict(
            os.environ,
            {
                "ANTHROPIC_API_KEY": "dummy",
                "CLAUDE_MAX_RETRIES": "5",
                "CLAUDE_RETRY_BACKOFF_SECONDS": "1.5",
            },
            clear=True,
        ):
            settings = self._reload_settings()

        self.assertEqual(settings.DEFAULT_MAX_RETRIES, 5)
        self.assertEqual(settings.DEFAULT_RETRY_BACKOFF_SECONDS, 1.5)

    def test_retry_settings_defaults(self) -> None:
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "dummy"}, clear=True):
            settings = self._reload_settings()

        self.assertEqual(settings.DEFAULT_MAX_RETRIES, 2)
        self.assertEqual(settings.DEFAULT_RETRY_BACKOFF_SECONDS, 0.5)

    def test_get_auth_description_with_api_key(self) -> None:
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"}, clear=True):
            settings = self._reload_settings()

        self.assertEqual(settings.get_auth_description(), "API Key")

    def test_get_auth_description_not_configured(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            settings = self._reload_settings()
            settings.ANTHROPIC_API_KEY = ""

        self.assertEqual(settings.get_auth_description(), "Not configured")

    def test_validation_fails_without_api_key(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            settings = self._reload_settings()
            settings.ANTHROPIC_API_KEY = ""
            errors = settings.validate_runtime_environment()

        self.assertTrue(errors)
        self.assertIn("ANTHROPIC_API_KEY", errors[0])

    def test_validation_ignores_subscription_auth_mode_env(self) -> None:
        with patch.dict(
            os.environ,
            {"CLAUDE_AUTH_MODE": "subscription"},
            clear=True,
        ):
            settings = self._reload_settings()
            settings.ANTHROPIC_API_KEY = ""
            errors = settings.validate_runtime_environment()

        self.assertTrue(errors)
        self.assertIn("ANTHROPIC_API_KEY", errors[0])
