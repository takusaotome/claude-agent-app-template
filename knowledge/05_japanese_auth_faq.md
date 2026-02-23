# 認証設定FAQ（日本語）

このドキュメントは、テンプレートの認証設定に関する日本語の補足ナレッジです。

## 対応している認証方式

このテンプレートは `ANTHROPIC_API_KEY` による認証を前提にしています。  
`.env` に APIキーを設定してから起動してください。

## よくあるエラー

### 「ANTHROPIC_API_KEY is not set」

原因:
- `.env` に APIキーが設定されていない。

対処:
1. `.env` に `ANTHROPIC_API_KEY` を設定する。
2. アプリを再起動して環境変数を再読み込みする。

## 推奨設定（ローカル開発）

- `ANTHROPIC_API_KEY=<your-key>`
- `CLAUDE_MAX_RETRIES=2`
- `CLAUDE_RETRY_BACKOFF_SECONDS=0.5`
