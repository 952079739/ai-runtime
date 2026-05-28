"""Build a delta-context.md for a task by combining task.md + architecture knowledge.

Usage: python build_delta_context.py <task_dir>
"""
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
KNOWLEDGE = PROJECT_DIR / "knowledge"


def build(task_dir: Path):
    task_file = task_dir / "task.md"
    if not task_file.exists():
        print(f"task.md not found in {task_dir}")
        return

    task_content = task_file.read_text(encoding="utf-8")

    context = f"""# TASK

{task_content}

# GLOBAL KNOWLEDGE

"""

    # Append architecture reports
    arch_dir = KNOWLEDGE / "architecture"
    if arch_dir.exists():
        for file in sorted(arch_dir.glob("*.md")):
            context += "\n\n"
            context += f"# Architecture: {file.stem}\n\n"
            context += file.read_text(encoding="utf-8", errors="ignore")[:5000]

    # Append module overview from summaries dir (top-level view)
    summaries_dir = KNOWLEDGE / "summaries"
    if summaries_dir.exists():
        summary_files = sorted(summaries_dir.glob("*.md"))
        if summary_files:
            context += "\n\n# Module Summaries (sample)\n\n"
            # Include a subset to keep delta-context manageable
            for file in summary_files[:50]:
                context += file.read_text(encoding="utf-8", errors="ignore")[:2000]
                context += "\n---\n"
            if len(summary_files) > 50:
                context += f"\n(+ {len(summary_files) - 50} more summaries available in knowledge/summaries/)\n"

    context += """

# SAFETY RULES

- preserve backward compatibility
- incremental migration only
- avoid breaking plugin lifecycle
- maintain API contracts
- all knowledge updates go through incremental_build.ps1
"""

    (task_dir / "delta-context.md").write_text(context, encoding="utf-8")
    print(f"delta-context.md generated ({len(context)} chars)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python build_delta_context.py <task_dir>")
        sys.exit(1)
    build(Path(sys.argv[1]))
