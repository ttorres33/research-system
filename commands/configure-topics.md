---
name: configure-topics
description: Walk through each research topic to set its arXiv categories, mode and Claude brief; converts a pre-0.4 keywords file to the new format
allowed-tools: [Read, Write, Bash, AskUserQuestion]
---

# Configure Topics Command

Set or change, topic by topic, which arXiv categories a topic watches, how new papers are
picked for it (`keywords`, `claude` or `both`), and the brief Claude reads against.
Existing users upgrading from 0.3 run this once to convert their keywords file. It also
works on an already-converted file, to change a topic later. Keywords are kept exactly as
they are unless the user asks to change one. Nothing is written until the end, and the
original file is backed up first.

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

3. **Mode.** Add up the per-day volumes of the chosen categories:
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

4. **Looking for**, only for `claude` or `both`. Draft two or three sentences from the
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

5. **No keywords:** say that Google Scholar searches by keyword, so this topic is skipped
   on Sundays until it has one.

6. **Keyword fixes, only if asked.** When Step 2 flagged a keyword as `high volume`,
   `no hits` or `UNSUPPORTED`, mention it and offer a rewrite (a category restriction
   usually fixes high volume; whole-word matching means `worker` does not match
   "workers"; `cat:` and `*` are not supported). Change a keyword only when the user
   agrees to that exact change.

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
3. Verify by parsing it again with `topics.py` (Step 1.2). The topic count and the
   keywords must match the original; show any warnings and fix them before finishing.
4. Run the dry run once more (Step 2.2) and show, per topic, the papers per day in its
   categories and, for Claude topics, the number Claude would read.

## Step 5: Report

For each topic: mode, categories, and the first sentence of the brief. Then:
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
