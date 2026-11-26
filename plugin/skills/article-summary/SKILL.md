---
name: article-summary
description: Summarize journal articles the way the professor likes them (short, plain, each detail with its page) and show the article's own sentences when he asks for them. Use when he pastes a DOI or an article link, brings or mentions PDFs, asks about articles in the folder or from Zotero, asks to summarize or compare papers, or asks for quotes, evidence or the article's own words in any wording.
---

Before answering, read `CLAUDE.md`, `memory/INDEX.md` and `memory/SETTINGS.md` in his folder, unless this task has already shown them to you.

# Summarizing articles

He is a professor of archaeology. He reads a summary to learn what an article says and whether to open it, and he checks what he reads against his own copy, which is why each detail points to a page.

## The default

His first version was "Too long, too cluttered": fixed sections, a quote in every bullet, about twenty bullets. So, until his settings say otherwise, a summary has this shape, called the default:

```
# <Article title> (<First author et al.> <year>)

<Opening: two or three sentences on what the article asks and what it concludes.>

- <One plain sentence, about 15 to 20 words.> (p. 4)
- <One plain sentence.> (p. 9)
```

- 5 to 8 key details, the ones a specialist wants first: the question, the material and sample, the method, the main findings with their numbers, the authors' conclusion, the limits they admit.
- Each detail ends with a pointer to the one page its supporting sentence is on: `(p. N)`. A copy with no pages gets `(sec. "Heading")`, `(Fig. N)` or `(Table N)`. A reading of your own that no single sentence states ends `(inference)`; keep those rare.
- Quotes stay hidden: the details are in your own words.
- A long article can take a few headings worded from its own sections; a short one needs none.
- Keep the authors' hedges ("may", "suggests") and sample sizes, and keep each claim as narrow as what was studied. Summaries drift toward overgeneralising, and that is the error he would mind most.
- What the article does not say is left out, with no placeholder. Only the article: nothing from memory of other work.
- The reply starts at the title line and ends with the last detail. No closing line.

All of this is the default and nothing more. What he has asked for instead (three details, prose, the methods first, quotes always shown) is in `memory/SETTINGS.md`.

Page numbers are the ones printed on the page; a file with none is counted from its first page.

## Reading

Read the whole article, page by page, keeping each page's text apart. For each detail, find the one sentence that supports it and note its page before you write; being one page off is the commonest slip.

## When he asks for the article's own words

He may put it any way ("quotes", "where does it say that"). He is checking the summary against the article, so what helps is the article's own sentence under each detail. A note on where the sentence sits is not that.

The sentences come from a script reading the copy in his folder, so they are word for word what his copy says and do not depend on your recall:

```
python3 <this skill's folder>/scripts/quotes.py "<the copy>" --page 4 --near "a few words of the sentence" --page 9 --near "..."
```

It prints one line per `--near`, such as `p. 4: "The whole sentence."` (`--first-page 366` when the journal's printed pages start at 366). Repeat the summary as you gave it and put each printed sentence on an indented line under its detail, unaltered:

```
- Wood from the peat core was dated to 1606–1433 cal BCE. (p. 10)
  > "Results from the 14C analyses are 1606–1433 cal BCE for the sample from 94–96 cm depth."
```

- The script reports the page it found the sentence on; if that differs from your pointer, correct the pointer.
- If the printed sentence does not support the detail, try other words. An `(inference)` detail gets a line saying what it rests on.
- The script reads a file. When he asks for quotes from an article that was read from the web, save it in his folder as text then (`articles/<author>-<year>-<words>.txt`, headings as `# ` lines) and run the script on that, without asking him first: he asked for the quotes, and the copy is how they are made.
- Exit 3 means the session has no PDF text tool: install `pymupdf` or `pypdf` if you can and run it again. Exit 4 means the pages are pictures: copy each sentence by eye from the page image and say in the first line that a scan may be misread.
- If the sentences still cannot be shown (the script cannot run, or you are prevented from reproducing them), the first line of the reply says plainly that the quotes could not be shown. Then give, for each detail, its page and the first words of the paragraph, so he can find it. If he objects, he is right that those are not quotes: say so in a line, without defending it, and try again if there is another way.

## Getting the article

For a DOI or link, look it up at `https://api.openalex.org/works/doi:<DOI>` (`open_access.is_oa`, `oa_url`, `locations`).

- An open copy: prefer a PDF to a web page, since only a PDF has pages; try the publisher's `pdf_url` first, then repositories. Keep it as `articles/<first author>-<year>-<two or three title words>.pdf`. Apart from that and a text copy saved for quotes, leave no working files in his folder.
- No open copy (`is_oa` false): say it is paywalled, give the title, authors, year and journal, then the abstract (OpenAlex's `abstract_inverted_index` put back in order, or Crossref's), labelled as the abstract and not the article. One sentence asks for the PDF from his library. No key details: nothing was read to base them on.
- A copy is listed but cannot be read: the same reply, without the word paywalled: the title, what is known, one sentence asking for the PDF.

In all of this he does not care how the text was reached. Leave out addresses, servers, refused requests and tools; say only which copy you read if it matters (a preprint, a scan with unreadable pages).

PDFs he brings: read every page, tables included; one summary per article in the order given.

Several articles: one summary each, then `## Across these articles` with agreements and disagreements, each point pointing into both articles by author, year and page. When the articles ask different questions, say so and compare what they share: evidence, method, how far each generalises.

Scans (pages with no selectable text): read the page images. If you can, summarize as usual and say in the first line that a scan may be misread; if you cannot, say so and ask for another copy.

Zotero: if Zotero tools are connected, read the item's attached PDF; if not, ask for the DOI or the PDF.

## Order of work

Read; then the discussion-memory skill, which sets up a new folder's `memory/` and holds how a subject is kept; then the summary whole, as the last thing in your turn.
