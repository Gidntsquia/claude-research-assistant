import datetime
import json

import score_conversations as sc


def event(kind, **kw):
    return json.dumps({"type": kind, **kw})


def say(text):
    return event("assistant", message={"content": [{"type": "text", "text": text}]})


def tool():
    return event("assistant", message={"content": [{"type": "tool_use", "name": "Read", "input": {}}]})


def write_run(tmp_path, name, turns):
    lines = []
    for turn in turns:
        lines += ["" if False else say("working on it"), tool(), say(turn), event("result")]
    (tmp_path / f"{name}.jsonl").write_text("\n".join(lines) + "\n")
    return tmp_path / name


def test_replies_keep_only_text_after_last_tool(tmp_path):
    base = write_run(tmp_path, "r1-c1", ["one", "two"])
    assert sc.replies(tmp_path / "r1-c1.jsonl") == ["one", "two"]


def test_count_details_counts_only_lines_with_pointer():
    s = "# T\n\nOpening.\n\n- A fact. (p. 3)\n- Another. (sec. \"2. Methods\")\n- No pointer here\n- Mine. (inference)\n"
    assert sc.count_details(s) == 3


def test_first_line_ignores_bold_and_blank():
    assert sc.first_line("\n**Quotes could not be shown.**\nrest").startswith("Quotes could not")


def test_own_words():
    quoted = '# T\n\nO.\n\n- a. (p. 1)\n  > "The sentence."\n- b. (p. 2)\n  > "Another one."\n- c. (p. 3)\n'
    assert sc.own_words(quoted)
    assert sc.own_words("The quotes could not be shown here.\n\n- a. (p. 1): the paragraph opening Results from\n")
    assert not sc.own_words("# T\n\n- a. (p. 1)\n- b. (p. 2)\n  > first sentence under the heading\n")


def test_has_date_accepts_common_forms_and_next_day():
    d = datetime.date(2026, 11, 24)
    assert sc.has_date("We talked on 24 November.", d)
    assert sc.has_date("on November 25, 2026", d)
    assert sc.has_date("(2026-11-24)", d)
    assert not sc.has_date("on 2 November", d)
    assert not sc.has_date("some time ago", d)


PRESETS = "By the way, there are three modes: quick read, full breakdown and devil's advocate."


def test_score_c1_meets_and_misses(tmp_path):
    summary = "# T\n\nO.\n\n" + "".join(f"- d{i}. (p. {i})\n" for i in range(1, 7))
    base = write_run(tmp_path, "r1-c1", [summary, summary.replace(")\n", ')\n  > "Its sentence."\n'),
                                         "Here they are again.", "Done. " + PRESETS,
                                         "Length: shorter."])
    snap = tmp_path / "r1-c1.memory" / "after-4"
    snap.mkdir(parents=True)
    (snap / "SETTINGS.md").write_text("# Settings\n- Length: shorter (asked 2026-11-24)\n")
    s = sc.score_c1(base)
    assert (s["own words"], s["no defence"], s["settings saved"], s["details"]) == ("meets",) * 3 + (6,)
    assert "presets once" not in s
    (snap / "SETTINGS.md").write_text("# Settings\n- Length: default\n")
    base = write_run(tmp_path, "r1-c1", [summary, summary, "Position: held\nConfidence: high.",
                                         "Done.", PRESETS])
    s = sc.score_c1(base)
    assert (s["own words"], s["no defence"], s["settings saved"]) == ("misses",) * 3


def test_score_c2(tmp_path):
    short = "# T\n\nO.\n\n- a. (p. 1)\n- b. (p. 2)\n- c. (p. 3)\n"
    base = write_run(tmp_path, "r1-c2", ["We discussed this on 24 November. You held X; I held Y. New angle: Z.",
                                         "Corrected.", "Forgotten.", short])
    (tmp_path / "r1-c2.memory" / "after-2").mkdir(parents=True)
    (tmp_path / "r1-c2.memory" / "after-2" / "salt.md").write_text("## Caprolace\n- His position: undecided\n")
    (tmp_path / "r1-c2.memory" / "after-3").mkdir(parents=True)
    (tmp_path / "r1-c2.memory" / "after-3" / "INDEX.md").write_text("# Subjects\n")
    s = sc.score_c2(base, {"details": 6}, datetime.date(2026, 11, 24))
    assert [s[r] for r in sc.C2_RULES] == ["meets"] * 4 and "presets once" not in sc.COLUMNS
    (tmp_path / "r1-c2.memory" / "after-3" / "salt.md").write_text("## Caprolace\n")
    s = sc.score_c2(base, {"details": 3}, datetime.date(2026, 11, 20))
    assert (s["forgotten"], s["fewer details"], s["recall with date"]) == ("misses",) * 3
