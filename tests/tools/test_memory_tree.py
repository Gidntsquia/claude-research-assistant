"""uv run --with pytest pytest tests/tools"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import memory_tree as mt


def test_limits_hold_and_loaded_tokens_do_not_grow(tmp_path):
    rs = [mt.simulate(n, tmp_path / f"n{n}") for n in (10, 100, 1000)]
    for r in rs:
        assert mt.verdict(r) == [], mt.verdict(r)
        assert r["loaded_max"] <= 1200 and r["recall_level_max"] <= 1200 and r["depth_max"] <= 3
    # on-disk memory grows with n; what one chat reads does not grow with it
    assert rs[2]["total_tokens"] > 5 * rs[1]["total_tokens"]
    assert rs[2]["recall_files_max"] <= 3 and rs[2]["files"] > 100


def test_recall_opens_one_file_per_level_and_finds_the_entry(tmp_path):
    tree = mt.MemoryTree(tmp_path)
    s = mt.Subject(["Bell Beaker", "ancient DNA", "migration"], "Replacement in Britain")
    root = (tmp_path / "INDEX.md").read_text()
    tree.save(s, ["- Last discussed: 2026-11-23", "- His position: doubts it", "- My position: holds"], "2026-11-23", root)
    root = (tmp_path / "INDEX.md").read_text()
    op, found = tree.recall(s, root)
    assert [r for r, _ in op.reads] == ["bell-beaker.md"]
    assert found and "- His position: doubts it" in found["body"]
    op, found = tree.recall(mt.Subject(["Maya", "x", "y"], "Unknown"), root)
    assert op.reads == [] and found is None          # unknown subject: nothing opened


def test_branch_over_limit_splits_and_save_rewrites_same_entry(tmp_path):
    tree = mt.MemoryTree(tmp_path)
    body = ["- Last discussed: 2026-11-23", "- His position: " + "x" * 300, "- My position: " + "y" * 300]
    for i in range(12):
        root = (tmp_path / "INDEX.md").read_text()
        tree.save(mt.Subject(["Area", f"method {i % 3}", "d"], f"Subject {i}"), body, "2026-11-23", root)
    assert (tmp_path / "area" / "INDEX.md").is_file()
    assert (tmp_path / "area.md").read_text().startswith(mt.MOVED)
    stats, problems = mt.check_folder(tmp_path)
    assert problems == [] and stats["max_depth"] == 2 and stats["max_file_tokens"] <= 1200
    root = (tmp_path / "INDEX.md").read_text()
    files_before = stats["files"]
    tree.save(mt.Subject(["Area", "method 0", "d"], "Subject 0"), ["- Last discussed: 2026-12-01"], "2026-12-01", root)
    text = (tmp_path / "area" / "method-0.md").read_text()
    assert text.count("## Subject 0") == 1 and "2026-12-01" in text
    assert mt.check_folder(tmp_path)[0]["files"] == files_before


def test_check_flags_oversize_and_too_many_headings(tmp_path):
    rows = [{"heading": f"H{i}", "target": f"h{i}.md", "gist": "g", "last": "2026-01-01"} for i in range(31)]
    (tmp_path / "INDEX.md").write_text(mt.render_index("Subjects", rows))
    for r in rows:
        (tmp_path / r["target"]).write_text("## e\n- x\n")
    (tmp_path / "h0.md").write_text("z" * 5000)
    (tmp_path / "SETTINGS.md").write_text("s" * 1300)
    _, problems = mt.check_folder(tmp_path)
    joined = " ".join(problems)
    assert "31 headings" in joined and "h0.md: 1250 tokens" in joined and "SETTINGS.md" in joined
