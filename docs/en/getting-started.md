# Getting Started

Chinese version: [../getting-started.md](../getting-started.md)

## Generic quick start

Input:

```bash
pip install claude-md-governance
claude-md-governance init --repo . --preset generic --ci github --yes
claude-md-governance verify --repo .
```

Output:

```text
Installed CLAUDE.md governance into <repo>
Preset: generic; CI provider: github; ConfigChange mode: block
Governance verification passed.
```

Failure handling:

- `Repo not found`: check that `--repo` points at the repository root.
- `Use --yes for non-interactive installation.`: add `--yes`.
- `Governance verification failed`: read the failed item and `.claude-governance/score.json`.

## onm-agent / Codeup example

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

- If Codeup docs are missing, check that `.claude-governance/policy.json` has `ci.provider=codeup`.
- Maven related tests are skipped by default unless `CLAUDE_GOVERNANCE_RUN_TESTS=1` is set.

## Common commands

`init` installs templates:

```bash
claude-md-governance init --repo . --preset generic --ci github --yes
```

Input: target repo path, preset, and CI provider.
Output: `CLAUDE.md`, `.claude/settings.json`, `.claude-governance/policy.json`, `scripts/`, and CI files.
Failure handling: use `--force` to overwrite managed files with backups under `.claude-governance/backups/`.

`verify` checks the installation:

```bash
claude-md-governance verify --repo .
```

Input: an installed repository.
Output: `PASS` / `FAIL` lines and final status.
Failure handling: fix the failed item; static lint details are in `.claude-governance/score.json`.

`lint` writes a score report:

```bash
claude-md-governance lint --repo . --policy .claude-governance/policy.json --output .claude-governance/score.json
```

Input: policy and root `CLAUDE.md`.
Output: JSON findings, score, threshold, and hard-fail status.
Failure handling: fix errors first; warnings depend on team policy.

`behavior-test` runs optional LLM behavior tests:

```bash
claude-md-governance behavior-test --repo . --cases tests/ai_behavior_cases.json
```

Input: behavior case JSON and a logged-in Claude CLI.
Output: JSON results; without Claude CLI it is skipped and exits 0 by default.
Failure handling: add `--require-claude` only when CI has Claude CLI credentials.
