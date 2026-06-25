# Reports

对应英文版：[docs/en/reports.md](en/reports.md)

`report` 将现有 lint score JSON 渲染为可审阅的 Markdown 报告。它不重新运行
lint，也不改变 pass/fail 判定；CI gate 仍应使用 `lint` 或 `verify`。

## Markdown 报告

先生成 score JSON：

```bash
codex-md-governance lint --repo . --policy .claude-governance/policy.json --output .claude-governance/score.json
```

再生成 Markdown：

```bash
codex-md-governance report --repo . --score .claude-governance/score.json --output .claude-governance/report.md
```

不提供 `--output` 时，报告会输出到 stdout：

```bash
codex-md-governance report --repo .
```

当前支持的格式：

- `--format markdown`：默认值，输出 summary、findings 表格和检测到的敏感路径。

## 退出码

- `0`：报告生成成功，即使 score JSON 本身是 `fail`。
- `2`：score 文件缺失、不是 JSON object，或 JSON 解析失败。

报告命令只负责展示。要让失败阻断流程，请继续使用：

```bash
codex-md-governance lint --repo .
codex-md-governance verify --repo .
```
