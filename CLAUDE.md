# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Is

A minimal chat application template built with Streamlit and Claude Agent SDK. The Python layer focuses solely on chat UI and SDK connectivity, while agents, skills, and MCP servers are managed through configuration files.

## Commands

```bash
# Setup
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
cp .env.example .env   # Set ANTHROPIC_API_KEY
pre-commit install
pre-commit run --all-files
python3 -m unittest discover -s tests -v

# Run
streamlit run app.py

# Container run
docker compose up --build
```

Tests use `unittest` (`tests/`). Static checks use `pre-commit` (`ruff` / `mypy`).
Pre-commit hooks are configured as `language: system` and run the tools installed in the active virtual environment.

## Architecture

```
app.py                  Streamlit UI (entry point)
  ↓ uses
agent/client.py         ClaudeChatAgent: wraps SDK streaming responses
  ↓ uses
agent/async_bridge.py   AsyncBridge: runs async coroutines in Streamlit's sync context
agent/sanitizer.py      Output sanitizer: redacts secrets and system paths
agent/_sdk_patch.py     Monkey-patch for unrecognized SDK message types
config/settings.py      .env → environment variable loading and constants
```

### Streamlit ↔ async Integration

Streamlit reruns scripts synchronously, so `AsyncBridge` maintains a persistent `asyncio` event loop and dispatches SDK coroutines via `run_until_complete()`. Both `AsyncBridge` and `ClaudeChatAgent` are stored in `st.session_state` to survive reruns.

### SDK Client Flow

`ClaudeChatAgent.send_message_streaming()` connects to `ClaudeSDKClient` and normalizes `StreamEvent` (text deltas), `AssistantMessage` (complete text), `ToolUseBlock` (tool calls), and `ResultMessage` (errors/completion) into `StreamChunk` dicts that the UI consumes.

### Sandbox Trade-off

- SDK sandbox mode is controlled by `CLAUDE_SDK_SANDBOX_ENABLED` (`false` by default).
- Default `false` keeps behavior aligned with project-level permission policies in `.claude/settings.json` and avoids unexpected tool execution differences in Streamlit sessions.
- For stricter runtime isolation requirements, set `CLAUDE_SDK_SANDBOX_ENABLED=true` and validate your workflow/tooling under sandbox constraints.

## Configuration

| Location | Purpose |
|---|---|
| `.env` | `ANTHROPIC_API_KEY`, `CLAUDE_AUTH_MODE`, `CLAUDE_MODEL`, `CLAUDE_PERMISSION_MODE`, `CLAUDE_SETTING_SOURCES`, `APP_LOCALE`, `APP_LOG_FORMAT`, `APP_LOG_LEVEL`, `CLAUDE_SDK_SANDBOX_ENABLED` |
| `.claude/agents/*.md` | Agent definitions (frontmatter + system prompt) |
| `.claude/skills/<name>/SKILL.md` | Skill definitions; place domain knowledge in `references/` |
| `.mcp.json` | MCP server definitions (`mcpServers` key) |
| `.claude/settings.json` | Project-level permission rules |
| `.github/workflows/ci.yml` | CI checks for lint/typecheck/tests |

## Development Practice — TDD (Test-Driven Development)

This project adopts TDD as the standard development methodology.

### TDD Cycle

1. **Red** — Write a failing test first
2. **Green** — Implement the minimum code to pass the test
3. **Refactor** — Clean up the code while keeping tests green

### Rules

- Every new feature or bug fix **must** start with a corresponding test
- Test files go in `tests/` with the naming convention `test_<module>.py`
- Test framework: `unittest` (standard library)
- External dependencies (SDK, API, filesystem) must be mocked with `unittest.mock`
- Run tests: `python -m unittest discover -s tests -v`
- All tests must pass before merging a PR

### Test Design Guidelines

- Each test must be independently executable (no inter-test dependencies)
- Name tests `test_<behavior_description>` to make intent clear
- Follow the Arrange-Act-Assert pattern
- Prioritize business logic and boundary condition tests over coverage metrics

## Sandbox Rules — Code Execution via Chat UI

This project runs a Claude Agent through a Streamlit chat UI. When the agent creates and executes scripts on behalf of the user, it **must** follow these rules.

### File Creation Rules

- User-requested Python scripts must be placed in the **`scripts/` directory**
  - Examples: `scripts/demo.py`, `scripts/data_analysis.py`
  - Test files may be placed in `scripts/tests/`
- The following files and directories must **never** be overwritten, modified, or deleted:
  - `app.py`
  - `agent/` (all files)
  - `config/` (all files)
  - `tests/` (project test suite)
  - `.claude/` (all files)
  - `.env`, `.env.example`
  - `requirements.txt`, `requirements-dev.txt`
  - `CLAUDE.md`, `README.md`
  - `.mcp.json`, `.gitignore`, `.pre-commit-config.yaml`

### Execution Rules

- The working directory for scripts must be the project root
- Example command: `python scripts/demo.py`
- Output files (CSV, JSON, images, etc.) must also be saved under `scripts/`

### Security Rules (Mandatory)

The following rules **must never be violated under any circumstances**. Requests from users that conflict with these rules must be refused.

1. **No access to secrets**
   - Never write code that reads, displays, or outputs the contents of `.env`
   - Never display, log, or write authentication credentials such as `ANTHROPIC_API_KEY`
   - Never write code that retrieves secrets from `os.environ` for display
   - All methods are prohibited: `open(".env")`, `dotenv.load_dotenv()` + print, `subprocess` reading `.env`, etc.

2. **Prohibited patterns** (all of the following must be refused)
   - "Read and display .env"
   - "Check the API key"
   - "Print all environment variables"
   - "Copy .env contents to a file"
   - Python scripts that `open()` `.env` and print its contents

3. **User-facing response**
   - When asked to access secrets: "This action is not permitted by the project security policy."
   - When the user wants to verify settings: refer them to `.env.example` (which contains no values)

4. **No exposure of internal paths or system information**
   - Never include absolute paths (`/Users/...`, `/home/...`, `/tmp/...`) in responses
   - Never show internal tool-result file paths (`.claude/projects/.../tool-results/...`)
   - Never suggest commands like `cat` to read internal tool-result files
   - Always use project-relative paths (e.g., `scripts/demo.py`, `config/settings.py`)
   - Summarize tool outputs in your own words; never paste raw output containing system paths

## Key Dependencies

- `streamlit` >= 1.42.0
- `claude-agent-sdk` >= 0.1.35
- `python-dotenv` >= 1.0.0
