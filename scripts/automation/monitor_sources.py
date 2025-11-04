#!/usr/bin/env python3
"""
Monitor all topic folders for new PDFs in Sources/ directories.
Create queue for PDF summarization.
"""

import os
import json
import yaml
from datetime import datetime
from pathlib import Path

def load_config():
    """Load configuration from config.yaml"""
    # Plugin structure: scripts/automation/script.py -> config/config.yaml
    script_dir = Path(__file__).parent
    plugin_dir = script_dir.parent.parent  # Go up two levels to plugin root
    config_path = plugin_dir / "config" / "config.yaml"

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # Validate research_root path
    research_root = Path(config['paths']['research_root']).expanduser().resolve()
    if not research_root.exists():
        raise ValueError(f"research_root does not exist: {research_root}\nPlease check your config.yaml file.")
    if not research_root.is_dir():
        raise ValueError(f"research_root is not a directory: {research_root}\nPlease check your config.yaml file.")

    return config

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

def find_new_pdfs(research_root, processed_files):
    """Find all PDFs in Sources/ folders that haven't been processed

    Returns: list of tuples (pdf_path, has_summary, pdf_id)
    """
    new_pdfs = []

    # Walk through all topic folders
    for topic_dir in research_root.iterdir():
        if not topic_dir.is_dir() or topic_dir.name in ['scripts', 'daily-digests', '.research-data']:
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

def create_queue(queue_file, pdf_paths, research_root):
    """Create queue file with PDF paths relative to research_root"""
    # Convert absolute paths to relative paths
    relative_paths = []
    for pdf_path in pdf_paths:
        try:
            rel_path = pdf_path.relative_to(research_root)
            relative_paths.append(str(rel_path))
        except ValueError:
            # If path is not relative to research_root, use absolute path
            relative_paths.append(str(pdf_path))

    # Write queue file
    queue_file.parent.mkdir(parents=True, exist_ok=True)
    with open(queue_file, 'w') as f:
        json.dump(relative_paths, f, indent=2)

def main():
    # Load configuration
    config = load_config()
    research_root = Path(config['paths']['research_root']).expanduser().resolve()
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

    # Collect PDF paths and mark as processed
    pdf_paths_to_queue = []
    for pdf_path, has_summary, pdf_id in new_pdfs:
        status = "summary exists, will link" if has_summary else "needs summary"
        print(f"  • {pdf_path.name} ({status})")
        pdf_paths_to_queue.append(pdf_path)
        processed_files.add(pdf_id)

    # Create queue file in research data directory
    data_dir = research_root / config['paths']['data']
    queue_file = data_dir / '.research-queue.json'
    create_queue(queue_file, pdf_paths_to_queue, research_root)

    # Save processed files tracking
    save_processed_files(tracking_file, processed_files)

    print(f"\n✓ Created queue with {len(pdf_paths_to_queue)} PDF(s): {queue_file}")

if __name__ == "__main__":
    main()
