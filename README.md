# CLAUDE.md Governance

`claude-md-governance` 是一个 Python CLI，用 policy-as-code 管理 Claude Code 项目的 `CLAUDE.md`、hook、CI 和验证报告。它面向开源仓库和团队仓库：安装后会生成可审计的规则、保护敏感路径，并用确定性检查发现 `CLAUDE.md` 过长、规则空泛、hook 缺失或本地模块规则缺失等问题。

English docs: [docs/en/README.md](docs/en/README.md)

## 解决什么问题

只写一个很长的 `CLAUDE.md` 不够。规则会漂移，敏感目录可能没有本地说明，`@import` 可能把大段上下文塞进常驻提示，hook 配置可能被改掉，CI 也无法判断规则是否仍然可执行。

本项目把这些约束拆成：

- `CLAUDE.md`：短的根上下文和入口地图。
- `.claude-governance/policy.json`：可版本化的规则、阈值、敏感路径和 CI 配置。
- `.claude/settings.json`：Claude Code hook 注册。
- `scripts/claude_*`：仓库本地的确定性 lint、hook guard、autofix 和 verify。
- 可选行为测试：通过 Claude CLI 运行提示词回归，但不作为默认确定性门禁。

## 30 秒安装

输入：

```bash
pip install claude-md-governance
claude-md-governance init --repo . --preset generic --ci github --yes
claude-md-governance verify --repo .
```

成功输出会包含：

```text
Installed CLAUDE.md governance into <repo>
Preset: generic; CI provider: github; ConfigChange mode: block
Governance verification passed.
```

失败处理：

- `Repo not found`：确认 `--repo` 指向存在的仓库根目录。
- `Policy file not found`：先运行 `init`，或检查 `.claude-governance/policy.json` 是否被删除。
- `static linter passes` 失败：打开 `.claude-governance/score.json`，按 finding 修复 `CLAUDE.md` 或 policy。

本地开发安装：

```bash
python -m pip install -e ".[dev]"
```

## 选择 preset

- `generic`：通用仓库，默认 `ConfigChange` 为 `block`，适合 GitHub Actions。
- `java-maven`：Java/Maven 仓库，敏感目录匹配 payment/order/refund/consumer/migration，默认 `ConfigChange` 为 `warn`。
- `enterprise-java-codeup`：面向 enterprise-java-codeup 类 Java/Maven + Codeup 仓库，默认 CI provider 为 `codeup`，行为用例为 `tests/ai_behavior_cases.enterprise-java-codeup.json`。
- `auto`：根据 `pom.xml`、`package.json`、git remote 和目录名做保守推断；公开文档和 CI 中建议显式指定 preset。

enterprise-java-codeup / Codeup 示例：

```bash
claude-md-governance init --repo <repo> --preset enterprise-java-codeup --ci codeup --config-change-mode warn --yes
claude-md-governance verify --repo <repo>
```

## 安装后验证

确定性验证：

```bash
claude-md-governance verify --repo .
claude-md-governance lint --repo . --policy .claude-governance/policy.json --output .claude-governance/score.json
```

可选 Claude CLI 行为测试：

```bash
claude-md-governance behavior-test --repo . --cases tests/ai_behavior_cases.json
claude-md-governance verify --repo . --with-claude
```

如果本机或 CI 没有登录 Claude CLI，可选测试会跳过；加 `--require-claude` 后会把缺失 Claude CLI 视为失败。

## CI 接入

GitHub Actions：

```bash
claude-md-governance init --repo . --preset generic --ci github --yes
```

这会安装 `.github/workflows/claude-md-governance.yml`。工作流运行：

```bash
python scripts/claude_md_lint.py --policy .claude-governance/policy.json --output .claude-governance/score.json
python scripts/verify_claude_governance.py
```

Codeup / 云效：

```bash
claude-md-governance init --repo . --preset enterprise-java-codeup --ci codeup --config-change-mode warn --yes
```

这会安装 `ci/codeup/claude-md-governance-step.yml` 和 `docs/ci/codeup-claude-md-governance.md`，把其中脚本加入 Codeup pipeline step。

## 安全边界

- `PreToolUse` 在写入前运行，可以阻止受保护路径编辑。
- `PostToolUse` 在工具动作之后运行，可以 lint、报告失败并阻止后续流程，但不能撤销已经发生的写入。
- `ConfigChange` 可按 policy 配置为 `block`、`warn` 或 `off`。
- hook guard 只执行 allowlist 中的仓库本地命令，例如 `python scripts/...`、`mvn ...`、`npm run ...`。
- 本项目不读取密钥，不替代代码审查，也不保证 LLM 会按规则行动；它提供可审计的结构和确定性门禁。

## 贡献 preset、policy、rule

贡献前请阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 和 [GOVERNANCE.md](GOVERNANCE.md)。新增 preset 通常需要：

- `src/claude_md_governance/data/templates/policies/<preset>.json`
- `docs/presets/<preset>.md` 和 `docs/en/presets/<preset>.md`
- 覆盖 init、lint、verify 或行为用例的测试
- 示例仓库或 demo
- README / reference 文档链接

## 文档

- [快速开始](docs/getting-started.md) / [Getting Started](docs/en/getting-started.md)
- [概念](docs/concepts.md) / [Concepts](docs/en/concepts.md)
- [Generic preset](docs/presets/generic.md) / [English](docs/en/presets/generic.md)
- [Java Maven preset](docs/presets/java-maven.md) / [English](docs/en/presets/java-maven.md)
- [enterprise-java-codeup preset](docs/presets/enterprise-java-codeup.md) / [English](docs/en/presets/enterprise-java-codeup.md)
- [Policy Reference](docs/policy-reference.md) / [English](docs/en/policy-reference.md)
- [Hooks Reference](docs/hooks-reference.md) / [English](docs/en/hooks-reference.md)
- [GitHub CI](docs/ci-github.md) / [English](docs/en/ci-github.md)
- [Codeup CI](docs/ci-codeup.md) / [English](docs/en/ci-codeup.md)
- [Verification](docs/verification.md) / [English](docs/en/verification.md)
- [Behavior Tests](docs/behavior-tests.md) / [English](docs/en/behavior-tests.md)
- [Security Model](docs/security-model.md) / [English](docs/en/security-model.md)
- [Architecture](docs/architecture.md) / [English](docs/en/architecture.md)
- [Research Basis](docs/research-basis.md) / [English](docs/en/research-basis.md)
- [FAQ](docs/faq.md) / [English](docs/en/faq.md)
