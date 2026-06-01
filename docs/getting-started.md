# 快速开始

对应英文版：[docs/en/getting-started.md](en/getting-started.md)

## Generic 快速开始

PyPI 包发布前，不要使用 `pip install claude-md-governance`。当前公开安装路径是
GitHub Release wheel 或源码 checkout。

源码 checkout：

```bash
python -m pip install -e ".[test]"
claude-md-governance init --repo . --preset generic --ci github --yes
claude-md-governance verify --repo .
```

`v0.1.0` GitHub Release 发布后，wheel 安装路径是：

```bash
python -m pip install "https://github.com/lliangcol/claude-md-governance/releases/download/v0.1.0/claude_md_governance-0.1.0-py3-none-any.whl"
claude-md-governance init --repo . --preset generic --ci github --yes
claude-md-governance verify --repo .
```

输出：

```text
Installed CLAUDE.md governance into <repo>
Preset: generic; CI provider: github; ConfigChange mode: block
Governance verification passed.
```

失败处理：

- `Repo not found`：确认 `--repo` 是仓库根目录。
- `Use --yes for non-interactive installation.`：补上 `--yes`。
- `Governance verification failed`：读取失败项和 `.claude-governance/score.json`。

## enterprise-java-codeup / Codeup 示例

输入：

```bash
claude-md-governance init --repo <repo> --preset enterprise-java-codeup --ci codeup --config-change-mode warn --yes
claude-md-governance verify --repo <repo>
```

输出：

```text
Preset: enterprise-java-codeup; CI provider: codeup; ConfigChange mode: warn
Governance verification passed.
```

失败处理：

- 如果 Codeup 文档未生成，检查 `.claude-governance/policy.json` 中 `ci.provider` 是否为 `codeup`。
- 如果 Maven 敏感目录测试被提示跳过，这是默认行为；只有设置 `CLAUDE_GOVERNANCE_RUN_TESTS=1` 才执行相关测试命令。

## 常用命令

`init` 安装模板：

```bash
claude-md-governance init --repo . --preset generic --ci github --yes
```

输入：目标仓库路径、preset、CI provider。
输出：生成或合并 `CLAUDE.md`、`.claude/settings.json`、`.claude-governance/policy.json`、`scripts/` 和 CI 文件。
失败处理：加 `--force` 可覆盖受管文件并备份；不确定时先检查 `.claude-governance/backups/`。

`verify` 验证安装：

```bash
claude-md-governance verify --repo .
```

输入：已安装治理文件的仓库。
输出：每个检查项的 `PASS` / `FAIL` 和最终状态。
失败处理：按失败项修复；静态 lint 的详细报告在 `.claude-governance/score.json`。

`lint` 生成评分报告：

```bash
claude-md-governance lint --repo . --policy .claude-governance/policy.json --output .claude-governance/score.json
```

输入：policy 和根 `CLAUDE.md`。
输出：JSON finding、score、threshold、hard_fail。
失败处理：修复 error；warning 可按团队阈值处理。

`behavior-test` 运行可选 LLM 行为测试：

```bash
claude-md-governance behavior-test --repo . --cases tests/ai_behavior_cases.json
```

输入：行为用例 JSON 和已登录的 Claude CLI。
输出：JSON 结果；无 Claude CLI 时默认 `skipped` 且退出 0。
失败处理：需要 CI 强制执行时加 `--require-claude`，并配置 Claude CLI 凭据。
