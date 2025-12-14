---
name: check-logs
description: Check recent log entries from fetch_papers and monitor_sources scripts to diagnose issues
allowed-tools: [Read, Bash]
model: haiku
---

# Check Logs Command

Review recent log entries from both automation scripts to diagnose issues or verify the system is working correctly.

## Step 1: Load Configuration

1. Read `~/.claude/research-system-config/config.yaml`
2. Extract `paths.research_root`
3. Set log file paths:
   - `fetch_log = research_root + "/.research-data/fetch_papers.log"`
   - `monitor_log = research_root + "/.research-data/monitor_sources.log"`

## Step 2: Check Log Files Exist

1. Check if each log file exists:
   ```bash
   test -f "$fetch_log" && echo "EXISTS" || echo "NOT_FOUND"
   test -f "$monitor_log" && echo "EXISTS" || echo "NOT_FOUND"
   ```

2. Note which logs are missing (script may not have run yet)

## Step 3: Read Recent Log Entries

For each log file that exists:

1. **Get last 50 lines:**
   ```bash
   tail -50 "$log_file"
   ```

2. **Look for key patterns:**
   - Timestamps to identify when scripts last ran
   - Error messages (ERROR, Exception, Traceback, failed)
   - Success indicators (papers found, digest created, queue updated)
   - Rate limiting (429, rate limit, too many requests)
   - File not found errors (indicates broken paths)

## Step 4: Analyze and Report

**Provide a summary report:**

```
Research System Log Report

=== Fetch Papers Log ===
Last run: [timestamp from most recent entry]
Status: [OK / Errors detected / Not run yet]

Recent activity:
- [Summary of what happened in recent runs]
- [Any errors or warnings]

=== Monitor Sources Log ===
Last run: [timestamp from most recent entry]
Status: [OK / Errors detected / Not run yet]

Recent activity:
- [Summary of what happened in recent runs]
- [Any errors or warnings]

=== Issues Detected ===
[List any problems found, or "No issues detected"]

=== Recommendations ===
[Suggestions based on log analysis]
```

## Common Issues to Flag

**Fetch Papers:**
- "429" or "rate limit" → arXiv rate limiting, may need longer delays
- "No API key" or "SerpAPI" errors → Google Scholar won't work
- "file not found" or "No such file" → Run `/fix-scheduled-scripts`
- No recent entries → Cron job may not be running

**Monitor Sources:**
- "Permission denied" → Check folder permissions
- "file not found" → Run `/fix-scheduled-scripts`
- No recent entries → Cron job may not be running
- Empty queue messages → Normal if no new PDFs added

## Step 5: Provide Actionable Next Steps

Based on findings, suggest:

- `/fix-scheduled-scripts` - if path errors detected
- `/setup-research-automation` - if config missing
- `crontab -l | grep research` - if no recent log entries
- `/fetch-papers` - to manually trigger paper fetching
- Check network connectivity - if connection errors

## Error Handling

- **Log file not found**: Note that script hasn't run yet, suggest running manually or checking cron
- **Config not found**: Run `/setup-research-automation` first
- **Empty logs**: Scripts may not have run yet, check cron setup
- **Permission errors**: Note the issue, suggest checking file permissions

## Notes

- Logs are appended to, so older entries remain
- Each script run adds timestamped entries
- Cron jobs redirect both stdout and stderr to logs
- Large logs can be truncated; this command shows last 50 lines
