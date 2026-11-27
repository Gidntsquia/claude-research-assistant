#!/usr/bin/env python3
"""Rewrite the fixtures in this folder: clean Caprolace summaries and one planted fault each.

    python3 tools/fixtures/make_fixtures.py

Every sentence, page and quote was taken by hand from test-set/caprolace.pdf / .html.
The first line of each fixture holds the checker flags it is meant to be run with.
"""
import pathlib

HERE = pathlib.Path(__file__).parent
OPEN = ("This article reports a 2017 excavation on two small islands in the Caprolace lagoon, central Italy. "
        "The authors argue that the southern island held a Middle Bronze Age workshop, most likely making salt by briquetage. "
        "They also suggest that fish products may have been processed at similar coastal sites.")
TITLE = "# Salt or fish (or salted fish)? New insights from Caprolace settlement (Alessandri et al. 2019)"
# (heading or None, sentence, pdf page, web pointer, quote)
D = [
 ("Background", "Briquetage boils brine in special vessels, which are then broken to take out the salt cakes.", 2,
  'sec. "2.1 Salt production in Europe"', "which were then broken to extract the salt cakes"),
 (None, "Before this study, no Bronze Age site in Italy had produced evidence of fish processing.", 7,
  'sec. "2.6 Evidence of fish consumption and processing in Italy"', "evidence of fish processing has never been found in Bronze Age Italian sites"),
 ("Results", "Wood from 94–96 cm deep in the peat core dates to 1606–1433 cal BCE.", 10,
  'sec. "4.1 Environmental reconstruction"', "Results from the 14C analyses are 1606–1433 cal BCE"),
 (None, "Layer SU 202 was only partly excavated, so the authors cannot say whether its pottery sample is representative.", 13,
  'sec. "4.2 Pottery typo-chronology and contexts"', "it is not possible to know whether our sample is statistically representative"),
 (None, "Sherd CP 131 held the largest salt microcrystals, up to 0.3–0.4 mm, inside its microcracks.", 22,
  "Fig. 20", "in CP 131 we found the largest NaCl microcrystals"),
 ("Discussion", "The authors suggest that SU 104 and part of SU 103 are debris from briquetage, though the chemistry was not conclusive.", 28,
  'sec. "5.1 Content and use"', "we suggest that SU 104 and partially SU 103 are the debris of a briquetage activity"),
 (None, "They suggest the “fish hypothesis” might be a viable line of research for the other vessel shapes.", 31,
  'sec. "6. Conclusion"', "might be a viable line of research"),
]


def build(form, quotes=False, details=None, note=""):
    details = D if details is None else details
    out = [f"<!-- check: --source {form}" + (" --quotes" if quotes else "") + " -->", f"<!-- {note} -->", TITLE, "", OPEN]
    for h, sent, page, webp, q in details:
        if h:
            out += ["", f"## {h}", ""]
        out.append(f"- {sent} " + (f"(p. {page})" if form == "pdf" else f"({webp})"))
        if quotes and q:
            out.append(f"  > “{q}”")
    return "\n".join(out) + "\n"


def swap(i, **kw):
    keys = ["h", "sent", "page", "webp", "q"]
    d = list(D)
    row = dict(zip(keys, d[i])); row.update(kw)
    d[i] = tuple(row[k] for k in keys)
    return d


def w(name, text):
    (HERE / name).write_text(text, encoding="utf-8")


w("clean-pdf.md", build("pdf", note="passes every rule"))
w("clean-pdf-quotes.md", build("pdf", quotes=True, note='passes every rule, as shown after "show quotes"'))

w("fault-invented-quote.md", build("pdf", quotes=True, details=swap(2, q="the wood sample proves that forty households lived on the island"),
  note="fault: the quote under detail 3 is nowhere in the article; fails quote-match only"))
w("fault-wrong-page.md", build("pdf", quotes=True, details=swap(4, page=12),
  note="fault: detail 5 cites p. 12, its quote is on p. 22; fails quote-match only"))
extra = [(None, "The excavation took place on two small islands in the lagoon.", 1, 'sec. "Abstract"', None),
         (None, "The lagoon lies in the Circeo National Park near Sabaudia.", 7, 'sec. "3.1 Description of the site"', None)]
w("fault-nine-details.md", build("pdf", details=extra + D, note="fault: nine details; fails detail-count only"))
LONG = ("The authors suggest that layer SU 104 and part of layer SU 103 are debris left by a briquetage "
        "activity, though chemical analyses were not conclusive.")
assert len(LONG.split()) == 26, len(LONG.split())
w("fault-26-word-detail.md", build("pdf", details=swap(5, sent=LONG), note="fault: detail 6 has 26 words; fails detail-length only"))
fixed = [(h, *x[1:]) for h, x in zip(["Research question", None, "Evidence", None, None, "Limits", None], D)]
w("fault-fixed-sections.md", build("pdf", details=fixed,
  note="fault: headings are the old fixed section names, not this article's; fails headings only"))
w("fault-quote-by-default.md", build("pdf", details=swap(1,
  sent="The authors write that “evidence of fish processing has never been found in Bronze Age Italian sites”."),
  note="fault: detail 2 shows a 13-word quote without being asked; fails no-quotes only"))
w("fault-not-stated.md", build("pdf", details=swap(6, sent="Sample size for the chemical analyses: not stated."),
  note='fault: detail 7 reads "not stated"; fails not-stated only'))
