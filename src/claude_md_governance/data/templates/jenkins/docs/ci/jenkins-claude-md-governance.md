# Jenkins AGENTS.md Governance

This repository is configured for Jenkins. The installed `Jenkinsfile` runs deterministic governance checks only for change requests that touch root or local instruction files, governance policy, hook settings, or governance scripts.

The required commands are:

```bash
python scripts/claude_md_lint.py --policy .claude-governance/policy.json --output .claude-governance/score.json
python scripts/verify_claude_governance.py
```

The pipeline archives `.claude-governance/score.json` when available so reviewers can inspect lint findings.
