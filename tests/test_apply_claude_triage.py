"""Tests for scripts/utilities/apply_claude_triage.py: prepare batches, apply kept lists."""

import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from tests.support import fixture  # noqa: F401  (puts scripts/automation and scripts/utilities on sys.path)

import apply_claude_triage as act
import arxiv_harvest as ah
import digest as dg

PAGE1 = ah.parse_page(fixture("arxiv_raw_page1.xml"))[0]
PAGE2 = ah.parse_page(fixture("arxiv_raw_page2.xml"))[0]


class TriageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        root = Path(self.tmp.name)
        self.data_dir = root / ".research-data"
        store = ah.HarvestStore(self.data_dir)
        store.add(PAGE1 + PAGE2)
        self.digest_path = root / "2026-09-14.md"
        sections = [dg.TopicSection("Keyword Topic", [dg.paper_entry(PAGE1[1])]),
                    dg.TopicSection("Agents", pending=2), dg.TopicSection("Care", pending=1)]
        self.digest_path.write_text(dg.render_digest(sections, "2026-09-14"))
        self.candidates_path = self.data_dir / "claude-candidates" / "2026-09-14.json"
        self.candidates_path.parent.mkdir(parents=True)
        self.candidates_path.write_text(json.dumps({
            "date": "2026-09-14", "data_dir": str(self.data_dir), "digest_path": str(self.digest_path),
            "topics": [
                {"name": "Agents", "looking_for": "human-agent interaction", "exclude": ["medicine"],
                 "paper_ids": ["2609.13136", "1304.2717"]},
                {"name": "Care", "looking_for": "care coordination", "exclude": [], "paper_ids": ["2609.12070"]},
            ],
        }))
        self.outdir = root / "triage"

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = act.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def manifest(self):
        return json.loads((self.outdir / "manifest.json").read_text())

    def test_prepare_writes_batches_and_manifest(self):
        code, out, _ = self.run_cli("prepare", str(self.candidates_path), str(self.outdir), "--batch-size", "1")
        self.assertEqual(code, 0)
        manifest = self.manifest()
        self.assertEqual([(m["topic"], m["count"]) for m in manifest], [("Agents", 1), ("Agents", 1), ("Care", 1)])
        batch = Path(manifest[0]["batch"]).read_text()
        self.assertIn("# Claude review: Agents (batch 1 of 2, 1 papers)", batch)
        self.assertIn(f"Write your result to: {manifest[0]['kept']}", batch)
        self.assertIn("## Brief\n\nhuman-agent interaction", batch)
        self.assertIn("- medicine", batch)
        self.assertIn("### 2609.13136 [cs.HC]\nFrom Review to Reuse", batch)
        self.assertIn("manifest:", out)

    def test_apply_replaces_pending_lines_and_marks_processed(self):
        self.run_cli("prepare", str(self.candidates_path), str(self.outdir))
        manifest = self.manifest()
        Path(manifest[0]["kept"]).write_text(json.dumps({"kept": [
            {"id": "2609.13136", "why": "developers reviewing agent work"},
            {"id": "9999.99999", "why": "not a candidate"},
        ]}))
        Path(manifest[1]["kept"]).write_text(json.dumps({"kept": []}))
        code, out, err = self.run_cli("apply", str(self.candidates_path), str(self.outdir))
        self.assertEqual(code, 0, err)
        text = self.digest_path.read_text()
        self.assertIn("\n## Agents\n\n_Claude reviewed 2 candidates, kept 1._\n### From Review to Reuse", text)
        self.assertIn("**Why:** developers reviewing agent work\n", text)
        self.assertIn("\n## Care\n\n_Claude reviewed 1 candidates, kept 0._\n", text)
        self.assertNotIn("await Claude review", text)
        self.assertIn("### A Replaced Paper", text, "keyword section untouched")
        self.assertIn("not a candidate; ignored", err)
        data = json.loads(self.candidates_path.read_text())
        self.assertIn("processed_at", data)
        self.assertEqual(data["applied"], [{"topic": "Agents", "reviewed": 2, "kept": 1}, {"topic": "Care", "reviewed": 1, "kept": 0}])
        code, out, _ = self.run_cli("apply", str(self.candidates_path), str(self.outdir))
        self.assertEqual(code, 0)
        self.assertIn("Already processed", out)

    def test_missing_batch_result_keeps_that_topic_pending(self):
        self.run_cli("prepare", str(self.candidates_path), str(self.outdir))
        manifest = self.manifest()
        Path(manifest[1]["kept"]).write_text(json.dumps({"kept": [{"id": "2609.12070", "why": "fits"}]}))
        code, _, err = self.run_cli("apply", str(self.candidates_path), str(self.outdir))
        self.assertEqual(code, 2)
        text = self.digest_path.read_text()
        self.assertIn("_2 papers await Claude review.", text, "Agents still pending")
        self.assertIn("_Claude reviewed 1 candidates, kept 1._", text, "Care applied")
        self.assertNotIn("processed_at", json.loads(self.candidates_path.read_text()))
        self.assertIn("Agents", err)

    def test_malformed_kept_entries_are_ignored_not_fatal(self):
        self.run_cli("prepare", str(self.candidates_path), str(self.outdir))
        manifest = self.manifest()
        Path(manifest[0]["kept"]).write_text('{"kept": ["2609.13136", {"id": "1304.2717", "why": "old but fits"}]}')
        Path(manifest[1]["kept"]).write_text('{"kept": {"id": "2609.12070"}}')
        code, _, err = self.run_cli("apply", str(self.candidates_path), str(self.outdir))
        self.assertEqual(code, 2, "Care's result was not a list, so Care stays pending")
        text = self.digest_path.read_text()
        self.assertIn("_Claude reviewed 2 candidates, kept 1._\n### Bayesian Prediction", text, "the well-formed entry applied")
        self.assertIn("is not an object with id and why; ignored", err)
        self.assertIn("_1 paper awaits Claude review.", text)

    def test_missing_pending_line_leaves_the_file_unprocessed(self):
        self.run_cli("prepare", str(self.candidates_path), str(self.outdir))
        manifest = self.manifest()
        Path(manifest[0]["kept"]).write_text('{"kept": [{"id": "2609.13136", "why": "fits"}]}')
        Path(manifest[1]["kept"]).write_text('{"kept": []}')
        self.digest_path.write_text("# Research Digest - 2026-09-14\n\n**No papers today.**\n")
        code, _, err = self.run_cli("apply", str(self.candidates_path), str(self.outdir))
        self.assertEqual(code, 2)
        self.assertIn("rerun fetch_papers.py --force", err)
        self.assertNotIn("processed_at", json.loads(self.candidates_path.read_text()))

    def test_prepare_skips_topics_whose_candidates_are_gone(self):
        data = json.loads(self.candidates_path.read_text())
        data["topics"][1]["paper_ids"] = ["0000.00000"]
        self.candidates_path.write_text(json.dumps(data))
        code, _, err = self.run_cli("prepare", str(self.candidates_path), str(self.outdir))
        self.assertEqual(code, 0)
        self.assertEqual([m["topic"] for m in self.manifest()], ["Agents"])
        self.assertIn('no candidates left to review for "Care"', err)

    def test_prepare_refuses_processed_file(self):
        data = json.loads(self.candidates_path.read_text())
        data["processed_at"] = "2026-09-14T15:00:00+00:00"
        self.candidates_path.write_text(json.dumps(data))
        code, out, _ = self.run_cli("prepare", str(self.candidates_path), str(self.outdir))
        self.assertEqual(code, 0)
        self.assertIn("Already processed", out)
        self.assertFalse(self.outdir.exists())


if __name__ == "__main__":
    unittest.main()
