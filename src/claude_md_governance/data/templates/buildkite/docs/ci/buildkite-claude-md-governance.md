# Buildkite AGENTS.md Governance

This repository is configured for Buildkite. The installed `.buildkite/pipeline.yml` runs deterministic governance checks and uploads `.claude-governance/score.json` as an artifact.

The required commands are:

```bash
python scripts/claude_md_lint.py --policy .claude-governance/policy.json --output .claude-governance/score.json
python scripts/verify_claude_governance.py
```

Use Buildkite branch or pipeline settings to decide which branches and pull requests run this governance step.
