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
- `ci`: provider: `auto`, `github`, `gitlab`, `jenkins`, `buildkite`, `codeup`, or `none`.
- `behavior_tests`: optional behavior test configuration.

## Command

Input:

```bash
codex-md-governance lint --repo . --policy .claude-governance/policy.json --output .claude-governance/score.json
```

Output: JSON report with `status`, `score`, `threshold`, `hard_fail`, `findings`, and `summary`.

Validate the policy schema:

```bash
codex-md-governance policy validate --repo . --policy .claude-governance/policy.json
```

Conservatively migrate an older policy shape:

```bash
codex-md-governance policy migrate --repo . --policy .claude-governance/policy.json --write
```

Inspect the hook policy command allowlist:

```bash
codex-md-governance policy command-allowlist
```

`migrate` only fills mechanically derivable fields such as `root_doc`, `hooks.config_change_mode`, and `ci.provider`; maintainers should still edit fields that require project knowledge. When `init` merges an existing policy, it applies the same root-doc compatibility rule first so legacy `CLAUDE.md` repositories are not silently switched to the new-template default `AGENTS.md`.

Failure handling:

- `ROOT_MISSING`: create root `AGENTS.md` or the root instruction file configured by policy.
- `MISSING_SECTION`: add the required heading or an accepted alias.
- `MISSING_LOCAL_DOC`: create local `AGENTS.md`/`CLAUDE.md` rules for the sensitive directory.
- `ROOT_LOCAL_DOC_CONFLICT`: move the local rule path under the sensitive directory; the local instruction file must not resolve to the root instruction file.
- `BANNED_DEP_PRESENT`: remove the policy-banned dependency from dependency files or explicitly update policy.
- `PRE_HOOK_MISSING` / `POST_HOOK_MISSING`: repair `.claude/settings.json`.

## Contributing policy

New fields should be backward compatible. New mandatory rules need tests and synchronized Chinese and English docs.
