# GitLab CI AGENTS.md Governance

This repository is configured for GitLab CI. The installed `.gitlab-ci.yml` runs deterministic governance checks when merge requests touch root or local instruction files, governance policy, hook settings, or governance scripts.

The required commands are:

```bash
python scripts/claude_md_lint.py --policy .claude-governance/policy.json --output .claude-governance/score.json
python scripts/verify_claude_governance.py
```

The job uploads `.claude-governance/score.json` as a short-lived artifact for review.
