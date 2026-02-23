# Authentication FAQ

This note explains common authentication setup and troubleshooting patterns.

## Supported authentication

This template supports Claude Agent SDK authentication via `ANTHROPIC_API_KEY`.
Set the key in `.env` before starting Streamlit.

## Typical errors and fixes

### Error: ANTHROPIC_API_KEY is not set

Cause: API key is missing from runtime environment.

Fix:
1. Set `ANTHROPIC_API_KEY` in `.env`.
2. Restart the app process so the new environment value is loaded.

### Error: Request failed after retries

Cause: network instability, invalid credentials, or upstream API rejection.

Fix:
- Verify API key validity.
- Confirm internet connectivity.
- Increase `CLAUDE_MAX_RETRIES` if failures are transient.

## Recommended baseline

For local development, keep:
- `ANTHROPIC_API_KEY=<your-key>`
- `CLAUDE_MAX_RETRIES=2`
- `CLAUDE_RETRY_BACKOFF_SECONDS=0.5`
