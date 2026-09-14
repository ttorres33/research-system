#!/usr/bin/env python3
"""Show what each topic and keyword would match against recent arXiv harvests.

Reads the harvest files fetch_papers.py keeps under {research_root}/.research-data/
arxiv-harvest/ (the last seven days) and runs every topic's keywords over them with the
same matcher the daily run uses. Prints, per topic, the size of its category pool per
day and, per keyword, hits per day with sample titles, so an over-broad phrase such as
"active learning" shows itself before it fills a digest.

Options:
  --harvest        fetch yesterday's papers from arXiv into memory first (not saved, so the
                   next scheduled run still treats them as new); for setups with no
                   harvest files yet
  --volumes        print new papers per day by category instead; used to refresh
                   config/arxiv-categories.md
  --keywords PATH  keywords.md to test (default: keywords.md in the data directory)
  --data-dir PATH  .research-data directory to read harvests from (default: the configured
                   one; with this flag config.yaml is not read at all)
  --days N         how many harvest days to use (default 7, minimum 1)
"""

import argparse
import sys
from collections import Counter, defaultdict
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "automation"))

from arxiv_harvest import HarvestError, HarvestStore, harvest, utc_today  # noqa: E402
from config import data_dir as config_data_dir, load_config  # noqa: E402
from keyword_match import QueryError, parse  # noqa: E402
from topics import load_topics  # noqa: E402

HIGH_VOLUME_PER_DAY = 20      # a keyword matching more than this a day is probably a false friend
CLAUDE_POOL_PER_DAY = 60      # above this, the wizard suggests keyword mode instead of Claude mode
SAMPLE_TITLES = 5


def load_days(store, days, do_harvest):
    """{datestamp: [Paper]} for the most recent `days` harvest files, plus an in-memory day."""
    by_day = store.load()
    if do_harvest:
        today = utc_today()
        print(f"Harvesting arXiv from {(today - timedelta(days=1)).isoformat()} (in memory only)...", flush=True)
        try:
            records = harvest(today - timedelta(days=1))
        except HarvestError as e:
            print(f"  harvest failed: {e}", flush=True)
        else:
            known = {p.id for papers in by_day.values() for p in papers}
            for paper in records:
                if paper.is_new(today) and paper.id not in known:
                    by_day.setdefault(paper.datestamp, []).append(paper)
                    known.add(paper.id)
    days_sorted = sorted(by_day)[-days:]
    return {d: by_day[d] for d in days_sorted}


def print_volumes(by_day):
    primary, any_listed = Counter(), Counter()
    for papers in by_day.values():
        for paper in papers:
            primary[paper.primary_category] += 1
            for category in set(paper.categories):
                any_listed[category] += 1
    n = max(len(by_day), 1)
    print(f"New papers per day by category, averaged over {len(by_day)} harvest day(s): {', '.join(sorted(by_day))}")
    print(f"{'category':18} {'primary/day':>12} {'listed/day':>11}")
    for category, count in sorted(any_listed.items(), key=lambda kv: -kv[1]):
        print(f"{category:18} {primary[category] / n:12.1f} {count / n:11.1f}")


def main():
    args = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    args.add_argument("--harvest", action="store_true")
    args.add_argument("--volumes", action="store_true")
    args.add_argument("--keywords", type=Path)
    args.add_argument("--data-dir", type=Path)
    args.add_argument("--days", type=int, default=7)
    opts = args.parse_args()

    data_dir = opts.data_dir or config_data_dir(load_config())
    keywords_path = opts.keywords or (data_dir / "keywords.md")
    days = max(1, opts.days)

    by_day = load_days(HarvestStore(data_dir), days, opts.harvest)
    if not by_day:
        print("No harvest files found. Run fetch_papers.py once, or pass --harvest to fetch a day into memory.")
        return 1
    days = sorted(by_day)
    print(f"Using {len(days)} harvest day(s): {', '.join(days)}; "
          f"{sum(len(v) for v in by_day.values())} new papers in total\n")

    if opts.volumes:
        print_volumes(by_day)
        return 0

    topics = load_topics(keywords_path)
    day_label = " ".join(f"{d[5:]:>6}" for d in days)
    for topic in topics:
        print(f"== {topic.name}  (mode: {topic.mode}; categories: {', '.join(topic.categories) or 'all of arXiv'})")
        for warning in topic.warnings:
            print(f"   warning: {warning}")
        pools = {d: [p for p in by_day[d] if p.in_categories(topic.categories)] for d in days}
        print(f"   papers in categories per day:  {day_label}")
        print(f"   {'':30} " + " ".join(f"{len(pools[d]):6}" for d in days))
        matched_ids = defaultdict(set)
        for keyword in topic.keywords:
            try:
                query = parse(keyword)
            except QueryError as e:
                print(f"   - {keyword}\n       UNSUPPORTED: {e}")
                continue
            hits = {d: [p for p in pools[d] if query.matches(p)] for d in days}
            total = sum(len(v) for v in hits.values())
            per_day = total / len(days)
            flags = []
            if total == 0:
                flags.append("no hits")
            if per_day > HIGH_VOLUME_PER_DAY:
                flags.append(f"high volume, {per_day:.0f}/day: probably matches a different meaning; add categories or a narrower phrase")
            print(f"   - {keyword[:60]:60} " + " ".join(f"{len(hits[d]):6}" for d in days)
                  + (f"   [{'; '.join(flags)}]" if flags else ""))
            shown = 0
            for d in reversed(days):
                for paper in hits[d]:
                    if shown >= SAMPLE_TITLES:
                        break
                    print(f"         {paper.id} [{paper.primary_category}] {paper.title[:90]}")
                    shown += 1
                matched_ids[d].update(p.id for p in hits[d])
        if topic.uses_claude:
            pool_sizes = [len(pools[d]) - (len(matched_ids[d]) if topic.uses_keywords else 0) for d in days]
            avg = sum(pool_sizes) / len(days)
            hint = (" (over %d a day: consider keyword mode for this topic)" % CLAUDE_POOL_PER_DAY
                    if avg > CLAUDE_POOL_PER_DAY else "")
            print(f"   Claude review would read {avg:.0f} papers a day for this topic{hint}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
