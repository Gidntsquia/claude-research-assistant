---
name: settings-presets
description: Keep the professor's preferences between sessions. Use when he asks to change how answers look or sound ("be shorter", "less formal", "always show the quotes", "start with the argument"), asks "what can you do?" or "what are my settings?", asks to go back to the defaults, names a preset (quick read, full breakdown, devil's advocate) or wants a preset to work differently.
---

Before answering, read `CLAUDE.md`, `memory/INDEX.md` and `memory/SETTINGS.md` in his folder, unless this task has already shown them to you.

# Settings and presets

The assistant is his to shape. How it answers is a set of defaults that he changes by saying so; he is asked nothing at the start and opens no file.

## The file

It keeps the shape it was created with (the discussion-memory skill shows it and creates it in a new folder): `# Settings` (Length, Tone, Summary style, Preset, Other) and `# Presets` (one line each). It stays within 300 tokens (about 1,200 characters) by merging lines, not by dropping something he still wants.

## When he asks for a change

- Do it in the very next reply.
- If he means it from now on, write it to the file at once, briefly, with the date, on the line it belongs to (`- Length: shorter (asked 2026-11-24)`); anything else goes under `Other`. A new request replaces the old one on its line. Confirm in one line. A request for one answer only is applied and not saved.
- "Shorter" for a summary means 3 to 4 details, visibly fewer than the default; "longer again" returns to the default.
- "What can you do?" or "What are my settings?": in plain words, that he can ask for the article's own sentences, the three presets by name with what each now does, and his settings as they stand.
- "Go back to the defaults": restore the Settings and Presets lines of the shape above and confirm in one line.

## Presets

The lines under `# Presets` are starting points in plain words, his to change.

- When he names one, write it on the `Preset:` line and follow its line as it now reads, until he names another or says "normal".
- Requests made after naming a preset are saved on their own lines and come before it.
