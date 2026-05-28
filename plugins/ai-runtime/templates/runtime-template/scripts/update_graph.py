"""Copy global graph files into a task's delta-graph directory.

Usage: python update_graph.py <task_dir>
"""
import shutil
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
GLOBAL_GRAPH = PROJECT_DIR / "knowledge" / "global-graph"


def update(task_dir: Path):
    delta_graph = task_dir / "delta-graph"
    delta_graph.mkdir(parents=True, exist_ok=True)

    count = 0
    for file in GLOBAL_GRAPH.glob("*"):
        if file.is_file():
            shutil.copy2(file, delta_graph / file.name)
            count += 1

    print(f"delta-graph updated ({count} files)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python update_graph.py <task_dir>")
        sys.exit(1)
    update(Path(sys.argv[1]))
