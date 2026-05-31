# Behavior Tests

对应英文版：[docs/en/behavior-tests.md](en/behavior-tests.md)

行为测试用于观察 Claude CLI 是否按仓库规则回答。它是可选 LLM 行为测试，不是默认确定性门禁。

## 用例格式

文件：`tests/ai_behavior_cases.json` 或 `tests/ai_behavior_cases.enterprise-java-codeup.json`。

字段：

- `id`：用例标识。
- `prompt`：传给 `claude --bare -p` 的提示词。
- `expected_contains`：输出必须包含的文本。
- `forbidden_contains`：输出不得包含的文本。

## 运行

输入：

```bash
claude-md-governance behavior-test --repo . --cases tests/ai_behavior_cases.json
```

输出：JSON，包含 `status`、`failed` 和每个用例结果。

失败处理：

- `Claude CLI not found`：安装并登录 Claude CLI，或不要把行为测试设为硬门禁。
- 用例失败：先判断是规则不清、测试断言过窄，还是模型行为波动。
- CI 必须失败：加 `--require-claude`。

## 边界

行为测试能发现回归趋势，但不能证明模型永远遵守规则。确定性安全边界仍应依赖 policy、hook 和 CI lint。
