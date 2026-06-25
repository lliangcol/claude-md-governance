# Behavior Tests

对应英文版：[docs/en/behavior-tests.md](en/behavior-tests.md)

行为测试用于观察 Claude CLI 是否按仓库规则回答。它是可选 LLM 行为测试，不是默认确定性门禁。

## 用例格式

文件：`tests/ai_behavior_cases.json` 或 `tests/ai_behavior_cases.enterprise-java-codeup.json`。

字段：

- `id`：用例标识。
- `prompt`：传给 `claude --bare -p` 的提示词。
- `deterministic_output`：可选；`--evaluator deterministic` 使用的固定输出。
- `expected_contains`：输出必须包含的文本。
- `forbidden_contains`：输出不得包含的文本。

## 运行

输入：

```bash
codex-md-governance behavior-test --repo . --cases tests/ai_behavior_cases.json
```

默认 evaluator 是 `claude-cli`，它会调用 `claude --bare -p`。如果只想验证
用例和 JSON 输出契约，不依赖 Claude CLI，可运行：

```bash
codex-md-governance behavior-test --repo . --cases tests/ai_behavior_cases.json --evaluator deterministic
```

`deterministic` evaluator 不读取 Claude CLI，也不会因为未登录而跳过。它要求每个
用例提供 `deterministic_output`，然后用同一套 `expected_contains` /
`forbidden_contains` 断言验证固定输出。

输出：稳定 JSON，顶层字段固定：

- `schema_version`：当前为 `1`。
- `status`：`pass`、`fail` 或 `skipped`。
- `evaluator`：`claude-cli` 或 `deterministic`。
- `case_file`：本次读取的用例文件路径。
- `case_count`：读取到的用例数量；Claude CLI 不存在时为 `0`。
- `summary`：`passed`、`failed`、`skipped` 计数。
- `failed`：兼容字段，`status == "fail"` 时为 `true`。
- `reason`：跳过原因；非跳过结果为 `null`。
- `results`：每个用例的 `id`、`status`、`ok`、`returncode`、断言字段和 `output_preview`。

示例：

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

失败处理：

- `Claude CLI not found`：安装并登录 Claude CLI，或不要把行为测试设为硬门禁。
- 用例失败：先判断是规则不清、测试断言过窄，还是模型行为波动。
- CI 必须失败：加 `--require-claude`。

## 边界

行为测试能发现回归趋势，但不能证明模型永远遵守规则。确定性安全边界仍应依赖 policy、hook 和 CI lint。
