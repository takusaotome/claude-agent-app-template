# Knowledge Search Usage

This note describes how the app uses markdown files in `knowledge/`.

## How it works

- The app lists all `knowledge/*.md` files.
- It runs `rg` keyword search for each user message.
- It injects matching lines into prompt context as references.
- The model can read referenced files directly for more detail.

## Good question examples

- "How do I fix 403 Forbidden during file upload?"
- "What is the recommended auth mode?"
- "How does knowledge search work in this template?"

## Writing good knowledge files

- Use clear section headings.
- Include exact error keywords users may ask about.
- Keep one topic per file for better retrieval precision.
