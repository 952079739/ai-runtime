"""Save post-change git diff as a named patch."""
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
CONFIG = json.loads((PROJECT_DIR / "config" / "runtime.json").read_text(encoding="utf-8"))
SOURCE = CONFIG["source_path"]
PATCHES = PROJECT_DIR / "patches"
PATCHES.mkdir(parents=True, exist_ok=True)


def patch(name: str, description: str = ""):
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"{ts}_{name}.patch" if name else f"{ts}_patch.patch"
    out = PATCHES / filename

    try:
        result = subprocess.run(
            ["git", "-C", SOURCE, "diff", "HEAD"],
            capture_output=True, text=True
        )
        diff = result.stdout

        if not diff.strip():
            print("(no changes to save as patch)")
            return None

        content = []
        content.append(f"# Patch: {name}")
        content.append(f"# Date: {ts}")
        content.append(f"# Branch: {CONFIG.get('branch', 'N/A')}")
        content.append(f"# Source: {SOURCE}")
        if description:
            content.append(f"# Description: {description}")
        content.append("")
        content.append(diff)

        out.write_text("\n".join(content), encoding="utf-8")
        print(f"patch saved: {out.name} ({len(diff.splitlines())} lines)")
        return str(out)

    except Exception as e:
        print(f"patch failed: {e}")
        return None


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "changes"
    desc = sys.argv[2] if len(sys.argv) > 2 else ""
    patch(name, desc)
