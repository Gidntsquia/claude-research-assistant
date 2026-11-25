#!/bin/sh
# Run one headless Claude session in a workspace folder (standing in for the
# professor's Cowork folder), with the built plugin zip loaded, and save the raw
# event stream plus a readable transcript.
#
#   run_session.sh WORKSPACE OUT_BASENAME "PROMPT" [--resume SESSION_ID] [--no-plugin]
#
# User-level settings and CLAUDE.md are left out (--setting-sources project,local)
# so the session sees what the professor's would: the plugin and the folder.
set -eu
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
WORKSPACE="$1"; OUT="$2"; PROMPT="$3"; shift 3
PLUGIN="--plugin-dir $REPO/phase-4-customization-install/dist/research-assistant-plugin.zip"
RESUME=""
while [ $# -gt 0 ]; do
  case "$1" in
    --resume) RESUME="--resume $2"; shift 2 ;;
    --no-plugin) PLUGIN=""; shift ;;
    *) echo "unknown option $1" >&2; exit 2 ;;
  esac
done
# Cowork's sandbox has Python with PDF libraries; this Mac's system Python has none
# (and no poppler), so give the session a small venv that does.
VENV="$REPO/phase-1-baseline/tools/.venv"
if [ ! -x "$VENV/bin/python3" ]; then
  uv venv -q "$VENV" && uv pip install -q --python "$VENV/bin/python3" pymupdf pypdf
fi
PATH="$VENV/bin:$PATH"; export PATH
mkdir -p "$WORKSPACE" "$(dirname "$OUT")"
cd "$WORKSPACE"
# shellcheck disable=SC2086
claude -p "$PROMPT" $PLUGIN $RESUME \
  --model sonnet --max-budget-usd 4 --max-turns 60 \
  --setting-sources project,local \
  --permission-mode acceptEdits \
  --allowedTools "Read,Write,Edit,Glob,Grep,WebFetch,WebSearch,Skill,Bash(curl:*),Bash(ls:*),Bash(wc:*),Bash(mkdir:*),Bash(cp:*),Bash(date:*),Bash(python3:*),Bash(pdftotext:*)" \
  --output-format stream-json --verbose > "$OUT.jsonl" || echo "claude exited with $?" >&2
python3 "$REPO/phase-1-baseline/tools/transcript.py" "$OUT.jsonl" "$PROMPT" > "$OUT.md"
tail -4 "$OUT.md"
