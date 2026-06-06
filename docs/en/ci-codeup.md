# Codeup / Yunxiao

Chinese version: [../ci-codeup.md](../ci-codeup.md)

## Install

Input:

```bash
codex-md-governance init --repo . --preset enterprise-java-codeup --ci codeup --config-change-mode warn --yes
```

Output:

- `ci/codeup/claude-md-governance-step.yml`
- `docs/ci/codeup-claude-md-governance.md`
- `ci.provider=codeup` in `.claude-governance/policy.json`

Failure handling:

- Files missing: confirm `--ci codeup`.
- Existing files were not overwritten: rerun with `--force` and inspect `.claude-governance/backups/`.

## Pipeline step

Add these commands to a Yunxiao / Codeup pipeline:

```bash
python scripts/claude_md_lint.py \
  --policy .claude-governance/policy.json \
  --output .claude-governance/score.json
python scripts/verify_claude_governance.py
```

Input: checked-out repository.
Output: pipeline step pass/fail.
Failure handling: fix the `FAIL` line and score report findings.

## Recommended trigger paths

- `AGENTS.md`
- `**/AGENTS.md`
- `CLAUDE.md`
- `**/CLAUDE.md`
- `.agents/**`
- `.codex/**`
- `.claude/**`
- `.claude-governance/**`
- `scripts/claude_*`
- `tests/ai_behavior_cases*.json`

Optional behavior tests also require a logged-in Claude CLI and are not recommended as default Codeup hard gates.
