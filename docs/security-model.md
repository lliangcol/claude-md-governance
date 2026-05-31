# Security Model

对应英文版：[docs/en/security-model.md](en/security-model.md)

## 保护目标

- 防止受保护治理文件被无提示修改。
- 让敏感业务目录拥有本地 `CLAUDE.md`。
- 在 CI 中发现根 `CLAUDE.md` 过长、规则空泛、hook 缺失。
- 对 Claude Code 配置变化给出 block 或 warn。

## 非目标

- 不替代代码审查。
- 不读取或管理密钥。
- 不保证 LLM 一定遵守规则。
- 不回滚文件系统写入。

## hook 边界

`PreToolUse` 在写入前执行，可以阻止 `Edit`、`Write`、`MultiEdit` 对受保护路径的修改。

`PostToolUse` 在写入后执行。它可以运行 lint 或测试并退出失败，但不能撤销已经发生的写入。需要回滚时必须由用户或后续工具显式修改文件。

`ConfigChange` 只处理配置变化事件。`block` 更严格，`warn` 更适合企业 CI / Codeup 等需要兼容已有配置的场景。

## 命令 allowlist

hook guard 会解析命令参数，并且不用 shell 执行。policy 命令必须匹配以下 allowlist 形态：

- `python scripts/*.py`
- `python3 scripts/*.py`
- `py scripts/*.py`
- `mvn ...`
- `./mvnw ...`
- `mvnw ...`
- `npm test`
- `npm run ...`
- `pnpm test`
- `pnpm run ...`
- `yarn test`
- `yarn run ...`

失败处理：如果 policy 中的测试命令被跳过，改成 allowlist 前缀，或在 CI 中单独执行。
