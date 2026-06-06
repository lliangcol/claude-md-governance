# Verification

Chinese version: [../verification.md](../verification.md)

## Deterministic verification

Input:

```bash
codex-md-governance verify --repo .
```

Output:

```text
PASS: required file exists: AGENTS.md
PASS: static linter passes
PASS: PreToolUse blocks protected settings edit
PASS: mutation test catches bad root instructions
Governance verification passed.
```

Failure handling:

- Missing required file: rerun `init`.
- Static linter failure: read `.claude-governance/score.json`.
- Hook simulation failure: check `.claude/settings.json` and `scripts/claude_hook_guard.py`.
- Mutation test does not fail: lint is too weak or threshold is too low.

## Project tests

Input:

```bash
python -m pytest -q
```

Output: pytest result.
Failure handling: use the failing test to locate CLI, installer, lint, or behavior-test compatibility issues.

## Optional Claude CLI verification

Input:

```bash
codex-md-governance verify --repo . --with-claude
```

Output: shows `SKIPPED` if the `claude` command is unavailable.
Failure handling: add `--require-claude` only when Claude CLI is configured.
