---
name: monitor-sources
description: Manually scan Sources folders for new PDFs and add them to the summarization queue
allowed-tools: [Read, Bash]
model: haiku
---

# Monitor Sources Command

Manually trigger scanning of Sources folders for new PDFs instead of waiting for the scheduled cron job. New PDFs are added to the queue for summarization.

## Step 1: Load Configuration

1. Read `~/.claude/research-system-config/config.yaml`
2. Extract `paths.research_root` for log file and queue locations
3. Set paths:
   - `log_file = research_root + "/.research-data/monitor_sources.log"`
   - `queue_file = research_root + "/.research-data/.research-queue.json"`

## Step 2: Run Monitor Script

1. **Run the monitor script:**
   ```bash
   cd ${CLAUDE_PLUGIN_ROOT}/scripts/automation && python3 monitor_sources.py
   ```

2. **Capture output** - the script will show:
   - Which topic folders were scanned
   - New PDFs found
   - PDFs added to queue
   - PDFs skipped (already processed)

## Step 3: Report Results

**Provide summary to user:**

```
Monitor Sources Complete

Folders scanned: [X] topic folders
New PDFs found: [X]
Added to queue: [X]
Already processed: [X] (skipped)

Queue status:
- Total items in queue: [X]
- Queue file: [path to .research-queue.json]

[If new PDFs were found:]
Run /generate-research-digest to create summaries for queued papers.
```

**If no new PDFs:**
```
Monitor Sources Complete

Folders scanned: [X] topic folders
No new PDFs found.

To add papers for summarization:
1. Download PDFs to your topic's Sources/ folder
2. Run /monitor-sources again (or wait for cron job)
3. Run /generate-research-digest to create summaries
```

## Error Handling

- **Script not found**: Run `/fix-scheduled-scripts` to repair plugin symlink
- **Config not found**: Run `/setup-research-automation` first
- **Permission errors**: Check folder permissions on Sources/ directories
- **Python errors**: Show full error output for debugging

## Notes

- The script scans all `[Topic]/Sources/` folders under research_root
- PDFs are tracked in `.research-data/.processed_pdfs.json` to avoid re-processing
- Queue is stored in `.research-data/.research-queue.json`
- After monitoring, run `/generate-research-digest` to process the queue
- Check `.research-data/monitor_sources.log` for detailed execution history
