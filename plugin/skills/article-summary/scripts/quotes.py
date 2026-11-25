#!/usr/bin/env python3
"""Print the article's own sentence, word for word, from a copy in the folder.

    python3 quotes.py FILE --page N --near "WORDS"
    python3 quotes.py FILE --page 4 --near "salt microcrystals" --page 9 --near "radiocarbon"
    python3 quotes.py FILE --near "WORDS"                 # page not known: every page is searched
    python3 quotes.py FILE --first-page 366 --page 370 --near "WORDS"

FILE is a PDF or a text file (.txt, .md). WORDS are a few words of the sentence wanted, or
words describing it; the sentence on that page sharing the most of them is printed whole, as
the file has it, with the page it is on:

    p. 22: "The sentence, as printed in the article."

Pages are counted from the first page of the file; --first-page gives the number printed on
that first page when the journal numbers its pages differently. If the sentence is on another
page than the one asked for, it is still printed, with the page it was found on. A text file
has no pages (unless it has form feeds): the line then names the heading above the sentence.

Exit: 0 printed; 1 no such sentence; 2 the file cannot be opened; 3 no PDF text tool on
this machine (one line says so); 4 the pages are pictures with no text (a scan).
"""
import argparse
import pathlib
import re
import shutil
import subprocess
import sys

ABBREV = {"fig", "figs", "al", "ca", "cf", "eg", "ie", "no", "nos", "pp", "p", "vol", "ed", "eds",
          "dr", "prof", "st", "vs", "approx", "tab", "c", "e.g", "i.e", "resp", "incl", "ch", "sec"}


def read_fitz(path):
    try:
        import pymupdf as fitz
    except ImportError:
        import fitz  # older pymupdf
    with fitz.open(path) as doc:
        return [[b[4] for b in page.get_text("blocks") if len(b) > 6 and b[6] == 0] for page in doc]


def read_pypdf(path):
    try:
        from pypdf import PdfReader
    except ImportError:
        from PyPDF2 import PdfReader
    return [[page.extract_text() or ""] for page in PdfReader(path).pages]


def read_pdfminer(path):
    from pdfminer.high_level import extract_text
    return [[t] for t in extract_text(path).split("\f") if t.strip() or True][:-1] or [[""]]


def read_pdftotext(path):
    exe = shutil.which("pdftotext")
    if not exe:
        raise ImportError("pdftotext")
    out = subprocess.run([exe, "-enc", "UTF-8", path, "-"], capture_output=True, check=True)
    pages = out.stdout.decode("utf-8", "replace").split("\f")
    return [[t] for t in (pages[:-1] if len(pages) > 1 else pages)]


READERS = [("pymupdf", read_fitz), ("pypdf", read_pypdf), ("pdfminer", read_pdfminer),
           ("pdftotext", read_pdftotext)]


class NoTool(Exception):
    pass


def pdf_pages(path):
    """A list of pages, each a list of text blocks."""
    tried = []
    for name, reader in READERS:
        try:
            return reader(path)
        except ImportError:
            tried.append(name)
    raise NoTool(", ".join(tried) or "nothing")


def text_pages(path):
    """A text file: pages split at form feeds, blocks at blank lines. Headings are kept."""
    raw = pathlib.Path(path).read_text(encoding="utf-8", errors="replace")
    return [re.split(r"\n\s*\n", page) for page in raw.split("\f")]


def tidy(block):
    block = re.sub(r"(\w)-\n(?=[a-z])", r"\1", block)      # a word broken at a line end
    return re.sub(r"\s+", " ", block).strip()


def sentences(block):
    text = tidy(block)
    out, start = [], 0
    for m in re.finditer(r"[.!?][\"'”’)\]]*\s+(?=[\"'“‘(\[]?[A-Z0-9])", text):
        before = text[start:m.start()]
        last = re.findall(r"[\w.]+$", before)
        word = last[0].lower() if last else ""
        if text[m.start()] == "." and (word in ABBREV or re.fullmatch(r"[a-z]", word)):
            continue
        out.append(text[start:m.end()].strip())
        start = m.end()
    if text[start:].strip():
        out.append(text[start:].strip())
    return out


def words(text):
    return re.findall(r"[a-z0-9]+", text.lower().replace("ﬁ", "fi").replace("ﬂ", "fl"))


def score(sentence, need):
    have = words(sentence)
    if len(have) < 4:
        return 0.0
    joined, phrase = " ".join(have), " ".join(need)
    if phrase in joined:
        return 2.0
    got = sum(1 for w in need if w in have)
    return got / len(need)


def heading_above(blocks, i):
    for b in reversed(blocks[:i + 1]):
        m = re.match(r"\s*#+\s+(.*)", b)
        if m:
            return m.group(1).splitlines()[0].strip()
    return ""


def find(pages, page_index, near):
    """Best sentence: on the page asked for first, then its neighbours, then anywhere."""
    need = words(near)
    if not need:
        return None
    n = len(pages)
    if page_index is None:
        orders = [range(n)]
    else:
        rest = [i for i in range(n) if abs(i - page_index) > 1]
        orders = [[page_index], [i for i in (page_index - 1, page_index + 1) if 0 <= i < n], rest]
    for order in orders:
        best = (0.0, None)
        for p in order:
            if not 0 <= p < n:
                continue
            for b, block in enumerate(pages[p]):
                if re.match(r"\s*#+\s", block):
                    continue
                for s in sentences(block):
                    sc = score(s, need)
                    if sc > best[0]:
                        best = (sc, (p, b, s))
        if best[0] >= 0.6:
            return best[1]
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--page", type=int, action="append", default=[])
    ap.add_argument("--near", action="append", required=True)
    ap.add_argument("--first-page", type=int, default=1,
                    help="the number printed on the first page of the file (default 1)")
    a = ap.parse_args(argv)
    path = pathlib.Path(a.file)
    if not path.is_file():
        print(f"quotes.py: no such file: {path}")
        return 2
    is_pdf = path.suffix.lower() == ".pdf"
    try:
        pages = pdf_pages(str(path)) if is_pdf else text_pages(str(path))
    except NoTool as e:
        print(f"quotes.py: no PDF text tool on this machine (tried {e}); quotes cannot be read from a PDF here")
        return 3
    except Exception as e:  # a damaged or locked file
        print(f"quotes.py: cannot read {path.name}: {e}")
        return 2
    if is_pdf and not any(tidy(b) for page in pages for b in page):
        print(f"quotes.py: {path.name} has no text, its pages are pictures (a scan)")
        return 4
    paged = is_pdf or len(pages) > 1
    missing = 0
    for k, near in enumerate(a.near):
        asked = a.page[k] if k < len(a.page) else None
        hit = find(pages, asked - a.first_page if (asked is not None and paged) else None, near)
        if not hit:
            where = f" on or near p. {asked}" if asked is not None else ""
            print(f'no sentence found{where} for "{near}"')
            missing += 1
            continue
        p, b, sentence = hit
        if paged:
            found = p + a.first_page
            label = f"p. {found}" + (f" (not p. {asked})" if asked is not None and asked != found else "")
        else:
            head = heading_above(pages[p], b)
            label = f'under "{head}"' if head else "text copy"
        print(f'{label}: "{sentence}"')
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
