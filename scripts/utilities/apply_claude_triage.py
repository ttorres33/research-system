#!/usr/bin/env python3
"""Prepare and apply the Claude review of arXiv candidates.

The scheduled run records, per Claude-mode topic, the new papers Claude should read
(.research-data/claude-candidates/<date>.json). /generate-research-digest then:

  1. `prepare CANDIDATES OUTDIR`  writes one markdown batch file per topic (at most
     --batch-size papers each) with the brief, the exclusions and the papers, plus
     OUTDIR/manifest.json listing the batches and where each agent must write its result
  2. spawns one agent per batch file; each writes {"kept": [{"id", "why"}]} to its path
  3. `apply CANDIDATES OUTDIR`    replaces each topic's "await Claude review" line in the
     digest with the kept papers, rendered by the same code the scheduled run uses, and
     marks the candidates file processed

Python does the digest rewrite so Claude only returns data. A topic whose batch results
are missing keeps its pending line and can be retried.
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "automation"))

from arxiv_harvest import HarvestStore  # noqa: E402
from digest import paper_entry, render_paper, replace_pending  # noqa: E402

DEFAULT_BATCH_SIZE = 40
WHY_MAX_CHARS = 200


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "topic"


def load_candidates(path):
    try:
        data = json.loads(Path(path).read_text())
    except OSError as e:
        sys.exit(f"cannot read candidates file {path}: {e}")
    except ValueError as e:
        sys.exit(f"candidates file {path} is not valid JSON: {e}")
    for key in ("date", "data_dir", "digest_path", "topics"):
        if key not in data:
            sys.exit(f"candidates file {path} has no '{key}' field")
    return data


def load_papers(data):
    return {paper.id: paper for papers in HarvestStore(data["data_dir"]).load().values() for paper in papers}


def prepare(candidates_path, outdir, batch_size):
    data = load_candidates(candidates_path)
    if data.get("processed_at"):
        print(f"Already processed at {data['processed_at']}; nothing to prepare.")
        return 0
    papers = load_papers(data)
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    manifest = []
    number = 0
    for topic in data["topics"]:
        ids = [pid for pid in topic["paper_ids"] if pid in papers]
        missing = len(topic["paper_ids"]) - len(ids)
        if missing:
            print(f"warning: {missing} candidate(s) for \"{topic['name']}\" are no longer in the harvest files", file=sys.stderr)
        if not ids:
            print(f"warning: no candidates left to review for \"{topic['name']}\"; skipped", file=sys.stderr)
            continue
        batches = [ids[i:i + batch_size] for i in range(0, len(ids), batch_size)]
        for index, batch in enumerate(batches, 1):
            number += 1
            stem = f"batch-{number:02d}-{slug(topic['name'])}"
            batch_path = outdir / f"{stem}.md"
            kept_path = outdir / f"{stem}-kept.json"
            lines = [
                f"# Claude review: {topic['name']} (batch {index} of {len(batches)}, {len(batch)} papers)",
                "",
                f"Write your result to: {kept_path}",
                'Format: {"kept": [{"id": "2609.12345", "why": "one line, at most 25 words"}]}',
                "Keep a paper only if it fits the brief and is not excluded. Judge from the title and",
                'abstract. If nothing fits, write {"kept": []}. Do not add papers that are not listed here.',
                "",
                "## Brief",
                "",
                topic["looking_for"],
                "",
                "## Exclude",
                "",
            ]
            lines += [f"- {item}" for item in topic.get("exclude", [])] or ["- (nothing listed)"]
            lines += ["", f"## Papers ({len(batch)})", ""]
            for pid in batch:
                paper = papers[pid]
                lines += [f"### {pid} [{paper.primary_category}]", paper.title, "", paper.abstract, ""]
            batch_path.write_text("\n".join(lines))
            manifest.append({"topic": topic["name"], "batch": str(batch_path), "kept": str(kept_path), "count": len(batch)})
    (outdir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    for item in manifest:
        print(f"{item['count']:3} papers  {item['batch']}  ->  {item['kept']}")
    print(f"manifest: {outdir / 'manifest.json'}")
    return 0


def apply(candidates_path, outdir, force=False):
    data = load_candidates(candidates_path)
    if data.get("processed_at") and not force:
        print(f"Already processed at {data['processed_at']}; nothing to apply (use --force to redo).")
        return 0
    manifest_path = Path(outdir) / "manifest.json"
    if not manifest_path.exists():
        sys.exit(f"no manifest at {manifest_path}; run prepare first")
    manifest = json.loads(manifest_path.read_text())
    papers = load_papers(data)
    digest_path = Path(data["digest_path"])
    if not digest_path.exists():
        sys.exit(f"digest not found: {digest_path}")
    text = digest_path.read_text()

    kept_by_topic = {}
    incomplete = set()
    for item in manifest:
        kept_path = Path(item["kept"])
        if not kept_path.exists():
            incomplete.add(item["topic"])
            continue
        try:
            kept = json.loads(kept_path.read_text()).get("kept", [])
        except (OSError, ValueError, AttributeError) as e:
            print(f"warning: {kept_path} is unreadable ({e}); treating \"{item['topic']}\" as incomplete", file=sys.stderr)
            incomplete.add(item["topic"])
            continue
        if not isinstance(kept, list):
            print(f"warning: {kept_path}: \"kept\" is not a list; treating \"{item['topic']}\" as incomplete", file=sys.stderr)
            incomplete.add(item["topic"])
            continue
        kept_by_topic.setdefault(item["topic"], []).extend(kept)

    applied = []
    for topic in data["topics"]:
        name = topic["name"]
        if name in incomplete:
            print(f"\"{name}\": results missing for at least one batch; pending line kept", file=sys.stderr)
            continue
        allowed = set(topic["paper_ids"])
        entries, seen = [], set()
        for item in kept_by_topic.get(name, []):
            if not isinstance(item, dict):
                print(f"warning: \"{name}\": kept entry {item!r} is not an object with id and why; ignored", file=sys.stderr)
                continue
            pid = str(item.get("id", "")).strip()
            if pid not in allowed:
                print(f"warning: \"{name}\": kept id {pid!r} was not a candidate; ignored", file=sys.stderr)
                continue
            if pid in seen or pid not in papers:
                continue
            seen.add(pid)
            why = " ".join(str(item.get("why", "")).split())[:WHY_MAX_CHARS]
            entries.append(paper_entry(papers[pid], why=why))
        summary = f"_Claude reviewed {len(topic['paper_ids'])} candidates, kept {len(entries)}._"
        replacement = summary + "".join(render_paper(entry) for entry in entries)
        text, replaced = replace_pending(text, name, replacement)
        if not replaced:
            print(f"warning: no pending line found under \"{name}\" in {digest_path}; not applied "
                  f"(was the digest rebuilt? rerun fetch_papers.py --force to restore the pending line)", file=sys.stderr)
            incomplete.add(name)
            continue
        applied.append((name, len(topic["paper_ids"]), len(entries)))
        print(f"\"{name}\": reviewed {len(topic['paper_ids'])}, kept {len(entries)}")

    digest_path.write_text(text)
    data["applied"] = [{"topic": n, "reviewed": r, "kept": k} for n, r, k in applied]
    if not incomplete:
        data["processed_at"] = datetime.now(timezone.utc).isoformat()
    Path(candidates_path).write_text(json.dumps(data, indent=2))
    if incomplete:
        print(f"{len(incomplete)} topic(s) not applied; run the missing batches and apply again", file=sys.stderr)
        return 2
    print(f"digest updated: {digest_path}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare", help="write batch files and a manifest for the review agents")
    prep.add_argument("candidates")
    prep.add_argument("outdir")
    prep.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    app = sub.add_parser("apply", help="write the kept papers into the digest")
    app.add_argument("candidates")
    app.add_argument("outdir")
    app.add_argument("--force", action="store_true")
    opts = parser.parse_args(argv)
    if opts.command == "prepare":
        return prepare(opts.candidates, opts.outdir, opts.batch_size)
    return apply(opts.candidates, opts.outdir, opts.force)


if __name__ == "__main__":
    sys.exit(main())
