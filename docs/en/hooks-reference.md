# Hooks Reference

Chinese version: [../hooks-reference.md](../hooks-reference.md)

## Registration

The installer merges `.claude/settings.json` and copies the Codex-compatible `.codex/hooks.json` template:

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

Input: Claude Code hook JSON, usually with `tool_input.file_path`. It also reads `tool_input.path`, `tool_input.notebook_path`, `tool_input.filePath`, and the same path fields on every item in `tool_input.edits` / `tool_input.changes`.
Output: exit `0` allows the edit; exit `2` blocks it.
Failure handling: if a protected edit is explicitly approved, set `CLAUDE_GOVERNANCE_APPROVED_PATHS` to the approved path or glob.

Path matching semantics:

- The hook guard converts backslashes to `/` and normalizes absolute paths inside the repository to repository-relative paths.
- Protected matching checks both the lexically normalized path and the symlink-resolved real path, so symlinks inside protected directories or symlinks pointing at protected files do not bypass policy.
- `protected_paths` and `sensitive_paths` entries with `protected: true` are combined into the protected glob set.
- `CLAUDE_GOVERNANCE_APPROVED_PATHS` uses the same glob matching and accepts repository-relative paths, in-repository absolute paths, or globs separated by commas, semicolons, or newlines.
- When one event contains multiple paths, any protected path that is not approved blocks the whole event.
- Paths outside the repository exit `2` by default and are allowed only when `CLAUDE_GOVERNANCE_APPROVED_PATHS` explicitly matches the resolved outside target. Matching only an in-repository symlink path does not approve the outside target.
- Empty input is treated as a no-path event and exits `0`; non-empty malformed JSON or a non-object top-level payload exits `2`.

Example:

```bash
echo '{"tool_input":{"file_path":".claude/settings.json"}}' | python scripts/claude_hook_guard.py pre
```

PowerShell approval example:

```powershell
$env:CLAUDE_GOVERNANCE_APPROVED_PATHS = ".claude/settings.json"
'{"tool_input":{"file_path":".claude/settings.json"}}' | python scripts/claude_hook_guard.py pre
```

## PostToolUse

Input: hook JSON after a write.
Output: runs lint when governance files change; sensitive-path tests are warnings by default.
Failure handling: read stderr and `.claude-governance/score.json`.

Events with multiple paths are evaluated across all paths: lint runs once when any governance path changed, and matching sensitive-path test commands are deduplicated before they are run or reported.

Important boundary: `PostToolUse` cannot undo writes that already happened. It can only report failure, exit `2`, and stop the next flow.

Environment variables:

- `CLAUDE_GOVERNANCE_LINT_SKIP=1`: skip post lint.
- `CLAUDE_GOVERNANCE_RUN_TESTS=1`: run related policy test commands.
- `CLAUDE_GOVERNANCE_COMMAND_TIMEOUT_SECONDS=300`: adjust policy command timeout.
- `CLAUDE_GOVERNANCE_STRICT_COMMANDS=warn|0|false|off`: downgrade non-allowlisted policy commands from
  failure to warning; strict failure is the default.
- `PYTHON=<python>`: override the Python interpreter used by lint.

Use `codex-md-governance policy command-allowlist` to inspect the current allowed policy command forms.

## ConfigChange

Input: configuration-change event JSON.
Output: `block` exits `2`; `warn` and `off` exit `0`.
Failure handling: set `hooks.config_change_mode` to `block`, `warn`, or `off`.
