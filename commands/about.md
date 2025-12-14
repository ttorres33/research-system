---
description: Show plugin documentation and usage
allowed-tools: [Read, AskUserQuestion]
model: haiku
---

# About Research System

Help the user learn about the Research System plugin interactively.

## Step 1: Read the README

Read `${CLAUDE_PLUGIN_ROOT}/README.md` to understand the full documentation.

## Step 2: Present Overview and Ask What They Want to Learn

Present a brief welcome and list the main topics:

```
Welcome to Research System! This plugin automates research paper discovery and summarization.

What would you like to learn about?
```

Use AskUserQuestion with these options:
- **Quick Start** - How to install and get started
- **Daily Workflow** - How to use the system day-to-day
- **Commands** - List of all available slash commands
- **Troubleshooting** - Common issues and how to fix them
- **Full Documentation** - Show the complete README

## Step 3: Show Relevant Section

Extract and display the relevant section from the README you read in Step 1. Do NOT hardcode content - always pull from the README so users see the latest documentation.

Based on the user's choice, find and display:

- **Quick Start**: The "## Quick Start" section from README
- **Daily Workflow**: The "## Sample Daily Workflow" section from README
- **Commands**: The "## Commands" section from README
- **Troubleshooting**: The "## Troubleshooting" section from README
- **Full Documentation**: Output the entire README

## Step 4: Offer to Continue

After showing the requested section, ask if they want to learn about another topic or if they have questions.
