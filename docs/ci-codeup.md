# Codeup / 云效接入

对应英文版：[docs/en/ci-codeup.md](en/ci-codeup.md)

## 安装

输入：

```bash
claude-md-governance init --repo . --preset enterprise-java-codeup --ci codeup --config-change-mode warn --yes
```

输出：

- `ci/codeup/claude-md-governance-step.yml`
- `docs/ci/codeup-claude-md-governance.md`
- `.claude-governance/policy.json` 中 `ci.provider=codeup`

失败处理：

- 文件未生成：确认 `--ci codeup`。
- 现有文件未覆盖：加 `--force`，并查看 `.claude-governance/backups/`。

## Pipeline step

把下面命令加入云效 / Codeup pipeline：

```bash
python scripts/claude_md_lint.py \
  --policy .claude-governance/policy.json \
  --output .claude-governance/score.json
python scripts/verify_claude_governance.py
```

输入：已 checkout 的仓库。
输出：pipeline step 通过或失败。
失败处理：按日志中的 `FAIL` 和 score report 修复。

## 推荐触发路径

- `CLAUDE.md`
- `**/CLAUDE.md`
- `.claude/**`
- `.claude-governance/**`
- `scripts/claude_*`
- `tests/ai_behavior_cases*.json`

可选行为测试同样需要已登录 Claude CLI；默认不建议作为 Codeup 硬门禁。
