# 社内共有チェックリスト（日本語）

このドキュメントは、テンプレートを社内共有する前に確認する項目をまとめた日本語ナレッジです。

## 共有前チェックは次の5項目です

1. `pre-commit run --all-files` が成功すること。
2. `python3 -m unittest discover -s tests -v` が成功すること。
3. `.env.example` に危険な既定値（`bypassPermissions` など）が入っていないこと。
4. `knowledge/` の内容に機密情報が含まれていないこと。
5. README の手順が現行実装（添付機能・ナレッジ検索）と一致していること。

## 推奨設定（社内共有向け）

- `CLAUDE_PERMISSION_MODE=default`
- `CLAUDE_SDK_SANDBOX_ENABLED=true`
- `APP_LOG_FORMAT=json`

## 補足

共有前チェックは「品質・安全性・再現性」を同時に担保することが目的です。
