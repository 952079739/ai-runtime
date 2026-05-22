# AI-Runtime Plugin for Claude Code

One-command install: `/plugin install github:xxx/ai-runtime`

## Requirements

- Git, Node.js, npm
- Docker (for Qdrant vector DB)
- Python 3.11+ with packages from `templates/runtime-template/requirements.txt`

## What It Does

- **SessionStart hook**: Checks environment, detects projects, reports status
- **`/bootstrap`**: Initialize a project — sets up knowledge infrastructure, configures LLM backend, runs first full build
- **`/manage-runtime`**: Build & refactor workflow — decide full vs incremental build, structured refactoring with snapshots and changelogs
- **`/test-gap`**: Find high-impact symbols with zero test coverage

## Quick Start

```bash
cd your-project
claude
# SessionStart reports: "New project detected. Run /bootstrap to initialize."
/bootstap
# Follow the prompts...
```
