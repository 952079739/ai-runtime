"""Record a changelog entry for a completed change."""
import json
import sys
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
CONFIG = json.loads((PROJECT_DIR / "config" / "runtime.json").read_text(encoding="utf-8"))
CHANGELOG = PROJECT_DIR / "changelog"
CHANGELOG.mkdir(parents=True, exist_ok=True)


def record(title: str, files: list[str] = None, reason: str = "", compatibility: str = ""):
    ts = datetime.now().strftime("%Y%m%d")
    entry_file = CHANGELOG / f"{ts}.md"

    existing = ""
    if entry_file.exists():
        existing = entry_file.read_text(encoding="utf-8")

    lines = []
    if not existing:
        lines.append("# Runtime Changes\n")

    lines.append(f"## {title}")
    lines.append(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**Branch**: {CONFIG.get('branch', 'N/A')}")
    lines.append("")

    if files:
        lines.append("### Files\n")
        for f in files:
            lines.append(f"- `{f}`")
        lines.append("")

    if reason:
        lines.append(f"### Reason\n\n{reason}\n")

    if compatibility:
        lines.append(f"### Compatibility\n\n{compatibility}\n")

    lines.append("---\n")

    if existing:
        parts = existing.split("\n---\n", 1)
        if len(parts) == 2:
            entry_file.write_text(parts[0] + "\n---\n" + "\n".join(lines) + "\n" + parts[1], encoding="utf-8")
        else:
            entry_file.write_text(existing + "\n" + "\n".join(lines), encoding="utf-8")
    else:
        entry_file.write_text("\n".join(lines), encoding="utf-8")

    print(f"changelog recorded: {entry_file.name} -> {title}")


if __name__ == "__main__":
    title = sys.argv[1] if len(sys.argv) > 1 else "Untitled change"
    files = sys.argv[2].split(",") if len(sys.argv) > 2 and sys.argv[2] else None
    reason = sys.argv[3] if len(sys.argv) > 3 else ""
    compatibility = sys.argv[4] if len(sys.argv) > 4 else ""
    record(title, files, reason, compatibility)
