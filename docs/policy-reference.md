# Policy Reference

对应英文版：[docs/en/policy-reference.md](en/policy-reference.md)

policy 文件路径：`.claude-governance/policy.json`。

## 顶层字段

- `version`：policy schema 版本，当前模板为 `2`。
- `preset`：`generic`、`java-maven` 或 `enterprise-java-codeup`。
- `score_threshold`：lint 通过分数线，默认 `75`。
- `root_claude`：根 `CLAUDE.md` 路径、行数和 token 阈值。
- `required_sections`：必需章节、别名、严重级别和扣分。
- `vague_phrases`：英文和中文空泛短语列表。
- `banned_dependencies`：必须在 `CLAUDE.md` 中说明的禁用依赖。
- `sensitive_paths`：敏感路径、本地 `CLAUDE.md`、测试命令和保护标记。
- `protected_paths`：`PreToolUse` 默认保护的路径。
- `hooks`：hook 需求和 `config_change_mode`。
- `ci`：`provider` 为 `auto`、`github`、`codeup` 或 `none`。
- `behavior_tests`：可选行为测试配置。

## 命令

输入：

```bash
claude-md-governance lint --repo . --policy .claude-governance/policy.json --output .claude-governance/score.json
```

输出：JSON report，包含 `status`、`score`、`threshold`、`hard_fail`、`findings` 和 `summary`。

失败处理：

- `ROOT_MISSING`：创建根 `CLAUDE.md`。
- `MISSING_SECTION`：添加必需章节或可接受别名。
- `MISSING_LOCAL_CLAUDE`：为敏感目录创建本地 `CLAUDE.md`。
- `PRE_HOOK_MISSING` / `POST_HOOK_MISSING`：修复 `.claude/settings.json`。

## 贡献 policy

新增字段应保持向后兼容；新增强制规则必须配套测试，并在本页和英文版同步说明。
