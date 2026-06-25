# Security Model

对应英文版：[docs/en/security-model.md](en/security-model.md)

## 保护目标

- 防止受保护治理文件被无提示修改。
- 让敏感业务目录拥有本地 `AGENTS.md`/`CLAUDE.md`。
- 在 CI 中发现根指令过长、规则空泛、hook 缺失。
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

Python policy 脚本必须是仓库相对的 `scripts/` 目录内 `.py` 文件；绝对路径或包含 `..` 后会逃出 `scripts/` 的路径会被拒绝。
所有参数中的 shell control operator（如 `&&`、`||`、`;`、`|`、`<`、`>`）都会被拒绝，
避免把 shell-chain 片段当成普通参数后仍执行第一段命令。

每条 policy 命令默认最多运行 300 秒，可用 `CLAUDE_GOVERNANCE_COMMAND_TIMEOUT_SECONDS` 调整。

可审计 allowlist：

```bash
codex-md-governance policy command-allowlist
```

该命令输出机器可读 JSON，包含 `shell: false`、严格模式环境变量、超时环境变量、
允许的命令形态和示例。默认严格模式下，非 allowlist 命令返回 `2`；只有显式设置
`CLAUDE_GOVERNANCE_STRICT_COMMANDS=warn`、`0`、`false` 或 `off` 时才降级为警告。

失败处理：如果 policy 中的测试命令被跳过，改成 allowlist 前缀，或在 CI 中单独执行。

## 受保护路径授权

如果确需编辑受保护路径，先取得人工确认，再设置路径范围授权：

```powershell
$env:CLAUDE_GOVERNANCE_APPROVED_PATHS = ".claude/settings.json"
```

该变量只放行匹配的路径或 glob；不要使用全局放行。

受保护集合由 `protected_paths` 和 `sensitive_paths` 中 `protected: true` 的条目组成。hook guard 会规范化路径分隔符，并对单个事件里的所有路径逐一匹配；匹配时同时检查词法路径和 symlink 解析后的真实路径。MultiEdit / nested edit 中任一未授权受保护路径都会阻止整个事件。授权值可使用仓库相对路径、仓库内绝对路径或 glob，按逗号、分号或换行拆分，并使用同一套 glob 匹配。

仓库外路径不属于本仓库 policy 可审计范围，因此默认退出 `2`。只有取得人工确认并在 `CLAUDE_GOVERNANCE_APPROVED_PATHS` 中显式匹配该仓库外路径或 glob 后，hook guard 才会放行。若仓库内 symlink 解析到仓库外目标，授权必须匹配解析后的仓库外目标；只匹配 symlink 的仓库相对路径不会放行。

非空 hook 输入如果不是合法 JSON 对象，guard 会 fail closed 并退出 `2`，避免在无法判断目标路径时放行写入。
