# Architecture

对应英文版：[docs/en/architecture.md](en/architecture.md)

## 组件

- `src/claude_md_governance/cli.py`：统一 CLI 入口。
- `installer.py`：安装 common 模板、policy、hook settings 和 CI 模板。
- `policy.py`：package 内 policy 路径解析、root-doc 兼容迁移和默认值合并入口。
- `lint.py`：确定性评分器。
- `hook_guard.py`：Claude Code hook guard。
- `verify.py`：安装后 smoke verification。
- `behavior.py`：可选 Claude CLI 行为测试。
- `data/templates/`：common、github、gitlab、jenkins、buildkite、codeup 和 policies 模板。

## 数据流

1. `init` 读取目标仓库，选择 preset、CI provider 和 config mode。
2. 安装器复制模板，合并 `.claude/settings.json`，生成或合并 policy。
3. `lint` 读取 policy 和 root instruction file，输出 score report。
4. hook guard 在 Claude Code 事件中读取同一份 policy。
5. CI 运行 lint 和 verify，保证安装结构仍可执行。

## 命令一致性

所有公开命令以 `codex-md-governance <subcommand>` 暴露，`claude-md-governance` 保留为兼容 alias。模板中仍保留 `python scripts/...`，因为安装后的目标仓库不一定安装了 Python package，但会包含本地脚本。

失败处理：

- CLI 参数变化时，同时更新 `cli.py`、模板脚本、README、中文 docs 和英文 docs。
- 模板结构变化时，运行 `python -m pytest -q` 和至少一个 init/verify smoke。
