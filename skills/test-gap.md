# Test Gap Analysis

Find high-impact symbols with zero test coverage. Uses gitnexus call graph + file path heuristics.

## When to Use

- After any build — check `knowledge/test-gap-report.md`
- Before adding features touching high fan-in symbols
- Code review: verify no critical gaps introduced

## Workflow

### 1. Read the report

Open `{project_dir}/knowledge/test-gap-report.md`.

### 2. For each Critical item

Show the user:
> "{symbol} has {fan_in} callers but zero test coverage. Risk: HIGH. Want me to write tests?"

If yes:
1. Read the module SKILL.md at `knowledge/gitnexus/generated/{module}/SKILL.md`
2. Understand the symbol's role, inputs, outputs, and callers
3. Find the appropriate test file (or create one)
4. Write targeted tests for the uncovered symbol

### 3. For Warning items

Note them contextually — suggest writing tests when working in that module.

### 4. Re-run after changes

After writing tests, the next build will re-run test_gap.py and update the report.

## Report Format

```markdown
# Test Gap Report — YYYY-MM-DD HH:MM

## Critical (high impact, zero coverage)
| Symbol | Module | Fan-in | Files affected | Risk |
|--------|--------|--------|---------------|------|

## Warning (moderate impact, zero coverage)
| Symbol | Module | Fan-in | Risk |
|--------|--------|--------|------|

## Summary
- Total core symbols: N
- Covered: X (Y%)
- Uncovered: Z
  - Critical: ...
  - Warning: ...
  - Low risk: ...
```

## Data Sources

- gitnexus graph → symbol-level call graph, fan-in/fan-out
- gitnexus SKILL.md → core symbols, entry points
- `knowledge/graphify-out/graph.json` → AST symbols, file-to-symbol mapping
- File path heuristics → `tests/`, `test_*.py`, `*.test.ts`, `*_test.go`
