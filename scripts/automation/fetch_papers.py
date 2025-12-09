#!/usr/bin/env python3
"""
Fetch papers from arXiv and Google Scholar based on keywords.
Generates daily digest in markdown format.
"""

import os
import sys
import yaml
import json
import time
import logging
import warnings
import arxiv
from datetime import datetime, timedelta
from pathlib import Path
from serpapi import GoogleSearch


def setup_logging(config):
    """Configure logging to capture both stdout and stderr (including warnings)."""
    research_root = Path(config['paths']['research_root']).expanduser().resolve()
    data_dir = research_root / config['paths']['data']
    log_file = data_dir / "fetch_papers.log"

    # Configure root logger to capture everything
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(log_file, mode='a'),
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Redirect warnings to the logging system
    logging.captureWarnings(True)

    # Also capture any warnings that bypass the logging system
    def warning_handler(message, category, filename, lineno, file=None, line=None):
        logging.warning(f"{category.__name__}: {message} ({filename}:{lineno})")

    warnings.showwarning = warning_handler

    return logging.getLogger(__name__)


class RateLimitAbort(Exception):
    """Raised when arXiv rate limiting persists after all retries exhausted."""
    def __init__(self, topic, keyword, query_num, total_queries):
        self.topic = topic
        self.keyword = keyword
        self.query_num = query_num
        self.total_queries = total_queries
        super().__init__(f"Rate limit abort at query {query_num}/{total_queries}: {keyword}")

def load_config():
    """Load configuration from config.yaml"""
    # Config stored outside plugin directory to survive updates
    config_path = Path.home() / ".claude" / "research-system-config" / "config.yaml"

    if not config_path.exists():
        raise FileNotFoundError(
            f"Config file not found at {config_path}\n"
            f"Please create ~/.claude/research-system-config/config.yaml\n"
            f"See the plugin's config/config.template.yaml for reference."
        )

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # Validate research_root path
    research_root = Path(config['paths']['research_root']).expanduser().resolve()
    if not research_root.exists():
        raise ValueError(f"research_root does not exist: {research_root}\nPlease check your config.yaml file.")
    if not research_root.is_dir():
        raise ValueError(f"research_root is not a directory: {research_root}\nPlease check your config.yaml file.")

    return config

def load_keywords(research_root):
    """Parse keywords.md and extract topics with their keywords"""
    # Keywords stored in research root's .research-data directory
    keywords_path = Path(research_root) / ".research-data" / "keywords.md"

    if not keywords_path.exists():
        raise FileNotFoundError(
            f"Keywords file not found at {keywords_path}\n"
            f"Please run /setup-research-automation to create keywords file."
        )

    topics = {}
    current_topic = None

    with open(keywords_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('## '):
                current_topic = line[3:].strip()
                topics[current_topic] = []
            elif line.startswith('- ') and current_topic:
                keyword = line[2:].strip()
                topics[current_topic].append(keyword)

    return topics

def load_seen_arxiv_papers(config):
    """Load previously seen arXiv papers from tracking file"""
    research_root = Path(config['paths']['research_root']).expanduser().resolve()
    data_dir = research_root / config['paths']['data']
    tracking_file = data_dir / ".seen_arxiv_papers.json"

    if tracking_file.exists():
        with open(tracking_file, 'r') as f:
            data = json.load(f)
            return set(data.get('urls', []))
    return set()

def save_seen_arxiv_papers(config, seen_urls):
    """Save seen arXiv papers to tracking file"""
    research_root = Path(config['paths']['research_root']).expanduser().resolve()
    data_dir = research_root / config['paths']['data']
    tracking_file = data_dir / ".seen_arxiv_papers.json"

    with open(tracking_file, 'w') as f:
        json.dump({
            'urls': list(seen_urls),
            'last_updated': datetime.now().isoformat()
        }, f, indent=2)

def search_arxiv(keywords, config, max_results=10, days_back=1, topic_name=None, global_query_offset=0, total_global_queries=0):
    """Search arXiv for papers matching keywords.

    Args:
        keywords: List of search keywords
        config: Configuration dict
        max_results: Max results per keyword
        days_back: Only include papers from last N days
        topic_name: Name of current topic (for error reporting)
        global_query_offset: Number of queries already completed in this run
        total_global_queries: Total queries planned for entire run

    Returns:
        List of paper dicts

    Raises:
        RateLimitAbort: If 429 errors persist after all retries exhausted
    """
    # Search each keyword separately and combine results
    # This prevents overly broad OR queries
    all_papers = []
    seen_urls = set()

    # Load previously seen papers to avoid duplicates across runs
    previously_seen = load_seen_arxiv_papers(config)

    # 429 retry delays: 1 minute, 5 minutes, 10 minutes
    RATE_LIMIT_DELAYS = [60, 300, 600]

    # Create a single client instance to reuse across all queries
    # This is the recommended approach per arxiv.py documentation
    client = arxiv.Client()

    for i, keyword in enumerate(keywords, 1):
        global_query_num = global_query_offset + i
        print(f"  [arXiv {i}/{len(keywords)}] Searching: {keyword[:80]}...", flush=True)

        # Respect arXiv rate limit: 10 seconds between requests to avoid 429 errors
        if i > 1:
            time.sleep(10)

        # Track if we succeeded for this keyword
        query_succeeded = False

        # Retry logic for 503 errors (quick retries)
        max_503_retries = 3
        retry_delay_503 = 5  # Start with 5 seconds

        for attempt_503 in range(max_503_retries):
            try:
                # Use the keyword as-is (assumes each line is a complete search)
                search = arxiv.Search(
                    query=keyword,
                    max_results=max_results,
                    sort_by=arxiv.SortCriterion.SubmittedDate
                )

                for result in client.results(search):
                    # Skip duplicates (both from this run and previous runs)
                    if result.entry_id in seen_urls or result.entry_id in previously_seen:
                        continue

                    # Only include papers from last N days
                    days_old = (datetime.now() - result.published.replace(tzinfo=None)).days
                    if days_old <= days_back:
                        all_papers.append({
                            'title': result.title,
                            'authors': ', '.join([author.name for author in result.authors]),
                            'year': result.published.year,
                            'abstract': result.summary.replace('\n', ' '),
                            'url': result.entry_id,
                            'pdf_url': result.pdf_url,
                            'source': 'arXiv'
                        })
                        seen_urls.add(result.entry_id)

                # If successful, break out of retry loop
                query_succeeded = True
                break

            except Exception as e:
                error_str = str(e)

                # Handle 429 rate limit errors with longer backoff
                if '429' in error_str:
                    # Try the 429 retry sequence: 1min, 5min, 10min
                    for retry_num, delay in enumerate(RATE_LIMIT_DELAYS):
                        delay_mins = delay // 60
                        print(f"    429 rate limit, waiting {delay_mins} minute(s) (attempt {retry_num + 1}/{len(RATE_LIMIT_DELAYS)})...", flush=True)
                        time.sleep(delay)

                        try:
                            search = arxiv.Search(
                                query=keyword,
                                max_results=max_results,
                                sort_by=arxiv.SortCriterion.SubmittedDate
                            )

                            for result in client.results(search):
                                if result.entry_id in seen_urls or result.entry_id in previously_seen:
                                    continue
                                days_old = (datetime.now() - result.published.replace(tzinfo=None)).days
                                if days_old <= days_back:
                                    all_papers.append({
                                        'title': result.title,
                                        'authors': ', '.join([author.name for author in result.authors]),
                                        'year': result.published.year,
                                        'abstract': result.summary.replace('\n', ' '),
                                        'url': result.entry_id,
                                        'pdf_url': result.pdf_url,
                                        'source': 'arXiv'
                                    })
                                    seen_urls.add(result.entry_id)

                            # Success after retry
                            print(f"    Retry successful after {delay_mins} minute wait", flush=True)
                            query_succeeded = True
                            break

                        except Exception as retry_e:
                            if '429' not in str(retry_e):
                                # Different error, re-raise
                                raise retry_e
                            # Still 429, continue to next delay
                            continue

                    if query_succeeded:
                        break  # Break out of 503 retry loop too

                    # All 429 retries exhausted - save what we have and abort
                    all_seen = previously_seen.union(seen_urls)
                    save_seen_arxiv_papers(config, all_seen)

                    raise RateLimitAbort(
                        topic=topic_name or "Unknown",
                        keyword=keyword,
                        query_num=global_query_num,
                        total_queries=total_global_queries
                    )

                # Handle 503 errors with quick retries
                elif '503' in error_str and attempt_503 < max_503_retries - 1:
                    print(f"    503 error, retrying in {retry_delay_503}s (attempt {attempt_503 + 1}/{max_503_retries})...", flush=True)
                    time.sleep(retry_delay_503)
                    retry_delay_503 *= 2  # Exponential backoff
                else:
                    # Unknown error or final 503 attempt, raise
                    raise

    # Save all seen URLs (merge with previously seen)
    all_seen = previously_seen.union(seen_urls)
    save_seen_arxiv_papers(config, all_seen)

    return all_papers

def load_seen_papers(config):
    """Load previously seen Google Scholar papers from tracking file"""
    research_root = Path(config['paths']['research_root']).expanduser().resolve()
    data_dir = research_root / config['paths']['data']
    tracking_file = data_dir / ".seen_scholar_papers.json"

    if tracking_file.exists():
        with open(tracking_file, 'r') as f:
            data = json.load(f)
            return set(data.get('urls', []))
    return set()

def save_seen_papers(config, seen_urls):
    """Load previously seen Google Scholar papers from tracking file"""
    research_root = Path(config['paths']['research_root']).expanduser().resolve()
    data_dir = research_root / config['paths']['data']
    tracking_file = data_dir / ".seen_scholar_papers.json"

    with open(tracking_file, 'w') as f:
        json.dump({
            'urls': list(seen_urls),
            'last_updated': datetime.now().isoformat()
        }, f, indent=2)

def search_google_scholar(keywords, config, api_key, max_results=5, days_back=7):
    """Search Google Scholar for papers matching keywords"""
    import re

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

    for i, keyword in enumerate(keywords, 1):
        print(f"  [Scholar {i}/{len(keywords)}] Searching: {keyword[:80]}...", flush=True)

        # Respect SerpAPI rate limit: free tier allows 50 searches/hour
        # Add 2 second delay to be conservative (allows ~1800 searches/hour max)
        if i > 1:
            time.sleep(2)

        params = {
            "engine": "google_scholar",
            "q": keyword,  # Each line is searched individually
            "api_key": api_key,
            "num": max_results,
            "as_ylo": start_date.year,  # Year low
            "scisbd": 1  # Sort by date (most recent first)
        }

        search = GoogleSearch(params)
        results = search.get_dict()

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

def generate_digest(topics_papers, output_path, rate_limit_note=None, total_keywords=0):
    """Generate markdown digest from papers grouped by topic.

    Args:
        topics_papers: Dict mapping topic names to lists of paper dicts
        output_path: Path to write the digest file
        rate_limit_note: Optional note about rate limiting to include at top of digest
        total_keywords: Total number of keywords searched across all topics
    """
    today = datetime.now().strftime('%Y-%m-%d')

    content = [f"# Research Digest - {today}\n"]

    # Add rate limit warning if present
    if rate_limit_note:
        content.append(f"\n> **Note:** {rate_limit_note}\n")

    # Check if all searches returned 0 results
    total_papers = sum(len(papers) for papers in topics_papers.values())
    if total_papers == 0:
        content.append("\n**No papers found today.**\n")
        content.append("\nAll searches returned 0 results. This can happen when:\n")
        content.append("- No new papers were published matching your keywords\n")
        content.append("- arXiv had no new submissions in your research areas\n")
        content.append("- The `days_back` setting is filtering out older papers\n")
        content.append(f"\nSearched {total_keywords} keywords across {len(topics_papers)} topics.\n")

    for topic, papers in topics_papers.items():
        if not papers:
            continue

        content.append(f"\n## {topic}\n")

        for paper in papers:
            content.append(f"\n### {paper['title']}\n")
            content.append(f"**Authors:** {paper['authors']}  \n")
            content.append(f"**Year:** {paper['year']}")

            if paper['source'] == 'Google Scholar' and paper.get('citations'):
                content.append(f" | **Citations:** {paper['citations']}")

            content.append("  \n")

            # Add abstract or snippet
            if 'abstract' in paper:
                # Truncate long abstracts
                abstract = paper['abstract'][:300] + '...' if len(paper['abstract']) > 300 else paper['abstract']
                content.append(f"**Abstract:** {abstract}\n")
            elif 'snippet' in paper:
                content.append(f"**Snippet:** {paper['snippet']}\n")

            # Add links
            links = [f"[View Paper]({paper['url']})"]
            if 'pdf_url' in paper:
                links.append(f"[PDF]({paper['pdf_url']})")
            content.append(' | '.join(links) + '\n')
            content.append('\n---\n')

    # Write to file
    with open(output_path, 'w') as f:
        f.write(''.join(content))

    return len([p for papers in topics_papers.values() for p in papers])

def main():
    # Load configuration
    config = load_config()

    # Setup logging to capture warnings and errors
    logger = setup_logging(config)
    logger.info("Starting fetch_papers.py")

    # Load keywords by topic
    research_root = config['paths']['research_root']
    topics = load_keywords(research_root)

    print(f"Found {len(topics)} topics with keywords", flush=True)

    # Calculate total queries for progress tracking
    total_arxiv_queries = sum(len(keywords) for keywords in topics.values())

    # Determine which sources to search
    is_weekly = datetime.now().weekday() == 6  # Sunday = weekly Google Scholar search

    # Fetch papers for each topic
    topics_papers = {}
    rate_limit_note = None
    global_query_offset = 0

    for topic_num, (topic, keywords) in enumerate(topics.items(), 1):
        print(f"\n[{topic_num}/{len(topics)}] Searching for '{topic}' ({len(keywords)} keywords)...", flush=True)
        papers = []

        # Always search arXiv (daily)
        try:
            arxiv_days = config['arxiv'].get('days_back', 1)  # Default to 1 day
            arxiv_papers = search_arxiv(
                keywords,
                config,
                config['arxiv']['max_results'],
                arxiv_days,
                topic_name=topic,
                global_query_offset=global_query_offset,
                total_global_queries=total_arxiv_queries
            )
            papers.extend(arxiv_papers)
            print(f"  Found {len(arxiv_papers)} papers from arXiv", flush=True)
            global_query_offset += len(keywords)

        except RateLimitAbort as e:
            print(f"  ✗ arXiv rate limit exceeded after retries. Aborting remaining queries.", flush=True)
            rate_limit_note = (
                f"arXiv rate limiting encountered at topic \"{e.topic}\" "
                f"(query {e.query_num} of {e.total_queries}). "
                f"Papers from remaining topics may be incomplete."
            )
            topics_papers[topic] = papers
            break  # Exit the topic loop entirely

        except Exception as e:
            print(f"  Error searching arXiv: {e}", flush=True)
            global_query_offset += len(keywords)

        # Search Google Scholar (weekly only)
        if is_weekly:
            try:
                scholar_papers = search_google_scholar(
                    keywords,
                    config,
                    config['serpapi']['api_key'],
                    config['google_scholar']['max_results'],
                    config['google_scholar']['search_days']
                )
                papers.extend(scholar_papers)
                print(f"  Found {len(scholar_papers)} papers from Google Scholar", flush=True)
            except Exception as e:
                print(f"  Error searching Google Scholar: {e}", flush=True)

        topics_papers[topic] = papers

    # Generate digest
    today = datetime.now().strftime('%Y-%m-%d')
    digest_path = Path(config['paths']['research_root']) / config['paths']['daily_digests'] / f"{today}.md"

    total_papers = generate_digest(topics_papers, digest_path, rate_limit_note=rate_limit_note, total_keywords=total_arxiv_queries)

    if rate_limit_note:
        print(f"\n⚠ Generated partial digest with {total_papers} papers: {digest_path}", flush=True)
        print(f"  {rate_limit_note}", flush=True)
    else:
        print(f"\n✓ Generated digest with {total_papers} papers: {digest_path}", flush=True)

if __name__ == "__main__":
    main()
