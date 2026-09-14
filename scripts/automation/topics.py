"""Parse keywords.md into topics: name, keywords, and the per-topic settings.

File shape (settings lines are optional and sit between the heading and the keywords):

    ## AI & Productivity
    categories: cs.HC, cs.CY, econ.GN
    mode: claude
    looking for: How professionals adopt and work with AI tools and agents;
      effects on productivity, skills and collaboration. Not model benchmarks.
    - LLM AND "knowledge work"
    - "AI collaboration" AND work

Defaults keep old files working: no categories = all of arXiv, no mode = keywords.
A `looking for` value continues on indented lines. Keys are case-insensitive.
Lines that are neither a heading, a setting nor a `- keyword` are ignored, and a top-level
`# Heading` ends the current topic, so a template's tips section is never read as keywords.

Run as a script to see what the daily run sees:  python3 topics.py path/to/keywords.md
prints the topics as a JSON array (name, keywords, categories, mode, looking_for,
uses_keywords, uses_claude, warnings). The /configure-topics command relies on it.
"""

import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

MODES = ("keywords", "claude", "both")
SETTING_RE = re.compile(r"^(categories|mode|looking[ _-]for)\s*:\s*(.*)$", re.IGNORECASE)
CATEGORY_RE = re.compile(r"^[a-z-]+(\.[A-Za-z-]+)?$")


@dataclass
class Topic:
    name: str
    keywords: list = field(default_factory=list)
    categories: list = field(default_factory=list)   # [] means all of arXiv
    mode: str = "keywords"
    looking_for: str = ""
    warnings: list = field(default_factory=list)      # things worth a log line, not errors

    @property
    def uses_keywords(self):
        return self.mode in ("keywords", "both")

    @property
    def uses_claude(self):
        return self.mode in ("claude", "both")


def parse_topics(text):
    """Return the topics in keywords.md text, in file order."""
    topics = []
    current = None
    continuing = None  # the setting whose value may continue on indented lines
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if stripped.startswith("## "):
            current = Topic(name=stripped[3:].strip())
            topics.append(current)
            continuing = None
            continue
        if stripped.startswith("# "):
            current = None
            continuing = None
            continue
        if current is None or not stripped:
            continuing = None if not stripped else continuing
            continue
        if stripped.startswith("- "):
            current.keywords.append(stripped[2:].strip())
            continuing = None
            continue
        setting = SETTING_RE.match(stripped)
        if setting and not line[0].isspace():
            key = re.sub(r"[ _-]", "_", setting.group(1).lower())
            value = setting.group(2).strip()
            if key == "categories":
                current.categories = [c for c in re.split(r"[,\s]+", value) if c]
                for category in current.categories:
                    if not CATEGORY_RE.match(category):
                        current.warnings.append(f"category {category!r} does not look like an arXiv category code")
                continuing = None
            elif key == "mode":
                mode = value.lower()
                if mode in MODES:
                    current.mode = mode
                else:
                    current.warnings.append(f"mode {value!r} is not one of {', '.join(MODES)}; using keywords")
                continuing = None
            else:
                current.looking_for = value
                continuing = "looking_for"
            continue
        if continuing == "looking_for" and line[0].isspace():
            current.looking_for = f"{current.looking_for} {stripped}".strip()
            continue
        continuing = None
    for topic in topics:
        if topic.uses_keywords and not topic.keywords:
            topic.warnings.append("mode uses keywords but the topic has none; it will match nothing on arXiv")
        if topic.uses_claude and not topic.looking_for:
            topic.warnings.append("mode uses Claude but has no 'looking for' text; the config's filter criteria will be used")
        if not topic.keywords:
            topic.warnings.append("no keywords, so Google Scholar is skipped for this topic")
    return topics


def load_topics(path):
    """Read keywords.md from `path`. Raises FileNotFoundError with the setup hint."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"Keywords file not found at {path}\n"
            f"Please run /setup-research-automation to create keywords file."
        )
    return parse_topics(path.read_text())


def topics_as_json(topics):
    return json.dumps([
        dict(asdict(topic), uses_keywords=topic.uses_keywords, uses_claude=topic.uses_claude) for topic in topics
    ], indent=2)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: topics.py path/to/keywords.md", file=sys.stderr)
        return 2
    try:
        topics = load_topics(argv[0])
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        return 1
    print(topics_as_json(topics))
    return 0


if __name__ == "__main__":
    sys.exit(main())
