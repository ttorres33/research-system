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
2. Extract `paths.research_root`; the digest is written to `research_root/daily-digests/YYYY-MM-DD.md`

## Step 2: Run Fetch Script

1. **Run the fetch script:**
   ```bash
   cd ${CLAUDE_PLUGIN_ROOT}/scripts/automation && python3 fetch_papers.py
   ```

2. **Capture output** - the script will show:
   - The arXiv harvest: the date it started from, how many records came back, how many are
     new papers not seen before
   - Per topic: its mode and categories, the size of its pool, keyword matches, and the
     number of papers set aside for the Claude review
   - Google Scholar results per topic on Sundays, or "skipped: no keywords"
   - Any note that will appear at the top of the digest (harvest failure, capped catch-up,
     unsupported keyword syntax)
   - Path to the created digest file, and the candidates file if a Claude review is pending

## Step 3: Report Results

**Provide summary to user:**

```
Fetch Papers Complete

arXiv harvest: [N] records since [date], [M] new papers
Google Scholar: [Searched / Skipped (not Sunday) / No API key]

Per topic:
- [Topic]: [K] keyword matches, [C] waiting for the Claude review

Digest created: [path to daily-digests/YYYY-MM-DD.md]
[If a Claude review is pending: "Run /generate-research-digest to have Claude read [C] candidates"]

[If any errors occurred, list them here]
```

**If script fails:**
- Show the error output (a manual run prints everything to the terminal; it does not append to the log file)
- Common issues:
  - Network connectivity
  - arXiv's OAI-PMH endpoint returning 503 or timing out (the script retries three times,
    honouring Retry-After, then writes a digest note; the next run catches up automatically)
  - Invalid SerpAPI key

## Error Handling

- **Script not found**: Run `/fix-scheduled-scripts` to repair plugin symlink
- **Config not found**: Run `/setup-research-automation` first
- **Python errors**: Show full error output for debugging
- **Harvest failed**: Nothing to fix on the user's side; the harvest state is unchanged and the next run starts from the same date

## Notes

- Google Scholar searches only run on Sundays (to conserve API quota) and only for topics with keywords
- arXiv is harvested every time through OAI-PMH: everything announced since the last run, in two to five requests, then matched per topic by categories and mode
- Results are written to `daily-digests/YYYY-MM-DD.md`; papers for Claude-mode topics are written to `.research-data/claude-candidates/YYYY-MM-DD.json` and reviewed by `/generate-research-digest`
- Duplicate papers (seen before) are automatically filtered out
- `.research-data/fetch_papers.log` holds the history of the scheduled (cron) runs only; the crontab redirects each run's output there
