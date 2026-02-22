# claude-agent-app-template

Claude Agent SDK + Streamlit の最小チャットアプリテンプレートです。

このテンプレートの目的:
- Python側は「チャットUI + SDK接続」だけにする
- エージェント/スキル/MCPは設定ファイルで管理する
- `.claude/skills` にスキルを置くだけで再利用できる土台にする

## Features

- Streamlit ベースの最小チャットUI
- Claude Agent SDK のストリーミング応答
- `.claude/agents` / `.claude/skills` でエージェント・スキル管理
- `.mcp.json` による MCP サーバー設定

## Requirements

- Python 3.12 以上

## Project Structure

```text
claude-agent-app-template/
├── app.py
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
├── .pre-commit-config.yaml
├── .env.example
├── .mcp.json
├── .claude/
│   ├── settings.json
│   ├── agents/
│   │   └── general-chat-assistant.md
│   └── skills/
│       └── example-skill/
│           ├── SKILL.md
│           └── references/
│               └── quick-start.md
├── agent/
│   ├── async_bridge.py
│   └── client.py
└── config/
    └── settings.py
```

## Quick Start

```bash
cd claude-agent-app-template
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
cp .env.example .env
pre-commit install
pre-commit run --all-files
python -m unittest discover -s tests -v
streamlit run app.py
```

## Configuration

### 1) Environment Variables (`.env`)

- `ANTHROPIC_API_KEY`: 必須
- `CLAUDE_MODEL`: 例 `claude-sonnet-4-5-20250929`
- `CLAUDE_PERMISSION_MODE`: 例 `default` / `acceptEdits` / `bypassPermissions`
- `CLAUDE_SETTING_SOURCES`: 例 `project,local`
- `CLAUDE_MAX_RETRIES`: SDK接続/問い合わせ失敗時の再試行回数
- `CLAUDE_RETRY_BACKOFF_SECONDS`: 再試行間の待機秒数（線形バックオフ）

### 2) Agent/Skill Settings (`.claude`)

- エージェント: `.claude/agents/*.md`
- スキル: `.claude/skills/<skill-name>/SKILL.md`
- プロジェクト設定: `.claude/settings.json`

スキル追加方法:
1. `.claude/skills` 配下にフォルダ作成
2. `SKILL.md` を追加
3. 必要なら `references/` を追加

### 3) MCP Settings (`.mcp.json`)

`mcpServers` に MCP サーバーを定義します。例:

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

## Testing

```bash
python -m unittest discover -s tests -v
```

## Quality Gate (Ruff / Mypy / pre-commit)

```bash
pre-commit install
pre-commit run --all-files
```

`git commit` 時に以下が自動実行されます。
- `ruff check --fix`
- `ruff format`
- `mypy --config-file pyproject.toml`
