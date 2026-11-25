#!/bin/sh
# SessionStart hook: put the memory index and the settings in front of Claude.
#
# Folder with memory/: counts the conversation (one line of SETTINGS.md), then prints
# at most 4,800 + 1,200 characters of INDEX.md and SETTINGS.md (1,200 + 300 tokens at
# 4 characters per token) whatever is on disk, so the loaded size cannot grow with the
# number of chats. Reads those two files and nothing else.
# Folder without memory/: writes nothing (the plugin is installed for the whole
# account, and other folders must stay untouched); prints the template so Claude can
# create the files the first time a research subject comes up.
ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
DIR="${CLAUDE_PROJECT_DIR:-$PWD}"
INDEX="$DIR/memory/INDEX.md"
SETTINGS="$DIR/memory/SETTINGS.md"
TPL="$ROOT/folder-template"

# The hook's input (JSON on stdin) says how the session began; a resumed or
# compacted session is the same conversation and is not counted again.
INPUT=""
if [ ! -t 0 ]; then INPUT="$(cat 2>/dev/null || true)"; fi
case "$INPUT" in
  *'"source":"resume"'*|*'"source": "resume"'*|*'"source":"compact"'*|*'"source": "compact"'*) NEW=no ;;
  *) NEW=yes ;;
esac

if [ -f "$INDEX" ]; then
  if [ "$NEW" = yes ] && [ -f "$SETTINGS" ] && grep -q '^- Conversations: [0-9][0-9]*' "$SETTINGS"; then
    awk '/^- Conversations: [0-9]+/ { n = $3 + 1; print "- Conversations: " n; next } { print }' \
      "$SETTINGS" > "$SETTINGS.tmp" && mv "$SETTINGS.tmp" "$SETTINGS"
  fi
  echo "[research-assistant] The research memory is the folder $DIR/memory (inside the user's connected folder, next to CLAUDE.md). Every memory path below is inside that folder. It is not Claude's or the app's own memory store: read and write research memory only there."
  echo "[research-assistant] Memory index ($INDEX), already loaded - do not read it again:"
  head -c 4800 "$INDEX"
  echo
  if [ -f "$SETTINGS" ]; then
    echo "[research-assistant] Settings (memory/SETTINGS.md), already loaded - follow them in every reply:"
    head -c 1200 "$SETTINGS"
    echo
  fi
  echo "[research-assistant] This conversation is already counted in Conversations above: do not add 1 again."
  echo "[research-assistant] Recall: when the user's subject matches a heading above, open that heading's one branch file in $DIR/memory/ (one file per level, never the whole folder), then tell him the date you last discussed it, his position then and your position then, and add one new angle that is not in the notes. No match: it is a new subject; do not claim to remember. Save: with each answer on a research subject, rewrite that subject's one branch and its index line first, quietly (discussion-memory skill has the format), then give the answer as the last thing in your turn."
else
  echo "[research-assistant] This folder has no memory yet. If the user brings an article or any research subject, then before replying create these three files in the folder $DIR yourself (that folder, not Claude's or the app's own memory store), silently, with exactly this content (the user must not be asked to do anything):"
  for f in memory/INDEX.md memory/SETTINGS.md CLAUDE.md; do
    if [ -f "$TPL/$f" ]; then
      echo "--- file: $f"
      cat "$TPL/$f"
    fi
  done
  echo "--- end of files. In memory/SETTINGS.md set Conversations to 1 (this conversation). If the folder already has a CLAUDE.md, put these lines at its top instead of replacing it. Then, after each answer on a research subject, save it as the discussion-memory skill describes."
fi
exit 0
