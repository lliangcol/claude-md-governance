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
- Current worktree was clean at the start of the 2026-06-25 maintenance round,
  with `HEAD...@{u}` at `0 0`.
- Latest pushed maintenance commits:
  - `97a3018 feat: expand governance providers and reports`
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

Initial status run on 2026-06-25:

- `.\.venv\Scripts\python.exe -m pip install -e ".[test]"`: passed.
- `.\.venv\Scripts\python.exe -m pytest -q`: passed, `83 passed`.
- `.\.venv\Scripts\codex-md-governance.exe doctor --repo .`: passed.
- `.\.venv\Scripts\codex-md-governance.exe verify --repo .`: passed.

Latest validation run after fallback-validator alignment:

- `.\.venv\Scripts\python.exe -m pytest tests\test_validation_system.py::test_verify_script_fallback_policy_validator_matches_core_schema -q`: passed.
- `.\.venv\Scripts\python.exe -m pytest -q`: passed, `84 passed`.
- `.\.venv\Scripts\codex-md-governance.exe doctor --repo .`: passed.
- `.\.venv\Scripts\codex-md-governance.exe verify --repo .`: passed.
- `.\.venv\Scripts\python.exe scripts\claude_md_lint.py --policy .claude-governance\policy.json --output .claude-governance\score.json`: passed.
- `.\.venv\Scripts\python.exe scripts\verify_claude_governance.py`: passed.
- `git diff --check`: passed.

Current round targeted validation:

- `.\.venv\Scripts\python.exe -m pytest tests\test_package_behaviors.py::test_installed_verify_script_validates_policy_without_package_import tests\test_package_behaviors.py::test_installed_verify_script_allows_parallel_runs -q`: passed.
- `.\.venv\Scripts\python.exe -m pytest -q`: passed, `86 passed`.
- `git diff --check`: passed.
- `.\.venv\Scripts\python.exe scripts\claude_md_lint.py --policy .claude-governance\policy.json --output .claude-governance\score.json`: passed, score `100`.
- `.\.venv\Scripts\python.exe scripts\verify_claude_governance.py`: passed.
- `.\.venv\Scripts\codex-md-governance.exe doctor --repo .`: passed.
- `.\.venv\Scripts\codex-md-governance.exe verify --repo .`: passed.

## Known Risks

- Maintenance rounds should stay PR-sized; review only files touched in the
  current round unless explicitly asked to reconcile all changes.
- Hook guard behavior has synchronized copies; any hook change must update all
  copies and tests together.
- Policy schema has both a packaged JSON Schema and a standard-library runtime
  validator; user-visible behavior depends on the runtime validator.
- New CI providers and report features appear in-flight; do not assume they are
  release-ready without targeted provider/report smoke tests.

## Highest Priority Candidates

1. P1: Pick exactly one new CI provider and verify installer, template, docs,
   fixture, and smoke behavior end to end.
2. P0: Continue policy schema regression coverage for edge cases not covered by
   `test_verify_script_fallback_policy_validator_matches_core_schema`.
3. P0: Continue focused installed-template smoke coverage for copied script
   behavior when the target repository does not have the package import
   available. The installed `verify_claude_governance.py` fallback validator is
   covered; remaining copied scripts can still use targeted no-package smoke
   tests.

## Next Candidate

The fallback validator comparison is complete and pushed in `97a3018`; the
installed verify-script no-package smoke regression and concurrent verify
cleanup behavior are covered in the current round. The next implementation
slice should either continue installed-script smoke coverage or pick exactly one
CI provider, preferably GitLab because working-tree evidence already contains
GitLab installer support, template files, and docs. A correct GitLab slice
likely exceeds three files, so either get explicit approval to widen that round
or split it carefully without shipping a partially usable provider.
