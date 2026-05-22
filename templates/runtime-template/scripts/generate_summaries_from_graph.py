"""Generate per-file summary markdown files from graphify's graph.json.

Reads graph.json, groups nodes by source_file, writes one summary .md per file
to knowledge/summaries/.  These summaries are the building blocks for context.md.
"""
import json
from pathlib import Path
from collections import defaultdict

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
KNOWLEDGE = PROJECT_DIR / "knowledge"

GRAPHIFY_GRAPH = KNOWLEDGE / "graphify-out" / "graph.json"
SUMMARIES_DIR = KNOWLEDGE / "summaries"

# Common top-level source dirs for module detection
TOP_DIRS = {"src", "lib", "app", "packages", "fastapi_admin", "examples",
            "console", "core", "tests"}


def main():
    if not GRAPHIFY_GRAPH.exists():
        print("graphify graph.json not found, skipping summaries")
        return

    with open(GRAPHIFY_GRAPH, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Group nodes by source_file
    file_nodes: dict[str, list[dict]] = defaultdict(list)
    file_types: dict[str, set[str]] = defaultdict(set)
    file_communities: dict[str, set[int]] = defaultdict(set)

    for node in data.get("nodes", []):
        sf = node.get("source_file", "")
        if not sf:
            continue
        file_nodes[sf].append(node)
        file_types[sf].add(node.get("file_type", "?"))
        if "community" in node:
            file_communities[sf].add(node["community"])

    # Build cross-file dependency index
    node_index: dict[str, dict] = {n["id"]: n for n in data.get("nodes", [])}
    file_deps: dict[str, set[str]] = defaultdict(set)

    for link in data.get("links", []):
        src_node = node_index.get(link.get("source"))
        tgt_node = node_index.get(link.get("target"))
        if src_node and tgt_node:
            src_file = src_node.get("source_file", "")
            tgt_file = tgt_node.get("source_file", "")
            if src_file and tgt_file and src_file != tgt_file:
                file_deps[src_file].add(tgt_file)

    SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)

    written = 0
    for sf, nodes in sorted(file_nodes.items()):
        parts = sf.replace("\\", "/").split("/")
        module = parts[0] if parts else "root"

        symbols = [n["label"] for n in nodes if n.get("label") != sf]
        communities = file_communities.get(sf, set())
        deps = sorted(file_deps.get(sf, set()))

        text = f"# {sf}\n\n"
        text += f"Module: {module}\n"
        text += f"Type: {', '.join(sorted(file_types.get(sf, {'?'})))}\n"
        text += f"Community: {min(communities) if communities else 'N/A'}\n"
        text += f"Symbols ({len(symbols)}): {', '.join(symbols[:80])}"
        if len(symbols) > 80:
            text += f" ... (+{len(symbols) - 80} more)"
        text += "\n"

        if deps:
            text += f"Dependencies ({len(deps)}): {', '.join(deps[:30])}"
            if len(deps) > 30:
                text += f" ... (+{len(deps) - 30} more)"
            text += "\n"

        safe_name = sf.replace("\\", "_").replace("/", "_")
        out_path = SUMMARIES_DIR / f"{safe_name}.md"
        out_path.write_text(text, encoding="utf-8")
        written += 1

    print(f"Generated {written} summary files in {SUMMARIES_DIR}")


if __name__ == "__main__":
    main()
