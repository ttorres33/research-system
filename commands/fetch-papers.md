---
name: fetch-papers
description: Manually run the paper fetching script to retrieve new papers from arXiv and Google Scholar
allowed-tools: [Read, Bash]
model: haiku
---

# Fetch Papers Command

Manually trigger paper fetching from arXiv and Google Scholar instead of waiting for the scheduled cron job.

## Step 1: Load Configuration

1. Read `~/.claude/research-system-config/config.yaml`
2. Extract `paths.research_root` for log file location
3. Set `log_file = research_root + "/.research-data/fetch_papers.log"`

## Step 2: Run Fetch Script

1. **Run the fetch script:**
   ```bash
   cd ${CLAUDE_PLUGIN_ROOT}/scripts/automation && python3 fetch_papers.py
   ```

2. **Capture output** - the script will show:
   - Which sources are being searched (arXiv, Google Scholar)
   - Number of papers found per keyword/topic
   - Any errors or rate limiting messages
   - Path to created digest file

## Step 3: Report Results

**Provide summary to user:**

```
Fetch Papers Complete

Sources searched:
- arXiv: [X] keywords searched
- Google Scholar: [Searched / Skipped (not Sunday) / No API key]

Results:
- New papers found: [X]
- Digest created: [path to daily-digests/YYYY-MM-DD.md]

[If any errors occurred, list them here]
```

**If script fails:**
- Show the error output
- Suggest checking `log_file` for details
- Common issues:
  - Network connectivity
  - Rate limiting (arXiv 429 errors)
  - Invalid SerpAPI key

## Error Handling

- **Script not found**: Run `/fix-scheduled-scripts` to repair plugin symlink
- **Config not found**: Run `/setup-research-automation` first
- **Python errors**: Show full error output for debugging
- **Rate limiting**: Note that arXiv has a 10-second delay between queries

## Notes

- Google Scholar searches only run on Sundays (to conserve API quota)
- arXiv searches run every time
- Results are written to `daily-digests/YYYY-MM-DD.md`
- Duplicate papers (seen before) are automatically filtered out
- Check `.research-data/fetch_papers.log` for detailed execution history
