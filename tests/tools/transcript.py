#!/usr/bin/env python3
"""Turn a `claude -p --output-format stream-json` event file into a readable transcript.

    transcript.py EVENTS.jsonl "the prompt" > transcript.md
    transcript.py --reply EVENTS.jsonl      > everything Claude said in the turn, in order
    transcript.py --final EVENTS.jsonl      > what Claude said after its last tool call (the answer itself,
                                              without "let me fetch that" lines); all of it if that is empty
"""
import json
import sys


def events(path):
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line:
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                pass


def brief(tool_input):
    for key in ("file_path", "url", "command", "pattern", "skill", "path", "query"):
        if key in tool_input:
            extra = f" pages={tool_input['pages']}" if "pages" in tool_input else ""
            return f"{key}={str(tool_input[key])[:160]}{extra}"
    return json.dumps(tool_input)[:160]


def main():
    args = sys.argv[1:]
    if args and args[0] == "--reply":
        # everything Claude said in the turn, in order (a summary may come before the last message)
        texts = [c["text"].strip() for e in events(args[1]) if e.get("type") == "assistant"
                 and not e.get("parent_tool_use_id")
                 for c in e["message"].get("content", []) if c.get("type") == "text" and c["text"].strip()]
        print("\n\n".join(texts))
        return
    if args and args[0] == "--final":
        texts = []
        for e in events(args[1]):
            if e.get("type") != "assistant" or e.get("parent_tool_use_id"):
                continue
            for c in e["message"].get("content", []):
                if c.get("type") == "tool_use":
                    texts = [("tool", "")]
                elif c.get("type") == "text" and c["text"].strip():
                    texts.append(("text", c["text"].strip()))
        final = [t for k, t in texts if k == "text"]
        if not final:
            final = [c["text"].strip() for e in events(args[1]) if e.get("type") == "assistant"
                     and not e.get("parent_tool_use_id")
                     for c in e["message"].get("content", []) if c.get("type") == "text" and c["text"].strip()]
        print("\n\n".join(final))
        return
    path, prompt = args[0], (args[1] if len(args) > 1 else "")
    out, hook_text = [], []
    for e in events(path):
        t = e.get("type")
        if t == "system" and e.get("subtype") == "init":
            out.append(f"_Session {e.get('session_id')} | model {e.get('model')} | "
                       f"plugins {[p.get('name') for p in e.get('plugins', [])]} | skills {e.get('skills')}_\n")
        elif t == "system" and "hook" in str(e.get("subtype", "")):
            text = e.get("stdout") or e.get("output") or ""
            if text.strip():
                hook_text.append(text.strip())
        elif t == "assistant":
            for c in e["message"].get("content", []):
                if c.get("type") == "text" and c["text"].strip():
                    out.append(f"**Claude:**\n\n{c['text'].strip()}\n")
                elif c.get("type") == "tool_use":
                    out.append(f"> tool: {c['name']} {brief(c.get('input', {}))}\n")
        elif t == "result":
            out.append(f"_Result: {e.get('subtype')} | turns {e.get('num_turns')} | "
                       f"cost ${e.get('total_cost' '_usd', 0):.2f} | session {e.get('session_id')}_")
    head = []
    if hook_text:
        head.append("**Session-start hook printed:**\n\n```\n" + "\n".join(hook_text)[:3000] + "\n```\n")
    head.append(f"**Professor:**\n\n{prompt}\n")
    print("\n".join(out[:1] + head + out[1:]))


if __name__ == "__main__":
    main()
