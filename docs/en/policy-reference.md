# Policy Reference

Chinese version: [../policy-reference.md](../policy-reference.md)

Policy path: `.claude-governance/policy.json`.

## Top-level fields

- `version`: schema version; current templates use `2`.
- `preset`: `generic`, `java-maven`, or `onm-agent`.
- `score_threshold`: lint pass threshold, default `75`.
- `root_claude`: root `CLAUDE.md` path and line/token budgets.
- `required_sections`: required headings, aliases, severity, and deduction.
- `vague_phrases`: English and Chinese vague phrases.
- `banned_dependencies`: dependencies that must be documented in `CLAUDE.md`.
- `sensitive_paths`: sensitive path patterns, local `CLAUDE.md`, test commands, and protection flag.
- `protected_paths`: paths guarded by `PreToolUse`.
- `hooks`: hook requirements and `config_change_mode`.
- `ci`: provider: `auto`, `github`, `codeup`, or `none`.
- `behavior_tests`: optional behavior test configuration.

## Command

Input:

```bash
claude-md-governance lint --repo . --policy .claude-governance/policy.json --output .claude-governance/score.json
```

Output: JSON report with `status`, `score`, `threshold`, `hard_fail`, `findings`, and `summary`.

Failure handling:

- `ROOT_MISSING`: create root `CLAUDE.md`.
- `MISSING_SECTION`: add the required heading or an accepted alias.
- `MISSING_LOCAL_CLAUDE`: create local rules for the sensitive directory.
- `PRE_HOOK_MISSING` / `POST_HOOK_MISSING`: repair `.claude/settings.json`.

## Contributing policy

New fields should be backward compatible. New mandatory rules need tests and synchronized Chinese and English docs.
