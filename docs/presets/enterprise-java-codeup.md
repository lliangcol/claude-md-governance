# enterprise-java-codeup preset

对应英文版：[docs/en/presets/enterprise-java-codeup.md](../en/presets/enterprise-java-codeup.md)

## 适用场景

`enterprise-java-codeup` 是面向 enterprise-java-codeup 类 Java/Maven + Codeup 仓库的示例 preset。它不是通用默认值。

## 安装

输入：

```bash
codex-md-governance init --repo <repo> --preset enterprise-java-codeup --ci codeup --config-change-mode warn --yes
codex-md-governance verify --repo <repo>
```

输出：

```text
Preset: enterprise-java-codeup; CI provider: codeup; ConfigChange mode: warn
Governance verification passed.
```

失败处理：

- `Codeup CI instructions exists` 失败：确认 `docs/ci/codeup-claude-md-governance.md` 存在。
- 行为用例路径错误：确认 policy 中 `behavior_tests.case_file` 为 `tests/ai_behavior_cases.enterprise-java-codeup.json`。

## 默认规则

- CI provider：`codeup`。
- 行为测试用例：`tests/ai_behavior_cases.enterprise-java-codeup.json`。
- 敏感路径和 Java/Maven 规则继承 `java-maven` 方向。
- `ConfigChange`：默认 `warn`，避免云效或企业环境配置变更被本地直接硬阻断。

## 边界

该 preset 不会连接真实业务系统，不读取私有配置，不执行 Codeup API。它只安装仓库内文件和 pipeline step 示例。
