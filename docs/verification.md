# Verification

对应英文版：[docs/en/verification.md](en/verification.md)

## 确定性验证

输入：

```bash
claude-md-governance verify --repo .
```

输出：

```text
PASS: required file exists: CLAUDE.md
PASS: static linter passes
PASS: PreToolUse blocks protected settings edit
PASS: mutation test catches bad CLAUDE.md
Governance verification passed.
```

失败处理：

- 必需文件缺失：重新运行 `init`。
- static linter 失败：读取 `.claude-governance/score.json`。
- hook simulation 失败：检查 `.claude/settings.json` 和 `scripts/claude_hook_guard.py`。
- mutation test 未失败：说明 lint 太弱或 policy 阈值过低。

## 本项目测试

输入：

```bash
python -m pytest -q
```

输出：pytest 结果。
失败处理：按失败测试定位 CLI、安装器、lint 或行为测试兼容性。

## 可选 Claude CLI 验证

输入：

```bash
claude-md-governance verify --repo . --with-claude
```

输出：如果没有 `claude` 命令，会显示 `SKIPPED`。
失败处理：需要强制行为测试时加 `--require-claude` 并配置 Claude CLI。
