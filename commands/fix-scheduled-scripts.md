---
name: fix-scheduled-scripts
description: Update symlink and crontab entries to use stable plugin paths, fixing broken scheduled scripts after plugin directory changes
allowed-tools: [Bash]
---

# Fix Scheduled Scripts Command

Repair scheduled scripts (cron jobs) when the plugin directory location changes. This command:
1. Creates/updates a stable symlink pointing to the current plugin location
2. Scans crontab for hardcoded plugin paths and replaces them with symlink paths

## Step 1: Create/Update Stable Symlink

1. **Define paths:**
   - Symlink location: `~/.claude/research-system-config/plugin` (stable, never changes)
   - Target: `${CLAUDE_PLUGIN_ROOT}` (actual plugin location, may change)

2. **Check config directory:**
   - Run: `test -d ~/.claude/research-system-config && echo "EXISTS" || echo "NOT_FOUND"`
   - If NOT_FOUND: Run `mkdir -p ~/.claude/research-system-config`
   - If EXISTS: Continue (directory already exists)

3. **Check if symlink exists:**
   - Run: `ls -la ~/.claude/research-system-config/plugin 2>/dev/null || echo "NOT_FOUND"`

4. **Handle existing path:**
   - If symlink exists and points to correct location: "Symlink already up to date"
   - If symlink exists but points to wrong location: Remove and recreate
   - If regular directory exists: Show error - "Cannot create symlink: ~/.claude/research-system-config/plugin exists as a directory. Please remove or rename it."
   - If not found: Create new symlink

5. **Create/update symlink:**
   - Run: `ln -sfn "${CLAUDE_PLUGIN_ROOT}" ~/.claude/research-system-config/plugin`
   - Verify: `ls -la ~/.claude/research-system-config/plugin`
   - Report: "Created symlink: ~/.claude/research-system-config/plugin -> [actual path]"

## Step 2: Scan Crontab for Hardcoded Paths

1. **Get current crontab:**
   - Run: `crontab -l 2>/dev/null || echo "NO_CRONTAB"`
   - If no crontab exists, skip to Step 4

2. **Identify research-system related entries:**
   - Look for lines containing:
     - `fetch_papers.py`
     - `monitor_sources.py`
     - Any path containing `research-system`

3. **Check for hardcoded paths:**
   - Pattern to find: Any path that is NOT `~/.claude/research-system-config/plugin/` but references research-system scripts
   - Common hardcoded patterns:
     - `~/.claude/plugins/cache/research-system/`
     - `~/.claude/plugins/research-system/`
     - Any absolute path containing `/research-system/scripts/`
   - Also check for the old symlink location `~/.claude/research-system/` (if we used that previously)

## Step 3: Update Crontab Entries

1. **For each hardcoded path found:**
   - Extract the full cron entry
   - Replace the hardcoded path with `~/.claude/research-system-config/plugin/`
   - Example:
     - Before: `0 6 * * * cd ~/.claude/plugins/cache/research-system/scripts/automation && python3 fetch_papers.py`
     - After: `0 6 * * * cd ~/.claude/research-system-config/plugin/scripts/automation && python3 fetch_papers.py`

2. **Create updated crontab:**
   - Build new crontab content with all replacements
   - Show diff to user: "Found [N] entries to update:"
   - Show before/after for each changed line

3. **Apply updated crontab:**
   - Run: `echo "[new_crontab_content]" | crontab -`
   - Verify: `crontab -l | grep research-system`

## Step 4: Report Results

**Provide summary:**

```
Fix Scheduled Scripts Complete

Symlink Status:
- ~/.claude/research-system-config/plugin -> [actual plugin path]
- Status: [Created/Updated/Already correct]

Crontab Updates:
- Entries scanned: [N]
- Entries updated: [N]
- [List each updated entry if any]

Scheduled Scripts:
- fetch_papers.py: [Found at HH:MM daily / Not scheduled]
- monitor_sources.py: [Found at HH:MM daily / Not scheduled]

All scheduled scripts are now using stable paths.
```

**If no crontab exists:**
```
Fix Scheduled Scripts Complete

Symlink Status:
- ~/.claude/research-system-config/plugin -> [actual plugin path]
- Status: Created

Crontab Updates:
- No crontab found. Run /setup-research-automation to configure scheduled scripts.
```

## Error Handling

- **Cannot create symlink directory:** Check ~/.claude/research-system-config/ exists and is writable
- **Crontab permission denied:** Show error, suggest checking user permissions
- **Symlink target doesn't exist:** Show error - plugin may not be properly installed
- **Cannot read ${CLAUDE_PLUGIN_ROOT}:** Show error - Claude Code environment variable not available

## When to Run This Command

Run this command when:
- Scheduled scripts stop working after a Claude Code update
- You see errors about missing plugin scripts in cron logs
- After reinstalling or updating the research-system plugin
- When `~/.research-data/*.log` shows "file not found" errors for Python scripts

## Notes

- This command is safe to run multiple times - it's idempotent
- The symlink approach ensures cron jobs survive plugin directory changes
- After running this command, future plugin updates only require re-running this command to fix paths
- The symlink is created in ~/.claude/research-system-config/ alongside config.yaml
