# Concepts

Chinese version: [../concepts.md](../concepts.md)

## Why AGENTS.md alone is not enough

`AGENTS.md` is prompt context, not a governance system. A single file tends to become too long, too vague, disconnected from hooks and CI, and fragile when protected files or settings change.

## Policy as code

`.claude-governance/policy.json` defines root `AGENTS.md` budgets, required sections, vague phrases, sensitive paths, protected paths, hooks, CI provider, and behavior test case files.

## Deterministic checks vs optional LLM behavior tests

Deterministic checks use local Python scripts and do not depend on model output:

- `claude_md_lint.py`
- `claude_hook_guard.py`
- `verify_claude_governance.py`

Optional behavior tests use `claude --bare -p`. They depend on Claude CLI installation, credentials, and model behavior. They are not default hard gates unless `--require-claude` is used.

## Hook lifecycle

- `PreToolUse`: runs before writes and can block protected path edits.
- `PostToolUse`: runs after writes; it can lint and fail the next flow, but it cannot undo writes that already happened.
- `ConfigChange`: runs on Claude Code configuration changes and can be `block`, `warn`, or `off`.
