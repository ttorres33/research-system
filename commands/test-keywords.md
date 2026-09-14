---
name: test-keywords
description: Show what each topic and keyword would match against the last week of arXiv papers, before it reaches a digest
allowed-tools: [Read, Bash]
---

# Test Keywords Command

Run the keyword dry run and help the user read it. Nothing is written; the daily run is
not affected.

## Step 1: Load Configuration

1. Read `~/.claude/research-system-config/config.yaml`
2. Extract `paths.research_root` and `paths.data`; the harvest files live in
   `research_root/[paths.data]/arxiv-harvest/`

## Step 2: Run the Dry Run

1. Check for harvest files:
   ```bash
   ls "[research_root]/[paths.data]/arxiv-harvest/" 2>/dev/null
   ```
2. If there are files, run:
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/utilities/keyword_dryrun.py
   ```
   If there are none (first day, or the scheduled run has not happened yet), add `--harvest`
   so one day is fetched into memory; this takes a few seconds and is not saved.
3. Capture the output.

## Step 3: Explain the Output

For each topic the script prints the number of new papers per day in its categories,
then one line per keyword with hits per day and up to five sample titles, and for a
Claude-mode topic the number of papers the review would read each day.

Walk the user through what stands out:
- **Keywords flagged `high volume`** almost always match a different meaning of the phrase
  ("active learning" is a machine-learning technique; "decision making" appears in control
  and robotics papers). Suggest a category restriction for the topic or a narrower phrase.
- **Keywords flagged `no hits`** may be fine (specific phrases hit rarely) or may need a
  plural, a synonym, or a hyphen removed. Remind the user that matching is whole-word and
  case-insensitive with no stemming: `worker` does not match "workers".
- **Keywords flagged `UNSUPPORTED`** use arXiv API syntax the matcher does not support
  (`cat:`, `ti:`, `*`). They are skipped by the daily run until fixed.
- **Claude review size** above 60 a day means the wizard would suggest keyword mode for
  that topic; below it, Claude mode is comfortable.
- Sample titles show whether a keyword is finding what the user meant. Point at concrete
  titles rather than describing them.

## Step 4: Offer Changes

Offer to edit `research_root/.research-data/keywords.md` with the specific changes
discussed (a `categories:` line, a `mode:` line, a rephrased keyword). See
`config/README.md` in the plugin for the settings and syntax. Do not edit the file
without the user agreeing to each change.

## Error Handling

- **Config not found**: Run `/setup-research-automation` first
- **No harvest files and `--harvest` fails**: arXiv's OAI-PMH endpoint is unreachable; try again later
- **Python errors**: Show the full output
