"""Build a dependency graph by parsing imports in source files."""
from pathlib import Path
import networkx as nx
import json

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
CONFIG_FILE = PROJECT_DIR / "config" / "runtime.json"

with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    config = json.load(f)

SOURCE = Path(config["source_path"])
OUTPUT = PROJECT_DIR / "knowledge" / "global-graph"

graph = nx.DiGraph()

for file in SOURCE.rglob("*.py"):

    s = str(file)
    if any(skip in s for skip in [".ai-runtime", "__pycache__", ".gitnexus", "graphify-out", "node_modules", ".venv"]):
        continue

    try:
        text = file.read_text(encoding="utf-8", errors="ignore")
        graph.add_node(str(file))

        for line in text.splitlines():
            line = line.strip()

            if line.startswith("import "):
                dep = line.replace("import ", "").split(" as ")[0].strip()
                graph.add_edge(str(file), dep)

            elif line.startswith("from "):
                parts = line.split(" import ")
                if len(parts) >= 1:
                    dep = parts[0].replace("from ", "").strip()
                    graph.add_edge(str(file), dep)

    except Exception:
        pass

OUTPUT.mkdir(parents=True, exist_ok=True)

with open(OUTPUT / "dependency-graph.json", "w", encoding="utf-8") as f:
    json.dump(nx.readwrite.json_graph.node_link_data(graph), f, indent=2)

print("graph generated")
