---
name: article-summary
description: Summarize journal articles as a short opening and 5 to 8 plain key details, each ending with the page it came from; exact quotes on request ("show quotes"). Use whenever the user pastes a DOI or an article link, drags in or mentions PDF files, asks about articles in the folder, asks for an article from Zotero, asks to summarize, compare or "tell me the key details" of a paper, or says "show quotes".
---

# Summarizing articles

The reader is a professor of archaeology. He reads the summary to decide what an article says and whether to open it. He wants it short and uncluttered: a few plain sentences, each with a small pointer to where it comes from. He does not want quotations unless he asks. When he asks, every quote must be in the article exactly as shown, on the page shown.

## 1. The reply, in full

Your reply starts with the title line. Nothing comes before it (no greeting, no "here is the summary").

```
# <Article title> (<First author et al.> <year>)

<Opening: 2 or 3 sentences, 60 words at most. What the article is about and what it concludes.>

## <a heading taken from the article>

- <One plain sentence, 25 words at most.> (p. 4)
- <One plain sentence.> (p. 9)

## <another heading from the article>

- <One plain sentence.> (p. 17)
- <One plain sentence.> (inference)

Read from <the publisher's PDF | a repository copy | the web page | your PDF>. Say "show quotes" to see the sentence behind each detail.
```

The rules, each of which he will notice if broken:

- **Opening.** Two or three sentences and no more than 60 words; aim for 45. Write whole words where an abbreviation would need a full stop ("about", not "c."; "BCE", not "B.C."), because a stray full stop reads as a sentence end.
- **Key details.** At least 5 and at most 8 in all, as a plain `- ` list. Each is one sentence of at most 25 words, not counting the pointer; aim for 15 to 20, and give one fact per detail rather than two joined by "and". Every number, unit and abbreviation counts as a word ("13 mm in SU 104" is five). Pick the details a specialist would want first: the question, the material and sample, the method, the main findings with their numbers, the authors' conclusion, the limits they admit.
- **Pointer.** Every detail ends with exactly one pointer, the last thing on the line:
  - a PDF was read: `(p. N)`, one page, the page the supporting sentence is on;
  - only a web page was read: `(sec. "Heading")` with the heading exactly as the article prints it, numbering included, of the section the sentence is in; or `(Fig. N)` or `(Table N)` when the detail comes from a figure or table. Never a page number for a web page: it has none.
  - a detail that is your own reading and that no one sentence states ends `(inference)` instead. At most 2 of these in a summary; prefer none.
- **No quotations.** Put the details in your own words. Do not put quotation marks around any run of five or more of the article's words. A term of one to four words may be quoted.
- **Headings.** At most 4, each worded from the article's own section titles or the steps of its argument (for example "Briquetage at Caprolace", not "Evidence"). Do not use a stock set of headings. An article of fewer than 10 pages gets no headings at all: the list follows the opening directly. Write headings as `## ` lines only; do not use bold text as a heading or as a label at the start of a line.
- **Nothing is "not stated".** If the article does not say something, leave it out. Never write "not stated", "not specified" or "N/A".
- **Keep the author's hedges and sample sizes.** If the article says "may", "suggests", "in this sample" or "preliminary", so does the detail. Give the numbers studied (14 burials, 85 skeletons, 3 cores). Do not widen a claim beyond the sites, samples, periods or numbers studied, and keep the past tense for what was found. Language models overgeneralize when they summarize; this is the main error to avoid.
- **Only the article.** Nothing from memory of other work, from reviews, or from the abstract of a different version.
- **Last line.** One line saying which copy you read and that he can say "show quotes". If pages could not be read, name them there.

**Check before you send, every time.** Do not send a summary you have not checked. If you can run code, run one check over the finished text; otherwise do each step by hand:

1. The opening has 2 or 3 sentences and at most 55 words.
2. There are 5 to 8 details. Nine is a failure: merge or drop one.
3. Each detail has at most 22 words before its pointer (the limits are 60 and 25; the margin covers a miscount).
4. Each detail's supporting sentence is in the text of the page its pointer names. Test it: strip both the sentence and that page's text to letters and digits and see that one contains the other. If it is found on a neighbouring page instead, change the pointer to that page. A sentence that runs over a page break belongs to the page that holds the part you will quote.

Fix what fails and run the check again until it is clean.

Page numbers: use the number printed on the page. If the pages carry no printed number of their own, count from the first page of the PDF. When the printed numbers do not start at 1 (a journal issue running 366 to 384, say), work out the shift once (printed number = position in the file + shift), keep each page's text under its printed number, and use that one numbering everywhere. Being one page off is the commonest way a pointer goes wrong.

## 2. Read before writing

1. Read the whole article, page by page, keeping each page's text apart so that page numbers stay true. If a PDF will not open directly, take its text out page by page with whatever the session offers (for example Python with `pymupdf` or `pypdf`, or `pdftotext`).
2. For each detail you mean to give, first find the one sentence in the article that supports it, and note its page (or section heading) and its exact words. A detail with no such sentence is either dropped or marked `(inference)`.
3. Write the summary from those sentences. Do not show them. Keep them: he may ask for them next.

## 3. "show quotes"

When he says `show quotes` (or asks to see the quotes, the evidence or the sources for a summary), repeat the summary exactly as you gave it: the same title, opening, headings and details, word for word and in the same order. Under each detail add one indented line with the supporting quote:

```
- Wood from the peat core was dated to 1606–1433 cal BCE. (p. 10)
  > "Results from the 14C analyses are 1606–1433 cal BCE"
```

- The quote is one unbroken run of the article's own words, about 6 to 25 words, copied character for character. No joining of two passages, no ellipsis, no corrected spelling, no translation.
- The whole quote sits on the page the detail's pointer names (or under the heading it names). If the best sentence runs over a page break, quote only the part on the cited page. If you find the sentence is on a different page from the pointer you gave, correct the pointer and keep the quote.
- Choose a run with no quotation marks inside it.
- A detail marked `(inference)` gets a line saying what it rests on instead of a quote: `  > inference from the pottery counts on pp. 13–14`.
- **Check before you send; never answer "show quotes" straight from memory.** Take out the text of each cited page again and test that every quote is found in the text of the page its pointer names (compare letters and digits only, so that line breaks and hyphens do not matter). A quote found on another page means the pointer was wrong: change the pointer to the page the quote is on. A quote found nowhere is replaced by a run that is. Send only when every quote is found on its page.
- Apart from a corrected pointer, the details are the ones you gave: do not add, drop, merge or reword any, and do not remark on the earlier reply.

The last line then reads `Read from <copy>.` only.

## 4. Getting the article

**A DOI or a link.** Find the DOI (in the link, or on the page the link opens). Fetch `https://api.openalex.org/works/doi:<DOI>` and read `open_access.is_oa`, `open_access.oa_url` and the `locations` list.

- **An open copy exists** (`is_oa` is true): get a PDF of it and read that.
  - **A PDF before any web page.** Only a PDF has page numbers. Try every `pdf_url` in `locations` (the publisher's first, then repositories and preprint servers), and `oa_url` when it is a PDF, before settling for a web page of the text.
  - Fetch with the web fetch tool first; if it will not return the PDF itself, download the file another way the session allows. When a fetched PDF comes back as a saved file rather than as text, open that file and read it page by page.
  - Only if no PDF can be had, read the article's web page. Then the pointers are section headings, figures and tables, and quotes must come from the page's own text, not from a tool's retelling of it: if the fetch tool gives you a summary or a reworded page, get the page's raw text another way before quoting.
  - Keep a copy in the folder's `articles/` as `<first author>-<year>-<two or three title words>.pdf` when you can. Leave no other working files behind in his folder (text you extracted, notes, scripts): keep them out of it or delete them.
- **No open copy** (`is_oa` is false): do not go looking for another route. Reply in this shape and stop:
  1. First line, exactly: `This article is paywalled: OpenAlex lists no open copy.`
  2. Title, authors, year, journal.
  3. `Abstract (from OpenAlex, not from the article itself):` then the abstract as a paragraph. OpenAlex stores it as `abstract_inverted_index` (each word with its positions); put the words back in order. If OpenAlex has none, fetch `https://api.crossref.org/works/<DOI>` and use its `abstract`. If neither has one, say "No abstract is available from OpenAlex or Crossref."
  4. Ask him to download the PDF through his library and drag it into the chat or the folder. One line: if his library offers LibKey Nomad, its "Download PDF" button does this in one click.
  Give no key details, no list and no headings for a paywalled article, and never guess what it says.
- **An open copy is listed but every address refused**: say exactly that (it is not paywalled), give him the link to click, and ask him to drop the downloaded PDF in.

**PDFs he drags in or has placed in the folder.** Read every page of each, tables included. Give one summary per article, in the order he gave them.

**Several articles.** One full summary each (each with its own `# ` title line, opening, 5 to 8 details and "Read from" line), in the order given. Then:

```
## Across these articles

Agreements
- <point, one sentence> (<Author year>, p. N; <Author year>, p. N)

Disagreements
- <point: who says what> (<Author year>, p. N; <Author year>, p. N)
```

Every point there points into both articles, by author, year and page. Compare only on what the articles themselves say. Always give at least two points, however far apart the articles are. When they address different questions, say so in one sentence under the heading, then compare what they do share: the kind of evidence, the method, how far each author generalises, a limit each admits. Leave out the "Agreements" or the "Disagreements" list only when it would be empty; never leave out both. End with one line offering "show quotes".

**Pages that are pictures of text** (a scan: the pages have no selectable text). Look at the page images themselves.

- If you can read them: the first line of the reply, before the title line, is exactly `Scanned pages: quotes may contain reading errors`. Then the same format, with `(p. N)` counted from the first page of the file when no number is printed. For "show quotes" on a scan, look at each cited page again, one page at a time and enlarged if you can, and copy the quote character by character from what you see; do not tidy spelling or modernize. Prefer a short run of ordinary words that you can read with certainty over a longer one with figures or unusual names.
- If you cannot read them: say the pages are unreadable to you, give no summary, and ask for another copy (a PDF downloaded from the publisher, or a clearer scan).

**Zotero.** If Zotero tools are connected in this session, find the item there and read its attached PDF. If they are not, say Zotero is not connected yet (the guide has an optional step for it) and ask for the DOI or the PDF instead.

## 5. How to say it

Write for a reader who does not care how you got the text. Never mention tools, shells, agents, downloads that failed, or what you "could not verify". The "Read from" line says which copy you read, and that is all he needs. If part of the article could not be read, say which pages, in that line.

If the folder has `memory/SETTINGS.md`, follow it for tone, for what comes first and for length within the limits above. A setting never removes the pointers.

## 6. Order of work

1. Read the article and find the supporting sentence for each detail.
2. If the `discussion-memory` skill is installed, save what was covered under its subject as that skill describes, without being asked.
3. Give the summary as the last thing in your turn, whole, starting at the title line (or the scanned-pages or paywalled line). He sees only that final message: never end with a remark about notes or files, and never say the summary is "above".
