# Research System

Automated research paper discovery, PDF monitoring, and AI-powered summarization for academic and technical literature.

## Overview

The Research System automates your research workflow in a simple daily cycle:

1. **Automated Discovery** - Every day the system harvests all new arXiv papers and picks the ones for each of your topics, by keyword, by having Claude read them against a short brief, or both, scoped to the arXiv categories you choose. Google Scholar is searched weekly. The result is a daily digest
2. **Review & Save** - You review the digest and download PDFs of interesting papers to your topic's `Sources/` folder
3. **Automatic Summarization** - The system detects new PDFs and generates summaries in the `Notes/` folder

**Sample Daily Workflow:**
- **Morning (Automated)**: System searches for new papers and creates today's digest
- **When you start work**: Run `/generate-research-digest`. It has Claude review the day's candidates for your Claude-mode topics, then shows today's papers and any new summaries
- **Throughout the day**: Review digest → Download interesting PDFs to `[Topic]/Sources/`
- **Evening (Automated)**: System detects new PDFs and queues them for summarization
- **Next day**: Run `/generate-research-digest` again → Get today's papers + yesterday's summaries

*Note: Timing is fully customizable during setup. Schedule the automated tasks (paper discovery and PDF monitoring) whenever works best for your workflow.*

## Features

- **Automated Discovery**: A daily arXiv harvest over OAI-PMH (two to five requests, no API key) plus weekly Google Scholar searches
- **Per-Topic Picking**: Keyword matching, a Claude review against a short brief, or both, scoped to the arXiv categories you choose
- **Keyword Dry Run**: `/test-keywords` shows what each keyword matches against the last week of arXiv papers before it reaches a digest
- **PDF Monitoring**: Automatically detects new PDFs you save to Sources/ folders
- **AI Summarization**: Generates concise bullet-point summaries with semantic tags
- **Large PDF Handling**: Automatically splits papers ≥5 MB into sections to avoid context overflow
- **Conference Proceedings Support**: Extract individual papers from multi-paper proceedings
- **Intelligent Filtering**: Removes irrelevant papers based on your business focus
- **Flexible Integration**: Works standalone or with task management systems
- **Markdown-based**: Works with any markdown editor (Obsidian support built-in)

## Quick Start

### 1. Install the Plugin

**Option A: Claude Code Marketplace (Recommended)**

In Claude Code, run:
```
/plugin marketplace add ttorres33/teresa-torres-plugins
/plugin install research-system
```

**Option B: Manual Installation**
```bash
cd ~/.claude/plugins/
git clone https://github.com/ttorres33/research-system.git
```

### 2. Run Setup Wizard

In Claude Code:
```
/setup-research-automation
```

The wizard will guide you through:
- Installing Python dependencies (automated)
- Configuring research directory location
- Setting up research topics: keywords, arXiv categories, and whether Claude reads new papers for the topic
- Configuring filter criteria
- Setting up automated cron jobs
- Getting a SerpAPI key (optional, for Google Scholar)

### 3. Wait for Papers or Run Manually

Papers are fetched automatically by cron job, or run manually:
```
/fetch-papers
```

### 4. Process New Papers

```
/generate-research-digest
```

This command:
- Has Claude review the arXiv papers waiting for your Claude-mode topics and adds the keepers to today's digest
- Archives yesterday's `research-today.md` to `research-today-archive/`
- Generates summaries for new PDFs
- Creates new `research-today.md` with today's papers and summaries

## Sample Daily Workflow

*Note: The timing below is just one example. During setup, you choose when each automated task runs to fit your schedule.*

### Automated Tasks
- **Paper Discovery**: Harvests arXiv (daily) and searches Google Scholar (Sundays), writes the digest to `daily-digests/YYYY-MM-DD.md`. Papers for Claude-mode topics wait in the digest for your morning review
- **PDF Monitoring**: Scans for new PDFs you've saved, queues them for summarization

### Your Workflow
1. Run `/generate-research-digest` to:
   - Have Claude review the day's candidates for Claude-mode topics
   - Generate summaries for new PDFs
   - Create research-today.md with links
2. Review the digest and download interesting PDFs to topic folders

### Sunday Special (Google Scholar Day)
- Large digest (~200-300 papers from Google Scholar)
- Run `/generate-research-digest` first, then `/filter-research-digest` to remove irrelevant papers (the filter refuses a digest whose Claude review is still pending)
- If still too many, run `/update-research-filters` to refine criteria

## Commands

- `/about` - Show this README for help and usage information
- `/generate-research-digest` - Generate summaries and create today's digest
- `/research-summary` - Generate summary for a single PDF (handles large PDFs automatically)
- `/split-conference-pdf` - Split conference proceedings into individual papers
- `/filter-research-digest` - Filter digest by relevance
- `/update-research-filters` - Interactively refine filter criteria
- `/setup-research-automation` - Configuration wizard
- `/fix-scheduled-scripts` - Repair cron jobs after plugin directory changes
- `/fetch-papers` - Manually run paper fetching (instead of waiting for cron)
- `/test-keywords` - Show what each topic and keyword matches against the last week of arXiv papers
- `/configure-topics` - Walk through each topic's arXiv categories, mode and Claude brief; converts a pre-0.4 keywords file
- `/monitor-sources` - Scan for new PDFs and add to summarization queue
- `/check-logs` - View recent log entries to diagnose issues

## Working with Large PDFs and Conference Proceedings

### Large Paper Handling

The system automatically handles large papers (≥5 MB) by:
1. Detecting file size before processing
2. Splitting into sections using PDF structure (outline/bookmarks) or standard academic sections
3. Processing each section separately to avoid context overflow
4. Cleaning up temporary files after summarization

This happens automatically in both:
- `/generate-research-digest` (automated queue processing)
- `/research-summary` (manual single-paper summarization)

**No action needed** - large PDFs just work!

### Conference Proceedings

If you download conference proceedings containing multiple papers:

1. **Split the proceedings:**
   ```
   /split-conference-pdf ~/Downloads/proceedings.pdf
   ```

2. **Review extracted papers** in the output directory

3. **Save desired papers** to your topic's `Sources/` folder
   ```
   cp split_papers/03_Interesting_Paper.pdf ~/Research/AI/Sources/
   ```

4. **Run digest generation** to summarize them
   ```
   /generate-research-digest
   ```

**Note:** Conference splitting requires the PDF to have embedded bookmarks/table of contents.

## Directory Structure

```
research-directory/
├── research-today.md           # Your daily starting point
├── research-today-archive/     # Historical daily digests
│   ├── 2025-11-03.md
│   └── 2025-11-02.md
├── daily-digests/              # Daily paper discovery results
│   ├── 2025-11-04.md
│   └── 2025-11-03.md
├── .research-data/             # Topics, tracking files and logs
│   ├── keywords.md             # Your topics: keywords, categories, mode, looking for
│   ├── .research-queue.json
│   ├── .seen_arxiv_papers.json
│   ├── .seen_scholar_papers.json
│   ├── .processed_pdfs.json
│   ├── .arxiv_harvest_state.json   # Last arXiv date stamp harvested
│   ├── arxiv-harvest/          # New arXiv papers, last 7 days (for the dry run and the review)
│   ├── claude-candidates/      # Papers waiting for the Claude review, per day
│   ├── fetch_papers.log
│   └── monitor_sources.log
├── [Topic Folders]/            # One per research topic
│   ├── Sources/                # Put PDFs here
│   └── Notes/                  # Auto-generated summaries
```

## Configuration

Run `/setup-research-automation` to configure the system interactively. This wizard handles:
- API keys (SerpAPI for Google Scholar)
- Research directory location
- Research topics: keywords, arXiv categories, mode (`keywords`, `claude`, or `both`) and, for Claude mode, a short "looking for" brief
- Filter criteria (business focus, relevant/irrelevant topics)
- Cron job scheduling

The config file lives in `~/.claude/research-system-config/config.yaml`; topics live in
`{research_root}/.research-data/keywords.md`. Each topic can set `categories:` (which arXiv
areas to watch), `mode:` and `looking for:`; a topic with no keywords gets no Google Scholar
search. Keyword matching is whole-word with no stemming. See
[config/README.md](config/README.md) for every setting and the keyword syntax, and
[config/arxiv-categories.md](config/arxiv-categories.md) for category codes with their
daily volumes.

### Upgrading from 0.3

Your existing `keywords.md` keeps working: every topic runs in keyword mode across all of
arXiv, as before, minus the stemming noise the old search API added. To get the new
behaviour, run `/configure-topics` once. It reads your topics, shows where their keywords
actually hit, walks you through categories, mode and a Claude brief for each topic, backs
up the original file, and writes the new format. Keywords are kept as they are.

## Requirements

- Python 3.10+
- Claude Code (for summarization)
- SerpAPI key (optional, for Google Scholar - free tier: 250 searches/month)

## API Usage

- **arXiv**: Harvested through OAI-PMH, two to five requests a day, no key needed. arXiv asks for one request every three seconds, which the harvester honours
- **Google Scholar** (via SerpAPI): Free tier allows 250 searches/month
  - Weekly searches only (Sundays)
  - With 10 topics × 4 Sundays = ~40 searches/month
  - Plenty of room for most research needs

## Tips

- **Start with 3-5 topics** with 3-5 keywords each
- **Monitor Sunday digests** - they're largest and show if you need more filtering
- **Refine filter criteria iteratively** using `/update-research-filters`; refine a Claude-mode topic by editing its `looking for` line
- **Run `/test-keywords`** after changing keywords: matching is whole-word, so `worker` does not match "workers", and phrases such as "active learning" mean something else in machine learning unless the topic has categories
- **Check logs** if papers stop appearing: run `/check-logs`

## Troubleshooting

### Cron jobs stopped working
After Claude Code updates, the plugin directory may move, breaking cron jobs:
- Run `/fix-scheduled-scripts` to repair the symlink and update crontab
- This updates the stable symlink at `~/.claude/research-system-config/plugin`

### No papers in digest
- Run `/check-logs` to see if there are errors
- Run `/fetch-papers` to manually trigger paper fetching
- Run `/fix-scheduled-scripts` if cron paths are broken

### Summaries not generating
- Run `/monitor-sources` to scan for new PDFs and add them to the queue
- Run `/generate-research-digest` to process queued PDFs
- Verify PDFs exist in your topic's `Sources/` folders

### Too many irrelevant papers
- Run `/configure-topics` to give the topic `categories:` and a mode; generic phrases then stay in the right areas
- Switch small topics to `mode: claude` with a `looking for` brief
- Run `/test-keywords` to see which keyword brings the noise, and rephrase it
- Run `/filter-research-digest` on large Sunday digests and `/update-research-filters` to refine its criteria

### arXiv papers missing from the digest
- A note at the top of the digest saying the harvest failed means arXiv's OAI-PMH endpoint was down; the next run catches up automatically
- A line saying papers "await Claude review" means the morning step has not run yet: run `/generate-research-digest`
- Run `/check-logs` to see the harvest lines from the scheduled runs

## Development

- **How it works**: [scripts/automation/fetch_papers.py](scripts/automation/fetch_papers.py) runs from cron. It harvests arXiv through [arxiv_harvest.py](scripts/automation/arxiv_harvest.py), reads topics with [topics.py](scripts/automation/topics.py), matches keywords with [keyword_match.py](scripts/automation/keyword_match.py), renders the digest with [digest.py](scripts/automation/digest.py), and records Claude-mode candidates. `/generate-research-digest` then runs the review through [scripts/utilities/apply_claude_triage.py](scripts/utilities/apply_claude_triage.py), which prepares batch files for review agents and writes the kept papers back into the digest. Cron does the fetching in plain Python; Claude only runs inside commands.
- **Tests**: plain `unittest`, no network. See [docs/test.md](docs/test.md).
  ```bash
  python3 -m unittest discover -s tests -t . -p "test_*.py"
  ```
- **Dependencies**: `requirements.in` lists the direct dependencies; `requirements.txt` is generated from it with `uv pip compile` (command in the file header) and must not be edited by hand.

## License

MIT

## Author

Teresa Torres
