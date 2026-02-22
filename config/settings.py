"""Application settings for Claude Agent App Template."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal, cast

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLAUDE_DIR = PROJECT_ROOT / ".claude"
MCP_CONFIG_PATH = PROJECT_ROOT / ".mcp.json"

APP_TITLE = "Claude Agent App Template"
APP_ICON = "🤖"

PermissionMode = Literal["default", "acceptEdits", "plan", "bypassPermissions"]
SettingSource = Literal["user", "project", "local"]
AuthMode = Literal["auto", "api_key"]


def _parse_permission_mode(raw: str) -> PermissionMode:
    if raw in {"default", "acceptEdits", "plan", "bypassPermissions"}:
        return cast(PermissionMode, raw)
    return "default"


def _parse_setting_sources(raw: str) -> list[SettingSource]:
    parsed: list[SettingSource] = []
    for source in raw.split(","):
        normalized = source.strip()
        if normalized in {"user", "project", "local"}:
            parsed.append(cast(SettingSource, normalized))
    return parsed or ["project", "local"]


def _parse_auth_mode(raw: str) -> AuthMode:
    if raw in {"auto", "api_key"}:
        return cast(AuthMode, raw)
    return "auto"


ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
DEFAULT_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5-20250929")
DEFAULT_PERMISSION_MODE: PermissionMode = _parse_permission_mode(
    os.getenv("CLAUDE_PERMISSION_MODE", "default").strip()
)
DEFAULT_MAX_RETRIES = int(os.getenv("CLAUDE_MAX_RETRIES", "2"))
DEFAULT_RETRY_BACKOFF_SECONDS = float(os.getenv("CLAUDE_RETRY_BACKOFF_SECONDS", "0.5"))

SETTING_SOURCES = _parse_setting_sources(os.getenv("CLAUDE_SETTING_SOURCES", "project,local"))


AUTH_MODE: AuthMode = _parse_auth_mode(os.getenv("CLAUDE_AUTH_MODE", "auto").strip())


def _detect_cli_subscription() -> bool:
    """Check if Claude CLI has an active subscription login."""
    import json
    import subprocess

    try:
        result = subprocess.run(
            ["claude", "auth", "status"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            info = json.loads(result.stdout)
            return info.get("loggedIn", False)
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
        pass
    return False


HAS_CLI_SUBSCRIPTION = _detect_cli_subscription()


def validate_runtime_environment() -> list[str]:
    """Return user-facing configuration errors that block chat requests."""
    errors: list[str] = []
    if AUTH_MODE == "api_key" and not ANTHROPIC_API_KEY:
        errors.append("ANTHROPIC_API_KEY is not set. Add it to .env before sending chat requests.")
    elif AUTH_MODE == "auto" and not ANTHROPIC_API_KEY and not HAS_CLI_SUBSCRIPTION:
        errors.append(
            "No authentication found. Either set ANTHROPIC_API_KEY in .env, "
            "or run `claude login` to use your Claude subscription."
        )
    return errors


def get_auth_description() -> str:
    """Return a human-readable description of the active auth method."""
    if ANTHROPIC_API_KEY:
        return "API Key"
    if HAS_CLI_SUBSCRIPTION:
        return "Subscription (OAuth)"
    return "Not configured"
