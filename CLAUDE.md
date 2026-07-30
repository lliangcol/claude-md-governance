# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Project Overview

This repository publishes the `codex-md-governance` Python CLI (installed as both `codex-md-governance` and the legacy alias `claude-md-governance`) for installing, linting, repairing, and verifying `AGENTS.md`/`CLAUDE.md` governance in downstream repositories. It ships policy-as-code (`.claude-governance/policy.json`), Claude Code hook definitions, and CI templates so that repo rules for AI coding agents are enforced deterministically instead of just being prose in a context file.

Optimization priority: correctness > security > maintainability > speed.

# Tech Stack

- Python >= 3.10, no runtime dependencies (`pyproject.toml`).
- `pytest` for tests; `build` + `twine` for packaging (see `[project.optional-dependencies]`).
- `src/` layout package: `claude_md_governance`.

# Do NOT introduce

- Do not introduce new frameworks, state managers, UI libraries, databases, or test runners without explicit approval.
- Do not add runtime dependencies for convenience when the standard library is sufficient.
- Do not add project-specific banned dependencies or business invariants to generic presets without evidence — use TODO placeholders when facts are unknown (see CONTRIBUTING.md).

# Commands

```bash
python -m pip install -e ".[test]"          # editable install with test deps
python -m pytest -q                         # run full test suite
python -m pytest tests/test_package_behaviors.py::test_generic_install_verify_passes  # single test
claude-md-governance doctor                 # alias for `verify`; smoke-checks this repo's own governance install
claude-md-governance init --repo /tmp/x --yes --preset generic --ci none
claude-md-governance verify --repo /tmp/x
python scripts/claude_md_lint.py --policy .claude-governance/policy.json --output .claude-governance/score.json
python scripts/verify_claude_governance.py
```

CI mirrors these commands (see `.github/workflows/`): `ci.yml` runs pytest + doctor + package build/twine/wheel-smoke across OS/Python matrices; `claude-md-governance.yml` runs the static lint + governance smoke script whenever `AGENTS.md`/`CLAUDE.md`/`.claude*`/`.codex*` change; `release-build.yml` builds and publishes wheel assets on `v*` tags.

# Architecture

CLI entry point `src/claude_md_governance/cli.py` dispatches subcommands (`init`, `lint`, `autofix`, `hook`, `verify`, `eval`, `behavior-test`, `doctor`) to focused modules:

- `installer.py` — copies `data/templates/` (common files, CI provider templates, preset policies) into a target repo and merges `.claude/settings.json` / policy files non-destructively.
- `lint.py` — deterministic scorer: reads `.claude-governance/policy.json` plus the root instruction file and produces a score report (line/token budgets, required sections, vague-phrase detection, protected paths, hook coverage).
- `autofix.py` — conservative, non-inventive repair of lint failures (creates placeholders/hook registrations; must never invent business rules).
- `hook_guard.py` — implements the actual Claude Code hook behavior (`PreToolUse` blocks protected-path writes before they happen; `PostToolUse` can run checks after a write but cannot roll it back; `ConfigChange` is `block`/`warn`/`off` per policy). Hook commands must stay on an allowlist and run without shell chaining — never introduce shell string interpolation here.
- `verify.py` — post-install smoke verification (structure + hook + lint pass) used by `verify`/`doctor`.
- `behavior.py` — optional, non-gating LLM behavior tests driven by `claude --bare -p` against `tests/ai_behavior_cases*.json`; skipped (not failed) when the Claude CLI is unavailable, unless `--require-claude`.
- `data/templates/` — `common/` (shared scaffolding: skills, scripts, docs), `github/` and `codeup/` (CI provider templates), `policies/` (`generic`, `java-maven`, `enterprise-java-codeup` preset JSON).

Data flow: `init` picks a preset/CI provider/config-mode → installer copies templates and merges policy/settings → `lint` scores the root doc against that policy → `hook_guard` enforces the same policy live in Claude Code → CI re-runs lint/verify to catch drift.

This repo dogfoods its own tool: root `AGENTS.md`/`CLAUDE.md` and `.claude-governance/policy.json` are the actual governance config Claude Code operates under here — changes to CLI behavior that affect installed output should keep these root files consistent with what `init` would generate.

Command-surface changes must stay consistent across `cli.py`, the template scripts under `data/templates/common/scripts/` (and root `scripts/`), README, and both `docs/` (Chinese) and `docs/en/` (English) — the two doc trees are parallel translations, not duplicates to reconcile ad hoc.

# Code Rules

- Use explicit types at public boundaries.
- Keep functions focused; split large functions when one function mixes validation, I/O, and transformation.
- Do not leave commented-out code, debug logs, or unowned TODOs.
- Prefer existing repository patterns over introducing new abstractions.

# Context Map

- Architecture overview: docs/architecture.md
- Policy reference: docs/policy-reference.md
- Verification guide: docs/verification.md
- AI long-form context: docs/ai-context/
- Archive/deprecated docs: docs/archive/ — do not read unless explicitly requested.

# Quality Gates

- Lint AGENTS.md when it changes.
- Block protected path edits unless explicitly approved.
- Run related tests for sensitive modules when CLAUDE_GOVERNANCE_RUN_TESTS=1.
- Keep root AGENTS.md under the configured line and token budget.
- After template/CLI structural changes, run `python -m pytest -q` and at least one `init`/`verify` smoke test (per docs/architecture.md).

# Working Style

- For complex changes, propose a short plan before editing.
- For trivial fixes, edit directly and summarize the diff.
- If uncertain, state assumptions and choose the conservative path.

# Sensitive Areas

- Read local AGENTS.md files before editing sensitive modules.
- Ask for explicit approval before modifying public APIs, auth, billing/payment, database schema, migrations, or infrastructure.
