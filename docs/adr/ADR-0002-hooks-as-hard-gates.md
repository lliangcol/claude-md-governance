# ADR-0002: Use Hooks for Pre-Write Gates and Post-Write Feedback

## Status

Accepted

## Context

CLAUDE.md instructions are context, not enforcement. Some actions must be blocked deterministically.

## Decision

Use Claude Code `PreToolUse` hooks for protected path blocking and `PostToolUse` hooks for governance lint feedback.

## Consequences

- `PreToolUse` can stop risky edits before they happen.
- `PostToolUse` runs after the tool action. It can report a failed governance state and stop the next flow, but it cannot undo writes that already happened.
- Hook scripts become security-sensitive and must be protected.
