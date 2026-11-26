"""Unit tests for the live-trial watcher and the trial build (no claude launch, no network)."""
import json
import os
import pathlib
import subprocess
import sys
import time
import zipfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import trial_watch as tw  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[2]
T0 = 1_795_626_000.0   # 25 Nov 2026, about noon ET


def ev(i, t, **kw):
    return dict(kw, id=i, t=T0 + t)


def msg(i, t, text=""):
    return ev(i, t, type="trace", kind="message", text=text)


def write(i, t, path="memory/INDEX.md"):
    return ev(i, t, type="file", action="changed", path=path, size=10, version=i)


def sample(t, fh, sd=30):
    return {"t": T0 + t, "fh": fh, "sd": sd}


def messages(rows):
    return [r for r in rows if "message" in r]


# ---- marker lines ----

def seen(h, m, s):
    import datetime
    return datetime.datetime(2026, 11, 25, h, m, s, tzinfo=tw.ET).timestamp()


def test_marker_line_gives_kind_version_and_its_own_time():
    e = tw.parse_marker_line("research-assistant 1.3.0-trial message 12:09:25 ET\n", seen(12, 10, 0))
    assert (e["kind"], e["version"], e["t"]) == ("message", "1.3.0-trial", seen(12, 9, 25))


def test_marker_line_found_inside_a_list_item_or_code():
    e = tw.parse_marker_line("- `research-assistant 1.3.0-trial session-start 12:09:25 ET`", seen(12, 9, 30))
    assert e["kind"] == "session-start" and e["version"] == "1.3.0-trial"


def test_marker_time_far_from_the_clock_takes_the_time_seen():
    """A VM without Eastern time prints another hour; the row is then placed when it was seen."""
    e = tw.parse_marker_line("research-assistant 1.3.0-trial message 17:09:25 ET", seen(12, 10, 0))
    assert e["t"] == seen(12, 10, 0)


def test_other_lines_are_not_marker_lines():
    assert tw.parse_marker_line("hello", 1.0) is None
    assert tw.parse_marker_line("research-assistant 1.3.0 unknown 12:00:00 ET", 1.0) is None
    assert tw.parse_marker_line("2026-11-25 12:09:25 ET\tmessage\tSummarise this\t1795626565", 1.0) is None


def test_times_are_eastern():
    assert tw.et(1795626565, "%Y-%m-%d %H:%M:%S") == "2026-11-25 12:09:25"


# ---- banner (R4) ----

def test_banner_green_counts_session_starts_and_messages_and_names_the_version():
    events = [ev(1, 0, type="trace", kind="session-start", text="", version="1.3.0-trial"),
              dict(msg(2, 1), version="1.3.0-trial"), dict(msg(3, 9), version="1.3.0-trial"), write(4, 10)]
    assert tw.banner(events) == {"color": "green", "text": "hooks ran in Claude Desktop: 1 session start, "
                                 "2 messages, plugin 1.3.0-trial"}


def test_banner_red_when_memory_files_are_written_and_no_marker():
    assert tw.banner([write(1, 3)]) == {"color": "red", "text": "hooks did not reach Claude: remove them"}


def test_banner_grey_for_files_that_are_not_memory():
    assert tw.banner([write(1, 3, path="articles/a.pdf")]) == {"color": "grey", "text": "no chat yet"}


def test_banner_grey_before_anything():
    assert tw.banner([]) == {"color": "grey", "text": "no chat yet"}


# ---- seconds to reply (R6) ----

def test_seconds_from_trace_line_to_reply_done_click():
    events = [msg(1, 0), write(2, 20), ev(3, 42, type="mark", kind="done", text=""), msg(4, 100)]
    m = messages(tw.build_rows(events, [], T0 + 200))[0]["message"]
    assert (m["secs"], m["approx"]) == (42, False)


def test_seconds_approx_from_last_write_before_the_next_message():
    events = [msg(1, 0), write(2, 20), write(3, 31), msg(4, 100), write(5, 130)]
    first, second = messages(tw.build_rows(events, [], T0 + 200))
    assert (first["message"]["secs"], first["message"]["approx"]) == (31, True)
    assert (second["message"]["secs"], second["message"]["approx"]) == (30, True)


def test_seconds_unknown_without_a_write_or_click():
    assert messages(tw.build_rows([msg(1, 0)], [], T0 + 50))[0]["message"]["secs"] is None


def test_sent_click_starts_a_message_only_when_no_hook_lines():
    sent = ev(1, 0, type="mark", kind="sent", text="hi")
    rows = tw.build_rows([sent, ev(2, 12, type="mark", kind="done", text="")], [], T0 + 50)
    assert messages(rows)[0]["message"]["secs"] == 12
    rows = tw.build_rows([sent, msg(2, 1, "hi")], [], T0 + 50)
    assert [r["id"] for r in messages(rows)] == [2] and all(r["id"] != 1 for r in rows)


# ---- usage, form 1: the usage file has numeric fh (R7, R8) ----

def test_usage_form_file_when_samples_have_numeric_fh():
    data = {"version": 2, "samples": [{"t": (T0 + 1) * 1000, "org": "x", "u": {"fh": 5, "sd": 20}}]}
    samples = tw.read_samples(data)
    assert tw.usage_form(samples) == "file" and samples[0]["fh"] == 5


def test_usage_change_per_message_and_times_five():
    samples = [sample(-60, 10, 30), sample(50, 12, 30), sample(150, 15, 31)]
    events = [msg(1, 0, "https://doi.org/10.1371/journal.pone.0224435"), msg(2, 100, "You're wrong")]
    a, b = messages(tw.build_rows(events, samples, T0 + 200))
    assert (a["message"]["usage"]["fh"], a["message"]["usage"]["sd"]) == (2, 0)
    assert a["message"]["usage"]["pro"] == 10 and a["message"]["usage"]["source"] == "file"
    assert (b["message"]["usage"]["fh"], b["message"]["usage"]["sd"]) == (3, 1)
    assert b["message"]["usage"]["pro"] == 15


def test_article_total_runs_from_one_doi_message_to_the_next():
    samples = [sample(-60, 10), sample(50, 12), sample(150, 15), sample(250, 16), sample(350, 16)]
    events = [msg(1, 0, "https://doi.org/10.1371/journal.pone.0224435"), msg(2, 100, "You're wrong"),
              msg(3, 200, "10.5334/jcaa.263 please"), msg(4, 300, "shorter")]
    rows = messages(tw.build_rows(events, samples, T0 + 400))
    assert [r["message"]["article_total"] for r in rows] == [10, 25, 5, 5]
    assert rows[1]["message"]["article"] == "doi.org/10.1371/journal.pone.0224435"
    assert rows[2]["message"]["article"].startswith("10.5334/jcaa.263")


def test_no_article_before_the_first_doi():
    rows = messages(tw.build_rows([msg(1, 0, "What do you think of this?")],
                                  [sample(-5, 1), sample(5, 2)], T0 + 10))
    assert rows[0]["message"]["article"] is None and rows[0]["message"]["article_total"] is None


def test_window_reset_counts_from_zero():
    assert tw.change(37, 4) == 4 and tw.change(4, 9) == 5 and tw.change(None, 3) is None


def test_stale_usage_file_falls_back_to_the_boxes():
    rows = messages(tw.build_rows([msg(1, 0)], [sample(-5_000_000, 14)], T0 + 60))
    u = rows[0]["message"]["usage"]
    assert u["form"] == "typed" and u["fh"] is None and "no usage sample since" in u["note"]
    assert rows[0]["message"]["article_total"] is None


def test_typed_boxes_win_over_the_usage_file_and_stay_on_the_row():
    events = [msg(1, 0), ev(2, 1, type="usage", msg=1, which="before", value=1.0),
              ev(3, 2, type="usage", msg=1, which="after", value=4.0)]
    u = messages(tw.build_rows(events, [sample(-5, 10), sample(5, 11)], T0 + 60))[0]["message"]["usage"]
    assert (u["form"], u["fh"], u["pro"]) == ("typed", 3.0, 15.0)


# ---- usage, form 2: no numeric fh, two typed boxes (R7, R8) ----

def test_usage_form_typed_when_fh_is_missing_or_not_a_number():
    assert tw.usage_form([]) == "typed"
    assert tw.usage_form(tw.read_samples({"samples": [{"t": 1, "u": {"fh": "n/a"}}]})) == "typed"
    assert tw.usage_form(tw.read_samples({"samples": [{"t": 1, "u": {}}]})) == "typed"
    assert tw.usage_form(tw.read_samples("garbage")) == "typed"


def test_typed_boxes_give_the_change_and_times_five():
    events = [msg(1, 0, "https://doi.org/10.1038/nature25738"),
              ev(2, 1, type="usage", msg=1, which="before", value=12.0),
              ev(3, 90, type="usage", msg=1, which="after", value=15.0)]
    rows = tw.build_rows(events, [], T0 + 100)
    u = messages(rows)[0]["message"]["usage"]
    assert (u["form"], u["fh"], u["pro"], u["source"]) == ("typed", 3.0, 15.0, "typed")
    assert messages(rows)[0]["message"]["article_total"] == 15.0
    assert all(r["type"] != "usage" for r in rows)


def test_typed_boxes_half_filled_show_no_change():
    events = [msg(1, 0), ev(2, 1, type="usage", msg=1, which="before", value=12.0)]
    u = messages(tw.build_rows(events, [], T0 + 100))[0]["message"]["usage"]
    assert u["fh"] is None and u["before"] == 12.0 and u["form"] == "typed"


# ---- the watcher on a real folder ----

def make_watch(tmp_path, usage=None):
    usage_file = tmp_path / "usage.json"
    if usage is not None:
        usage_file.write_text(json.dumps(usage))
    return tw.Watch(tmp_path / "Research", tmp_path / "out", usage_file)


def test_watch_waits_for_the_folder_then_sees_files_versions_and_trace(tmp_path):
    w = make_watch(tmp_path)
    w.poll()
    assert w.events == [] and w.state()["folder_exists"] is False
    folder = tmp_path / "Research"
    (folder / "memory").mkdir(parents=True)
    now = tw.et(time.time())
    (folder / "trial-markers.md").write_text(
        f"research-assistant 1.3.0-trial session-start {now} ET\n"
        f"research-assistant 1.3.0-trial message {now} ET\n"
        f"research-assistant 1.3.0-trial message {now} ET\n")       # copied twice: counted once
    (folder / "memory" / "INDEX.md").write_text("# Subjects\n")
    w.poll()
    (folder / "memory" / "INDEX.md").write_text("# Subjects\n- Caprolace\n")
    w.poll()
    w.poll()
    kinds = [(e["type"], e.get("kind") or e.get("action")) for e in w.events]
    assert sorted(kinds) == sorted([("trace", "session-start"), ("trace", "message"),
                                    ("file", "created"), ("file", "changed")])
    assert all(e.get("path") != "trial-markers.md" for e in w.events)
    v = w.version(2)
    assert v["content"] == "# Subjects\n- Caprolace\n" and "+- Caprolace" in v["diff"]
    assert w.version(1)["note"] == "new file"
    assert (tmp_path / "out/versions/0001-memory__INDEX.md").read_text() == "# Subjects\n"
    assert w.state()["banner"] == {"color": "green", "text": "hooks ran in Claude Desktop: 1 session start, "
                                   "1 message, plugin 1.3.0-trial"}


def test_watch_red_banner_deleted_file_and_static_page(tmp_path):
    w = make_watch(tmp_path)
    folder = tmp_path / "Research"
    (folder / "memory").mkdir(parents=True)
    (folder / "CLAUDE.md").write_text("notes\n")
    w.poll()
    assert w.state()["banner"] == {"color": "grey", "text": tw.GREY_TEXT}
    (folder / "memory/INDEX.md").write_text("# Subjects\n")
    (folder / "article.pdf").write_bytes(b"%PDF\xff\xfe\x00")
    w.poll()
    (folder / "CLAUDE.md").unlink()
    w.poll()
    s = w.state()
    assert s["banner"] == {"color": "red", "text": tw.RED_TEXT}
    assert [r["action"] for r in s["rows"] if r["type"] == "file"].count("deleted") == 1
    assert "not text" in w.version(2 if w.versions[1]["path"] == "article.pdf" else 1)["note"]
    page = w.write_static()
    text = page.read_text()
    assert page.name == "timeline.html" and tw.RED_TEXT in text and "/*STATIC*/null" not in text
    lines = (tmp_path / "out/timeline.jsonl").read_text().splitlines()
    assert len(lines) == 4 and json.loads(lines[0])["et"].endswith(" ET")


def test_watch_reads_the_usage_file_without_changing_it(tmp_path):
    usage = {"version": 2, "samples": [{"t": 1000, "org": "o", "u": {"fh": 5, "sd": 20}}]}
    w = make_watch(tmp_path, usage)
    before = (tmp_path / "usage.json").read_bytes()
    w.poll()
    assert w.state()["form"] == "file" and (tmp_path / "usage.json").read_bytes() == before


# ---- the trial zip (R1, R2) ----

def test_trial_zip_is_the_shipped_plugin_plus_the_trace(tmp_path):
    shipped = REPO / "dist/research-assistant-plugin.zip"
    before = shipped.read_bytes()
    subprocess.run([sys.executable, str(REPO / "build_plugin.py"), "--trial"], check=True,
                   capture_output=True)
    assert shipped.read_bytes() == before
    a, b = zipfile.ZipFile(shipped), zipfile.ZipFile(REPO / "dist/research-assistant-trial.zip")
    assert set(b.namelist()) - set(a.namelist()) == {"hooks/trace.sh"}
    changed = {n for n in a.namelist() if a.read(n) != b.read(n)}
    assert changed == {"hooks/hooks.json", ".claude-plugin/plugin.json"}
    man_a, man_b = (json.loads(z.read(".claude-plugin/plugin.json")) for z in (a, b))
    assert man_b["name"] == man_a["name"] and man_b["version"] == man_a["version"] + "-trial"
    assert b.read("hooks/trace.sh") == (REPO / "tests/trial/trace.sh").read_bytes()
    b.extractall(tmp_path / "plugin")
    folder = tmp_path / "folder"
    (folder / "memory").mkdir(parents=True)      # the hook prints only in a research folder
    (folder / "memory/INDEX.md").write_text("# Subjects\n")
    env = dict(os.environ, CLAUDE_PLUGIN_ROOT=str(tmp_path / "plugin"), CLAUDE_PROJECT_DIR=str(folder))
    prompt = "Summarise https://doi.org/10.1371/journal.pone.0224435 " + "x" * 80
    out = subprocess.run(["sh", str(tmp_path / "plugin/hooks/trace.sh"), "message", "each-message.sh"],
                         input=json.dumps({"prompt": prompt}), capture_output=True, text=True, env=env)
    shipped_out = subprocess.run(["sh", str(tmp_path / "plugin/hooks/each-message.sh")], input="{}",
                                 capture_output=True, text=True, env=env)
    first, second, rest = out.stdout.split("\n", 2)
    e = tw.parse_marker_line(first, time.time())
    assert first == f"research-assistant {man_b['version']} message {e['stamp']}"
    assert e["kind"] == "message" and abs(e["t"] - time.time()) < 60       # Eastern, now
    assert "trial-markers.md" in second and "file tool" in second
    assert rest == shipped_out.stdout and rest.startswith("[research-assistant]")
    assert not (folder / ".ra-trace.log").exists() and not (folder / "trial-markers.md").exists()
    (folder / ".git").mkdir()                    # a coding session's folder: no marker
    out = subprocess.run(["sh", str(tmp_path / "plugin/hooks/trace.sh"), "message", "each-message.sh"],
                         input="{}", capture_output=True, text=True, env=env)
    assert out.stdout == shipped_out.stdout
