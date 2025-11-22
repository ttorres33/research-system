---
name: research-summary
description: Generate a summary for a single PDF research paper
allowed-tools: [Read, Write, Bash, Task]
---

# Research Summary Command

Generate a summary for a single PDF research paper, with intelligent handling of large PDFs.

## Usage

This command takes a PDF path and generates a summary in the appropriate Notes/ folder, automatically handling large PDFs by splitting them into sections.

## Steps

### 1. Get PDF Path

1. **Prompt user for PDF path** if not provided in command arguments
2. Verify the file exists and is a PDF
3. Extract the parent directory structure to determine topic and paths
   - Example: `~/Research/AI & Productivity/Sources/paper.pdf`
   - Topic: `AI & Productivity`
   - Notes path: `~/Research/AI & Productivity/Notes/paper.md`

### 2. Check if Summary Already Exists

1. Determine summary path: same as PDF but in `Notes/` folder instead of `Sources/` and `.md` extension
2. If summary already exists:
   - Ask user if they want to regenerate it
   - If no, exit with message showing existing summary path
   - If yes, continue (will overwrite)

### 3. Check PDF Size and Split Large PDFs

1. **Set plugin directory:**
   - `plugin_dir = ~/.claude/plugins/cache/research-system`

2. **Get file size:**
   - Run: `stat -f%z "$pdf_path"`
   - Store size in bytes

3. **Split if needed:**
   - If size ≥ 5242880 bytes (5 MB):
     - Generate unique timestamp: `date +%s`
     - Create temp directory: `/tmp/research-sections-$timestamp`
     - Run: `python3 $plugin_dir/scripts/utilities/split_pdf_by_sections.py "$pdf_path" "/tmp/research-sections-$timestamp"`
     - This splits PDF into section files (000_Introduction.pdf, 001_Methods.pdf, etc.)
     - Set `sections_dir = "/tmp/research-sections-{timestamp}"`
     - Inform user: "Large PDF detected ({size} MB). Splitting into sections for processing..."
   - Else (small PDF < 5 MB):
     - Set `sections_dir = null` (not needed)
     - Inform user: "Processing PDF..."

### 4. Extract Paper Metadata

**For large PDFs (sections_dir is set):**
1. List section files in the temp directory, sorted numerically
2. Read the first section PDF (000_*.pdf) to extract:
   - Paper title (usually in header/title block on first page)
   - Publication date (if available)
3. Store metadata for use in final summary

**For small PDFs (sections_dir is null):**
1. Read first 2 pages of PDF to extract:
   - Paper title
   - Publication date (if available)
2. Store metadata for use in final summary

### 5. Generate Summary

**For large PDFs (sections_dir is set):**
1. List all section PDF files in `sections_dir`, sorted numerically
2. Create temp summaries directory: `/tmp/research-summaries-{timestamp}`
3. For each section PDF, spawn a research-summarizer agent IN PARALLEL:
   - Use Task tool with subagent_type="research-system:research-summarizer"
   - Pass section PDF path: `{sections_dir}/00X_SectionName.pdf`
   - Pass output path: `/tmp/research-summaries-{timestamp}/00X_SectionName.md`
4. Wait for all agents to complete
5. Aggregate section summaries:
   - Extract tags from all section summary files (read only frontmatter):
     ```bash
     grep "^tags:" /tmp/research-summaries-{timestamp}/*.md
     ```
   - Combine and deduplicate tags, keep top 5-10 most relevant
   - Create final summary at Notes/ folder location:
     ```markdown
     ---
     tags: [aggregated, deduplicated, tags]
     ---

     # Paper Title (from metadata)

     Publication Date: [if found in metadata]

     ```
   - Append all section summaries (strip their frontmatter):
     ```bash
     for file in /tmp/research-summaries-{timestamp}/*.md; do
       sed '1,/^---$/d; 1,/^---$/d' "$file" >> "$output_path"
     done
     ```
6. Cleanup temp summaries: `rm -rf "/tmp/research-summaries-{timestamp}"`

**For small PDFs (sections_dir is null):**
1. Create temp file: `/tmp/research-summary-{timestamp}.md`
2. Spawn single research-summarizer agent:
   - Use Task tool with subagent_type="research-system:research-summarizer"
   - Pass PDF path
   - Pass temp output path: `/tmp/research-summary-{timestamp}.md`
3. Wait for agent to complete
4. Extract tags from agent's summary (read only frontmatter)
5. Create final summary at Notes/ folder location:
   - Write frontmatter with tags from agent
   - Add paper title as `# Title` (from metadata)
   - Add publication date (from metadata)
   - Append agent's summary content (strip frontmatter):
     ```bash
     sed '1,/^---$/d; 1,/^---$/d' /tmp/research-summary-{timestamp}.md >> "$output_path"
     ```
6. Cleanup temp file: `rm "/tmp/research-summary-{timestamp}.md"`

### 6. Cleanup Temporary Files

1. If section directory was created (large PDF):
   - Run: `rm -rf "/tmp/research-sections-{timestamp}"`
   - Inform user: "Cleaned up temporary section files"

### 7. Report Results

Inform user:
- "✓ Summary generated successfully"
- "Location: {summary_path}"
- Show link to summary file

## Error Handling

- **PDF not found**: Show clear error with provided path
- **PDF is not readable**: Show error suggesting permissions check
- **Split script fails**: Show error output from script, suggest checking PDF format
- **Agent fails**: Show agent error, suggest retrying or checking PDF content
- **Permission errors**: Show clear error with file path

## Example Usage

```bash
# Command invocation
/research-summary ~/Research/AI & Productivity/Sources/large-paper.pdf

# Output:
# Large PDF detected (8.2 MB). Splitting into sections for processing...
# Generating summary using research-summarizer agent...
# Cleaned up temporary section files
# ✓ Summary generated successfully
# Location: ~/Research/AI & Productivity/Notes/large-paper.md
```

## Notes

- This command is useful for immediate one-off summarization outside the queue workflow
- Large PDFs (≥5 MB) are automatically split into sections to avoid context overflow
- The same research-summarizer agent is used as in the automated digest workflow
- Temporary section files are always cleaned up after processing
