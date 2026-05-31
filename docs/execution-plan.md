# Execution Plan

This document maps the generic v2 execution plan into open-source project assets.

Original source material was reviewed from private migration inputs and is not part of this repository:

- Generic CLAUDE.md governance execution plan.
- Starter kit archive.
- Open-source prelaunch material archive.

The source plans are not runtime context. Maintained behavior lives in package code, policy JSON, tests, and these docs.

## Delivered Assets

- CLI commands: `src/claude_md_governance/cli.py`.
- Installer and preset selection: `src/claude_md_governance/installer.py`.
- Package-managed templates: `src/claude_md_governance/data/templates/`.
- Policy presets: `src/claude_md_governance/data/templates/policies/`.
- Deterministic scoring: `src/claude_md_governance/lint.py`.
- Conservative repairs: `src/claude_md_governance/autofix.py`.
- Hook enforcement: `src/claude_md_governance/hook_guard.py`.
- Verification and mutation tests: `src/claude_md_governance/verify.py` and `tests/`.
- Public project materials: `README.md`, `CONTRIBUTING.md`, `SECURITY.md`, `GOVERNANCE.md`, `ROADMAP.md`, and `docs/`.

## Generic Installation Flow

```bash
claude-md-governance init --repo <repo> --preset generic --ci auto --yes
claude-md-governance verify --repo <repo>
```

The installer performs a conservative sequence:

- Detect or accept the preset.
- Back up existing files before overwrite or merge.
- Install common templates.
- Write `.claude-governance/policy.json`.
- Append missing root `CLAUDE.md` governance sections instead of replacing the file.
- Generate local `CLAUDE.md` files only for detected sensitive directories.
- Merge hooks into `.claude/settings.json`.
- Install CI assets only for the selected provider.
- Run verification unless skipped.

## Presets and CI Modes

Supported presets:

- `generic`: default, no Codeup assumption.
- `java-maven`: Maven-oriented thresholds and sensitive-module patterns.
- `enterprise-java-codeup`: example Java/Maven team preset with Codeup defaults.

Supported CI modes:

- `github`: install GitHub Actions workflow.
- `codeup`: install Codeup step and documentation.
- `none`: install no CI files.
- `auto`: infer from remote and preset.

## Repair Loop

The intended unattended loop is:

```bash
claude-md-governance lint --repo <repo> --output <repo>/.claude-governance/score.json
claude-md-governance autofix --repo <repo> --apply
claude-md-governance verify --repo <repo>
```

Autofix is intentionally limited. It may add missing sections, create local templates, and insert TODOs, but it must not invent business rules, banned dependencies, architecture history, or approval facts.

## Acceptance Commands

```bash
python -m pip install -e ".[test]"
python -m pytest -q
claude-md-governance --help
```
