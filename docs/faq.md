# FAQ

对应英文版：[docs/en/faq.md](en/faq.md)

## 这个项目会替我写 AGENTS.md 吗？

`init` 会生成骨架并补齐缺失章节，但内容仍需要仓库维护者填入真实架构、禁用依赖和敏感边界。

## 为什么 README 说 PostToolUse 不能撤销写入？

因为 `PostToolUse` 发生在工具动作之后。它能失败退出并阻止后续流程，但已经写入的文件不会自动恢复。

## 可以不接 CI 吗？

可以。使用：

```bash
codex-md-governance init --repo . --preset generic --ci none --yes
```

输出：不生成 GitHub、GitLab、Jenkins、Buildkite 或 Codeup CI 文件。
失败处理：仍建议本地运行 `codex-md-governance verify --repo .`。

## 如何只生成 GitLab pipeline？

```bash
codex-md-governance init --repo . --preset generic --ci gitlab --yes
```

失败处理：如果已有 `.gitlab-ci.yml` 未覆盖，加 `--force`。

## 如何只生成 Jenkins pipeline？

```bash
codex-md-governance init --repo . --preset generic --ci jenkins --yes
```

失败处理：如果已有 `Jenkinsfile` 未覆盖，加 `--force`。

## 如何只生成 Buildkite pipeline？

```bash
codex-md-governance init --repo . --preset generic --ci buildkite --yes
```

失败处理：如果已有 `.buildkite/pipeline.yml` 未覆盖，加 `--force`。

## 如何只生成 Codeup 示例？

```bash
codex-md-governance init --repo . --preset enterprise-java-codeup --ci codeup --config-change-mode warn --yes
```

失败处理：如果已有文件未覆盖，加 `--force`。

## 行为测试为什么跳过？

默认缺少 Claude CLI 时跳过。需要强制执行：

```bash
codex-md-governance behavior-test --repo . --require-claude
```

失败处理：安装并登录 Claude CLI，或移除 `--require-claude`。

## 如何贡献 preset？

新增 policy JSON、中文文档、英文文档、测试和示例。至少运行：

```bash
python -m pytest -q
codex-md-governance verify --repo .
```
