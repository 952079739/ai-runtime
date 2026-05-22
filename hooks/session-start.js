const { execSync } = require('child_process');
const { existsSync, readFileSync } = require('fs');
const path = require('path');
const os = require('os');
const crypto = require('crypto');

// ---- Helpers ----

function checkCmd(cmd) {
    try {
        execSync(cmd, { stdio: 'pipe', timeout: 10000 });
        return { ok: true };
    } catch {
        return { ok: false };
    }
}

function checkPythonPackage(pkg) {
    try {
        execSync(`python -c "import ${pkg}"`, { stdio: 'pipe', timeout: 15000 });
        return { name: pkg, ok: true };
    } catch {
        return { name: pkg, ok: false };
    }
}

function checkQdrant() {
    try {
        const out = execSync('docker ps --filter name=qdrant --format "{{.Names}}"', { stdio: 'pipe', timeout: 10000 }).toString().trim();
        return { ok: out === 'qdrant', running: out === 'qdrant' };
    } catch {
        return { ok: false, running: false };
    }
}

// ---- Phase 1: Environment detection ----

const systemTools = [
    { name: 'git', cmd: 'git --version' },
    { name: 'node', cmd: 'node -v' },
    { name: 'npm', cmd: 'npm -v' },
    { name: 'docker', cmd: 'docker --version' },
];
const sysResults = systemTools.map(t => ({ ...t, ...checkCmd(t.cmd) }));

const pyPackages = [
    'graphifyy', 'networkx', 'qdrant_client', 'sentence_transformers',
    'faiss', 'numpy', 'pandas', 'orjson', 'rich', 'typer', 'pydantic',
    'git', 'watchdog', 'tqdm', 'tree_sitter', 'langchain', 'langchain_community',
    'openai', 'anthropic',
];
const pyResults = pyPackages.map(checkPythonPackage);

const qdrant = checkQdrant();

// ---- Phase 2: Project detection ----

const homeConfig = path.join(os.homedir(), '.claude', 'ai-runtime-config.json');
let config = null;
if (existsSync(homeConfig)) {
    try {
        config = JSON.parse(readFileSync(homeConfig, 'utf-8'));
    } catch {
        config = null;
    }
}

let isGitRepo = false;
let projectStatus = 'no_git';
let projectName = '';
try {
    const topLevel = execSync('git rev-parse --show-toplevel', { stdio: 'pipe', timeout: 5000 }).toString().trim();
    isGitRepo = true;
    projectName = path.basename(topLevel);
} catch {
    isGitRepo = false;
}

if (config && config.storage_root && isGitRepo) {
    try {
        const remote = execSync('git remote get-url origin', { stdio: 'pipe', timeout: 5000 }).toString().trim();
        const branch = execSync('git branch --show-current', { stdio: 'pipe', timeout: 5000 }).toString().trim();
        const hash = crypto.createHash('md5').update(`${remote}@${branch}`).digest('hex').slice(0, 8);
        const projectId = `${projectName}_${hash}`;
        const projectPath = path.join(config.storage_root, 'projects', projectId);
        if (existsSync(projectPath)) {
            projectStatus = 'initialized';
        } else {
            projectStatus = 'new_project';
        }
    } catch {
        projectStatus = 'detect_error';
    }
}

// ---- Phase 3: LLM backend check ----

let backendStatus = 'not_configured';
let backendName = null;
if (config && config.llm_backend) {
    backendName = config.llm_backend;
    backendStatus = 'configured';
}

// ---- Output ----

console.log('');
console.log('[AI-Runtime] Environment check:');

// System tools
const sysOk = sysResults.every(r => r.ok);
sysResults.forEach(r => {
    console.log(`  ${r.ok ? 'PASS' : 'FAIL'}  ${r.name}`);
});
if (!sysOk) {
    const missing = sysResults.filter(r => !r.ok).map(r => r.name).join(', ');
    console.log(`  → Missing: ${missing}. Please install before running /bootstrap.`);
}

// Python packages
const pyOk = pyResults.every(r => r.ok);
const pyPassed = pyResults.filter(r => r.ok).length;
console.log(`  ${pyOk ? 'PASS' : 'WARN'}  Python packages: ${pyPassed}/${pyPackages.length}`);
if (!pyOk) {
    const missingPy = pyResults.filter(r => !r.ok).map(r => r.name).join(', ');
    console.log(`  → Missing packages: ${missingPy}`);
    console.log('  → Run: pip install -r requirements.txt (from AI-Runtime template)');
}

// Qdrant
console.log(`  ${qdrant.ok ? 'PASS' : 'WARN'}  Qdrant vector DB`);
if (!qdrant.ok) {
    const storageRoot = config ? config.storage_root : '<storage_root>';
    console.log(`  → Start with: docker run -d --name qdrant -p 6333:6333 -v ${storageRoot}/qdrant-data:/qdrant/storage qdrant/qdrant`);
}

// Config status
if (!config) {
    console.log('');
    console.log('[AI-Runtime] No config found. Run /bootstrap to set up.');
} else if (!config.storage_root) {
    console.log('');
    console.log('[AI-Runtime] Storage root not set. Run /bootstrap to configure.');
} else if (!isGitRepo) {
    console.log('');
    console.log('[AI-Runtime] Not a git repository. AI-Runtime skipped.');
} else if (projectStatus === 'initialized') {
    console.log('');
    console.log(`[AI-Runtime] Ready. ${projectName} (backend: ${backendName || 'not set'})`);
} else if (projectStatus === 'new_project') {
    console.log('');
    console.log(`[AI-Runtime] New project: ${projectName}. Run /bootstrap to initialize.`);
}

if (backendStatus === 'not_configured' && config && config.storage_root) {
    console.log('[AI-Runtime] LLM backend not configured. Run /bootstrap to set up.');
}

console.log('');
