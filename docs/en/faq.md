# FAQ

Chinese version: [../faq.md](../faq.md)

## Does this write AGENTS.md for me?

`init` creates a skeleton and fills missing sections, but maintainers still need to add real architecture, banned dependencies, and sensitive boundaries.

## Why does PostToolUse not undo writes?

Because `PostToolUse` runs after the tool action. It can fail and stop the next flow, but files already written are not automatically restored.

## Can I skip CI?

Yes:

```bash
codex-md-governance init --repo . --preset generic --ci none --yes
```

Output: no GitHub, GitLab, Jenkins, Buildkite, or Codeup CI files.
Failure handling: still run `codex-md-governance verify --repo .` locally.

## How do I generate only a GitLab pipeline?

```bash
codex-md-governance init --repo . --preset generic --ci gitlab --yes
```

Failure handling: use `--force` if an existing `.gitlab-ci.yml` should be overwritten.

## How do I generate only a Jenkins pipeline?

```bash
codex-md-governance init --repo . --preset generic --ci jenkins --yes
```

Failure handling: use `--force` if an existing `Jenkinsfile` should be overwritten.

## How do I generate only a Buildkite pipeline?

```bash
codex-md-governance init --repo . --preset generic --ci buildkite --yes
```

Failure handling: use `--force` if an existing `.buildkite/pipeline.yml` should be overwritten.

## How do I generate only a Codeup example?

```bash
codex-md-governance init --repo . --preset enterprise-java-codeup --ci codeup --config-change-mode warn --yes
```

Failure handling: use `--force` if managed files already exist.

## Why were behavior tests skipped?

They skip by default when Claude CLI is missing. To require them:

```bash
codex-md-governance behavior-test --repo . --require-claude
```

Failure handling: install and log in to Claude CLI, or remove `--require-claude`.

## How do I contribute a preset?

Add policy JSON, Chinese docs, English docs, tests, and examples. Run at least:

```bash
python -m pytest -q
codex-md-governance verify --repo .
```
