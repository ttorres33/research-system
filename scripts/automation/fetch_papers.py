#!/usr/bin/env python3
"""
Fetch papers from arXiv and Google Scholar and write the daily digest.

arXiv: one OAI-PMH harvest of everything new since the last run (see arxiv_harvest.py),
then per-topic matching. A topic in keyword mode gets whole-word keyword matches; a topic
in Claude mode gets its new papers recorded as candidates for the Claude review that
/generate-research-digest runs; "both" does both. Google Scholar runs on Sundays, by
keyword, unchanged.
"""

import argparse
import json
import logging
import re
import sys
import time
import warnings
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import serpapi

from arxiv_harvest import HarvestError, HarvestStore, harvest, utc_today
from config import data_dir as config_data_dir, load_config
from digest import TopicSection, has_content, paper_entry, write_digest
from keyword_match import QueryError, parse as parse_keyword
from topics import load_topics

CANDIDATES_DIR = "claude-candidates"
CANDIDATES_KEEP_DAYS = 7


def setup_logging():
    """Send log lines and captured warnings to stdout.

    The crontab entry redirects stdout and stderr into fetch_papers.log, so the
    script must not also write to that file itself or every line lands twice.
    urllib3 is held at WARNING so its per-request chatter stays out of the log.
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    logging.getLogger('urllib3').setLevel(logging.WARNING)

    logging.captureWarnings(True)

    def warning_handler(message, category, filename, lineno, file=None, line=None):
        logging.warning(f"{category.__name__}: {message} ({filename}:{lineno})")

    warnings.showwarning = warning_handler

    return logging.getLogger(__name__)


def load_seen_arxiv_papers(config):
    """Load previously seen arXiv papers from tracking file"""
    tracking_file = config_data_dir(config) / ".seen_arxiv_papers.json"

    if tracking_file.exists():
        with open(tracking_file, 'r') as f:
            data = json.load(f)
            return set(data.get('urls', []))
    return set()


def save_seen_arxiv_papers(config, seen_urls):
    """Save seen arXiv papers to tracking file"""
    tracking_file = config_data_dir(config) / ".seen_arxiv_papers.json"

    with open(tracking_file, 'w') as f:
        json.dump({
            'urls': list(seen_urls),
            'last_updated': datetime.now().isoformat()
        }, f, indent=2)


def load_seen_papers(config):
    """Load previously seen Google Scholar papers from tracking file"""
    tracking_file = config_data_dir(config) / ".seen_scholar_papers.json"

    if tracking_file.exists():
        with open(tracking_file, 'r') as f:
            data = json.load(f)
            return set(data.get('urls', []))
    return set()


def save_seen_papers(config, seen_urls):
    """Save seen Google Scholar papers to tracking file"""
    tracking_file = config_data_dir(config) / ".seen_scholar_papers.json"

    with open(tracking_file, 'w') as f:
        json.dump({
            'urls': list(seen_urls),
            'last_updated': datetime.now().isoformat()
        }, f, indent=2)


def search_google_scholar(keywords, config, api_key, max_results=5, days_back=7):
    """Search Google Scholar for papers matching keywords"""
    # Search each keyword separately and combine results
    # This prevents overly broad OR queries
    all_papers = []
    seen_urls = set()

    # Load previously seen papers to avoid duplicates across runs
    previously_seen = load_seen_papers(config)
    print(f"  [DEBUG] Loaded {len(previously_seen)} previously seen Google Scholar URLs", flush=True)

    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)

    client = serpapi.Client(api_key=api_key)

    for i, keyword in enumerate(keywords, 1):
        print(f"  [Scholar {i}/{len(keywords)}] Searching: {keyword[:80]}...", flush=True)

        # Respect SerpAPI rate limit: free tier allows 50 searches/hour
        # Add 2 second delay to be conservative (allows ~1800 searches/hour max)
        if i > 1:
            time.sleep(2)

        params = {
            "engine": "google_scholar",
            "q": keyword,  # Each line is searched individually
            "num": max_results,
            "as_ylo": start_date.year,  # Year low
            "scisbd": 1  # Sort by date (most recent first)
        }

        results = client.search(params)

        if 'organic_results' in results:
            for result in results['organic_results']:
                # Skip duplicates (both from this run and previous runs)
                url = result.get('link', '')
                if url in seen_urls or url in previously_seen:
                    continue

                # Get publication info
                pub_info = result.get('publication_info', {})
                summary = pub_info.get('summary', '') if pub_info else ''

                # Extract year from summary
                year_match = re.search(r'\b(20\d{2})\b', summary)
                year = year_match.group(1) if year_match else 'Unknown'

                # Add the paper
                all_papers.append({
                    'title': result.get('title', 'No title'),
                    'authors': pub_info.get('authors', [{}])[0].get('name', 'Unknown') if pub_info.get('authors') else 'Unknown',
                    'year': year,
                    'snippet': result.get('snippet', ''),
                    'url': url,
                    'citations': result.get('inline_links', {}).get('cited_by', {}).get('total', 0),
                    'source': 'Google Scholar'
                })
                seen_urls.add(url)

    # Save all seen URLs (merge with previously seen)
    all_seen = previously_seen.union(seen_urls)
    print(f"  [DEBUG] Saving {len(all_seen)} total URLs ({len(previously_seen)} previous + {len(seen_urls)} new)", flush=True)
    print(f"  [DEBUG] Filtered out {len(previously_seen.intersection(seen_urls))} duplicate URLs during search", flush=True)
    save_seen_papers(config, all_seen)

    return all_papers


def today_is_sunday():
    return datetime.now().weekday() == 6


def scrub_secrets(message):
    """Hide an API key that a library error message may carry in a URL."""
    return re.sub(r'api_key=[^&\s]+', 'api_key=***', message)


def compile_keywords(topic):
    """Parse a topic's keywords. Returns (queries, problems); problems are strings
    naming the topic and the keyword, for the log and the digest note."""
    queries, problems = [], []
    for keyword in topic.keywords:
        try:
            queries.append(parse_keyword(keyword))
        except QueryError as e:
            problems.append(f'topic "{topic.name}", keyword {keyword!r}: {e}')
    return queries, problems


def keyword_matches(topic, new_papers, queries, excluded_urls):
    """(pool, matched): the topic's new papers by category, and those a keyword matches."""
    pool = [p for p in new_papers if p.in_categories(topic.categories) and p.url not in excluded_urls]
    matched = [p for p in pool if topic.uses_keywords and any(q.matches(p) for q in queries)]
    return pool, matched


def claude_pool(new_papers, claude_topics, excluded_urls):
    """[(paper, [eligible topic names])]: every unclaimed new paper that falls in the
    categories of at least one Claude-mode topic, once. Claude reads each paper once and
    may keep it under any topic it is eligible for."""
    candidates = []
    for paper in new_papers:
        if paper.url in excluded_urls:
            continue
        eligible = [t.name for t in claude_topics if paper.in_categories(t.categories)]
        if eligible:
            candidates.append((paper, eligible))
    return candidates


def looking_for_text(topic, config):
    """The review brief for a Claude-mode topic; falls back to the config's filter criteria."""
    if topic.looking_for:
        return topic.looking_for
    filt = config.get('filter') or {}
    parts = [f'Papers relevant to the topic "{topic.name}".']
    if filt.get('relevance_criteria'):
        parts.append(filt['relevance_criteria'])
    if filt.get('relevant_topics'):
        parts.append("Relevant topics: " + ", ".join(filt['relevant_topics']) + ".")
    return " ".join(parts)


def load_unprocessed_candidates(config, today):
    """{paper id: [topic names]} from today's candidates file when the Claude review has not run.

    A second run on the same day must not lose them: the harvest store already knows
    the papers, so they would not come back as new, and they are already marked seen.
    """
    path = config_data_dir(config) / CANDIDATES_DIR / f"{today}.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
    except ValueError as e:
        logging.getLogger(__name__).warning("Candidates file %s unreadable (%s); ignored", path, e)
        return {}
    if data.get("processed_at"):
        return {}
    return {item.get("id"): list(item.get("topics", [])) for item in data.get("papers", []) if item.get("id")}


def write_candidates(config, today, store, claude_topics, candidates, digest_path):
    """Record the Claude review's input for /generate-research-digest.

    `candidates` is a list of (Paper, [eligible topic names]). Every Claude-mode topic's
    brief is included once; paper bodies stay in the harvest files. Returns the path, or
    None when there is nothing to review.
    """
    if not candidates:
        return None
    candidates_dir = config_data_dir(config) / CANDIDATES_DIR
    candidates_dir.mkdir(parents=True, exist_ok=True)
    filt = config.get('filter') or {}
    payload = {
        'date': today,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'data_dir': str(store.data_dir),
        'digest_path': str(digest_path),
        'exclude': list(filt.get('irrelevant_topics') or []),
        'topics': [
            {'name': t.name, 'looking_for': looking_for_text(t, config), 'keywords': list(t.keywords)}
            for t in claude_topics
        ],
        'papers': [{'id': paper.id, 'topics': names} for paper, names in candidates],
    }
    path = candidates_dir / f"{today}.json"
    path.write_text(json.dumps(payload, indent=2))
    return path


def prune_candidates(config, today_utc, keep_days=CANDIDATES_KEEP_DAYS):
    candidates_dir = config_data_dir(config) / CANDIDATES_DIR
    if not candidates_dir.exists():
        return
    cutoff = today_utc - timedelta(days=keep_days)
    for path in candidates_dir.glob("*.json"):
        try:
            if datetime.strptime(path.stem, "%Y-%m-%d").date() < cutoff:
                path.unlink()
        except ValueError:
            continue


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Harvest arXiv, search Google Scholar on Sundays, write today's digest.")
    parser.add_argument("--force", action="store_true",
                        help="rebuild today's digest even though one with papers already exists")
    return parser.parse_args(argv)


def main(argv=None):
    opts = parse_args(argv)
    config = load_config()
    logger = setup_logging()
    logger.info("Starting fetch_papers.py")

    if config.get('arxiv'):
        logger.warning("config.yaml: the 'arxiv' section (max_results, days_back) is no longer used; "
                       "arXiv is harvested in full and matched per topic")

    research_root = Path(config['paths']['research_root']).expanduser().resolve()
    topics = load_topics(config_data_dir(config) / "keywords.md")
    for topic in topics:
        for warning in topic.warnings:
            logger.warning('topic "%s": %s', topic.name, warning)
    print(f"Found {len(topics)} topics", flush=True)

    today = datetime.now().strftime('%Y-%m-%d')
    today_utc = utc_today()
    is_weekly = today_is_sunday()
    notes = []

    digest_path = research_root / config['paths']['daily_digests'] / f"{today}.md"
    if has_content(digest_path) and not opts.force:
        print(f"\nToday's digest already has papers: {digest_path}", flush=True)
        print("  A second run would rebuild it from scratch, and papers already recorded as seen would not "
              "come back. Nothing was changed. Run /generate-research-digest to complete a pending Claude "
              "review, or rerun with --force to rebuild the digest anyway.", flush=True)
        return 1
    carried = load_unprocessed_candidates(config, today)

    # --- arXiv harvest ---------------------------------------------------------
    store = HarvestStore(config_data_dir(config))
    from_date, cap_note = store.window_start(today_utc)
    if cap_note:
        notes.append(f"arXiv catch-up was capped: {cap_note}.")
    new_papers = []
    harvest_failed = None
    print(f"\nHarvesting arXiv via OAI-PMH from {from_date.isoformat()}...", flush=True)
    try:
        records = harvest(from_date)
    except HarvestError as e:
        harvest_failed = str(e)
        print(f"  ✗ arXiv harvest failed: {e}", flush=True)
        notes.append(f"arXiv harvest failed ({e}). The next run will catch up from {from_date.isoformat()}.")
    else:
        new_papers = [p for p in records if p.is_new(today_utc)]
        new_papers = store.add(new_papers)
        if records:
            latest = max(p.datestamp for p in records)
            store.set_last_datestamp(date.fromisoformat(latest))
        removed = store.prune(today_utc)
        print(f"  {len(records)} records since {from_date.isoformat()}; {len(new_papers)} new papers not seen before"
              + (f"; pruned {len(removed)} old harvest file(s)" if removed else ""), flush=True)
    prune_candidates(config, today_utc)

    # --- keyword pass: a keyword topic claims what its keywords match, first topic wins ---
    previously_seen = load_seen_arxiv_papers(config)
    claimed = set()
    sections = []
    claude_topics = []
    scholar_failures = 0
    scholar_skipped = 0
    keyword_problems = []

    for topic_num, topic in enumerate(topics, 1):
        print(f"\n[{topic_num}/{len(topics)}] '{topic.name}' (mode: {topic.mode}, "
              f"categories: {', '.join(topic.categories) or 'all'}, {len(topic.keywords)} keywords)", flush=True)
        queries, problems = compile_keywords(topic)
        for problem in problems:
            logger.warning("keyword skipped: %s", problem)
        keyword_problems.extend(problems)

        pool, matched = keyword_matches(topic, new_papers, queries, previously_seen | claimed)
        claimed.update(p.url for p in matched)
        entries = [paper_entry(p) for p in matched]
        if topic.uses_claude:
            claude_topics.append(topic)
        if harvest_failed is None:
            print(f"  arXiv: {len(pool)} new papers in the topic's categories, {len(matched)} keyword matches", flush=True)

        topic_notes = []
        if is_weekly:
            if not topic.keywords:
                scholar_skipped += 1
                topic_notes.append("Google Scholar skipped for this topic: no keywords")
                print("  Google Scholar skipped: no keywords", flush=True)
            else:
                try:
                    scholar_papers = search_google_scholar(
                        topic.keywords,
                        config,
                        config['serpapi']['api_key'],
                        config['google_scholar']['max_results'],
                        config['google_scholar']['search_days']
                    )
                    entries.extend(scholar_papers)
                    print(f"  Found {len(scholar_papers)} papers from Google Scholar", flush=True)
                except Exception as e:
                    print(f"  Error searching Google Scholar: {type(e).__name__}: {scrub_secrets(str(e))}", flush=True)
                    scholar_failures += 1

        sections.append(TopicSection(topic.name, entries, 0, topic_notes))

    # --- Claude pool: every unclaimed new paper in any Claude topic's categories, once ---
    candidates = claude_pool(new_papers, claude_topics, previously_seen | claimed)
    if carried:
        by_id = {paper.id: (paper, names) for paper, names in candidates}
        known = {p.id: p for papers in store.load().values() for p in papers}
        claude_names = [t.name for t in claude_topics]
        for pid, names in carried.items():
            names = [n for n in names if n in claude_names]
            if not names or pid not in known:
                continue
            if pid in by_id:
                merged = by_id[pid][1] + [n for n in names if n not in by_id[pid][1]]
                by_id[pid] = (by_id[pid][0], merged)
            else:
                by_id[pid] = (known[pid], names)
        candidates = list(by_id.values())
    for section in sections:
        section.pending = sum(1 for _, names in candidates if section.name in names)
    if claude_topics and harvest_failed is None:
        print(f"\nClaude review: {len(candidates)} papers to read once, eligible for "
              + ", ".join(f"'{s.name}' ({s.pending})" for s in sections if s.pending), flush=True)
    newly_seen = claimed | {paper.url for paper, _ in candidates}

    # --- digest ----------------------------------------------------------------
    if keyword_problems:
        notes.append("Some keywords use syntax the matcher does not support and were skipped: "
                     + "; ".join(keyword_problems) + ".")
    if is_weekly and scholar_failures:
        notes.append(f"Google Scholar failed for {scholar_failures} of {len(topics)} topics; see fetch_papers.log.")
    elif is_weekly and harvest_failed:
        notes.append("Google Scholar results are unaffected.")
    note = " ".join(notes) if notes else None

    if harvest_failed:
        empty_message = "arXiv could not be harvested; see the note above."
    else:
        empty_message = f"The harvest found {len(new_papers)} new arXiv papers; none matched a topic."

    # The digest is written before the tracking files: if it fails, nothing is marked seen
    # and the papers come back next run instead of vanishing.
    total_papers = write_digest(sections, digest_path, note=note, empty_message=empty_message, today=today)
    save_seen_arxiv_papers(config, previously_seen | newly_seen)
    candidates_path = write_candidates(config, today, store, claude_topics, candidates, digest_path)

    marker = "⚠" if note else "✓"
    print(f"\n{marker} Generated digest with {total_papers} papers: {digest_path}", flush=True)
    if candidates_path:
        print(f"  {len(candidates)} papers await the Claude review in {candidates_path}; run /generate-research-digest", flush=True)
    if scholar_skipped:
        print(f"  Google Scholar skipped for {scholar_skipped} topic(s) without keywords", flush=True)
    if note:
        print(f"  {note}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
