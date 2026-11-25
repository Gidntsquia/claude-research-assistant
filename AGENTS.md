# Research assistant for Claude Desktop Cowork

A plugin (three skills, two hooks, a folder template) plus a one-page guide for a professor of archaeology. The research behind the parts lives in `research/`, one file per topic.

## Where things live

- Plugin source is `plugin/`: skills in `plugin/skills/`, hooks and manifest in `plugin/hooks/` and `plugin/.claude-plugin/`, folder template in `plugin/folder-template/`. Edit it there.
- `build/` is generated and gitignored; `dist/research-assistant-plugin.zip` is committed.
- Tests and the test set are in `tests/` (`tests/test-set/`, `tests/tools/`, `tests/runs/`). `tests/RESULTS.md` is written by `score_conversations.py`; `tests/runs/walkthrough.html` by `render_walkthrough.py`. `tests/runs/first-build/` and `tests/runs/load-test/` are records of earlier builds.
- The one check in the real app is `tests/cowork/COWORK-CHECKLIST.md` (done by the user, not by an agent).
- Before a skill or the guide changes, the reason goes into its `research/<topic>.md` in an earlier commit.
- The guide is `guide/guide.html`; its PDF is `guide/research-assistant-guide.pdf`.
- `plans/` is gitignored.

## Commands

```
uv run build_plugin.py                                        # rebuild the plugin zip
claude plugin validate build/research-assistant
uv run guide/make_pdf.py                                      # reprint the guide PDF after a guide change
uv run --with pytest --with pymupdf pytest -q tests/tools
uv run tests/tools/check_summary.py SUMMARY.md --pdf ARTICLE.pdf --require-pages
uv run tests/tools/memory_tree.py scale                       # rewrites tests/runs/memory/REPORT.md
uv run tests/tools/memory_tree.py check DIR/memory
tests/tools/run_session.sh WORKSPACE OUT_BASENAME "PROMPT" [--resume ID] [--no-plugin]
tests/tools/run_conversation.sh c1|c2 K                      # one launch: conversation 1 or 2 of repeat K (messages in conversations.json)
uv run tests/tools/score_conversations.py                     # rewrites tests/RESULTS.md
uv run tests/tools/render_walkthrough.py 1                    # rewrites tests/runs/walkthrough.html
```

## Facts worth knowing

- `run_conversation.sh` and `run_session.sh` each start one headless `claude -p` with the built zip (Sonnet, budget and turn caps). It is the stand-in for Cowork; nothing here drives the Claude Desktop window. Use a scratch folder as WORKSPACE, never the repo.
- A headless child may confuse the workspace `memory/` with Claude Code's own memory directory under `~/.claude/projects/`; the hook prints the absolute path for that reason. Keep it.
- The child sees only what the hooks print and the skills say; a rule that must hold on every message belongs in `hooks/each-message.sh`, not only in a skill.
- The guide is `guide/guide.html` printed to Letter PDF with headless Chrome by `guide/make_pdf.py`. This Chrome does not always exit after printing; the script shows how to stop it. Check the PDF is still one page after any edit.
- This Mac has no poppler; PDF work uses `pymupdf` through `uv run --with pymupdf`.
- Publisher PDF links (Royal Society, PMC) return 403 to curl; repository copies work.
- Tokens are counted as characters / 4 everywhere.
- Every `run_conversation.sh` launch adds a line to `tests/runs/LAUNCHES.md` and the script refuses at 15 lines. It needs `plugin/` and `dist/` committed and the zip rebuilt. Conversation 2 reuses conversation 1's scratch workspace (`$RA_SCRATCH` or `$TMPDIR`), so run c1 before c2 for a repeat.
- A changed plugin means old conversation rows no longer count: move them to `tests/runs/conversations/old/` before rerunning.
- A summary length setting must give fewer details than the default's minimum of 5, or "shorter" cannot be told from default.
