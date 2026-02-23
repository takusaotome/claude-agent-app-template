# Project Usage Guide

This knowledge note summarizes the basic usage of `claude-agent-app-template`.

## 1. Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
cp .env.example .env
```

## 2. Authentication

- API key mode: set `ANTHROPIC_API_KEY` in `.env`
- Subscription mode: run `claude login` in your terminal

## 3. Run the App

```bash
streamlit run app.py
```

## 4. Chat Usage

- Send prompts from the chat input at the bottom of the page
- Attach `txt/md/csv/json` files when needed
- Attachments are stored under `uploads/<session_id>/` on the server side
- The prompt includes attachment paths; the agent reads files at runtime when needed

## 5. Knowledge Lookup

- Markdown files under `knowledge/` are searchable references
- The app runs `rg` per request and injects relevant line hits into prompt context
- Add new knowledge by placing additional `.md` files in `knowledge/`

## 6. Quality Checks

```bash
pre-commit run --all-files
python3 -m unittest discover -s tests -v
```

## 7. Common Settings

- `APP_LOCALE=en|ja`: UI language
- `ATTACHMENTS_ENABLED=true|false`: toggle attachment support
- `KNOWLEDGE_ENABLED=true|false`: toggle knowledge lookup
- `CONTEXT_MAX_CHARS=12000`: total prompt context budget
