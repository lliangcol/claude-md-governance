# Aliyun Codeup / 云效 CLAUDE.md Governance Step

This repository is configured for a non-GitHub CI provider. Add the following shell commands to a 云效 / Codeup pipeline step that runs on merge requests touching governance files:

```bash
python scripts/claude_md_lint.py \
  --policy .claude-governance/policy.json \
  --output .claude-governance/score.json
python scripts/verify_claude_governance.py
```

Recommended trigger paths:

- `CLAUDE.md`
- `**/CLAUDE.md`
- `.claude/**`
- `.claude-governance/**`
- `scripts/claude_*`
- `tests/ai_behavior_cases*.json`

The optional behavior tests require a logged-in Claude CLI and should usually run manually:

```bash
python scripts/verify_claude_governance.py --with-claude
```
