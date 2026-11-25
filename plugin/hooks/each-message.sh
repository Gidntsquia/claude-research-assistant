#!/bin/sh
# UserPromptSubmit hook: two facts on each message, in at most 60 words: where the research
# memory is, and what he has asked for (the lines of memory/SETTINGS.md that are not at their
# default; an active preset is given with its text as the file now has it).
# Prints only in a folder that has memory/INDEX.md, so other folders on his account get nothing.
DIR="${CLAUDE_PROJECT_DIR:-$PWD}"
S="$DIR/memory/SETTINGS.md"
[ -f "$DIR/memory/INDEX.md" ] || exit 0
SAVED=""
if [ -f "$S" ]; then
  SAVED="$(awk '
    /^# /               { sec = $0; next }
    sec == "# Presets" && /^- / { line = substr($0, 3); i = index(line, ":")
                          if (i) { name[++n] = substr(line, 1, i - 1); text[n] = substr(line, i + 2) } next }
    sec == "# Settings" && /^- / { line = substr($0, 3); i = index(line, ":")
                          if (!i) next
                          key = substr(line, 1, i - 1); val = substr(line, i + 2)
                          low = tolower(val)
                          if (low == "" || low ~ /^(default|none)/) next
                          if (key == "Preset") preset = val
                          else out = out (out == "" ? "" : "; ") key ": " val }
    END { if (preset != "") { p = "preset " preset
            for (k = 1; k <= n; k++) if (index(tolower(preset), tolower(name[k])) == 1) p = "preset " name[k] " = " text[k]
            out = out (out == "" ? "" : "; ") p }
          print out }' "$S")"
fi
if [ -n "$SAVED" ]; then
  MSG="[research-assistant] Research memory: $DIR/memory. His saved settings apply to this reply: $SAVED"
else
  MSG="[research-assistant] Research memory: $DIR/memory. His saved settings: all at the defaults."
fi
printf '%s\n' "$MSG" | awk '{ if (NF <= 60) { print; next }
  for (i = 1; i <= 56; i++) printf "%s ", $i
  print "... (rest: memory/SETTINGS.md)" }'
exit 0
