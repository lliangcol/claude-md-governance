# Policy Reference

Chinese version: [../policy-reference.md](../policy-reference.md)

Policy path: `.claude-governance/policy.json`.

## Top-level fields

- `version`: schema version; current templates use `2`.
- `preset`: `generic`, `java-maven`, or `enterprise-java-codeup`.
- `score_threshold`: lint pass threshold, default `75`.
- `root_doc`: root `AGENTS.md` path and line/token budgets; new templates use this field by default.
- `root_claude`: compatibility field for root `CLAUDE.md` path and line/token budgets.
- `required_sections`: required headings, aliases, severity, and deduction.
- `vague_phrases`: English and Chinese vague phrases.
- `banned_dependencies`: dependencies that must be documented in root instructions and must not appear in dependency files.
- `sensitive_paths`: sensitive path patterns, local `AGENTS.md`/`CLAUDE.md`, test commands, and protection flag.
- `protected_paths`: paths guarded by `PreToolUse`.
- `hooks`: hook requirements and `config_change_mode`.
- `ci`: provider: `auto`, `github`, `codeup`, or `none`.
- `behavior_tests`: optional behavior test configuration.

## Command

Input:

```bash
codex-md-governance lint --repo . --policy .claude-governance/policy.json --output .claude-governance/score.json
```

Output: JSON report with `status`, `score`, `threshold`, `hard_fail`, `findings`, and `summary`.

Failure handling:

- `ROOT_MISSING`: create root `AGENTS.md` or the root instruction file configured by policy.
- `MISSING_SECTION`: add the required heading or an accepted alias.
- `MISSING_LOCAL_DOC`: create local `AGENTS.md`/`CLAUDE.md` rules for the sensitive directory.
- `BANNED_DEP_PRESENT`: remove the policy-banned dependency from dependency files or explicitly update policy.
- `PRE_HOOK_MISSING` / `POST_HOOK_MISSING`: repair `.claude/settings.json`.

## Contributing policy

New fields should be backward compatible. New mandatory rules need tests and synchronized Chinese and English docs.
