#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pymupdf"]
# ///
"""Score one article summary against the short format, and show why it fails.

    uv run check_summary.py SUMMARY.md --pdf ARTICLE.pdf --html ARTICLE.html --source pdf|web [--quotes] [--json]

--source says which copy the summary was written from: `pdf` (pointers are pages)
or `web` (the DOI's web page, which has no page numbers; pointers are section
headings, figures or tables). --quotes is for a summary made after "show quotes".

Rules (each failure prints the rule, the full sentence and what was examined):
  opening        2-3 sentences, at most 60 words, before the first detail or heading
  detail-count   5 to 8 key details (list items)
  detail-length  each detail at most 25 words, its pointer not counted
  pointer        pdf: each detail ends (p. N), N a page of the PDF
                 web: it ends (sec. "Heading"), (Fig. N) or (Table N), present in the HTML;
                      (p. N) fails: no page numbers in the web copy
                 a detail labelled (inference) needs no pointer
  no-quotes      no quoted run of 5 or more words (skipped with --quotes)
  headings       at most 4; none when the PDF has under 10 pages; none of the old
                 seven fixed names unless the article has a section of that name
  not-stated     the words "not stated" appear nowhere
  quote-match    (--quotes only) under each detail, a quote found word for word on the
                 cited page or under the cited heading

The last line is `RESULT: PASS` or `RESULT: FAIL (n)`. Exit code 0 only on PASS.
The old seven-section checker is check_summary_v1.py.
"""
from __future__ import annotations

import argparse
import html as htmllib
import json
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from html.parser import HTMLParser

RULES = ["opening", "detail-count", "detail-length", "pointer", "no-quotes", "headings", "not-stated"]
QUOTE_RULE = "quote-match"
FIXED_NAMES = ["Research question", "Site, region and period", "Materials and methods",
               "Evidence", "Argument", "Significance", "Limits"]
MAX_OPENING_WORDS, MAX_DETAIL_WORDS, MIN_DETAILS, MAX_DETAILS = 60, 25, 5, 8
MAX_HEADINGS, MIN_PAGES_FOR_HEADINGS, MIN_QUOTED_RUN = 4, 10, 5

OPENQ, CLOSEQ = "\"“„«", "\"”»"
QUOTED = re.compile("[" + OPENQ + "]([^" + OPENQ + CLOSEQ + "]+)[" + CLOSEQ + "]")
PAGE_PTR = re.compile(r"\(\s*pp?\.\s*(\d+(?:\s*[-–—,]\s*\d+)*)\s*\)")
SEC_PTR = re.compile(r"\(\s*sec(?:tion|\.)?\s*[" + OPENQ + "](.+?)[" + CLOSEQ + r"]\s*\)", re.I)
FIG_PTR = re.compile(r"\(\s*(Fig(?:ure|\.)?|Table)\s*(\d+)\s*\)", re.I)
INFERENCE = re.compile(r"\(\s*inference\s*\)|^\s*inference\s*:", re.I)
ANY_PTR = re.compile("|".join(p.pattern for p in (PAGE_PTR, SEC_PTR, FIG_PTR)), re.I)
ABBREV = re.compile(r"\b(e\.g|i\.e|et al|c|ca|cf|vs|Fig|Figs|p|pp|no|sec|approx|St|Dr|cal)\.", re.I)


# ---------- text helpers ----------

def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).replace("­", "")
    text = re.sub(r"[‘’‚′]", "'", text)
    text = re.sub(r"[“”„«»]", '"', text)
    text = re.sub(r"[‐‑‒–—−]", "-", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def squash(text: str) -> str:
    """Letters and digits only: survives line-break hyphens, spacing and quote styles."""
    return re.sub(r"[^a-z0-9]", "", normalize(text))


def strip_md(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)                 # <sub>(p. 3)</sub>
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)  # links
    return re.sub(r"(\*\*|__|\*|`)", "", text).strip()


def words(text: str) -> int:
    return len([w for w in text.split() if re.search(r"\w", w)])


def sentences(text: str) -> list[str]:
    guarded = ABBREV.sub(lambda m: m.group(0).replace(".", "․"), text)
    parts = re.split(r"(?<=[.!?])[\"”)]?\s+(?=[\"“(]?[A-Z0-9])", guarded)
    return [p.replace("․", ".").strip() for p in parts if p.strip()]


def heading_key(text: str) -> str:
    """Compare headings without numbering, case, punctuation or plural s."""
    text = re.sub(r"^\s*\d+(\.\d+)*\.?\s+", "", normalize(text))
    return " ".join(re.sub(r"s$", "", w) for w in re.findall(r"[a-z0-9]+", text))


# ---------- the summary ----------

@dataclass
class Detail:
    raw: str                      # the sentence as written, markdown stripped
    sub: list = field(default_factory=list)   # lines under it (quotes after "show quotes")

    @property
    def inference(self) -> bool:
        return bool(INFERENCE.search(self.raw))

    @property
    def pointer(self) -> str | None:
        """The pointer the sentence ends with, or None."""
        m = None
        for m in ANY_PTR.finditer(self.raw):
            pass
        if m and not re.search(r"\w", self.raw[m.end():]):
            return m.group(0)
        return None

    @property
    def body(self) -> str:
        p = self.pointer
        text = self.raw[: self.raw.rfind(p)] if p else self.raw
        return INFERENCE.sub("", text).strip()


@dataclass
class Summary:
    title: str | None = None
    opening: str = ""
    headings: list = field(default_factory=list)
    details: list = field(default_factory=list)
    lines: list = field(default_factory=list)     # every visible line, markdown stripped


def parse_summary(md: str) -> Summary:
    md = re.sub(r"<!--.*?-->", "", md, flags=re.S)
    s = Summary()
    opening_open, seen_text = True, False
    for line in md.splitlines():
        if not line.strip() or re.match(r"^\s*([-*_]\s*){3,}$", line):
            continue
        plain = strip_md(line)
        if not plain:
            continue
        s.lines.append(plain)
        h = re.match(r"^\s{0,3}#{1,6}\s+(.*?)\s*#*\s*$", line)
        bold = re.match(r"^\s*(\*\*|__)(.+?)\1:?\s*$", line)
        item = re.match(r"^(\s*)([-*+•]|\d+[.)])\s+(.*)$", line)
        label = None if (h or bold) else re.match(r"^\s*(\*\*|__)([^*_]{1,60}?):?\1:?\s+(\S.*)$", line)
        is_title_spot = not seen_text and s.title is None and not s.headings
        if h or (bold and (words(bold.group(2)) <= 10 or is_title_spot)):
            text = strip_md(h.group(1) if h else bold.group(2)).rstrip(":")
            if is_title_spot:
                s.title = text            # the first heading above any text is the title
            else:
                s.headings.append(text)
                opening_open = False
            continue
        if label:                         # "**Methods:** The team ..." is a heading with its text on the same line
            s.headings.append(strip_md(label.group(2)).rstrip(":"))
            opening_open = False
            seen_text = True
            continue
        seen_text = True
        if item and len(item.group(1).expandtabs(4)) < 2:
            s.details.append(Detail(raw=strip_md(item.group(3))))
            opening_open = False
        elif s.details and (item or line.lstrip().startswith(">") or line.startswith(("  ", "\t"))):
            s.details[-1].sub.append(strip_md(re.sub(r"^\s*(>|[-*+•]|\d+[.)])\s*", "", line)))
        elif opening_open:
            s.opening = (s.opening + " " + plain).strip()
    return s


# ---------- the article ----------

def pdf_pages(path: str) -> list[str]:
    import pymupdf

    with pymupdf.open(path) as doc:
        return [page.get_text() for page in doc]


def printed_offset(pages: list[str]) -> int:
    """Printed page number minus PDF page number, when the pages carry running numbers
    (a journal article printed as pp. 366-384); 0 when they do not."""
    votes: dict[int, int] = {}
    for i, text in enumerate(pages, 1):
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        for l in lines[:4] + lines[-4:]:
            for n in re.findall(r"(?<![\d/.])\b(\d{1,4})\b(?!\s*/)", l) if len(l) < 60 else []:
                o = int(n) - i
                if o > 0:
                    votes[o] = votes.get(o, 0) + 1
    if votes:
        o, v = max(votes.items(), key=lambda kv: kv[1])
        if v >= max(3, 0.6 * len(pages)):
            return o
    return 0


class _Sections(HTMLParser):
    """Headings (h1-h4) and the text under each, from a saved article page."""
    SKIP = {"script", "style", "noscript", "svg", "template"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.sections = [[0, "", []]]   # level, heading, text chunks
        self._h, self._skip = None, 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1
        elif re.fullmatch(r"h[1-4]", tag):
            self._h = [int(tag[1]), []]

    def handle_endtag(self, tag):
        if tag in self.SKIP:
            self._skip = max(0, self._skip - 1)
        elif re.fullmatch(r"h[1-4]", tag) and self._h:
            self.sections.append([self._h[0], " ".join("".join(self._h[1]).split()), []])
            self._h = None

    def handle_data(self, data):
        if self._skip:
            return
        if self._h:
            self._h[1].append(data)
        self.sections[-1][2].append(data)


@dataclass
class Web:
    sections: list      # (level, heading, text)
    text: str

    def under(self, heading: str) -> list[str]:
        """Text under every heading of this name, down to the next heading of the same or a higher level."""
        key, out = heading_key(heading), []
        for i, (level, h, _) in enumerate(self.sections):
            if level and heading_key(h) == key:
                chunk = [self.sections[i][2]]
                for lv, _, t in self.sections[i + 1:]:
                    if lv <= level:
                        break
                    chunk.append(t)
                out.append(" ".join(chunk))
        return out

    def has_label(self, kind: str, n: str) -> bool:
        names = ["fig", "figure"] if kind.lower().startswith("fig") else ["table"]
        return any(re.search(rf"\b{w}\.?\s*{n}\b", normalize(self.text)) for w in names)


def load_web(path: str) -> Web:
    p = _Sections()
    p.feed(open(path, encoding="utf-8", errors="replace").read())
    secs = [(lv, h, " ".join(" ".join(t).split())) for lv, h, t in p.sections]
    return Web(secs, " ".join(t for _, _, t in secs))


def pdf_section_titles(pages: list[str]) -> set[str]:
    return {heading_key(l) for t in pages for l in t.splitlines() if 0 < len(l.strip()) < 80}


# ---------- the rules ----------

@dataclass
class Failure:
    rule: str
    why: str
    sentence: str
    examined: str

    def line(self) -> str:
        return f'FAIL [{self.rule}] {self.why}\n      sentence: "{self.sentence}"\n      examined: {self.examined}'


def quoted_runs(text: str) -> list[str]:
    return [q for q in QUOTED.findall(text) if words(q) >= MIN_QUOTED_RUN]


def check(summary: Summary, source: str, pages: list[str] | None = None, web: Web | None = None,
          quotes: bool = False) -> list[Failure]:
    f: list[Failure] = []
    n_pages = len(pages) if pages else None
    offset = printed_offset(pages) if pages else 0

    # opening
    sents = sentences(summary.opening)
    if not summary.opening:
        f.append(Failure("opening", "no opening before the first detail or heading", "", "the lines above the first detail"))
    else:
        if not 2 <= len(sents) <= 3:
            f.append(Failure("opening", f"{len(sents)} sentence(s), wanted 2 to 3", summary.opening, "the opening"))
        if words(summary.opening) > MAX_OPENING_WORDS:
            f.append(Failure("opening", f"{words(summary.opening)} words, limit {MAX_OPENING_WORDS}", summary.opening, "the opening"))

    # detail-count
    n = len(summary.details)
    if not MIN_DETAILS <= n <= MAX_DETAILS:
        extra = summary.details[MAX_DETAILS].raw if n > MAX_DETAILS else (summary.details[-1].raw if n else "")
        f.append(Failure("detail-count", f"{n} details, wanted {MIN_DETAILS} to {MAX_DETAILS}", extra,
                         f"all {n} list items" + (f"; this is number {MAX_DETAILS + 1}" if n > MAX_DETAILS else "")))

    for i, d in enumerate(summary.details, 1):
        where = f"detail {i}"
        # detail-length
        if words(d.body) > MAX_DETAIL_WORDS:
            f.append(Failure("detail-length", f"{words(d.body)} words, limit {MAX_DETAIL_WORDS} (pointer not counted)", d.raw, where))
        # pointer
        ptr = d.pointer
        if d.inference:
            pass
        elif ptr is None:
            want = "(p. N)" if source == "pdf" else '(sec. "Heading"), (Fig. N) or (Table N)'
            f.append(Failure("pointer", f"does not end with {want}", d.raw, where))
        elif source == "pdf":
            m = PAGE_PTR.fullmatch(ptr)
            if not m:
                f.append(Failure("pointer", "the PDF was read, so the pointer must be a page: (p. N)", d.raw, f"{where}, pointer {ptr}"))
            elif n_pages:
                for num in map(int, re.findall(r"\d+", m.group(1))):
                    if not (1 <= num <= n_pages or (offset and 1 + offset <= num <= n_pages + offset)):
                        rng = f"1-{n_pages}" + (f" or printed {1 + offset}-{n_pages + offset}" if offset else "")
                        f.append(Failure("pointer", f"page {num} is outside the PDF", d.raw, f"p. {num}; the PDF has pages {rng}"))
        else:
            if PAGE_PTR.fullmatch(ptr):
                f.append(Failure("pointer", "no page numbers in the web copy", d.raw, f"{where}, pointer {ptr}"))
            elif web is not None:
                ms, mf = SEC_PTR.fullmatch(ptr), FIG_PTR.fullmatch(ptr)
                if ms and not web.under(ms.group(1)):
                    f.append(Failure("pointer", "no such heading on the web page", d.raw, f'heading "{ms.group(1)}"'))
                elif mf and not web.has_label(mf.group(1), mf.group(2)):
                    f.append(Failure("pointer", "no such figure or table on the web page", d.raw, f"{mf.group(1)} {mf.group(2)}"))
        # no-quotes / quote-match
        if not quotes:
            for text, shown in [(d.body, d.raw)] + [(ANY_PTR.sub("", t), f"{d.raw} / {t}") for t in d.sub]:
                for q in quoted_runs(text):
                    f.append(Failure("no-quotes", f"quoted run of {words(q)} words shown by default", shown, f'{where}: "{q}"'))
        elif not d.inference:
            f.extend(_quote_match(d, where, source, pages, web, offset))

    if not quotes:
        for q in quoted_runs(summary.opening):
            if _is_article_title(q, pages, web):
                continue                # naming the article by its title is not quoting from it
            f.append(Failure("no-quotes", f"quoted run of {words(q)} words shown by default", summary.opening, f'the opening: "{q}"'))

    # headings
    if len(summary.headings) > MAX_HEADINGS:
        f.append(Failure("headings", f"{len(summary.headings)} headings, limit {MAX_HEADINGS}",
                         summary.headings[MAX_HEADINGS], "headings: " + " | ".join(summary.headings)))
    if n_pages is not None and n_pages < MIN_PAGES_FOR_HEADINGS and summary.headings:
        f.append(Failure("headings", f"headings in the summary of a {n_pages}-page article (none under {MIN_PAGES_FOR_HEADINGS} pages)",
                         summary.headings[0], "headings: " + " | ".join(summary.headings)))
    titles = set()
    if web is not None:
        titles |= {heading_key(h) for lv, h, _ in web.sections if lv}
    if pages:
        titles |= pdf_section_titles(pages)
    fixed = {heading_key(x): x for x in FIXED_NAMES}
    for h in ([summary.title] if summary.title else []) + summary.headings:
        k = heading_key(h)
        if k in fixed and k not in titles:
            f.append(Failure("headings", f'fixed section name "{fixed[k]}", not a section title of this article', h,
                             "the article's section titles (web page and PDF)"))

    # not-stated
    for line in summary.lines:
        if re.search(r"\bnot\s+stated\b", line, re.I):
            f.append(Failure("not-stated", 'the words "not stated"', line, "every line of the summary"))
    return f


def _is_article_title(q: str, pages, web) -> bool:
    """True when the quoted run is the article's own title: a level-1 heading of the web page,
    or within the first 80 words of the PDF's first page."""
    key = normalize(q)
    if web is not None and any(lv == 1 and key and (key in normalize(h) or normalize(h) in key) and words(h) >= 3
                               for lv, h, _ in web.sections):
        return True
    return bool(pages) and key in normalize(" ".join(pages[0].split()[:80]))


def _quote_match(d: Detail, where: str, source: str, pages, web, offset) -> list[Failure]:
    quotes_ = [q for line in d.sub for q in QUOTED.findall(line)]
    if not quotes_:
        return [Failure(QUOTE_RULE, "no quote under this detail", d.raw, where)]
    out, ptr = [], d.pointer or ""
    for q in quotes_:
        sq = squash(q)
        if source == "pdf" and pages:
            m = PAGE_PTR.fullmatch(ptr)
            cited = [int(x) for x in re.findall(r"\d+", m.group(1))] if m else []
            if m and len(cited) == 2 and re.search(r"[-–—]", m.group(1)):
                cited = list(range(cited[0], cited[1] + 1))
            found = [i for i, t in enumerate(pages, 1) if sq and sq in squash(t)]
            ok = any(c in found or (offset and c - offset in found) for c in cited)
            if not found:
                out.append(Failure(QUOTE_RULE, "quote not found anywhere in the PDF", f'{d.raw} / "{q}"',
                                   f"p. {', '.join(map(str, cited)) or '?'} and all {len(pages)} pages"))
            elif not ok:
                shown = ", ".join(str(p + offset) if offset else str(p) for p in found)
                out.append(Failure(QUOTE_RULE, f"quote is on p. {shown}, not the cited page", f'{d.raw} / "{q}"',
                                   f"p. {', '.join(map(str, cited)) or '?'}"))
        elif source == "web" and web is not None:
            ms = SEC_PTR.fullmatch(ptr)
            if ms:
                if not any(sq in squash(t) for t in web.under(ms.group(1))):
                    else_ = "it is elsewhere on the page" if sq in squash(web.text) else "it is nowhere on the page"
                    out.append(Failure(QUOTE_RULE, f"quote not found under the cited heading; {else_}", f'{d.raw} / "{q}"',
                                       f'heading "{ms.group(1)}"'))
            elif sq not in squash(web.text):
                out.append(Failure(QUOTE_RULE, "quote not found anywhere on the web page", f'{d.raw} / "{q}"', f"the whole web page ({ptr})"))
    return out


def by_rule(failures: list[Failure], quotes: bool = False) -> dict:
    rules = RULES + ([QUOTE_RULE] if quotes else [])
    return {r: [x for x in failures if x.rule == r] for r in rules}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("summary")
    ap.add_argument("--pdf", help="the article PDF (page count, page text)")
    ap.add_argument("--html", help="the DOI's web page as saved (headings, figures)")
    ap.add_argument("--source", choices=["pdf", "web"], required=True, help="which copy the summary was written from")
    ap.add_argument("--quotes", action="store_true", help='the summary was made after "show quotes"')
    ap.add_argument("--json", action="store_true", help="print one JSON object instead of text")
    a = ap.parse_args(argv)
    if a.source == "pdf" and not a.pdf:
        ap.error("--source pdf needs --pdf")
    if a.source == "web" and not a.html:
        ap.error("--source web needs --html")

    s = parse_summary(open(a.summary, encoding="utf-8").read())
    pages = pdf_pages(a.pdf) if a.pdf else None
    web = load_web(a.html) if a.html else None
    fails = check(s, a.source, pages, web, a.quotes)
    rules = by_rule(fails, a.quotes)
    if a.json:
        print(json.dumps({"result": "PASS" if not fails else "FAIL", "failures": len(fails),
                          "rules": {r: ("pass" if not v else "fail") for r, v in rules.items()},
                          "details": len(s.details), "headings": s.headings,
                          "opening_words": words(s.opening), "opening_sentences": len(sentences(s.opening)),
                          "why": [vars(x) for x in fails]}, ensure_ascii=False, indent=1))
        return 1 if fails else 0
    print(f"summary: {a.summary}  (source read: {a.source}" + (", with quotes" if a.quotes else "") + ")")
    print(f"opening: {len(sentences(s.opening))} sentences, {words(s.opening)} words | details: {len(s.details)} | "
          f"headings: {len(s.headings)} | words in all: {sum(words(l) for l in s.lines)}")
    for r, v in rules.items():
        print(f"{'pass' if not v else 'FAIL':4}  {r}" + (f"  ({len(v)})" if v else ""))
    for x in fails:
        print(x.line())
    print("RESULT: PASS" if not fails else f"RESULT: FAIL ({len(fails)})")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
