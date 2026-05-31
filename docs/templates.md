# Templates

Package templates live under `src/claude_md_governance/data/templates/`.

Runtime installation copies only the assets selected by preset and CI provider.

## Common Templates

- `common/.claude/skills/claude-md-governance/SKILL.md`
- `common/scripts/*.py`
- `common/tests/ai_behavior_cases*.json`
- `common/docs/ai-context/README.md`

The copied scripts are compatibility entry points for downstream repositories. Maintained implementation lives in package modules under `src/claude_md_governance/`.

## Policy Templates

- `policies/generic.json`: stack-neutral defaults.
- `policies/java-maven.json`: Maven-sensitive module defaults.
- `policies/enterprise-java-codeup.json`: example team preset with Codeup defaults.

## CI Templates

- `github/workflows/claude-md-governance.yml` is installed to `.github/workflows/claude-md-governance.yml` only when `--ci github` or auto-detection chooses GitHub.
- `codeup/ci/codeup/claude-md-governance-step.yml` and `codeup/docs/ci/codeup-claude-md-governance.md` are installed only when `--ci codeup` or auto-detection chooses Codeup.
- `--ci none` installs no CI assets.

## Migration Notes

The original starter kit archive included standalone scripts and templates. In this repository:

- Package modules are the source of truth for lint, autofix, hooks, install, and verify behavior.
- Template scripts remain only so installed target repositories can run familiar `python scripts/...` commands.
- New template changes need tests that cover installed output, not just package imports.
