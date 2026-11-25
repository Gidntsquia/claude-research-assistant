#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pymupdf"]
# ///
"""Score the plain-Claude baseline runs and write RESULTS.md.

    uv run tests/tools/score_baseline.py

For each <name>-run<k>.reply.md it works out what the run read (from the transcript),
runs tests/tools/check_summary.py with the matching --source, saves the checker's printout as
<name>-run<k>.check.txt and fills one row of the table. Nothing is typed in by hand.
"""
from __future__ import annotations

import contextlib
import io
import json
import pathlib
import re
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

TOOLS = pathlib.Path(__file__).resolve().parent
ROOT = TOOLS.parents[1]                          # the repo
HERE = ROOT / "tests" / "runs" / "baseline"      # this run set
sys.path.insert(0, str(TOOLS))
import check_summary as cs  # noqa: E402

ARTICLES = {
    "caprolace": "10.1371/journal.pone.0224435",
    "leprosy-adna": "10.1038/s41467-018-03857-x",
    "caa-theory": "10.5334/jcaa.263",
    "south-america": "10.1371/journal.pone.0232367",
}
RUNS = (1, 2, 3)
COLUMNS = [("opening", "opening"), ("detail-count", "detail count"), ("detail-length", "detail length"),
           ("pointer", "pointer"), ("no-quotes", "no quotes"), ("headings", "headings"), ("not-stated", '"not stated"')]
HARD = {"pointer"}                      # must pass 3 of 3 on every article
API_HOSTS = ("api.crossref.org", "api.openalex.org", "api.unpaywall.org", "europepmc/webservices", "eutils.ncbi")


def events(path):
    for line in open(path, encoding="utf-8"):
        with contextlib.suppress(json.JSONDecodeError):
            yield json.loads(line)


def source_read(jsonl: pathlib.Path) -> tuple[str, str]:
    """('PDF' | 'web page' | 'abstract' | 'nothing read', the evidence line), from the tool calls that succeeded."""
    calls, pdf, web, other = {}, None, None, None
    for e in events(jsonl):
        content = e.get("message", {}).get("content")
        if not isinstance(content, list):
            continue
        for c in content:
            if c.get("type") == "tool_use":
                calls[c["id"]] = (c["name"], c.get("input", {}))
            elif c.get("type") == "tool_result" and c.get("tool_use_id") in calls and not c.get("is_error"):
                name, inp = calls[c["tool_use_id"]]
                t = c.get("content")
                text = t if isinstance(t, str) else " ".join(x.get("text", "") for x in t or [] if isinstance(x, dict))
                target = str(inp.get("file_path") or inp.get("url") or inp.get("command") or "")
                if "REDIRECT DETECTED" in text or len(text) < 200:
                    continue
                is_pdf = (name == "Read" and target.lower().endswith(".pdf")) \
                    or (name == "WebFetch" and "application/pdf" in text[:400]) \
                    or (name == "Bash" and re.search(r"pymupdf|fitz|pypdf|pdftotext", target))
                if is_pdf:
                    pdf = pdf or f"{name} {target[:110]}"
                elif name == "WebFetch" and len(text) >= 2000 and not any(h in target for h in API_HOSTS):
                    web = web or f"{name} {target[:110]} ({len(text):,} characters returned)"
                elif name == "Bash" and "curl" in target and len(text) >= 2000 and not any(h in target for h in API_HOSTS):
                    web = web or f"curl {target[:110]} ({len(text):,} characters returned)"
                elif name in ("WebFetch", "WebSearch", "Bash"):
                    other = other or f"{name} {(target or str(inp.get('query', '')))[:110]}"
    if pdf:
        return "PDF", pdf
    if web:
        return "web page", web
    if other:
        return "abstract", f"no PDF or article page read; an index or search answered: {other}"
    return "nothing read", "no fetch of any kind succeeded in the transcript"


def score(name: str, k: int) -> dict:
    base = HERE / f"{name}-run{k}"
    notrun = base.with_suffix(".notrun")
    reply, jsonl = pathlib.Path(f"{base}.reply.md"), pathlib.Path(f"{base}.jsonl")
    if not reply.exists() or not jsonl.exists():
        why = notrun.read_text().strip() if notrun.exists() else "daily cap"
        return {"name": name, "k": k, "run": False, "why": why}
    src, evidence = source_read(jsonl)
    mode = "pdf" if src == "PDF" else "web"
    argv = [str(reply), "--pdf", str(ROOT / "tests" / "test-set" / f"{name}.pdf"),
            "--html", str(ROOT / "tests" / "test-set" / f"{name}.html"), "--source", mode]
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        cs.main(argv)
    out = buf.getvalue().replace(str(ROOT) + "/", "")
    cmd = (f"uv run tests/tools/check_summary.py tests/runs/baseline/{reply.name} --pdf tests/test-set/{name}.pdf "
           f"--html tests/test-set/{name}.html --source {mode}")
    pathlib.Path(f"{base}.check.txt").write_text(
        f"source read: {src}  <- {evidence}\n$ {cmd}\n{out}", encoding="utf-8")
    rules = {m.group(2): m.group(1) == "pass" for m in re.finditer(r"^(pass|FAIL)\s+([a-z-]+)", out, re.M)}
    cost = next((e.get("total_cost" "_usd") for e in events(jsonl) if e.get("type") == "result"), None)
    return {"name": name, "k": k, "run": True, "source": src, "rules": rules, "cost": cost,
            "result": out.strip().splitlines()[-1]}


def main() -> int:
    rows = [score(n, k) for n in ARTICLES for k in RUNS]
    done = [r for r in rows if r["run"]]
    now = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d, %-I:%M %p ET")
    L = ["# Baseline: plain Claude, no plugin", "",
         f"Scored {now} by `uv run tests/tools/score_baseline.py`. {len(done)} of 12 runs scored.", "",
         "Each run: one headless Claude session (Sonnet), no plugin, a fresh empty folder, the prompt exactly "
         "`Summarize this article for me. https://doi.org/<doi>`. The reply is what Claude wrote after its last tool call. "
         "The checker is `tests/tools/check_summary.py`; the rules are the short format phase 2 will build "
         "(2–3 sentence opening, 5–8 details of at most 25 words, a pointer on each, no quotes, at most 4 headings from the article, no \"not stated\"). "
         "A baseline that misses is a valid result: it is the gap the plugin has to close.", "",
         "| Run | Source read | " + " | ".join(label for _, label in COLUMNS) + " | Why |",
         "|---|---|" + "---|" * (len(COLUMNS) + 1)]
    for r in rows:
        tag = f"{r['name']}-run{r['k']}"
        if not r["run"]:
            L.append(f"| {tag} | not run: {r['why']} | " + " | ".join("–" for _ in COLUMNS) + " | |")
            continue
        cells = ["pass" if r["rules"].get(rule) else "**fail**" for rule, _ in COLUMNS]
        L.append(f"| [{tag}]({tag}.reply.md) | {r['source']} | " + " | ".join(cells) + f" | [checker output]({tag}.check.txt) |")

    L += ["", "## Passes of 3, per article", "", "Passes are counted out of the runs scored for that article.", "",
          "| Article | Runs scored | " + " | ".join(label for _, label in COLUMNS) + " |",
          "|---|---|" + "---|" * len(COLUMNS)]
    per = {}
    for n in ARTICLES:
        mine = [r for r in done if r["name"] == n]
        per[n] = {rule: sum(1 for r in mine if r["rules"].get(rule)) for rule, _ in COLUMNS}
        L.append(f"| {n} | {len(mine)} of 3 | " + " | ".join(f"{per[n][rule]} of {len(mine)}" for rule, _ in COLUMNS) + " |")

    L += ["", "## Passes of 12, per rule", ""]
    missing = 12 - len(done)
    for rule, label in COLUMNS:
        total = sum(per[n][rule] for n in ARTICLES)
        if rule in HARD:
            need, meets = "3 of 3 on every article", all(per[n][rule] == 3 for n in ARTICLES)
            can_still = all(per[n][rule] == len([r for r in done if r["name"] == n]) for n in ARTICLES)
        else:
            need = "2 of 3 on every article and 11 of 12 overall"
            meets = all(per[n][rule] >= 2 for n in ARTICLES) and total >= 11
            can_still = total + missing >= 11 and all(
                per[n][rule] + 3 - len([r for r in done if r["name"] == n]) >= 2 for n in ARTICLES)
        if meets:
            verdict = "meets"
        elif missing and can_still:
            verdict = f"not settled ({missing} runs not run)"
        else:
            verdict = "misses"
        L.append(f"- **{label}**: {total} of {len(done) if missing else 12}{' scored' if missing else ''} pass. Needs {need}: **{verdict}**.")

    srcs = {s: sum(1 for r in done if r["source"] == s) for s in ("PDF", "web page", "abstract", "nothing read")}
    costs = [r["cost"] for r in done if r["cost"] is not None]
    L += ["", "## What the runs read", "",
          f"- PDF: {srcs['PDF']} runs; web page: {srcs['web page']}; abstract only: {srcs['abstract']}; nothing read: {srcs['nothing read']}.",
          "- \"PDF\" means the transcript shows a successful read of a PDF; \"web page\" a successful fetch of the article's page; else \"abstract\" when an index or a search answered, and \"nothing read\" when no fetch succeeded at all (the reply is then not a summary). "
          "The first line of each checker output names the tool call that decided it.",
          "- A run that read the PDF is checked for `(p. N)` pointers; any other run for `(sec. \"Heading\")`, `(Fig. N)` or `(Table N)`."]
    if costs:
        L.append(f"- Cost of the {len(costs)} runs: ${sum(costs):.2f} in all, ${min(costs):.2f} to ${max(costs):.2f} each.")
    if missing:
        L += ["", f"{missing} rows read \"not run\". Start `tests/tools/run_baseline.sh` again (it skips finished runs), then this script."]
    L += ["", "## Reproduce one row", "", "```",
          "uv run tests/tools/check_summary.py tests/runs/baseline/caprolace-run1.reply.md --pdf tests/test-set/caprolace.pdf --html tests/test-set/caprolace.html --source web",
          "```", "", "Run it from the repo root. Use `--source pdf` for a row whose source read is PDF. The exact command for each row is the second line of its checker output.", ""]
    (HERE / "RESULTS.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L[6:6 + 2 + 12]))
    print(f"\nwrote {HERE / 'RESULTS.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
