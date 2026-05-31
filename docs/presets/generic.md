# Generic preset

对应英文版：[docs/en/presets/generic.md](../en/presets/generic.md)

## 适用场景

`generic` 适合普通 Python、Node、Go、Rust 或混合仓库。它不假设 Codeup、Maven 或特定业务目录。

## 安装

输入：

```bash
claude-md-governance init --repo . --preset generic --ci github --yes
claude-md-governance verify --repo .
```

输出：

```text
Preset: generic; CI provider: github; ConfigChange mode: block
Governance verification passed.
```

失败处理：

- `.github/workflows/claude-md-governance.yml` 未出现：确认 `--ci github`。
- `ConfigChange blocks` 失败：检查 `.claude/settings.json` 是否包含 `python scripts/claude_hook_guard.py config`。

## 默认规则

- 根 `CLAUDE.md`：`warn_lines=160`，`max_lines=200`，`hard_fail_lines=220`。
- 必需章节：Project Overview、Tech Stack、Do NOT introduce、Code Rules、Context Map、Quality Gates、Working Style。
- 敏感路径：`src/auth/**`、`src/billing/**`、`src/payments/**`、`prisma/migrations/**`、`infra/**`。
- `ConfigChange`：默认 `block`。

## 贡献 generic rule

新增 rule 应优先放进 policy，再补充 lint 测试。只写自然语言说明不够，因为 CI 无法验证。
