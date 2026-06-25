# GitLab CI

Chinese version: [../ci-gitlab.md](../ci-gitlab.md)

## Generate

```bash
codex-md-governance init --repo . --preset generic --ci gitlab --yes
```

Output:

- `.gitlab-ci.yml`
- `docs/ci/gitlab-claude-md-governance.md`
- `ci.provider=gitlab` in `.claude-governance/policy.json`

Failure handling:

- Pipeline missing: confirm `--ci gitlab`, or use `--force` if an existing `.gitlab-ci.yml` should be overwritten.
- Verify fails: confirm `.gitlab-ci.yml` exists, then run `codex-md-governance verify --repo .` locally.

## Pipeline Contents

The default job uses `python:3.11-slim` and runs:

```bash
python scripts/claude_md_lint.py --policy .claude-governance/policy.json --output .claude-governance/score.json
python scripts/verify_claude_governance.py
```

`.claude-governance/score.json` is uploaded as a short-lived artifact for MR review.

## Behavior Tests

GitLab CI does not run Claude CLI behavior tests by default. If your team configures authentication and credentials, add:

```bash
python scripts/verify_claude_governance.py --with-claude --require-claude
```
