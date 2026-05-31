# Hooks Reference

Chinese version: [../hooks-reference.md](../hooks-reference.md)

## Registration

The installer merges `.claude/settings.json`:

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

Input: Claude Code hook JSON, usually with `tool_input.file_path`.
Output: exit `0` allows the edit; exit `2` blocks it.
Failure handling: if a protected edit is explicitly approved, set `ALLOW_PROTECTED_EDIT=1`.

Example:

```bash
echo '{"tool_input":{"file_path":".claude/settings.json"}}' | python scripts/claude_hook_guard.py pre
```

## PostToolUse

Input: hook JSON after a write.
Output: runs lint when governance files change; sensitive-path tests are warnings by default.
Failure handling: read stderr and `.claude-governance/score.json`.

Important boundary: `PostToolUse` cannot undo writes that already happened. It can only report failure, exit `2`, and stop the next flow.

Environment variables:

- `CLAUDE_GOVERNANCE_LINT_SKIP=1`: skip post lint.
- `CLAUDE_GOVERNANCE_RUN_TESTS=1`: run related policy test commands.
- `PYTHON=<python>`: override the Python interpreter used by lint.

## ConfigChange

Input: configuration-change event JSON.
Output: `block` exits `2`; `warn` and `off` exit `0`.
Failure handling: set `hooks.config_change_mode` to `block`, `warn`, or `off`.
