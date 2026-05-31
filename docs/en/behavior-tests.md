# Behavior Tests

Chinese version: [../behavior-tests.md](../behavior-tests.md)

Behavior tests observe whether Claude CLI answers according to repository rules. They are optional LLM behavior tests, not default deterministic gates.

## Case format

Files: `tests/ai_behavior_cases.json` or `tests/ai_behavior_cases.onm-agent.json`.

Fields:

- `id`: case identifier.
- `prompt`: prompt passed to `claude --bare -p`.
- `expected_contains`: text that must appear.
- `forbidden_contains`: text that must not appear.

## Run

Input:

```bash
claude-md-governance behavior-test --repo . --cases tests/ai_behavior_cases.json
```

Output: JSON with `status`, `failed`, and per-case results.

Failure handling:

- `Claude CLI not found`: install and log in to Claude CLI, or do not make behavior tests a hard gate.
- Case failure: decide whether the rule is unclear, the assertion is too narrow, or model behavior changed.
- CI must fail: add `--require-claude`.

## Boundary

Behavior tests provide regression signals, but they cannot prove the model will always follow the rules. Deterministic safety should come from policy, hooks, and CI lint.
