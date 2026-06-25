# Java Maven preset

Chinese version: [../../presets/java-maven.md](../../presets/java-maven.md)

## Use case

`java-maven` fits single-module or multi-module Maven repositories. It adds Java/Maven thresholds and sensitive directory matching without binding the repo to GitHub, GitLab, Jenkins, Buildkite, or Codeup.

## Install

Input:

```bash
codex-md-governance init --repo . --preset java-maven --ci github --config-change-mode warn --yes
codex-md-governance verify --repo .
```

Output:

```text
Preset: java-maven; CI provider: github; ConfigChange mode: warn
Governance verification passed.
```

Failure handling:

- Missing local `AGENTS.md` under a sensitive directory: create it or tune `sensitive_paths`.
- Maven command failure: check whether the substituted `{module}` matches the real Maven module name.

## Defaults

- Root `AGENTS.md`: `warn_lines=180`, `max_lines=230`, `hard_fail_lines=280`.
- Required sections: Priority and Scope, Architecture Boundaries, Core Engineering Rules, Change Control, Do NOT introduce.
- Sensitive paths: payment, order, refund, consumer/MQ, migration.
- Related test template: `mvn -pl {module} -am test`.
- `ConfigChange`: `warn`.

## Note

`PostToolUse` only runs related tests when `CLAUDE_GOVERNANCE_RUN_TESTS=1` is set. Otherwise it emits a warning to avoid unexpected long local test runs.
