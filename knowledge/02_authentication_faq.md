# Authentication FAQ

This note explains common authentication setup and troubleshooting patterns.

## How to choose authentication mode

- Use `CLAUDE_AUTH_MODE=api_key` when you have `ANTHROPIC_API_KEY`.
- Use `CLAUDE_AUTH_MODE=subscription` when you logged in via `claude login`.
- Use `CLAUDE_AUTH_MODE=auto` to try API key first, then subscription.

## Typical errors and fixes

### Error: No authentication found

Cause: neither API key nor CLI subscription is available.

Fix:
1. Set `ANTHROPIC_API_KEY` in `.env`, or
2. Run `claude login`.

### Error: Request failed after retries

Cause: network instability, invalid credentials, or upstream API rejection.

Fix:
- Verify API key validity.
- Confirm internet connectivity.
- Increase `CLAUDE_MAX_RETRIES` if failures are transient.

## Recommended baseline

For local development, keep:
- `CLAUDE_AUTH_MODE=auto`
- `CLAUDE_MAX_RETRIES=2`
- `CLAUDE_RETRY_BACKOFF_SECONDS=0.5`
