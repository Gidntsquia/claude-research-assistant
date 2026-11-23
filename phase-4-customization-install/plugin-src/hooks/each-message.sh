#!/bin/sh
# UserPromptSubmit hook: one fixed line per message, only in a folder that has memory/.
# Saving after each answer is the rule most easily skipped late in a long conversation,
# and sessions end without warning, so it is repeated where Claude will see it.
DIR="${CLAUDE_PROJECT_DIR:-$PWD}"
if [ -f "$DIR/memory/INDEX.md" ]; then
  echo "[research-assistant] Order for this message: (1) read what you need; (2) if it is about a research subject, rewrite that subject's one branch file in $DIR/memory/ and its index line now (his position, yours, date, open angles), and if he asked to change how you answer, write that to $DIR/memory/SETTINGS.md now; (3) then write your answer to him as the last thing in your turn, complete in itself. Never end with a remark about notes or files, and never refer to text 'above': he sees only your final answer."
fi
exit 0
