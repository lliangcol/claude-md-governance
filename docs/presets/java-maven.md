# Java Maven preset

对应英文版：[docs/en/presets/java-maven.md](../en/presets/java-maven.md)

## 适用场景

`java-maven` 适合 Maven 多模块或单模块 Java 仓库。它提供 Java/Maven 阈值和敏感目录匹配，但不默认绑定 GitHub 或 Codeup。

## 安装

输入：

```bash
codex-md-governance init --repo . --preset java-maven --ci github --config-change-mode warn --yes
codex-md-governance verify --repo .
```

输出：

```text
Preset: java-maven; CI provider: github; ConfigChange mode: warn
Governance verification passed.
```

失败处理：

- 敏感目录缺少本地 `AGENTS.md`：为 finding 中的路径创建本地规则，或调整 policy 的 `sensitive_paths`。
- Maven 命令失败：检查 `{module}` 替换后的模块名是否符合仓库实际 Maven module。

## 默认规则

- 根 `AGENTS.md`：`warn_lines=180`，`max_lines=230`，`hard_fail_lines=280`。
- 必需章节：Priority and Scope、Architecture Boundaries、Core Engineering Rules、Change Control、Do NOT introduce。
- 敏感路径：payment、order、refund、consumer/MQ、migration。
- 相关测试：默认模板为 `mvn -pl {module} -am test`。
- `ConfigChange`：默认 `warn`。

## 注意事项

`PostToolUse` 只在 `CLAUDE_GOVERNANCE_RUN_TESTS=1` 时执行相关测试。否则会输出 warning，避免本地编辑时意外运行长测试。
