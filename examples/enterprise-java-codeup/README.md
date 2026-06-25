# enterprise-java-codeup Example

Blank starting state: this fixture intentionally has no root `AGENTS.md` or
`CLAUDE.md`. The payment-like module should be detected as sensitive and
receive a local `AGENTS.md`.

Expected:

```bash
claude-md-governance init --repo <tmp> --preset enterprise-java-codeup --ci codeup --config-change-mode warn --yes
claude-md-governance verify --repo <tmp>
```

GitHub Actions should not be created. Codeup docs should be created.

Smoke test:

```bash
bash scripts/smoke.sh
```
