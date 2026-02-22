# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Is

Streamlit + Claude Agent SDK による最小構成のチャットアプリテンプレート。Python側は「チャットUI + SDK接続」のみに専念し、エージェント・スキル・MCPは設定ファイルで管理する設計。

## Commands

```bash
# Setup
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
cp .env.example .env   # ANTHROPIC_API_KEY を設定
pre-commit install
pre-commit run --all-files
python -m unittest discover -s tests -v

# Run
streamlit run app.py
```

テストは `unittest` を利用（`tests/`）。静的チェックは `pre-commit`（`ruff` / `mypy`）を利用。

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

## Development Practice – TDD (Test-Driven Development)

このプロジェクトでは TDD を標準の開発手法として採用する。

### TDD サイクル

1. **Red** – 失敗するテストを先に書く
2. **Green** – テストを通す最小限のコードを実装する
3. **Refactor** – テストが通る状態を維持しつつコードを整理する

### ルール

- 新機能・バグ修正には、対応するテストを **必ず先に** 書く
- テストは `tests/` ディレクトリに `test_<module>.py` の命名規則で配置
- テストフレームワークは `unittest`（標準ライブラリ）を使用
- 外部依存（SDK, API, ファイルシステム）は `unittest.mock` でモック化する
- テスト実行: `python -m unittest discover -s tests -v`
- PR 前に全テストが通ることを確認する

### テスト設計指針

- 各テストは独立して実行可能であること（テスト間の依存を排除）
- テスト名は `test_<振る舞いの説明>` とし、何をテストしているか明確にする
- Arrange-Act-Assert パターンに従う
- カバレッジよりも、ビジネスロジックと境界条件のテストを優先する

## Sandbox Rules – チャットアプリ経由のコード実行

このプロジェクトは Streamlit チャット UI を通じて Claude Agent が動作する。
エージェントがユーザーの依頼でスクリプトを作成・実行する場合、以下のルールに **必ず** 従うこと。

### ファイル作成ルール

- ユーザーの依頼で作成する Python スクリプトは **`scripts/` ディレクトリに格納する**
  - 例: `scripts/demo.py`, `scripts/data_analysis.py`
  - テストファイルは `scripts/tests/` に配置してもよい
- **以下のファイル・ディレクトリは絶対に上書き・変更・削除しない**:
  - `app.py`
  - `agent/` ディレクトリ以下すべて
  - `config/` ディレクトリ以下すべて
  - `tests/` ディレクトリ以下すべて（プロジェクト本体のテスト）
  - `.claude/` ディレクトリ以下すべて
  - `.env`, `.env.example`
  - `requirements.txt`, `requirements-dev.txt`
  - `CLAUDE.md`, `README.md`
  - `.mcp.json`, `.gitignore`, `.pre-commit-config.yaml`

### 実行ルール

- スクリプト実行時のカレントディレクトリはプロジェクトルートとする
- 実行コマンド例: `python scripts/demo.py`
- 出力ファイル（CSV, JSON, 画像など）も `scripts/` 以下に保存する

## Key Dependencies

- `streamlit` >= 1.42.0
- `claude-agent-sdk` >= 0.1.35
- `python-dotenv` >= 1.0.0
