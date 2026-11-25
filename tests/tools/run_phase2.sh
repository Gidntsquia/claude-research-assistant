#!/bin/sh
# One phase-2 test run = one headless Claude launch (Sonnet, $4 and 60-turn caps).
#
#   tests/tools/run_phase2.sh RUN [--trial]
#
# RUN is <kind>-run<k>:
#   caprolace-run1..3, leprosy-adna-run1..3         prompt: https://doi.org/<doi>, then "show quotes"
#   caa-theory-run1..3, south-america-run1..3,
#   caprolace-scanned-run1..3                       the PDF in the folder; "Summarize <file>", then "show quotes"
#   paywalled-run1..3                               prompt: https://doi.org/10.1179/pan.2005.033
#   two-articles-run1..3                            caa-theory.pdf and south-america.pdf; "Summarize these two articles"
#   nohooks-caprolace-run1                          the Caprolace DOI with the no-hooks zip, then "show quotes"
#
# Both messages go to the same launch (tools/two_turns.py sends the second after the first reply).
# The workspace is a fresh scratch folder outside the repo holding folder-template/ and any PDF;
# it is deleted afterwards. A run that already has a result is skipped, so a list of runs can be
# started again after a refused launch. Scored runs need the skill committed and the zips built
# from it; --trial skips that check and writes to runs/summary/trials/.
# Afterwards: uv run tests/tools/score_phase2.py
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd)"                  # tests/
REPO="$(cd "$HERE/.." && pwd)"
TESTSET="$HERE/test-set"
RUN="${1:?usage: run_phase2.sh RUN [--trial]}"
TRIAL="${2:-}"
KIND="${RUN%-run*}"
OUTDIR="$HERE/runs/summary"
[ "$TRIAL" = "--trial" ] && OUTDIR="$HERE/runs/summary/trials"
OUT="$OUTDIR/$RUN"
ZIP="$REPO/dist/research-assistant-plugin.zip"
PDFS=""; SECOND="show quotes"
case "$KIND" in
  caprolace) PROMPT="https://doi.org/10.1371/journal.pone.0224435" ;;
  leprosy-adna) PROMPT="https://doi.org/10.1038/s41467-018-03857-x" ;;
  caa-theory) PDFS="caa-theory.pdf"; PROMPT="Summarize caa-theory.pdf" ;;
  south-america) PDFS="south-america.pdf"; PROMPT="Summarize south-america.pdf" ;;
  caprolace-scanned) PDFS="caprolace-scanned.pdf"; PROMPT="Summarize caprolace-scanned.pdf" ;;
  paywalled) PROMPT="https://doi.org/10.1179/pan.2005.033"; SECOND="" ;;
  two-articles) PDFS="caa-theory.pdf south-america.pdf"; PROMPT="Summarize these two articles"; SECOND="" ;;
  nohooks-caprolace) PROMPT="https://doi.org/10.1371/journal.pone.0224435"; ZIP="$REPO/dist/phase-2-plugin-nohooks.zip" ;;
  *) echo "unknown run $RUN" >&2; exit 2 ;;
esac
mkdir -p "$OUTDIR"
if [ -s "$OUT.jsonl" ] && grep -q '"type": *"result"' "$OUT.jsonl"; then
  echo "skip $RUN: already has a result"; exit 0
fi
# The zip must hold the skill as it is on disk, and for a scored run the skill must be committed.
if ! unzip -p "$ZIP" skills/article-summary/SKILL.md | cmp -s - "$REPO/plugin/skills/article-summary/SKILL.md"; then
  echo "the zip does not match skill/article-summary/SKILL.md: run uv run build_plugin.py first" >&2; exit 2
fi
if [ "$TRIAL" != "--trial" ] && ! git -C "$REPO" diff --quiet HEAD -- plugin dist; then
  echo "plugin or dist has uncommitted changes: commit before a scored run" >&2; exit 2
fi
COMMIT="$(git -C "$REPO" log -1 --format=%h -- plugin dist)"
BLOB="$(git -C "$REPO" hash-object plugin/skills/article-summary/SKILL.md | cut -c1-10)"
# Cowork's sandbox has Python with PDF libraries; this Mac's system Python has none.
VENV="$HERE/tools/.venv"
if [ ! -x "$VENV/bin/python3" ]; then
  uv venv -q "$VENV" && uv pip install -q --python "$VENV/bin/python3" pymupdf pypdf
fi
PATH="$VENV/bin:$PATH"; export PATH
WS="$(mktemp -d "${TMPDIR:-/tmp}/ra-phase2.XXXXXX")"
cp -R "$REPO/plugin/folder-template/." "$WS/"
for f in $PDFS; do cp "$TESTSET/$f" "$WS/"; done
rm -f "$OUT.notrun"
STARTED="$(TZ=America/New_York date '+%Y-%m-%d %-I:%M %p ET')"
echo "run  $RUN  ($STARTED)"
cd "$WS"
if [ -n "$SECOND" ]; then set -- "$PROMPT" "$SECOND"; else set -- "$PROMPT"; fi
python3 "$HERE/tools/two_turns.py" "$OUT.jsonl" "$@" -- \
  claude -p --input-format stream-json --output-format stream-json --verbose \
  --plugin-dir "$ZIP" --model sonnet --max-budget-usd 4 --max-turns 60 \
  --setting-sources project,local --permission-mode acceptEdits \
  --allowedTools "Read,Write,Edit,Glob,Grep,WebFetch,WebSearch,Skill,Bash(curl:*),Bash(ls:*),Bash(wc:*),Bash(mkdir:*),Bash(cp:*),Bash(date:*),Bash(python3:*),Bash(pdftotext:*)" \
  > "$OUT.log" 2>&1
cd "$HERE"
rm -rf "$WS"
if grep -q '"type": *"result"' "$OUT.jsonl" 2>/dev/null; then
  python3 "$HERE/tools/replies.py" "$OUT" "$@"
  printf '{"run": "%s", "prompt": "%s", "second": "%s", "zip": "%s", "skill_commit": "%s", "skill_blob": "%s", "started": "%s", "trial": %s}\n' \
    "$RUN" "$PROMPT" "$SECOND" "$(basename "$ZIP")" "$COMMIT" "$BLOB" "$STARTED" "$([ "$TRIAL" = "--trial" ] && echo true || echo false)" > "$OUT.meta.json"
  rm -f "$OUT.log"
elif grep -qi "usage-guard" "$OUT.log" "$OUT.jsonl" 2>/dev/null; then
  echo "daily cap" > "$OUT.notrun"; echo "     not run: daily cap"; rm -f "$OUT.jsonl"
else
  echo "no result" > "$OUT.notrun"; echo "     not run: no result, see $OUT.log"
fi
