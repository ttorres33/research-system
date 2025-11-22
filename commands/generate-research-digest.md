---
name: generate-research-digest
description: Generate summaries for new research PDFs and create today's research digest file with links to papers and summaries
allowed-tools: [Read, Write, Edit, Grep, Bash, Task]
---

# Generate Research Digest Command

Generate summaries for new research papers and create a daily digest file.

## Step 1: Load Configuration

1. Read `~/.claude/research-system-config/config.yaml`
2. Extract key paths:
   - `paths.research_root` - base directory for research files
   - `paths.daily_digests` - where digests are stored (relative to research_root)
   - `paths.data` - where tracking/queue files are stored (relative to research_root)
   - `links.format` - "obsidian" or "markdown" for link format

3. Set working paths:
   - `digest_dir = research_root + "/" + daily_digests`
   - `data_dir = research_root + "/" + data`
   - `queue_file = data_dir + "/.research-queue.json"`

## Step 2: Get Today's Date

1. Set plugin directory: `plugin_dir = ~/.claude/plugins/cache/research-system`
2. Run: `python3 $plugin_dir/scripts/utilities/calculate_dates.py`
3. Parse output to extract today's date in YYYY-MM-DD format
4. Store as `today_date`

## Step 3: Read Research Queue

1. Check if queue file exists at `queue_file`
2. If not found, set `queue_missing = true` and `queue_items = []`
3. If found, read the JSON file
4. Parse the queue - it contains an array of task file paths or PDF paths needing summaries
5. Store the queue items count for final report
6. **Continue to completion even if queue is empty - user needs final status report**

## Step 4: Process Each Queued Item

For each item in the queue:

1. **Verify PDF exists:**
   - Check if file exists at the PDF path
   - If not found, skip with warning and continue

2. **Check if summary already exists:**
   - Determine summary path: same as PDF but in `Notes/` folder instead of `Sources/` and `.md` extension
   - Example: `Research/AI & Productivity/Sources/paper.pdf` → `Research/AI & Productivity/Notes/paper.md`
   - If summary exists, skip (already processed)

3. **Check PDF size and conditionally split:**
   - Get file size in bytes: `stat -f%z "$pdf_path"`
   - Calculate output path: change `Sources/file.pdf` to `Notes/file.md`

   **If size ≥ 5242880 bytes (5 MB) - Large PDF:**
   - Set `is_large_pdf = true`
   - Generate unique timestamp: `date +%s`
   - Create temp directories:
     - Section PDFs: `/tmp/research-sections-{timestamp}`
     - Section summaries: `/tmp/research-summaries-{timestamp}`
   - Run: `python3 $plugin_dir/scripts/utilities/split_pdf_by_sections.py "$pdf_path" "/tmp/research-sections-$timestamp"`
     - This splits PDF into section files (000_Introduction.pdf, 001_Methods.pdf, etc.)
   - List section PDF files in numerical order
   - **Extract metadata from first section:**
     - Read the first section PDF (000_*.pdf) to extract:
       - Paper title (usually in header/title block)
       - Publication date (if available)
     - Store for use in final summary
   - For each section PDF, spawn a research-summarizer agent IN PARALLEL:
     - Use Task tool with subagent_type="research-system:research-summarizer"
     - Pass PDF path: `/tmp/research-sections-{timestamp}/00X_SectionName.pdf`
     - Pass output path: `/tmp/research-summaries-{timestamp}/00X_SectionName.md`
   - Wait for all agents to complete
   - Aggregate section summaries:
     - Extract tags from all section summary files (read only frontmatter):
       ```bash
       grep "^tags:" /tmp/research-summaries-{timestamp}/*.md
       ```
     - Combine and deduplicate tags, keep top 5-10 most relevant
     - Create final frontmatter header using metadata from step 3:
       ```markdown
       ---
       tags: [aggregated, deduplicated, tags]
       ---

       # Paper Title

       Publication Date: [if found]

       ```
     - Write frontmatter to output path in Notes/ folder
     - Use bash to append all section summaries (strip their frontmatter):
       ```bash
       for file in /tmp/research-summaries-{timestamp}/*.md; do
         sed '1,/^---$/d; 1,/^---$/d' "$file" >> "$output_path"
       done
       ```
   - Cleanup: `rm -rf "/tmp/research-sections-{timestamp}" "/tmp/research-summaries-{timestamp}"`

   **If size < 5242880 bytes (5 MB) - Small PDF:**
   - Set `is_large_pdf = false`
   - Generate unique timestamp: `date +%s`
   - **Extract metadata:**
     - Read first 2 pages of PDF to extract:
       - Paper title (usually in header/title block)
       - Publication date (if available)
     - Store for use in final summary
   - Create temp file for summary: `/tmp/research-summary-{timestamp}.md`
   - Spawn single research-summarizer agent:
     - Use Task tool with subagent_type="research-system:research-summarizer"
     - Pass PDF path: `$pdf_path`
     - Pass output path: `/tmp/research-summary-{timestamp}.md`
   - Wait for agent to complete
   - Extract tags from agent's summary file (read only frontmatter)
   - Create final summary at output path:
     - Write frontmatter with tags from agent
     - Add paper title as `# Title` using metadata from step 3
     - Add publication date using metadata from step 3
     - Append agent's summary content (strip the frontmatter from temp file):
       ```bash
       sed '1,/^---$/d; 1,/^---$/d' /tmp/research-summary-{timestamp}.md >> "$output_path"
       ```
   - Cleanup: `rm "/tmp/research-summary-{timestamp}.md"`

5. **Track processed items:**
   - Keep list of newly generated summaries (PDF path → summary path)
   - Keep list of skipped items (with reasons)

## Step 5: Find Today's Daily Digest

1. Construct digest path using `today_date`: `digest_dir + "/" + today_date + ".md"`
2. Check if today's digest exists
3. Store status for final report: `digest_exists = true/false`
4. **Continue to next step even if digest doesn't exist - will be noted in final report**

## Step 6: Archive Previous research-today.md

Before creating the new file:

1. Check if `research_root + "/research-today.md"` exists
2. If it exists:
   - Read the file
   - Extract date from the first line: `# Research Digest - YYYY-MM-DD`
   - Use regex or string parsing to get the date
   - Create archive directory if needed: `research_root + "/research-today-archive"`
   - Copy the file to: `research_root + "/research-today-archive/" + [extracted_date] + ".md"`
   - Example: `research-today-archive/2025-11-03.md`
3. If file doesn't exist or date extraction fails, skip archiving (first run)

## Step 7: Create research-today.md

1. **Always create this file** - even if there are no new summaries
2. Create file at `research_root + "/research-today.md"`
3. **IMPORTANT: Use link format from config:**
   - If `links.format` is "obsidian": Use `[[filename]]` format
   - If `links.format` is "markdown": Use `[text](relative/path/to/file.md)` format

**File structure:**

```markdown
# Research Digest - [today_date]

## Today's Papers

[If digest_exists is true:]
[Create link to today's digest using config link format]
- If obsidian: [[daily-digests/YYYY-MM-DD]]
- If markdown: [View Today's Digest](daily-digests/YYYY-MM-DD.md)

[Check if filtered digest exists: daily-digests/YYYY-MM-DD-filtered.md]
[If filtered digest exists, add a second link on the next line]
- If obsidian: [[daily-digests/YYYY-MM-DD-filtered]] - Filtered
- If markdown: [Filtered Digest](daily-digests/YYYY-MM-DD-filtered.md)

[If digest_exists is false:]
No digest found for today. Run fetch_papers.py to retrieve today's papers.

## Newly Summarized Papers

[If there are newly generated summaries:]
[For each newly generated summary, create link using config link format:]
- **[Topic Name]**:
  - If obsidian: [[Topic/Notes/paper-name]] - [Paper title]
  - If markdown: [Paper title](Topic/Notes/paper-name.md)

[If no new summaries:]
No new papers were summarized today.

## Papers Still Needing Review

[If there were any skipped items:]
- [PDF name]: [Reason skipped]

[If no skipped items:]
All queued papers have been processed.

---

Generated on [timestamp]
```

4. Write the file

**Example with Obsidian links (with filtered digest):**
```markdown
# Research Digest - 2025-11-03

## Today's Papers

[[daily-digests/2025-11-03]]
[[daily-digests/2025-11-03-filtered]] - Filtered

## Newly Summarized Papers

- **AI & Productivity**: [[AI & Productivity/Notes/llm-knowledge-work]] - LLMs and Knowledge Work
- **Decision Making**: [[Decision Making/Notes/managerial-decisions]] - Managerial Decision Making

---

Generated on 2025-11-03 10:30 AM
```

**Example with Markdown links (with filtered digest):**
```markdown
# Research Digest - 2025-11-03

## Today's Papers

[View Today's Digest](daily-digests/2025-11-03.md)
[Filtered Digest](daily-digests/2025-11-03-filtered.md)

## Newly Summarized Papers

- **AI & Productivity**: [LLMs and Knowledge Work](AI & Productivity/Notes/llm-knowledge-work.md)
- **Decision Making**: [Managerial Decision Making](Decision Making/Notes/managerial-decisions.md)

---

Generated on 2025-11-03 10:30 AM
```

## Step 8: Clear Queue

1. **Only clear queue if items were successfully processed**
2. If queue file exists and any items were processed (successfully or skipped):
   - Write empty array `[]` to queue file
   - This resets the queue for next run
3. If queue was missing, no action needed

## Step 9: Report Results

**ALWAYS provide a comprehensive status report**, including:

1. **Queue Status:**
   - If queue was missing: "No research queue found. Run monitor_sources.py cron job or manually add PDFs."
   - If queue was empty: "Research queue was empty."
   - If queue had items: "Processed [X] items from queue."

2. **Processing Summary:**
   - Number of new summaries generated: "[X] papers summarized"
   - Number already processed (skipped because summary exists): "[X] papers already had summaries"
   - Number skipped due to errors: "[X] papers skipped" with brief reason
   - If no items to process: "No papers needed processing."

3. **Daily Digest Status:**
   - If digest exists: "Today's digest available at: [path]"
   - If digest doesn't exist: "No digest for today. Run fetch_papers.py to retrieve papers."
   - If filtered digest exists: "Filtered digest also available."

4. **Output Files:**
   - Location of research-today.md file: "[full_path]"
   - If previous research-today.md was archived: "Previous digest archived to: [archive_path]"

5. **Next Steps (if applicable):**
   - If digest missing: "Run fetch_papers.py to fetch today's papers from arXiv"
   - If papers skipped: "Review skipped papers listed in research-today.md"
   - If queue was missing: "Set up the cron job to automatically monitor sources"

**Example comprehensive report:**
```
Research Digest Generation Complete

Queue Status: Processed 3 items from queue

Processing Summary:
- 2 papers summarized successfully
- 1 paper already had a summary (skipped)
- 0 papers skipped due to errors

Daily Digest Status:
- Today's digest available at: /Users/user/Research/daily-digests/2025-11-11.md
- Filtered digest also available

Output Files:
- research-today.md created at: /Users/user/Research/research-today.md
- Previous digest archived to: research-today-archive/2025-11-10.md

All papers processed successfully.
```

**Example when nothing to do:**
```
Research Digest Generation Complete

Queue Status: Research queue was empty

Processing Summary:
- 0 papers summarized
- No papers needed processing

Daily Digest Status:
- Today's digest available at: /Users/user/Research/daily-digests/2025-11-11.md

Output Files:
- research-today.md updated at: /Users/user/Research/research-today.md

No new papers to process. System is up to date.
```

**Example when queue missing:**
```
Research Digest Generation Complete

Queue Status: No research queue found

Processing Summary:
- 0 papers summarized
- No papers to process

Daily Digest Status:
- No digest for today

Output Files:
- research-today.md updated at: /Users/user/Research/research-today.md

Next Steps:
- Run monitor_sources.py cron job to populate the queue
- Or run fetch_papers.py to fetch today's papers from arXiv
```

## Error Handling

- **Queue file not found**: Continue with empty queue, note in final report
- **Queue empty**: Continue to completion, note in final report
- **PDF not found**: Skip with warning, continue processing others, include in final report
- **Summary generation fails**: Log error, skip that PDF, continue with others, include in final report
- **Config file not found**: Show error with setup instructions, cannot continue
- **Permission errors**: Show clear error message with file path, note in final report
- **calculate_dates.py fails**: Fall back to system date command, continue
- **Invalid link format in config**: Default to obsidian format with warning, continue
- **Daily digest not found**: Note in research-today.md and final report, continue
- **No new papers to process**: Complete successfully with informative report

**Key principle: Always complete execution and provide comprehensive status report**

## Notes

- This command processes the queue created by monitor_sources.py cron job
- Summaries are generated in parallel using Task tool for efficiency
- The research-today.md file is regenerated each time (overwrites previous)
- Queue is only cleared after successful processing of all items
- **Always respect the link format setting** - this ensures compatibility with user's markdown viewer
