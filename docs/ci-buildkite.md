# Buildkite 接入

对应英文版：[docs/en/ci-buildkite.md](en/ci-buildkite.md)

## 生成

```bash
codex-md-governance init --repo . --preset generic --ci buildkite --yes
```

输出：

- `.buildkite/pipeline.yml`
- `docs/ci/buildkite-claude-md-governance.md`
- `.claude-governance/policy.json` 中 `ci.provider=buildkite`

失败处理：

- pipeline 未生成：确认 `--ci buildkite`，或检查已有 `.buildkite/pipeline.yml` 是否需要 `--force` 覆盖。
- verify 失败：确认 `.buildkite/pipeline.yml` 存在，并先在本地运行 `codex-md-governance verify --repo .`。

## Pipeline 内容

默认 step 运行：

```bash
python scripts/claude_md_lint.py --policy .claude-governance/policy.json --output .claude-governance/score.json
python scripts/verify_claude_governance.py
```

`.claude-governance/score.json` 会作为 artifact 上传，便于 review。

## 行为测试

Buildkite 默认不运行 Claude CLI 行为测试。若团队自行配置登录态和凭据，可显式增加：

```bash
python scripts/verify_claude_governance.py --with-claude --require-claude
```
