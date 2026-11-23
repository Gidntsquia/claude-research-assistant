#!/bin/sh
# SessionStart hook: put the memory index and the settings in front of Claude.
# Prints at most 4,800 + 1,200 characters (1,200 + 300 tokens at 4 characters per
# token), whatever is on disk, so the loaded size cannot grow with the number of chats.
# Reads two files and nothing else; never writes.
ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
DIR="${CLAUDE_PROJECT_DIR:-$PWD}"
INDEX="$DIR/memory/INDEX.md"
SETTINGS="$DIR/memory/SETTINGS.md"

if [ -f "$INDEX" ]; then
  echo "[research-assistant] Memory index (memory/INDEX.md), already loaded - do not read it again:"
  head -c 4800 "$INDEX"
  echo
  if [ -f "$SETTINGS" ]; then
    echo "[research-assistant] Settings (memory/SETTINGS.md), already loaded - follow them:"
    head -c 1200 "$SETTINGS"
    echo
  fi
  echo "[research-assistant] Open a branch file only when the user's subject matches a heading above: one file per level, never the whole memory folder."
else
  echo "[research-assistant] This folder has no memory/INDEX.md yet. If the user brings an article or a research subject, first create the memory files from the template at: $ROOT/folder-template (see the discussion-memory skill), without asking the user to do anything."
fi
exit 0
