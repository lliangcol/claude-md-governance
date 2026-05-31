# ADR-0001: Use Policy-as-Code for CLAUDE.md Governance

## Status

Accepted

## Context

CLAUDE.md quality rules must be portable, reviewable, and testable across repositories.

## Decision

Store all thresholds and governance behavior in `.claude-governance/policy.json`.

## Consequences

- Teams can customize thresholds without editing scripts.
- The linter and hook guard share the same source of truth.
- Presets can be versioned and reviewed.
