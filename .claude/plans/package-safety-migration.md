# Package safety migration for cc-plugins/research-system

## Goal

Migrate `cc-plugins/research-system` to the Package Safety pattern documented in `~/Code/CLAUDE.md`. This will incidentally fix all 22 known CVEs flagged in the 2026-05-22 audit report (`~/Vaults/Work/Package Audits/2026-05-22.md`):

- 21 pypdf CVEs (pypdf 6.1.1 → latest)
- 1 requests CVE (CVE-2026-25645)

Per Teresa's trigger-driven update strategy, the migration *is* the fix: creating `requirements.in` with no version specifiers and running `uv pip compile --generate-hashes` lands on latest safe versions and clears all CVEs in one step.

## Context for the agent

The audit identified this project as both **non-compliant** with the Package Safety Migration (no `requirements.in`, `requirements.txt` not hash-pinned) and **vulnerable** (22 CVEs in pinned deps).

Separately, an investigation of how `pypdf` is used surfaced a second issue: `scripts/utilities/split_conference_pdf.py` (lines ~11-14) contains a runtime auto-install:

```python
try:
    from pypdf import PdfReader, PdfWriter
except ImportError:
    print("pypdf not installed. Installing...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pypdf"])
    from pypdf import PdfReader, PdfWriter
```

This violates `~/Code/CLAUDE.md` rule #6 (no install side effects) and rule #4 (no `pip install`, must use `uv`). Must be removed as part of this work.

## Scope

**In scope:**
- Create `requirements.in` and regenerate `requirements.txt --generate-hashes`
- Remove the auto-install fallback in `split_conference_pdf.py`
- Test that the two pypdf-using scripts still work after the version bump
- Commit the changes

**Out of scope:**
- Any feature work or refactoring beyond what the migration requires
- Touching other cc-plugins (task-management, project-docs) — they're separate projects
- Other findings from the audit report

## Required reading before starting

1. `~/Code/CLAUDE.md` — full "Package Installation Safety" section
2. `~/Code/package-safety-checklist.md` — follow the Python Lambda path (Phase 5b) even though this isn't a Lambda; the workflow is the same
3. `cc-plugins/research-system/README.md` and the latest 2-3 entries in `cc-plugins/research-system/process-notes/` (or `process-notes.md` if still in flat format — convert via `/project-docs:convert-flat-process-notes-to-dir` if needed)
4. Current `requirements.txt` to see the existing deps

## Specific tasks

### 1. Create `requirements.in`

At `cc-plugins/research-system/requirements.in`. Abstract deps only, no version specifiers. Sourced from current `requirements.txt`:

```
arxiv
feedparser
google-search-results
PyYAML
pypdf
```

### 2. Pre-flight: audit for sdist-only deps

Per `package-safety-checklist.md` Phase 5b:

```bash
uv pip compile requirements.in -o /tmp/wheel-check.txt --only-binary :all:
```

If any dep is sdist-only and has build hooks, surface to Teresa before continuing — do NOT silently approve.

### 3. Regenerate `requirements.txt`

```bash
uv pip compile requirements.in -o requirements.txt --generate-hashes
```

If `uv` errors on `exclude-newer` (a too-recently-published package), STOP — surface the error to Teresa with the affected package and date. Do not bypass.

Note: a PreToolUse hook blocks direct writes to `requirements.txt`. The `uv pip compile` invocation is the only way to update it.

### 4. Remove the auto-install fallback

In `cc-plugins/research-system/scripts/utilities/split_conference_pdf.py`, replace the try/except with a clean import:

```python
from pypdf import PdfReader, PdfWriter
```

If a downstream caller might run this without installing deps first, that's a README issue (document the prereq), not a try/except issue. Do NOT replace `pip install` with `uv pip install` — the fallback path should not exist at all.

### 5. Test the two pypdf-using scripts

Both scripts use only the stable `PdfReader` and `PdfWriter` surface, so the version bump (6.1.1 → latest) is very unlikely to break them. Still, run a quick smoke test:

```bash
# Install the new requirements.txt locally
uv pip install --require-hashes -r requirements.txt

# Smoke test split_pdf_by_sections.py (find a sample PDF first)
python scripts/utilities/split_pdf_by_sections.py --help

# Smoke test split_conference_pdf.py
python scripts/utilities/split_conference_pdf.py --help
```

If either script imports cleanly and `--help` runs without error, the API surface is intact. If Teresa has a known-good test PDF available, run a full split against it as well.

If anything breaks (ImportError, AttributeError on PdfReader/PdfWriter, etc.), STOP and surface to Teresa with the specific error. Do not attempt to pin pypdf to an older version unilaterally — that decision is Teresa's.

### 6. Document the migration

Add a process-notes entry capturing:
- What was migrated and why (CVE counts cleared, compliance achieved)
- The exact pypdf version landed on (whatever `uv pip compile` picked)
- The auto-install fallback removal and reasoning
- Any surprises during the migration

Use `/project-docs:process-notes` — do not write to `process-notes/` directly.

## What to surface to Teresa before committing

- The exact versions `uv pip compile` selected, especially for `pypdf` (she wants to verify it's past 6.10.2 to clear all 21 CVEs)
- Any sdist-only finding from step 2
- Any test failure from step 5
- Any unexpected diff in the lockfile beyond the deps we asked for

## Commit plan

Suggested grouping (per `package-safety-checklist.md`):

1. **Commit 1:** `requirements.in` + regenerated `requirements.txt` (the migration itself)
2. **Commit 2:** removal of the auto-install fallback in `split_conference_pdf.py`
3. **Commit 3:** process-notes entry

If the diffs are small and all related, a single commit is also acceptable — but keep the auto-install fix separable in case Teresa wants to discuss it independently.

## Acceptance criteria

When the work is complete, the following should be true:

- [ ] `cc-plugins/research-system/requirements.in` exists with abstract deps
- [ ] `cc-plugins/research-system/requirements.txt` contains `--hash=sha256:` entries for every dep
- [ ] `pypdf` version in the lockfile is >= 6.10.2 (clears all 21 CVEs)
- [ ] `requests` version in the lockfile is >= 2.33.0 (clears CVE-2026-25645)
- [ ] The auto-install try/except in `split_conference_pdf.py` is gone
- [ ] Both pypdf-using scripts import cleanly and pass `--help`
- [ ] A process-notes entry documents the migration
- [ ] On next audit run, this project no longer appears in either the "Vulnerabilities & errors" or the "Unmigrated targets" sections of the weekly report

## If something feels off

- Do not deploy or push without Teresa's review
- Do not approve build scripts, override minimum-release-age, or bypass any package safety defense unilaterally
- Ask Teresa, even mid-task
