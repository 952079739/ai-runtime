import json
import re
from pathlib import Path
from collections import defaultdict

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
KNOWLEDGE = PROJECT_DIR / "knowledge"
ARCH = KNOWLEDGE / "architecture"
CONTEXT = KNOWLEDGE / "context.md"
GRAPH_FILE = KNOWLEDGE / "global-graph" / "dependency-graph.json"
GRAPHIFY_GRAPH = KNOWLEDGE / "graphify-out" / "graph.json"
GRAPHIFY_ANALYSIS = KNOWLEDGE / "graphify-out" / ".graphify_analysis.json"

# --- helpers ---

def load_config():
    with open(PROJECT_DIR / "config" / "runtime.json", encoding="utf-8") as f:
        return json.load(f)

def load_gitnexus_data(source_path):
    """Parse gitnexus-generated SKILL.md files into structured module data.

    Reads from knowledge/gitnexus/generated/ first (synced by build scripts),
    falls back to <source>/.claude/skills/generated/ for backward compatibility.
    """
    # Primary: synced copy under knowledge/
    skills_dir = KNOWLEDGE / "gitnexus" / "generated"
    if not skills_dir.exists():
        # Fallback: read directly from source repo
        skills_dir = Path(source_path) / ".claude" / "skills" / "generated"
    if not skills_dir.exists():
        return []

    modules = []
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        try:
            text = skill_md.read_text(encoding="utf-8", errors="ignore")
            mod = _parse_gitnexus_skill(text, skill_md.parent.name)
            if mod:
                modules.append(mod)
        except Exception:
            pass
    return modules

def _parse_gitnexus_skill(text, dirname):
    """Parse a single gitnexus SKILL.md."""
    result = {"name": dirname, "description": "", "file_count": 0, "symbol_count": 0,
              "cohesion": None, "key_files": [], "entry_points": [], "key_symbols": []}

    # Parse frontmatter
    parts = text.split("---")
    if len(parts) >= 3:
        fm_text = parts[1]
        for line in fm_text.splitlines():
            m_fm = re.match(r"^\s*(\w+)\s*:\s*[\"']?(.*?)[\"']?\s*$", line)
            if m_fm:
                key = m_fm.group(1).lower()
                val = m_fm.group(2)
                if key == "name":
                    result["name"] = val
                elif key == "description":
                    result["description"] = val
        body = "---".join(parts[2:])
    else:
        body = text

    # Parse stats line: "119 symbols | 24 files | Cohesion: 88%"
    m = re.search(r"(\d+)\s+symbols?\s*\|\s*(\d+)\s+files?\s*\|\s*Cohesion:\s*(\d+)%", body)
    if m:
        result["symbol_count"] = int(m.group(1))
        result["file_count"] = int(m.group(2))
        result["cohesion"] = int(m.group(3))

    # Parse Key Files table
    in_key_files = False
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("## Key Files"):
            in_key_files = True
            continue
        if in_key_files:
            if stripped.startswith("##") or stripped.startswith("|"):
                if stripped.startswith("|") and not stripped.startswith("| File"):
                    parts_file = [p.strip() for p in stripped.split("|") if p.strip()]
                    if parts_file and "`" in parts_file[0]:
                        result["key_files"].append(parts_file[0].strip("`"))
                continue
            if stripped == "":
                continue
            break

    # Parse Entry Points
    in_entry_points = False
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("## Entry Points"):
            in_entry_points = True
            continue
        if in_entry_points:
            if stripped.startswith("##"):
                break
            if stripped.startswith("- **`"):
                # Extract symbol name and file path
                m_ep = re.match(r"- \*\*`(\w+)`\*\*", stripped)
                if m_ep and m_ep.group(1) not in [ep["name"] for ep in result["entry_points"]]:
                    result["entry_points"].append({"name": m_ep.group(1), "line": stripped})

    # Parse Key Symbols table
    in_key_symbols = False
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("## Key Symbols"):
            in_key_symbols = True
            continue
        if in_key_symbols:
            if stripped.startswith("##"):
                break
            if stripped.startswith("|") and not stripped.startswith("| Symbol"):
                parts_sym = [p.strip() for p in stripped.split("|") if p.strip()]
                if len(parts_sym) >= 2:
                    result["key_symbols"].append({"symbol": parts_sym[0].strip("`"), "type": parts_sym[1], "file": parts_sym[2] if len(parts_sym) >= 3 else ""})

    return result

def load_graph():
    if GRAPH_FILE.exists():
        with open(GRAPH_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"nodes": [], "edges": []}

def scan_source(source_path):
    """Build file tree, module map, and extract top-level definitions."""
    root = Path(source_path)
    modules = defaultdict(list)
    definitions = defaultdict(list)
    file_index = {}

    for py_file in root.rglob("*.py"):
        if any(skip in str(py_file) for skip in ["__pycache__", ".ai-runtime", ".gitnexus", "graphify-out"]):
            continue
        rel = py_file.relative_to(root)
        pkg = str(rel.parent).replace("\\", ".").replace("/", ".")
        modules[pkg].append(rel.name)
        file_index[str(py_file)] = str(rel)

        try:
            text = py_file.read_text(encoding="utf-8", errors="ignore")
            for line in text.splitlines():
                stripped = line.strip()
                # class definitions
                m = re.match(r"^class\s+(\w+)", stripped)
                if m:
                    definitions[str(rel)].append(("class", m.group(1)))
                # function definitions (top-level or method)
                m = re.match(r"^\s*def\s+(\w+)", stripped)
                if m:
                    indent = len(line) - len(line.lstrip())
                    kind = "method" if indent > 0 else "function"
                    definitions[str(rel)].append((kind, m.group(1)))
        except Exception:
            pass

    return modules, definitions, file_index

def build_import_summary(graph, file_index, source_path):
    """Map each module to its internal and external dependencies."""
    internal = defaultdict(set)
    external = defaultdict(set)
    source_root = str(Path(source_path).resolve())

    # Detect project package names from the file tree
    project_pkgs = set()
    for fpath in file_index:
        p = Path(file_index[fpath])
        if p.parts:
            project_pkgs.add(p.parts[0])

    for edge in graph.get("edges", []):
        src = edge["source"]
        tgt = edge["target"]
        src_rel = file_index.get(src, src)
        src_pkg = Path(src_rel).parent.as_posix().replace("/", ".")

        tgt_is_internal = (
            tgt.startswith(source_root) or
            any(tgt == pkg or tgt.startswith(pkg + ".") for pkg in project_pkgs)
        )

        if tgt_is_internal:
            tgt_pkg = tgt if "." in tgt else tgt
            if src_pkg != tgt_pkg:
                internal[src_pkg].add(tgt_pkg)
        else:
            external[src_pkg].add(tgt)

    return internal, external

def load_graphify_data():
    """Load semantic graph data from graphify output."""
    result = {}
    if GRAPHIFY_GRAPH.exists():
        try:
            with open(GRAPHIFY_GRAPH, encoding="utf-8") as f:
                gf = json.load(f)
            result["node_count"] = len(gf.get("nodes", []))
            result["link_count"] = len(gf.get("links", []))
        except Exception:
            result["node_count"] = 0
            result["link_count"] = 0

    if GRAPHIFY_ANALYSIS.exists():
        try:
            with open(GRAPHIFY_ANALYSIS, encoding="utf-8") as f:
                analysis = json.load(f)
            result["communities"] = analysis.get("communities", {})
            result["cohesion"] = analysis.get("cohesion", {})
            result["gods"] = analysis.get("gods", [])
            result["community_count"] = len(result["communities"])
        except Exception:
            result["communities"] = {}
            result["cohesion"] = {}
            result["gods"] = []
            result["community_count"] = 0
    else:
        result.update({"communities": {}, "cohesion": {}, "gods": [], "community_count": 0})

    return result


def get_dir_tree(source_path, max_depth=3):
    """Generate a compact directory tree."""
    root = Path(source_path)
    lines = []
    for path in sorted(root.rglob("*")):
        if any(skip in str(path) for skip in ["__pycache__", ".git", ".ai-runtime", ".gitnexus", "graphify-out", ".claude"]):
            continue
        rel = path.relative_to(root)
        depth = len(rel.parts) - 1
        if depth > max_depth:
            continue
        if path.is_dir():
            lines.append("  " * depth + f"{rel.parts[-1]}/")
        else:
            lines.append("  " * depth + f"{rel.parts[-1]}")
    return "\n".join(lines[:200])

def build_context():
    config = load_config()
    source_path = config["source_path"]
    project_name = config["project_name"]

    graph = load_graph()
    modules, definitions, file_index = scan_source(source_path)
    internal_deps, external_deps = build_import_summary(graph, file_index, source_path)

    ctx = []
    ctx.append(f"# {project_name} — AI Runtime Context\n")

    # --- 1. Project Overview ---
    ctx.append("## Project Overview\n")
    ctx.append(f"- **Source**: `{source_path}`")
    ctx.append(f"- **Git Remote**: `{config.get('git_remote', 'N/A')}`")
    ctx.append(f"- **Branch**: `{config.get('branch', 'N/A')}`")
    ctx.append(f"- **Graph**: {len(graph.get('nodes',[]))} nodes, {len(graph.get('edges',[]))} edges")
    ctx.append("")

    # --- 2. Directory Structure ---
    ctx.append("## Directory Structure\n")
    ctx.append("```")
    ctx.append(get_dir_tree(source_path))
    ctx.append("```\n")

    # --- 3. Module Map ---
    ctx.append("## Module Map\n")
    for pkg in sorted(modules.keys()):
        files = modules[pkg]
        pkg_label = pkg if pkg else "(root)"
        ctx.append(f"### `{pkg_label}`")
        for f in sorted(files):
            defs = definitions.get(f"{pkg}/{f}".replace("./", ""), [])
            if defs:
                items = ", ".join(f"{k} `{n}`" for k, n in defs[:10])
                ctx.append(f"  - `{f}` — {items}")
            else:
                ctx.append(f"  - `{f}`")
        ctx.append("")

    # --- 4. Internal Dependencies ---
    ctx.append("## Internal Dependencies\n")
    ctx.append("| Module | Depends On |")
    ctx.append("|--------|------------|")
    for pkg in sorted(internal_deps.keys()):
        deps = ", ".join(sorted(internal_deps[pkg])[:8])
        pkg_label = pkg if pkg else "(root)"
        ctx.append(f"| `{pkg_label}` | {deps} |")
    ctx.append("")

    # --- 5. External Dependencies ---
    ctx.append("## External Dependencies\n")
    ext_all = sorted(set(d for deps in external_deps.values() for d in deps))
    ctx.append(", ".join(f"`{d}`" for d in ext_all[:60]))
    ctx.append("\n")

    # --- 6. GitNexus Module Analysis ---
    ctx.append("## GitNexus Module Analysis\n")
    gitnexus_modules = load_gitnexus_data(source_path)

    if gitnexus_modules:
        ctx.append(f"_({len(gitnexus_modules)} modules)_\n")
        ctx.append("| Module | Files | Symbols | Cohesion |")
        ctx.append("|--------|-------|---------|----------|")
        for mod in gitnexus_modules:
            ctx.append(f"| `{mod['name']}` | {mod['file_count']} | {mod['symbol_count']} | {mod['cohesion']}% |" if mod['cohesion'] is not None else f"| `{mod['name']}` | {mod['file_count']} | {mod['symbol_count']} | - |")
        ctx.append("")

        for mod in gitnexus_modules:
            ctx.append(f"### {mod['name']}\n")
            if mod["key_files"]:
                ctx.append("**Key Files:**")
                for kf in mod["key_files"][:10]:
                    ctx.append(f"- `{kf}`")
                ctx.append("")
            if mod["entry_points"]:
                ctx.append("**Entry Points:**")
                for ep in mod["entry_points"][:5]:
                    ctx.append(f"- `{ep['name']}`")
                ctx.append("")
    else:
        ctx.append("_(no gitnexus skills found — run gitnexus analyze first)_\n")

    # --- 7. Graphify Semantic Analysis ---
    ctx.append("## Semantic Graph Analysis (Graphify)\n")
    graphify_data = load_graphify_data()

    if graphify_data:
        ctx.append(f"- **Semantic Nodes**: {graphify_data['node_count']}")
        ctx.append(f"- **Semantic Links**: {graphify_data['link_count']}")
        ctx.append(f"- **Communities**: {graphify_data['community_count']}")
        ctx.append("")

        # GODS — hub nodes
        gods = graphify_data.get("gods", [])
        if gods:
            ctx.append("### Hub Nodes (Most Connected)\n")
            ctx.append("| Node | Connections |")
            ctx.append("|------|-------------|")
            for g in gods[:10]:
                ctx.append(f"| `{g['label']}` | {g['degree']} |")
            ctx.append("")

        # Community summary
        communities = graphify_data.get("communities", {})
        if communities:
            ctx.append("### Community Map\n")
            for cid in sorted(communities.keys(), key=lambda k: len(communities[k]), reverse=True)[:10]:
                members = communities[cid][:8]
                cohesion = graphify_data.get("cohesion", {}).get(cid, "?")
                ctx.append(f"- **Community {cid}** (cohesion: {cohesion:.2f}, size: {len(communities[cid])})")
                for m in members:
                    ctx.append(f"  - `{m}`")
            ctx.append("")

    # --- 8. Key Definitions ---
    ctx.append("## Key Definitions\n")
    for file_path in sorted(definitions.keys()):
        defs = definitions[file_path]
        if defs:
            classes = [n for k, n in defs if k == "class"]
            funcs = [n for k, n in defs if k in ("function", "method")]
            parts = []
            if classes:
                parts.append(f"classes: {', '.join(classes[:10])}")
            if funcs:
                parts.append(f"functions: {', '.join(funcs[:15])}")
            ctx.append(f"- **{file_path}** — {'; '.join(parts)}")
    ctx.append("")

    # --- 9. Per-File Summaries ---
    ctx.append("## Per-File Summaries\n")
    summaries_dir = KNOWLEDGE / "summaries"
    if summaries_dir.exists():
        summary_files = sorted(summaries_dir.glob("*.md"))
        ctx.append(f"_({len(summary_files)} files)_\n")
        for sf in summary_files:
            ctx.append(f"### {sf.stem}\n")
            ctx.append(sf.read_text(encoding="utf-8", errors="ignore")[:4000])
            ctx.append("")
    else:
        ctx.append("_(no summaries generated yet — run full_build.ps1)_\n")

    # --- 10. Architecture Reports ---
    ctx.append("## Architecture Reports\n")
    arch_dir = KNOWLEDGE / "architecture"
    if arch_dir.exists():
        for af in sorted(arch_dir.glob("*.md")):
            ctx.append(f"### {af.stem}\n")
            ctx.append(af.read_text(encoding="utf-8", errors="ignore")[:5000])
            ctx.append("")

    # --- 11. Runtime Rules ---
    ctx.append("## Runtime Rules\n")
    ctx.append("- Preserve backward compatibility")
    ctx.append("- Incremental migration only")
    ctx.append("- Preserve plugin lifecycle / API surface")
    ctx.append("- Avoid breaking SPI")
    ctx.append("- All knowledge updates go through `incremental_build.ps1`")
    ctx.append("")

    # --- 12. Build Metadata ---
    ctx.append("## Build Metadata\n")
    ctx.append(f"- **schema_version**: node_link_data (networkx)")
    ctx.append(f"- **graph_file**: `{GRAPH_FILE}`")
    ctx.append(f"- **knowledge_root**: `{KNOWLEDGE}`")
    ctx.append(f"- **incremental_mode**: {config.get('incremental_mode', True)}")
    ctx.append("")

    CONTEXT.write_text("\n".join(ctx), encoding="utf-8")
    print(f"context generated ({len(ctx)} lines)")

def build_architecture():
    """Extract architecture insights from graph structure."""
    graph = load_graph()
    edges = graph.get("edges", [])
    nodes = [n["id"] for n in graph.get("nodes", [])]

    in_degree = defaultdict(int)
    out_degree = defaultdict(int)
    for e in edges:
        out_degree[e["source"]] += 1
        in_degree[e["target"]] += 1

    # Most depended-on files (hub nodes)
    ranked = sorted(in_degree.items(), key=lambda x: -x[1])[:20]
    arch_lines = ["# Architecture Analysis\n"]
    arch_lines.append("## Most Depended-On Files (Hub Nodes)\n")
    for path, count in ranked:
        name = Path(path).name
        arch_lines.append(f"- `{name}` — referenced by {count} other files")
    arch_lines.append("")

    arch_lines.append("## Top-Level Entry Points\n")
    for n in nodes:
        name = Path(n).name
        if name in ("app.py", "main.py", "__init__.py", "__main__.py"):
            rel = str(n)
            out = out_degree.get(n, 0)
            inn = in_degree.get(n, 0)
            arch_lines.append(f"- `{rel}` — imports {out}, imported-by {inn}")

    ARCH.mkdir(parents=True, exist_ok=True)
    (ARCH / "hub-nodes.md").write_text("\n".join(arch_lines), encoding="utf-8")
    print("architecture analysis generated")


if __name__ == "__main__":
    ARCH.mkdir(parents=True, exist_ok=True)
    build_context()
    build_architecture()
