#!/usr/bin/env python3
"""Turn one run's event stream into the files the scorer and a reader use.

    replies.py RUN_BASENAME "first message" ["second message"]

Reads RUN_BASENAME.jsonl and writes:
  RUN_BASENAME.jsonl      the same events with image data removed (a scanned PDF adds megabytes of it)
  RUN_BASENAME.md         readable transcript: each message, the tool calls, what Claude said
  RUN_BASENAME.reply.md   the reply to the first message: what Claude wrote after its last tool call
  RUN_BASENAME.quotes.md  the reply to the second message, when there was one
"""
import json
import pathlib
import sys


def slim(x):
    if isinstance(x, str):
        if len(x) > 5000 and " " not in x[:300] and "\n" not in x[:300]:
            return f"[{len(x):,} characters of image or file data removed]"
        return x
    if isinstance(x, list):
        return [slim(v) for v in x]
    if isinstance(x, dict):
        return {k: slim(v) for k, v in x.items()}
    return x


def brief(inp: dict) -> str:
    for key in ("file_path", "url", "command", "pattern", "skill", "path", "query", "description"):
        if key in inp:
            extra = f" pages={inp['pages']}" if "pages" in inp else ""
            return f"{key}={str(inp[key])[:160]}{extra}"
    return json.dumps(inp)[:160]


def main() -> int:
    base, messages = sys.argv[1], sys.argv[2:]
    path = pathlib.Path(base + ".jsonl")
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            events.append(slim(json.loads(line)))
        except json.JSONDecodeError:
            pass
    path.write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in events), encoding="utf-8")

    turns, cur = [], []
    for e in events:
        cur.append(e)
        if e.get("type") == "result":
            turns.append(cur)
            cur = []
    out = []
    init = next((e for e in events if e.get("type") == "system" and e.get("subtype") == "init"), {})
    out.append(f"_Session {init.get('session_id')} | model {init.get('model')} | "
               f"plugins {[p.get('name') for p in init.get('plugins', [])]}_\n")
    finals = []
    for i, turn in enumerate(turns):
        out.append(f"**Professor:**\n\n{messages[i] if i < len(messages) else ''}\n")
        texts = []
        for e in turn:
            t = e.get("type")
            if t == "system" and "hook" in str(e.get("subtype", "")):
                text = (e.get("stdout") or e.get("output") or "").strip()
                if text:
                    out.append("> hook printed: " + text[:300].replace("\n", " ") + ("…" if len(text) > 300 else "") + "\n")
            elif t == "assistant" and not e.get("parent_tool_use_id"):
                for c in e["message"].get("content", []):
                    if c.get("type") == "text" and c["text"].strip():
                        out.append(f"**Claude:**\n\n{c['text'].strip()}\n")
                        texts.append(c["text"].strip())
                    elif c.get("type") == "tool_use":
                        out.append(f"> tool: {c['name']} {brief(c.get('input', {}))}\n")
                        texts = []
            elif t == "result":
                out.append(f"_Result: {e.get('subtype')} | turns {e.get('num_turns')} | "
                           f"cost so far ${e.get('total_cost' '_usd') or 0:.2f}_\n")
        finals.append("\n\n".join(texts))
    pathlib.Path(base + ".md").write_text("\n".join(out), encoding="utf-8")
    if finals:
        pathlib.Path(base + ".reply.md").write_text(finals[0] + "\n", encoding="utf-8")
    if len(finals) > 1:
        pathlib.Path(base + ".quotes.md").write_text(finals[1] + "\n", encoding="utf-8")
    print(f"{pathlib.Path(base).name}: {len(turns)} turn(s); reply {len(finals[0]) if finals else 0} characters"
          + (f"; quotes reply {len(finals[1])} characters" if len(finals) > 1 else ""))
    return 0 if turns else 1


if __name__ == "__main__":
    sys.exit(main())
