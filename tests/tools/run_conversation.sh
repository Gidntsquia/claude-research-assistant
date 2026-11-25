#!/bin/sh
# One test conversation = one headless Claude launch (Sonnet, $6 and 120-turn caps) with the
# built zip, several messages sent one after another to the same process.
#
#   tests/tools/run_conversation.sh c1 K      conversation 1 of repeat K: a fresh, empty workspace
#   tests/tools/run_conversation.sh c2 K      conversation 2 of repeat K: a new launch in the SAME workspace
#
# Messages are in tests/tools/conversations.json. Output goes to tests/runs/conversations/rK-cN.*
# (events, transcript, meta, and memory/ as it was after each message). Every launch appends
# one line to tests/runs/LAUNCHES.md; at 15 lines the script refuses to launch (plan: hard stop).
# The workspace is a scratch folder outside the repo, kept between c1 and c2 of a repeat.
# Afterwards: uv run tests/tools/score_conversations.py
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd)"                  # tests/
REPO="$(cd "$HERE/.." && pwd)"
CONV="${1:?usage: run_conversation.sh c1|c2 K}"; K="${2:?repeat number}"
OUTDIR="$HERE/runs/conversations"; OUT="$OUTDIR/r$K-$CONV"
LOG="$HERE/runs/LAUNCHES.md"
ZIP="$REPO/dist/research-assistant-plugin.zip"
WS="${RA_SCRATCH:-${TMPDIR:-/tmp}}/ra-conversation-r$K"
mkdir -p "$OUTDIR"; touch "$LOG"
if [ "$(wc -l < "$LOG")" -ge 15 ]; then echo "not run: guard (LAUNCHES.md already has 15 lines)" >&2; exit 3; fi
if ! git -C "$REPO" diff --quiet HEAD -- plugin dist; then
  echo "plugin or dist has uncommitted changes: commit before a scored run" >&2; exit 2
fi
rm -rf "$REPO/build/zipcheck" && mkdir -p "$REPO/build/zipcheck" && unzip -q "$ZIP" -d "$REPO/build/zipcheck"
for f in hooks/each-message.sh hooks/session-start.sh skills/article-summary/SKILL.md skills/settings-presets/SKILL.md folder-template/CLAUDE.md; do
  cmp -s "$REPO/build/zipcheck/$f" "$REPO/plugin/$f" || { echo "the zip does not match plugin/$f: run uv run build_plugin.py" >&2; exit 2; }
done
case "$CONV" in
  c1) rm -rf "$WS"; mkdir -p "$WS" ;;
  c2) [ -f "$WS/memory/INDEX.md" ] || { echo "no workspace from c1 of repeat $K at $WS" >&2; exit 2; } ;;
  *) echo "unknown conversation $CONV" >&2; exit 2 ;;
esac
VENV="$HERE/tools/.venv"
if [ ! -x "$VENV/bin/python3" ]; then
  uv venv -q "$VENV" && uv pip install -q --python "$VENV/bin/python3" pymupdf pypdf
fi
PATH="$VENV/bin:$PATH"; export PATH
COMMIT="$(git -C "$REPO" log -1 --format=%h -- plugin dist)"
STARTED="$(TZ=America/New_York date '+%Y-%m-%d %-I:%M %p ET')"
rm -rf "$OUT.memory" "$OUT.jsonl" "$OUT.md" "$OUT.meta.json"
# The messages, one per line (none contains a newline), into "$@".
MSGS="$(python3 -c 'import json,sys; [print(m) for m in json.load(open(sys.argv[1]))[sys.argv[2]]]' "$HERE/tools/conversations.json" "$CONV")"
OLDIFS="$IFS"; IFS='
'
# shellcheck disable=SC2086
set -- $MSGS
IFS="$OLDIFS"
echo "run  r$K-$CONV  ($STARTED), $# messages, workspace $WS"
cd "$WS"
TWO_TURNS_SNAPSHOT="$WS/memory:$OUT.memory" python3 "$HERE/tools/two_turns.py" "$OUT.jsonl" "$@" -- \
  claude -p --input-format stream-json --output-format stream-json --verbose \
  --plugin-dir "$ZIP" --model sonnet --max-budget-usd 6 --max-turns 120 \
  --setting-sources project,local --permission-mode acceptEdits \
  --allowedTools "Read,Write,Edit,Glob,Grep,WebFetch,WebSearch,Skill,Bash(curl:*),Bash(ls:*),Bash(wc:*),Bash(mkdir:*),Bash(cp:*),Bash(date:*),Bash(python3:*),Bash(pdftotext:*)" \
  > "$OUT.log" 2>&1
CODE=$?
cd "$HERE"
RESULTS="$(grep -c '"type": *"result"' "$OUT.jsonl" 2>/dev/null || echo 0)"
echo "$STARTED | r$K-$CONV | plugin commit $COMMIT | $RESULTS of $# messages answered | exit $CODE" >> "$LOG"
if [ "$RESULTS" -gt 0 ]; then
  python3 "$HERE/tools/replies.py" "$OUT" "$@" > /dev/null
  rm -f "$OUT.reply.md" "$OUT.quotes.md" "$OUT.log"
fi
OUT="$OUT" python3 - "r$K-$CONV" "$CONV" "$K" "$COMMIT" "$STARTED" "$@" <<'PY'
import json, os, sys
json.dump({"run": sys.argv[1], "conversation": sys.argv[2], "repeat": int(sys.argv[3]), "plugin_commit": sys.argv[4],
           "started": sys.argv[5], "messages": sys.argv[6:]}, open(os.environ["OUT"] + ".meta.json", "w"), indent=1)
PY
echo "     $RESULTS of $# messages answered (exit $CODE); LAUNCHES.md has $(wc -l < "$LOG" | tr -d ' ') of 15 lines"
