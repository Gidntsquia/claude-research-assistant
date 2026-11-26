#!/bin/sh
# SessionStart hook: three facts for Claude at the start of a task, no instructions: where
# the research memory is, what its index says, what his settings say.
#
# Prints at most 4,800 + 1,200 characters of memory/INDEX.md and memory/SETTINGS.md
# (1,200 + 300 tokens at 4 characters per token) whatever is on disk, so the loaded size
# cannot grow with the number of chats. Reads those two files, writes nothing.
# Prints only in a folder that has memory/INDEX.md: the plugin is installed for the whole
# account and other folders get nothing. A new research folder's files are created by the
# discussion-memory skill; how to answer is in the folder's CLAUDE.md, not here.
DIR="${CLAUDE_PROJECT_DIR:-$PWD}"
INDEX="$DIR/memory/INDEX.md"
SETTINGS="$DIR/memory/SETTINGS.md"
[ -f "$INDEX" ] || exit 0
echo "[research-assistant] Research memory: $DIR/memory (a subfolder of the user's connected folder, next to CLAUDE.md; it is not Claude's or the app's own memory store)."
echo "[research-assistant] Its index, $INDEX, reads:"
head -c 4800 "$INDEX"
echo
if [ -f "$SETTINGS" ]; then
  echo "[research-assistant] His settings, $SETTINGS, read:"
  head -c 1200 "$SETTINGS"
  echo
fi
exit 0
