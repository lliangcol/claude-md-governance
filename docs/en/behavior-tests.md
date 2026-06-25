# Behavior Tests

Chinese version: [../behavior-tests.md](../behavior-tests.md)

Behavior tests observe whether Claude CLI answers according to repository rules. They are optional LLM behavior tests, not default deterministic gates.

## Case format

Files: `tests/ai_behavior_cases.json` or `tests/ai_behavior_cases.enterprise-java-codeup.json`.

Fields:

- `id`: case identifier.
- `prompt`: prompt passed to `claude --bare -p`.
- `deterministic_output`: optional fixed output used by `--evaluator deterministic`.
- `expected_contains`: text that must appear.
- `forbidden_contains`: text that must not appear.

## Run

Input:

```bash
codex-md-governance behavior-test --repo . --cases tests/ai_behavior_cases.json
```

The default evaluator is `claude-cli`, which calls `claude --bare -p`. To
validate case assertions and the JSON contract without Claude CLI, run:

```bash
codex-md-governance behavior-test --repo . --cases tests/ai_behavior_cases.json --evaluator deterministic
```

The `deterministic` evaluator does not read Claude CLI and never skips because
Claude is missing or logged out. Each case must provide `deterministic_output`;
the same `expected_contains` / `forbidden_contains` assertions are applied to
that fixed output.

Output: stable JSON with fixed top-level fields:

- `schema_version`: currently `1`.
- `status`: `pass`, `fail`, or `skipped`.
- `evaluator`: `claude-cli` or `deterministic`.
- `case_file`: behavior case file path used for the run.
- `case_count`: number of loaded cases; `0` when Claude CLI is not found.
- `summary`: `passed`, `failed`, and `skipped` counts.
- `failed`: compatibility field, `true` when `status == "fail"`.
- `reason`: skip reason; `null` for non-skipped results.
- `results`: per-case `id`, `status`, `ok`, `returncode`, assertion fields, and `output_preview`.

Example:

```json
{
  "schema_version": 1,
  "status": "skipped",
  "evaluator": "claude-cli",
  "case_file": "tests/ai_behavior_cases.json",
  "case_count": 0,
  "summary": {"passed": 0, "failed": 0, "skipped": 0},
  "failed": false,
  "reason": "Claude CLI not found",
  "results": []
}
```

Failure handling:

- `Claude CLI not found`: install and log in to Claude CLI, or do not make behavior tests a hard gate.
- Case failure: decide whether the rule is unclear, the assertion is too narrow, or model behavior changed.
- CI must fail: add `--require-claude`.

## Boundary

Behavior tests provide regression signals, but they cannot prove the model will always follow the rules. Deterministic safety should come from policy, hooks, and CI lint.
