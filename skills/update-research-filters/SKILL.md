---
name: update-research-filters
description: Interactively refine filter criteria based on current digest results to improve relevance filtering
allowed-tools: [Read, Write, Edit, AskUserQuestion]
---

# Update Research Filters Skill

When invoked, help the user refine their filter criteria through an interactive interview about what papers are irrelevant.

## Step 1: Load Current Configuration

1. Read `~/.claude/research-system-config/config.yaml`
2. Extract current filter settings:
   - `filter.business_focus`
   - `filter.relevant_topics`
   - `filter.irrelevant_topics`
   - `filter.relevance_criteria`
3. Extract paths:
   - `paths.research_root`
   - `paths.daily_digests`

## Step 2: Identify Which Digest to Review

1. Ask user using AskUserQuestion:
   - "Which filtered digest still has too many irrelevant papers?"
   - Option 1: "Most recent filtered digest"
   - Option 2: "Specify date (YYYY-MM-DD)"

2. Construct path to filtered digest
3. Read the filtered digest file
4. If file not found, suggest running `/filter-research-digest` first

## Step 3: Show Current Filter Settings

Display to user:
```
Current Filter Criteria:
- Business Focus: [business_focus]
- Relevant Topics: [list relevant_topics]
- Irrelevant Topics: [list irrelevant_topics]
- Relevance Criteria: [relevance_criteria]
```

## Step 4: Sample Papers from Digest

1. Extract 10-15 sample paper titles and snippets from the filtered digest
2. Show a representative sample across different topic sections
3. Display each paper with:
   - Topic category
   - Paper title
   - Brief snippet

## Step 5: Interactive Interview

Ask the user a series of questions to identify patterns:

### Question 1: Identify Irrelevant Papers
```
From the samples shown, which papers are NOT relevant to your work?
Please list the numbers of irrelevant papers.
```

### Question 2: Identify Patterns
For each paper the user marked as irrelevant, ask:
```
What makes this paper irrelevant?
- Is it about a specific domain/field you don't work in?
- Is it too technical/theoretical?
- Is it about a method/approach you don't use?
```

### Question 3: Extract Keywords
```
What keywords or topics in these irrelevant papers should we filter out?
Examples: "agriculture", "medical diagnosis", "pure mathematics"
```

### Question 4: Refine Relevance Criteria
```
Can you describe in one sentence what makes a paper relevant to you?
Focus on what you DO want to see, not what you don't want.
```

## Step 6: Update Configuration

Based on interview responses:

1. **Add to irrelevant_topics:**
   - Extract keywords/topics user mentioned
   - Add to existing list (don't remove old ones, append new ones)

2. **Update relevance_criteria:**
   - If user provided new description, use it
   - Otherwise, keep existing but add clarifications

3. **Optionally update relevant_topics:**
   - If user mentioned specific areas they DO care about, add those

4. **Keep business_focus:**
   - Only update if user explicitly says it's wrong

## Step 7: Update config.yaml

1. Read `~/.claude/research-system-config/config.yaml`
2. Update the filter section with new values
3. Write the updated config back to `~/.claude/research-system-config/config.yaml`
4. Preserve all other config sections unchanged

**Example update:**
```yaml
filter:
  business_focus: "product management and continuous discovery"
  relevant_topics:
    - "user research"
    - "decision making"
    - "product development"
    - "team collaboration"  # NEW
  irrelevant_topics:
    - "pure mathematics"
    - "medical procedures"
    - "agriculture"
    - "chemical engineering"  # NEW
    - "theoretical physics"   # NEW
  relevance_criteria: "Paper must relate to how product teams make decisions, discover customer needs, or collaborate effectively. Focus on practical applications, not pure theory."
```

## Step 8: Offer to Re-Filter

Ask user using AskUserQuestion:
```
Filter criteria updated! Would you like to re-run the filter on the same digest to see if it's better?
- Yes, re-filter now
- No, I'll filter manually later
```

If "Yes":
- Invoke the filter-research-digest skill with the same digest date
- Show before/after comparison (papers before update vs after)

## Step 9: Report Results

Show user:
- What was added to irrelevant_topics
- Updated relevance_criteria (if changed)
- Location of updated config file
- Suggestion: "Run `/filter-research-digest` on future digests to see improved results"

## Tips for Effective Filtering

Inform the user:
- **Be specific with irrelevant topics**: "agricultural chemistry" is better than "chemistry"
- **Start conservative**: Add a few topics, test, then refine
- **It's iterative**: May need 2-3 rounds to get it right
- **Check Sunday digests**: They're largest and show filter effectiveness best

## Error Handling

- **Config file not found**: Show error with setup instructions
- **Digest file not found**: Suggest running filter command first
- **No papers to sample**: Digest might be empty or already well-filtered
- **Config write fails**: Show permission error with file path

## Notes

- This skill modifies config.yaml in place
- Changes are permanent (updates the user's configuration)
- Old filter criteria are preserved and appended to (not replaced)
- Can be run multiple times to iteratively refine
- Works best with filtered digests (not raw digests)
