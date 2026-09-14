"""Harvest new arXiv papers through arXiv's OAI-PMH interface.

Why OAI-PMH and not the search API (export.arxiv.org/api/query): the search API refuses
whole runs with a capacity 429 ("Rate exceeded.") that no client-side pacing avoids, and
it stems query words, which put off-topic papers in the digest. OAI-PMH returns every
new paper with abstract, categories and version list in two to five requests a day.

Rules honoured here:
- one request every three seconds and an identifying User-Agent (arXiv terms of use)
- OAI errors arrive inside an HTTP 200 body, so every page is checked for <error>
- a paper is "new" when it has exactly one version and that version is recent
- harvest state and the saved per-day files live under {data_dir}, see HarvestStore
"""

import json
import logging
import time
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

OAI_BASE = "https://oaipmh.arxiv.org/oai"
METADATA_PREFIX = "arXivRaw"
NS = {
    "oai": "http://www.openarchives.org/OAI/2.0/",
    "raw": "http://arxiv.org/OAI/arXivRaw/",
}
REQUEST_SPACING_SECONDS = 3.0
RETRY_WAITS_SECONDS = (30, 120, 300)
REQUEST_TIMEOUT_SECONDS = 120
NEW_PAPER_MAX_AGE_DAYS = 60
HARVEST_KEEP_DAYS = 7
CATCH_UP_CAP_DAYS = 14
MAX_PAGES = 500          # a day is 2-5 pages; a 14-day catch-up about 40. Guards against a token loop.
STATE_FILE = ".arxiv_harvest_state.json"
HARVEST_DIR = "arxiv-harvest"


def _plugin_version():
    try:
        manifest = Path(__file__).resolve().parents[2] / ".claude-plugin" / "plugin.json"
        return json.loads(manifest.read_text())["version"]
    except (OSError, ValueError, KeyError):
        return "dev"


USER_AGENT = f"research-system/{_plugin_version()} (+https://github.com/ttorres33/research-system)"


class HarvestError(Exception):
    """The harvest could not complete. Keep the harvest state; the next run catches up."""


class _OAIError(Exception):
    """An <error> element in an OAI-PMH response body."""

    def __init__(self, code, message):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def utc_today():
    return datetime.now(timezone.utc).date()


@dataclass
class Paper:
    id: str
    title: str
    abstract: str
    authors: str          # the author string exactly as arXiv gives it
    categories: list      # primary category first, then cross-lists
    comments: str
    versions: list        # ISO 8601 UTC timestamps, first version first
    datestamp: str        # the record's OAI datestamp, YYYY-MM-DD (UTC)

    @property
    def primary_category(self):
        return self.categories[0] if self.categories else ""

    @property
    def first_version_date(self):
        return datetime.fromisoformat(self.versions[0]) if self.versions else None

    @property
    def year(self):
        first = self.first_version_date
        return first.year if first else None

    @property
    def url(self):
        # Same string the old search API produced as entry_id for a first version,
        # so .seen_arxiv_papers.json and old digest links carry over.
        return f"http://arxiv.org/abs/{self.id}v1"

    @property
    def pdf_url(self):
        return f"https://arxiv.org/pdf/{self.id}v1"

    def is_new(self, as_of, max_age_days=NEW_PAPER_MAX_AGE_DAYS):
        """True for a first-version-only paper submitted within max_age_days of as_of.

        Exactly one version reproduced the Atom feed's new/cross-list labels 32 of 32 in
        the 2026-09-14 check. The age cap drops old single-version papers that only got
        a metadata edit or a new cross-list, while keeping papers held in moderation.
        """
        if len(self.versions) != 1:
            return False
        first = self.first_version_date
        return first is not None and (as_of - first.date()).days <= max_age_days

    def in_categories(self, categories):
        """True when no categories are given, or any of the paper's categories is listed."""
        return not categories or bool(set(self.categories) & set(categories))

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        return cls(**data)


def _text(element):
    return " ".join((element.text or "").split()) if element is not None else ""


def _paper_from(meta, datestamp):
    paper_id = _text(meta.find("raw:id", NS))
    if not paper_id:
        return None
    versions = []
    for version in meta.findall("raw:version", NS):
        raw_date = _text(version.find("raw:date", NS))
        try:
            versions.append(parsedate_to_datetime(raw_date).astimezone(timezone.utc).isoformat())
        except (TypeError, ValueError):
            logger.warning("Paper %s: unparseable version date %r", paper_id, raw_date)
    return Paper(
        id=paper_id,
        title=_text(meta.find("raw:title", NS)),
        abstract=_text(meta.find("raw:abstract", NS)),
        authors=_text(meta.find("raw:authors", NS)),
        categories=_text(meta.find("raw:categories", NS)).split(),
        comments=_text(meta.find("raw:comments", NS)),
        versions=versions,
        datestamp=datestamp,
    )


def parse_page(text):
    """Return (papers, resumption_token) for one ListRecords response.

    Raises _OAIError for an OAI <error> element and HarvestError for unparseable XML.
    Deleted records and records without arXivRaw metadata are skipped.
    """
    try:
        root = ET.fromstring(text)
    except ET.ParseError as e:
        raise HarvestError(f"unparseable OAI-PMH response: {e}")
    error = root.find("oai:error", NS)
    if error is not None:
        raise _OAIError(error.get("code", "unknown"), _text(error))
    papers = []
    for record in root.iterfind(".//oai:ListRecords/oai:record", NS):
        header = record.find("oai:header", NS)
        if header is None or header.get("status") == "deleted":
            continue
        meta = record.find("oai:metadata/raw:arXivRaw", NS)
        if meta is None:
            continue
        datestamp = _text(header.find("oai:datestamp", NS))
        if not datestamp:
            logger.warning("Record %s has no datestamp; skipped", _text(header.find("oai:identifier", NS)))
            continue
        paper = _paper_from(meta, datestamp)
        if paper:
            papers.append(paper)
    token_element = root.find(".//oai:resumptionToken", NS)
    token = _text(token_element) if token_element is not None else ""
    return papers, (token or None)


def _retry_after_seconds(header_value):
    if not header_value:
        return None
    try:
        return max(0, int(header_value))
    except ValueError:
        pass
    try:
        when = parsedate_to_datetime(header_value)
        return max(0, int((when - datetime.now(timezone.utc)).total_seconds()))
    except (TypeError, ValueError):
        return None


def _fetch(session, params, sleep):
    """One OAI request. Retries 429, 503 and network trouble; returns the body text."""
    attempts = len(RETRY_WAITS_SECONDS)
    for attempt in range(attempts + 1):
        try:
            response = session.get(
                OAI_BASE, params=params, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT_SECONDS
            )
        except requests.RequestException as e:
            problem, retry_after = f"{type(e).__name__}: {e}", None
        else:
            if response.status_code == 200:
                return response.text
            if response.status_code not in (429, 503):
                raise HarvestError(f"HTTP {response.status_code} from {OAI_BASE}")
            problem, retry_after = f"HTTP {response.status_code}", response.headers.get("Retry-After")
        if attempt == attempts:
            raise HarvestError(f"{problem} after {attempts} retries")
        wait = _retry_after_seconds(retry_after)
        if wait is None:
            wait = RETRY_WAITS_SECONDS[attempt]
        logger.warning("arXiv OAI-PMH: %s; retry %d of %d in %ds", problem, attempt + 1, attempts, wait)
        sleep(wait)


def harvest(from_date, until_date=None, session=None, sleep=time.sleep):
    """Return every record whose OAI datestamp is from_date or later, as Paper objects.

    Follows resumption tokens with the three-second spacing arXiv asks for. An expired
    token restarts the harvest once. "No records" is an empty result, not an error.
    """
    session = session or requests.Session()
    initial = {"verb": "ListRecords", "metadataPrefix": METADATA_PREFIX, "from": from_date.isoformat()}
    if until_date:
        initial["until"] = until_date.isoformat()
    params, papers, restarted, requests_made = dict(initial), [], False, 0
    while True:
        if requests_made:
            sleep(REQUEST_SPACING_SECONDS)
        body = _fetch(session, params, sleep)
        requests_made += 1
        try:
            page, token = parse_page(body)
        except _OAIError as e:
            if e.code == "noRecordsMatch":
                logger.info("arXiv OAI-PMH: no records since %s", from_date.isoformat())
                return papers
            if e.code == "badResumptionToken" and not restarted:
                logger.warning("arXiv OAI-PMH: resumption token rejected; restarting the harvest once")
                restarted, params, papers = True, dict(initial), []
                continue
            raise HarvestError(f"OAI error {e.code}: {e.message}")
        papers.extend(page)
        logger.info("arXiv OAI-PMH: page %d, %d records", requests_made, len(page))
        if not token:
            return papers
        if requests_made >= MAX_PAGES:
            raise HarvestError(f"more than {MAX_PAGES} pages; stopping in case the resumption token is looping")
        params = {"verb": "ListRecords", "resumptionToken": token}


class HarvestStore:
    """Harvest state plus the per-datestamp files of new papers under {data_dir}/arxiv-harvest/.

    The state file records the latest datestamp fully harvested. The per-day files feed
    the keyword dry run and the Claude review, and they are what the inclusive harvest
    window is de-duplicated against, so .seen_arxiv_papers.json keeps its old meaning
    (papers that reached a digest) instead of becoming a ledger of all of arXiv.
    """

    def __init__(self, data_dir):
        self.data_dir = Path(data_dir)
        self.state_path = self.data_dir / STATE_FILE
        self.dir = self.data_dir / HARVEST_DIR

    def last_datestamp(self):
        try:
            return date.fromisoformat(json.loads(self.state_path.read_text())["last_datestamp"])
        except FileNotFoundError:
            return None
        except (ValueError, KeyError, TypeError) as e:
            logger.warning("Harvest state file %s unreadable (%s); treating as first run", self.state_path, e)
            return None

    def window_start(self, today):
        """(from_date, note): where the next harvest starts; note explains a capped catch-up."""
        last = self.last_datestamp()
        if last is None:
            return today - timedelta(days=1), None
        cap = today - timedelta(days=CATCH_UP_CAP_DAYS)
        if last < cap:
            return cap, f"last harvest was {last.isoformat()}; catching up from {cap.isoformat()} only"
        return last, None

    def set_last_datestamp(self, value):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(
            {"last_datestamp": value.isoformat(), "updated_at": datetime.now(timezone.utc).isoformat()}, indent=2
        ))

    def _file(self, datestamp):
        return self.dir / f"{datestamp}.json"

    def load(self):
        """{datestamp: [Paper, ...]} for every saved file, oldest first."""
        out = {}
        for path in sorted(self.dir.glob("*.json")):
            try:
                out[path.stem] = [Paper.from_dict(item) for item in json.loads(path.read_text())]
            except (ValueError, TypeError, KeyError) as e:
                logger.warning("Skipping unreadable harvest file %s: %s", path, e)
        return out

    def known_ids(self):
        return {paper.id for papers in self.load().values() for paper in papers}

    def add(self, papers):
        """Save papers into their datestamp files; return the ones not saved before."""
        known = self.known_ids()
        fresh, seen_now = [], set()
        for paper in papers:
            if paper.id in known or paper.id in seen_now:
                continue
            seen_now.add(paper.id)
            fresh.append(paper)
        by_day = {}
        for paper in fresh:
            by_day.setdefault(paper.datestamp, []).append(paper)
        self.dir.mkdir(parents=True, exist_ok=True)
        for datestamp, day_papers in by_day.items():
            path = self._file(datestamp)
            existing = []
            if path.exists():
                try:
                    existing = json.loads(path.read_text())
                except ValueError as e:
                    logger.warning("Harvest file %s was unreadable (%s); replacing it", path, e)
            path.write_text(json.dumps(existing + [paper.to_dict() for paper in day_papers], indent=1))
        return fresh

    def prune(self, today, keep_days=HARVEST_KEEP_DAYS):
        """Delete per-day files older than keep_days; return the names removed."""
        cutoff = today - timedelta(days=keep_days)
        removed = []
        for path in self.dir.glob("*.json"):
            try:
                datestamp = date.fromisoformat(path.stem)
            except ValueError:
                continue
            if datestamp < cutoff:
                path.unlink()
                removed.append(path.name)
        return removed
