# Java/Maven-like Example

Blank starting state: this fixture intentionally has no root `AGENTS.md` or
`CLAUDE.md`. The installer should infer a Maven-style stack from `pom.xml`,
create root governance files, and add a local `AGENTS.md` rule file for the
order-like module.

Expected:

```bash
claude-md-governance init --repo <tmp> --preset java-maven --ci none --yes
claude-md-governance verify --repo <tmp>
```

Smoke test:

```bash
bash scripts/smoke.sh
```
