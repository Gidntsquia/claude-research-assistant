# Research assistant for Claude Desktop Cowork

A plugin (three skills, two hooks, a folder template) plus a one-page guide and a pilot kit, built in five phase folders. Each folder has a `RESEARCH.md` that justifies its parts with sources.

## Where things live

- Skills are edited in their phase folder, not in the build: `phase-2-summarizing-input/skill/`, `phase-3-discussion-memory/skill/`, `phase-4-customization-install/skill/`.
- Hooks and manifest: `phase-4-customization-install/plugin-src/`. Folder template: `phase-4-customization-install/folder-template/` and `phase-3-discussion-memory/folder-template/`.
- `phase-4-customization-install/build/` is generated and gitignored; `dist/research-assistant-plugin.zip` is committed.
- `phase-5-professor-pilot/send/` is what goes to the professor; its zip, guide and PDFs are copies made by `make_pdfs.py`.
- `plans/` is gitignored.

## Commands

```
uv run phase-4-customization-install/build_plugin.py          # rebuild the plugin zip
claude plugin validate phase-4-customization-install/build/research-assistant
uv run phase-5-professor-pilot/tools/make_pdfs.py             # refresh send/ after any rebuild or guide change
uv run --with pytest --with pymupdf pytest -q phase-1-baseline/tools phase-3-discussion-memory/scaling phase-5-professor-pilot/tools
uv run phase-1-baseline/tools/check_summary.py SUMMARY.md --pdf ARTICLE.pdf --require-pages
uv run phase-3-discussion-memory/scaling/memory_tree.py scale          # rewrites scaling/REPORT.md
uv run phase-3-discussion-memory/scaling/memory_tree.py check DIR/memory
phase-1-baseline/tools/run_session.sh WORKSPACE OUT_BASENAME "PROMPT" [--resume ID] [--no-plugin]
```

## Facts worth knowing

- `run_session.sh` starts one headless `claude -p` with the built zip (Sonnet, budget and turn caps). It is the stand-in for Cowork; nothing here drives the Claude Desktop window. Use a scratch folder as WORKSPACE, never the repo.
- A headless child may confuse the workspace `memory/` with Claude Code's own memory directory under `~/.claude/projects/`; the hook prints the absolute path for that reason. Keep it.
- The child sees only what the hooks print and the skills say; a rule that must hold on every message belongs in `hooks/each-message.sh`, not only in a skill.
- The guide is `phase-4-customization-install/guide/guide.html` printed to Letter PDF with headless Chrome. This Chrome does not always exit after printing; `make_pdfs.py` shows how to stop it. Check the PDF is still one page after any edit.
- This Mac has no poppler; PDF work uses `pymupdf` through `uv run --with pymupdf`.
- Publisher PDF links (Royal Society, PMC) return 403 to curl; repository copies work.
- Tokens are counted as characters / 4 everywhere.
