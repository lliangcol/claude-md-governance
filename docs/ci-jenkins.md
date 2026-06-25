# Jenkins 接入

对应英文版：[docs/en/ci-jenkins.md](en/ci-jenkins.md)

## 生成

```bash
codex-md-governance init --repo . --preset generic --ci jenkins --yes
```

输出：

- `Jenkinsfile`
- `docs/ci/jenkins-claude-md-governance.md`
- `.claude-governance/policy.json` 中 `ci.provider=jenkins`

失败处理：

- pipeline 未生成：确认 `--ci jenkins`，或检查已有 `Jenkinsfile` 是否需要 `--force` 覆盖。
- verify 失败：确认 `Jenkinsfile` 存在，并先在本地运行 `codex-md-governance verify --repo .`。

## Pipeline 内容

默认 stage 仅在 change request 触及治理相关文件时运行：

```bash
python scripts/claude_md_lint.py --policy .claude-governance/policy.json --output .claude-governance/score.json
python scripts/verify_claude_governance.py
```

`.claude-governance/score.json` 会在存在时归档，便于 change request review。

## 行为测试

Jenkins 默认不运行 Claude CLI 行为测试。若团队自行配置登录态和凭据，可显式增加：

```bash
python scripts/verify_claude_governance.py --with-claude --require-claude
```
