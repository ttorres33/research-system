"""Tests for scripts/utilities/keyword_dryrun.py against a temporary harvest store."""

import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from tests.support import fixture  # noqa: F401  (puts scripts/automation and scripts/utilities on sys.path)

import arxiv_harvest as ah
import keyword_dryrun as kd

PAPERS = ah.parse_page(fixture("arxiv_raw_page1.xml"))[0] + ah.parse_page(fixture("arxiv_raw_page2.xml"))[0]
KEYWORDS = """## Care
categories: cs.HC
- "informal support"
- "quantum widgets"

## Agents
mode: claude
categories: cs.HC, cs.AI
looking for: human-agent interaction

## Broken
- cat:cs.HC AND support
"""


class DryRunTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.data_dir = Path(self.tmp.name) / ".research-data"
        self.keywords = Path(self.tmp.name) / "keywords.md"
        self.keywords.write_text(KEYWORDS)

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, *argv):
        out = io.StringIO()
        with redirect_stdout(out), mock.patch("sys.argv", ["keyword_dryrun.py", *argv]):
            code = kd.main()
        return code, out.getvalue()

    def test_no_harvest_files_exits_1(self):
        code, out = self.run_cli("--keywords", str(self.keywords), "--data-dir", str(self.data_dir))
        self.assertEqual(code, 1)
        self.assertIn("No harvest files found", out)

    def test_report_flags_and_samples(self):
        ah.HarvestStore(self.data_dir).add(PAPERS)
        code, out = self.run_cli("--keywords", str(self.keywords), "--data-dir", str(self.data_dir))
        self.assertEqual(code, 0)
        self.assertIn("Using 2 harvest day(s): 2026-09-13, 2026-09-14", out)
        self.assertIn("== Care  (mode: keywords; categories: cs.HC)", out)
        self.assertIn('"informal support"', out)
        self.assertIn('2609.12070 [cs.HC] "The Only Thing Certain', out, "sample title printed under the hit")
        self.assertIn('"quantum widgets"', out)
        self.assertIn("[no hits]", out)
        self.assertIn("UNSUPPORTED: field prefix", out)
        self.assertIn("papers in categories per day:   09-13  09-14\n                                       1      3", out)
        self.assertIn("Claude review: 2 papers a day eligible for this topic", out,
                      "3 papers on the 14th minus the one Care's keyword claimed, plus 1 on the 13th, averages 2")
        self.assertIn("Claude review total: about 2 papers a day", out)
        self.assertIn("warning: no keywords, so Google Scholar is skipped", out)

    def test_high_volume_flag_and_claude_hint(self):
        ah.HarvestStore(self.data_dir).add(PAPERS)
        with mock.patch.object(kd, "HIGH_VOLUME_PER_DAY", 0), mock.patch.object(kd, "CLAUDE_POOL_PER_DAY", 0):
            _, out = self.run_cli("--keywords", str(self.keywords), "--data-dir", str(self.data_dir))
        self.assertIn("high volume", out)
        self.assertIn("consider keyword mode", out)

    def test_volumes_table(self):
        ah.HarvestStore(self.data_dir).add(PAPERS)
        code, out = self.run_cli("--volumes", "--data-dir", str(self.data_dir), "--days", "0")
        self.assertEqual(code, 0)
        self.assertIn("primary/day", out)
        self.assertIn("cs.HC", out)
        self.assertIn("Using 1 harvest day(s)", out, "--days 0 is clamped to 1")


if __name__ == "__main__":
    unittest.main()
