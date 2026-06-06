# Security Model

Chinese version: [../security-model.md](../security-model.md)

## Goals

- Prevent silent edits to protected governance files.
- Ensure sensitive business directories have local `AGENTS.md`/`CLAUDE.md` files.
- Detect long root instructions, vague rules, and missing hooks in CI.
- Block or warn on Claude Code configuration changes.

## Non-goals

- It does not replace code review.
- It does not read or manage secrets.
- It does not guarantee LLM compliance.
- It does not roll back filesystem writes.

## Hook boundary

`PreToolUse` runs before writes and can block `Edit`, `Write`, and `MultiEdit` operations on protected paths.

`PostToolUse` runs after writes. It can run lint or tests and fail, but it cannot undo writes that already happened. Rollback requires an explicit user or tool action.

`ConfigChange` handles configuration-change events only. `block` is stricter; `warn` is better for enterprise CI or Codeup setups that need compatibility with existing settings.

## Command allowlist

The hook guard parses command arguments and executes them without a shell. Policy commands must match these allowlisted forms:

- `python scripts/*.py`
- `python3 scripts/*.py`
- `py scripts/*.py`
- `mvn ...`
- `./mvnw ...`
- `mvnw ...`
- `npm test`
- `npm run ...`
- `pnpm test`
- `pnpm run ...`
- `yarn test`
- `yarn run ...`

Each policy command has a default 300-second timeout. Override it with `CLAUDE_GOVERNANCE_COMMAND_TIMEOUT_SECONDS`.

Failure handling: if a policy command is skipped, change it to an allowlisted prefix or run it separately in CI.

## Protected path approval

If a protected edit is explicitly approved, scope the approval to the path:

```powershell
$env:CLAUDE_GOVERNANCE_APPROVED_PATHS = ".claude/settings.json"
```

The value matches only the approved path or glob. Do not use a global bypass.
