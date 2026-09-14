---
name: setup-research-automation
description: Interactive setup wizard for configuring research automation system including paths, cron jobs, keywords, and filter criteria
allowed-tools: [Read, Write, Bash, AskUserQuestion]
---

# Setup Research Automation Command

Guide you through complete setup of the research automation system.

## Step 1: Welcome and Detect Installation

1. Welcome user: "Welcome to Research System setup! I'll help you configure automated paper discovery and summarization."
2. Check Python dependencies:
   - Run `pip3 list | grep -E "(requests|serpapi|PyYAML|pypdf)"`
   - If any missing, show installation command: `pip3 install -r ${CLAUDE_PLUGIN_ROOT}/requirements.txt`

## Step 2: Gather Basic Configuration

Use AskUserQuestion to collect:

### Question 1: Research Directory Location
```
Where should research papers be stored?
- Option 1: ~/Research (create if doesn't exist)
- Option 2: Current directory (.)
- Option 3: Custom path (specify)
```

Store as `research_root`. If custom, validate path exists or offer to create it.

### Question 2: Obsidian Usage
```
Are you using Obsidian to view your research notes?
- Yes (use [[wiki-style]] links)
- No (use standard markdown [links](path))
```

Set `link_format`:
- Yes → "obsidian"
- No → "markdown"

### Question 3: Paper Fetch Time
```
What time should new papers be fetched daily?
- 6 AM (recommended)
- 8 AM
- Custom time (specify in HH:MM format)
```

Store as `fetch_time` in cron format (e.g., "0 6" for 6 AM)

### Question 4: PDF Monitoring Time
```
What time should PDFs be monitored for summaries?
- 6 PM (recommended, after work day)
- 8 PM
- Custom time (specify in HH:MM format)
```

Store as `monitor_time` in cron format

### Question 5: SerpAPI Key
```
Do you have a SerpAPI key for Google Scholar searches?
- Yes (enter key)
- No (skip Scholar, use arXiv only)
- Get one now (show link to serpapi.com)
```

Store as `serpapi_key` (empty string if skipped)

## Step 3: Interactive Topic Setup

Each topic has a name, optional keywords, the arXiv categories it covers, and a mode that
says how new arXiv papers are picked for it. The plugin's `config/arxiv-categories.md`
lists every category with its name and rough number of new papers per weekday; read it
once before this step.

1. Explain: "Let's set up the research topics you want to track. For each topic I'll ask
   for keywords, which arXiv areas to watch, and whether new papers should be picked by
   keyword or read by Claude."

2. Ask: "What's your first research topic?" (e.g., "AI & Productivity")

3. **Keywords** for the topic:
   ```
   Now some search keywords for "[topic name]". These are optional for topics Claude will
   read, but they are also how Google Scholar searches this topic on Sundays: a topic
   with no keywords gets no Google Scholar search.

   Tips:
   - Matching is whole-word and case-insensitive, with no stemming: "worker" does not match "workers"
   - Write out each form you want, joined with OR: (worker OR workers)
   - Use quotes for exact phrases: "knowledge work"
   - Use AND to require terms, OR for alternatives, parentheses to group: "customer interview" AND (LLM OR AI)
   - Phrases with a second meaning in machine learning ("active learning", "decision making",
     "modeling") need a category restriction or a narrower phrase

   Enter keywords one at a time (or 'done' when finished; 'none' for no keywords):
   ```
   Collect until the user says done or none.

   Why there is no stemming, for when the user asks or when you suggest a keyword: the
   arXiv search API the plugin used before 0.4 stemmed every word across all fields, so
   `modeling` matched "world models" and `organizations` matched "organized", and those
   matches produced most of the off-topic papers in digests. Whole-word matching is
   stricter on purpose. The cost is that a keyword must list every form it means, so
   suggest `(worker OR workers)` rather than relying on plurals or verb forms being caught.

4. **Categories** for the topic:
   - From the topic name and its keywords, propose 2-5 category codes from
     `config/arxiv-categories.md`, showing each code's name and new papers per weekday and
     the total, for example:
     ```
     For "AI & Productivity" I'd suggest:
     - cs.HC  Human-Computer Interaction     ~16/day
     - cs.CY  Computers and Society          ~8/day
     - econ.GN General Economics             ~3/day
     Total about 27 new papers a day. Keep these, add or remove codes, or say "all" to
     search every arXiv category (only sensible for very specific keywords).
     ```
   - Store the confirmed list as `categories` (empty list for "all").

5. **Mode** for the topic. Add up the per-day volumes of the chosen categories:
   - If the total is more than 60 a day, or the user chose "all", recommend `keywords`:
     "These categories produce about [N] papers a day, too many for Claude to read each
     morning. I'd suggest keyword mode: the daily run keeps papers matching your keywords."
   - Before settling on `keywords`, check for mixed volumes: take codes off the top, largest
     first, until the rest add up to 60 or fewer. If some codes are left and the topic has
     keywords, propose a split instead of one keyword topic: "[Topic] (LLM filter)" in
     `claude` mode on the small codes with a brief and no keywords, and "[Topic] (Keyword
     filter)" in `keywords` mode on the large codes with the keywords exactly as given.
     Say that Claude reads the small categories every morning, the keywords cover the
     large ones, Google Scholar searches the keywords once under the keyword half, and the
     digest shows two sections. If the user agrees, store two topics and ask for the brief
     (step 6) for the LLM half only.
   - Otherwise recommend `claude`: "These categories produce about [N] papers a day, few
     enough for Claude to read every morning against a short description of what you want.
     That catches papers your keywords would miss."
   - Explain `both`: keyword matches go straight into the digest and Claude reads the rest.
   - Explain that Claude reads each paper once whatever the number of Claude topics, and
     files it under every topic it fits, so overlapping categories between topics cost
     nothing extra.
   - If the user picks `keywords` and gave no keywords, say the topic would match nothing
     and ask for at least one keyword or a different mode.
   - Store as `mode`.

6. **Looking for**, only if the mode is `claude` or `both`:
   ```
   In two or three sentences, what are you looking for in "[topic name]", and what should
   be left out? Claude reads each new paper's title and abstract against this.
   Example: "How professionals adopt and work with AI tools and agents in day-to-day work;
   effects on productivity, skills and collaboration. Not model benchmarks or training methods."
   ```
   Store as `looking_for`.

7. Ask: "Add another research topic? (yes/no)" and repeat.

8. Build the keywords.md content from the collected topics (format in Step 5).

## Step 4: Setup Filter Criteria

1. Explain: "Now let's configure filters to remove irrelevant papers from large digests (especially useful for Sunday digests)."

2. Ask questions:

### Filter Question 1: Business Focus
```
What's your primary business focus or work domain?
Example: "product management and continuous discovery"
```

Store as `business_focus`

### Filter Question 2: Relevant Topics
```
What broad topics are relevant to your work? (comma-separated)
Examples: user research, decision making, team collaboration
```

Parse into array, store as `relevant_topics`

### Filter Question 3: Irrelevant Topics
```
What topics should definitely be filtered out? (comma-separated)
Examples: pure mathematics, medical procedures, agriculture
```

Parse into array, store as `irrelevant_topics`

### Filter Question 4: Relevance Criteria
```
In one sentence, what makes a paper relevant to you?
Example: "Paper must relate to how product teams make decisions or discover customer needs"
```

Store as `relevance_criteria`

## Step 5: Create Configuration Files

### Create ~/.claude/research-system-config/config.yaml

```yaml
# Research Automation Configuration
# Generated by setup wizard on [timestamp]

serpapi:
  api_key: "[serpapi_key]"

google_scholar:
  max_results: 10
  search_days: 7

paths:
  research_root: "[research_root]"
  daily_digests: "daily-digests"
  data: ".research-data"

links:
  format: "[link_format]"

filter:
  business_focus: "[business_focus]"
  relevant_topics: [relevant_topics array]
  irrelevant_topics: [irrelevant_topics array]
  relevance_criteria: "[relevance_criteria]"

integration:
  create_task_files: false
  task_output_dir: null
  queue_file_path: null
```

1. Create directory: `mkdir -p ~/.claude/research-system-config`
2. Write to `~/.claude/research-system-config/config.yaml`

### Create {research_root}/.research-data/keywords.md

```markdown
# Research Keywords

[For each topic:]
## [Topic Name]
categories: [comma-separated codes; omit the line when the user chose "all"]
mode: [keywords | claude | both; omit the line for keywords]
looking for: [the looking_for text; omit the line when the mode is keywords]
[For each keyword in topic:]
- [keyword]

```

Write to `{research_root}/.research-data/keywords.md`. A `looking for` value may run over
several lines if the continuation lines are indented.

## Step 6: Create Directory Structure

In research_root, create:
```
research_root/
├── daily-digests/
├── .research-data/
└── [Topic folders from keywords]/
    ├── Sources/
    └── Notes/
```

For each topic in keywords, create topic folder with Sources/ and Notes/ subdirectories.
A split pair shares one folder, named after the topic without its ` (LLM filter)` or
` (Keyword filter)` suffix.

## Step 7: Setup Cron Jobs

1. **Create stable symlink for cron jobs:**
   - Symlink location: `~/.claude/research-system-config/plugin` (stable path for cron)
   - Target: `${CLAUDE_PLUGIN_ROOT}` (actual plugin location)
   - Run: `ln -sfn "${CLAUDE_PLUGIN_ROOT}" ~/.claude/research-system-config/plugin`
   - This symlink allows cron jobs to survive plugin directory changes

2. Generate cron entries using the symlink path:

```bash
# Research paper discovery - [fetch_time]
[fetch_time cron] * * * cd ~/.claude/research-system-config/plugin/scripts/automation && python3 fetch_papers.py >> [research_root]/.research-data/fetch_papers.log 2>&1

# PDF monitoring - [monitor_time]
[monitor_time cron] * * * cd ~/.claude/research-system-config/plugin/scripts/automation && python3 monitor_sources.py >> [research_root]/.research-data/monitor_sources.log 2>&1
```

3. Ask user for confirmation:
```
I'll add these cron jobs to your crontab. The jobs will:
- Fetch new papers daily at [fetch_time]
- Monitor for new PDFs at [monitor_time]

Note: Cron jobs use a stable symlink path. If the plugin moves after a Claude Code
update, run /fix-scheduled-scripts to repair the symlink.

Proceed? (yes/no)
```

4. If yes:
   - Get current crontab: `crontab -l > /tmp/current_cron 2>/dev/null || true`
   - Append new entries
   - Install: `crontab /tmp/current_cron`
   - Clean up temp file

5. Show what was added

## Step 8: Validate Setup

Run validation checks:

1. **Run one real fetch** (the only network step in setup; two to five requests to
   arXiv's OAI-PMH endpoint, plus Google Scholar if today is Sunday and a key was given):
   ```bash
   cd ${CLAUDE_PLUGIN_ROOT}/scripts/automation && python3 fetch_papers.py
   ```
   - Check it runs without errors and reports the number of new arXiv papers harvested
   - It writes today's digest and, for Claude-mode topics, the candidates for the review
   - If it says "Today's digest already has papers", the scheduled job has already run today
     (a re-run of setup on an existing installation); that is fine, move on to the dry run

2. **Test API keys:**
   - If SerpAPI key provided, verify it's valid format
   - Show warning if it looks invalid

3. **Check directory permissions:**
   - Verify can write to research_root
   - Verify can write to .research-data

4. **Run the keyword dry run** and walk through it with the user:
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/utilities/keyword_dryrun.py
   ```
   - For each topic it shows papers per day in its categories and, per keyword, hits per
     day with sample titles; a keyword flagged `high volume` is probably matching a
     different meaning and needs a category or a narrower phrase
   - Offer to adjust keywords, categories or mode in keywords.md before finishing

## Step 9: Success Summary

Show complete setup summary:

```
✓ Setup Complete!

Configuration:
- Research directory: [research_root]
- Link format: [link_format]
- Topics configured: [count]
- Filter criteria: Set

Cron Jobs:
- Paper fetching: Daily at [fetch_time]
- PDF monitoring: Daily at [monitor_time]

Next Steps:
1. Customize keywords: edit [research_root]/.research-data/keywords.md
2. Wait for first paper fetch (tomorrow at [fetch_time])
   OR run manually: cd ${CLAUDE_PLUGIN_ROOT}/scripts/automation && python3 fetch_papers.py
3. Each morning run /generate-research-digest: it has Claude read the candidates for
   your Claude-mode topics and creates research-today.md
4. Download PDFs of interest to topic Sources/ folders; the evening job queues them for summaries
5. On Sundays run /filter-research-digest after /generate-research-digest to trim the Google Scholar results
6. Run /test-keywords any time to see what your keywords are matching, and /configure-topics to change a topic's categories or mode later

If cron jobs break after Claude Code updates:
- Run /fix-scheduled-scripts to repair the symlink

Files Created:
- ~/.claude/research-system-config/config.yaml
- ~/.claude/research-system-config/plugin (symlink to plugin directory)
- [research_root]/.research-data/keywords.md
- [research_root]/.research-data/ (tracking directory)
- [count] topic folders in [research_root]

Logs will be saved to:
- [research_root]/.research-data/fetch_papers.log
- [research_root]/.research-data/monitor_sources.log
```

## Error Handling

- **Plugin directory not found**: Show error, explain installation needed
- **Python dependencies missing**: Show pip install command
- **Research directory can't be created**: Show permission error
- **Crontab access denied**: Show manual cron setup instructions
- **Invalid API key format**: Warn but continue (user can fix later)
- **Cron job already exists**: Detect duplicates, offer to replace or skip
- **Symlink creation fails**: Show error, suggest checking permissions

## Notes

- Setup creates config.yaml and keywords.md from scratch (overwrites if exist)
- No network access until Step 8; category volumes come from `config/arxiv-categories.md`
- Cron jobs are appended to existing crontab (doesn't remove other jobs)
- Cron jobs use a stable symlink path that survives plugin directory changes
- If plugin moves, run /fix-scheduled-scripts to update the symlink
- Test commands help verify setup before first real run
- User can re-run setup to reconfigure (will ask about overwriting)
