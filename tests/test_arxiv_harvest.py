"""Tests for scripts/automation/arxiv_harvest.py. No network: sessions are scripted."""

import json
import unittest
from unittest import mock
from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

import requests

from tests.support import fixture  # noqa: F401  (puts scripts/automation on sys.path)

import arxiv_harvest as ah


class FakeResponse:
    def __init__(self, status_code=200, text="", headers=None):
        self.status_code = status_code
        self.text = text
        self.headers = headers or {}


class FakeSession:
    """Scripted responses: each item is a FakeResponse or an exception instance to raise."""

    def __init__(self, script):
        self.script = list(script)
        self.calls = []
        self.headers_sent = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append(dict(params or {}))
        self.headers_sent.append(dict(headers or {}))
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


PAGE1 = fixture("arxiv_raw_page1.xml")
PAGE2 = fixture("arxiv_raw_page2.xml")
NO_RECORDS = fixture("oai_no_records.xml")
BAD_TOKEN = fixture("oai_bad_token.xml")
BAD_ARGUMENT = fixture("oai_bad_argument.xml")
AS_OF = date(2026, 9, 14)


def ok(text):
    return FakeResponse(200, text)


class ParsePageTests(unittest.TestCase):
    def test_fields_are_extracted_and_whitespace_collapsed(self):
        papers, token = ah.parse_page(PAGE1)
        self.assertEqual([p.id for p in papers], ["2609.12070", "2204.07865", "1304.2717"], "deleted record skipped")
        self.assertEqual(token, "6893203|1301")
        first = papers[0]
        self.assertEqual(
            first.title, '"The Only Thing Certain About This is Uncertainty": Exploring Informal Care Coordination'
        )
        self.assertEqual(first.categories, ["cs.HC", "cs.CY"])
        self.assertEqual(first.authors, "Ada Author, Bo Builder")
        self.assertEqual(first.comments, "12 pages, 3 figures")
        self.assertEqual(
            first.abstract,
            "Older adults aging in place often have informal support systems. As they age, many deal with new & uncertain needs.",
        )
        self.assertEqual(first.datestamp, "2026-09-14")
        self.assertEqual(first.versions, ["2026-09-10T18:02:43+00:00"])

    def test_replaced_paper_keeps_every_version_in_order(self):
        papers, _ = ah.parse_page(PAGE1)
        self.assertEqual(len(papers[1].versions), 3)
        self.assertTrue(papers[1].versions[0].startswith("2022-04-16"))
        self.assertTrue(papers[1].versions[2].startswith("2026-09-11"))

    def test_empty_resumption_token_means_last_page(self):
        papers, token = ah.parse_page(PAGE2)
        self.assertEqual(len(papers), 1)
        self.assertIsNone(token)

    def test_oai_error_element_raises_oai_error(self):
        with self.assertRaises(ah._OAIError) as ctx:
            ah.parse_page(NO_RECORDS)
        self.assertEqual(ctx.exception.code, "noRecordsMatch")

    def test_unparseable_body_raises_harvest_error(self):
        with self.assertRaises(ah.HarvestError):
            ah.parse_page("<html>Rate exceeded.")


class PaperTests(unittest.TestCase):
    def setUp(self):
        self.new, self.replaced, self.old = ah.parse_page(PAGE1)[0]

    def test_new_paper_rule(self):
        self.assertTrue(self.new.is_new(AS_OF))
        self.assertFalse(self.replaced.is_new(AS_OF), "more than one version")
        self.assertFalse(self.old.is_new(AS_OF), "single version but submitted in 2013")

    def test_new_paper_age_boundary(self):
        paper = ah.Paper.from_dict(self.new.to_dict())
        paper.versions = [(AS_OF - timedelta(days=60)).isoformat() + "T00:00:00+00:00"]
        self.assertTrue(paper.is_new(AS_OF))
        paper.versions = [(AS_OF - timedelta(days=61)).isoformat() + "T00:00:00+00:00"]
        self.assertFalse(paper.is_new(AS_OF))

    def test_derived_fields(self):
        self.assertEqual(self.new.url, "http://arxiv.org/abs/2609.12070v1")
        self.assertEqual(self.new.pdf_url, "https://arxiv.org/pdf/2609.12070v1")
        self.assertEqual(self.new.year, 2026)
        self.assertEqual(self.new.primary_category, "cs.HC")

    def test_in_categories(self):
        self.assertTrue(self.new.in_categories([]))
        self.assertTrue(self.new.in_categories(["cs.CY", "cs.SE"]), "cross-list counts")
        self.assertFalse(self.new.in_categories(["cs.LG"]))

    def test_dict_round_trip(self):
        self.assertEqual(ah.Paper.from_dict(json.loads(json.dumps(self.new.to_dict()))), self.new)


class HarvestTests(unittest.TestCase):
    def run_harvest(self, script, **kwargs):
        session = FakeSession(script)
        sleeps = []
        papers = ah.harvest(date(2026, 9, 13), session=session, sleep=sleeps.append, **kwargs)
        return papers, session, sleeps

    def test_follows_resumption_token_with_three_second_spacing(self):
        papers, session, sleeps = self.run_harvest([ok(PAGE1), ok(PAGE2)])
        self.assertEqual([p.id for p in papers], ["2609.12070", "2204.07865", "1304.2717", "2609.13136"])
        self.assertEqual(session.calls[0], {"verb": "ListRecords", "metadataPrefix": "arXivRaw", "from": "2026-09-13"})
        self.assertEqual(session.calls[1], {"verb": "ListRecords", "resumptionToken": "6893203|1301"})
        self.assertEqual(sleeps, [ah.REQUEST_SPACING_SECONDS])

    def test_until_date_is_passed_through(self):
        _, session, _ = self.run_harvest([ok(PAGE2)], until_date=date(2026, 9, 13))
        self.assertEqual(session.calls[0]["until"], "2026-09-13")

    def test_identifying_user_agent_is_sent(self):
        _, session, _ = self.run_harvest([ok(PAGE2)])
        self.assertTrue(session.headers_sent[0]["User-Agent"].startswith("research-system/"))

    def test_no_records_is_an_empty_result(self):
        papers, _, sleeps = self.run_harvest([ok(NO_RECORDS)])
        self.assertEqual(papers, [])
        self.assertEqual(sleeps, [])

    def test_expired_token_restarts_once(self):
        papers, session, _ = self.run_harvest([ok(PAGE1), ok(BAD_TOKEN), ok(PAGE1), ok(PAGE2)])
        self.assertEqual(len(papers), 4, "no duplicates from the abandoned first pass")
        self.assertEqual([c.get("resumptionToken", "initial") for c in session.calls],
                         ["initial", "6893203|1301", "initial", "6893203|1301"])

    def test_second_expired_token_fails(self):
        with self.assertRaises(ah.HarvestError):
            self.run_harvest([ok(PAGE1), ok(BAD_TOKEN), ok(PAGE1), ok(BAD_TOKEN)])

    def test_other_oai_error_fails(self):
        with self.assertRaises(ah.HarvestError) as ctx:
            self.run_harvest([ok(BAD_ARGUMENT)])
        self.assertIn("badArgument", str(ctx.exception))

    def test_503_honours_retry_after(self):
        papers, _, sleeps = self.run_harvest([FakeResponse(503, headers={"Retry-After": "7"}), ok(PAGE2)])
        self.assertEqual(len(papers), 1)
        self.assertEqual(sleeps, [7])

    def test_503_without_header_uses_the_ladder(self):
        _, _, sleeps = self.run_harvest([FakeResponse(503), FakeResponse(429), ok(PAGE2)])
        self.assertEqual(sleeps, [30, 120])

    def test_gives_up_after_the_ladder(self):
        with self.assertRaises(ah.HarvestError) as ctx:
            self.run_harvest([FakeResponse(503)] * 4)
        self.assertIn("after 3 retries", str(ctx.exception))

    def test_non_retryable_status_fails_at_once(self):
        with self.assertRaises(ah.HarvestError):
            self.run_harvest([FakeResponse(404)])

    def test_page_cap_stops_a_looping_token(self):
        with mock.patch.object(ah, "MAX_PAGES", 3):
            with self.assertRaises(ah.HarvestError) as ctx:
                self.run_harvest([ok(PAGE1)] * 5)
        self.assertIn("more than 3 pages", str(ctx.exception))

    def test_record_without_datestamp_is_skipped(self):
        broken = PAGE2.replace("<datestamp>2026-09-14</datestamp>", "")
        with self.assertLogs(ah.logger, level="WARNING"):
            papers, _ = ah.parse_page(broken)
        self.assertEqual(papers, [])

    def test_network_error_is_retried(self):
        papers, _, sleeps = self.run_harvest([requests.ConnectionError("boom"), ok(PAGE2)])
        self.assertEqual(len(papers), 1)
        self.assertEqual(sleeps, [30])


class HarvestStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.store = ah.HarvestStore(Path(self.tmp.name) / ".research-data")
        self.today = AS_OF
        self.papers = ah.parse_page(PAGE1)[0] + ah.parse_page(PAGE2)[0]

    def tearDown(self):
        self.tmp.cleanup()

    def test_first_run_starts_yesterday(self):
        self.assertEqual(self.store.window_start(self.today), (self.today - timedelta(days=1), None))

    def test_window_starts_at_last_datestamp(self):
        self.store.set_last_datestamp(self.today - timedelta(days=3))
        self.assertEqual(self.store.window_start(self.today), (self.today - timedelta(days=3), None))

    def test_window_is_capped_with_a_note(self):
        self.store.set_last_datestamp(self.today - timedelta(days=30))
        start, note = self.store.window_start(self.today)
        self.assertEqual(start, self.today - timedelta(days=14))
        self.assertIn("catching up from 2026-08-31 only", note)

    def test_unreadable_state_is_treated_as_first_run(self):
        self.store.data_dir.mkdir(parents=True)
        self.store.state_path.write_text("{not json")
        with self.assertLogs(ah.logger, level="WARNING"):
            self.assertIsNone(self.store.last_datestamp())
        self.assertEqual(self.store.window_start(self.today)[0], self.today - timedelta(days=1))

    def test_add_groups_by_datestamp_and_dedupes(self):
        fresh = self.store.add(self.papers)
        self.assertEqual(len(fresh), 4)
        self.assertEqual(sorted(p.name for p in self.store.dir.glob("*.json")), ["2026-09-13.json", "2026-09-14.json"])
        self.assertEqual(self.store.add(self.papers), [], "already saved")
        self.assertEqual(self.store.add([self.papers[0], self.papers[0]]), [], "duplicate ids in one batch")
        loaded = self.store.load()
        self.assertEqual([p.id for p in loaded["2026-09-13"]], ["1304.2717"])
        self.assertEqual(len(loaded["2026-09-14"]), 3)

    def test_add_replaces_a_corrupt_day_file_instead_of_crashing(self):
        self.store.dir.mkdir(parents=True)
        (self.store.dir / "2026-09-14.json").write_text("{not json")
        with self.assertLogs(ah.logger, level="WARNING"):
            fresh = self.store.add(self.papers)
        self.assertEqual(len(fresh), 4)
        self.assertEqual(len(self.store.load()["2026-09-14"]), 3)

    def test_prune_removes_only_old_dated_files(self):
        self.store.dir.mkdir(parents=True)
        (self.store.dir / (self.today - timedelta(days=10)).isoformat()).with_suffix(".json").write_text("[]")
        (self.store.dir / (self.today - timedelta(days=2)).isoformat()).with_suffix(".json").write_text("[]")
        (self.store.dir / "notes.json").write_text("[]")
        removed = self.store.prune(self.today)
        self.assertEqual(removed, ["2026-09-04.json"])
        self.assertEqual(sorted(p.name for p in self.store.dir.glob("*.json")), ["2026-09-12.json", "notes.json"])


if __name__ == "__main__":
    unittest.main()
