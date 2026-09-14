"""Tests for scripts/automation/topics.py."""

import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from tests.support import fixture  # noqa: F401  (puts scripts/automation on sys.path)

import topics as tp

OLD_STYLE = """# Research Keywords

## AI & Productivity
- LLM AND "knowledge work"
- "generative AI" AND workplace

## Synthetic Users & Discovery
- "synthetic users"
"""

NEW_STYLE = """# Research Keywords

## AI & Productivity
categories: cs.HC, cs.CY econ.GN
mode: claude
looking for: How professionals adopt and work with AI tools;
  effects on productivity and skills.
  Not model benchmarks.
- LLM AND "knowledge work"

## Decision Making
Mode: Both
Categories: cs.HC
Looking-For: decisions in product teams
- "decision making" AND expertise

## Teams
mode: keywords
- "psychological safety" AND teams

## Empty Claude Topic
mode: claude
categories: cs.CY

# Tips for Effective Keywords
- **Use AND** to require multiple terms
"""


class ParseTopicsTests(unittest.TestCase):
    def test_old_style_file_keeps_its_meaning(self):
        result = tp.parse_topics(OLD_STYLE)
        self.assertEqual([t.name for t in result], ["AI & Productivity", "Synthetic Users & Discovery"])
        self.assertEqual(result[0].keywords, ['LLM AND "knowledge work"', '"generative AI" AND workplace'])
        self.assertEqual(result[0].categories, [])
        self.assertEqual(result[0].mode, "keywords")
        self.assertTrue(result[0].uses_keywords)
        self.assertFalse(result[0].uses_claude)
        self.assertEqual(result[0].warnings, [])

    def test_settings_and_continuation_lines(self):
        first = tp.parse_topics(NEW_STYLE)[0]
        self.assertEqual(first.categories, ["cs.HC", "cs.CY", "econ.GN"], "commas or spaces both separate")
        self.assertEqual(first.mode, "claude")
        self.assertEqual(
            first.looking_for,
            "How professionals adopt and work with AI tools; effects on productivity and skills. Not model benchmarks.",
        )
        self.assertEqual(first.keywords, ['LLM AND "knowledge work"'])
        self.assertTrue(first.uses_claude)
        self.assertFalse(first.uses_keywords)

    def test_keys_are_case_insensitive_and_accept_hyphen_or_underscore(self):
        second = tp.parse_topics(NEW_STYLE)[1]
        self.assertEqual(second.mode, "both")
        self.assertEqual(second.categories, ["cs.HC"])
        self.assertEqual(second.looking_for, "decisions in product teams")
        self.assertTrue(second.uses_keywords and second.uses_claude)

    def test_top_level_heading_ends_the_topic(self):
        result = tp.parse_topics(NEW_STYLE)
        self.assertEqual(result[-1].name, "Empty Claude Topic")
        self.assertEqual(result[-1].keywords, [], "the tips list under '# Tips' is not read as keywords")

    def test_warnings(self):
        result = tp.parse_topics(NEW_STYLE)
        empty = result[-1]
        self.assertIn("no 'looking for' text", " ".join(empty.warnings))
        self.assertIn("Google Scholar is skipped", " ".join(empty.warnings))
        self.assertEqual(result[2].warnings, [])
        bad = tp.parse_topics("## T\nmode: magic\ncategories: cs.HC, nonsense!\n- x\n")[0]
        self.assertEqual(bad.mode, "keywords")
        self.assertTrue(any("magic" in w for w in bad.warnings))
        self.assertTrue(any("nonsense!" in w for w in bad.warnings))
        keywordless = tp.parse_topics("## T\nmode: keywords\n")[0]
        self.assertTrue(any("match nothing" in w for w in keywordless.warnings))

    def test_load_topics_reads_a_file_and_reports_a_missing_one(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "keywords.md"
            path.write_text(OLD_STYLE)
            self.assertEqual(len(tp.load_topics(path)), 2)
            with self.assertRaises(FileNotFoundError) as ctx:
                tp.load_topics(Path(tmp) / "missing.md")
            self.assertIn("/setup-research-automation", str(ctx.exception))


class CommandLineTests(unittest.TestCase):
    def test_prints_topics_as_json(self):
        import json
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "keywords.md"
            path.write_text(NEW_STYLE)
            out = io.StringIO()
            with redirect_stdout(out):
                code = tp.main([str(path)])
            self.assertEqual(code, 0)
            data = json.loads(out.getvalue())
            self.assertEqual([t["name"] for t in data][:2], ["AI & Productivity", "Decision Making"])
            self.assertEqual(data[0]["mode"], "claude")
            self.assertEqual(data[0]["categories"], ["cs.HC", "cs.CY", "econ.GN"])
            self.assertTrue(data[0]["uses_claude"] and not data[0]["uses_keywords"])
            self.assertIn("Google Scholar is skipped", " ".join(data[-1]["warnings"]))

    def test_missing_file_and_bad_usage(self):
        err = io.StringIO()
        with redirect_stderr(err):
            self.assertEqual(tp.main(["/nonexistent/keywords.md"]), 1)
            self.assertEqual(tp.main([]), 2)
        self.assertIn("/setup-research-automation", err.getvalue())
        self.assertIn("usage:", err.getvalue())


if __name__ == "__main__":
    unittest.main()
