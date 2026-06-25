# Policy Reference

对应英文版：[docs/en/policy-reference.md](en/policy-reference.md)

policy 文件路径：`.claude-governance/policy.json`。

## 顶层字段

- `version`：policy schema 版本，当前模板为 `2`。
- `preset`：`generic`、`java-maven` 或 `enterprise-java-codeup`。
- `score_threshold`：lint 通过分数线，默认 `75`。
- `root_doc`：根 `AGENTS.md` 路径、行数和 token 阈值；新模板默认使用该字段。
- `root_claude`：兼容旧策略的根 `CLAUDE.md` 路径、行数和 token 阈值。
- `required_sections`：必需章节、别名、严重级别和扣分。
- `vague_phrases`：英文和中文空泛短语列表。
- `banned_dependencies`：必须在 root 指令中说明、且不得出现在 dependency file 中的禁用依赖。
- `sensitive_paths`：敏感路径、本地 `AGENTS.md`/`CLAUDE.md`、测试命令和保护标记。
- `protected_paths`：`PreToolUse` 默认保护的路径。
- `hooks`：hook 需求和 `config_change_mode`。
- `ci`：`provider` 为 `auto`、`github`、`gitlab`、`jenkins`、`buildkite`、`codeup` 或 `none`。
- `behavior_tests`：可选行为测试配置。

## 命令

输入：

```bash
codex-md-governance lint --repo . --policy .claude-governance/policy.json --output .claude-governance/score.json
```

输出：JSON report，包含 `status`、`score`、`threshold`、`hard_fail`、`findings` 和 `summary`。

校验 policy schema：

```bash
codex-md-governance policy validate --repo . --policy .claude-governance/policy.json
```

保守迁移旧 policy 形态：

```bash
codex-md-governance policy migrate --repo . --policy .claude-governance/policy.json --write
```

查看 hook policy 命令 allowlist：

```bash
codex-md-governance policy command-allowlist
```

`migrate` 只补齐可机械推导的字段，例如 `root_doc`、`hooks.config_change_mode` 和 `ci.provider`；无法推导的字段仍应由维护者显式编辑。`init` 合并既有 policy 时也会先按同样的 root-doc 兼容语义保留 `root_agents` / `root_claude`，避免旧 `CLAUDE.md` 仓库被静默切换到新模板默认的 `AGENTS.md`。

失败处理：

- `ROOT_MISSING`：创建根 `AGENTS.md` 或 policy 指定的 root instruction file。
- `MISSING_SECTION`：添加必需章节或可接受别名。
- `MISSING_LOCAL_DOC`：为敏感目录创建本地 `AGENTS.md`/`CLAUDE.md`。
- `ROOT_LOCAL_DOC_CONFLICT`：将本地规则路径改为敏感目录下的 `AGENTS.md`/`CLAUDE.md`；不能让 local instruction file 解析到 root instruction file。
- `BANNED_DEP_PRESENT`：从 dependency file 移除 policy 禁用依赖，或显式调整 policy。
- `PRE_HOOK_MISSING` / `POST_HOOK_MISSING`：修复 `.claude/settings.json`。

## 贡献 policy

新增字段应保持向后兼容；新增强制规则必须配套测试，并在本页和英文版同步说明。
