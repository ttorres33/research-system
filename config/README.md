# Configuration Guide

## Quick Start

1. Copy `config.template.yaml` to `config.yaml`
2. Copy `keywords.template.md` to `keywords.md`
3. Run `/setup-research-automation` to configure interactively

   OR manually edit the files:

## config.yaml

### Required Settings

- **serpapi.api_key**: Get from https://serpapi.com/ (free tier: 100 searches/month)
  - Required for Google Scholar searches
  - Leave empty to use arXiv only

- **paths.research_root**: Where your research directory is located
  - Use absolute path: `/Users/you/Research`
  - Or relative: `.` (current directory)

### Optional Settings

- **arxiv/google_scholar.max_results**: Papers per keyword (default: 10)
  - Higher = more papers but more to review
  - With 50 keywords × 10 results = up to 500 papers!

- **links.format**: Choose your link style
  - `obsidian`: Use `[[wiki-links]]` (for Obsidian users)
  - `markdown`: Use `[text](path)` (standard markdown)

- **filter**: Configure digest filtering
  - Set your business focus and relevance criteria
  - Add irrelevant topics to filter out
  - Run `/update-research-filters` to refine iteratively

- **integration**: Task system integration (advanced)
  - Set `create_task_files: true` to create markdown tasks
  - Specify `task_output_dir` and `queue_file_path`

## keywords.md

Define research topics you want to track. Each topic = one section in digests.

### Keyword Syntax

- **AND**: Require both terms
  ```
  "decision making" AND business
  ```

- **OR**: Any term matches (automatic across keywords in same topic)
  ```
  LLM OR "large language model"
  ```

- **Quotes**: Exact phrase
  ```
  "product discovery"
  ```

- **Parentheses**: Group terms
  ```
  interview AND (synthesis OR analysis)
  ```

### Best Practices

- **Group related concepts** in one topic
- **Use specific terms** to avoid noise
- **Start with 3-5 keywords per topic** and refine
- **Test keywords** by running fetch manually first

### Example Structure

```markdown
## AI & Productivity
- LLM AND "knowledge work"
- "generative AI" AND workplace
- "AI assistant" AND productivity

## User Research Methods
- "customer interview" AND analysis
- "user research" AND synthesis
- "interview coding"
```

## After Configuration

1. **Test the setup**:
   ```bash
   cd scripts/automation
   python3 fetch_papers.py  # Test paper fetching
   ```

2. **Check the cron jobs** are installed:
   ```bash
   crontab -l | grep research
   ```

3. **Monitor logs**:
   - `{research_root}/.research-data/fetch_papers.log`
   - `{research_root}/.research-data/monitor_sources.log`

4. **Adjust as needed**:
   - Add/remove keywords
   - Adjust max_results
   - Refine filter criteria with `/update-research-filters`
