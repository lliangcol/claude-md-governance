# Bad CLAUDE.md Example

Expected:

```bash
claude-md-governance init --repo <tmp> --preset generic --ci none --skip-verify --yes
claude-md-governance lint --repo <tmp>
claude-md-governance verify --repo <tmp>
```

Lint and verify should fail because the root file is vague and missing required
governance structure.

Smoke test:

```bash
bash scripts/smoke.sh
```
