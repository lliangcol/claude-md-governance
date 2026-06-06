# GitHub Actions 接入

对应英文版：[docs/en/ci-github.md](en/ci-github.md)

## 安装

输入：

```bash
codex-md-governance init --repo . --preset generic --ci github --yes
```

输出：`.github/workflows/claude-md-governance.yml`。

失败处理：

- workflow 未生成：确认 `--ci github`，或检查安装器是否因目标文件已存在而未覆盖。
- 需要覆盖受管 workflow：重新运行并加 `--force`，安装器会在 `.claude-governance/backups/` 备份。

## 工作流内容

当前模板在 Ubuntu 和 Windows 上运行：

```bash
python scripts/claude_md_lint.py \
  --policy .claude-governance/policy.json \
  --output .claude-governance/score.json
python scripts/verify_claude_governance.py
```

输出：GitHub check 通过或失败；lint 失败时可从日志和 `.claude-governance/score.json` 读取 finding。

## 可选行为测试

GitHub CI 默认不运行 Claude CLI 行为测试。若团队自行配置凭据，可增加：

```bash
python scripts/verify_claude_governance.py --with-claude --require-claude
```

失败处理：确认 runner 中存在 `claude` 命令并已登录；否则不要加 `--require-claude`。
