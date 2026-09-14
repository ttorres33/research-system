#!/usr/bin/env python3
"""Prepare and apply the Claude review of arXiv candidates.

The scheduled run records, once, every new paper that falls in the categories of at
least one Claude-mode topic, with the topics each paper is eligible for, plus every
Claude topic's brief (.research-data/claude-candidates/<date>.json). Claude reads each
paper once and may keep it under any topic it is eligible for. /generate-research-digest:

  1. `prepare CANDIDATES OUTDIR`  writes batch files of at most --batch-size papers, each
     carrying all the briefs and, per paper, its eligible topics, plus OUTDIR/manifest.json
     listing the batches and where each agent must write its result
  2. spawns one agent per batch file; each writes
     {"kept": [{"id", "topic", "why"}]} to its path, one entry per paper and topic kept
  3. `apply CANDIDATES OUTDIR`    replaces each topic's "await Claude review" line in the
     digest with that topic's kept papers, rendered by the same code the scheduled run
     uses, and marks the candidates file processed

Python does the digest rewrite so Claude only returns data. If any batch result is
missing or unreadable, nothing is applied and the review can be retried.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "automation"))

from arxiv_harvest import HarvestStore  # noqa: E402
from digest import paper_entry, render_paper, replace_pending  # noqa: E402

DEFAULT_BATCH_SIZE = 40
WHY_MAX_CHARS = 200
REQUIRED_KEYS = ("date", "data_dir", "digest_path", "topics", "papers")


def load_candidates(path):
    try:
        data = json.loads(Path(path).read_text())
    except OSError as e:
        sys.exit(f"cannot read candidates file {path}: {e}")
    except ValueError as e:
        sys.exit(f"candidates file {path} is not valid JSON: {e}")
    for key in REQUIRED_KEYS:
        if key not in data:
            sys.exit(f"candidates file {path} has no '{key}' field (written by an older version?)")
    return data


def load_papers(data):
    return {paper.id: paper for papers in HarvestStore(data["data_dir"]).load().values() for paper in papers}


def present_candidates(data, papers):
    """[(id, [eligible topics])] for candidates whose bodies are still in the harvest files."""
    items, missing = [], 0
    for item in data["papers"]:
        pid, topics = item.get("id"), list(item.get("topics", []))
        if pid in papers and topics:
            items.append((pid, topics))
        else:
            missing += 1
    return items, missing


def topics_block(data):
    lines = ["## Topics", ""]
    for topic in data["topics"]:
        lines += [f"### {topic['name']}", "", f"Brief: {topic['looking_for']}"]
        if topic.get("keywords"):
            lines += ["", "Keywords the user searches with for this topic, as examples of what it covers:"]
            lines += [f"- {keyword}" for keyword in topic["keywords"]]
        lines.append("")
    lines += ["## Exclude (applies to every topic)", ""]
    lines += [f"- {item}" for item in data.get("exclude", [])] or ["- (nothing listed)"]
    lines.append("")
    return lines


def prepare(candidates_path, outdir, batch_size):
    data = load_candidates(candidates_path)
    if data.get("processed_at"):
        print(f"Already processed at {data['processed_at']}; nothing to prepare.")
        return 0
    papers = load_papers(data)
    items, missing = present_candidates(data, papers)
    if missing:
        print(f"warning: {missing} candidate(s) are no longer in the harvest files and cannot be reviewed", file=sys.stderr)
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    batches = [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
    manifest = []
    for number, batch in enumerate(batches, 1):
        stem = f"batch-{number:02d}"
        batch_path, kept_path = outdir / f"{stem}.md", outdir / f"{stem}-kept.json"
        lines = [
            f"# Claude review: batch {number} of {len(batches)} ({len(batch)} papers)",
            "",
            f"Write your result to: {kept_path}",
            'Format: {"kept": [{"id": "2609.12345", "topic": "Topic name exactly as written", "why": "one line, at most 25 words"}]}',
            "Judge each paper from its title and abstract against the topics listed under it, and only",
            "those. Keep it under every topic whose brief it fits, one entry per paper and topic. Leave",
            'out papers that fit nothing. If nothing in this batch fits, write {"kept": []}. Do not add',
            "ids or topic names that are not listed here.",
            "",
        ]
        lines += topics_block(data)
        lines += [f"## Papers ({len(batch)})", ""]
        for pid, eligible in batch:
            paper = papers[pid]
            lines += [f"### {pid} [{paper.primary_category}]", f"Eligible topics: {'; '.join(eligible)}", "",
                      paper.title, "", paper.abstract, ""]
        batch_path.write_text("\n".join(lines))
        manifest.append({"batch": str(batch_path), "kept": str(kept_path), "count": len(batch)})
    (outdir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    for item in manifest:
        print(f"{item['count']:3} papers  {item['batch']}  ->  {item['kept']}")
    if not manifest:
        print("no candidates left to review; apply will close the review with nothing kept")
    print(f"manifest: {outdir / 'manifest.json'}")
    return 0


def read_results(manifest):
    """All kept entries across batches, or None when any batch result is missing or unreadable."""
    entries, problems = [], []
    for item in manifest:
        kept_path = Path(item["kept"])
        try:
            kept = json.loads(kept_path.read_text()).get("kept", [])
        except (OSError, ValueError, AttributeError) as e:
            problems.append(f"{kept_path}: unreadable ({e})")
            continue
        if not isinstance(kept, list):
            problems.append(f"{kept_path}: \"kept\" is not a list")
            continue
        entries.extend(kept)
    for problem in problems:
        print(f"warning: {problem}", file=sys.stderr)
    return None if problems else entries


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
    items, _ = present_candidates(data, papers)
    eligible = {pid: topics for pid, topics in items}
    digest_path = Path(data["digest_path"])
    if not digest_path.exists():
        sys.exit(f"digest not found: {digest_path}")

    results = read_results(manifest)
    if results is None:
        print("a batch result is missing or unreadable; nothing applied. Re-run that agent and apply again.", file=sys.stderr)
        return 2

    kept_by_topic = {topic["name"]: [] for topic in data["topics"]}
    seen_pairs = set()
    for item in results:
        if not isinstance(item, dict):
            print(f"warning: kept entry {item!r} is not an object with id, topic and why; ignored", file=sys.stderr)
            continue
        pid, topic = str(item.get("id", "")).strip(), str(item.get("topic", "")).strip()
        if pid not in eligible:
            print(f"warning: kept id {pid!r} was not a candidate; ignored", file=sys.stderr)
            continue
        if topic not in eligible[pid]:
            print(f"warning: paper {pid} is not eligible for topic {topic!r}; ignored", file=sys.stderr)
            continue
        if (pid, topic) in seen_pairs:
            continue
        seen_pairs.add((pid, topic))
        why = " ".join(str(item.get("why", "")).split())[:WHY_MAX_CHARS]
        kept_by_topic[topic].append(paper_entry(papers[pid], why=why))

    text = digest_path.read_text()
    applied, not_found = [], []
    for topic in data["topics"]:
        name = topic["name"]
        reviewed = sum(1 for _, topics in items if name in topics)
        entries = kept_by_topic[name]
        summary = f"_Claude reviewed {reviewed} candidates, kept {len(entries)}._"
        text, replaced = replace_pending(text, name, summary + "".join(render_paper(e) for e in entries))
        if not replaced:
            not_found.append(name)
            print(f"warning: no pending line found under \"{name}\" in {digest_path}; not applied "
                  f"(was the digest rebuilt? rerun fetch_papers.py --force to restore the pending line)", file=sys.stderr)
            continue
        applied.append({"topic": name, "reviewed": reviewed, "kept": len(entries)})
        print(f"\"{name}\": reviewed {reviewed}, kept {len(entries)}")

    digest_path.write_text(text)
    data["applied"] = applied
    if not not_found:
        data["processed_at"] = datetime.now(timezone.utc).isoformat()
    Path(candidates_path).write_text(json.dumps(data, indent=2))
    if not_found:
        print(f"{len(not_found)} topic(s) not applied: {', '.join(not_found)}", file=sys.stderr)
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
