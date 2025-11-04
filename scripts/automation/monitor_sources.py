#!/usr/bin/env python3
"""
Monitor all topic folders for new PDFs in Sources/ directories.
Create tasks for papers that need summaries.
"""

import os
import json
import yaml
from datetime import datetime, timedelta
from pathlib import Path
import hashlib

def load_config():
    """Load configuration from config.yaml"""
    script_dir = Path(__file__).parent
    config_path = script_dir / "config.yaml"

    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def get_processed_files(tracking_file):
    """Load list of already processed files"""
    if tracking_file.exists():
        with open(tracking_file, 'r') as f:
            return set(json.load(f))
    return set()

def save_processed_files(tracking_file, processed):
    """Save list of processed files"""
    with open(tracking_file, 'w') as f:
        json.dump(list(processed), f, indent=2)

def sanitize_filename(name):
    """Convert paper title/filename to valid task filename"""
    # Remove extension and path
    name = Path(name).stem
    # Convert to lowercase and replace spaces/special chars with hyphens
    name = name.lower()
    name = ''.join(c if c.isalnum() else '-' for c in name)
    # Remove multiple consecutive hyphens
    while '--' in name:
        name = name.replace('--', '-')
    return name.strip('-')

def create_task_file(pdf_path, tasks_dir, research_root, summary_exists=False):
    """Create a task file for a new PDF"""
    # Get relative path from research root
    rel_path = pdf_path.relative_to(research_root)

    # Extract paper title from filename
    paper_title = pdf_path.stem.replace('-', ' ').replace('_', ' ').title()

    # Create task filename
    task_filename = f"review-research-{sanitize_filename(pdf_path.name)}.md"
    task_path = tasks_dir / task_filename

    # Set due date to today
    today = datetime.now().strftime('%Y-%m-%d')

    # Create task content based on whether summary exists
    if summary_exists:
        # Summary already exists - create review task
        # Get path to summary in Notes folder
        topic_dir = pdf_path.parent.parent  # Go up from Sources/ to topic folder
        summary_rel_path = topic_dir / 'Notes' / f"{pdf_path.stem}.md"
        summary_rel = summary_rel_path.relative_to(research_root)

        # For unified vault: use Research/ prefix and remove .md extension
        summary_link = f"Research/{summary_rel}".replace('.md', '')
        source_link = f"Research/{rel_path}"

        content = f"""---
type: task
due: {today}
tags: [research-review]
source_path: "{rel_path}"
summary_path: "{summary_rel}"
---
# Review Research: {paper_title}

Summary already exists. Review and integrate insights.

Summary: [[{summary_link}]]
Source: [[{source_link}]]
"""
    else:
        # No summary - create summary-needed task
        # For unified vault: use Research/ prefix
        source_link = f"Research/{rel_path}"

        content = f"""---
type: task
due: {today}
tags: [research-summary-needed]
source_path: "{rel_path}"
---
# Review Research: {paper_title}

New research paper detected and ready for summary generation.

Source: [[{source_link}]]
"""

    # Write task file
    with open(task_path, 'w') as f:
        f.write(content)

    return task_path

def find_new_pdfs(research_root, processed_files):
    """Find all PDFs in Sources/ folders that haven't been processed

    Returns: list of tuples (pdf_path, has_summary, pdf_id)
    """
    new_pdfs = []

    # Walk through all topic folders
    for topic_dir in research_root.iterdir():
        if not topic_dir.is_dir() or topic_dir.name in ['scripts', 'daily-digests']:
            continue

        sources_dir = topic_dir / 'Sources'
        notes_dir = topic_dir / 'Notes'

        if not sources_dir.exists():
            continue

        # Find PDFs in Sources folder
        for pdf_file in sources_dir.glob('*.pdf'):
            # Use absolute path as identifier
            pdf_id = str(pdf_file.absolute())

            if pdf_id not in processed_files:
                # Check if summary already exists in Notes/ folder
                summary_file = notes_dir / f"{pdf_file.stem}.md"
                has_summary = summary_file.exists()

                # Add to new PDFs list with summary status AND pdf_id
                new_pdfs.append((pdf_file, has_summary, pdf_id))

    return new_pdfs

def update_queue(queue_file, task_files):
    """Update the research queue file for /today command"""
    # Convert task paths to relative paths from Tasks directory
    tasks_dir = Path("/Users/ttorres/Library/CloudStorage/Dropbox/Consulting/Notes/Tasks")
    queue = [str(task.relative_to(tasks_dir.parent)) for task in task_files]

    with open(queue_file, 'w') as f:
        json.dump(queue, f, indent=2)

def main():
    # Load configuration
    config = load_config()
    research_root = Path(config['paths']['research_root'])
    script_dir = Path(__file__).parent

    # Setup tracking
    tracking_file = script_dir / '.processed_pdfs.json'
    processed_files = get_processed_files(tracking_file)

    # Find new PDFs
    new_pdfs = find_new_pdfs(research_root, processed_files)

    if not new_pdfs:
        print("No new PDFs found.")
        return

    print(f"Found {len(new_pdfs)} new PDF(s):")

    # Create task files
    tasks_dir = Path("/Users/ttorres/Library/CloudStorage/Dropbox/Consulting/Notes/Tasks/tasks")
    tasks_dir.mkdir(parents=True, exist_ok=True)

    task_files = []
    for pdf, has_summary, pdf_id in new_pdfs:
        task_path = create_task_file(pdf, tasks_dir, research_root, summary_exists=has_summary)
        task_files.append(task_path)
        status = "review" if has_summary else "needs summary"
        print(f"  • {pdf.name} → {task_path.name} ({status})")
        # Only mark as processed after successful task creation
        processed_files.add(pdf_id)

    # Update queue file for /today
    queue_file = Path("/Users/ttorres/Library/CloudStorage/Dropbox/Consulting/Notes/Tasks") / config['paths']['scripts'] / config['paths']['queue_file']
    queue_file.parent.mkdir(parents=True, exist_ok=True)
    update_queue(queue_file, task_files)

    # Save processed files (now only after successful task creation)
    save_processed_files(tracking_file, processed_files)

    print(f"\n✓ Created {len(task_files)} task(s) and updated research queue")

if __name__ == "__main__":
    main()
