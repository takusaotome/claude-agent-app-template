# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Is

Streamlit + Claude Agent SDK による最小構成のチャットアプリテンプレート。Python側は「チャットUI + SDK接続」のみに専念し、エージェント・スキル・MCPは設定ファイルで管理する設計。

## Commands

```bash
# Setup
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # ANTHROPIC_API_KEY を設定

# Run
streamlit run app.py
```

テストやリンターの設定は現時点では存在しない。

## Architecture

```
app.py                  Streamlit UI（エントリポイント）
  ↓ uses
agent/client.py         ClaudeChatAgent: SDK のストリーミング応答をラップ
  ↓ uses
agent/async_bridge.py   AsyncBridge: Streamlit の同期コンテキストで async コルーチンを実行
config/settings.py      .env → 環境変数の読み込みと定数定義
```

### Streamlit ↔ async の接続

Streamlit は同期的に再実行されるため、`AsyncBridge` が専用の `asyncio` イベントループを保持し `run_until_complete` で SDK の async ストリーミングを橋渡しする。`AsyncBridge` と `ClaudeChatAgent` は `st.session_state` に保存され、リラン間で維持される。

### SDK クライアントの流れ

`ClaudeChatAgent.send_message_streaming()` は `ClaudeSDKClient` に接続し、`StreamEvent`（テキストデルタ）、`AssistantMessage`（完了テキスト）、`ResultMessage`（エラー/完了）を `dict` に正規化して yield する。

## Configuration

| 設定先 | 用途 |
|---|---|
| `.env` | `ANTHROPIC_API_KEY`, `CLAUDE_MODEL`, `CLAUDE_PERMISSION_MODE`, `CLAUDE_SETTING_SOURCES` |
| `.claude/agents/*.md` | エージェント定義（frontmatter + システムプロンプト） |
| `.claude/skills/<name>/SKILL.md` | スキル定義。`references/` にドメイン知識を配置可能 |
| `.mcp.json` | MCP サーバー定義（`mcpServers` キー） |
| `.claude/settings.json` | プロジェクトレベルの権限設定 |

## Key Dependencies

- `streamlit` >= 1.42.0
- `claude-agent-sdk` >= 0.1.35
- `python-dotenv` >= 1.0.0
