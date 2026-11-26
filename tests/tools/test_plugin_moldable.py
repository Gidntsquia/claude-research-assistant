"""The quotes script, the 60-word hook, presets read back from SETTINGS.md, the wording limits
of the definition (plugin 1.2.0), and he leads: no say-once rules, one home per rule, hooks that
print facts only (plugin 1.3.0)."""
import importlib.util
import pathlib
import re
import shutil
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
PLUGIN = REPO / "plugin"
QUOTES = PLUGIN / "skills/article-summary/scripts/quotes.py"
CAPROLACE = REPO / "tests/test-set/caprolace.pdf"

sys.dont_write_bytecode = True               # no __pycache__ inside plugin/
spec = importlib.util.spec_from_file_location("quotes", QUOTES)
quotes = importlib.util.module_from_spec(spec)
spec.loader.exec_module(quotes)


def folder(tmp_path):
    shutil.copytree(PLUGIN / "folder-template/memory", tmp_path / "memory")
    return tmp_path


def hook(name, ws, stdin="{}"):
    return subprocess.run(["sh", str(PLUGIN / "hooks" / name)], input=stdin, capture_output=True, text=True,
                          env={"CLAUDE_PROJECT_DIR": str(ws), "PATH": "/usr/bin:/bin"}).stdout


def edit_settings(ws, *pairs):
    f = ws / "memory/SETTINGS.md"
    text = f.read_text()
    for pattern, new in pairs:
        text, n = re.subn(pattern, new, text, flags=re.M)
        assert n == 1, pattern
    f.write_text(text)


# --- quotes.py ---------------------------------------------------------------------------

def test_quotes_prints_the_whole_sentence_with_its_page(capsys):
    assert quotes.main([str(CAPROLACE), "--page", "22", "--near", "microcrystals"]) == 0
    out = capsys.readouterr().out.strip()
    assert out.count("\n") == 0 and out.startswith('p. 22: "') and out.endswith('."')
    sentence = out[len('p. 22: "'):-1]
    assert sentence == ("Interestingly, in CP 131 we found the largest NaCl microcrystals, up to a size of "
                        "0.3–0.4 mm, within microcracks (Fig 20).")
    import pymupdf
    page = re.sub(r"\s+", " ", pymupdf.open(CAPROLACE)[21].get_text())
    assert sentence in page                      # word for word what page 22 of the file has


def test_quotes_reports_the_page_it_found_when_the_pointer_is_off(capsys):
    assert quotes.main([str(CAPROLACE), "--page", "12", "--near", "largest NaCl microcrystals"]) == 0
    assert capsys.readouterr().out.startswith('p. 22 (not p. 12): "Interestingly')


def test_quotes_several_details_in_one_run_and_a_miss(capsys):
    code = quotes.main([str(CAPROLACE), "--page", "17", "--near", "no pedestals were found",
                        "--page", "3", "--near", "zeppelin moonbase helicopter"])
    lines = capsys.readouterr().out.strip().splitlines()
    assert code == 1 and lines[0] == 'p. 17: "No pedestals were found in the entire sounding."'
    assert lines[1].startswith("no sentence found on or near p. 3")


def test_quotes_exit_3_and_one_line_without_a_pdf_tool(monkeypatch, capsys):
    def absent(path):
        raise ImportError("not installed")
    monkeypatch.setattr(quotes, "READERS", [("pymupdf", absent), ("pypdf", absent), ("pdftotext", absent)])
    assert quotes.main([str(CAPROLACE), "--page", "22", "--near", "microcrystals"]) == 3
    out = capsys.readouterr().out.strip()
    assert out.count("\n") == 0 and "no PDF text tool" in out


def test_quotes_exit_3_from_the_command_line_with_a_bare_python():
    """The real thing: a Python with no PDF library and a PATH with no pdftotext."""
    r = subprocess.run([sys.executable, "-I", "-S", str(QUOTES), str(CAPROLACE), "--page", "22", "--near", "microcrystals"],
                       capture_output=True, text=True, env={"PATH": "/nonexistent"})
    assert r.returncode == 3 and r.stdout.strip().count("\n") == 0 and "no PDF text tool" in r.stdout


def test_quotes_text_file_saved_from_a_web_page(tmp_path, capsys):
    f = tmp_path / "olalde-2018-beaker.txt"
    f.write_text("# The Beaker phenomenon\n\n## Results\n\nWe sampled 400 individuals. Steppe-related ancestry "
                 "arrived in Britain with the\nBeaker complex, as shown in Fig. 2 and discussed below. It replaced "
                 "about 90% of the gene pool.\n\n## Methods\n\nDNA was extracted in clean rooms.\n")
    assert quotes.main([str(f), "--near", "steppe ancestry Britain"]) == 0
    assert capsys.readouterr().out.strip() == ('under "Results": "Steppe-related ancestry arrived in Britain with '
                                               'the Beaker complex, as shown in Fig. 2 and discussed below."')
    assert quotes.main([str(f), "--page", "5", "--near", "extracted in clean rooms"]) == 0
    assert capsys.readouterr().out.strip() == 'under "Methods": "DNA was extracted in clean rooms."'


def test_quotes_scan_and_missing_file(capsys):
    assert quotes.main([str(REPO / "tests/test-set/caprolace-scanned.pdf"), "--near", "microcrystals"]) == 4
    assert quotes.main([str(REPO / "nope.pdf"), "--near", "x"]) == 2


# --- the hook on each message ------------------------------------------------------------

def test_each_message_is_silent_outside_a_research_folder(tmp_path):
    assert hook("each-message.sh", tmp_path) == ""


def test_each_message_defaults_under_60_words(tmp_path):
    out = hook("each-message.sh", folder(tmp_path))
    assert len(out.split()) <= 60 and f"{tmp_path}/memory" in out and "all at the defaults" in out


def test_changed_preset_is_read_back_from_settings(tmp_path):
    ws = folder(tmp_path)
    edit_settings(ws, (r"^- Preset: none$", "- Preset: quick read (asked 2026-11-25)"),
                  (r"^- quick read: .*$", "- quick read: three details in prose, no list."),
                  (r"^- Length: default$", "- Length: shorter (asked 2026-11-25)"))
    out = hook("each-message.sh", ws)
    assert "preset quick read = three details in prose, no list." in out
    assert "Length: shorter" in out and "5 details" not in out and len(out.split()) <= 60
    start = hook("session-start.sh", ws, '{"source":"startup"}')     # a later task
    assert "- quick read: three details in prose, no list." in start
    assert f"{tmp_path}/memory" in start and "# Subjects" in start


def test_each_message_stays_at_60_words_however_much_is_saved(tmp_path):
    ws = folder(tmp_path)
    edit_settings(ws, (r"^- Other: none$", "- Other: " + "; ".join(f"wish number {i} in several words" for i in range(30))))
    out = hook("each-message.sh", ws)
    assert len(out.split()) <= 60 and out.rstrip().endswith("(rest: memory/SETTINGS.md)")


def test_settings_template_fits_and_keeps_its_lines():
    text = (PLUGIN / "folder-template/memory/SETTINGS.md").read_text()
    assert len(text) / 4 <= 300 * 0.7            # room left for what he asks
    for line in ("- Length: default", "- Preset: none", "- quick read:", "- full breakdown:", "- devil's advocate:"):
        assert line in text
    assert "# State" not in text


def test_hooks_print_nothing_outside_a_research_folder_and_no_instructions_inside(tmp_path):
    assert hook("session-start.sh", tmp_path, '{"source":"startup"}') == ""
    assert not list(tmp_path.iterdir())
    ws = folder(tmp_path)
    before = (ws / "memory/SETTINGS.md").read_text()
    out = hook("session-start.sh", ws, '{"source":"startup"}') + hook("each-message.sh", ws)
    assert (ws / "memory/SETTINGS.md").read_text() == before              # the hooks write nothing
    notes = [l for l in out.splitlines() if l.startswith("[research-assistant]")]
    assert len(notes) == 4
    for line in notes:                                                     # facts, no instructions
        assert not re.search(r"\b(create|save|read it|before replying|applies|wins|do not|should)\b", line, re.I), line


# --- he leads (plugin 1.3.0) ---------------------------------------------------------------

def plugin_text():
    return {p: p.read_text() for p in PLUGIN.rglob("*") if p.is_file() and p.suffix in (".md", ".sh", ".json")}


def test_no_say_once_rules_state_lines_or_counter():
    for p, text in plugin_text().items():
        assert not re.search(r"Quotes mentioned|Presets mentioned|Conversations|say once|said once|Tell him once|# State", text), p


def test_one_sentence_says_he_leads_with_its_reason():
    text = (PLUGIN / "folder-template/CLAUDE.md").read_text()
    line = [l for l in text.splitlines() if "come up when he raises them" in l]
    assert len(line) == 1 and "answers what he asked" in line[0] and "since he learns them from his guide" in line[0]
    for word in ("quotes", "presets", "settings"):
        assert word in line[0]
    asked = [l for l in text.splitlines() if "what can you do?" in l]
    assert len(asked) == 1 and "what are my settings?" in asked[0] and "three presets by name" in asked[0]


def test_each_rule_has_one_home():
    texts = plugin_text()
    def homes(pattern):
        return sorted(str(p.relative_to(PLUGIN)) for p, t in texts.items() if re.search(pattern, t))
    assert homes(r"wins? over") == ["folder-template/CLAUDE.md"]                       # settings win over defaults
    assert homes(r"the new text is the preset") == ["folder-template/CLAUDE.md"]       # the preset-rewrite rule
    assert homes(r"[Ww]ith each answer on a research subject, first") == ["folder-template/CLAUDE.md"]   # the saving rule
    assert homes(r"one new angle") == []


def test_first_line_of_each_skill_and_of_claude_md_has_the_memory_files_read():
    assert "memory/SETTINGS.md" in (PLUGIN / "folder-template/CLAUDE.md").read_text().splitlines()[0]
    for skill in sorted((PLUGIN / "skills").glob("*/SKILL.md")):
        body = skill.read_text().split("---", 2)[2].strip().splitlines()[0]
        assert "memory/INDEX.md" in body and "memory/SETTINGS.md" in body and "CLAUDE.md" in body, skill


def test_guide_names_the_three_presets_and_no_reader_page_says_cowork():
    guide = (REPO / "guide/guide.html").read_text()
    for name in ("quick read", "full breakdown", "devil's advocate"):
        assert name in guide.lower(), name
    for p in [REPO / "guide/guide.html", *(REPO / "tests/cowork").glob("*.html"), REPO / "AGENTS.md",
              *[q for q in PLUGIN.rglob("*") if q.is_file() and q.suffix in (".md", ".sh", ".json", ".py")]]:
        assert "cowork" not in p.read_text().lower().replace("tests/cowork", "").replace("cowork-checklist", ""), p


# --- the definition ----------------------------------------------------------------------

BEFORE = {"skills/article-summary/SKILL.md": 2446, "skills/discussion-memory/SKILL.md": 1456,
          "skills/settings-presets/SKILL.md": 951, "folder-template/CLAUDE.md": 978}


def test_each_file_is_at_most_half_its_former_words():
    for rel, before in BEFORE.items():
        assert len((PLUGIN / rel).read_text().split()) <= before // 2, rel


def test_no_arguing_rules_and_no_fixed_phrases():
    for p in [*PLUGIN.rglob("*"), REPO / "guide/guide.html"]:
        if p.is_file() and p.suffix in (".md", ".sh", ".json", ".py", ".html"):
            text = p.read_text()
            for gone in ("Position:", "show quotes", "onfidence", "change my mind", "change your mind", "strongest form"):
                assert gone not in text, f"{p}: {gone}"


def test_exactly_never_must_only_in_the_memory_format():
    """Outside the memory sections the definition uses none of the three words."""
    hits = []
    for p in PLUGIN.rglob("*"):
        if not (p.is_file() and p.suffix in (".md", ".sh", ".json", ".py")):
            continue
        section = ""
        for n, line in enumerate(p.read_text().splitlines(), 1):
            if line.startswith("#") and not line.startswith("#!"):
                section = line
            if re.search(r"exactly|never|must", line, re.I):
                memory = "memory" in line.lower() or "31st" in line or "appended" in line
                in_memory_part = p.name == "SKILL.md" and "discussion-memory" in str(p) or "Memory" in section
                if not (memory and in_memory_part):
                    hits.append(f"{p.relative_to(REPO)}:{n}: {line[:80]}")
    assert not hits, hits


# --- memory in the shape plugin 1.2 writes ------------------------------------------------

def test_memory_fixture_in_the_new_shape_passes_the_check():
    sys.path.insert(0, str(REPO / "tests/tools"))
    import memory_tree
    mem = REPO / "tests/tools/fixtures/memory-1.2/memory"
    stats, problems = memory_tree.check_folder(mem)
    assert problems == [] and stats["headings"] == 2 and stats["settings_tokens"] <= 300
    template, _ = memory_tree.check_folder(PLUGIN / "folder-template/memory")
    assert template["settings_tokens"] <= 300
    out = hook("each-message.sh", mem.parent)
    assert "preset quick read = three details in prose, no list (changed 2026-11-25)." in out
    assert "always show the article's own sentences" in out and len(out.split()) <= 60
