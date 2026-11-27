# Claude Research Assistant 🏺

<!-- TODO: screenshot of the assistant answering in Claude Desktop -->

A plugin for [Claude Desktop](https://claude.ai/download) that turns a folder on your computer into a
research assistant for journal articles. Give it a DOI, a link or a PDF and it writes a short summary
in which each point carries its page number. It keeps notes on what you've discussed in plain Markdown
files inside that folder, and it changes how it answers when you tell it to. I built it for a
professor of archaeology, and it works for any field that reads papers.

## Quickstart 🚀

Requires the Claude Desktop app, signed in on a Pro plan or higher.

1. Download
   [research-assistant-plugin.zip](https://github.com/Gidntsquia/claude-research-assistant/releases/latest/download/research-assistant-plugin.zip)
   and leave it zipped.
2. In Claude Desktop, click **Plugins** in the left sidebar.
3. Click **Add plugin**, then **Upload plugin**.
4. Click **browse** and pick `research-assistant-plugin.zip` from your Downloads.
5. Click **Upload**. "Research assistant" is now in your list of plugins.
6. Click **New** at the top of the sidebar.
7. Under the message box, click **Project or folder**, then **Add folder**.
8. Pick or create a folder for it, such as `Documents/Research`, and click **Open**.

Paste a DOI or an article link and press Return, or drag PDFs into the chat. The assistant keeps its
notes in the folder you picked, so choose the same folder for later chats.

IMPORTANT: Claude asks before it fetches a page or saves a file. Click **Always allow** or
**Allow once** so it can read the article and save its notes.

To build the zip from source (needs [uv](https://docs.astral.sh/uv/)):

```
git clone https://github.com/Gidntsquia/claude-research-assistant
cd claude-research-assistant
uv run build_plugin.py                       # Writes dist/research-assistant-plugin.zip from plugin/
claude plugin validate build/research-assistant   # Optional, needs Claude Code
```

Other commands:

```
uv run --with pytest --with pymupdf pytest -q tests/tools   # Runs the tests (the clone has them, the downloads don't)
uv run --with pymupdf plugin/skills/article-summary/scripts/quotes.py FILE.pdf --page 12 --near "salt"   # Prints the article's sentence near those words
```

## Features 🔬

- A summary is two or three plain sentences followed by 5-8 details, and each detail ends with the
  page it came from.
- Ask "show me where it says that" and each point comes back with the article's own sentence and its
  page. The sentences are copied from the PDF by a script, so they match the article word for word.
- For a paywalled article it gives the abstract and asks you for the PDF from your library.
- A scanned PDF with no text is reported as a scan, and no quotes are made up for it.
- It remembers each subject you discuss with the date, your view and its own. Ask "where did we leave
  the Beaker question?" in a later chat and it picks up from there.
- "That's wrong" corrects what it remembered and "forget that" erases it.
- "Be shorter" or "less formal" takes effect in the next reply and is kept for every later chat.
- Three presets come with it: quick read, full breakdown and devil's advocate. You can reword what
  any of them does.
- "What are my settings?" lists what it has saved, and "go back to the defaults" undoes them.
- The memory is a small index plus one file per subject, so it stays quick to read after hundreds of
  chats.

## Documentation 📚

More details in the
[wiki](https://github.com/Gidntsquia/claude-research-assistant/wiki):

- [Using The Research Assistant](https://github.com/Gidntsquia/claude-research-assistant/wiki/Using-The-Research-Assistant) — setup clicks, things to say, optional extras

## License 📄

[MIT](LICENSE). The two test articles, `tests/test-set/caprolace.pdf` and `caprolace-scanned.pdf`, are
copies of Alessandri et al. 2019 from PLoS ONE and are CC-BY, as listed in
[tests/test-set/MANIFEST.md](tests/test-set/MANIFEST.md).
