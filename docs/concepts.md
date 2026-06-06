# 概念

对应英文版：[docs/en/concepts.md](en/concepts.md)

## 为什么仅写 AGENTS.md 不够

`AGENTS.md` 是提示上下文，不是治理系统。单文件容易出现四类问题：

- 太长：常驻上下文消耗 token，并混入不相关细节。
- 太虚：`保持简洁`、`高质量` 这类规则不可验证。
- 太散：敏感目录、CI、hook 和团队流程没有统一来源。
- 太脆：配置变更和受保护路径写入缺少写入前拦截。

## policy-as-code

`.claude-governance/policy.json` 是机器可读契约。它定义：

- 根 `AGENTS.md` 的行数和 token 阈值。
- 必需章节和别名。
- 空泛短语。
- 敏感路径、本地 `AGENTS.md`/`CLAUDE.md` 和相关测试命令。
- 受保护路径。
- hook 需求和 `ConfigChange` 模式。
- CI provider 和行为测试用例文件。

## 确定性验证 vs 可选 LLM 行为测试

确定性验证由 Python 脚本完成，不依赖模型输出：

- `claude_md_lint.py`
- `claude_hook_guard.py`
- `verify_claude_governance.py`

可选 LLM 行为测试由 `claude --bare -p` 执行：

- 依赖本机或 CI 的 Claude CLI。
- 依赖登录状态和模型行为。
- 默认不作为硬门禁；使用 `--require-claude` 才把缺失 CLI 视为失败。

## hook 生命周期

- `PreToolUse`：写入前执行，可阻止受保护路径写入。
- `PostToolUse`：写入后执行，可运行 lint 或测试并阻止后续流程，但不能撤销已经发生的写入。
- `ConfigChange`：Claude Code 配置变化时执行，可按 policy `block`、`warn` 或 `off`。
