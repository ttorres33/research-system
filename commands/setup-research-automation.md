---
description: Interactive setup wizard for research automation system
---

Use the `research-setup` skill to configure the research automation system.

This guided setup will:
1. Check Python dependencies are installed
2. Ask where to store research papers
3. Configure link format (Obsidian vs standard markdown)
4. Set up cron job timing for paper fetching and PDF monitoring
5. Collect your SerpAPI key for Google Scholar (optional)
6. Help you define research topics and keywords
7. Configure filter criteria for removing irrelevant papers
8. Create all necessary configuration files
9. Set up automated cron jobs
10. Validate the setup with test runs

After setup completes:
- Papers will be fetched daily at your specified time
- PDFs in your research folders will be monitored automatically
- Run `/generate-research-digest` to process new papers
- Run `/filter-research-digest` on Sundays to filter large digests

You can re-run this command to reconfigure the system at any time.
