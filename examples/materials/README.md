# Materials

The original research reports, execution plans, and starter kit archives were used to produce the public docs, package modules, and templates.

Raw local source paths and private workspace details are not required at runtime and should not be committed as project inputs.

## Source Materials

Local migration inputs:

- CLAUDE.md research report.
- Generic CLAUDE.md governance execution plan.
- onm-agent governance execution plan.
- Starter kit archive.
- Open-source prelaunch material archive.

These files are provenance for the migration, not repository dependencies.

## Migration Mapping

- Research summary -> `docs/research-basis.md`.
- Generic v2 execution plan -> `docs/execution-plan.md`, `docs/architecture.md`, and `docs/security-model.md`.
- onm-agent plan -> `docs/presets/onm-agent.md`.
- Starter-kit scripts -> package modules plus compatibility templates under `src/claude_md_governance/data/templates/common/scripts/`.
- Starter-kit policies -> `src/claude_md_governance/data/templates/policies/`.
- Prelaunch open-source materials -> root governance files and `docs/`.

## What Not To Commit

- Raw private reports or archives.
- Consumer repository secrets, real credentials, private CI tokens, or local browser/auth state.
- Long-form reports copied into `README.md` or installed `CLAUDE.md` files.
