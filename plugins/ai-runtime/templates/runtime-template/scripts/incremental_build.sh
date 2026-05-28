#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

CONFIG_FILE="$PROJECT_DIR/config/runtime.json"
SOURCE_PATH=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['source_path'])")

NOW=$(date +"%Y%m%d_%H%M")
BUILD_LOG="$PROJECT_DIR/logs/build/$NOW.log"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S')  $1" | tee -a "$BUILD_LOG"
}

log "=== INCREMENTAL BUILD (changed files only, no LLM) ==="
log "project: $PROJECT_DIR"
log "source: $SOURCE_PATH"

# 1. GitNexus — incremental
echo ""
echo "--- GITNEXUS (incremental) ---"

if command -v gitnexus &> /dev/null; then
    pushd "$SOURCE_PATH" > /dev/null
    gitnexus analyze . --skills 2>&1 | tee -a "$PROJECT_DIR/logs/graph/$NOW-gitnexus.log"
    popd > /dev/null
    GITNEXUS_SRC="$SOURCE_PATH/.claude/skills"
    GITNEXUS_DST="$PROJECT_DIR/knowledge/gitnexus"
    if [ -d "$GITNEXUS_SRC" ]; then
        mkdir -p "$GITNEXUS_DST"
        cp -rf "$GITNEXUS_SRC"/* "$GITNEXUS_DST"/
        log "gitnexus: synced to knowledge/gitnexus/"
    fi
    log "gitnexus: done"
else
    log "gitnexus: skipped (not available)"
fi

# 2. Graphify — update (AST only)
echo ""
echo "--- GRAPHIFY (incremental update) ---"

if command -v graphify &> /dev/null; then
    pushd "$SOURCE_PATH" > /dev/null
    graphify update . 2>&1 | tee -a "$PROJECT_DIR/logs/graph/$NOW-graphify.log"
    popd > /dev/null
    GRAPHIFY_SRC="$SOURCE_PATH/graphify-out"
    GRAPHIFY_DST="$PROJECT_DIR/knowledge/graphify-out"
    if [ -d "$GRAPHIFY_SRC" ]; then
        mkdir -p "$GRAPHIFY_DST"
        cp -rf "$GRAPHIFY_SRC"/* "$GRAPHIFY_DST"/
        log "graphify: synced to knowledge/graphify-out/"
    fi
    log "graphify: done"
else
    log "graphify: skipped (not available)"
fi

# 3. Summaries
echo ""
echo "--- SUMMARIES ---"
python3 "$PROJECT_DIR/scripts/generate_summaries_from_graph.py" 2>&1 | tee -a "$BUILD_LOG"
log "summaries: done"

# 4. Graph builder
echo ""
echo "--- GRAPH BUILDER ---"
python3 "$PROJECT_DIR/scripts/graph_builder.py" 2>&1 | tee -a "$PROJECT_DIR/logs/graph/$NOW-graph.log"
log "graph_builder: done"

# 5. Context
echo ""
echo "--- CONTEXT ---"
python3 "$PROJECT_DIR/scripts/generate_knowledge_artifacts.py" 2>&1 | tee -a "$BUILD_LOG"
log "context: done"

# 6. Test gap
echo ""
echo "--- TEST GAP ---"
python3 "$PROJECT_DIR/scripts/test_gap.py" 2>&1 | tee -a "$BUILD_LOG"
log "test-gap: done"

# Runtime log
RUNTIME_LOG="$PROJECT_DIR/logs/runtime/$NOW.log"
BRANCH=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['branch'])")
cat > "$RUNTIME_LOG" << RUNTIMEEOF
build: incremental
timestamp: $NOW
source: $SOURCE_PATH
branch: $BRANCH
build_log: $BUILD_LOG
RUNTIMEEOF

log "=== INCREMENTAL BUILD COMPLETE ==="
log "build log: $BUILD_LOG"
