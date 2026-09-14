"""Test support: import the plugin's scripts without installing anything.

The automation scripts are plain files in scripts/automation/ (cron runs them from that
directory), so tests put that directory on sys.path.
"""

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTOMATION_DIR = ROOT / "scripts" / "automation"
UTILITIES_DIR = ROOT / "scripts" / "utilities"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

for directory in (AUTOMATION_DIR, UTILITIES_DIR):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))


# A root NullHandler keeps logging's last-resort stderr output out of test runs;
# assertLogs still captures what it needs.
logging.getLogger().addHandler(logging.NullHandler())


def fixture(name):
    return (FIXTURES_DIR / name).read_text()
