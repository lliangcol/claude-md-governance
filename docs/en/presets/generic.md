# Generic preset

Chinese version: [../../presets/generic.md](../../presets/generic.md)

## Use case

`generic` fits general Python, Node, Go, Rust, or mixed repositories. It does not assume Codeup, Maven, or business-specific modules.

## Install

Input:

```bash
claude-md-governance init --repo . --preset generic --ci github --yes
claude-md-governance verify --repo .
```

Output:

```text
Preset: generic; CI provider: github; ConfigChange mode: block
Governance verification passed.
```

Failure handling:

- Missing GitHub workflow: confirm `--ci github`.
- ConfigChange verification fails: check `.claude/settings.json` for `python scripts/claude_hook_guard.py config`.

## Defaults

- Root `CLAUDE.md`: `warn_lines=160`, `max_lines=200`, `hard_fail_lines=220`.
- Required sections: Project Overview, Tech Stack, Do NOT introduce, Code Rules, Context Map, Quality Gates, Working Style.
- Sensitive paths: `src/auth/**`, `src/billing/**`, `src/payments/**`, `prisma/migrations/**`, `infra/**`.
- `ConfigChange`: `block`.

## Contributing rules

Add enforceable rules to policy first, then tests. Natural-language-only rules cannot be checked by CI.
