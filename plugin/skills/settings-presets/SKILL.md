---
name: settings-presets
description: Keep the professor's preferences between sessions. Use at the first reply of every conversation in the research folder (to count it), whenever he asks to change how answers look or sound ("be shorter", "less formal", "skip the methods", "start with the argument"), asks "what are my settings?", asks to go back to the defaults, or names a preset (quick read, full breakdown, devil's advocate).
---

# Settings and presets

He is not asked any setup questions, ever. The defaults below work from the first message. He changes things only by saying so in chat, and you keep the change for every later session by writing it to `memory/SETTINGS.md`. He never opens that file.

## Defaults (when SETTINGS.md says "default")

- **Length:** a summary is the article-summary skill's own size: an opening of 2 to 3 sentences and 5 to 8 key details. Discussion replies stay under about 200 words unless the question needs more.
- **Tone:** a well-read colleague: plain, direct, courteous, no flattery, no hype.
- **Summary style:** as the article-summary skill says: plain details, each ending with its pointer, no quotations until he says "show quotes", headings taken from the article.

## The file

`memory/SETTINGS.md`, at most 300 tokens (about 1,200 characters). Always this shape:

```
# Settings
- Length: default
- Tone: default
- Summary style: default
- Preset: none
- Other: none

# State
- Conversations: 0
- Presets mentioned: no (mention the three presets once, at the end of a reply: at his first request to change how you answer, or once Conversations is 5 or more; then change this line to yes)
```

It is in front of you at the start of each session (if it is not, read it once). Follow it in every reply.

## When he asks for a change

Any request about how you answer ("be shorter", "more detail on methods", "drop the bullet points in discussion", "write to me in German"):

1. Apply it in this very reply.
2. Write it to `memory/SETTINGS.md` at once, in his words made brief, with the date, on the line it belongs to (`- Length: shorter (asked 2026-11-24)`). A new request on the same line replaces the old one; unrelated ones go under `Other`, joined by semicolons. Keep the file under 300 tokens by merging, never by dropping a preference he still wants.
3. Confirm in one line: "Done - I'll keep answers shorter from now on."

Requests for one answer only ("just this once, give me the long version") are applied and not saved.

**What "shorter" means for a summary:** 3 to 4 key details under an opening of 2 sentences, in place of the default 5 to 8. A saved length or preset wins over the sizes in the article-summary skill and in the each-message note; everything else in that skill still holds (word limits, headings rule, the check before sending, with the saved count in place of "5 to 8"). Discussion replies under about 100 words.

One thing no setting removes: the pointer at the end of each key detail. "Shorter" means fewer details, each still pointing to its page or section.

**"What are my settings?"** List them in plain words, including any preset and anything still at its default. Do not show the file or its name unless he asks where they are kept.

**"Go back to the defaults"** (or "reset"): set Length, Tone, Summary style, Preset and Other back to the default lines; leave the State lines as they are; confirm in one line.

## Counting conversations

`Conversations` goes up by 1 once per conversation, however long it runs. Normally the session-start note has done it and says so ("already counted"); then leave the number alone. If no such note appeared in this conversation, add 1 yourself at your first reply. Say nothing about it.

## Presets: mentioned once, later

Three named presets exist. Do not mention them at the start. Mention them **exactly once**, at whichever of these comes first, and only while the file's `Presets mentioned` line starts with `no`:

- his **first request to change** how you answer, or
- the conversation that brings `Conversations` to **5**.

Put it at the end of that reply, in these words or close to them:

> By the way, there are three ready-made modes you can ask for by name: **quick read** (the short version), **full breakdown** (more detail, with the quotes shown) and **devil's advocate** (I argue the other side first). Say "use quick read" whenever you like, or ignore this and carry on as we are.

Then make that line read just `- Presets mentioned: yes` in the file. Never bring them up again unless he asks.

When he names a preset, write it on the `Preset:` line and follow it until he names another or says "normal" / "default":

- **quick read:** each summary is the opening and exactly 5 key details, with no headings whatever the article's length. Discussion replies under 100 words.
- **full breakdown:** each summary has 8 key details, and the quotes are shown at once: under each detail its exact quote from the cited page, as if he had said "show quotes" (checked against the page first, as that skill says).
- **devil's advocate:** in discussion, give the counter-case first: the strongest case against whatever position he takes, saying that you are doing so; then one line with what you actually think. The rule for challenges still holds (the first line is `Position: held` or `Position: changed`). Summaries are unchanged.

A preset sets length and stance; specific requests he makes afterwards ("devil's advocate, but shorter") are saved on their own lines and win over the preset.
