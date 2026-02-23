# claude-agent-app-template

A minimal chat application template built with Claude Agent SDK + Streamlit.

Design goals:
- The Python layer handles **only** chat UI and SDK connectivity
- Agents, skills, and MCP servers are managed through configuration files
- Adding a skill is as simple as placing it under `.claude/skills`

## Features

- Minimal Streamlit-based chat UI
- Claude Agent SDK streaming responses with real-time tool activity display
- Agent and skill management via `.claude/agents` / `.claude/skills`
- MCP server configuration via `.mcp.json`
- Output sanitization (redacts API keys and system paths)
- IME composition fix for Safari / Chrome (Japanese input support)
- Subscription authentication support (`claude login`)
- Bilingual UI (`APP_LOCALE=en|ja`)

## Requirements

- Python 3.12+
- Claude Agent SDK 0.1.35+
- `requirements-dev.txt` tools installed in your active environment (`pre-commit`, `ruff`, `mypy`)

## Project Structure

```text
claude-agent-app-template/
├── app.py                        # Streamlit UI (entry point)
├── agent/
│   ├── __init__.py               # SDK patch auto-apply
│   ├── async_bridge.py           # Async-to-sync bridge for Streamlit
│   ├── client.py                 # ClaudeChatAgent (SDK wrapper)
│   ├── sanitizer.py              # Output sanitizer (secrets & paths)
│   └── _sdk_patch.py             # Monkey-patch for unknown SDK events
├── config/
│   └── settings.py               # Environment variables and constants
├── tests/
│   ├── test_app.py
│   ├── test_async_bridge.py
│   ├── test_client.py
│   ├── test_sdk_patch.py
│   ├── test_sanitizer.py
│   └── test_settings.py
├── scripts/                      # User-generated scripts (via chat)
├── .claude/
│   ├── settings.json             # Project-level permission rules
│   ├── agents/
│   │   └── general-chat-assistant.md
│   └── skills/
│       └── example-skill/
│           ├── SKILL.md
│           └── references/
│               └── quick-start.md
├── .env.example
├── .mcp.json
├── requirements.txt
├── requirements-dev.txt
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── pyproject.toml
├── .pre-commit-config.yaml
├── LICENSE
├── .github/workflows/ci.yml
└── CLAUDE.md
```

## Quick Start

```bash
cd claude-agent-app-template
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
cp .env.example .env              # Set ANTHROPIC_API_KEY or use `claude login`
pre-commit install
pre-commit run --all-files
python3 -m unittest discover -s tests -v
streamlit run app.py
```

## Authentication

Two authentication methods are supported:

| Method | Setup | `.env` setting |
|---|---|---|
| API Key | Set `ANTHROPIC_API_KEY` in `.env` | `CLAUDE_AUTH_MODE=api_key` (or omit) |
| Subscription (OAuth) | Run `claude login` in terminal | `CLAUDE_AUTH_MODE=subscription` |

When `CLAUDE_AUTH_MODE=auto` (default), the app tries the API key first and falls back to subscription.

## Configuration

### 1) Environment Variables (`.env`)

| Variable | Description | Default |
|---|---|---|
| `ANTHROPIC_API_KEY` | API key (leave empty if using subscription) | — |
| `CLAUDE_MODEL` | Model name | `claude-sonnet-4-5-20250929` |
| `CLAUDE_AUTH_MODE` | `auto` / `api_key` / `subscription` | `auto` |
| `CLAUDE_PERMISSION_MODE` | `default` / `acceptEdits` / `bypassPermissions` | `default` |
| `CLAUDE_SETTING_SOURCES` | Settings sources | `project,local` |
| `CLAUDE_MAX_RETRIES` | Retry count on connection/query failure | `2` |
| `CLAUDE_RETRY_BACKOFF_SECONDS` | Wait time between retries (linear backoff) | `0.5` |
| `APP_LOCALE` | UI language (`en` / `ja`) | `en` |
| `APP_LOG_FORMAT` | Log format (`text` / `json`) | `text` |
| `APP_LOG_LEVEL` | Log level (`DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`) | `INFO` |
| `CLAUDE_SDK_SANDBOX_ENABLED` | SDK sandbox toggle (`true` / `false`) | `false` |

For non-interactive Streamlit usage, set `CLAUDE_PERMISSION_MODE=acceptEdits` only when your workflow requires automatic file edits.

### 2) Agent / Skill Settings (`.claude`)

- **Agents**: `.claude/agents/*.md` — frontmatter + system prompt
- **Skills**: `.claude/skills/<skill-name>/SKILL.md` — skill definition with optional `references/`
- **Permissions**: `.claude/settings.json` — allow/deny rules for tools and file access

To add a new skill:
1. Create a folder under `.claude/skills/`
2. Add a `SKILL.md` file
3. Optionally add `references/` for domain knowledge

### 3) MCP Settings (`.mcp.json`)

Define MCP servers under the `mcpServers` key:

```json
{
  "mcpServers": {
    "my-server": {
      "command": "python",
      "args": ["-m", "my_mcp_server"],
      "cwd": "/path/to/server"
    }
  }
}
```

## Security

- **Permission rules** in `.claude/settings.json` restrict filesystem access, Bash commands, and tool use
- `Bash(python -c *)` / `Bash(python3 -c *)` are explicitly denied to block arbitrary Python one-liners
- `pip*`, `python -m pip*`, and `WebFetch(*)` are denied by default (least-privilege baseline)
- **Output sanitization** (`agent/sanitizer.py`) redacts API keys and absolute paths from responses
- Output sanitization is a display-layer safeguard; it does not replace permission controls
- **System prompt restrictions** prevent the agent from accessing `.env`, credentials, or navigating outside the project
- SDK sandbox is disabled by default (`CLAUDE_SDK_SANDBOX_ENABLED=false`) to keep Streamlit + project-scoped permission flow predictable; enable it when your runtime policy requires additional process isolation
- See `CLAUDE.md` for the full security policy

## Scripts Policy

- `scripts/` is for local helper scripts only
- Only `scripts/.gitkeep` is tracked in Git
- Do not commit temporary security/debug scripts

## Container Run

```bash
docker compose up --build
```

Then open `http://localhost:8501`.
Container health endpoint: `/_stcore/health` (used by Docker `HEALTHCHECK` and Compose health probes).

## Testing

```bash
python3 -m unittest discover -s tests -v
```

## Quality Gate (Ruff / Mypy / pre-commit)

```bash
pre-commit install
pre-commit run --all-files
```

The following checks run automatically on `git commit`:
- `ruff check --fix`
- `ruff format`
- `mypy --config-file pyproject.toml`

Hooks are configured with `language: system`, so they use tools already installed in the active virtual environment and do not create isolated hook environments.

## CI

- GitHub Actions workflow: `.github/workflows/ci.yml`
- Runs `pre-commit run --all-files` and `unittest` on push / pull request

## License

This template is released under the MIT License. See `LICENSE`.
