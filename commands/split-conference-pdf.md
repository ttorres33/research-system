---
name: split-conference-pdf
description: Split a conference proceedings PDF into individual papers based on table of contents
allowed-tools: [Read, Bash]
model: haiku
---

# Split Conference PDF Command

Split a conference proceedings PDF into individual paper PDFs based on the embedded table of contents.

## Usage

This command is useful when you download conference proceedings and want to extract specific papers to add to your research workflow.

## Steps

### 1. Get Input Parameters

1. **Prompt for PDF path** if not provided in command arguments:
   - Ask: "Please provide the path to the conference proceedings PDF"
   - Verify the file exists and is a PDF

2. **Prompt for output directory** (optional):
   - Ask: "Where should the individual papers be saved? (default: same directory as PDF)"
   - Default: Same directory as the source PDF
   - Create directory if it doesn't exist

### 2. Run Split Script

1. **Run the split script:**
   - Run: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/utilities/split_conference_pdf.py "$pdf_path" "$output_dir"`
   - The script will:
     - Extract TOC from PDF metadata/bookmarks
     - Identify individual papers based on TOC structure
     - Create separate PDF files for each paper
     - Name files: `01_Paper_Title.pdf`, `02_Paper_Title.pdf`, etc.

3. **Capture output:**
   - Script will show:
     - Number of papers found
     - Title and page range of each paper
     - Created file names
   - Display this output to user

### 3. Report Results

1. **Show summary:**
   - "✓ Split {N} papers from proceedings"
   - "Output directory: {output_dir}"

2. **List created files:**
   - Show each paper file name and title

3. **Provide next steps:**
   - "To add papers to your research workflow:"
   - "  1. Review the extracted papers in: {output_dir}"
   - "  2. Copy desired papers to your Research/Topic/Sources/ folders"
   - "  3. Run monitor_sources.py or wait for cron job to queue them"
   - "  4. Run /generate-research-digest to create summaries"

## Error Handling

- **PDF not found**: Show error with provided path
- **No TOC found**: Script will exit with message:
  - "Could not extract TOC automatically. You may need to manually specify page ranges."
  - Suggest user manually extract papers using Preview/Adobe
- **Malformed PDF**: Show error from script with suggestion to check PDF format
- **Permission errors**: Show clear error with directory path
- **Output directory creation fails**: Show error and suggest checking parent directory permissions

## Example Usage

```bash
# Command invocation
/split-conference-pdf ~/Downloads/CHI-2024-Proceedings.pdf

# Output:
# Processing: ~/Downloads/CHI-2024-Proceedings.pdf
# Output directory: ~/Downloads/split_papers
#
# Extracted 15 TOC entries
# Total pages: 250
#
# Found 12 papers:
# 1. Understanding User Behavior in AI Systems (pages 1-20)
# 2. Novel Interaction Techniques for AR (pages 21-42)
# ...
#
# Created: 01_Understanding_User_Behavior_in_AI_Systems.pdf
# Created: 02_Novel_Interaction_Techniques_for_AR.pdf
# ...
#
# ✓ Split 12 papers from proceedings
# Output directory: ~/Downloads/split_papers
#
# To add papers to your research workflow:
#   1. Review the extracted papers in: ~/Downloads/split_papers
#   2. Copy desired papers to your Research/Topic/Sources/ folders
#   3. Run monitor_sources.py or wait for cron job to queue them
#   4. Run /generate-research-digest to create summaries
```

## Notes

- This command requires the proceedings PDF to have embedded TOC/bookmarks
- Works best with well-structured proceedings from major publishers
- Individual papers maintain original PDF quality and formatting
- Papers are named using TOC entry titles (sanitized for filenames)
- This is a manual preprocessing step - papers don't automatically enter the queue
- You control which papers to keep by selectively copying to Sources/ folders
