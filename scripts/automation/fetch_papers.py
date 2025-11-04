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
import arxiv
from datetime import datetime, timedelta
from pathlib import Path
from serpapi import GoogleSearch

def load_config():
    """Load configuration from config.yaml"""
    # Plugin structure: scripts/automation/script.py -> config/config.yaml
    script_dir = Path(__file__).parent
    plugin_dir = script_dir.parent.parent  # Go up two levels to plugin root
    config_path = plugin_dir / "config" / "config.yaml"

    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def load_keywords():
    """Parse keywords.md and extract topics with their keywords"""
    # Plugin structure: scripts/automation/script.py -> config/keywords.md
    script_dir = Path(__file__).parent
    plugin_dir = script_dir.parent.parent  # Go up two levels to plugin root
    keywords_path = plugin_dir / "config" / "keywords.md"

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

def load_seen_arxiv_papers():
    """Load previously seen arXiv papers from tracking file"""
    script_dir = Path(__file__).parent
    tracking_file = script_dir / ".seen_arxiv_papers.json"

    if tracking_file.exists():
        with open(tracking_file, 'r') as f:
            data = json.load(f)
            return set(data.get('urls', []))
    return set()

def save_seen_arxiv_papers(seen_urls):
    """Save seen arXiv papers to tracking file"""
    script_dir = Path(__file__).parent
    tracking_file = script_dir / ".seen_arxiv_papers.json"

    with open(tracking_file, 'w') as f:
        json.dump({
            'urls': list(seen_urls),
            'last_updated': datetime.now().isoformat()
        }, f, indent=2)

def search_arxiv(keywords, max_results=10, days_back=1):
    """Search arXiv for papers matching keywords"""
    # Search each keyword separately and combine results
    # This prevents overly broad OR queries
    all_papers = []
    seen_urls = set()

    # Load previously seen papers to avoid duplicates across runs
    previously_seen = load_seen_arxiv_papers()

    for i, keyword in enumerate(keywords, 1):
        print(f"  [arXiv {i}/{len(keywords)}] Searching: {keyword[:80]}...", flush=True)

        # Respect arXiv rate limit: 3 seconds between requests
        if i > 1:
            time.sleep(3)

        # Retry logic for 503 errors
        max_retries = 3
        retry_delay = 5  # Start with 5 seconds

        for attempt in range(max_retries):
            try:
                # Use the keyword as-is (assumes each line is a complete search)
                search = arxiv.Search(
                    query=keyword,
                    max_results=max_results,
                    sort_by=arxiv.SortCriterion.SubmittedDate
                )

                for result in search.results():
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
                break

            except Exception as e:
                if '503' in str(e) and attempt < max_retries - 1:
                    print(f"    503 error, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})...", flush=True)
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    # If not 503 or final attempt, raise the error
                    raise

    # Save all seen URLs (merge with previously seen)
    all_seen = previously_seen.union(seen_urls)
    save_seen_arxiv_papers(all_seen)

    return all_papers

def load_seen_papers():
    """Load previously seen Google Scholar papers from tracking file"""
    script_dir = Path(__file__).parent
    tracking_file = script_dir / ".seen_scholar_papers.json"

    if tracking_file.exists():
        with open(tracking_file, 'r') as f:
            data = json.load(f)
            return set(data.get('urls', []))
    return set()

def save_seen_papers(seen_urls):
    """Save seen Google Scholar papers to tracking file"""
    script_dir = Path(__file__).parent
    tracking_file = script_dir / ".seen_scholar_papers.json"

    with open(tracking_file, 'w') as f:
        json.dump({
            'urls': list(seen_urls),
            'last_updated': datetime.now().isoformat()
        }, f, indent=2)

def search_google_scholar(keywords, api_key, max_results=5, days_back=7):
    """Search Google Scholar for papers matching keywords"""
    import re

    # Search each keyword separately and combine results
    # This prevents overly broad OR queries
    all_papers = []
    seen_urls = set()

    # Load previously seen papers to avoid duplicates across runs
    previously_seen = load_seen_papers()
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
    save_seen_papers(all_seen)

    return all_papers

def generate_digest(topics_papers, output_path):
    """Generate markdown digest from papers grouped by topic"""
    today = datetime.now().strftime('%Y-%m-%d')

    content = [f"# Research Digest - {today}\n"]

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

    # Load keywords by topic
    topics = load_keywords()

    print(f"Found {len(topics)} topics with keywords", flush=True)

    # Determine which sources to search
    is_weekly = datetime.now().weekday() == 6  # Sunday = weekly Google Scholar search

    # Fetch papers for each topic
    topics_papers = {}

    for topic_num, (topic, keywords) in enumerate(topics.items(), 1):
        print(f"\n[{topic_num}/{len(topics)}] Searching for '{topic}' ({len(keywords)} keywords)...", flush=True)
        papers = []

        # Always search arXiv (daily)
        try:
            arxiv_days = config['arxiv'].get('days_back', 1)  # Default to 1 day
            arxiv_papers = search_arxiv(keywords, config['arxiv']['max_results'], arxiv_days)
            papers.extend(arxiv_papers)
            print(f"  Found {len(arxiv_papers)} papers from arXiv", flush=True)
        except Exception as e:
            print(f"  Error searching arXiv: {e}", flush=True)

        # Search Google Scholar (weekly only)
        if is_weekly:
            try:
                scholar_papers = search_google_scholar(
                    keywords,
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

    total_papers = generate_digest(topics_papers, digest_path)

    print(f"\n✓ Generated digest with {total_papers} papers: {digest_path}", flush=True)

if __name__ == "__main__":
    main()
