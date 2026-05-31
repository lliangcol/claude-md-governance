# Hooks Reference

对应英文版：[docs/en/hooks-reference.md](en/hooks-reference.md)

## 注册位置

安装器会合并 `.claude/settings.json`：

```json
{
  "hooks": {
    "PreToolUse": [{"matcher": "Edit|Write|MultiEdit", "hooks": [{"type": "command", "command": "python scripts/claude_hook_guard.py pre"}]}],
    "PostToolUse": [{"matcher": "Edit|Write|MultiEdit", "hooks": [{"type": "command", "command": "python scripts/claude_hook_guard.py post"}]}],
    "ConfigChange": [{"matcher": "", "hooks": [{"type": "command", "command": "python scripts/claude_hook_guard.py config"}]}]
  }
}
```

## PreToolUse

输入：Claude Code hook JSON，通常包含 `tool_input.file_path`。
输出：退出码 `0` 允许；退出码 `2` 阻止。
失败处理：如果确需编辑受保护路径，先人工确认，再设置 `ALLOW_PROTECTED_EDIT=1`。

示例：

```bash
echo '{"tool_input":{"file_path":".claude/settings.json"}}' | python scripts/claude_hook_guard.py pre
```

## PostToolUse

输入：已完成写入的 hook JSON。
输出：治理文件变化时运行 lint；敏感路径相关测试默认只提示。
失败处理：查看 stderr 和 `.claude-governance/score.json`。

重要边界：`PostToolUse` 不能撤销已经发生的写入。它只能报告失败、退出 `2` 并阻止后续流程。

环境变量：

- `CLAUDE_GOVERNANCE_LINT_SKIP=1`：跳过 post lint。
- `CLAUDE_GOVERNANCE_RUN_TESTS=1`：执行 policy 中的相关测试命令。
- `PYTHON=<python>`：覆盖 lint 命令的 Python 解释器。

## ConfigChange

输入：配置变更事件 JSON。
输出：`block` 模式退出 `2`；`warn` 和 `off` 退出 `0`。
失败处理：根据 policy 修改 `hooks.config_change_mode` 为 `block`、`warn` 或 `off`。
