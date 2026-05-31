# Java/Maven-like Example

Blank starting state: this fixture intentionally has no `CLAUDE.md`. The
installer should infer a Maven-style stack from `pom.xml` when it creates root
governance files.

Expected:

```bash
claude-md-governance init --repo <tmp> --preset java-maven --ci none --yes
claude-md-governance verify --repo <tmp>
```

Smoke test:

```bash
bash scripts/smoke.sh
```
