# 添付ファイルアップロード 403 対処（日本語）

このドキュメントは、`/_stcore/upload_file/...` で 403 が返る場合の対処をまとめた日本語ナレッジです。

## 症状

- ファイル添付時に `403 Forbidden` が発生する。
- ブラウザのNetworkタブで、`_streamlit_xsrf` Cookie と `X-Xsrftoken` ヘッダーが不一致になる。

## 主な原因

StreamlitのXSRF検証でトークン不一致が起きると、アップロードは拒否されます。
`localhost` と `127.0.0.1` を混在させる運用や、複数アプリ同時起動で発生しやすいです。

## 対処手順

1. localhost関連のStreamlitタブをすべて閉じる。
2. ブラウザのサイトデータ（localhost / 127.0.0.1）を削除する。
3. Streamlitを再起動する。
4. URL表記を1種類に統一する（例: `127.0.0.1` のみ）。

## 安定運用設定

`.streamlit/config.toml` の例:

```toml
[server]
address = "127.0.0.1"
enableXsrfProtection = true
enableCORS = true

[browser]
serverAddress = "127.0.0.1"
```
