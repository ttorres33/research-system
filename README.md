# Research System

Automated research paper discovery, PDF monitoring, and AI-powered summarization for academic and technical literature.

## Overview

The Research System automates your research workflow in a simple daily cycle:

1. **Automated Discovery** - The system searches arXiv and Google Scholar based on your topic/keyword list and creates a daily digest
2. **Review & Save** - You review the digest and download PDFs of interesting papers to your topic's `Sources/` folder
3. **Automatic Summarization** - The system detects new PDFs and generates summaries in the `Notes/` folder

**Sample Daily Workflow:**
- **Morning (Automated)**: System searches for new papers and creates today's digest
- **When you start work**: Run `/generate-research-digest` to see today's papers and any new summaries
- **Throughout the day**: Review digest → Download interesting PDFs to `[Topic]/Sources/`
- **Evening (Automated)**: System detects new PDFs and queues them for summarization
- **Next day**: Run `/generate-research-digest` again → Get today's papers + yesterday's summaries

*Note: Timing is fully customizable during setup. Schedule the automated tasks (paper discovery and PDF monitoring) whenever works best for your workflow.*

## Features

- **Automated Discovery**: Daily arXiv searches + weekly Google Scholar searches
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
- Setting up research topics and keywords
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
- Archives yesterday's `research-today.md` to `research-today-archive/`
- Generates summaries for new PDFs
- Creates new `research-today.md` with today's papers and summaries

## Sample Daily Workflow

*Note: The timing below is just one example. During setup, you choose when each automated task runs to fit your schedule.*

### Automated Tasks
- **Paper Discovery**: Searches arXiv (daily) and Google Scholar (Sundays), creates digest in `daily-digests/YYYY-MM-DD.md`
- **PDF Monitoring**: Scans for new PDFs you've saved, queues them for summarization

### Your Workflow
1. Run `/generate-research-digest` to:
   - Generate summaries for new PDFs
   - Create research-today.md with links
2. Review the digest and download interesting PDFs to topic folders

### Sunday Special (Google Scholar Day)
- Large digest (~200-300 papers from Google Scholar)
- Run `/filter-research-digest` to remove irrelevant papers
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
├── .research-data/             # Tracking files and logs
│   ├── .research-queue.json
│   ├── .seen_arxiv_papers.json
│   ├── .seen_scholar_papers.json
│   ├── .processed_pdfs.json
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
- Research topics and keywords
- Filter criteria (business focus, relevant/irrelevant topics)
- Cron job scheduling

Configuration files are stored in `~/.claude/research-system-config/`.

## Requirements

- Python 3.8+
- Claude Code (for summarization)
- SerpAPI key (optional, for Google Scholar - free tier: 250 searches/month)

## API Usage

- **arXiv**: Free and unlimited
- **Google Scholar** (via SerpAPI): Free tier allows 250 searches/month
  - Weekly searches only (Sundays)
  - With 10 topics × 4 Sundays = ~40 searches/month
  - Plenty of room for most research needs

## Tips

- **Start with 3-5 topics** with 3-5 keywords each
- **Monitor Sunday digests** - they're largest and show if you need more filtering
- **Refine filter criteria iteratively** using `/update-research-filters`
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
- Run `/filter-research-digest` on large digests
- Run `/update-research-filters` to refine criteria
- Adjust keywords to be more specific

## License

MIT

## Author

Teresa Torres
