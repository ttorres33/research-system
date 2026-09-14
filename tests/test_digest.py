"""Tests for scripts/automation/digest.py."""

import unittest

from tests.support import fixture  # noqa: F401  (puts scripts/automation on sys.path)

import arxiv_harvest as ah
import digest as dg

ARXIV = {"title": "T", "authors": "A, B", "year": 2026, "abstract": "x" * 310,
         "url": "http://arxiv.org/abs/2609.00001v1", "pdf_url": "https://arxiv.org/pdf/2609.00001v1", "source": "arXiv"}
SCHOLAR = {"title": "S", "authors": "C", "year": "2025", "snippet": "snip", "url": "https://example.org/s",
           "citations": 4, "source": "Google Scholar"}


class RenderPaperTests(unittest.TestCase):
    def test_arxiv_entry_truncates_abstract_and_links_pdf(self):
        text = dg.render_paper(ARXIV)
        self.assertIn("### T\n", text)
        self.assertIn("**Authors:** A, B  \n", text)
        self.assertIn("**Year:** 2026  \n", text)
        self.assertIn("**Abstract:** " + "x" * 300 + "...\n", text)
        self.assertIn("[View Paper](http://arxiv.org/abs/2609.00001v1) | [PDF](https://arxiv.org/pdf/2609.00001v1)\n", text)
        self.assertTrue(text.endswith("\n---\n"))
        self.assertNotIn("**Why:**", text)

    def test_scholar_entry_shows_citations_and_snippet(self):
        text = dg.render_paper(SCHOLAR)
        self.assertIn("**Year:** 2025 | **Citations:** 4  \n", text)
        self.assertIn("**Snippet:** snip\n", text)
        self.assertIn("[View Paper](https://example.org/s)\n", text)
        self.assertNotIn("[PDF]", text)

    def test_why_line_sits_after_the_abstract(self):
        text = dg.render_paper(dict(ARXIV, abstract="short", why="matches the brief"))
        self.assertIn("**Abstract:** short\n**Why:** matches the brief\n", text)

    def test_paper_entry_from_harvest_paper(self):
        paper = ah.parse_page(fixture("arxiv_raw_page2.xml"))[0][0]
        entry = dg.paper_entry(paper, why="w")
        self.assertEqual(entry["url"], "http://arxiv.org/abs/2609.13136v1")
        self.assertEqual(entry["year"], 2026)
        self.assertEqual(entry["source"], "arXiv")
        self.assertEqual(entry["why"], "w")
        self.assertNotIn("why", dg.paper_entry(paper))


class RenderDigestTests(unittest.TestCase):
    def test_sections_notes_pending_and_empty_topics(self):
        sections = [
            dg.TopicSection("Keyword Topic", [ARXIV]),
            dg.TopicSection("Claude Topic", [], pending=12),
            dg.TopicSection("Quiet Topic"),
            dg.TopicSection("Sunday Topic", [], 0, ["Google Scholar skipped for this topic: no keywords"]),
        ]
        text = dg.render_digest(sections, "2026-09-15", note="careful")
        self.assertTrue(text.startswith("# Research Digest - 2026-09-15\n\n> **Note:** careful\n"))
        self.assertIn("\n## Keyword Topic\n\n### T\n", text)
        self.assertIn("\n## Claude Topic\n\n_12 papers await Claude review. Run /generate-research-digest._\n", text)
        self.assertNotIn("Quiet Topic", text)
        self.assertIn("\n## Sunday Topic\n\n_Google Scholar skipped for this topic: no keywords_\n", text)
        self.assertNotIn("No papers today", text)

    def test_empty_message_only_when_nothing_to_show(self):
        text = dg.render_digest([dg.TopicSection("A")], "2026-09-15", empty_message="Nothing matched.")
        self.assertIn("**No papers today.** Nothing matched.\n", text)
        text = dg.render_digest([dg.TopicSection("A", pending=1)], "2026-09-15", empty_message="Nothing matched.")
        self.assertNotIn("No papers today", text)
        self.assertIn("_1 paper awaits Claude review.", text)

    def test_replace_pending_touches_only_the_named_section(self):
        sections = [dg.TopicSection("A", pending=2), dg.TopicSection("B", pending=3)]
        text = dg.render_digest(sections, "2026-09-15")
        new_text, replaced = dg.replace_pending(text, "B", "REPLACED")
        self.assertTrue(replaced)
        self.assertIn("\n## A\n\n_2 papers await Claude review. Run /generate-research-digest._\n", new_text)
        self.assertIn("\n## B\n\nREPLACED\n", new_text)
        self.assertEqual(dg.replace_pending(new_text, "B", "AGAIN"), (new_text, False), "nothing pending any more")
        self.assertEqual(dg.replace_pending(text, "Missing", "X"), (text, False))


if __name__ == "__main__":
    unittest.main()
