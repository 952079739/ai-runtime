# Runtime Rules

## Must NOT

- invent runtime structure
- invent script names
- invent graph formats
- invent context schema
- create runtime files inside git repo
- hardcode source paths in scripts

## Must

- preserve script compatibility
- preserve incremental build
- preserve context schema
- read source_path from config/runtime.json
- write all knowledge into {storage_root}/projects/{ProjectID}
- log all builds to logs/build/
- save snapshot before major changes
- save patch after each change
- record changelog for completed tasks

## Build Modes

### full_build.ps1
- gitnexus analyze
- graph_builder.py
- generate_knowledge_artifacts.py
- writes build log

### incremental_build.ps1
- graph_builder.py (incremental)
- generate_knowledge_artifacts.py
- writes build log

## Task Lifecycle

task.py create  → tasks/active/
task.py start   → mark running
task.py complete → tasks/completed/
task.py fail    → tasks/failed/

## Workflow Order

1. snapshot.py (pre-change)
2. code changes
3. patch.py (post-change diff)
4. changelog.py (record)
5. incremental_build.ps1
6. task.py complete
