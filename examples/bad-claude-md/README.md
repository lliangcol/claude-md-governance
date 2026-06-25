# Bad AGENTS.md Example

Expected:

```bash
claude-md-governance init --repo <tmp> --preset generic --ci none --skip-verify --yes
claude-md-governance lint --repo <tmp>
claude-md-governance verify --repo <tmp>
```

Lint and verify should fail because the root `AGENTS.md` file keeps vague,
non-measurable rules even after `init` appends the missing governance sections.
The directory name is retained for demo script compatibility.

Smoke test:

```bash
bash scripts/smoke.sh
```
