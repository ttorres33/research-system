"""Render the daily digest markdown.

One renderer for every paper block, whether it comes from the cron run (arXiv keyword
matches, Google Scholar results) or from the Claude review that runs later in
/generate-research-digest. The review replaces a topic's "await Claude review" line
with rendered papers, so both paths must produce the same shape.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

ABSTRACT_LIMIT = 300
PENDING_RE = re.compile(r"^_(\d+) papers? awaits? Claude review\. Run /generate-research-digest\._$", re.MULTILINE)


@dataclass
class TopicSection:
    name: str
    entries: list = field(default_factory=list)   # paper dicts, see paper_entry()
    pending: int = 0                               # papers waiting for the Claude review
    notes: list = field(default_factory=list)      # one-line notes under the heading


def paper_entry(paper, why=None):
    """The digest's paper dict for an arxiv_harvest.Paper."""
    entry = {
        "title": paper.title,
        "authors": paper.authors,
        "year": paper.year,
        "abstract": paper.abstract,
        "url": paper.url,
        "pdf_url": paper.pdf_url,
        "source": "arXiv",
    }
    if why:
        entry["why"] = why
    return entry


def render_paper(entry):
    """Markdown for one paper. `entry` has title, authors, year, url, and abstract or snippet;
    optional pdf_url, citations (Scholar), source, why (Claude review reason)."""
    lines = [f"\n### {entry['title']}\n", f"**Authors:** {entry['authors']}  \n", f"**Year:** {entry['year']}"]
    if entry.get("source") == "Google Scholar" and entry.get("citations"):
        lines.append(f" | **Citations:** {entry['citations']}")
    lines.append("  \n")
    if "abstract" in entry:
        abstract = entry["abstract"]
        if len(abstract) > ABSTRACT_LIMIT:
            abstract = abstract[:ABSTRACT_LIMIT] + "..."
        lines.append(f"**Abstract:** {abstract}\n")
    elif "snippet" in entry:
        lines.append(f"**Snippet:** {entry['snippet']}\n")
    if entry.get("why"):
        lines.append(f"**Why:** {entry['why']}\n")
    links = [f"[View Paper]({entry['url']})"]
    if entry.get("pdf_url"):
        links.append(f"[PDF]({entry['pdf_url']})")
    lines.append(" | ".join(links) + "\n")
    lines.append("\n---\n")
    return "".join(lines)


def pending_line(count):
    verb = "awaits" if count == 1 else "await"
    noun = "paper" if count == 1 else "papers"
    return f"_{count} {noun} {verb} Claude review. Run /generate-research-digest._"


def render_digest(sections, today, note=None, empty_message=None):
    """The whole digest as text. Topics with nothing to show are left out."""
    content = [f"# Research Digest - {today}\n"]
    if note:
        content.append(f"\n> **Note:** {note}\n")
    shown = [s for s in sections if s.entries or s.pending or s.notes]
    if not any(s.entries or s.pending for s in sections) and empty_message:
        content.append(f"\n**No papers today.** {empty_message}\n")
    for section in shown:
        content.append(f"\n## {section.name}\n")
        for line in section.notes:
            content.append(f"\n_{line}_\n")
        if section.pending:
            content.append(f"\n{pending_line(section.pending)}\n")
        for entry in section.entries:
            content.append(render_paper(entry))
    return "".join(content)


def write_digest(sections, output_path, note=None, empty_message=None, today=None):
    """Write the digest; return the number of paper entries written."""
    today = today or datetime.now().strftime("%Y-%m-%d")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(render_digest(sections, today, note=note, empty_message=empty_message))
    return sum(len(s.entries) for s in sections)


def has_content(path):
    """True when a digest file at `path` holds papers or a pending Claude review."""
    path = Path(path)
    if not path.exists():
        return False
    text = path.read_text()
    return "\n### " in text or PENDING_RE.search(text) is not None


def replace_pending(text, topic_name, replacement):
    """Replace the pending line under `## topic_name` with `replacement`.

    Returns (new_text, True) when a pending line was found in that section, else
    (text, False). Only the named topic's section, up to the next `## ` heading, is touched.
    """
    heading = f"\n## {topic_name}\n"
    start = text.find(heading)
    if start < 0:
        return text, False
    body_start = start + len(heading)
    next_heading = text.find("\n## ", body_start)
    end = len(text) if next_heading < 0 else next_heading
    section = text[body_start:end]
    match = PENDING_RE.search(section)
    if not match:
        return text, False
    section = section[:match.start()] + replacement + section[match.end():]
    return text[:body_start] + section + text[end:], True
