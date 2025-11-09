---
name: filter-research-digest
description: Filter research digests by business relevance using configurable filter criteria to remove irrelevant papers
allowed-tools: [Read, Write, Grep, Bash, Task, AskUserQuestion]
---

# Filter Research Digest Skill

When invoked, filter a research digest to show only papers relevant to the user's business focus.

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
     - Run `python3 {plugin_dir}/scripts/utilities/calculate_dates.py`
     - Extract today's date from output
   - If "Sunday digest":
     - Run `python3 {plugin_dir}/scripts/utilities/calculate_dates.py`
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

1. **Split digest into sections** by topic headings (`## Topic Name`)
2. **Spawn parallel agents** (one per topic section) using Task tool
3. Each agent filters papers in its section based on:
   - business_focus from config
   - relevant_topics from config
   - irrelevant_topics from config
   - relevance_criteria from config

**Agent instructions for each section:**
```
Review the following research papers and filter out papers that are NOT relevant to:
- Business focus: [business_focus]
- Relevant topics: [relevant_topics]
- Irrelevant topics to exclude: [irrelevant_topics]
- Relevance criteria: [relevance_criteria]

For each paper, assess:
1. Does the title/snippet relate to the business focus?
2. Is it in an irrelevant topic category?
3. Does it meet the relevance criteria?

Return only papers that ARE relevant. Remove all others.
Maintain the original markdown format for kept papers.
```

4. **Collect results** from all parallel agents
5. **Combine filtered sections** back into complete digest structure

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

## Step 6: Report Results

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
