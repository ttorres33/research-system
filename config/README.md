# Configuration Guide

## Quick Start

1. Copy `config.template.yaml` to `config.yaml`
2. Copy `keywords.template.md` to `keywords.md`
3. Run `/setup-research-automation` to configure interactively

   OR manually edit the files:

## config.yaml

### Required Settings

- **serpapi.api_key**: Get from https://serpapi.com/ (free tier: 250 searches/month)
  - Required for Google Scholar searches
  - Leave empty to use arXiv only

- **paths.research_root**: Where your research directory is located
  - Use absolute path: `/Users/you/Research`
  - Or relative: `.` (current directory)

### Optional Settings

- **google_scholar.max_results**: Scholar papers per keyword per week (default: 10)
  - arXiv has no per-keyword cap: every new paper is harvested once a day and matched per
    topic (see keywords.md below); an old `arxiv:` block in config.yaml is ignored

- **links.format**: Choose your link style
  - `obsidian`: Use `[[wiki-links]]` (for Obsidian users)
  - `markdown`: Use `[text](path)` (standard markdown)

- **filter**: Configure digest filtering
  - Set your business focus and relevance criteria
  - Add irrelevant topics to filter out
  - Run `/update-research-filters` to refine iteratively
  - Which knob controls which step: `filter.*` drives `/filter-research-digest` (the Sunday
    trim of Google Scholar results) and supplies the exclusions for the Claude review;
    each topic's `looking for` line in keywords.md is what the Claude review reads
    against. A Claude topic with no `looking for` falls back to `filter.relevance_criteria`

- **integration**: Task system integration (advanced)
  - Set `create_task_files: true` to create markdown tasks
  - Specify `task_output_dir` and `queue_file_path`

## keywords.md

Define research topics you want to track. Each topic = one section in digests. A topic
has a name, optional keywords, and two optional settings:

```markdown
## AI & Productivity
categories: cs.HC, cs.CY, econ.GN
mode: claude
looking for: How professionals adopt and work with AI tools and agents; effects on
  productivity, skills and collaboration. Not model benchmarks.
- LLM AND "knowledge work"
- "AI collaboration" AND work
```

### Settings

- **categories**: arXiv category codes, comma-separated. Only papers listed in one of
  them (as primary category or cross-list) are considered for the topic. Leave the line
  out to search all of arXiv, which only makes sense for very specific phrases. The
  plugin's `config/arxiv-categories.md` lists every code with its name and rough volume;
  the human, social and software side of computing is cs.HC, cs.CY, cs.SE and cs.MA,
  while cs.LG, cs.CV, cs.AI and cs.CL are the high-volume technical areas.
- **mode**:
  - `keywords` (default): the daily run keeps papers matching a keyword
  - `claude`: the daily run records every new paper in the categories as a candidate, and
    Claude reads them against `looking for` when you run `/generate-research-digest`
  - `both`: keyword matches go straight into the digest, Claude reads the rest
  - Claude reads each candidate paper once, however many Claude topics could take it, and
    keeps it under every eligible topic whose brief it fits, so a paper can appear under
    two topics. What Claude reads each morning is the union of the Claude topics'
    categories minus what keyword topics claimed; `/test-keywords` prints that total.
    Up to about 100 a day is a quick morning step; above that give the biggest topics
    keywords
- **looking for**: two or three sentences on what you want and what to leave out, for
  `claude` and `both`. Continuation lines must be indented. If missing, the config's
  `filter.relevance_criteria` is used and a warning is logged.
- **Google Scholar always searches by keyword.** A topic with no keywords is skipped on
  Sundays, with a line saying so in the digest.
- **Keyword topics claim first.** A paper matched by a keyword goes under the first topic
  whose keyword matches it and is not offered to the Claude review. Claude candidates are
  never claimed by one topic ahead of another.
- **Mixed volumes: split the topic.** When a topic's categories mix small areas (say cs.HC
  and cs.CY) with a large one (cs.LG), one mode does not fit both. Make two topics named
  after the original: `[Topic] (LLM filter)` with `mode: claude`, the small categories, a
  brief and no keywords; and `[Topic] (Keyword filter)` with `mode: keywords`, the large
  categories and the keywords. Claude reads the small areas every morning, the keywords
  cover the large one, Google Scholar runs once under the keyword half, and the digest
  shows two sections. One topic folder serves both. `/configure-topics` proposes the split
  when the volumes call for it.

Old-style files with only headings and keywords keep working: every topic defaults to
`keywords` mode over all of arXiv. Run `/configure-topics` to set the three settings
interactively, topic by topic, with category suggestions based on where the keywords
actually hit; it backs up the file first and keeps the keywords as they are.

### Keyword Syntax

Matching is **whole-word and case-insensitive with no stemming**. `worker` does not match
"workers"; `"AI assistant"` does not match "AI-assisted". Write out the forms you mean,
joined with OR: `(worker OR workers)`. This is stricter than the arXiv search API used to
be, on purpose: its stemming put papers about "world models" under `modeling AND education`
and "organized" under `organizations`, and those matches were most of the off-topic
papers in the digests.

- **AND**: Require both terms
  ```
  "decision making" AND business
  ```

- **OR**: Either term
  ```
  LLM OR "large language model"
  ```

- **ANDNOT**: Exclude a term
  ```
  "decision making" ANDNOT robotics
  ```

- **Quotes**: Exact phrase, words adjacent
  ```
  "product discovery"
  ```

- **Parentheses**: Group terms
  ```
  interview AND (synthesis OR analysis)
  ```

- Hyphens are word breaks on both sides, so `"AI-assisted"` equals `"AI assisted"`.
- Not supported: field prefixes (`cat:`, `ti:`, `abs:`) and the `*` wildcard. A keyword
  using them is skipped, logged, and reported in the digest. Use the topic's
  `categories` setting instead of `cat:`.

### False friends

Some phrases mean something else in the high-volume machine-learning categories and
will match dozens of unrelated papers a week unless the topic has categories:
"active learning" (a training technique), "modeling" (models of anything),
"decision making" (control and robotics), "scaffolding", "personalized learning"
(speech and recommendation). Give the topic categories, or use a narrower phrase.

### Best Practices

- **Group related concepts** in one topic
- **Give every topic categories** unless its phrases are unmistakable
- **Use specific terms** to avoid noise; prefer `claude` mode when the categories are small
- **Start with 3-5 keywords per topic** and refine
- **Test keywords** with `/test-keywords`: it shows hits per day and sample titles against
  the last week of arXiv papers

## After Configuration

1. **Test the setup**:
   ```bash
   cd scripts/automation
   python3 fetch_papers.py  # Harvest arXiv and write today's digest
   python3 ../utilities/keyword_dryrun.py  # What each keyword matches (or /test-keywords)
   ```

2. **Check the cron jobs** are installed:
   ```bash
   crontab -l | grep research
   ```

3. **Monitor logs** (the scheduled cron runs write here; a manual test run prints to the terminal instead):
   - `{research_root}/.research-data/fetch_papers.log`
   - `{research_root}/.research-data/monitor_sources.log`

4. **Adjust as needed**:
   - Add/remove keywords, categories and modes in keywords.md
   - Adjust google_scholar.max_results
   - Refine the Claude review with each topic's `looking for` line; refine the Sunday
     filter with `/update-research-filters`
