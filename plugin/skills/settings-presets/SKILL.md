---
name: settings-presets
description: Keep the professor's preferences between sessions. Use at the first reply of every conversation in the research folder (to count it), when he asks to change how answers look or sound ("be shorter", "less formal", "always show the quotes", "start with the argument"), asks "what are my settings?", asks to go back to the defaults, names a preset (quick read, full breakdown, devil's advocate) or wants a preset to work differently.
---

# Settings and presets

The assistant is his to shape. How it answers is a set of defaults that he changes by saying so; he is asked nothing at the start and opens no file.

**Scope.** What is saved in `memory/SETTINGS.md` applies to every later reply of every kind, in this task and every later one, and wins over any default in the skills or `CLAUDE.md`.

## The file

It keeps the shape it was created with (the discussion-memory skill shows it): `# Settings` (Length, Tone, Summary style, Preset, Other), `# Presets` (one line each) and `# State`. It stays within 300 tokens (about 1,200 characters) by merging lines, not by dropping something he still wants. If it is not shown at the start of a session, read it once.

## When he asks for a change

- Do it in the very next reply.
- If he means it from now on, write it to the file at once, briefly, with the date, on the line it belongs to (`- Length: shorter (asked 2026-11-24)`); anything else goes under `Other`. A new request replaces the old one on its line. Confirm in one line. A request for one answer only is applied and not saved.
- "Shorter" for a summary means 3 to 4 details, visibly fewer than the default; "longer again" returns to the default.
- "What are my settings?": list them in plain words, presets included. "Go back to the defaults": restore the Settings and Presets lines of the shape above, leave State alone, confirm in one line.

## Presets

The lines under `# Presets` are starting points in plain words, his to change.

- When he names one, write it on the `Preset:` line and follow its line as it now reads, until he names another or says "normal".
- When he says one should work differently ("quick read should be three details"), rewrite that line and confirm in one line. The new text is the preset in every later task.
- Requests made after naming a preset are saved on their own lines and win over it.
- Tell him once that the presets exist, as the `Presets mentioned` line says.

## Counting conversations

`Conversations` goes up by 1 once per conversation. The session-start note normally does it and says so; if none appeared, add 1 at your first reply.
