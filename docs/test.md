# Tests

Plain `unittest` from the standard library, no test packages. Run them with an
interpreter that has the plugin's requirements installed (`requests`, `PyYAML`), for
example the one the cron jobs use.

## Running

From the plugin root:

```bash
python3 -m unittest discover -s tests -t . -p "test_*.py"
```

One file:

```bash
python3 -m unittest tests.test_arxiv_harvest
```

One case:

```bash
python3 -m unittest tests.test_arxiv_harvest.HarvestTests.test_expired_token_restarts_once
```

The suite makes no network calls and writes only to temporary directories.

## Layout

| File | Covers |
|---|---|
| `support.py` | Puts `scripts/automation` and `scripts/utilities` on `sys.path`; loads fixtures |
| `fixtures/` | Two pages of an arXiv OAI-PMH `ListRecords` response and three OAI error bodies |
| `test_arxiv_harvest.py` | Response parsing, the new-paper rule, paging and retries with a scripted session, the harvest state store |
| `test_keyword_match.py` | Keyword syntax, whole-word semantics, precedence, unsupported syntax, `explain()` |
| `test_topics.py` | `keywords.md` parsing: settings lines, continuation, defaults, warnings, old-style files; the JSON command-line mode `/configure-topics` uses |
| `test_digest.py` | Paper rendering for arXiv and Scholar entries, section layout, replacing a topic's pending line |
| `test_fetch_papers.py` | `main()` against a scratch research root with the harvest, Scholar and the clock replaced: routing by mode and category, catch-up, harvest failure, Sundays, unsupported syntax, same-day reruns |
| `test_apply_claude_triage.py` | Batch preparation, applying kept lists to the digest, malformed and missing agent results, the processed guard |
| `test_keyword_dryrun.py` | The dry run's per-topic report and flags, `--volumes`, the no-harvest exit code |

## Not covered by unit tests

The slash commands (`commands/*.md`) are prompts, so their control flow, for example the
order check in `/filter-research-digest` and the agent spawning in
`/generate-research-digest`, is exercised by running the command in Claude Code, not here.
The scripts they call are tested.

## Conventions

- Test files are `tests/test_*.py`; anything else under `tests/` is support code.
- Utility scripts are never named `test_*.py`, so discovery cannot pick them up.
- Network access is stubbed with a scripted session object; see `FakeSession` in
  `test_arxiv_harvest.py`.
