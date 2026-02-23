# 認証設定FAQ（日本語）

このドキュメントは、テンプレートの認証設定に関する日本語の補足ナレッジです。

## 認証モードの選び方

- `CLAUDE_AUTH_MODE=api_key`:
  `ANTHROPIC_API_KEY` を使って認証する場合に利用します。
- `CLAUDE_AUTH_MODE=subscription`:
  `claude login` 済みのサブスクリプション認証を使う場合に利用します。
- `CLAUDE_AUTH_MODE=auto`:
  APIキー優先で、未設定ならサブスクリプションへフォールバックします。

## よくあるエラー

### 「No authentication found」

原因:
- APIキー未設定かつ `claude login` 未実施。

対処:
1. `.env` に `ANTHROPIC_API_KEY` を設定する。
2. もしくは `claude login` を実行する。

## 推奨設定（ローカル開発）

- `CLAUDE_AUTH_MODE=auto`
- `CLAUDE_MAX_RETRIES=2`
- `CLAUDE_RETRY_BACKOFF_SECONDS=0.5`
