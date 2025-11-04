# Research System

Automated research paper discovery, PDF monitoring, and AI-powered summarization for academic and technical literature.

## Features

- **Automated Discovery**: Daily searches of arXiv and weekly Google Scholar searches based on your research topics
- **PDF Monitoring**: Automatically detects new PDFs in your research folders
- **AI Summarization**: Generates concise bullet-point summaries of research papers
- **Intelligent Filtering**: Removes irrelevant papers from large digests based on your business focus
- **Flexible Integration**: Works standalone or integrates with task management systems
- **Markdown-based**: Uses standard markdown files, works with any markdown editor (Obsidian support built-in)

## Quick Start

### 1. Install the Plugin

**Option A: Claude Code Marketplace (Recommended)**

In Claude Code, run:
```
/plugin marketplace add ttorres33/cc-plugins
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
```bash
cd scripts/automation
python3 fetch_papers.py
```

### 4. Process New Papers

```
/generate-research-digest
```

## Daily Workflow

### Morning (Automated)
- 6 AM: `fetch_papers.py` searches arXiv (daily) and Google Scholar (Sundays)
- Creates digest in `daily-digests/YYYY-MM-DD.md`

### Your Morning
1. Run `/generate-research-digest` to:
   - Generate summaries for new PDFs
   - Create research-today.md with links
2. Review the digest and download interesting PDFs to topic folders

### Evening (Automated)
- 6 PM: `monitor_sources.py` scans for new PDFs
- Creates queue for tomorrow's summary generation

### Sunday Special
- Large digest (~200-300 papers from Google Scholar)
- Run `/filter-research-digest` to remove irrelevant papers
- If still too many, run `/update-research-filters` to refine criteria

## Commands

- `/generate-research-digest` - Generate summaries and create today's digest
- `/filter-research-digest` - Filter digest by relevance
- `/update-research-filters` - Interactively refine filter criteria
- `/setup-research-automation` - Configuration wizard

## Directory Structure

```
research-directory/
├── daily-digests/              # Daily paper discovery results
│   ├── 2025-11-03.md
│   └── 2025-11-02-filtered.md
├── .research-data/             # Tracking files and logs
│   ├── .seen_arxiv_papers.json
│   ├── .seen_scholar_papers.json
│   ├── .processed_pdfs.json
│   ├── .research-queue.json
│   ├── fetch_papers.log
│   └── monitor_sources.log
├── [Topic Folders]/            # One per research topic
│   ├── Sources/                # Put PDFs here
│   └── Notes/                  # Auto-generated summaries
└── research-today.md           # Daily summary file
```

## Configuration

Edit `config/config.yaml` to customize:
- API keys (SerpAPI for Google Scholar)
- Search settings (max results, days back)
- Paths (research directory location)
- Link format (Obsidian vs standard markdown)
- Filter criteria (business focus, relevant/irrelevant topics)
- Task system integration (optional)

Edit `config/keywords.md` to define research topics and search keywords.

See `config/README.md` for detailed configuration guide.

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
- **Check logs** if papers stop appearing: `.research-data/*.log`

## Troubleshooting

### No papers in digest
- Check cron jobs: `crontab -l | grep research`
- Check logs: `tail -f .research-data/fetch_papers.log`
- Verify SerpAPI key in config.yaml
- Run manually to see errors: `cd scripts/automation && python3 fetch_papers.py`

### Summaries not generating
- Check queue exists: `cat .research-data/.research-queue.json`
- Verify PDFs exist in Sources/ folders
- Check Claude Code is running

### Too many irrelevant papers
- Run `/filter-research-digest` on large digests
- Run `/update-research-filters` to refine criteria
- Adjust keywords to be more specific

## License

MIT

## Author

Teresa Torres
