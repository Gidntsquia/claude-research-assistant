#!/usr/bin/env python3
"""Render one run's two replies as a page to judge by eye.

    python3 tests/tools/render_html.py tests/runs/summary/caprolace-run1      # writes tests/runs/summary/caprolace-run1.html

Left to right (or top to bottom on a narrow screen): the reply to the prompt, then the reply to
"show quotes". Only the Markdown the summary format uses is handled: # headings, - lists,
> quote lines under a list item, plain paragraphs.
"""
import html
import json
import pathlib
import re
import sys

POINTER = re.compile(r'(\((?:p\. ?\d+|sec\. [^)]*|Fig\. ?\d+\w*|Table ?\d+\w*|inference)\))\s*$')


def inline(text: str) -> str:
    t = html.escape(text, quote=False)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<!\*)\*(?!\*)(.+?)\*", r"<em>\1</em>", t)
    t = re.sub(r"`(.+?)`", r"<code>\1</code>", t)
    return POINTER.sub(r'<span class="ptr">\1</span>', t)


def render(md: str) -> str:
    out, in_list, item_open = [], False, False

    def close():
        nonlocal in_list, item_open
        if item_open:
            out.append("</li>")
        if in_list:
            out.append("</ul>")
        in_list = item_open = False

    for line in md.splitlines():
        if not line.strip():
            continue
        m = re.match(r"^(#{1,4})\s+(.*)$", line)
        if m:
            close()
            n = len(m.group(1))
            out.append(f"<h{n}>{inline(m.group(2))}</h{n}>")
        elif re.match(r"^[-*]\s+", line):
            if item_open:
                out.append("</li>")
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append("<li>" + inline(re.sub(r"^[-*]\s+", "", line)))
            item_open = True
        elif re.match(r"^\s*>\s?", line):
            q = inline(re.sub(r"^\s*>\s?", "", line))
            out.append(f'<div class="quote">{q}</div>' if item_open else f"<blockquote>{q}</blockquote>")
        else:
            close()
            out.append(f"<p>{inline(line.strip())}</p>")
    close()
    return "\n".join(out)


CSS = """
body{font:16px/1.5 -apple-system,"Segoe UI",Helvetica,Arial,sans-serif;color:#1c1c1c;background:#f4f2ee;margin:0;padding:24px}
header{max-width:1500px;margin:0 auto 16px} header h1{font-size:18px;margin:0 0 4px} header p{margin:0;color:#555;font-size:14px}
main{display:flex;gap:24px;max-width:1500px;margin:0 auto;align-items:flex-start;flex-wrap:wrap}
section{flex:1 1 520px;min-width:0}
.msg{font:14px ui-monospace,Menlo,monospace;background:#e3e9f2;border-radius:10px;padding:8px 12px;margin:0 0 10px;display:inline-block;word-break:break-all}
.msg b{font-family:-apple-system,sans-serif;font-weight:600;color:#445}
.reply{background:#fff;border:1px solid #ddd8cf;border-radius:10px;padding:18px 24px}
.reply h1{font-size:19px;line-height:1.3;margin:0 0 10px} .reply h2{font-size:15px;margin:18px 0 4px;color:#333}
.reply p{margin:8px 0} .reply ul{margin:4px 0 8px;padding-left:20px} .reply li{margin:6px 0}
.ptr{color:#777;font-size:13px;white-space:nowrap}
.quote{margin:3px 0 8px;padding-left:10px;border-left:3px solid #c9bfa8;color:#4a4436;font-size:14.5px;font-style:italic}
footer{max-width:1500px;margin:14px auto 0;color:#666;font-size:13px}
"""


def main() -> int:
    base = pathlib.Path(sys.argv[1])
    meta = json.loads(pathlib.Path(f"{base}.meta.json").read_text())
    first = pathlib.Path(f"{base}.reply.md").read_text(encoding="utf-8")
    second = pathlib.Path(f"{base}.quotes.md").read_text(encoding="utf-8")
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(base.name)}: the two replies</title><style>{CSS}</style></head><body>
<header><h1>{html.escape(base.name)}: what the professor would see</h1>
<p>One headless Claude launch, {html.escape(meta.get("started", ""))}, {html.escape(meta.get("zip", ""))}, skill commit {html.escape(meta.get("skill_commit", ""))}. Left: the reply to the link. Right: the reply to “show quotes”.</p></header>
<main>
<section><div class="msg"><b>Professor:</b> {html.escape(meta.get("prompt", ""))}</div><div class="reply">{render(first)}</div></section>
<section><div class="msg"><b>Professor:</b> {html.escape(meta.get("second", ""))}</div><div class="reply">{render(second)}</div></section>
</main>
<footer>Made by tools/render_html.py from {html.escape(base.name)}.reply.md and {html.escape(base.name)}.quotes.md; the text is unchanged.</footer>
</body></html>
"""
    pathlib.Path(f"{base}.html").write_text(page, encoding="utf-8")
    print(f"wrote {base}.html")
    return 0


if __name__ == "__main__":
    sys.exit(main())
