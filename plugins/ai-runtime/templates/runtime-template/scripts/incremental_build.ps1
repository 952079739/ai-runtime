$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir

# Read config
$Config = Get-Content "$ProjectDir\config\runtime.json" | ConvertFrom-Json
$SourcePath = $Config.source_path

$Now = Get-Date -Format "yyyyMMdd_HHmm"
$BuildLog = "$ProjectDir\logs\build\$Now.log"

function Write-Log($msg) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  $msg"
    Add-Content -Path $BuildLog -Value $line
    Write-Host $msg
}

Write-Log "=== INCREMENTAL BUILD (changed files only, no LLM) ==="
Write-Log "project: $ProjectDir"
Write-Log "source: $SourcePath"

# 1. GitNexus — incremental (no -f), only re-indexes changed files
Write-Host ""
Write-Host "--- GITNEXUS (incremental) ---"

try {
    Push-Location $SourcePath
    gitnexus analyze . --skills 2>&1 | Tee-Object -FilePath "$ProjectDir\logs\graph\$Now-gitnexus.log" | Out-Host
    Pop-Location
    # Sync gitnexus output to knowledge/
    $GitNexusSrc = "$SourcePath\.claude\skills"
    $GitNexusDst = "$ProjectDir\knowledge\gitnexus"
    if (Test-Path $GitNexusSrc) {
        New-Item -ItemType Directory -Force -Path $GitNexusDst | Out-Null
        Copy-Item -Recurse -Force "$GitNexusSrc\*" $GitNexusDst
        Write-Log "gitnexus: synced to knowledge/gitnexus/"
    }
    Write-Log "gitnexus: done"
} catch {
    Write-Log "gitnexus: skipped (not available)"
}

# 2. Graphify — update mode (AST only, no LLM, changed files only)
Write-Host ""
Write-Host "--- GRAPHIFY (incremental update) ---"

try {
    Push-Location $SourcePath
    graphify update . 2>&1 | Tee-Object -FilePath "$ProjectDir\logs\graph\$Now-graphify.log" | Out-Host
    Pop-Location
    # Copy updated graph from source to knowledge/
    $GraphifySrc = "$SourcePath\graphify-out"
    $GraphifyDst = "$ProjectDir\knowledge\graphify-out"
    if (Test-Path $GraphifySrc) {
        New-Item -ItemType Directory -Force -Path $GraphifyDst | Out-Null
        Copy-Item -Recurse -Force "$GraphifySrc\*" $GraphifyDst
        Write-Log "graphify: synced to knowledge/graphify-out/"
    }
    Write-Log "graphify: done"
} catch {
    Write-Log "graphify: skipped (not available)"
}

# 3. Per-file summaries
Write-Host ""
Write-Host "--- SUMMARIES ---"

python "$ProjectDir\scripts\generate_summaries_from_graph.py" 2>&1 | ForEach-Object {
    Add-Content -Path $BuildLog -Value $_
    Write-Host $_
}
Write-Log "summaries: done"

# 4. Dependency graph
Write-Host ""
Write-Host "--- GRAPH BUILDER ---"

python "$ProjectDir\scripts\graph_builder.py" 2>&1 | Tee-Object -FilePath "$ProjectDir\logs\graph\$Now-graph.log" | Out-Host
Write-Log "graph_builder: done"

# 5. Context + architecture (integrates gitnexus + graphify data)
Write-Host ""
Write-Host "--- CONTEXT ---"

python "$ProjectDir\scripts\generate_knowledge_artifacts.py" 2>&1 | ForEach-Object {
    Add-Content -Path $BuildLog -Value $_
    Write-Host $_
}
Write-Log "context: done"

# 6. Test gap analysis
Write-Host ""
Write-Host "--- TEST GAP ---"

python "$ProjectDir\scripts\test_gap.py" 2>&1 | ForEach-Object {
    Add-Content -Path $BuildLog -Value $_
    Write-Host $_
}
Write-Log "test-gap: done"

# Runtime log
$RuntimeLog = "$ProjectDir\logs\runtime\$Now.log"
@"
build: incremental
timestamp: $Now
source: $SourcePath
branch: $($Config.branch)
build_log: $BuildLog
"@ | Set-Content -Path $RuntimeLog

Write-Log "=== INCREMENTAL BUILD COMPLETE ==="
Write-Log "build log: $BuildLog"
