# onm-agent preset

Chinese version: [../../presets/onm-agent.md](../../presets/onm-agent.md)

## Use case

`onm-agent` is an example preset for onm-agent-like Java/Maven repositories using Codeup. It is not the global default.

## Install

Input:

```bash
claude-md-governance init --repo <repo> --preset onm-agent --ci codeup --config-change-mode warn --yes
claude-md-governance verify --repo <repo>
```

Output:

```text
Preset: onm-agent; CI provider: codeup; ConfigChange mode: warn
Governance verification passed.
```

Failure handling:

- `Codeup CI instructions exists` fails: confirm `docs/ci/codeup-claude-md-governance.md`.
- Wrong behavior case path: policy should use `tests/ai_behavior_cases.onm-agent.json`.

## Defaults

- CI provider: `codeup`.
- Behavior cases: `tests/ai_behavior_cases.onm-agent.json`.
- Sensitive paths follow the Java/Maven direction.
- `ConfigChange`: `warn`.

## Boundary

This preset does not connect to real business systems, read private config, or call Codeup APIs. It only installs repository files and a pipeline-step example.
