#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Render one repeat's two conversations as a single page to read by eye.

    uv run tests/tools/render_walkthrough.py [K]        # repeat K (default 1) -> tests/runs/walkthrough.html

Top to bottom: conversation 1, then conversation 2 (a later session in the same folder), each
message followed by the reply the professor would see. The reply text is unchanged; the look is
that of runs/summary/caprolace-run1.html (render_html.py).
"""
import html
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from render_html import CSS, render          # noqa: E402
from score_conversations import replies      # noqa: E402

TESTS = pathlib.Path(__file__).resolve().parent.parent
RUNS = TESTS / "runs" / "conversations"
EXTRA = """
main{display:block;max-width:860px}
h2.conv{font-size:16px;margin:28px 0 4px} p.conv{margin:0 0 14px;color:#555;font-size:14px}
.turn{margin:0 0 22px} .msg{word-break:normal;max-width:100%;box-sizing:border-box}
.reply blockquote{margin:8px 0;padding-left:10px;border-left:3px solid #c9bfa8;color:#4a4436}
.reply table{border-collapse:collapse;margin:8px 0;font-size:14.5px} .reply td,.reply th{border:1px solid #ddd8cf;padding:3px 8px;text-align:left}
.reply ol{margin:4px 0 8px;padding-left:22px} .reply li{margin:6px 0}
.what{font-size:12.5px;color:#7a6a4a;margin:0 0 4px;text-transform:uppercase;letter-spacing:.04em}
"""
WHAT = {
    "c1": ["A link to an article: the short summary", "A request for the article's own sentences",
           "A complaint about that answer", "A request to change how it answers: saved, presets mentioned once",
           "The settings, listed"],
    "c2": ["A later session: recall of the subject", "A correction to what was remembered", "Forgetting it",
           "A new article: the summary is now shorter"],
}


def tables_and_lists(md: str) -> str:
    """render() knows headings, - lists, quotes and paragraphs; add Markdown tables and 1. lists."""
    out, block = [], []

    def flush():
        if block:
            out.append(render("\n".join(block)))
            block.clear()

    lines = md.splitlines()
    i = 0
    import re
    from render_html import inline
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1]):
            flush()
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            head, body = rows[0], rows[2:]
            out.append("<table><tr>" + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr>"
                       + "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in body) + "</table>")
            continue
        if re.match(r"^\d+\.\s+", line):
            flush()
            items = []
            while i < len(lines) and (re.match(r"^\d+\.\s+", lines[i]) or (lines[i].startswith("   ") and lines[i].strip())):
                if re.match(r"^\d+\.\s+", lines[i]):
                    items.append(re.sub(r"^\d+\.\s+", "", lines[i]))
                else:
                    items[-1] += " " + lines[i].strip()
                i += 1
            out.append("<ol>" + "".join(f"<li>{inline(x)}</li>" for x in items) + "</ol>")
            continue
        if line.strip() in ("---", "***"):
            flush()
            out.append("<hr>")
        else:
            block.append(line)
        i += 1
    flush()
    return "\n".join(out)


def main() -> int:
    k = sys.argv[1] if len(sys.argv) > 1 else "1"
    parts = []
    for conv, title in (("c1", "Conversation 1: a new, empty folder"), ("c2", "Conversation 2: a later session in the same folder")):
        base = RUNS / f"r{k}-{conv}"
        meta = json.loads(pathlib.Path(f"{base}.meta.json").read_text())
        rs = replies(pathlib.Path(f"{base}.jsonl"))
        parts.append(f'<h2 class="conv">{html.escape(title)}</h2><p class="conv">One headless Claude launch, '
                     f'{html.escape(meta["started"])}, plugin commit {html.escape(meta["plugin_commit"])}. '
                     f'{len(rs)} of {len(meta["messages"])} messages answered.</p>')
        for i, msg in enumerate(meta["messages"]):
            reply = rs[i] if i < len(rs) else "(no reply: the launch ended before this message)"
            what = WHAT[conv][i] if i < len(WHAT[conv]) else ""
            parts.append(f'<div class="turn"><div class="what">{html.escape(what)}</div>'
                         f'<div class="msg"><b>Professor:</b> {html.escape(msg)}</div>'
                         f'<div class="reply">{tables_and_lists(reply)}</div></div>')
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Walkthrough: two conversations with the research assistant</title><style>{CSS}{EXTRA}</style></head><body>
<header><h1>Walkthrough: what the professor would see (repeat {html.escape(k)})</h1>
<p>Two real conversations with the final plugin zip, run headless as the stand-in for Cowork. Messages in blue, replies in white; the reply text is unchanged. Scores for all repeats: tests/RESULTS.md.</p></header>
<main>
{chr(10).join(parts)}
</main>
<footer>Made by tests/tools/render_walkthrough.py from tests/runs/conversations/r{html.escape(k)}-c1 and r{html.escape(k)}-c2.</footer>
</body></html>
"""
    out = TESTS / "runs" / "walkthrough.html"
    out.write_text(page, encoding="utf-8")
    print("wrote", out.relative_to(TESTS.parent))
    return 0


if __name__ == "__main__":
    sys.exit(main())
