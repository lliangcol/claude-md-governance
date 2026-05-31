# Project Governance

## Maintainer roles

- Core maintainer: owns releases, roadmap, and breaking changes.
- Policy maintainer: reviews new rules and presets.
- Security maintainer: reviews hooks, protected path logic, and CI integrations.
- Documentation maintainer: keeps examples and migration guides current.

## Decision process

- Small fixes: one maintainer approval.
- New policy rules: one policy maintainer approval and one test.
- Hook behavior changes: one security maintainer approval.
- Breaking changes: RFC issue and changelog entry.

## Release criteria

A release must pass:

```bash
python -m pip install -e .
python -m pytest -q
claude-md-governance doctor
claude-md-governance init --repo /tmp/generic-smoke --yes --preset generic --ci none
claude-md-governance verify --repo /tmp/generic-smoke
```

Plus at least one Java/Maven preset smoke test before v1.0.
