---
name: filter-research-digest
description: Filter research digests by business relevance using configurable filter criteria to remove irrelevant papers
allowed-tools: [Read, Write, Grep, Bash, Task, AskUserQuestion]
---

# Filter Research Digest Command

Filter a research digest to show only papers relevant to your business focus.

## Step 1: Load Configuration

1. Read `~/.claude/research-system-config/config.yaml`
2. Extract filter criteria:
   - `filter.business_focus` - user's business domain (e.g., "product management and discovery")
   - `filter.relevant_topics` - array of topics to keep
   - `filter.irrelevant_topics` - array of topics to filter out
   - `filter.relevance_criteria` - description of what makes a paper relevant
3. Extract paths:
   - `paths.research_root` - base directory
   - `paths.daily_digests` - where digests are stored
4. Extract link format:
   - `links.format` - "obsidian" or "markdown"

## Step 2: Identify Digest to Filter

1. Ask user which digest to filter using AskUserQuestion:
   - Option 1: "Today's digest"
   - Option 2: "Most recent Sunday digest" (largest, weekly Google Scholar)
   - Option 3: "Specify date (YYYY-MM-DD)"

2. Based on answer:
   - If "Today's digest":
     - Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/utilities/calculate_dates.py`
     - Extract today's date from output
   - If "Sunday digest":
     - Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/utilities/calculate_dates.py`
     - Extract "Last Sunday" date from output
   - If "Specify date": Use provided date

3. Construct digest path: `research_root + "/" + daily_digests + "/" + date + ".md"`
4. Verify digest exists, show error if not found

## Step 3: Read and Analyze Digest

1. Read the digest file
2. Count total number of papers (count `### ` headers)
3. If digest is very large (>100 papers):
   - Inform user this will take a few minutes
   - Consider processing in batches

## Step 4: Filter Papers in Parallel

For efficient processing of large digests:

### 4a. Split digest into temp files

1. **Parse digest** and split by `## ` headers (topic sections)
2. **Write each section** to a temp file:
   - Create temp directory: `/tmp/research-filter-{timestamp}/`
   - For each section, write to `/tmp/research-filter-{timestamp}/section-{n}-{topic-slug}.md`
   - Include the `## Topic Name` header in each file
3. **Track sections**: Keep a list of `{section_name, temp_file_path}` for reassembly

### 4b. Spawn parallel agents

1. **Spawn one agent per section** using Task tool
2. Each agent receives:
   - Path to the section temp file (NOT the content)
   - Filter criteria from config
   - Output file path for filtered results

**Agent instructions:**
```
Filter research papers for relevance.

1. Read the section file: [temp_file_path]
2. Filter papers based on:
   - Business focus: [business_focus]
   - Relevant topics: [relevant_topics]
   - Irrelevant topics to exclude: [irrelevant_topics]
   - Relevance criteria: [relevance_criteria]

For each paper (### heading), assess:
- Does the title/snippet relate to the business focus?
- Is it in an irrelevant topic category?
- Does it meet the relevance criteria?

3. Write ONLY the relevant papers to: [output_file_path]
   - Keep the ## section header
   - Maintain original markdown format for kept papers
   - If no papers are relevant, write just the ## header
```

### 4c. Collect and reassemble

1. **Wait for all agents** to complete
2. **Read filtered results** from each output temp file
3. **Combine sections** in original order back into complete digest
4. **Clean up temp files**: Remove the `/tmp/research-filter-{timestamp}/` directory

## Step 5: Create Filtered Digest

1. Create filename: `daily_digests + "/" + date + "-filtered.md"`
2. Build filtered digest:

```markdown
# Filtered Research Digest - [date]

**Filtered for:** [business_focus]
**Original papers:** [total_count]
**After filtering:** [kept_count]
**Removed:** [removed_count]

[For each topic section that has remaining papers:]

## [Topic Name]

[Filtered papers in original format]

---

Filtered on [timestamp]
```

3. Use link format from config for any internal links
4. Write the filtered digest file

## Step 6: Update research-today.md

1. Check if `research_root + "/research-today.md"` exists
2. If it exists:
   - Read the file
   - Find the "## Today's Papers" section
   - Add a link to the filtered digest below the original digest link
   - Use the config link format (obsidian or markdown)

**Example update (Obsidian format):**
```markdown
## Today's Papers

[[daily-digests/2025-11-09]]
[[daily-digests/2025-11-09-filtered]] - Filtered (47 papers, 81% removed)
```

**Example update (Markdown format):**
```markdown
## Today's Papers

[View Today's Digest](daily-digests/2025-11-09.md)
[Filtered Digest](daily-digests/2025-11-09-filtered.md) - 47 papers, 81% removed
```

3. If research-today.md doesn't exist, skip this step (user hasn't run generate-research-digest yet)

## Step 7: Report Results

Inform the user:
- Original paper count
- Papers after filtering
- Percentage removed
- Location of filtered digest file
- Link to filtered digest (using config link format)

**Example output:**
```
Filtered 253 papers → 47 papers (81% removed)
Filtered digest: daily-digests/2025-11-02-filtered.md
```

## Error Handling

- **Config file not found**: Show error with setup instructions
- **Digest file not found**: Show clear error with available digest dates
- **No filter criteria configured**: Suggest running `/setup-research-automation` or `/update-research-filters`
- **Empty filter result**: Warn user that all papers were filtered out, suggest reviewing criteria
- **Agent failures**: Retry failed sections, continue with others
- **calculate_dates.py fails**: Fall back to system date command

## Optimization Notes

- For large digests (>100 papers), use parallel agent processing
- Process in batches of ~30-50 papers per agent for optimal performance
- Sunday digests typically have 200-300 papers and benefit most from this approach
- Filtering happens at the paper level (title + snippet analysis)
- More specific filter criteria = better results

## Filter Criteria Examples

**Good criteria:**
- business_focus: "product management and continuous discovery"
- relevant_topics: ["user research", "decision making", "product development"]
- irrelevant_topics: ["pure mathematics", "medical procedures", "agriculture"]
- relevance_criteria: "Paper must relate to how product teams make decisions or discover customer needs"

**Too vague criteria:**
- business_focus: "business"
- relevant_topics: ["AI"]
- May result in keeping too many irrelevant papers

If filtering results are poor, user should run `/update-research-filters` to refine criteria.
