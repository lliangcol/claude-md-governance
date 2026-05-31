# GitHub Actions

Chinese version: [../ci-github.md](../ci-github.md)

## Install

Input:

```bash
claude-md-governance init --repo . --preset generic --ci github --yes
```

Output: `.github/workflows/claude-md-governance.yml`.

Failure handling:

- Workflow missing: confirm `--ci github`.
- Need to overwrite a managed workflow: rerun with `--force`; backups go under `.claude-governance/backups/`.

## Workflow

The current template runs:

```bash
python scripts/claude_md_lint.py \
  --policy .claude-governance/policy.json \
  --output .claude-governance/score.json
python scripts/verify_claude_governance.py
```

Output: GitHub check pass/fail. Lint failures are visible in logs and `.claude-governance/score.json`.

## Optional behavior tests

GitHub CI does not run Claude CLI behavior tests by default. If credentials are configured, add:

```bash
python scripts/verify_claude_governance.py --with-claude --require-claude
```

Failure handling: ensure the runner has the `claude` command and is logged in; otherwise do not use `--require-claude`.
