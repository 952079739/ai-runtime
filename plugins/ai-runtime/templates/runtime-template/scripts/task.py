"""Task lifecycle management with full directory scaffolding.

Each task is a directory under tasks/active/ with:
  task.md          — task description + constraints
  delta-context.md — combined context for Claude (auto-generated)
  delta-graph/     — frozen copy of global graph
  patches/         — git diffs for this task
  logs/            — task-specific logs
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
TASKS_DIR = PROJECT_DIR / "tasks"
CONFIG = json.loads((PROJECT_DIR / "config" / "runtime.json").read_text(encoding="utf-8"))
SOURCE = Path(CONFIG["source_path"])

now = lambda: datetime.now().strftime("%Y%m%d_%H%M")
ts_id = lambda: datetime.now().strftime("%Y-%m-%d-%H%M%S")


def _build_delta_context(task_dir: Path):
    """Generate delta-context.md for this task."""
    task_file = task_dir / "task.md"
    if not task_file.exists():
        return
    task_content = task_file.read_text(encoding="utf-8")

    ctx = f"""# TASK

{task_content}

# GLOBAL KNOWLEDGE

"""
    arch_dir = PROJECT_DIR / "knowledge" / "architecture"
    if arch_dir.exists():
        for f in sorted(arch_dir.glob("*.md")):
            ctx += f"\n\n# Architecture: {f.stem}\n\n"
            ctx += f.read_text(encoding="utf-8", errors="ignore")[:5000]

    summaries_dir = PROJECT_DIR / "knowledge" / "summaries"
    if summaries_dir.exists():
        summary_files = sorted(summaries_dir.glob("*.md"))
        if summary_files:
            ctx += "\n\n# Module Summaries (sample)\n\n"
            for f in summary_files[:50]:
                ctx += f.read_text(encoding="utf-8", errors="ignore")[:2000] + "\n---\n"
            if len(summary_files) > 50:
                ctx += f"\n(+ {len(summary_files) - 50} more in knowledge/summaries/)\n"

    ctx += """

# SAFETY RULES

- preserve backward compatibility
- incremental migration only
- avoid breaking plugin lifecycle
- maintain API contracts
"""

    (task_dir / "delta-context.md").write_text(ctx, encoding="utf-8")


def _copy_graph(task_dir: Path):
    """Copy global graph into task's delta-graph."""
    global_graph = PROJECT_DIR / "knowledge" / "global-graph"
    delta_graph = task_dir / "delta-graph"
    delta_graph.mkdir(parents=True, exist_ok=True)
    count = 0
    for f in global_graph.glob("*"):
        if f.is_file():
            shutil.copy2(f, delta_graph / f.name)
            count += 1
    return count


def create(goal: str, constraints: list[str] = None):
    """Create a new task directory with full scaffolding."""
    slug = re.sub(r'[^a-zA-Z0-9]+', '-', goal.lower())[:40]
    task_id = f"{ts_id()}-{slug}"
    task_dir = TASKS_DIR / "active" / task_id

    # Create directory structure
    (task_dir / "delta-graph").mkdir(parents=True, exist_ok=True)
    (task_dir / "patches").mkdir(parents=True, exist_ok=True)
    (task_dir / "logs").mkdir(parents=True, exist_ok=True)

    # Write task.md
    lines = [
        "# Task",
        "",
        "## Goal",
        "",
        goal,
        "",
        "## Constraints",
        "",
    ]
    if constraints:
        for c in constraints:
            lines.append(f"- {c}")
    else:
        lines.append("- preserve backward compatibility")
    lines += [
        "",
        "## Context",
        "",
        f"- branch: {CONFIG.get('branch', 'N/A')}",
        f"- source: {SOURCE}",
        f"- created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Status",
        "",
        "pending",
    ]

    (task_dir / "task.md").write_text("\n".join(lines), encoding="utf-8")

    # Auto-generate delta context and graph snapshot
    _build_delta_context(task_dir)
    graph_count = _copy_graph(task_dir)

    print(f"task created: {task_id}")
    print(f"  dir: {task_dir}")
    print(f"  graph: {graph_count} files")
    return task_id


def start(task_id: str):
    return _set_status(task_id, "running")


def complete(task_id: str):
    _set_status(task_id, "completed")
    return _move(task_id, "active", "completed")


def fail(task_id: str, reason: str = ""):
    task = _set_status(task_id, "failed")
    if reason and task:
        text = task.read_text(encoding="utf-8")
        text += f"\n\n## Failure Reason\n\n{reason}\n"
        task.write_text(text, encoding="utf-8")
    return _move(task_id, "active", "failed")


def _find_task(task_id: str, folder: str = "active") -> Path | None:
    """Find a task directory by partial ID match."""
    task_dir = TASKS_DIR / folder
    matches = list(task_dir.glob(f"*{task_id}*"))
    if not matches:
        return None
    return matches[0]


def _set_status(task_id: str, status: str):
    task_dir = _find_task(task_id, "active")
    if not task_dir:
        print(f"task not found: {task_id}")
        return None
    task_file = task_dir / "task.md"
    text = task_file.read_text(encoding="utf-8")
    text = text.replace("pending", status).replace("running", status)
    task_file.write_text(text, encoding="utf-8")
    print(f"task {task_id}: {status}")
    return task_file


def _move(task_id: str, src: str, dst: str):
    task_dir = _find_task(task_id, src)
    if not task_dir:
        print(f"task not found in {src}: {task_id}")
        return
    dst_root = TASKS_DIR / dst
    dst_root.mkdir(parents=True, exist_ok=True)
    target = dst_root / task_dir.name
    shutil.move(str(task_dir), str(target))
    print(f"task moved: {src} -> {dst}")


def save_patch(task_id: str, name: str = ""):
    """Save current git diff into the task's patches/ directory."""
    task_dir = _find_task(task_id, "active") or _find_task(task_id, "completed") or _find_task(task_id, "failed")
    if not task_dir:
        print(f"task not found: {task_id}")
        return

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    patch_name = f"{ts}_{name}.patch" if name else f"{ts}_patch.patch"
    patch_file = task_dir / "patches" / patch_name

    try:
        result = subprocess.run(
            ["git", "-C", str(SOURCE), "diff", "HEAD"],
            capture_output=True, text=True
        )
        diff = result.stdout
        if not diff.strip():
            print("(no changes to save)")
            return

        content = f"# Patch: {name or 'unnamed'}\n"
        content += f"# Date: {ts}\n"
        content += f"# Task: {task_id}\n\n"
        content += diff

        patch_file.write_text(content, encoding="utf-8")
        print(f"patch saved: {patch_file.name} ({len(diff.splitlines())} lines)")
    except Exception as e:
        print(f"patch failed: {e}")


def list_tasks(folder: str = "active"):
    task_dir = TASKS_DIR / folder
    if not task_dir.exists():
        print(f"no {folder} tasks")
        return
    for d in sorted(task_dir.iterdir()):
        if d.is_dir():
            task_md = d / "task.md"
            if task_md.exists():
                first = task_md.read_text(encoding="utf-8").split("\n")[0]
                print(f"  {d.name}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    args = sys.argv[2:] if len(sys.argv) > 2 else []

    if cmd == "create":
        create(args[0] if args else "Untitled task", args[1:] if len(args) > 1 else None)
    elif cmd == "start":
        start(args[0])
    elif cmd == "complete":
        complete(args[0])
    elif cmd == "fail":
        fail(args[0], args[1] if len(args) > 1 else "")
    elif cmd == "patch":
        save_patch(args[0], args[1] if len(args) > 1 else "")
    elif cmd == "list":
        list_tasks(args[0] if args else "active")
    else:
        print(f"unknown command: {cmd}")
        print("usage: task.py create|start|complete|fail|patch|list [args...]")
