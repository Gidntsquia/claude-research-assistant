#!/usr/bin/env python3
"""Send several user messages to ONE headless Claude process, each after the reply to the one before.

    two_turns.py OUT.jsonl "first message" ["second message" ...] -- claude -p --input-format stream-json ...

The command after `--` is started once. Its stdout (stream-json events) is written to OUT.jsonl
as it arrives. A message is sent only after the `result` event of the previous one, so the second
message can never land in the middle of the first turn. If the environment variable
TWO_TURNS_SNAPSHOT is set to "SRC_DIR:DST_DIR", SRC_DIR is copied to DST_DIR/after-N when the reply
to message N is complete (used to see what memory/ held after each message). If a turn ends in an error (budget or turn
cap), the later messages are not sent. Exit code: 0 when every message got a result, else 1.
"""
import json
import os
import shutil
import subprocess
import sys
import threading

LIMIT_SECONDS = 45 * 60


def main() -> int:
    args = sys.argv[1:]
    cut = args.index("--")
    out_path, messages, cmd = args[0], args[1:cut], args[cut + 1:]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
    timer = threading.Timer(LIMIT_SECONDS, proc.kill)
    timer.start()

    def send(text: str) -> None:
        proc.stdin.write(json.dumps({"type": "user", "message": {"role": "user", "content": [{"type": "text", "text": text}]}}) + "\n")
        proc.stdin.flush()

    results, pending = 0, list(messages)
    try:
        send(pending.pop(0))
        with open(out_path, "w", encoding="utf-8") as out:
            for line in proc.stdout:
                out.write(line)
                out.flush()
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if event.get("type") != "result":
                    continue
                results += 1
                snap = os.environ.get("TWO_TURNS_SNAPSHOT", "")
                if ":" in snap:
                    src, dst = snap.split(":", 1)
                    if os.path.isdir(src):
                        shutil.copytree(src, os.path.join(dst, f"after-{results}"), dirs_exist_ok=True)
                if pending and not event.get("is_error"):
                    send(pending.pop(0))
                else:
                    proc.stdin.close()
                    break
            for line in proc.stdout:          # whatever is left after the last result
                out.write(line)
    finally:
        timer.cancel()
        try:
            proc.stdin.close()
        except Exception:
            pass
        try:
            proc.wait(timeout=60)
        except subprocess.TimeoutExpired:
            proc.kill()
    return 0 if results == len(messages) else 1


if __name__ == "__main__":
    sys.exit(main())
