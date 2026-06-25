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
- Latest pushed maintenance commit before the current round:
  - `91295bb fix: require gitlab governance changes rule`
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

- `.\.venv\Scripts\python.exe -m pytest tests\test_package_behaviors.py::test_codeup_init_does_not_create_github_actions tests\test_package_behaviors.py::test_jenkins_init_installs_pipeline_and_verifies tests\test_package_behaviors.py::test_jenkins_pipeline_requires_change_request_and_governance_changes tests\test_package_behaviors.py::test_buildkite_init_installs_pipeline_and_verifies tests\test_package_behaviors.py::test_installed_lint_script_validates_policy_without_package_import tests\test_package_behaviors.py::test_policy_schema_rejects_container_shape_edges -q`: passed.
- `.\.venv\Scripts\python.exe -m pytest -q`: passed, `91 passed`.
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
- Report features still need the same targeted audit discipline as provider and
  copied-script changes.

## Highest Priority Candidates

1. P1: CI provider coverage now includes GitLab, Jenkins, Buildkite, and Codeup
   installer/template/docs/verify smoke checks, with GitLab and Jenkins rule
   shape covered for change-request plus governance-file gating.
2. P0: Policy schema edge coverage includes invalid scalar fields, container
   shape errors, and fallback-validator parity for verify/lint copied scripts.
3. P0: Copied-script no-package smoke coverage includes installed
   `verify_claude_governance.py`, `claude_hook_guard.py`, and
   `claude_md_lint.py`.

## Next Candidate

The previous remaining provider, copied-script, and policy schema hardening
tasks are covered. The next implementation slice should audit report-generation
behavior or release packaging, then add targeted tests only for a confirmed gap.
