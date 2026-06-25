# GitLab CI 接入

对应英文版：[docs/en/ci-gitlab.md](en/ci-gitlab.md)

## 生成

```bash
codex-md-governance init --repo . --preset generic --ci gitlab --yes
```

输出：

- `.gitlab-ci.yml`
- `docs/ci/gitlab-claude-md-governance.md`
- `.claude-governance/policy.json` 中 `ci.provider=gitlab`

失败处理：

- pipeline 未生成：确认 `--ci gitlab`，或检查已有 `.gitlab-ci.yml` 是否需要 `--force` 覆盖。
- verify 失败：确认 `.gitlab-ci.yml` 存在，并先在本地运行 `codex-md-governance verify --repo .`。

## Pipeline 内容

默认 job 使用 `python:3.11-slim`，运行：

```bash
python scripts/claude_md_lint.py --policy .claude-governance/policy.json --output .claude-governance/score.json
python scripts/verify_claude_governance.py
```

`.claude-governance/score.json` 会作为短期 artifact 保存，便于 MR review。

## 行为测试

GitLab CI 默认不运行 Claude CLI 行为测试。若团队自行配置登录态和凭据，可显式增加：

```bash
python scripts/verify_claude_governance.py --with-claude --require-claude
```
