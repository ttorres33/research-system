# Research Keywords Template

Define your research topics here. Each topic has a name, optional keywords, and two
optional settings that control how new arXiv papers are picked for it. Google Scholar
(Sundays) always searches by keyword, so a topic with no keywords gets no Scholar search.
`/configure-topics` sets the settings interactively and converts an older file.

## Example Topic: AI & Productivity
categories: cs.HC, cs.CY, econ.GN
mode: claude
looking for: How professionals adopt and work with AI tools and agents in their day-to-day
  work; effects on productivity, skills and collaboration. Not model benchmarks or
  training methods.
- LLM AND "knowledge work"
- "AI collaboration" AND work

## Example Topic: User Research
categories: cs.HC, cs.CY, cs.SE
mode: both
looking for: Methods for discovering customer needs: interviews, synthesis, and how AI
  changes that work.
- "customer interview" AND (LLM OR AI)
- "user research" AND automation
- "interview synthesis"

## Example Topic: Synthetic Users
- "synthetic users"
- "synthetic consumers"
- "LLM focus groups"

# Settings

- **categories:** arXiv category codes the topic watches, separated by commas. Leave the
  line out to search all of arXiv, which only makes sense for very specific phrases.
  Codes and their daily volumes are listed in the plugin's `config/arxiv-categories.md`.
- **mode:** `keywords` (default) keeps papers that match a keyword; `claude` has Claude
  read every new paper in the categories against the `looking for` text each morning when
  you run `/generate-research-digest`; `both` does both. Claude reads each paper once and
  may keep it under every Claude topic it fits.
- **looking for:** two or three sentences on what you want and what to leave out. Needed
  for `claude` and `both`. Continuation lines must be indented.
- **Mixed volumes:** when a topic's categories mix a small area with a large one, split it
  into `[Topic] (LLM filter)` (mode `claude`, the small categories, a brief, no keywords)
  and `[Topic] (Keyword filter)` (mode `keywords`, the large categories, the keywords).
  `/configure-topics` proposes this when the volumes call for it.

# Keyword syntax

- Matching is **whole-word and case-insensitive with no stemming**: `worker` does not
  match "workers", and `"AI assistant"` does not match "AI-assisted". Write out the forms
  you mean, joined with OR: `(worker OR workers)`. This is stricter than the old arXiv
  search API on purpose: its stemming was the source of most off-topic digest papers.
- **Quotes** for exact phrases: `"product discovery"`
- **AND** requires both, **OR** either, **ANDNOT** excludes: `"decision making" ANDNOT robotics`
- **Parentheses** group: `"customer interview" AND (LLM OR AI)`
- Hyphens are word breaks on both sides: `"AI-assisted"` and `"AI assisted"` are the same.
- Field prefixes such as `cat:` or `ti:` and the `*` wildcard are not supported; a keyword
  using them is skipped and reported in the digest.
- Watch phrases with a second meaning in machine learning: "active learning", "modeling",
  "decision making" and "scaffolding" match hundreds of technical papers a week unless the
  topic has categories. Run `/test-keywords` to see what each keyword matches.

# Your Research Topics

## Topic 1: [Your Topic Name]
categories: [codes]
mode: [keywords | claude | both]
looking for: [what you want; leave out for keywords mode]
- [keyword search 1]
- [keyword search 2]
