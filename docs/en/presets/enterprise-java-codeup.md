# enterprise-java-codeup preset

Chinese version: [../../presets/enterprise-java-codeup.md](../../presets/enterprise-java-codeup.md)

## Use case

`enterprise-java-codeup` is an example preset for enterprise-java-codeup Java/Maven repositories using Codeup. It is not the global default.

## Install

Input:

```bash
codex-md-governance init --repo <repo> --preset enterprise-java-codeup --ci codeup --config-change-mode warn --yes
codex-md-governance verify --repo <repo>
```

Output:

```text
Preset: enterprise-java-codeup; CI provider: codeup; ConfigChange mode: warn
Governance verification passed.
```

Failure handling:

- `Codeup CI instructions exists` fails: confirm `docs/ci/codeup-claude-md-governance.md`.
- Wrong behavior case path: policy should use `tests/ai_behavior_cases.enterprise-java-codeup.json`.

## Defaults

- CI provider: `codeup`.
- Behavior cases: `tests/ai_behavior_cases.enterprise-java-codeup.json`.
- Sensitive paths follow the Java/Maven direction.
- `ConfigChange`: `warn`.

## Boundary

This preset does not connect to real business systems, read private config, or call Codeup APIs. It only installs repository files and a pipeline-step example.
