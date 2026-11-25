#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Score the test conversations and write tests/RESULTS.md.

    uv run tests/tools/score_conversations.py

Reads tests/runs/conversations/rK-c1.* and rK-c2.* (made by run_conversation.sh): the event
stream, the meta file, and memory/ as it was after each message. One row per launch.

Rules (each "meets" or "misses"; "n/a" where the conversation does not test it):
  conversation 1
    own words       reply to the request for the article's own sentences has a quoted line (> "...")
                    under at least half of its details, or says in its first line that the quotes
                    could not be shown
    no defence      the reply to the complaint has no "Position:" line, no "Confidence" line and
                    no "your point at its strongest"
    settings saved  after "From now on, be shorter." memory/SETTINGS.md has a Length line that is not
                    "default" and says short; the reply to "What are my settings?" says short
    presets once    the presets note (naming quick read, full breakdown and devil's advocate) is in
                    the reply to "be shorter" and in no other reply of the conversation
  conversation 2
    recall with date  reply to "What did we say about Caprolace?" gives the date of conversation 1
                      and both positions ("you" and "I")
    corrected       after "That's wrong: ..." the Caprolace entry in memory/ says "undecided"
    forgotten       after "Forget that." no file in memory/ mentions Caprolace; reply says "Forgotten"
    presets once    no reply of conversation 2 carries the presets note again
    fewer details   the second summary has fewer key details than the first of the same repeat
Pass rule: every rule 3 of 3, except fewer details, 2 of 3.

The rows and the scorer of the plugin before 1.2.0 (which scored "Position: held" and
"Position: changed") are in tests/runs/conversations/old/ (research/discussion-memory.md).
"""
import datetime
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
TESTS = HERE.parent
RUNS = TESTS / "runs" / "conversations"
POINTER = re.compile(r'\((?:p\. ?\d+|sec\. [^)]*|Fig\. ?\d+\w*|Table ?\d+\w*|inference)\)\s*$')
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December"]


def replies(jsonl: pathlib.Path) -> list[str]:
    """The final reply of each turn: what Claude wrote after its last tool call."""
    out, texts = [], []
    for line in jsonl.read_text(encoding="utf-8").splitlines():
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        t = e.get("type")
        if t == "assistant" and not e.get("parent_tool_use_id"):
            for c in e["message"].get("content", []):
                if c.get("type") == "text" and c["text"].strip():
                    texts.append(c["text"].strip())
                elif c.get("type") == "tool_use":
                    texts = []
        elif t == "result":
            out.append("\n\n".join(texts))
            texts = []
    return out


def first_line(text: str) -> str:
    for line in text.splitlines():
        if line.strip():
            return line.strip().strip("*_# ").strip()
    return ""


def count_details(summary: str) -> int:
    return sum(1 for line in summary.splitlines()
               if re.match(r"^\s*[-*]\s+", line) and POINTER.search(line.strip()))


DEFENCE = re.compile(r"position:|^\W*confidence\b|point at its strongest", re.I | re.M)


def own_words(reply: str) -> bool:
    """Each detail followed by a quoted line, for at least half of them; or a plain first line
    saying the quotes could not be shown."""
    lines = reply.splitlines()
    details = [i for i, line in enumerate(lines)
               if re.match(r"^\s*[-*]\s+", line) and POINTER.search(line.strip())]
    quoted = sum(1 for i in details
                 if any(re.match(r'^\s*>\s*["“]', nxt) for nxt in lines[i + 1:i + 3]))
    if details and quoted * 2 >= len(details):
        return True
    first = first_line(reply).replace("’", "'")
    return bool(re.search(r"could not|cannot|can't|couldn't|unable", first, re.I) and re.search(r"quot", first, re.I))


def has_presets_note(text: str) -> bool:
    low = text.lower().replace("’", "'")
    return "quick read" in low and "full breakdown" in low and "devil's advocate" in low


def date_forms(d: datetime.date) -> list[str]:
    m = MONTHS[d.month - 1]
    return [d.isoformat(), f"{d.day} {m}", f"{m} {d.day}", f"{d.day} {m[:3]}", f"{m[:3]} {d.day}",
            f"{d.day}th {m}", f"{d.day}th of {m}", f"{m} {d.day}th"]


def has_date(text: str, day: datetime.date) -> bool:
    # The session may have taken the date in UTC, so the day after counts too.
    for d in (day, day + datetime.timedelta(days=1)):
        for form in date_forms(d):
            if re.search(r"(?<!\d)" + re.escape(form) + r"(?!\d)", text, re.I):
                return True
    return False


def memory_text(snap: pathlib.Path) -> str:
    if not snap.is_dir():
        return ""
    return "\n".join(f"--- {p.relative_to(snap)}\n{p.read_text(encoding='utf-8', errors='replace')}"
                     for p in sorted(snap.rglob("*")) if p.is_file())


def mark(ok: bool) -> str:
    return "meets" if ok else "misses"


def score_c1(base: pathlib.Path) -> dict:
    r = replies(pathlib.Path(f"{base}.jsonl"))
    r += [""] * (5 - len(r))
    settings = pathlib.Path(f"{base}.memory/after-4/SETTINGS.md")
    length = ""
    if settings.is_file():
        m = re.search(r"^- Length:\s*(.*)$", settings.read_text(encoding="utf-8"), re.M)
        length = m.group(1).strip() if m else ""
    notes = [i + 1 for i, text in enumerate(r) if has_presets_note(text)]
    return {
        "answered": sum(1 for x in r if x),
        "details": count_details(r[0]),
        "own words": mark(own_words(r[1])),
        "no defence": mark(bool(r[2]) and not DEFENCE.search(r[2])),
        "settings saved": mark(bool(length) and not length.lower().startswith("default") and "short" in length.lower()
                               and "short" in r[4].lower()),
        "presets once": mark(notes == [4]),
        "note": f"Length line: `{length or 'none'}`; presets note in replies {notes or 'none'}",
    }


def score_c2(base: pathlib.Path, c1: dict | None, c1_day: datetime.date | None) -> dict:
    r = replies(pathlib.Path(f"{base}.jsonl"))
    r += [""] * (4 - len(r))
    low = r[0].lower()
    recalled = bool(c1_day) and has_date(r[0], c1_day) and "you" in low and re.search(r"\b(i|my)\b", low) is not None
    after2 = memory_text(pathlib.Path(f"{base}.memory/after-2"))
    after3_dir = pathlib.Path(f"{base}.memory/after-3")
    after3 = memory_text(after3_dir)
    details = count_details(r[3])
    notes = [i + 1 for i, text in enumerate(r) if has_presets_note(text)]
    return {
        "answered": sum(1 for x in r if x),
        "details": details,
        "recall with date": mark(recalled),
        "corrected": mark("undecided" in after2.lower()),
        "forgotten": mark(after3_dir.is_dir() and "caprolace" not in after3.lower() and "forgotten" in r[2].lower()),
        "presets once": mark(not notes),
        "fewer details": mark(bool(c1) and 0 < details < c1["details"]),
        "note": f"second summary {details} details against {c1['details'] if c1 else '?'}; presets note in replies {notes or 'none'}",
    }


C1_RULES = ["own words", "no defence", "settings saved", "presets once"]
C2_RULES = ["recall with date", "corrected", "forgotten", "presets once", "fewer details"]
COLUMNS = ["own words", "no defence", "settings saved", "presets once", "recall with date", "corrected", "forgotten", "fewer details"]


def main() -> int:
    rows, tallies = [], {}
    repeats = sorted({int(m.group(1)) for p in RUNS.glob("r*-c?.meta.json") if (m := re.match(r"r(\d+)-", p.name))})
    for k in repeats:
        c1 = None
        c1_day = None
        for conv in ("c1", "c2"):
            base = RUNS / f"r{k}-{conv}"
            link = f"[r{k}-{conv}](runs/conversations/r{k}-{conv}.md)"
            if not pathlib.Path(f"{base}.jsonl").is_file():
                reason = pathlib.Path(f"{base}.notrun").read_text().strip() if pathlib.Path(f"{base}.notrun").is_file() else "not run"
                rows.append(f"| r{k}-{conv} | | | " + " | ".join(reason for _ in COLUMNS) + " | |")
                continue
            meta = json.loads(pathlib.Path(f"{base}.meta.json").read_text())
            if conv == "c1":
                s = c1 = score_c1(base)
                c1_day = datetime.date.fromisoformat(meta["started"][:10])
                rules = C1_RULES
            else:
                s = score_c2(base, c1, c1_day)
                rules = C2_RULES
            for rule in rules:
                key = (conv, rule)
                tallies.setdefault(key, [0, 0])
                tallies[key][1] += 1
                tallies[key][0] += s[rule] == "meets"
            cells = [s[c] if c in rules else "n/a" for c in COLUMNS]
            rows.append(f"| {link} | {meta['started']} | `{meta['plugin_commit']}` | " + " | ".join(cells)
                        + f" | {s['answered']} answered; {s['note']} |")
    launches = TESTS / "runs" / "LAUNCHES.md"
    n_launch = len(launches.read_text().splitlines()) if launches.is_file() else 0
    summary, all_ok = [], True
    for conv, rules in (("c1", C1_RULES), ("c2", C2_RULES)):
        for rule in rules:
            got, of = tallies.get((conv, rule), [0, 0])
            need = 2 if rule == "fewer details" else 3
            ok = got >= need and of >= 3
            all_ok = all_ok and ok
            summary.append(f"| {'conversation 1' if conv == 'c1' else 'conversation 2'} | {rule} | {got} of {of} | {need} of 3 | {mark(ok)} |")
    text = f"""# Results

Written by `tests/tools/score_conversations.py`; do not edit by hand.

## Conversations with the current plugin

No headless conversation has been run with plugin 1.2.0: it is tested by Jaxon in Cowork. Rows appear here if `run_conversation.sh` is run.

Each row is one headless Claude launch (Sonnet) with `dist/research-assistant-plugin.zip`, standing in for Cowork. Conversation 1 (c1) starts in an empty folder: the Caprolace link, a request for the article's own sentences, a complaint about the answer, "From now on, be shorter.", "What are my settings?". Conversation 2 (c2) is a new launch in the same folder: "What did we say about Caprolace?", "That's wrong: …", "Forget that.", then a second article link. The messages are in `tests/tools/conversations.json`. Launches used: {n_launch} of 15 (`runs/LAUNCHES.md`). Read a repeat as a page: `runs/walkthrough.html` (after `render_walkthrough.py`).

| launch | started | plugin | {" | ".join(COLUMNS)} | observed |
|---|---|---|{"---|" * len(COLUMNS)}---|
{chr(10).join(rows)}

## Rules over the repeats

| conversation | rule | met | needed | result |
|---|---|---|---|---|
{chr(10).join(summary)}

{"Every rule meets." if all_ok else ("Not every rule meets." if rows else "No rows to score.")}

What each rule checks is at the top of `tests/tools/score_conversations.py`. Rows of earlier plugin commits, with the table and scorer of that time (held / changed), are in `runs/conversations/old/` and are not counted.

## Earlier tables

- The short summary alone, 15 runs over 5 articles, plus paywalled, scanned and two-article runs: [runs/summary/RESULTS.md](runs/summary/RESULTS.md)
- Plain Claude with no plugin (the baseline): [runs/baseline/RESULTS.md](runs/baseline/RESULTS.md)
- Memory size at 10, 100 and 1,000 chats: [runs/memory/REPORT.md](runs/memory/REPORT.md)
- First build of discussion, memory and settings (old reply format, one run each): `runs/first-build/`
- The real app: [cowork/COWORK-CHECKLIST.md](cowork/COWORK-CHECKLIST.md), results in `cowork/RESULT.md`
"""
    (TESTS / "RESULTS.md").write_text(text, encoding="utf-8")
    print(text[text.index("| launch"):text.index("What each rule")])
    return 0


if __name__ == "__main__":
    sys.exit(main())
