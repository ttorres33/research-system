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

### 3. Check PDF Size and Conditionally Split

1. **Find plugin directory:**
   - Search for `.claude-plugin/plugin.json` in parent directories
   - Store as `plugin_dir`

2. **Get file size:**
   - Run: `stat -f%z "$pdf_path"`
   - Store size in bytes

3. **Decide processing strategy:**
   - If size ≥ 5242880 bytes (5 MB):
     - Generate unique timestamp: `date +%s`
     - Create temp directory: `/tmp/research-sections-{timestamp}`
     - Run: `python3 {plugin_dir}/scripts/utilities/split_pdf_by_sections.py "$pdf_path" "/tmp/research-sections-{timestamp}"`
     - This splits PDF into section files (000_Introduction.pdf, 001_Methods.pdf, etc.)
     - Set `input_type = "section_dir"` and `input_path = "/tmp/research-sections-{timestamp}"`
     - Inform user: "Large PDF detected ({size} MB). Splitting into sections for processing..."
   - Else (small PDF < 5 MB):
     - Set `input_type = "pdf"` and `input_path = pdf_path`
     - Inform user: "Processing PDF..."

### 4. Generate Summary

1. **Spawn research-summarizer agent:**
   - Use Task tool with subagent_type="research-system:research-summarizer"
   - Pass the appropriate input:
     - If `input_type` is "section_dir": Include section directory path in prompt
     - If `input_type` is "pdf": Include PDF path in prompt
   - Include output path (Notes/ folder location)

2. **Wait for completion:**
   - Agent will read PDF or section files
   - Generate structured summary with bullets
   - Write to Notes/ folder

### 5. Cleanup Temporary Files

1. If section directory was created:
   - Run: `rm -rf "/tmp/research-sections-{timestamp}"`
   - Inform user: "Cleaned up temporary section files"

### 6. Report Results

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
