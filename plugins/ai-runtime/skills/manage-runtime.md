# Manage AI-Runtime

Triggered during daily development. Handles build decisions and structured refactoring workflow.

## Build Decision

When the user has made changes, decide full vs incremental build:

```
What changed?
  ├─ *.md / *.rst / *.txt        → full build
  ├─ *.png / *.jpg / *.svg       → full build
  ├─ *.json / *.yaml / config    → full build (may affect semantics)
  ├─ directory added/removed     → full build
  └─ code only (*.py / *.ts / *.go etc.) → incremental build
```

**Rule: doc/image/config change → full; pure code change → incremental.**

### Running the build

Read `{storage_root}/projects/{ProjectID}/config/runtime.json` to get `source_path`.

**Full build (Windows):**
```powershell
{project_dir}/scripts/full_build.ps1
```

**Full build (Mac/Linux):**
```bash
bash {project_dir}/scripts/full_build.sh
```

**Incremental build (Windows):**
```powershell
{project_dir}/scripts/incremental_build.ps1
```

**Incremental build (Mac/Linux):**
```bash
bash {project_dir}/scripts/incremental_build.sh
```

After build completes:
- Check `knowledge/test-gap-report.md` for new critical gaps
- Report: modules updated, context.md size, test gaps

## Refactor Workflow

For structured, traceable refactoring:

```
1. task.py create "goal" "constraint1" "constraint2"
   → tasks/active/task_xxx.md

2. snapshot.py "description"
   → snapshots/xxx.patch (save current state)

3. [Execute code changes]

4. patch.py "description" "notes"
   → patches/xxx.patch (save diff)

5. changelog.py "title" "files" "reason" "compatibility"
   → changelog/xxx.md

6. Build (full or incremental based on what changed)
   → Rebuild knowledge artifacts

7. task.py complete task_xxx
   → tasks/completed/
```

All artifacts under `{storage_root}/projects/{ProjectID}/`. Zero git repo pollution.

## Project Knowledge

- Full architecture and dependency graph: `knowledge/context.md`
- Per-module key files, entry points, execution flows: `knowledge/gitnexus/generated/<module>/SKILL.md`
- Test coverage gaps: `knowledge/test-gap-report.md`
