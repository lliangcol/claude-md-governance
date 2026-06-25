# codex-md-governance Maintenance Status

Last updated: 2026-06-25

## Project Positioning

`codex-md-governance` is the primary CLI for policy-as-code management of
`AGENTS.md` / `CLAUDE.md`, hooks, CI templates, and verification reports.
`claude-md-governance` remains a legacy command alias and must stay compatible.

This repository is not an agent platform, CI replacement, permissions bypass
tool, or private knowledge distribution system. Root instructions should stay
short; detailed rules belong in docs, templates, skills, or policy reference
files.

## Current Branch State

- Branch: `feature/governance-hardening-roadmap`.
- Baseline install: `.venv\Scripts\python.exe -m pip install -e ".[test]"`.
- Current worktree has broad pre-existing uncommitted changes across docs,
  templates, scripts, package modules, examples, and tests. Treat those as
  in-flight work and avoid unrelated rewrites.
- `dist/`, caches, `*.egg-info`, local reports, and private machine paths must
  not be committed.

## Key Directories

- `src/claude_md_governance/`: package implementation and CLI entrypoint.
- `src/claude_md_governance/data/schemas/`: packaged policy schema assets.
- `src/claude_md_governance/data/templates/`: install templates for common files
  and CI providers.
- `scripts/`: repository-local script copies used by installed target repos.
- `tests/`: pytest coverage for CLI, installer, hook guard, schema, verify,
  behavior tests, and reports.
- `docs/`: architecture, policy, hook, security, provider, report, and
  verification docs.
- `.github/workflows/`: GitHub CI and governance workflows.

## Fact Sources

- CLI compatibility: `pyproject.toml` scripts and `src/claude_md_governance/cli.py`.
- Policy loading/defaults/migration: `src/claude_md_governance/policy.py` and
  `src/claude_md_governance/policy_schema.py`.
- Runtime policy schema: `src/claude_md_governance/data/schemas/policy.schema.json`.
- Hook guard behavior: `src/claude_md_governance/hook_guard.py`,
  `scripts/claude_hook_guard.py`, and
  `src/claude_md_governance/data/templates/common/scripts/claude_hook_guard.py`.
- Verify behavior: `src/claude_md_governance/verify.py` and
  `scripts/verify_claude_governance.py`.
- Governance CI gate: `.github/workflows/claude-md-governance.yml`.
- Architecture and policy docs: `docs/architecture.md` and
  `docs/policy-reference.md`.

## Verification Commands

Use the repository virtual environment on this machine:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\codex-md-governance.exe doctor --repo .
.\.venv\Scripts\codex-md-governance.exe verify --repo .
.\.venv\Scripts\python.exe scripts\claude_md_lint.py --policy .claude-governance\policy.json --output .claude-governance\score.json
.\.venv\Scripts\python.exe scripts\verify_claude_governance.py
git diff --check
```

## Latest Baseline

Run on 2026-06-25:

- `.\.venv\Scripts\python.exe -m pip install -e ".[test]"`: passed.
- `.\.venv\Scripts\python.exe -m pytest -q`: passed, `83 passed`.
- `.\.venv\Scripts\codex-md-governance.exe doctor --repo .`: passed.
- `.\.venv\Scripts\codex-md-governance.exe verify --repo .`: passed.

## Known Risks

- Large dirty worktree makes scope control important; review only files touched
  in the current round unless explicitly asked to reconcile all changes.
- Hook guard behavior has synchronized copies; any hook change must update all
  copies and tests together.
- Policy schema has both a packaged JSON Schema and a standard-library runtime
  validator; user-visible behavior depends on the runtime validator.
- New CI providers and report features appear in-flight; do not assume they are
  release-ready without targeted provider/report smoke tests.

## Highest Priority Candidates

1. P0: Expand policy schema and verify regression tests for invalid scalar
   types, especially JSON bool values in integer fields.
2. P0: Audit copied `scripts/verify_claude_governance.py` fallback validation
   against `policy_schema.py` so target repos without the installed package fail
   closed consistently.
3. P1: Pick exactly one new CI provider and verify installer, template, docs,
   fixture, and smoke behavior end to end.

## Next Candidate

After this status pass, the smallest next slice is to compare the repository
verify script fallback validator with package `policy_schema.py`, then either
document the intentional reduced surface or sync the missing checks with tests.
