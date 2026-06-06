# Project Overview

This repository publishes the `Codex-md-governance` Python CLI for installing, linting, repairing, and verifying Codex `AGENTS.md` governance in downstream repositories. The legacy `claude-md-governance` command remains as a compatibility alias.
Optimization priority: correctness > security > maintainability > speed.

# Tech Stack

- Python / pyproject.toml

# Do NOT introduce

- Do not introduce new frameworks, state managers, UI libraries, databases, or test runners without explicit approval.
- Do not add runtime dependencies for convenience when the standard library is sufficient.

# Code Rules

- Use explicit types at public boundaries.
- Keep functions focused; split large functions when one function mixes validation, I/O, and transformation.
- Do not leave commented-out code, debug logs, or unowned TODOs.
- Prefer existing repository patterns over introducing new abstractions.

# Context Map

- Architecture overview: docs/architecture.md
- Policy reference: docs/policy-reference.md
- Verification guide: docs/verification.md
- AI long-form context: docs/ai-context/
- Archive/deprecated docs: docs/archive/ — do not read unless explicitly requested.

# Quality Gates

- Lint AGENTS.md when it changes.
- Block protected path edits unless explicitly approved.
- Run related tests for sensitive modules when CLAUDE_GOVERNANCE_RUN_TESTS=1.
- Keep root AGENTS.md under the configured line and token budget.

# Working Style

- For complex changes, propose a short plan before editing.
- For trivial fixes, edit directly and summarize the diff.
- If uncertain, state assumptions and choose the conservative path.

# Sensitive Areas

- Read local AGENTS.md files before editing sensitive modules.
- Ask for explicit approval before modifying public APIs, auth, billing/payment, database schema, migrations, or infrastructure.
