# Security Policy

## Scope

This project generates hook scripts and repository governance files. Hook scripts can execute local commands, so security review matters.

## Supported versions

Until v1.0, only the latest `main` branch is supported.

## Reporting vulnerabilities

Please open a private security advisory or contact the maintainers once the public repository is available. Do not disclose exploitable hook bypasses publicly before maintainers have had time to respond.

## Security principles

- Hooks should be deterministic and minimal.
- Protected paths must include hook scripts and policy files.
- The installer must not delete existing project files.
- Generated scripts must not exfiltrate repository content.
- Optional LLM evaluation must use `--bare` or an equivalent isolation mode.
- Unknown business facts must become TODOs, not fabricated rules.
- Policy-provided hook commands must be parsed, allowlisted, and executed without shell chaining.
- `autofix` must only apply mechanical repairs; it must not fabricate business rules, dependency bans, or domain invariants.
- Generated `.claude/settings.json` must merge only the minimal required hook entries and preserve unrelated user settings.
- Do not commit API keys, tokens, cookies, private absolute paths, or local machine identifiers.

## Release workflow

The release workflow builds on tag pushes only and uploads `dist/*` to the matching GitHub Release with the repository `GITHUB_TOKEN`. It does not publish to PyPI and must not contain credential values. If package publishing is added later, use GitHub secrets by name only or Trusted Publishing, and document the manual approval path.
