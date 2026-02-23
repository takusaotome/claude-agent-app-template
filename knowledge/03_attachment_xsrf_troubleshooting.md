# Attachment Upload and XSRF Troubleshooting

This note explains why file upload may fail with HTTP 403 in Streamlit.

## Symptom

- Upload request to `/_stcore/upload_file/...` returns `403 Forbidden`.
- Browser network panel shows a mismatch between cookie `_streamlit_xsrf` and header `X-Xsrftoken`.

## Root cause

Streamlit rejects upload requests when XSRF token validation fails.
This can happen when multiple local apps share localhost cookies.

## Recovery steps

1. Close all Streamlit tabs for localhost.
2. Clear browser site data for localhost / 127.0.0.1.
3. Restart Streamlit.
4. Use only one host style (for example only `127.0.0.1`).

## Stable config

Use `.streamlit/config.toml`:

```toml
[server]
address = "127.0.0.1"
enableXsrfProtection = true
enableCORS = true

[browser]
serverAddress = "127.0.0.1"
```

This keeps XSRF protection enabled while reducing token mismatch risk.
