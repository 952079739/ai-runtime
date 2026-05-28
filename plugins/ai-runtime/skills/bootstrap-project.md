# Bootstrap AI-Runtime Project

Triggered by `/bootstrap`. Initializes a new project with AI-Runtime knowledge infrastructure.

## Workflow

### 1. Show environment status

Read the SessionStart hook output (Claude has it in context). Categorize:

- **Green**: All system tools, Python packages, and Qdrant are available
- **Yellow**: Optional deps missing (individual Python packages)
- **Red**: Required deps missing (git, node, npm, docker, graphify)

### 2. Handle missing dependencies

If system tools missing:
  → Guide user to install: git, node, npm, docker

If Python packages missing:
  → "Run: pip install -r <plugin_dir>/templates/runtime-template/requirements.txt"

If Qdrant not running:
  → Ask for storage root first (step 3), then start Qdrant:
  → `docker run -d --name qdrant -p 6333:6333 -v {storage_root}/qdrant-data:/qdrant/storage qdrant/qdrant`

### 3. Ask for storage root (one-time)

Ask: "Where should AI-Runtime store project data? e.g. E:/AI-Runtime or ~/ai-runtime"

Save to `~/.claude/ai-runtime-config.json`:
```json
{ "storage_root": "<user_provided_path>" }
```

Use the Write tool to create/update the file.

### 4. Test graphify backend

Run: `graphify extract --help`

**If it works** → LLM backend already configured. Skip to step 5.

**If it fails** → Show supported backends:

| Backend | Environment Variable |
|---------|---------------------|
| claude | ANTHROPIC_API_KEY |
| deepseek | DEEPSEEK_API_KEY |
| openai | OPENAI_API_KEY |
| gemini | GEMINI_API_KEY or GOOGLE_API_KEY |
| kimi | MOONSHOT_API_KEY |
| ollama | (local, no key needed) |

Ask: "Which backend do you want to use?"

After user picks a backend (e.g. deepseek), do NOT ask for the key. Instead, tell the user to set the environment variable themselves:

**Windows:**
```
Please set the environment variable, then reply "done":

  setx DEEPSEEK_API_KEY your-key

(Close and reopen this terminal, then re-run /bootstrap)
```

**Mac/Linux:**
```
Please set the environment variable, then reply "done":

  export DEEPSEEK_API_KEY=your-key

(Then re-run /bootstrap in the same terminal)
```

Replace `DEEPSEEK_API_KEY` with the correct variable name from the table above, and the command based on OS.

Wait for the user to reply "done" or confirm, then re-test with `graphify extract --help` to verify it works. If `graphify extract --help` now succeeds, proceed.

Update config (backend only, no key):
```json
{ "storage_root": "...", "llm_backend": "deepseek" }
```

### 5. Run runtime_bootstrap.py

```bash
python <plugin_dir>/templates/runtime-template/scripts/runtime_bootstrap.py \
  --storage-root <storage_root> \
  --template-dir <plugin_dir>/templates/runtime-template
```

This creates:
- `{storage_root}/projects/{ProjectID}/` directory structure
- `config/runtime.json` with project metadata
- Copies scripts, prompts, CLAUDE.md template

### 6. Run full build

**Windows:**
```powershell
{storage_root}/projects/{ProjectID}/scripts/full_build.ps1
```

**Mac/Linux:**
```bash
bash {storage_root}/projects/{ProjectID}/scripts/full_build.sh
```

Pipeline: gitnexus → graphify → summaries → graph → context → test-gap → CLAUDE.md merge

### 7. Report completion

Show summary:
- Project name and ID
- Modules found (from gitnexus)
- Graph nodes and edges
- context.md line count
- Test gap report summary (critical/warning/covered)

## Constraints

- NEVER create files inside the source git repo (except CLAUDE.md and .gitignore)
- NEVER ask for or store API keys — users set them via environment variables
- All knowledge artifacts go under `{storage_root}/projects/{ProjectID}/`
- Read `{storage_root}/projects/{ProjectID}/config/runtime.json` for source_path before any build
