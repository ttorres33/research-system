#!/usr/bin/env python3
"""
Split a PDF into separate files per section for agent processing.

Creates temporary section PDFs that can be safely passed to agents without
triggering auto-read of the full document.
"""

import sys
import json
import os
from pathlib import Path
from pypdf import PdfReader, PdfWriter


def split_pdf_by_sections(pdf_path, output_dir):
    """
    Split PDF into section files.

    Args:
        pdf_path: Path to source PDF
        output_dir: Directory to write section PDFs

    Returns:
        List of dicts with section metadata and file paths
    """
    try:
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)

        # Extract section structure
        sections = extract_sections(reader, pdf_path)

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        # Split into section files
        section_files = []
        for i, section in enumerate(sections):
            # Create safe filename
            safe_title = "".join(c for c in section["title"] if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_title = safe_title[:50]  # Limit length
            filename = f"{i:03d}_{safe_title}.pdf"
            output_path = os.path.join(output_dir, filename)

            # Write section pages to new PDF
            writer = PdfWriter()
            for page_num in range(section["start_page"], section["end_page"] + 1):
                if page_num < len(reader.pages):
                    writer.add_page(reader.pages[page_num])

            with open(output_path, 'wb') as f:
                writer.write(f)

            section_files.append({
                "title": section["title"],
                "start_page": section["start_page"],
                "end_page": section["end_page"],
                "file_path": output_path,
                "page_count": section["end_page"] - section["start_page"] + 1
            })

        return {
            "source_pdf": pdf_path,
            "total_pages": total_pages,
            "section_count": len(section_files),
            "output_dir": output_dir,
            "sections": section_files
        }

    except Exception as e:
        return {
            "error": str(e),
            "sections": []
        }


def extract_sections(reader, pdf_path):
    """Extract section structure from PDF."""
    sections = []

    # Try outline first
    if reader.outline:
        sections = extract_from_outline(reader.outline, reader)

    # If no sections found or very few, create page-based chunks
    if len(sections) < 3:
        sections = create_default_chunks(len(reader.pages))

    return sections


def extract_from_outline(outline, reader, parent_page=0):
    """Extract sections from PDF outline/bookmarks."""
    sections = []

    for item in outline:
        if isinstance(item, list):
            sections.extend(extract_from_outline(item, reader, parent_page))
        else:
            try:
                page_num = reader.get_destination_page_number(item)
                title = item.title if hasattr(item, 'title') else str(item)

                sections.append({
                    "title": title,
                    "start_page": page_num,
                    "end_page": None
                })
            except:
                continue

    # Calculate end pages
    for i in range(len(sections) - 1):
        sections[i]["end_page"] = max(sections[i]["start_page"], sections[i + 1]["start_page"] - 1)

    if sections:
        sections[-1]["end_page"] = len(reader.pages) - 1

    # Filter invalid sections
    sections = [s for s in sections if s["end_page"] >= s["start_page"]]

    return sections


def create_default_chunks(total_pages, chunk_size=15):
    """Create default page-based chunks when no structure detected."""
    sections = []

    for start in range(0, total_pages, chunk_size):
        end = min(start + chunk_size - 1, total_pages - 1)
        sections.append({
            "title": f"Pages {start + 1}-{end + 1}",
            "start_page": start,
            "end_page": end
        })

    return sections


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(json.dumps({"error": "Usage: split_pdf_by_sections.py <pdf_path> <output_dir>"}))
        sys.exit(1)

    pdf_path = sys.argv[1]
    output_dir = sys.argv[2]

    result = split_pdf_by_sections(pdf_path, output_dir)
    print(json.dumps(result, indent=2))
