# Research Basis

对应英文版：[docs/en/research-basis.md](en/research-basis.md)

本项目的设计依据是工程治理原则，而不是声称某个 LLM 能被完全约束。

## 基础判断

- 短根上下文比长根上下文更容易维护和审计。
- 机器可读 policy 比自然语言规则更适合 CI。
- 写入前 hook 能降低受保护路径误改概率。
- 写入后 hook 适合发现问题，但不能撤销已经发生的写入。
- LLM 行为测试能提供回归信号，但结果受模型、凭据、环境和提示词影响。

## 可验证假设

输入：

```bash
codex-md-governance verify --repo .
python -m pytest -q
```

输出：确定性 pass/fail。
失败处理：优先修复代码或 policy；不要把失败归因于模型行为。

## 贡献研究材料

新增材料应转化为可执行 rule、policy 字段、测试或文档限制。避免写入无法验证的宣传性结论。
