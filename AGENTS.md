# Research assistant for Claude Desktop

A plugin for Claude Desktop: three skills, a quotes script and a folder template; no hooks. Its two contributions are the memory format and that the user can reshape how it answers by saying so; everything else in the definition is a default.

## Where things live

- Plugin source is `plugin/`: skills in `plugin/skills/`, manifest in `plugin/.claude-plugin/`, folder template in `plugin/folder-template/`. Edit it there.
- `build/` is generated and gitignored; `dist/research-assistant-plugin.zip` is committed and is the file attached to each release.
- Tests are in `tests/tools/`; the article they read is `tests/test-set/caprolace.pdf` with its page-image copy `caprolace-scanned.pdf` (`tests/test-set/MANIFEST.md`).
- `tests/**`, `AGENTS.md` and `.gitattributes` are marked `export-ignore`, so `git archive` and GitHub's "Source code" downloads leave them out.
- The user guide is the wiki page "Using The Research Assistant"; `wiki/` is a gitignored clone of the wiki repo.
- `tests/runs/` and `tests/RESULTS.md` are written by the run and score scripts and are gitignored.

## Commands

```
uv run build_plugin.py                                        # rebuild the plugin zip
claude plugin validate build/research-assistant
uv run --with pytest --with pymupdf pytest -q tests/tools
uv run tests/tools/check_summary.py SUMMARY.md --pdf ARTICLE.pdf --require-pages   # checks the default summary shape
uv run --with pymupdf plugin/skills/article-summary/scripts/quotes.py FILE --page N --near "WORDS"   # the article's own sentence with its page
uv run tests/tools/memory_tree.py scale                       # writes tests/runs/memory/REPORT.md
uv run tests/tools/memory_tree.py check DIR/memory
uv run tests/tools/trial_watch.py FOLDER                      # watches a research folder during a chat, page on http://localhost:8765
tests/tools/run_session.sh WORKSPACE OUT_BASENAME "PROMPT" [--resume ID] [--no-plugin]
tests/tools/run_conversation.sh c1|c2 K                      # one launch: conversation 1 or 2 of repeat K (messages in conversations.json)
uv run tests/tools/score_conversations.py                     # writes tests/RESULTS.md
```

## Facts worth knowing

- `run_conversation.sh` and `run_session.sh` each start one headless `claude -p` with the built zip (Sonnet, budget and turn caps). It is the stand-in for the app; nothing here drives the Claude Desktop window. Use a scratch folder as WORKSPACE, never the repo.
- Every `run_conversation.sh` launch adds a line to `tests/runs/LAUNCHES.md` and the script refuses at 15 lines. It needs `plugin/` and `dist/` committed and the zip rebuilt. Conversation 2 reuses conversation 1's scratch workspace (`$RA_SCRATCH` or `$TMPDIR`), so run c1 before c2 for a repeat.
- The plugin definition (skills, `folder-template/CLAUDE.md`) is a short description with named defaults. Outside the memory format it uses no "exactly", "never" or "must" (`test_plugin_moldable.py` checks this and the word counts).
- The user leads: a reply answers what was asked; quotes, presets and settings come up when the user raises them. There are no "say once" rules, no state lines and no conversation counter; do not add any. "Settings win over defaults", the saving rule and the preset-rewrite rule live in `folder-template/CLAUDE.md` only.
- No hooks: plugin hooks did not reach Claude in Claude Desktop 7.37095.0. Do not add hooks back. The first line of `CLAUDE.md` and of each skill has the memory files read, and the discussion-memory skill creates a new folder's files from the template text the build writes into it.
- `memory/SETTINGS.md` is the one place a preference lives. Presets are plain lines under `# Presets` there; the file stays within 300 tokens.
- Quotes are the output of `quotes.py` run on the copy in the user's folder (a web article is saved there as text first). Exit 3: no PDF text tool; exit 4: a scan.
- PDF work in the tests uses `pymupdf` through `uv run --with pymupdf`.
- Tokens are counted as characters / 4 everywhere.
- In Claude Desktop a file reaches the Mac folder only when Claude writes it with its file tools; a shell write never arrives.
- A summary length setting must give fewer details than the default's minimum of 5, or "shorter" cannot be told from default.
- A release is tag `vX.Y.Z` matching `plugin.json`, titled "Research assistant X.Y.Z", with the one asset `research-assistant-plugin.zip`; the README links `releases/latest/download/research-assistant-plugin.zip`.
