# Hooks Reference

对应英文版：[docs/en/hooks-reference.md](en/hooks-reference.md)

## 注册位置

安装器会合并 `.claude/settings.json`，并复制 Codex 兼容的 `.codex/hooks.json` 模板：

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

输入：Claude Code hook JSON，通常包含 `tool_input.file_path`。也会读取 `tool_input.path`、`tool_input.notebook_path`、`tool_input.filePath`，以及 `tool_input.edits` / `tool_input.changes` 中每个条目的这些路径字段。
输出：退出码 `0` 允许；退出码 `2` 阻止。
失败处理：如果确需编辑受保护路径，先人工确认，再设置 `CLAUDE_GOVERNANCE_APPROVED_PATHS` 为被批准的路径或 glob。

路径匹配语义：

- hook guard 会把反斜杠转为 `/`，并把仓库内绝对路径规范化为仓库相对路径。
- 受保护匹配会同时检查词法规范化路径和 symlink 解析后的真实路径，避免 protected 目录内的 symlink 或指向 protected 文件的 symlink 绕过策略。
- `protected_paths` 与 `sensitive_paths` 中 `protected: true` 的路径共同组成受保护 glob。
- `CLAUDE_GOVERNANCE_APPROVED_PATHS` 使用同一套 glob 匹配，可写仓库相对路径、仓库内绝对路径或 glob；可用逗号、分号或换行分隔多项。
- 一个事件包含多个路径时，只要任一路径受保护且未被授权，整个事件都会被阻止。
- 仓库外路径默认退出 `2`；只有在 `CLAUDE_GOVERNANCE_APPROVED_PATHS` 显式匹配解析后的仓库外目标时才允许。仓库内 symlink 路径本身的匹配不会授权仓库外目标。
- 空输入被视为无路径事件并退出 `0`；非空但格式错误或顶层不是对象的 JSON 会退出 `2`。

示例：

```bash
echo '{"tool_input":{"file_path":".claude/settings.json"}}' | python scripts/claude_hook_guard.py pre
```

PowerShell 授权示例：

```powershell
$env:CLAUDE_GOVERNANCE_APPROVED_PATHS = ".claude/settings.json"
'{"tool_input":{"file_path":".claude/settings.json"}}' | python scripts/claude_hook_guard.py pre
```

## PostToolUse

输入：已完成写入的 hook JSON。
输出：治理文件变化时运行 lint；敏感路径相关测试默认只提示。
失败处理：查看 stderr 和 `.claude-governance/score.json`。

包含多个路径的事件会按所有路径判断：任一治理路径变化只运行一次 lint；所有匹配敏感路径的测试命令会去重后汇总执行或提示。

重要边界：`PostToolUse` 不能撤销已经发生的写入。它只能报告失败、退出 `2` 并阻止后续流程。

环境变量：

- `CLAUDE_GOVERNANCE_LINT_SKIP=1`：跳过 post lint。
- `CLAUDE_GOVERNANCE_RUN_TESTS=1`：执行 policy 中的相关测试命令。
- `CLAUDE_GOVERNANCE_COMMAND_TIMEOUT_SECONDS=300`：调整 policy 命令超时。
- `CLAUDE_GOVERNANCE_STRICT_COMMANDS=warn|0|false|off`：将非 allowlist policy 命令从失败降级为警告；默认严格失败。
- `PYTHON=<python>`：覆盖 lint 命令的 Python 解释器。

用 `codex-md-governance policy command-allowlist` 查看当前允许的 policy 命令形态。

## ConfigChange

输入：配置变更事件 JSON。
输出：`block` 模式退出 `2`；`warn` 和 `off` 退出 `0`。
失败处理：根据 policy 修改 `hooks.config_change_mode` 为 `block`、`warn` 或 `off`。
