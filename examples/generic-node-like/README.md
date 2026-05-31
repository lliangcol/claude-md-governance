# Generic Node-like Example

Blank starting state: this fixture intentionally has no `CLAUDE.md`. The
installer should create root governance files and a local rule file for
`src/auth`.

Expected:

```bash
claude-md-governance init --repo <tmp> --preset generic --ci github --yes
claude-md-governance verify --repo <tmp>
```

GitHub Actions should be created.

Smoke test:

```bash
bash scripts/smoke.sh
```
