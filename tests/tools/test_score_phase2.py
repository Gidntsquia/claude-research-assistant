"""uv run --with pytest --with pymupdf pytest -q tools"""
import importlib.util
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("score_phase2", HERE / "score_phase2.py")
sp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sp)


def row(kind, k, **fail):
    rules = {r: True for r, _ in sp.COLUMNS} | {r: False for r in fail}
    return {"kind": kind, "k": k, "run": True, "rules": rules}


def all_rows():
    return [row(kind, k) for kind in sp.SCORED for k in sp.RUNS]


def verdict(rows, rule):
    return next(v for r, _, _, _, _, v in sp.verdicts(rows) if r == rule)


def test_all_pass_meets():
    assert all(v[5] == "meets" for v in sp.verdicts(all_rows()))


def test_one_pointer_miss_misses():
    rows = all_rows()
    rows[4]["rules"]["pointer"] = False
    assert verdict(rows, "pointer") == "misses"
    assert verdict(rows, "opening") == "meets"


def test_soft_rule_two_misses_on_different_articles_meets_three_misses():
    rows = all_rows()
    rows[0]["rules"]["opening"] = False
    rows[3]["rules"]["opening"] = False
    assert verdict(rows, "opening") == "meets"            # 13 of 15, 2 of 3 each
    rows[6]["rules"]["opening"] = False
    assert verdict(rows, "opening") == "misses"           # 12 of 15


def test_soft_rule_two_misses_on_one_article_misses():
    rows = all_rows()
    rows[0]["rules"]["headings"] = False
    rows[1]["rules"]["headings"] = False
    assert verdict(rows, "headings") == "misses"          # 1 of 3 on caprolace


def test_missing_runs_are_not_settled_unless_already_lost():
    rows = all_rows()
    rows[14] = {"kind": "caprolace-scanned", "k": 3, "run": False, "why": "daily cap"}
    assert verdict(rows, "pointer").startswith("not settled")
    rows[0]["rules"]["pointer"] = False
    assert verdict(rows, "pointer") == "misses"


def test_scan_line_set_aside(tmp_path):
    src, dst = tmp_path / "a.md", tmp_path / "b.md"
    src.write_text(sp.SCAN_LINE + "\n\n# Title (A 2019)\n\nOpening.\n")
    assert sp.set_scan_line_aside(src, dst) is True
    assert sp.SCAN_LINE not in dst.read_text() and "# Title" in dst.read_text()
    src.write_text("# Title (A 2019)\n\nOpening.\n")
    assert sp.set_scan_line_aside(src, dst) is False
