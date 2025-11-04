---
description: Generate summaries for new research PDFs and create today's research digest
---

Use the `generate-research-digest` skill to process new research papers that have been detected by the monitoring system.

This command will:
1. Read the research queue (created by the monitor_sources.py cron job)
2. Generate AI summaries for each new PDF
3. Create a research-today.md file with links to:
   - Today's digest of newly discovered papers
   - All newly generated summaries
   - Any PDFs that still need review
