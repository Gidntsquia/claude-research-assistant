#!/bin/sh
# Plain-Claude baseline: each of the four test DOIs summarized 3 times with no plugin.
#
#   tests/tools/run_baseline.sh [NAME ...]        # default: all four articles
#
# 12 headless launches in all (Sonnet, $4 and 60-turn caps, set in tests/tools/run_session.sh).
# A run that already has a result is skipped, so the script can be started again after a
# refused launch or a stop. Each run gets a fresh scratch folder outside the repo.
# Afterwards: uv run tests/tools/score_baseline.py
set -u
TOOLS="$(cd "$(dirname "$0")" && pwd)"
RUNS="$TOOLS/../runs/baseline"
doi_of() {
  case "$1" in
    caprolace) echo "10.1371/journal.pone.0224435" ;;
    leprosy-adna) echo "10.1038/s41467-018-03857-x" ;;
    caa-theory) echo "10.5334/jcaa.263" ;;
    south-america) echo "10.1371/journal.pone.0232367" ;;
    *) echo "unknown article $1" >&2; exit 2 ;;
  esac
}
[ $# -gt 0 ] || set -- caprolace leprosy-adna caa-theory south-america
for name in "$@"; do
  doi="$(doi_of "$name")" || exit 2
  for k in 1 2 3; do
    out="$RUNS/$name-run$k"
    if [ -s "$out.jsonl" ] && grep -q '"type":"result"' "$out.jsonl"; then
      echo "skip $name run $k: already has a result"; continue
    fi
    rm -f "$out.notrun"
    ws="$(mktemp -d "${TMPDIR:-/tmp}/ra-baseline.XXXXXX")"
    echo "run  $name run $k  ($(TZ=America/New_York date '+%-I:%M %p ET'))"
    "$TOOLS/run_session.sh" "$ws" "$out" "Summarize this article for me. https://doi.org/$doi" --no-plugin > "$out.log" 2>&1
    rm -rf "$ws"
    if grep -q '"type":"result"' "$out.jsonl" 2>/dev/null; then
      python3 "$TOOLS/transcript.py" --final "$out.jsonl" > "$out.reply.md"
      rm -f "$out.log"
    elif grep -qi "usage-guard" "$out.log" "$out.jsonl" 2>/dev/null; then
      echo "daily cap" > "$out.notrun"; echo "     not run: daily cap"
      rm -f "$out.jsonl" "$out.md"
    else
      echo "no result" > "$out.notrun"; echo "     not run: no result, see $out.log"
    fi
  done
done
