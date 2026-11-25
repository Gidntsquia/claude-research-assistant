#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pymupdf"]
# ///
"""Score the phase-2 runs with the checker and write tests/runs/summary/RESULTS.md.

    uv run tests/tools/score_phase2.py                 # score tests/runs/summary/
    uv run tests/tools/score_phase2.py --archive N     # move the 15 scored runs to round-N/ and score them there
    uv run tests/tools/score_phase2.py --dir tests/runs/summary/round-1

For each scored run it works out which copy was read (from the transcript), runs
tests/tools/check_summary.py on the first reply and, with --quotes, on the
"show quotes" reply, saves both printouts beside the reply and fills one table row.
Nothing in RESULTS.md is typed by hand.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import pathlib
import re
import shutil
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

TESTS = pathlib.Path(__file__).resolve().parents[1]              # tests/
HERE = TESTS / "runs" / "summary"                               # the summary and its runs
P1 = TESTS                                                      # test-set/ and runs/baseline/
sys.path.insert(0, str(TESTS / "tools"))
import check_summary as cs  # noqa: E402
from score_baseline import source_read as _p1_source_read  # noqa: E402  (the same "what was read" test as the baseline)


def source_read(jsonl: pathlib.Path) -> tuple[str, str]:
    """Phase 1's test, given only the events it was written for: newer Claude Code versions add
    system events whose `message` is a plain string (permission notices), which it cannot take."""
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", encoding="utf-8", delete=False) as t:
        for line in jsonl.read_text(encoding="utf-8").splitlines():
            with contextlib.suppress(json.JSONDecodeError):
                if isinstance(json.loads(line).get("message", {}), dict):
                    t.write(line + "\n")
    try:
        src, evidence = _p1_source_read(pathlib.Path(t.name))
    finally:
        pathlib.Path(t.name).unlink()
    if src == "PDF":
        return src, evidence
    # Phase 1's test wants 200 characters back from the call that read the PDF. A run that writes the
    # pages to text files and then reads those returns almost nothing from that call, so look for it here:
    # a successful command that ran a PDF library on a .pdf, or a successful Read of a .pdf.
    # Also a PDF read: a successful command on a .pdf that runs a script the run itself wrote with a PDF library in it.
    calls, pdf_scripts = {}, set()
    for line in jsonl.read_text(encoding="utf-8").splitlines():
        with contextlib.suppress(json.JSONDecodeError):
            msg = json.loads(line).get("message")
            for c in (msg.get("content") if isinstance(msg, dict) and isinstance(msg.get("content"), list) else []):
                if c.get("type") == "tool_use":
                    calls[c["id"]] = (c["name"], c.get("input", {}))
                    inp = c.get("input", {})
                    if c["name"] == "Write" and inp.get("file_path") and re.search(r"pymupdf|fitz|pypdf", str(inp.get("content", ""))):
                        pdf_scripts.add(str(inp["file_path"]))
                elif c.get("type") == "tool_result" and c.get("tool_use_id") in calls and not c.get("is_error"):
                    name, inp = calls[c["tool_use_id"]]
                    target = str(inp.get("file_path") or inp.get("command") or "")
                    if (name == "Read" and target.lower().endswith(".pdf")) or (
                            name == "Bash" and ".pdf" in target.lower() and (
                                re.search(r"pymupdf|fitz|pypdf|pdftotext", target) or any(sc in target for sc in pdf_scripts))):
                        return "PDF", f"{name} {target[:110]} (pages written to files or read directly)"
    if src != "web page":
        # Phase 1 counts every Europe PMC address as an index. Its fullTextXML endpoint returns the
        # whole article, so a successful fetch of it that printed text back is a read of the web text.
        for line in jsonl.read_text(encoding="utf-8").splitlines():
            with contextlib.suppress(json.JSONDecodeError):
                msg = json.loads(line).get("message")
                for c in (msg.get("content") if isinstance(msg, dict) and isinstance(msg.get("content"), list) else []):
                    if c.get("type") == "tool_result" and c.get("tool_use_id") in calls and not c.get("is_error"):
                        name, inp = calls[c["tool_use_id"]]
                        target = str(inp.get("url") or inp.get("command") or "")
                        t = c.get("content")
                        text = t if isinstance(t, str) else " ".join(x.get("text", "") for x in t or [] if isinstance(x, dict))
                        if "fullTextXML" in target and len(text) >= 200:
                            return "web page", f"{name} {' '.join(target.split())[:110]} (Europe PMC full text; no PDF could be downloaded)"
    return src, evidence

SCORED = ["caprolace", "leprosy-adna", "caa-theory", "south-america", "caprolace-scanned"]
BY_DOI = {"caprolace", "leprosy-adna", "nohooks-caprolace"}
ARTICLE = {"caprolace-scanned": "caprolace", "nohooks-caprolace": "caprolace"}   # whose PDF and web page to check against
RUNS = (1, 2, 3)
FORMAT = [("opening", "opening"), ("detail-count", "detail count"), ("detail-length", "detail length"),
          ("pointer", "pointer"), ("no-quotes", "no quotes"), ("headings", "headings"), ("not-stated", '"not stated"')]
EXTRA = [("quote-match", "quote match"), ("same-details", "same details")]
COLUMNS = FORMAT + EXTRA
HARD = {"pointer", "quote-match"}       # 3 of 3 on every article
SCAN_LINE = "Scanned pages: quotes may contain reading errors"
PAYWALL_LINE = "This article is paywalled: OpenAlex lists no open copy."
SUFFIXES = [".jsonl", ".md", ".reply.md", ".quotes.md", ".meta.json", ".check.txt", ".quotes.check.txt",
            ".reply.noscan.md", ".quotes.noscan.md", ".notrun", ".log"]


def rel(p: pathlib.Path) -> str:
    """A path as typed from tests/runs/summary/."""
    p = p.resolve()
    try:
        return str(p.relative_to(HERE))
    except ValueError:
        return "../" + str(p.relative_to(HERE.parent))


def run_checker(summary: pathlib.Path, article: str, mode: str, quotes: bool) -> tuple[str, str, dict]:
    pdf, html = P1 / "test-set" / f"{article}.pdf", P1 / "test-set" / f"{article}.html"
    argv = [str(summary), "--pdf", str(pdf), "--html", str(html), "--source", mode] + (["--quotes"] if quotes else [])
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        cs.main(argv)
    out = buf.getvalue().replace(str(summary), rel(summary))
    cmd = (f"uv run ../../tools/check_summary.py {rel(summary)} --pdf {rel(pdf)} --html {rel(html)} "
           f"--source {mode}" + (" --quotes" if quotes else ""))
    rules = {m.group(2): m.group(1) == "pass" for m in re.finditer(r"^(pass|FAIL)\s+([a-z-]+)", out, re.M)}
    return cmd, out, rules


def set_scan_line_aside(src: pathlib.Path, dst: pathlib.Path) -> bool:
    """Write src without its scan line to dst; True when the reply's first line was the scan line."""
    lines = src.read_text(encoding="utf-8").splitlines()
    first = next((i for i, l in enumerate(lines) if l.strip()), None)
    had = first is not None and cs.strip_md(lines[first]).strip().rstrip(".") == SCAN_LINE
    kept = [l for l in lines if cs.strip_md(l).strip().rstrip(".") != SCAN_LINE]
    dst.write_text("\n".join(kept) + "\n", encoding="utf-8")
    return had


def cost_of(jsonl: pathlib.Path):
    cost = None
    for line in jsonl.read_text(encoding="utf-8").splitlines():
        with contextlib.suppress(json.JSONDecodeError):
            e = json.loads(line)
            if e.get("type") == "result" and e.get("total_cost" "_usd") is not None:
                cost = e["total_cost" "_usd"]
    return cost


def score(d: pathlib.Path, kind: str, k: int) -> dict:
    tag = f"{kind}-run{k}"
    base = d / tag
    reply, quotes, jsonl = d / f"{tag}.reply.md", d / f"{tag}.quotes.md", d / f"{tag}.jsonl"
    row = {"kind": kind, "k": k, "tag": tag}
    if not reply.exists() or not jsonl.exists():
        notrun = d / f"{tag}.notrun"
        return row | {"run": False, "why": notrun.read_text().strip() if notrun.exists() else "not started"}
    meta = json.loads((d / f"{tag}.meta.json").read_text()) if (d / f"{tag}.meta.json").exists() else {}
    article = ARTICLE.get(kind, kind)
    if kind in BY_DOI:
        src, evidence = source_read(jsonl)
    else:
        src, evidence = "PDF", "the PDF was in the folder"
        seen, _ = source_read(jsonl)
        if seen != "PDF":
            src, evidence = "PDF (no read seen)", "the PDF was in the folder, but the transcript shows no successful read of it"
    evidence = " ".join(evidence.split())
    mode = "pdf" if src.startswith("PDF") else "web"
    notes = []
    target, qtarget = reply, quotes
    if kind == "caprolace-scanned":
        target = d / f"{tag}.reply.noscan.md"
        had = set_scan_line_aside(reply, target)
        notes.append("scan line first: " + ("yes" if had else "**no**"))
        if quotes.exists():
            qtarget = d / f"{tag}.quotes.noscan.md"
            set_scan_line_aside(quotes, qtarget)
    cmd, out, rules = run_checker(target, article, mode, False)
    (d / f"{tag}.check.txt").write_text(f"source read: {src}  <- {evidence}\n$ {cmd}\n{out}", encoding="utf-8")
    first = cs.parse_summary(target.read_text(encoding="utf-8"))
    n_inf = sum(1 for x in first.details if x.inference)
    notes.append(f"{len(first.details)} details" + (f", {n_inf} inference" if n_inf else "") + ("" if n_inf <= 2 else " (**over 2**)"))
    if quotes.exists() and quotes.read_text(encoding="utf-8").strip():
        qcmd, qout, qrules = run_checker(qtarget, article, mode, True)
        second = cs.parse_summary(qtarget.read_text(encoding="utf-8"))
        a, b = [cs.squash(x.body) for x in first.details], [cs.squash(x.body) for x in second.details]
        same = sum(1 for x, y in zip(a, b) if x == y)
        rules["quote-match"] = qrules.get("quote-match", False)
        rules["same-details"] = a == b and bool(a)
        n_q = len([x for x in second.details if not x.inference])
        bad = len(re.findall(r"^FAIL \[quote-match\]", qout, re.M))
        (d / f"{tag}.quotes.check.txt").write_text(
            f"source read: {src}  <- {evidence}\n$ {qcmd}\n{qout}"
            f"same details as the first reply: {same} of {len(a)} word for word ({len(b)} details in this reply)\n", encoding="utf-8")
        notes.append(f"quotes: {max(n_q - bad, 0)} of {n_q} found on the cited page" if n_q else "quotes: none")
        row["quotes"] = True
    else:
        rules["quote-match"] = rules["same-details"] = None
        row["quotes"] = False
    return row | {"run": True, "source": src, "rules": rules, "cost": cost_of(jsonl), "meta": meta, "notes": "; ".join(notes)}


def baseline() -> dict:
    """Passes per article and rule in phase 1's plain-Claude baseline, read from its checker printouts."""
    out = {}
    for name in ("caprolace", "leprosy-adna", "caa-theory", "south-america"):
        out[name] = {"n": 0} | {r: 0 for r, _ in FORMAT}
        for k in RUNS:
            f = P1 / "runs" / "baseline" / f"{name}-run{k}.check.txt"
            if not f.exists():
                continue
            out[name]["n"] += 1
            for m in re.finditer(r"^(pass|FAIL)\s+([a-z-]+)", f.read_text(encoding="utf-8"), re.M):
                if m.group(1) == "pass" and m.group(2) in out[name]:
                    out[name][m.group(2)] += 1
    return out


def cell(v) -> str:
    return "pass" if v else ("not asked" if v is None else "**fail**")


def verdicts(rows: list[dict]) -> list[tuple[str, str, int, int, str, str]]:
    done = [r for r in rows if r["run"]]
    missing = len(rows) - len(done)
    res = []
    for rule, label in FORMAT + EXTRA[:1]:
        per = {k: [r for r in done if r["kind"] == k] for k in SCORED}
        passes = {k: sum(1 for r in per[k] if r["rules"].get(rule)) for k in SCORED}
        total = sum(passes.values())
        if rule in HARD:
            need = "3 of 3 on every article"
            meets = all(passes[k] == 3 for k in SCORED)
            can = all(passes[k] == len(per[k]) for k in SCORED)
        else:
            need = "2 of 3 on every article and 13 of 15 overall"
            meets = all(passes[k] >= 2 for k in SCORED) and total >= 13
            can = total + missing >= 13 and all(passes[k] + 3 - len(per[k]) >= 2 for k in SCORED)
        v = "meets" if meets else (f"not settled ({missing} runs not run)" if missing and can else "misses")
        res.append((rule, label, total, len(done), need, v))
    return res


def scored_section(d: pathlib.Path, title: str) -> tuple[list[str], list[dict], list]:
    rows = [score(d, kind, k) for kind in SCORED for k in RUNS]
    done = [r for r in rows if r["run"]]
    base = baseline()
    L = [f"## {title}", ""]
    versions = sorted({(r["meta"].get("skill_commit"), r["meta"].get("skill_blob")) for r in done})
    if len(versions) == 1:
        L.append(f"Skill version for all {len(done)} runs: commit `{versions[0][0]}` (`skill/article-summary/SKILL.md` blob `{versions[0][1]}`), "
                 "built into `dist/phase-2-plugin.zip`.")
    elif versions:
        L.append("**The runs do not share one skill version:** " + ", ".join(f"commit `{c}` (blob `{b}`)" for c, b in versions) + ".")
    L += ["",
          "| Run | Source read | " + " | ".join(label for _, label in COLUMNS) + " | Notes | Checker output |",
          "|---|---|" + "---|" * (len(COLUMNS) + 2)]
    for r in rows:
        if not r["run"]:
            L.append(f"| {r['tag']} | not run: {r['why']} | " + " | ".join("–" for _ in COLUMNS) + " | | |")
            continue
        cells = [cell(r["rules"].get(rule)) for rule, _ in COLUMNS]
        links = f"[first reply]({r['tag']}.check.txt)" + (f", [quotes reply]({r['tag']}.quotes.check.txt)" if r["quotes"] else "")
        name = f"[{r['tag']}]({r['tag']}.reply.md)" + (f" · [quotes]({r['tag']}.quotes.md)" if r["quotes"] else "") + f" · [transcript]({r['tag']}.md)"
        L.append(f"| {name} | {r['source']} | " + " | ".join(cells) + f" | {r['notes']} | {links} |")

    L += ["", "### Passes of 3 per article, with the plain-Claude baseline beside each", "",
          "Each cell: this skill, then the baseline (`../baseline/RESULTS.md`: the same article by DOI, no plugin). "
          "The baseline never asked for quotes and never ran the scanned copy, so those cells have none.", "",
          "| Article | Runs scored | " + " | ".join(label for _, label in COLUMNS) + " |",
          "|---|---|" + "---|" * len(COLUMNS)]
    for k in SCORED:
        mine = [r for r in done if r["kind"] == k]
        cells = []
        for rule, _ in COLUMNS:
            p = sum(1 for r in mine if r["rules"].get(rule))
            b = base.get(k)
            cells.append(f"{p} of {len(mine)}" + (f" (baseline {b[rule]} of {b['n']})" if b and rule in b else ""))
        L.append(f"| {k} | {len(mine)} of 3 | " + " | ".join(cells) + " |")

    V = verdicts(rows)
    L += ["", "### Pass rules", ""]
    btot = {rule: (sum(base[a][rule] for a in base), sum(base[a]["n"] for a in base)) for rule, _ in FORMAT}
    for rule, label, total, n, need, v in V:
        b = f" Baseline: {btot[rule][0]} of {btot[rule][1]}." if rule in btot else " Baseline: not asked."
        L.append(f"- **{label}**: {total} of {n} pass. Needs {need}: **{v}**.{b}")
    same = sum(1 for r in done if r["rules"].get("same-details"))
    asked = sum(1 for r in done if r["quotes"])
    L.append(f"- same details (not one of the plan's pass rules, shown for requirement 3): in {same} of {asked} quote replies the details "
             "repeat the first reply word for word.")
    costs = [r["cost"] for r in done if r["cost"] is not None]
    if costs:
        L += ["", f"Cost of the {len(costs)} runs: ${sum(costs):.2f} in all, ${min(costs):.2f} to ${max(costs):.2f} each."]
    return L, rows, V


# ---------- extra runs ----------

def paywalled_row(d: pathlib.Path, k: int) -> str:
    tag = f"paywalled-run{k}"
    reply = d / f"{tag}.reply.md"
    if not reply.exists():
        why = (d / f"{tag}.notrun").read_text().strip() if (d / f"{tag}.notrun").exists() else "not started"
        return f"| {tag} | not run: {why} | – | – | – | – |"
    text = reply.read_text(encoding="utf-8")
    lines = [l for l in text.splitlines() if l.strip()]
    first = cs.strip_md(lines[0]).strip() == PAYWALL_LINE if lines else False
    s = cs.parse_summary(text)
    pointers = len(cs.ANY_PTR.findall(text))
    abstract = bool(re.search(r"\babstract\b", text, re.I)) and cs.words(text) > 80
    asks = bool(re.search(r"\bPDF\b", text))
    yn = lambda v: "yes" if v else "**no**"  # noqa: E731
    return (f"| [{tag}]({tag}.reply.md) · [transcript]({tag}.md) | {yn(first)} | {yn(abstract)} | {yn(asks)} | "
            f"{'none' if not s.details and not pointers else f'**{len(s.details)} list items, {pointers} pointers**'} | "
            f"{'none' if not s.headings else '**' + ' / '.join(s.headings) + '**'} |")


def two_articles_row(d: pathlib.Path, k: int) -> str:
    tag = f"two-articles-run{k}"
    reply = d / f"{tag}.reply.md"
    if not reply.exists():
        why = (d / f"{tag}.notrun").read_text().strip() if (d / f"{tag}.notrun").exists() else "not started"
        return f"| {tag} | not run: {why} | – | – | – | – | – |"
    text = reply.read_text(encoding="utf-8")
    m = re.search(r"^#{1,6}\s*Across these articles\s*$", text, re.M | re.I)
    body, across = (text[:m.start()], text[m.end():]) if m else (text, "")
    parts = [p for p in re.split(r"(?m)^(?=#\s)", body) if p.strip().startswith("# ")]
    names, fmt = [], []
    for i, part in enumerate(parts, 1):
        head = part.splitlines()[0].lower()
        art = "caa-theory" if ("theory" in head or "rajala" in head) else ("south-america" if ("south america" in head or "souza" in head) else None)
        names.append(art or "?")
        if art:
            f = d / f"{tag}.part{i}.md"
            f.write_text(part.strip() + "\n", encoding="utf-8")
            cmd, out, rules = run_checker(f, art, "pdf", False)
            (d / f"{tag}.part{i}.check.txt").write_text(f"$ {cmd}\n{out}", encoding="utf-8")
            ok = sum(1 for r, _ in FORMAT if rules.get(r))
            fmt.append(f"[{art}: {ok} of {len(FORMAT)} rules]({tag}.part{i}.check.txt)")
    points = [l for l in across.splitlines() if re.match(r"^\s*[-*+•]\s+", l)]
    both = [l for l in points if re.search(r"rajala", l, re.I) and re.search(r"souza", l, re.I)
            and len(re.findall(r"\bpp?\.\s*\d+", l)) >= 2]
    yn = lambda v: "yes" if v else "**no**"  # noqa: E731
    return (f"| [{tag}]({tag}.reply.md) · [transcript]({tag}.md) | {len(parts)} ({', '.join(names)}) | {yn(bool(m))} | "
            f"{len(points)} | {len(both)} of {len(points)} | {'; '.join(fmt) or '–'} | "
            f"{'yes' if len(parts) == 2 and m and points and len(both) == len(points) else '**no**'} |")


def extras_section(d: pathlib.Path) -> list[str]:
    L = ["## Extra runs", "",
         "### Paywalled DOI (10.1179/pan.2005.033), three times", "",
         f"Written: the first line is exactly `{PAYWALL_LINE}`, then title, abstract and a request for the PDF, and no key details.", "",
         "| Run | Paywalled line first | Abstract given | Asks for the PDF | Key details | Headings |", "|---|---|---|---|---|---|"]
    L += [paywalled_row(d, k) for k in RUNS]
    L += ["", "### Two PDFs in the folder (`caa-theory.pdf`, `south-america.pdf`), prompt `Summarize these two articles`, three times", "",
          "Written: one summary each, then `## Across these articles` with every point pointing into both articles (both authors named, a page from each).", "",
          "| Run | Summaries | \"Across these articles\" | Points | Pointing into both | Each summary against the format rules | As written |",
          "|---|---|---|---|---|---|---|"]
    L += [two_articles_row(d, k) for k in RUNS]
    first = d / "two-articles-first"
    if first.exists():
        fm = [json.loads(f.read_text()).get("skill_commit") for f in sorted(first.glob("*.meta.json"))]
        L += ["", f"First try, kept in `two-articles-first/` (skill commit `{fm[0] if fm else '?'}`): the skill then allowed one line "
              "saying the articles address different questions, and all three runs gave that line and no points. "
              "The skill's several-articles paragraph was changed and the three runs repeated (the rows above).", "",
              "| Run | Summaries | \"Across these articles\" | Points | Pointing into both | Each summary against the format rules | As written |",
              "|---|---|---|---|---|---|---|"]
        L += [two_articles_row(first, k).replace("](two-articles-run", "](two-articles-first/two-articles-run") for k in RUNS]
    L += ["", "### Caprolace by DOI with the no-hooks zip (`dist/phase-2-plugin-nohooks.zip`), once", "",
          "Written: the format holds from the skill and the folder's `CLAUDE.md` alone.", "",
          "| Run | Source read | " + " | ".join(label for _, label in COLUMNS) + " | Notes | Checker output |",
          "|---|---|" + "---|" * (len(COLUMNS) + 2)]
    r = score(d, "nohooks-caprolace", 1)
    if not r["run"]:
        L.append(f"| {r['tag']} | not run: {r['why']} | " + " | ".join("–" for _ in COLUMNS) + " | | |")
    else:
        cells = [cell(r["rules"].get(rule)) for rule, _ in COLUMNS]
        links = f"[first reply]({r['tag']}.check.txt)" + (f", [quotes reply]({r['tag']}.quotes.check.txt)" if r["quotes"] else "")
        name = f"[{r['tag']}]({r['tag']}.reply.md)" + (f" · [quotes]({r['tag']}.quotes.md)" if r["quotes"] else "") + f" · [transcript]({r['tag']}.md)"
        L.append(f"| {name} | {r['source']} | " + " | ".join(cells) + f" | {r['notes']} | {links} |")
        hooks = "hook" in (d / f"{r['tag']}.md").read_text(encoding="utf-8").split("**Professor:**")[1].split("**Claude:**")[0]
        L += ["", f"Hook output in this run's transcript: {'**present**' if hooks else 'none (as intended)'}."]
    metas = [json.loads(f.read_text()) for f in sorted(d.glob("*.meta.json"))
             if f.name.startswith(("paywalled", "two-articles", "nohooks"))]
    by = {}
    for m in metas:
        if m.get("skill_commit"):
            by.setdefault(m["run"].rsplit("-run", 1)[0], set()).add(m["skill_commit"])
    if by:
        L += ["", "Skill version of the extra runs: " + "; ".join(
            f"{kind} commit " + ", ".join(f"`{v}`" for v in sorted(vs)) for kind, vs in by.items()) + "."]
    return L


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(HERE))
    ap.add_argument("--archive", type=int, help="move the scored runs to round-N/ first")
    a = ap.parse_args()
    top = HERE
    d = pathlib.Path(a.dir).resolve()
    if a.archive:
        d = top / f"round-{a.archive}"
        d.mkdir(exist_ok=True)
        for kind in SCORED:
            for k in RUNS:
                for suf in SUFFIXES:
                    f = top / f"{kind}-run{k}{suf}"
                    if f.exists():
                        shutil.move(str(f), str(d / f.name))
    now = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d, %-I:%M %p ET")
    is_round = d != top
    earlier = sorted(p for p in top.glob("round-*") if (p / "RESULTS.md").exists()) if not is_round else []
    n_round = len(earlier) + 1
    title = ((f"Round {d.name.split('-')[1]} (an earlier round, kept)" if d.name.startswith("round-") else f"Runs in {d.name}/ (not the scored set)")
             if is_round else f"The 15 scored runs (round {n_round})")
    sec, rows, V = scored_section(d, title)
    done = [r for r in rows if r["run"]]
    L = ["# Phase 2 results: the short summary" + (f", {d.name}" if is_round else ""), "",
         f"Scored {now} by `uv run tests/tools/score_phase2.py`. {len(done)} of 15 runs scored. A script-made table; nothing is typed in.", "",
         "Each run is one headless Claude launch (Sonnet) with the phase-2 plugin zip, in a fresh scratch folder holding "
         "`folder-template/` and, for the PDF runs, the PDF. Two messages go to the same launch: the prompt, then `show quotes`. "
         "Prompts: `https://doi.org/<doi>` for caprolace and leprosy-adna; `Summarize <file>` for caa-theory, south-america and caprolace-scanned. "
         "The checker is `check_summary.py`: the first reply against the format rules, the second with `--quotes` "
         "(every quote found word for word on its cited page). \"Same details\" is this script's own test: the details of the second reply "
         "are the details of the first, word for word. On the scanned copy the scan-warning line is set aside before checking, and the "
         "quotes are checked against the text of the original `caprolace.pdf`.", ""]
    L += sec
    if not is_round:
        L += [""] + extras_section(d)
        trials = sorted((d / "trials").glob("*.meta.json")) if (d / "trials").exists() else []
        L += ["", "## Earlier rounds and trial launches", ""]
        for p in earlier:
            vline = [l for l in (p / "RESULTS.md").read_text(encoding="utf-8").splitlines() if l.startswith("- **")]
            miss = [re.match(r"- \*\*(.+?)\*\*", l).group(1) for l in vline if "**misses**" in l]
            L.append(f"- [{p.name}]({p.name}/RESULTS.md): " + ("missed " + ", ".join(miss) if miss else "no rule missed") + ".")
        if not earlier:
            L.append("- No earlier round.")
        L.append(f"- Trial launches (not scored, in `trials/`): {len(trials)}"
                 + (": " + ", ".join(f"[{t.name[:-10]}](trials/{t.name[:-10]}.reply.md)" for t in trials) if trials else "") + ".")
    missing = 15 - len(done)
    if missing:
        L += ["", f"{missing} scored rows read \"not run\". Start each with `tests/tools/run_phase2.sh <run>` (a finished run is skipped), then this script."]
    L += ["", "## Reproduce one row", "", "From `tests/runs/summary/`:", "", "```"]
    ex = next((r for r in done if r["tag"] == "caprolace-run1"), done[0] if done else None)
    if ex:
        for f in (f"{ex['tag']}.check.txt", f"{ex['tag']}.quotes.check.txt"):
            if (d / f).exists():
                L.append((d / f).read_text(encoding="utf-8").splitlines()[1][2:])
    L += ["```", "", "The exact command for every row is the second line of its checker output.", ""]
    (d / "RESULTS.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(l for l in L if l.startswith(("| ", "- **"))))
    print(f"\nwrote {d / 'RESULTS.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
