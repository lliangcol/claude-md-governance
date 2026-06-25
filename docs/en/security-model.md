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

Python policy scripts must be repository-relative `.py` files under `scripts/`; absolute paths or `..` paths that escape `scripts/` are rejected.
Shell control operators in any argument, such as `&&`, `||`, `;`, `|`, `<`, or `>`, are rejected so a
shell-chain fragment cannot be treated as plain arguments while still executing the first command.

Each policy command has a default 300-second timeout. Override it with `CLAUDE_GOVERNANCE_COMMAND_TIMEOUT_SECONDS`.

Auditable allowlist:

```bash
codex-md-governance policy command-allowlist
```

This command prints machine-readable JSON with `shell: false`, the strict-mode
environment variable, the timeout environment variable, allowed command forms,
and examples. In default strict mode, non-allowlisted commands return `2`; they
are downgraded to warnings only when `CLAUDE_GOVERNANCE_STRICT_COMMANDS=warn`,
`0`, `false`, or `off` is set explicitly.

Failure handling: if a policy command is skipped, change it to an allowlisted prefix or run it separately in CI.

## Protected path approval

If a protected edit is explicitly approved, scope the approval to the path:

```powershell
$env:CLAUDE_GOVERNANCE_APPROVED_PATHS = ".claude/settings.json"
```

The value matches only the approved path or glob. Do not use a global bypass.

The protected set is built from `protected_paths` plus `sensitive_paths` entries with `protected: true`. The hook guard normalizes path separators and checks every path in a single event; matching checks both the lexical path and the symlink-resolved real path. Any unapproved protected path in a MultiEdit / nested edit blocks the whole event. Approval values may be repository-relative paths, in-repository absolute paths, or globs; they are split on commas, semicolons, or newlines and use the same glob matching.

Paths outside the repository are outside this repository policy's auditable scope, so they exit `2` by default. The hook guard allows them only after explicit human approval and a matching outside-repository path or glob in `CLAUDE_GOVERNANCE_APPROVED_PATHS`. When an in-repository symlink resolves to an outside target, approval must match the resolved outside target; matching only the repository-relative symlink path does not allow the edit.

When non-empty hook input is not a valid JSON object, the guard fails closed with exit `2` so writes are not allowed when the target path cannot be inspected.
