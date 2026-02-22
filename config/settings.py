"""Application settings for Claude Agent App Template."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLAUDE_DIR = PROJECT_ROOT / ".claude"
MCP_CONFIG_PATH = PROJECT_ROOT / ".mcp.json"

APP_TITLE = "Claude Agent App Template"
APP_ICON = "🤖"

DEFAULT_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5-20250929")
DEFAULT_PERMISSION_MODE = os.getenv("CLAUDE_PERMISSION_MODE", "acceptEdits")

_SETTING_SOURCES_RAW = os.getenv("CLAUDE_SETTING_SOURCES", "project,local")
SETTING_SOURCES = [
    source.strip()
    for source in _SETTING_SOURCES_RAW.split(",")
    if source.strip()
]
