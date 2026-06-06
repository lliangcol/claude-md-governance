# Research Basis

Chinese version: [../research-basis.md](../research-basis.md)

The project is based on engineering governance principles. It does not claim that any LLM can be perfectly constrained.

## Base assumptions

- Short root context is easier to maintain and audit than long root context.
- Machine-readable policy is better for CI than natural language alone.
- Pre-write hooks can reduce accidental edits to protected paths.
- Post-write hooks can detect problems, but they cannot undo writes that already happened.
- LLM behavior tests provide regression signals, but they depend on model, credentials, environment, and prompts.

## Verifiable assumptions

Input:

```bash
codex-md-governance verify --repo .
python -m pytest -q
```

Output: deterministic pass/fail.
Failure handling: fix code or policy first; do not attribute deterministic failures to model behavior.

## Contributing research material

New material should become an executable rule, policy field, test, or documented limit. Avoid unverifiable promotional claims.
