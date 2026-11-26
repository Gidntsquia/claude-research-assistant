"""The quotes script, presets kept as lines in SETTINGS.md, the wording limits of the definition
(plugin 1.2.0), he leads: no say-once rules, one home per rule (1.3.0), and no hooks: the
definition itself has the memory files read (1.3.1)."""
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


# --- the settings file ------------------------------------------------------------------

def test_settings_template_fits_and_keeps_its_lines():
    text = (PLUGIN / "folder-template/memory/SETTINGS.md").read_text()
    assert len(text) / 4 <= 300 * 0.7            # room left for what he asks
    for line in ("- Length: default", "- Preset: none", "- quick read:", "- full breakdown:", "- devil's advocate:"):
        assert line in text
    assert "# State" not in text


def test_no_hooks_and_the_definition_has_the_memory_files_read():
    """The live trial read red (research/live-trial.md): hooks do not reach Claude in Claude
    Desktop, so the plugin has none and each entry point says to read the memory files."""
    assert not (PLUGIN / "hooks").exists()
    assert not [p for p in PLUGIN.rglob("*") if p.suffix == ".sh" or p.name == "hooks.json"]
    import json
    assert "hooks" not in json.loads((PLUGIN / ".claude-plugin/plugin.json").read_text())
    first = (PLUGIN / "folder-template/CLAUDE.md").read_text().splitlines()[0]
    assert "memory/INDEX.md" in first and "memory/SETTINGS.md" in first
    for skill in sorted((PLUGIN / "skills").glob("*/SKILL.md")):
        body = skill.read_text().split("---", 2)[2].strip().splitlines()[0]
        assert "memory/INDEX.md" in body and "memory/SETTINGS.md" in body, skill
    for f in [PLUGIN / "folder-template/CLAUDE.md", *sorted((PLUGIN / "skills").glob("*/SKILL.md"))]:
        assert not re.search(r"\bhooks?\b", f.read_text(), re.I), f



# --- memory in the shape plugin 1.2 writes ------------------------------------------------

def test_memory_fixture_in_the_new_shape_passes_the_check():
    sys.path.insert(0, str(REPO / "tests/tools"))
    import memory_tree
    mem = REPO / "tests/tools/fixtures/memory-1.2/memory"
    stats, problems = memory_tree.check_folder(mem)
    assert problems == [] and stats["headings"] == 2 and stats["settings_tokens"] <= 300
    template, _ = memory_tree.check_folder(PLUGIN / "folder-template/memory")
    assert template["settings_tokens"] <= 300
    settings = (mem / "SETTINGS.md").read_text()
    assert "- quick read: three details in prose, no list (changed 2026-11-25)." in settings
    assert "always show the article's own sentences" in settings
