# Open Source Project Guide

This repository is structured as a Python package with package data templates, deterministic tests, governance docs, and demo repositories. The long reports and starter-kit archives were migrated into maintainable project assets instead of being committed as runtime context.

## Contributor Flow

```bash
python -m pip install -e ".[test]"
python -m pytest -q
codex-md-governance doctor
```

Preset contributions should include policy changes, docs under `docs/presets/`, tests, and an example when practical.

## Documentation Layout

- `README.md`: project position, quick start, commands, and links only.
- `docs/research-basis.md`: summarized research basis.
- `docs/execution-plan.md`: generic v2 execution plan mapped to package assets.
- `docs/architecture.md`: component model and v2 migration fixes.
- `docs/security-model.md`: hook, CI, policy, and behavior-test safety boundaries.
- `docs/presets/`: preset-specific install and behavior notes.
- `docs/templates.md`: package template ownership and compatibility-script notes.
- `docs/verification.md`: local and installed-repo verification.
- `examples/materials/README.md`: how raw materials informed the project.

## Contribution Rules

- Keep `README.md` short. Add detailed background to `docs/`.
- Do not commit private source reports, local workspace paths beyond documentation provenance, or raw archives as required project inputs.
- Do not make team presets affect generic defaults.
- Keep behavior deterministic by default; optional Claude behavior tests must be clearly marked optional.
- Update package source and tests before mirroring behavior into downstream compatibility templates.
