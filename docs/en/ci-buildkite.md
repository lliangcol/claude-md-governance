# Buildkite

Chinese version: [../ci-buildkite.md](../ci-buildkite.md)

## Generate

```bash
codex-md-governance init --repo . --preset generic --ci buildkite --yes
```

Output:

- `.buildkite/pipeline.yml`
- `docs/ci/buildkite-claude-md-governance.md`
- `ci.provider=buildkite` in `.claude-governance/policy.json`

Failure handling:

- Pipeline missing: confirm `--ci buildkite`, or use `--force` if an existing `.buildkite/pipeline.yml` should be overwritten.
- Verify fails: confirm `.buildkite/pipeline.yml` exists, then run `codex-md-governance verify --repo .` locally.

## Pipeline Contents

The default step runs:

```bash
python scripts/claude_md_lint.py --policy .claude-governance/policy.json --output .claude-governance/score.json
python scripts/verify_claude_governance.py
```

`.claude-governance/score.json` is uploaded as an artifact for review.

## Behavior Tests

Buildkite does not run Claude CLI behavior tests by default. If your team configures authentication and credentials, add:

```bash
python scripts/verify_claude_governance.py --with-claude --require-claude
```
