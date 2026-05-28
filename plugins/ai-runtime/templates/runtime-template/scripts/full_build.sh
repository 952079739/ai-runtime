#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Read config
CONFIG_FILE="$PROJECT_DIR/config/runtime.json"
SOURCE_PATH=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['source_path'])")

NOW=$(date +"%Y%m%d_%H%M")
BUILD_LOG="$PROJECT_DIR/logs/build/$NOW.log"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S')  $1" | tee -a "$BUILD_LOG"
}

log "============================================"
log "=== FULL BUILD (full re-index + LLM) ==="
log "============================================"
log "project: $PROJECT_DIR"
log "source: $SOURCE_PATH"

# 1. GitNexus — full
echo ""
echo "=== GITNEXUS (full) ==="

if command -v gitnexus &> /dev/null; then
    pushd "$SOURCE_PATH" > /dev/null
    gitnexus analyze . --skills -f 2>&1 | tee -a "$PROJECT_DIR/logs/graph/$NOW-gitnexus.log"
    popd > /dev/null
    # Sync gitnexus output
    GITNEXUS_SRC="$SOURCE_PATH/.claude/skills"
    GITNEXUS_DST="$PROJECT_DIR/knowledge/gitnexus"
    if [ -d "$GITNEXUS_SRC" ]; then
        mkdir -p "$GITNEXUS_DST"
        cp -rf "$GITNEXUS_SRC"/* "$GITNEXUS_DST"/
        log "gitnexus: synced to knowledge/gitnexus/"
    fi
    log "gitnexus: done"

    # Build CLAUDE.md: merge AI-Runtime section with gitnexus section
    CLAUDE_MD="$SOURCE_PATH/CLAUDE.md"
    TEMPLATE_CLAUDE_MD="$PROJECT_DIR/CLAUDE.md"
    if [ ! -f "$TEMPLATE_CLAUDE_MD" ]; then
        TEMPLATE_CLAUDE_MD="$SCRIPT_DIR/../CLAUDE.md"
    fi
    PROJECT_NAME=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['project_name'])")

    if [ -f "$TEMPLATE_CLAUDE_MD" ]; then
        # Extract AI-Runtime section from template
        AI_SECTION=$(sed -n '/<!-- AI-Runtime:start -->/,/<!-- AI-Runtime:end -->/p' "$TEMPLATE_CLAUDE_MD" | sed '1d;$d')
        AI_SECTION="${AI_SECTION//\{\{PROJECT_NAME\}\}/$PROJECT_NAME}"
    fi

    if [ -z "$AI_SECTION" ]; then
        AI_SECTION="
# $PROJECT_NAME — AI Runtime Build Rules

## Build Modes
| Mode | Command | When |
|------|---------|------|
| **Full** | \`full_build.sh\` | Doc/image/config changes, new project init |
| **Incremental** | \`incremental_build.sh\` | Code-only changes |

Quick rule: \`*.md\` / \`*.png\` / \`*.json\` / \`*.yaml\` / directory changes → full build. Pure code → incremental.
"
    fi

    if [ -f "$CLAUDE_MD" ]; then
        if grep -q '<!-- AI-Runtime:start -->' "$CLAUDE_MD"; then
            # Replace existing AI-Runtime section
            python3 -c "
import re
existing = open('$CLAUDE_MD').read()
section = '''$AI_SECTION'''
merged = re.sub(r'<!-- AI-Runtime:start -->.*?<!-- AI-Runtime:end -->', f'<!-- AI-Runtime:start -->\n{section}\n<!-- AI-Runtime:end -->', existing, flags=re.DOTALL)
open('$CLAUDE_MD', 'w').write(merged)
"
        else
            # Prepend
            echo -e "<!-- AI-Runtime:start -->\n$AI_SECTION\n<!-- AI-Runtime:end -->\n\n$(cat "$CLAUDE_MD")" > "$CLAUDE_MD"
        fi
    else
        echo -e "<!-- AI-Runtime:start -->\n$AI_SECTION\n<!-- AI-Runtime:end -->\n\n<!-- gitnexus:start -->\n<!-- gitnexus:end -->\n" > "$CLAUDE_MD"
    fi
    cp -f "$CLAUDE_MD" "$PROJECT_DIR/CLAUDE.md"
    log "CLAUDE.md: merged AI-Runtime + gitnexus sections"
else
    log "gitnexus: skipped (not available)"
fi

# 2. Graphify — full + LLM
echo ""
echo "=== GRAPHIFY (full + LLM) ==="

if command -v graphify &> /dev/null; then
    if [ -z "$DEEPSEEK_API_KEY" ]; then
        echo ""
        echo "============================================"
        echo "  DEEPSEEK_API_KEY is not set"
        echo "  Run this in terminal, then retry:"
        case "$(uname -s)" in
            Darwin*) echo "  export DEEPSEEK_API_KEY=your-key" ;;
            Linux*)  echo "  export DEEPSEEK_API_KEY=your-key" ;;
            MINGW*|MSYS*|CYGWIN*) echo "  setx DEEPSEEK_API_KEY your-key" ;;
            *)       echo "  export DEEPSEEK_API_KEY=your-key" ;;
        esac
        echo "============================================"
        echo ""
        exit 1
    fi
    pushd "$SOURCE_PATH" > /dev/null
    graphify extract . --backend deepseek --out "$PROJECT_DIR/knowledge" 2>&1 | tee -a "$PROJECT_DIR/logs/graph/$NOW-graphify.log"
    popd > /dev/null
    log "graphify: done"
else
    log "graphify: skipped (not available)"
fi

# 3. Summaries
echo ""
echo "=== SUMMARIES ==="
python3 "$PROJECT_DIR/scripts/generate_summaries_from_graph.py" 2>&1 | tee -a "$BUILD_LOG"
log "summaries: done"

# 4. Custom graph
echo ""
echo "=== CUSTOM GRAPH ==="
python3 "$PROJECT_DIR/scripts/graph_builder.py" 2>&1 | tee -a "$PROJECT_DIR/logs/graph/$NOW-graph.log"
log "graph_builder: done"

# 5. Context
echo ""
echo "=== CONTEXT ==="
python3 "$PROJECT_DIR/scripts/generate_knowledge_artifacts.py" 2>&1 | tee -a "$BUILD_LOG"
log "context: done"

# 6. Test gap analysis
echo ""
echo "=== TEST GAP ==="
python3 "$PROJECT_DIR/scripts/test_gap.py" 2>&1 | tee -a "$BUILD_LOG"
log "test-gap: done"

# Runtime log
RUNTIME_LOG="$PROJECT_DIR/logs/runtime/$NOW.log"
BRANCH=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['branch'])")
cat > "$RUNTIME_LOG" << RUNTIMEEOF
build: full
timestamp: $NOW
source: $SOURCE_PATH
branch: $BRANCH
build_log: $BUILD_LOG
RUNTIMEEOF

log "============================================"
log "=== FULL BUILD COMPLETE ==="
log "============================================"
log "build log: $BUILD_LOG"
