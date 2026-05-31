---
name: claude-md-governance
description: Evaluate, repair, and verify CLAUDE.md quality governance for a repository. Use this skill when CLAUDE.md, .claude settings, hooks, memory, AI coding rules, or agent governance are discussed.
---

# CLAUDE.md Governance Skill

Use this skill to keep repository AI instructions short, enforceable, and safe.

## Operating rules

1. Treat CLAUDE.md as always-loaded context. Keep it short and global.
2. Move long procedures into skills or docs, referenced by path from CLAUDE.md.
3. Use local CLAUDE.md files or path-scoped rules for sensitive directories such as auth, billing, payments, migrations, MQ consumers, and infra.
4. Use hooks and CI for deterministic enforcement; do not rely on reminders.
5. Prefer conservative defaults. If a project-specific decision is unknown, create a clearly marked TODO and continue.
6. After changing CLAUDE.md or governance files, run:

```bash
python scripts/claude_md_lint.py --policy .claude-governance/policy.json --output .claude-governance/score.json
python scripts/verify_claude_governance.py
```

## Fix sequence

1. Run the static linter.
2. Fix hard failures first: excessive length, missing Do NOT introduce, missing hooks, sensitive directories without local rules.
3. Rewrite vague rules into measurable rules.
4. Replace long @imports with Context Map links unless the file is small and truly always needed.
5. Add or update local CLAUDE.md files under sensitive modules.
6. Run automated verification.
7. Summarize score, hard failures, fixes, and remaining TODOs.
