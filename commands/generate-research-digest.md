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
   - `candidates_dir = data_dir + "/claude-candidates"` (arXiv papers waiting for the Claude review)

## Step 2: Get Today's Date

1. Run: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/utilities/calculate_dates.py`
2. Parse output to extract today's date in YYYY-MM-DD format
3. Store as `today_date`

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
   - Run: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/utilities/split_pdf_by_sections.py "$pdf_path" "/tmp/research-sections-$timestamp"`
     - This splits PDF into section files (000_Introduction.pdf, 001_Methods.pdf, etc.)
   - List section PDF files in numerical order
   - For each section PDF, spawn a research-summarizer agent IN PARALLEL:
     - Use Task tool with subagent_type="research-system:research-summarizer"
     - Pass PDF path: `/tmp/research-sections-{timestamp}/00X_SectionName.pdf`
     - Pass output path: `/tmp/research-summaries-{timestamp}/00X_SectionName.md`
   - Wait for all agents to complete
   - Aggregate section summaries:
     - Read all section summary files to extract from frontmatter:
       - All tags (combine and deduplicate, keep top 5-10 most relevant)
       - Title from first section's frontmatter
       - Date from first section's frontmatter (if found)
     - Create final frontmatter header:
       ```markdown
       ---
       tags: [aggregated, deduplicated, tags]
       title: "Title from first section"
       date: "Date from first section (if found)"
       ---
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
   - Spawn single research-summarizer agent:
     - Use Task tool with subagent_type="research-system:research-summarizer"
     - Pass PDF path: `$pdf_path`
     - Pass output path directly to Notes/ folder (no temp file needed)
   - Wait for agent to complete
   - Agent will create the summary file with frontmatter (tags, title, date) and content all in one file

5. **Track processed items:**
   - Keep list of newly generated summaries (PDF path → summary path)
   - Keep list of skipped items (with reasons)

## Step 5: Find Today's Daily Digest

1. Construct digest path using `today_date`: `digest_dir + "/" + today_date + ".md"`
2. **Check if today's digest exists using bash test command:**
   ```bash
   test -f "$digest_dir/$today_date.md" && echo "EXISTS" || echo "NOT FOUND"
   ```
3. Store status for final report: `digest_exists = true/false`
4. **Continue to next step even if digest doesn't exist - will be noted in final report**

## Step 5b: Claude Review of arXiv Candidates

The scheduled run records, once, every new arXiv paper that falls in the categories of at
least one topic in `claude` or `both` mode, together with the topics each paper is eligible
for and every Claude topic's brief. The digest shows one line per Claude topic:
`_N papers await Claude review. Run /generate-research-digest._` This step has Claude read
each paper once, keep it under every eligible topic whose brief it fits, and writes the
keepers into the digest. Run it before Step 6 so the archived and linked digest is complete.

1. **Find today's candidates:** `candidates_file = candidates_dir + "/" + today_date + ".json"`
   - If it does not exist: set `review_status = "no candidates"` and skip to Step 6
   - Read it. If it has a `processed_at` field: set `review_status = "already done"` and skip to Step 6
   - Also list any other `*.json` in `candidates_dir` without `processed_at` (earlier days the
     command was not run); store their dates as `older_candidates` for the report. Do not process them here.

2. **Check for a stale filtered digest:** if `digest_dir + "/" + today_date + "-filtered.md"`
   exists, set `filtered_stale = true`; it was made before this review and must be regenerated
   with `/filter-research-digest` afterwards (tell the user in the report).

3. **Prepare the batch files.** Use a fixed working directory for the day,
   `triage_dir = /tmp/research-triage-{today_date}`, and write both paths out in full
   (each bash call starts a fresh shell, so do not rely on shell variables between steps):
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/utilities/apply_claude_triage.py prepare "[candidates_file]" "/tmp/research-triage-[today_date]"
   ```
   This writes batch files of at most 40 papers each. Every batch carries all the Claude
   topics' briefs (with the topic's keywords as examples), the exclusions, and per paper
   its id, category, eligible topics, title and abstract, plus `manifest.json` in that
   directory listing each batch file and the path its result must be written to. Read the
   manifest to get the batch file paths for the next step. If the manifest is empty, every
   candidate has aged out of the harvest files; go straight to step 5.

4. **Spawn one agent per batch file, in parallel,** using the Task tool. Each agent receives
   the batch file path (not its content) and these instructions:
   ```
   Review arXiv papers against the user's research topics.

   1. Read the batch file: [batch_path]. Its header states where to write your result and
      the exact JSON format. The "Topics" section gives each topic's brief, with the
      keywords the user searches with as examples; "Exclude" lists what to leave out of
      every topic.
   2. For each paper under "Papers", read the title and abstract and decide, for each of
      the topics listed as eligible for that paper and only those, whether it fits that
      topic's brief. A paper may fit more than one topic, or none. Be selective: the user
      reads every paper you keep.
   3. Write the result file named in the header as JSON:
      {"kept": [{"id": "...", "topic": "...", "why": "..."}]} with one entry per paper and
      topic kept, the topic name exactly as written, and a "why" of at most 25 words. If
      nothing fits, write {"kept": []}. Only ids and topic names from the batch file are allowed.
   ```

5. **Wait for all agents**, then apply the results:
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/utilities/apply_claude_triage.py apply "[candidates_file]" "/tmp/research-triage-[today_date]"
   ```
   Python rewrites the digest: each topic's pending line becomes
   `_Claude reviewed N candidates, kept K._` (N is the papers eligible for that topic)
   followed by the kept papers in the digest's normal format with a `**Why:**` line. A paper
   kept for two topics appears under both. The candidates file gets `processed_at`.
   The command prints one line per topic (`"Topic": reviewed N, kept K`); keep them for the report.
   - Exit code 2 with "nothing applied" means a batch result was missing or unreadable;
     re-run that agent and `apply` again. Exit code 2 naming topics means the digest no
     longer had those topics' pending lines (it was rebuilt by a manual fetch); run
     `fetch_papers.py --force` and start this step over. Do not hand-edit the digest.

6. **Clean up:** `rm -rf "/tmp/research-triage-[today_date]"`. Set `review_status = "done"` with the per-topic counts.

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

[If review_status is "done": add a line "Claude review: kept K of N arXiv candidates across M topics"]

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

3. **Claude Review Status:**
   - If review_status is "done": "Claude reviewed [N] arXiv candidates across [M] topics and kept [K]" plus the per-topic lines
   - If "already done": "Claude review already applied earlier today"
   - If "no candidates": "No arXiv papers were waiting for a Claude review" (every topic is in keyword mode, or nothing new landed in the Claude topics' categories)
   - If `older_candidates` is not empty: "Unreviewed candidates from earlier days: [dates]. They were not processed; the harvest files behind them are kept for 7 days."
   - If `filtered_stale` is true: "The filtered digest for today was made before this review; run /filter-research-digest again to include the kept papers"

4. **Daily Digest Status:**
   - If digest exists: "Today's digest available at: [path]"
   - If digest doesn't exist: "No digest for today. Run fetch_papers.py to retrieve papers."
   - If filtered digest exists: "Filtered digest also available."

5. **Output Files:**
   - Location of research-today.md file: "[full_path]"
   - If previous research-today.md was archived: "Previous digest archived to: [archive_path]"

6. **Next Steps (if applicable):**
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
- **Candidates file unreadable or `prepare` fails**: Report the error, leave the pending lines in the digest, continue
- **A review agent fails or writes no result**: `apply` reports the topic and keeps its pending line; re-run that agent and `apply` again, then continue
- **`apply` cannot find a topic's pending line**: The digest was edited by hand or already processed; report it and continue
- **No new papers to process**: Complete successfully with informative report

**Key principle: Always complete execution and provide comprehensive status report**

## Notes

- This command processes the queue created by monitor_sources.py cron job
- Summaries are generated in parallel using Task tool for efficiency
- The research-today.md file is regenerated each time (overwrites previous)
- Queue is only cleared after successful processing of all items
- **Always respect the link format setting** - this ensures compatibility with user's markdown viewer
- **Order on Sundays: run this command before `/filter-research-digest`.** The filter reads the digest file, so a filtered digest made before the Claude review will not contain the kept papers
- The Claude review reads each candidate paper once, title and abstract only, against every Claude topic it is eligible for by category; the brief comes from each topic's `looking for` setting in `keywords.md` (or the config's filter criteria when a topic has none). Cost is the number of candidate papers, however many Claude topics there are
