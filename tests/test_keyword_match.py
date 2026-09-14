"""Tests for scripts/automation/keyword_match.py."""

import unittest

from tests.support import fixture  # noqa: F401  (puts scripts/automation on sys.path)

import keyword_match as km

PAPER = {
    "title": "AI-assisted analysis of customer interviews",
    "abstract": "We use an LLM to synthesize customer interview transcripts. Workers benefit; managers do not.",
}


def hit(query, paper=PAPER):
    return km.parse(query).matches(paper)


class MatchingTests(unittest.TestCase):
    def test_phrase_and_grouped_or(self):
        self.assertTrue(hit('"customer interview" AND (LLM OR AI)'))
        self.assertFalse(hit('"customer interviews" AND GPT'))

    def test_whole_words_only(self):
        self.assertTrue(hit("interview"), "singular appears in the abstract")
        self.assertTrue(hit("interviews"), "plural appears in the title")
        self.assertFalse(hit("interviewer"))
        self.assertFalse(hit("view"), "no substring matching")
        self.assertFalse(hit("worker"), "no stemming: 'workers' is not 'worker'")

    def test_case_insensitive(self):
        self.assertTrue(hit("llm AND CUSTOMER"))

    def test_hyphens_split_on_both_sides(self):
        self.assertTrue(hit('"AI-assisted analysis"'))
        self.assertTrue(hit('"AI assisted analysis"'))
        self.assertTrue(hit('"ai assisted"'))

    def test_phrase_needs_adjacent_words(self):
        self.assertTrue(hit('"customer interview transcripts"'))
        self.assertFalse(hit('"customer transcripts"'))

    def test_implicit_and_between_adjacent_terms(self):
        self.assertTrue(hit("customer interview LLM"))
        self.assertFalse(hit("customer interview GPT"))

    def test_andnot_and_not_synonym(self):
        self.assertFalse(hit("customer ANDNOT managers"))
        self.assertFalse(hit("customer NOT managers"))
        self.assertTrue(hit("customer ANDNOT executives"))

    def test_precedence_and_binds_tighter_than_or(self):
        self.assertTrue(hit("GPT AND banana OR customer"))
        self.assertEqual(str(km.parse("GPT AND banana OR customer")), "((GPT AND banana) OR customer)")

    def test_lower_case_and_is_a_word(self):
        self.assertFalse(hit("customer and managers"), "'and' is searched as a word here")
        self.assertTrue(hit("customer AND managers"))

    def test_matches_objects_with_title_and_abstract(self):
        class Paper:
            title = PAPER["title"]
            abstract = PAPER["abstract"]
        self.assertTrue(km.parse("LLM").matches(Paper()))

    def test_explain_lists_failed_terms(self):
        query = km.parse('"AI tools" AND workers')
        self.assertEqual(query.explain(PAPER), ["AI tools"])
        self.assertEqual(km.parse("LLM AND customer").explain(PAPER), [])
        self.assertEqual(km.parse("GPT OR banana").explain(PAPER), ["GPT", "banana"])


class ParseErrorTests(unittest.TestCase):
    def test_field_prefix_is_unsupported(self):
        with self.assertRaises(km.UnsupportedSyntax) as ctx:
            km.parse("cat:cs.HC AND agents")
        self.assertIn("field prefix", str(ctx.exception))
        with self.assertRaises(km.UnsupportedSyntax):
            km.parse('ti:"active learning"')

    def test_wildcard_is_unsupported(self):
        with self.assertRaises(km.UnsupportedSyntax):
            km.parse("assist*")
        with self.assertRaises(km.UnsupportedSyntax):
            km.parse('"AI assist*"')

    def test_malformed_queries(self):
        for bad in ["", "   ", "LLM AND", "AND LLM", "(LLM", "LLM)", '"unbalanced', "LLM OR OR AI", '""']:
            with self.subTest(bad=bad):
                with self.assertRaises(km.QueryError):
                    km.parse(bad)

    def test_unsupported_is_a_query_error_too(self):
        self.assertTrue(issubclass(km.UnsupportedSyntax, km.QueryError))


class RealKeywordShapesTests(unittest.TestCase):
    """The shapes in the shipped template and in the 2026-09 live file all parse."""

    def test_template_and_live_shapes(self):
        for query in [
            'LLM AND "knowledge work"', '"generative AI" AND workplace', '"customer interview" AND (LLM OR AI)',
            '"decision making" AND (management OR business OR organizations)', '"problem-based learning"',
            "scaffolding AND (teaching OR education)", '"synthetic users"', 'interview AND (synthesis OR analysis)',
        ]:
            with self.subTest(query=query):
                km.parse(query)

    def test_tree_rendering(self):
        self.assertEqual(str(km.parse('"customer interview" AND (LLM OR AI)')), '("customer interview" AND (LLM OR AI))')


if __name__ == "__main__":
    unittest.main()
