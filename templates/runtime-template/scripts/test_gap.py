"""Test coverage gap analysis.

Finds high-impact symbols with zero test coverage by cross-referencing
gitnexus call graph data against test file heuristics.
"""
from pathlib import Path
import json
import re
import sys
from datetime import datetime
from collections import defaultdict


def find_project_root():
    """Locate the AI-Runtime project directory (parent of scripts/)."""
    return Path(__file__).resolve().parent.parent


def extract_core_symbols(project_dir: Path) -> list[dict]:
    """Phase 1: Extract core symbols from gitnexus SKILL.md files."""
    skills_dir = project_dir / "knowledge" / "gitnexus" / "generated"
    if not skills_dir.exists():
        print("  [test-gap] No gitnexus generated skills found, skipping.")
        return []

    symbols = []
    for skill_md in skills_dir.glob("*/SKILL.md"):
        module = skill_md.parent.name
        content = skill_md.read_text(encoding="utf-8", errors="replace")

        in_key_symbols = False
        for raw_line in content.splitlines():
            line = raw_line.strip()

            # Detect "Key Symbols" table header
            if line.startswith("|") and "Symbol" in line and "Type" in line:
                in_key_symbols = True
                continue
            if in_key_symbols and line.startswith("|-"):
                continue
            if in_key_symbols and line.startswith("|"):
                parts = [p.strip() for p in raw_line.split("|")]
                if len(parts) >= 2 and parts[1]:
                    name = parts[1].strip("`*_ ")
                    if name and len(name) > 1 and not name.startswith("#"):
                        symbols.append({"symbol": name, "module": module})
            elif in_key_symbols and not line.startswith("|"):
                in_key_symbols = False

            # Parse Entry Points (bullet list: - **`name`** (Type) — file)
            if line.startswith("- **`"):
                end = line.find("`**")
                if end > 4:
                    name = line[4:end].strip("`*_ ")
                    if name and len(name) > 1:
                        symbols.append({"symbol": name, "module": module})

    return symbols


def compute_fan_in(symbol: str, project_dir: Path) -> int:
    """Phase 2: Compute fan-in from gitnexus graph data."""
    graph_dir = project_dir / "knowledge" / "gitnexus"
    for graph_file in graph_dir.glob("**/*.json"):
        try:
            data = json.loads(graph_file.read_text(encoding="utf-8"))
            count = _count_incoming_from_graph(data, symbol)
            if count > 0:
                return count
        except (json.JSONDecodeError, KeyError):
            continue

    count = 0
    skills_dir = project_dir / "knowledge" / "gitnexus" / "generated"
    if skills_dir.exists():
        for skill_md in skills_dir.glob("*/SKILL.md"):
            content = skill_md.read_text(encoding="utf-8", errors="replace")
            mentions = len(re.findall(r'\b' + re.escape(symbol) + r'\b', content))
            if mentions > 1:
                count += mentions - 1

    return count


def _count_incoming_from_graph(data: dict, symbol: str) -> int:
    """Count incoming edges to symbol in gitnexus graph JSON."""
    count = 0
    if "relationships" in data:
        for rel in data["relationships"]:
            if rel.get("target") == symbol or rel.get("to") == symbol:
                count += 1
    if "edges" in data:
        for edge in data["edges"]:
            if edge.get("target") == symbol or edge.get("to") == symbol:
                count += 1
    if "nodes" in data:
        for node in data["nodes"]:
            if node.get("name") == symbol or node.get("id") == symbol:
                count = node.get("fan_in", node.get("incoming", 0))
                break
    return count


def has_test_coverage(symbol: str, module: str, project_dir: Path, source_path: Path) -> bool:
    """Phase 3: Check if symbol has any test coverage."""
    test_patterns = [
        "tests/", "test/", "__tests__/", "spec/",
        "test_*.py", "*_test.py", "*.test.ts", "*_test.go",
        "*.test.js", "*_test.java", "*.spec.ts", "*_spec.py",
    ]

    for pattern in test_patterns:
        for test_file in source_path.glob(pattern):
            if test_file.is_file():
                try:
                    content = test_file.read_text(encoding="utf-8", errors="replace")
                    if symbol in content:
                        return True
                except Exception:
                    continue

    for test_dir_name in ["tests", "test", "__tests__", "spec"]:
        test_dir = source_path / test_dir_name
        if test_dir.exists():
            for test_file in test_dir.rglob("*"):
                if test_file.suffix in {".py", ".ts", ".js", ".go", ".java"}:
                    try:
                        content = test_file.read_text(encoding="utf-8", errors="replace")
                        if symbol in content:
                            return True
                    except Exception:
                        continue

    return False


def generate_report(symbols: list[dict], project_dir: Path, source_path: Path) -> str:
    """Phase 4: Rank by fan_in * uncovered and generate markdown report."""
    results = []
    for s in symbols:
        fan_in = compute_fan_in(s["symbol"], project_dir)
        covered = has_test_coverage(s["symbol"], s["module"], project_dir, source_path)
        if fan_in > 0 and not covered:
            score = fan_in
            risk = "HIGH" if fan_in >= 8 else "MEDIUM" if fan_in >= 4 else "LOW"
            results.append({**s, "fan_in": fan_in, "score": score, "risk": risk})

    results.sort(key=lambda x: x["score"], reverse=True)

    critical = [r for r in results if r["risk"] == "HIGH"]
    warning = [r for r in results if r["risk"] == "MEDIUM"]
    low = [r for r in results if r["risk"] == "LOW"]

    total = len(symbols)
    covered_count = total - len(results)
    pct = (covered_count / total * 100) if total > 0 else 0

    lines = [
        f"# Test Gap Report — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## Critical (high impact, zero coverage)",
        "",
    ]

    if critical:
        lines.append("| Symbol | Module | Fan-in | Risk |")
        lines.append("|--------|--------|--------|------|")
        for r in critical:
            lines.append(f"| {r['symbol']} | {r['module']} | {r['fan_in']} | HIGH |")
    else:
        lines.append("*No critical gaps found.*")

    lines += ["", "## Warning (moderate impact, zero coverage)", ""]
    if warning:
        lines.append("| Symbol | Module | Fan-in | Risk |")
        lines.append("|--------|--------|--------|------|")
        for r in warning:
            lines.append(f"| {r['symbol']} | {r['module']} | {r['fan_in']} | MEDIUM |")
    else:
        lines.append("*No warnings.*")

    lines += ["", "## Summary", ""]
    lines.append(f"- Total core symbols: {total}")
    lines.append(f"- Covered: {covered_count} ({pct:.0f}%)")
    lines.append(f"- Uncovered: {len(results)}")
    lines.append(f"  - Critical: {len(critical)}")
    lines.append(f"  - Warning: {len(warning)}")
    lines.append(f"  - Low risk: {len(low)}")
    lines.append("")

    return "\n".join(lines)


def main():
    project_dir = find_project_root()

    config_path = project_dir / "config" / "runtime.json"
    if not config_path.exists():
        print("  [test-gap] No runtime.json found, skipping.")
        sys.exit(0)

    config = json.loads(config_path.read_text(encoding="utf-8"))
    source_path = Path(config.get("source_path", "."))
    if not source_path.exists():
        print(f"  [test-gap] Source path not found: {source_path}")
        sys.exit(0)

    print("  [test-gap] Phase 1: Extracting core symbols from gitnexus SKILL.md files...")
    symbols = extract_core_symbols(project_dir)
    print(f"  [test-gap] Found {len(symbols)} core symbols across modules.")

    print("  [test-gap] Phase 2-3: Computing fan-in and cross-referencing tests...")
    report = generate_report(symbols, project_dir, source_path)

    print("  [test-gap] Phase 4: Writing report...")
    report_path = project_dir / "knowledge" / "test-gap-report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    print(f"  [test-gap] Report saved: {report_path}")


if __name__ == "__main__":
    main()
