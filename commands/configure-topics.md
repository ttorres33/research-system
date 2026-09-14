---
name: configure-topics
description: Walk through each research topic to set its arXiv categories, mode and Claude brief; splits a topic whose categories mix small and large volumes; converts a pre-0.4 keywords file to the new format
allowed-tools: [Read, Write, Bash, AskUserQuestion]
---

# Configure Topics Command

Set or change, topic by topic, which arXiv categories a topic watches, how new papers are
picked for it (`keywords`, `claude` or `both`), and the brief Claude reads against.
Existing users upgrading from 0.3 run this once to convert their keywords file. It also
works on an already-converted file, to change a topic later. A topic whose categories mix
small and large volumes can be split into two: Claude reads the small categories and the
keywords cover the large ones. Keywords are kept exactly as they are unless the user asks
to change one. Nothing is written until the end, and the original file is backed up first.

## How Keywords Match (read before advising on any keyword)

Matching is whole-word and case-insensitive with no stemming: `worker` matches "worker"
only, not "workers" or "working", and `"AI assistant"` does not match "AI-assisted". This
is deliberate. The arXiv search API the plugin used before 0.4 stemmed every word across
title, abstract, authors and comments, so `modeling AND (teaching OR education)` matched
"world models" plus "teaches", `organizations` matched "organized", and `"AI assistant"
AND productivity` matched "AI-assisted" plus "production". Those matches were most of the
off-topic papers in the digests. Whole-word matching removes them, at the price that a
keyword has to spell out every form it means.

So whenever you draft, rewrite or judge a keyword:
- Write out the forms you want, joined with OR: `(worker OR workers)`,
  `("AI assistant" OR "AI assistants")`, `(interview OR interviews OR interviewing)`.
- Use the phrase people write in abstracts, not a stem or a wildcard: `"knowledge work" OR
  "knowledge workers"`, never `knowledge work*` (`*` is unsupported).
- Hyphens are word breaks, so `"AI-assisted"` and `"AI assisted"` are the same keyword.
- A `no hits` flag in the dry run usually means a missing form, not a wrong idea. A
  `high volume` flag usually means the phrase has a second meaning and needs categories.
- Widen deliberately, one form at a time, and check the dry run. Never suggest adding
  stemming back or matching on word prefixes.

## Step 1: Load Configuration and the Current Topics

1. Read `~/.claude/research-system-config/config.yaml`. Set
   `data_dir = [paths.research_root]/[paths.data]` and `keywords_file = [data_dir]/keywords.md`.
   If the config is missing, stop: the user should run `/setup-research-automation` first.
2. Parse the file with the plugin's own parser, so you see exactly what the daily run sees:
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/automation/topics.py "[keywords_file]"
   ```
   It prints a JSON array, one object per topic: `name`, `keywords`, `categories`, `mode`,
   `looking_for`, `uses_keywords`, `uses_claude`, `warnings`. A pre-0.4 file shows every
   topic with empty categories and mode `keywords`.
3. Read `${CLAUDE_PLUGIN_ROOT}/config/arxiv-categories.md` once: codes, names, and the
   approximate new papers per weekday used for every suggestion below.
4. Tell the user what you found: how many topics, how many already have settings, and that
   keywords stay as they are.

## Step 2: Gather Evidence From Real Papers

Category suggestions are better when based on where a topic's papers actually land.

1. Check for harvest files: `ls "[data_dir]/arxiv-harvest/" 2>/dev/null`.
2. If there are any, run the dry run:
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/utilities/keyword_dryrun.py
   ```
   If there are none (the scheduled run has not happened on this version yet), add
   `--harvest`, which fetches one day into memory in a few seconds and saves nothing.
   If that fails too, continue without evidence and say so.
3. From the output, note for each topic: the primary categories in brackets before its
   sample titles (that is where the keywords' hits live), keywords flagged `high volume`
   or `no hits`, and any `UNSUPPORTED` keyword.

## Step 3: Walk Through Each Topic

For each topic, in file order, one at a time:

1. **Show** the name, the keywords verbatim, the current settings, and the evidence from
   Step 2 in one or two lines, for example: "Your keywords here hit 3 papers this week, in
   cs.HC and cs.CY; 'active learning' is flagged high volume (machine learning papers)."

2. **Categories.** Propose two to five codes with each code's name and papers per weekday
   and the total, for example:
   ```
   For "AI & Productivity" I'd suggest:
   - cs.HC  Human-Computer Interaction     ~16/day   (your hits landed here)
   - cs.CY  Computers and Society          ~8/day
   - econ.GN General Economics             ~3/day
   Total about 27 new papers a day. Keep these, add or remove codes, or say "all" to
   search every arXiv category (only sensible for very specific keywords).
   ```
   Rules for the proposal: categories where the topic's hits actually landed come first;
   then the areas the name and keywords point to; leave out cs.LG, cs.CV, cs.AI and
   cs.CL unless the topic is about those methods, and say why (they add hundreds of
   papers a day). If the topic already has categories, propose keeping them unless the
   evidence disagrees. Store the confirmed list as `categories` (empty for "all").

3. **Mixed volumes: offer a split.** Sort the confirmed codes by papers per weekday. If
   the total is over 60 a day, take codes off the top, largest first, until the rest add
   up to 60 or fewer. When some codes are left and the topic has keywords, propose two
   topics instead of one topic in keyword mode:
   ```
   "AI & Productivity" spans two very different volumes:
   - cs.HC  Human-Computer Interaction     ~16/day
   - cs.CY  Computers and Society          ~8/day
   - cs.LG  Machine Learning               ~80/day
   About 104 a day in all, too many for Claude, but cs.HC and cs.CY alone are about 24.
   I'd split it into two topics:
   - "AI & Productivity (LLM filter)": Claude mode on cs.HC and cs.CY, with a brief
     and no keywords
   - "AI & Productivity (Keyword filter)": keyword mode on cs.LG, with your keywords
     exactly as they are
   Claude reads the small categories every morning and your keywords cover the large
   one. Google Scholar searches the keywords once, under the keyword half. The digest
   shows two sections; your topic folder stays as it is. Split it, or keep one topic in
   keyword mode?
   ```
   Naming is always the original name plus ` (LLM filter)` and ` (Keyword filter)`. If
   the user agrees: the LLM half takes the small codes, `mode: claude` and a brief
   (step 5); the keyword half takes the large codes, `mode: keywords` and every keyword
   verbatim. Steps 4 and 6 do not apply to a split topic; step 7 applies to its keyword
   half. Do not create a folder for either half. A topic with no keywords cannot be
   split: offer to drop the large codes, or to write a keyword for them.

4. **Mode.** Skip for a split topic, both halves already have one. Otherwise add up the
   per-day volumes of the chosen categories:
   - More than 60 a day, or "all": recommend `keywords`. "These categories produce about
     [N] papers a day, too many for Claude to read each morning; keyword mode keeps the
     papers matching your keywords."
   - Otherwise recommend `claude`. "About [N] papers a day, few enough for Claude to read
     every morning against a short brief. That catches papers your keywords would miss."
   - Explain `both`: keyword matches go straight into the digest and Claude reads the rest.
   - Explain that Claude reads each paper once whatever the number of Claude topics, and
     files it under every topic it fits, so overlapping categories between topics cost
     nothing extra; the dry run's last line shows the daily total Claude would read.
   - If the topic already has a mode, show it and ask whether to keep it.
   - If the user picks `keywords` and the topic has no keywords, say it would match
     nothing and ask for at least one keyword or a different mode.

5. **Looking for**, only for `claude` or `both` (for a split topic, only its LLM half).
   Draft two or three sentences from the
   topic name and keywords, phrased as what to find and what to leave out, and show it:
   ```
   Draft brief for "AI & Productivity":
   "How professionals adopt and work with AI tools and agents in their day-to-day work;
   effects on productivity, skills and collaboration. Not model benchmarks or training
   methods."
   Keep it, edit it, or write your own. Claude reads each new paper's title and abstract
   against this.
   ```
   If a brief already exists, show it and offer to keep it.

6. **No keywords:** say that Google Scholar searches by keyword, so this topic is skipped
   on Sundays until it has one. (The LLM half of a split has none by design; its keyword
   half does the Scholar search, so say nothing here.)

7. **Keyword fixes, only if asked.** When Step 2 flagged a keyword as `high volume`,
   `no hits` or `UNSUPPORTED`, mention it and offer a rewrite following "How Keywords
   Match" above (a category restriction usually fixes high volume; a missing form,
   written out with OR, usually fixes no hits; `cat:` and `*` are not supported). Change
   a keyword only when the user agrees to that exact change.

Do not write anything until every topic is done.

## Step 4: Write the File

1. Back up the original:
   ```bash
   cp "[keywords_file]" "[keywords_file].bak-[YYYY-MM-DD]"
   ```
   If that name already exists, use `.bak-[YYYY-MM-DD]-2`, and so on.
2. Write the whole file, topics in the original order, keywords verbatim, settings lines
   only when they differ from the defaults (no line for "all" categories, none for
   `mode: keywords`, none for an empty brief):
   ```markdown
   # Research Keywords

   ## [Topic Name]
   categories: [comma-separated codes]
   mode: [claude | both]
   looking for: [first line of the brief]
     [continuation lines indented by two spaces]
   - [keyword, exactly as before]
   ```
   A split topic becomes two consecutive sections in place of the original, the LLM half
   first:
   ```markdown
   ## AI & Productivity (LLM filter)
   categories: cs.HC, cs.CY
   mode: claude
   looking for: [the brief]

   ## AI & Productivity (Keyword filter)
   categories: cs.LG
   - [every keyword of the original topic, exactly as before]
   ```
3. Verify by parsing it again with `topics.py` (Step 1.2). Every original keyword must
   still be present, and the topic count must be the original plus one for each split;
   show any warnings and fix them before finishing.
4. Run the dry run once more (Step 2.2) and show, per topic, the papers per day in its
   categories and, for Claude topics, the number Claude would read.

## Step 5: Report

For each topic: mode, categories, and the first sentence of the brief; show the two halves
of a split topic together. Then:
- Where the backup is
- That the next scheduled run uses the new settings, and each morning
  `/generate-research-digest` runs the Claude review for Claude-mode topics
- `/test-keywords` shows what the keywords match at any time; `/configure-topics` can be
  run again to change a topic

## Error Handling

- **Config not found**: Stop; run `/setup-research-automation` first
- **Keywords file not found**: Stop; run `/setup-research-automation`, which creates it
- **`topics.py` reports a topic with warnings after writing**: Show them and fix the file before finishing
- **Dry run cannot fetch (no network)**: Continue without evidence; say the suggestions are from names and keywords only
- **Backup copy fails**: Stop before writing; the original must not be the only copy at risk
