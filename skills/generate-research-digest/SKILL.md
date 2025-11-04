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

1. **Determine if it's a task file or PDF path:**
   - If path ends with `.md` → it's a task file (contains metadata about PDF)
   - If path ends with `.pdf` → it's a direct PDF path

2. **Extract PDF path:**
   - If task file: Read the file, extract `source_path` from frontmatter
   - If PDF: Use the path directly

3. **Verify PDF exists:**
   - Check if file exists at the PDF path
   - If not found, skip with warning and continue

4. **Check if summary already exists:**
   - Determine summary path: same as PDF but in `Notes/` folder instead of `Sources/` and `.md` extension
   - Example: `Research/AI & Productivity/Sources/paper.pdf` → `Research/AI & Productivity/Notes/paper.md`
   - If summary exists, skip (already processed)

5. **Generate summary using research-summarizer agent:**
   - Use Task tool to spawn research-summarizer agent
   - Pass PDF path as parameter
   - Agent will create summary in appropriate Notes/ folder
   - Wait for agent to complete

6. **Track processed items:**
   - Keep list of newly generated summaries (PDF path → summary path)
   - Keep list of skipped items (with reasons)

## Step 5: Find Today's Digest

1. Construct digest path using `today_date`: `digest_dir + "/" + today_date + ".md"`
2. Check if today's digest exists
3. If not found:
   - Check if it's Sunday (no arXiv papers typically)
   - Inform user digest may not exist yet or suggest running fetch_papers.py

## Step 6: Create research-today.md

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

## Step 7: Update Task Files (if applicable)

If queue contained task file paths (not just PDF paths):

1. For each successfully processed task file:
   - Read the task file
   - Update frontmatter:
     - Change `tags: [research-summary-needed]` to `tags: [research-review]`
     - Add `summary_path: "[path to generated summary]"`
   - Update body with link to summary (using config link format)
   - Write updated task file

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
- Task file updates are optional (only if task files exist in queue)
- **Always respect the link format setting** - this ensures compatibility with user's markdown viewer
