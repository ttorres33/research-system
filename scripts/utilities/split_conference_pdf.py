#!/usr/bin/env python3
"""
Split a conference proceedings PDF into individual papers based on TOC.
"""

import sys
from pathlib import Path
try:
    from pypdf import PdfReader, PdfWriter
except ImportError:
    print("pypdf not installed. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pypdf"])
    from pypdf import PdfReader, PdfWriter

def extract_toc_from_pdf(pdf_path):
    """Extract table of contents with page numbers from PDF metadata"""
    with open(pdf_path, 'rb') as file:
        reader = PdfReader(file)

        # Try to get outline/bookmarks (TOC)
        try:
            outlines = reader.outline
        except Exception as e:
            print(f"Error reading PDF outline: {e}")
            print("PDF may have malformed bookmarks.")
            return None

        if not outlines:
            print("No table of contents found in PDF metadata.")
            return None

        toc_entries = []

        def process_outline(items, level=0):
            """Recursively process outline items"""
            for item in items:
                if isinstance(item, list):
                    # Nested items
                    process_outline(item, level + 1)
                else:
                    # Single item
                    try:
                        title = item.title if hasattr(item, 'title') else str(item)
                        # Get page number
                        if hasattr(item, 'page'):
                            page_obj = item.page
                            if page_obj is not None:
                                try:
                                    page_num = reader.pages.index(page_obj) + 1  # +1 for 1-based indexing
                                    toc_entries.append({
                                        'title': title,
                                        'page': page_num,
                                        'level': level
                                    })
                                except ValueError:
                                    # Page not found in reader.pages
                                    pass
                    except Exception as e:
                        print(f"Warning: Could not process outline item: {e}")

        try:
            process_outline(outlines)
        except Exception as e:
            print(f"Error processing outlines: {e}")
            return None

        return toc_entries, len(reader.pages)

def split_pdf_by_toc(pdf_path, output_dir, toc_entries, total_pages):
    """Split PDF based on TOC entries"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Group entries by top-level (assume level 0 or 1 are individual papers)
    papers = []
    for i, entry in enumerate(toc_entries):
        if entry['level'] <= 1:  # Top-level entries are papers
            start_page = entry['page']
            # End page is the start of next paper (or end of document)
            if i + 1 < len(toc_entries):
                # Find next paper at same or higher level
                end_page = None
                for next_entry in toc_entries[i+1:]:
                    if next_entry['level'] <= entry['level']:
                        end_page = next_entry['page'] - 1
                        break
                if end_page is None:
                    end_page = total_pages
            else:
                end_page = total_pages

            papers.append({
                'title': entry['title'],
                'start': start_page,
                'end': end_page
            })

    print(f"\nFound {len(papers)} papers:")
    for i, paper in enumerate(papers, 1):
        print(f"{i}. {paper['title']} (pages {paper['start']}-{paper['end']})")

    # Split the PDF
    with open(pdf_path, 'rb') as file:
        reader = PdfReader(file)

        for i, paper in enumerate(papers, 1):
            writer = PdfWriter()

            # Add pages to writer (convert to 0-based indexing)
            for page_num in range(paper['start'] - 1, paper['end']):
                if page_num < len(reader.pages):
                    writer.add_page(reader.pages[page_num])

            # Sanitize filename
            safe_title = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in paper['title'])
            safe_title = safe_title[:100]  # Limit length
            output_path = output_dir / f"{i:02d}_{safe_title}.pdf"

            with open(output_path, 'wb') as output_file:
                writer.write(output_file)

            print(f"Created: {output_path.name}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python split_conference_pdf.py <pdf_path> [output_dir]")
        sys.exit(1)

    pdf_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "split_papers"

    print(f"Processing: {pdf_path}")
    print(f"Output directory: {output_dir}")

    # Extract TOC
    result = extract_toc_from_pdf(pdf_path)
    if result is None:
        print("\nCould not extract TOC automatically.")
        print("You may need to manually specify page ranges.")
        sys.exit(1)

    toc_entries, total_pages = result
    print(f"\nExtracted {len(toc_entries)} TOC entries")
    print(f"Total pages: {total_pages}")

    # Split PDF
    split_pdf_by_toc(pdf_path, output_dir, toc_entries, total_pages)

    print(f"\n✓ Done! Papers saved to: {output_dir}")

if __name__ == "__main__":
    main()
