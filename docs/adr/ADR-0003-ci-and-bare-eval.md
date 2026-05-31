# ADR-0003: Separate CI Governance and Bare LLM Evaluation

## Status

Accepted

## Context

Static checks must be deterministic. Optional LLM evaluation should not be affected by the repository's own CLAUDE.md.

## Decision

Run deterministic lint/verifier in CI. Run optional Claude-based evaluation with `claude --bare -p`.

## Consequences

- CI can run without Claude credentials.
- LLM evaluation is isolated from target repository instructions.
- Behavior tests remain optional because they require a configured Claude CLI.
