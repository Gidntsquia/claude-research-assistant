"""uv run --with pytest --with pymupdf pytest -q tests/tools"""
import pathlib
import re
import sys

import pytest

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
import check_summary as cs

TS = HERE.parent / "test-set"
FIX = HERE / "fixtures"
PDF = str(TS / "caprolace.pdf")       # the web copy is not in this repo, so the web rules are not tested here

# fixture -> the one rule it must fail, and words its failure must show (sentence, then what was examined)
FAULTS = {
    "fault-invented-quote.md": ("quote-match", "Wood from 94–96 cm deep", "forty households", "all 41 pages"),
    "fault-wrong-page.md": ("quote-match", "Sherd CP 131 held the largest salt microcrystals", "p. 12", "p. 22"),
    "fault-nine-details.md": ("detail-count", "9 details", "fish hypothesis"),
    "fault-26-word-detail.md": ("detail-length", "26 words", "The authors suggest that layer SU 104"),
    "fault-fixed-sections.md": ("headings", "Research question", "Evidence", "Limits"),
    "fault-quote-by-default.md": ("no-quotes", "The authors write that", "evidence of fish processing has never been found"),
    "fault-not-stated.md": ("not-stated", "Sample size for the chemical analyses: not stated."),
}
CLEAN = ["clean-pdf.md", "clean-pdf-quotes.md"]


@pytest.fixture(scope="module")
def article():
    return cs.pdf_pages(PDF), None


def flags(name):
    m = re.match(r"<!-- check: (.*?) -->", (FIX / name).read_text(encoding="utf-8"))
    return m.group(1).split()


def run(name, article):
    fl = flags(name)
    s = cs.parse_summary((FIX / name).read_text(encoding="utf-8"))
    return cs.check(s, fl[fl.index("--source") + 1], article[0], article[1], "--quotes" in fl)


def test_every_fault_named_in_the_plan_has_a_fixture():
    assert len(FAULTS) == 7 and all((FIX / n).exists() for n in list(FAULTS) + CLEAN)


@pytest.mark.parametrize("name", CLEAN)
def test_clean_summary_passes(name, article):
    fails = run(name, article)
    assert fails == [], [x.line() for x in fails]


@pytest.mark.parametrize("name", list(FAULTS))
def test_planted_fault_fails_only_its_rule_and_shows_why(name, article):
    rule, *shown = FAULTS[name]
    fails = run(name, article)
    assert fails, f"{name}: the planted fault was not caught"
    assert {x.rule for x in fails} == {rule}, [x.line() for x in fails]
    text = "\n".join(x.line() for x in fails)
    assert f"[{rule}]" in text
    for piece in shown:
        assert piece in text, f"{piece!r} not shown in:\n{text}"


@pytest.mark.parametrize("name", list(FAULTS) + CLEAN)
def test_command_line_last_line_and_exit_code(name, capsys):
    code = cs.main([str(FIX / name), "--pdf", PDF] + flags(name))
    last = capsys.readouterr().out.strip().splitlines()[-1]
    if name in CLEAN:
        assert code == 0 and last == "RESULT: PASS"
    else:
        assert code == 1 and re.fullmatch(r"RESULT: FAIL \(\d+\)", last)


def test_wrong_page_prints_rule_sentence_and_page(capsys):
    cs.main([str(FIX / "fault-wrong-page.md"), "--pdf", PDF, "--source", "pdf", "--quotes"])
    out = capsys.readouterr().out
    assert "FAIL [quote-match] quote is on p. 22, not the cited page" in out
    assert 'sentence: "Sherd CP 131 held the largest salt microcrystals, up to 0.3–0.4 mm, inside its microcracks. (p. 12)' in out
    assert "examined: p. 12" in out


# ---- the limits themselves, on small made-up summaries ----

OPENING = "The dig found pots. The authors date them to the Bronze Age."


def make(details, opening=OPENING, headings=()):
    lines = ["# A title", "", opening, ""] + [f"## {h}\n" for h in headings] + [f"- {d}" for d in details]
    return cs.parse_summary("\n".join(lines))


def rules(fails):
    return sorted({x.rule for x in fails})


FIVE = [f"Detail number {i} says something plain. (p. {i})" for i in range(1, 6)]
PAGES = ["text"] * 41


def test_opening_limits():
    assert cs.check(make(FIVE), "pdf", PAGES) == []
    assert rules(cs.check(make(FIVE, opening="Only one sentence here."), "pdf", PAGES)) == ["opening"]
    assert rules(cs.check(make(FIVE, opening="One. Two. Three. Four."), "pdf", PAGES)) == ["opening"]
    long = "The dig found " + "very " * 60 + "old pots. They are old."
    assert rules(cs.check(make(FIVE, opening=long), "pdf", PAGES)) == ["opening"]
    assert rules(cs.check(make(FIVE, opening=""), "pdf", PAGES)) == ["opening"]


def test_abbreviations_do_not_split_sentences():
    assert len(cs.sentences("Alessandri et al. dug ca. 2017 at the site (Fig. 3). They found pots, e.g. jars.")) == 2


def test_detail_count_limits():
    assert rules(cs.check(make(FIVE[:4]), "pdf", PAGES)) == ["detail-count"]
    eight = [f"Detail number {i} says something plain. (p. {i})" for i in range(1, 9)]
    assert cs.check(make(eight), "pdf", PAGES) == []


def test_detail_of_25_words_passes_and_pointer_is_not_counted():
    d25 = " ".join(["word"] * 24) + " end. (p. 3)"
    assert cs.check(make(FIVE[:4] + [d25]), "pdf", PAGES) == []
    web = cs.Web([(2, "A long heading of many words here", "text")], "text")
    d25w = " ".join(["word"] * 24) + ' end. (sec. "A long heading of many words here")'
    fails = cs.check(make([d25w] * 5), "web", None, web)
    assert fails == [], [x.line() for x in fails]


def test_pdf_pointer_must_be_a_page_inside_the_pdf():
    assert rules(cs.check(make(FIVE[:4] + ["No pointer on this one."]), "pdf", PAGES)) == ["pointer"]
    fails = cs.check(make(FIVE[:4] + ["Past the last page. (p. 42)"]), "pdf", PAGES)
    assert rules(fails) == ["pointer"] and "page 42 is outside the PDF" in fails[0].line()
    assert rules(cs.check(make(FIVE[:4] + ['A heading pointer. (sec. "Results")']), "pdf", PAGES)) == ["pointer"]
    assert cs.check(make(FIVE[:4] + ["Small print pointer. <sub>(p. 7)</sub>"]), "pdf", PAGES) == []
    assert cs.check(make(FIVE[:4] + ["A page range. (pp. 7–8)"]), "pdf", PAGES) == []




def test_inference_needs_no_pointer():
    assert cs.check(make(FIVE[:4] + ["Read together these imply trade. (inference)"]), "pdf", PAGES) == []


def test_quoted_run_of_four_words_passes_five_fails():
    assert cs.check(make(FIVE[:4] + ["They call it “a typical briquetage set”. (p. 2)"]), "pdf", PAGES) == []
    assert rules(cs.check(make(FIVE[:4] + ["They call it “a very typical briquetage set”. (p. 2)"]), "pdf", PAGES)) == ["no-quotes"]


def test_heading_limits(article):
    four = ["Background", "Results", "Discussion", "Conclusion"]
    assert cs.check(make(FIVE, headings=four), "pdf", PAGES) == []
    assert rules(cs.check(make(FIVE, headings=four + ["Outlook"]), "pdf", PAGES)) == ["headings"]
    fails = cs.check(make(FIVE, headings=["Results"]), "pdf", ["text"] * 9)
    assert rules(fails) == ["headings"] and "9-page article" in fails[0].line()
    assert cs.check(make(FIVE), "pdf", ["text"] * 9) == []
    # a fixed name is allowed when the article really has that section (Caprolace: "3. Material and methods")
    assert cs.check(make(FIVE, headings=["Materials and methods"]), "pdf", article[0], article[1]) == []
    assert rules(cs.check(make(FIVE, headings=["Significance"]), "pdf", article[0], article[1])) == ["headings"]


def test_bold_line_counts_as_a_heading():
    s = cs.parse_summary("# T\n\n" + OPENING + "\n\n**Evidence**\n\n" + "\n".join(f"- {d}" for d in FIVE))
    assert s.headings == ["Evidence"]


def test_bold_label_with_text_on_the_line_is_a_heading_and_a_long_bold_first_line_is_the_title():
    md = ("**A very long article title of more than ten words in all, as plain Claude writes it**\n"
          "Author et al., Journal, 2019.\n\n**Question:** Was salt made here?\n\n**Findings:**\n- One.\n- Two.\n")
    s = cs.parse_summary(md)
    assert s.title.startswith("A very long article title")
    assert s.headings == ["Question", "Findings"] and len(s.details) == 2
    assert s.opening == "Author et al., Journal, 2019."






def test_show_quotes_needs_a_quote_under_each_detail(article):
    fails = cs.check(make(FIVE), "pdf", article[0], None, quotes=True)
    assert rules(fails) == ["quote-match"] and len(fails) == 5


def test_title_in_quote_marks_is_not_a_quote():
    pages, web = cs.pdf_pages(PDF), None
    title = "Salt or fish (or salted fish)? The Bronze Age specialised sites along the Tyrrhenian coast of Central Italy: New insights from Caprolace settlement"
    assert cs._is_article_title(title, pages, web)
    assert not cs._is_article_title("we suggest that SU 104 and partially SU 103 are the debris of a briquetage activity", pages, web)
