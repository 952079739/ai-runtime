from pathlib import Path
import hashlib
import json
import subprocess
import shutil
import argparse
import sys


def make_project_id():
    remote = subprocess.check_output(
        ["git", "remote", "get-url", "origin"]
    ).decode().strip()

    branch = subprocess.check_output(
        ["git", "branch", "--show-current"]
    ).decode().strip()

    raw = f"{remote}@{branch}"
    return hashlib.md5(raw.encode()).hexdigest()[:8]


def ensure_gitignore(source_path):
    """Append AI Runtime / GitNexus entries to source repo's .gitignore."""
    gi = Path(source_path) / ".gitignore"
    entries = [
        "\n# AI Runtime / GitNexus (generated, do not commit)\n",
        ".claude/\n",
        "AGENTS.md\n",
        "CLAUDE.md\n",
        ".gitnexus/\n",
        "graphify-out/\n",
    ]

    existing = gi.read_text(encoding="utf-8") if gi.exists() else ""

    to_add = []
    for e in entries:
        if e.strip().startswith("#") or e.strip() == "":
            to_add.append(e)
        elif e.strip() not in existing:
            to_add.append(e)

    if len(to_add) > 1:  # more than just the comment line
        with open(gi, "a", encoding="utf-8") as f:
            f.writelines(to_add)
        print(f"Updated .gitignore: {gi}")
    else:
        print(f".gitignore already up to date: {gi}")


def bootstrap(storage_root: str, template_dir: str):
    source_root = Path.cwd()
    project_name = source_root.name
    project_id = f"{project_name}_{make_project_id()}"

    template_path = Path(template_dir)
    projects_root = Path(storage_root) / "projects" / project_id

    # Create full directory structure
    dirs = [
        "config",
        "knowledge/architecture",
        "knowledge/global-graph",
        "knowledge/summaries",
        "logs/build",
        "logs/graph",
        "logs/claude",
        "logs/runtime",
        "tasks/active",
        "tasks/completed",
        "tasks/failed",
        "patches",
        "snapshots",
        "changelog",
        "scripts",
        "prompts",
    ]
    for d in dirs:
        (projects_root / d).mkdir(parents=True, exist_ok=True)

    # Copy scripts from template
    template_scripts = template_path / "scripts"
    if template_scripts.exists():
        for f in template_scripts.glob("*"):
            if f.name.startswith("__pycache") or f.name.endswith(".pyc"):
                continue
            dst = projects_root / "scripts" / f.name
            if not dst.exists():
                shutil.copy2(f, dst)

    # Copy CLAUDE.md template to project root
    template_claude = template_path / "CLAUDE.md"
    if template_claude.exists():
        dst_claude = projects_root / "CLAUDE.md"
        if not dst_claude.exists():
            shutil.copy2(template_claude, dst_claude)

    # Copy prompts from template
    template_prompts = template_path / "prompts"
    if template_prompts.exists():
        for f in template_prompts.glob("*"):
            dst = projects_root / "prompts" / f.name
            if not dst.exists():
                shutil.copy2(f, dst)

    # Generate runtime.json
    runtime_json = {
        "project_name": project_name,
        "project_id": project_id,
        "source_path": str(source_root.resolve()),
        "qdrant_collection": project_id,
        "knowledge_version": 1,
        "incremental_mode": True,
        "git_remote": subprocess.check_output(
            ["git", "remote", "get-url", "origin"]
        ).decode().strip(),
        "branch": subprocess.check_output(
            ["git", "branch", "--show-current"]
        ).decode().strip(),
        "template_version": "2.0",
    }

    with open(projects_root / "config" / "runtime.json", "w", encoding="utf-8") as f:
        json.dump(runtime_json, f, indent=2)

    # Auto-add AI Runtime / GitNexus entries to source repo's .gitignore
    ensure_gitignore(source_root)

    print(f"Runtime initialized: {project_id}")
    print(f"Project path: {projects_root}")
    return str(projects_root)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI-Runtime project bootstrap")
    parser.add_argument("--storage-root", required=True, help="AI-Runtime storage root directory")
    parser.add_argument("--template-dir", required=True, help="Path to templates/runtime-template")
    args = parser.parse_args()

    bootstrap(args.storage_root, args.template_dir)
