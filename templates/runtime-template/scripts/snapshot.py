"""Save pre-change git diff as a snapshot."""
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
CONFIG = json.loads((PROJECT_DIR / "config" / "runtime.json").read_text(encoding="utf-8"))
SOURCE = CONFIG["source_path"]
SNAPSHOTS = PROJECT_DIR / "snapshots"
SNAPSHOTS.mkdir(parents=True, exist_ok=True)


def snapshot(label: str = ""):
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    name = f"{ts}_{label}.patch" if label else f"{ts}_snapshot.patch"
    out = SNAPSHOTS / name

    try:
        result = subprocess.run(
            ["git", "-C", SOURCE, "diff", "HEAD"],
            capture_output=True, text=True
        )
        diff = result.stdout

        result2 = subprocess.run(
            ["git", "-C", SOURCE, "diff", "--cached"],
            capture_output=True, text=True
        )
        staged = result2.stdout

        content = []
        content.append(f"# Snapshot: {ts}")
        content.append(f"# Label: {label or 'N/A'}")
        content.append(f"# Branch: {CONFIG.get('branch', 'N/A')}")
        content.append(f"# Source: {SOURCE}")
        content.append("")

        if staged:
            content.append("# --- Staged Changes ---")
            content.append(staged)

        if diff:
            content.append("# --- Unstaged Changes ---")
            content.append(diff)

        if not staged and not diff:
            content.append("# (no changes — clean working tree)")

        out.write_text("\n".join(content), encoding="utf-8")
        print(f"snapshot saved: {out.name}")
        return str(out)

    except Exception as e:
        print(f"snapshot failed: {e}")
        return None


if __name__ == "__main__":
    label = sys.argv[1] if len(sys.argv) > 1 else ""
    snapshot(label)
