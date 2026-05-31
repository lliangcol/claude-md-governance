# FAQ

对应英文版：[docs/en/faq.md](en/faq.md)

## 这个项目会替我写 CLAUDE.md 吗？

`init` 会生成骨架并补齐缺失章节，但内容仍需要仓库维护者填入真实架构、禁用依赖和敏感边界。

## 为什么 README 说 PostToolUse 不能撤销写入？

因为 `PostToolUse` 发生在工具动作之后。它能失败退出并阻止后续流程，但已经写入的文件不会自动恢复。

## 可以不接 CI 吗？

可以。使用：

```bash
claude-md-governance init --repo . --preset generic --ci none --yes
```

输出：不生成 GitHub 或 Codeup CI 文件。
失败处理：仍建议本地运行 `claude-md-governance verify --repo .`。

## 如何只生成 Codeup 示例？

```bash
claude-md-governance init --repo . --preset onm-agent --ci codeup --config-change-mode warn --yes
```

失败处理：如果已有文件未覆盖，加 `--force`。

## 行为测试为什么跳过？

默认缺少 Claude CLI 时跳过。需要强制执行：

```bash
claude-md-governance behavior-test --repo . --require-claude
```

失败处理：安装并登录 Claude CLI，或移除 `--require-claude`。

## 如何贡献 preset？

新增 policy JSON、中文文档、英文文档、测试和示例。至少运行：

```bash
python -m pytest -q
claude-md-governance verify --repo .
```
