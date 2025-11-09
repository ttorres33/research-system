---
name: generate-research-digest
description: Generate summaries for new research PDFs and create today's research digest file with links to papers and summaries
allowed-tools: [Read, Write, Edit, Grep, Bash, Task]
---

# Generate Research Digest Skill

When invoked, generate summaries for new research papers and create a daily digest file.

## Step 1: Load Configuration

1. Find the plugin installation directory (check for .claude-plugin/plugin.json)
2. Read `config/config.yaml` from plugin directory
3. Extract key paths:
   - `paths.research_root` - base directory for research files
   - `paths.daily_digests` - where digests are stored (relative to research_root)
   - `paths.data` - where tracking/queue files are stored (relative to research_root)
   - `links.format` - "obsidian" or "markdown" for link format

4. Set working paths:
   - `digest_dir = research_root + "/" + daily_digests`
   - `data_dir = research_root + "/" + data`
   - `queue_file = data_dir + "/.research-queue.json"`
   - `plugin_dir = [directory containing .claude-plugin/plugin.json]`

## Step 2: Get Today's Date

1. Run: `python3 {plugin_dir}/scripts/utilities/calculate_dates.py`
2. Parse output to extract today's date in YYYY-MM-DD format
3. Store as `today_date`

## Step 3: Read Research Queue

1. Check if queue file exists at `queue_file`
2. If not found, inform user: "No research queue found. Run the monitor_sources.py cron job or manually add PDFs to your research directories."
3. If found, read the JSON file
4. Parse the queue - it contains an array of task file paths or PDF paths needing summaries
5. If queue is empty, inform user: "Research queue is empty. No new papers to process."

## Step 4: Process Each Queued Item

For each item in the queue:

1. **Verify PDF exists:**
   - Check if file exists at the PDF path
   - If not found, skip with warning and continue

2. **Check if summary already exists:**
   - Determine summary path: same as PDF but in `Notes/` folder instead of `Sources/` and `.md` extension
   - Example: `Research/AI & Productivity/Sources/paper.pdf` → `Research/AI & Productivity/Notes/paper.md`
   - If summary exists, skip (already processed)

3. **Extract paper metadata:**
   - Read first 2 pages of PDF to extract:
     - Paper title (usually in header/title block)
     - Publication date (if available)
   - Store for use in final summary

4. **Check PDF size and conditionally process:**
   - Get file size in bytes: `stat -f%z "$pdf_path"`
   - Calculate output path: change `Sources/file.pdf` to `Notes/file.md`

   **If size ≥ 5242880 bytes (5 MB) - Large PDF:**
   - Generate unique timestamp: `date +%s`
   - Create temp directories:
     - Section PDFs: `/tmp/research-sections-{timestamp}`
     - Section summaries: `/tmp/research-summaries-{timestamp}`
   - Run: `python3 {plugin_dir}/scripts/utilities/split_pdf_by_sections.py "$pdf_path" "/tmp/research-sections-{timestamp}"`
     - This splits PDF into section files (000_Introduction.pdf, 001_Methods.pdf, etc.)
   - List section PDF files in numerical order
   - For each section PDF, spawn a research-summarizer agent IN PARALLEL:
     - PDF path: `/tmp/research-sections-{timestamp}/00X_SectionName.pdf`
     - Output path: `/tmp/research-summaries-{timestamp}/00X_SectionName.md`
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
   - Create temp file for summary: `/tmp/research-summary-{timestamp}.md`
   - Spawn single research-summarizer agent:
     - PDF path: `$pdf_path`
     - Output path: `/tmp/research-summary-{timestamp}.md`
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
3. If not found:
   - Inform user digest may not exist yet or suggest running fetch_papers.py

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

1. Create file at `research_root + "/research-today.md"`
2. **IMPORTANT: Use link format from config:**
   - If `links.format` is "obsidian": Use `[[filename]]` format
   - If `links.format` is "markdown": Use `[text](relative/path/to/file.md)` format

**File structure:**

```markdown
# Research Digest - [today_date]

## Today's Papers

[Create link to today's digest using config link format]
- If obsidian: [[daily-digests/YYYY-MM-DD]]
- If markdown: [View Today's Digest](daily-digests/YYYY-MM-DD.md)

## Newly Summarized Papers

[For each newly generated summary, create link using config link format:]
- **[Topic Name]**:
  - If obsidian: [[Topic/Notes/paper-name]] - [Paper title]
  - If markdown: [Paper title](Topic/Notes/paper-name.md)

## Papers Still Needing Review

[If there were any skipped items:]
- [PDF name]: [Reason skipped]

---

Generated on [timestamp]
```

3. Write the file

**Example with Obsidian links:**
```markdown
# Research Digest - 2025-11-03

## Today's Papers

[[daily-digests/2025-11-03]]

## Newly Summarized Papers

- **AI & Productivity**: [[AI & Productivity/Notes/llm-knowledge-work]] - LLMs and Knowledge Work
- **Decision Making**: [[Decision Making/Notes/managerial-decisions]] - Managerial Decision Making

---

Generated on 2025-11-03 10:30 AM
```

**Example with Markdown links:**
```markdown
# Research Digest - 2025-11-03

## Today's Papers

[View Today's Digest](daily-digests/2025-11-03.md)

## Newly Summarized Papers

- **AI & Productivity**: [LLMs and Knowledge Work](AI & Productivity/Notes/llm-knowledge-work.md)
- **Decision Making**: [Managerial Decision Making](Decision Making/Notes/managerial-decisions.md)

---

Generated on 2025-11-03 10:30 AM
```

## Step 8: Clear Queue

1. Write empty array `[]` to queue file
2. This resets the queue for next run

## Step 9: Report Results

Inform the user:
- Number of summaries generated
- Location of research-today.md file
- Link to today's digest (if found)
- Any warnings or skipped items

## Error Handling

- **Queue file not found**: Inform user to run cron job or check setup
- **PDF not found**: Skip with warning, continue processing others
- **Summary generation fails**: Log error, skip that PDF, continue with others
- **Config file not found**: Show error with setup instructions
- **Permission errors**: Show clear error message with file path
- **calculate_dates.py fails**: Fall back to system date command
- **Invalid link format in config**: Default to obsidian format with warning

## Notes

- This skill processes the queue created by monitor_sources.py cron job
- Summaries are generated in parallel using Task tool for efficiency
- The research-today.md file is regenerated each time (overwrites previous)
- Queue is only cleared after successful processing of all items
- **Always respect the link format setting** - this ensures compatibility with user's markdown viewer
