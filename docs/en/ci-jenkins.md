# Jenkins

Chinese version: [../ci-jenkins.md](../ci-jenkins.md)

## Generate

```bash
codex-md-governance init --repo . --preset generic --ci jenkins --yes
```

Output:

- `Jenkinsfile`
- `docs/ci/jenkins-claude-md-governance.md`
- `ci.provider=jenkins` in `.claude-governance/policy.json`

Failure handling:

- Pipeline missing: confirm `--ci jenkins`, or use `--force` if an existing `Jenkinsfile` should be overwritten.
- Verify fails: confirm `Jenkinsfile` exists, then run `codex-md-governance verify --repo .` locally.

## Pipeline Contents

The default stage runs:

```bash
python scripts/claude_md_lint.py --policy .claude-governance/policy.json --output .claude-governance/score.json
python scripts/verify_claude_governance.py
```

`.claude-governance/score.json` is archived when present so change request reviewers can inspect lint findings.

## Behavior Tests

Jenkins does not run Claude CLI behavior tests by default. If your team configures authentication and credentials, add:

```bash
python scripts/verify_claude_governance.py --with-claude --require-claude
```
