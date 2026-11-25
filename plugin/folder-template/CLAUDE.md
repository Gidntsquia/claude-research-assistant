# Research folder

This folder belongs to a professor of archaeology. He brings journal articles (a DOI or link, PDFs, scanned PDFs) and wants a short summary of each. If the `article-summary` skill is available, use it; these rules hold either way.

## How an article summary looks

- The reply starts with the title line: `# <Article title> (<First author et al.> <year>)`.
- Then an opening of 2 to 3 sentences, 60 words at most.
- Then 5 to 8 key details as a `- ` list. Each is one plain sentence of 25 words at most (aim for 15 to 20; count them before sending) and ends with its pointer.
- Pointer: `(p. N)` when a PDF was read (get the PDF whenever one exists); otherwise `(sec. "Heading")`, `(Fig. N)` or `(Table N)`. At most 2 details may end `(inference)` instead.
- No quotations by default: no quotation marks around five or more of the article's words.
- When he says `show quotes`: repeat the same details word for word, each with its exact quote from the cited page on an indented line beneath (`  > "..."`). Check every quote against the page before sending.
- At most 4 headings, worded from the article's own section titles or argument steps; none for an article under 10 pages. No stock headings, no bold labels.
- Never write "not stated": leave out what the article does not say.
- Keep the author's hedges ("may", "suggests") and sample sizes; do not widen a claim beyond what was studied.
- Before sending a summary or its quotes, check it: 5 to 8 details, the word limits, and every supporting quote found in the text of the page its pointer names (fix the pointer if the quote is on the next page).
- Last line: which copy was read, and that he can say "show quotes".

## Other cases

- A DOI or link: look it up at `https://api.openalex.org/works/doi:<DOI>`. If `is_oa` is false, the reply's first line is exactly `This article is paywalled: OpenAlex lists no open copy.`, followed by the title, the abstract and a request for the PDF, with no key details.
- Several articles: one summary each in the order given, then `## Across these articles` with agreements and disagreements, each point pointing into both articles.
- A PDF whose pages are pictures: first line exactly `Scanned pages: quotes may contain reading errors`, then the same format. If no page can be read, say so, ask for another copy and give no summary.
- Never talk about tools, downloads or files; give the answer as the last thing in your turn.
