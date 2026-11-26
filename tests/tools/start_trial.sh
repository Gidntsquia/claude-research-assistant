#!/bin/sh
# The one command for the live trial in real Claude Desktop.
#
#   tests/tools/start_trial.sh
#
# Builds the trial zip, copies it to ~/Downloads/research-assistant-plugin.zip (the name the
# guide uses), starts the watcher on ~/Documents/Research and opens the guide PDF, the trial
# card and the live page in Firefox. Then you follow the guide's twelve clicks in Claude Desktop;
# nothing here drives the app. Ctrl-C stops the watcher and writes timeline.html.
#
# For tests only: RA_TRIAL_FOLDER, RA_TRIAL_DOWNLOADS, RA_TRIAL_PORT replace the folder, the
# Downloads folder and the port; RA_TRIAL_BACKGROUND=1 opens the tabs without raising Firefox.
set -eu
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
FOLDER="${RA_TRIAL_FOLDER:-$HOME/Documents/Research}"
DOWNLOADS="${RA_TRIAL_DOWNLOADS:-$HOME/Downloads}"
PORT="${RA_TRIAL_PORT:-8765}"

if [ -e "$FOLDER" ]; then
  echo "stopped: $FOLDER already exists."
  echo "The trial starts fresh: the guide's part 2 creates that folder. Move or rename it, then run this again."
  exit 1
fi

cd "$REPO"
uv run build_plugin.py --trial | head -1
cp "$REPO/dist/research-assistant-trial.zip" "$DOWNLOADS/research-assistant-plugin.zip"
echo "copied the trial zip to $DOWNLOADS/research-assistant-plugin.zip"
echo "first, in Claude Desktop: Plugins, then Uninstall every Research assistant entry (the setup page's step 1)"

trap : INT TERM
uv run tests/tools/trial_watch.py "$FOLDER" --port "$PORT" \
  --page "/guide.pdf=$REPO/guide/research-assistant-guide.pdf" \
  --page "/card=$REPO/tests/cowork/TRIAL-CARD.html" &
WATCHER=$!

n=0
until curl -s -o /dev/null "http://localhost:$PORT/state.json"; do
  n=$((n + 1))
  if [ "$n" -gt 40 ] || ! kill -0 "$WATCHER" 2>/dev/null; then
    echo "stopped: the watcher did not start on port $PORT."
    kill "$WATCHER" 2>/dev/null || true
    exit 1
  fi
  sleep 0.25
done

BG=""
if [ "${RA_TRIAL_BACKGROUND:-}" = 1 ]; then BG="-g"; fi
# All three come from the watcher, so it can say which tabs really loaded (and the card's
# Copy buttons work, which they may not from a file).
for target in "http://localhost:$PORT/guide.pdf" "http://localhost:$PORT/card" "http://localhost:$PORT/"; do
  # shellcheck disable=SC2086
  open $BG -a Firefox "$target"
  sleep 0.5
done
sleep 3
echo "asked Firefox for three tabs: the guide, the trial card, the live page (each \"opened in\" line above is a tab that loaded)."
echo "Now open Claude Desktop and follow the guide. Waiting; Ctrl-C when the trial is over."

# The first wait returns when Ctrl-C arrives; the second lets the watcher write timeline.html.
wait "$WATCHER" || true
kill -INT "$WATCHER" 2>/dev/null || true
wait "$WATCHER" 2>/dev/null || true
echo "to remove the trial plugin: in Claude Desktop click Plugins in the left sidebar, pick Research assistant and click Uninstall (then delete $DOWNLOADS/research-assistant-plugin.zip)"
