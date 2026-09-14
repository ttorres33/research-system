"""End-to-end tests for scripts/automation/fetch_papers.py against a scratch research root.

load_config, the harvest, Google Scholar, the clock and the Sunday check are replaced,
so nothing touches the network or the real vault.
"""

import io
import json
import unittest
from contextlib import contextmanager, redirect_stdout
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from tests.support import fixture  # noqa: F401  (puts scripts/automation on sys.path)

import arxiv_harvest as ah
import fetch_papers as fp

AS_OF = date(2026, 9, 14)
PAGE1 = ah.parse_page(fixture("arxiv_raw_page1.xml"))[0]   # new cs.HC/cs.CY paper, replaced paper, old cs.AI paper
PAGE2 = ah.parse_page(fixture("arxiv_raw_page2.xml"))[0]   # new cs.HC/cs.AI paper about AI agents
KEYWORDS = """## Care
categories: cs.HC
- "informal support"

## Agents
mode: claude
categories: cs.HC, cs.AI
looking for: human-agent interaction

## Both
mode: both
categories: cs.HC
- "aging in place"

## Everything
- "Bayesian prediction"
"""


class FetchPapersTests(unittest.TestCase):
    def setUp(self):
        self._quiet = redirect_stdout(io.StringIO())
        self._quiet.__enter__()
        self.tmp = TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / ".research-data").mkdir()
        (self.root / "daily-digests").mkdir()
        self.config = {
            "serpapi": {"api_key": "k"},
            "google_scholar": {"max_results": 5, "search_days": 7},
            "paths": {"research_root": str(self.root), "daily_digests": "daily-digests", "data": ".research-data"},
            "links": {"format": "obsidian"},
            "filter": {"relevance_criteria": "product work", "relevant_topics": ["ux"], "irrelevant_topics": ["medicine"]},
        }
        self.write_keywords(KEYWORDS)

    def tearDown(self):
        self.tmp.cleanup()
        self._quiet.__exit__(None, None, None)

    def write_keywords(self, text):
        (self.root / ".research-data" / "keywords.md").write_text(text)

    @contextmanager
    def running(self, records=None, harvest_error=None, sunday=False, scholar=None):
        def fake_harvest(from_date, until_date=None, session=None, sleep=None):
            self.harvest_from = from_date
            if harvest_error:
                raise ah.HarvestError(harvest_error)
            return list(records or [])
        with mock.patch.object(fp, "load_config", return_value=self.config), \
             mock.patch.object(fp, "harvest", side_effect=fake_harvest), \
             mock.patch.object(fp, "utc_today", return_value=AS_OF), \
             mock.patch.object(fp, "today_is_sunday", return_value=sunday), \
             mock.patch.object(fp, "search_google_scholar", side_effect=scholar or (lambda *a, **k: [])) as scholar_mock, \
             mock.patch.object(fp, "setup_logging", return_value=mock.Mock()):
            yield scholar_mock

    def digest(self):
        files = list((self.root / "daily-digests").glob("*.md"))
        self.assertEqual(len(files), 1)
        return files[0].read_text()

    def candidates(self):
        files = list((self.root / ".research-data" / "claude-candidates").glob("*.json"))
        return json.loads(files[0].read_text()) if files else None

    def seen(self):
        path = self.root / ".research-data" / ".seen_arxiv_papers.json"
        return set(json.loads(path.read_text())["urls"]) if path.exists() else set()

    def test_normal_day_routes_papers_by_mode_and_category(self):
        with self.running(records=PAGE1 + PAGE2):
            self.assertEqual(fp.main([]), 0)
        text = self.digest()
        self.assertIn("\n## Care\n\n### \"The Only Thing Certain", text, "keyword match in cs.HC")
        self.assertIn("\n## Agents\n\n_1 paper awaits Claude review.", text)
        self.assertIn("\n## Both\n\n_1 paper awaits Claude review.", text,
                      "the care paper was claimed by Care's keyword; the agents paper is eligible for Both too")
        self.assertNotIn("## Everything", text, "the 2013 paper is not new, so no match")
        self.assertNotIn("A Replaced Paper", text)
        candidates = self.candidates()
        self.assertEqual([t["name"] for t in candidates["topics"]], ["Agents", "Both"])
        self.assertEqual(candidates["topics"][0]["looking_for"], "human-agent interaction")
        self.assertEqual(candidates["topics"][1]["keywords"], ['"aging in place"'])
        self.assertEqual(candidates["exclude"], ["medicine"])
        self.assertEqual(candidates["papers"], [{"id": "2609.13136", "topics": ["Agents", "Both"]}],
                         "one entry per paper, listing every Claude topic it is eligible for")
        self.assertEqual(self.seen(), {"http://arxiv.org/abs/2609.12070v1", "http://arxiv.org/abs/2609.13136v1"})
        state = json.loads((self.root / ".research-data" / ".arxiv_harvest_state.json").read_text())
        self.assertEqual(state["last_datestamp"], "2026-09-14")
        self.assertEqual(self.harvest_from, AS_OF.replace(day=13), "first run harvests from yesterday")

    def test_looking_for_falls_back_to_filter_criteria(self):
        self.write_keywords("## Agents\nmode: claude\ncategories: cs.HC\n")
        with self.running(records=PAGE2):
            fp.main([])
        brief = self.candidates()["topics"][0]["looking_for"]
        self.assertIn('topic "Agents"', brief)
        self.assertIn("product work", brief)
        self.assertIn("Relevant topics: ux.", brief)

    def test_harvest_failure_writes_a_note_and_keeps_state(self):
        with self.running(harvest_error="HTTP 503 after 3 retries"):
            fp.main([])
        text = self.digest()
        self.assertIn("> **Note:** arXiv harvest failed (HTTP 503 after 3 retries). The next run will catch up from 2026-09-13.", text)
        self.assertIn("**No papers today.** arXiv could not be harvested", text)
        self.assertFalse((self.root / ".research-data" / ".arxiv_harvest_state.json").exists())
        self.assertIsNone(self.candidates())

    def test_second_run_does_not_repeat_papers(self):
        with self.running(records=PAGE1 + PAGE2):
            fp.main([])
        for path in list((self.root / "daily-digests").glob("*.md")) + list((self.root / ".research-data" / "claude-candidates").glob("*.json")):
            path.unlink()
        with self.running(records=PAGE1 + PAGE2):
            fp.main([])
        text = self.digest()
        self.assertIn("**No papers today.** The harvest found 0 new arXiv papers", text)
        self.assertEqual(self.harvest_from, AS_OF, "second run starts at the last datestamp")

    def test_same_day_rerun_refuses_to_clobber_a_digest_with_papers(self):
        with self.running(records=PAGE1 + PAGE2):
            fp.main([])
        before = self.digest()
        with self.running(records=PAGE1 + PAGE2):
            code = fp.main([])
        self.assertEqual(code, 1)
        self.assertEqual(self.digest(), before, "digest untouched")
        self.assertEqual(self.candidates()["papers"][0]["id"], "2609.13136", "candidates untouched")

    def test_forced_rerun_carries_unprocessed_candidates(self):
        with self.running(records=PAGE1 + PAGE2):
            fp.main([])
        with self.running(records=PAGE1 + PAGE2):
            code = fp.main(["--force"])
        self.assertEqual(code, 0)
        text = self.digest()
        self.assertIn("\n## Agents\n\n_1 paper awaits Claude review.", text, "pending line re-emitted from the carried ids")
        self.assertIn("\n## Both\n\n_1 paper awaits Claude review.", text)
        self.assertNotIn("No papers today", text)
        self.assertEqual(self.candidates()["papers"], [{"id": "2609.13136", "topics": ["Agents", "Both"]}])

    def test_processed_candidates_are_not_carried(self):
        with self.running(records=PAGE1 + PAGE2):
            fp.main([])
        data = json.loads(self.candidates_path().read_text())
        data["processed_at"] = "2026-09-14T15:00:00+00:00"
        self.candidates_path().write_text(json.dumps(data))
        with self.running(records=PAGE1 + PAGE2):
            fp.main(["--force"])
        self.assertNotIn("await Claude review", self.digest())

    def test_claude_topics_sharing_a_category_all_see_the_paper(self):
        self.write_keywords("## A\nmode: claude\ncategories: cs.HC\n\n## B\nmode: claude\ncategories: cs.CY, cs.AI\n\n## C\nmode: claude\ncategories: econ.GN\n")
        with self.running(records=PAGE1 + PAGE2):
            fp.main([])
        papers = {p["id"]: p["topics"] for p in self.candidates()["papers"]}
        self.assertEqual(papers, {"2609.12070": ["A", "B"], "2609.13136": ["A", "B"]},
                         "no topic claims a candidate; C has no eligible paper")
        text = self.digest()
        self.assertIn("\n## A\n\n_2 papers await Claude review.", text)
        self.assertIn("\n## B\n\n_2 papers await Claude review.", text)
        self.assertNotIn("## C", text)

    def test_prune_candidates_removes_only_old_dated_files(self):
        cdir = self.root / ".research-data" / "claude-candidates"
        cdir.mkdir()
        for name in ("2026-09-01.json", "2026-09-13.json", "notes.json"):
            (cdir / name).write_text("{}")
        fp.prune_candidates(self.config, AS_OF)
        self.assertEqual(sorted(p.name for p in cdir.glob("*.json")), ["2026-09-13.json", "notes.json"])

    def test_scholar_error_never_logs_the_api_key(self):
        def failing(*a, **k):
            raise RuntimeError("401 Client Error for url: https://serpapi.com/search?q=x&api_key=SECRET123&num=5")
        out = io.StringIO()
        with self.running(records=[], sunday=True, scholar=failing):
            with mock.patch.object(fp, "print", create=True):
                pass
            with redirect_stdout(out):
                fp.main([])
        self.assertNotIn("SECRET123", out.getvalue())
        self.assertIn("api_key=***", out.getvalue())
        self.assertIn("Google Scholar failed for 3 of 4 topics", self.digest())

    def candidates_path(self):
        return next((self.root / ".research-data" / "claude-candidates").glob("*.json"))

    def test_catch_up_is_capped_with_a_note(self):
        store = ah.HarvestStore(self.root / ".research-data")
        store.set_last_datestamp(date(2026, 8, 1))
        with self.running(records=[]):
            fp.main([])
        self.assertEqual(self.harvest_from, date(2026, 8, 31))
        self.assertIn("arXiv catch-up was capped: last harvest was 2026-08-01; catching up from 2026-08-31 only.", self.digest())

    def test_unsupported_keyword_is_reported_not_swallowed(self):
        self.write_keywords('## Care\n- cat:cs.HC AND support\n- "informal support"\n')
        with self.running(records=PAGE1):
            fp.main([])
        text = self.digest()
        self.assertIn("Some keywords use syntax the matcher does not support and were skipped: topic \"Care\", keyword 'cat:cs.HC AND support': field prefix", text)
        self.assertIn("### \"The Only Thing Certain", text, "the good keyword still ran")

    def test_sunday_runs_scholar_by_keyword_and_skips_keywordless_topics(self):
        scholar = lambda keywords, *a, **k: [dict(title=f"S:{keywords[0]}", authors="x", year="2026", snippet="s",
                                                  url=f"https://example.org/{len(keywords)}", citations=0, source="Google Scholar")]
        with self.running(records=[], sunday=True, scholar=scholar) as scholar_mock:
            fp.main([])
        text = self.digest()
        self.assertEqual(scholar_mock.call_count, 3, "Care, Both and Everything have keywords; Agents does not")
        self.assertIn("\n## Agents\n\n_Google Scholar skipped for this topic: no keywords_\n", text)
        self.assertIn('### S:"informal support"', text)

    def test_weekday_never_calls_scholar(self):
        with self.running(records=PAGE2) as scholar_mock:
            fp.main([])
        self.assertEqual(scholar_mock.call_count, 0)
        self.assertNotIn("Google Scholar", self.digest())


if __name__ == "__main__":
    unittest.main()
