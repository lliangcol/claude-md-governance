# Contributing

Thanks for helping improve CLAUDE.md Governance.

## Contribution types

- New policy rules or presets.
- Bug fixes in installer, linter, autofix, hook guard, or verifier.
- Documentation and examples.
- CI provider integrations.
- Behavior regression cases.

## Development workflow

```bash
python -m pip install -e ".[test]"
python -m pytest -q
claude-md-governance doctor
claude-md-governance init --repo /tmp/claude-gov-smoke --yes --preset generic --ci none
claude-md-governance verify --repo /tmp/claude-gov-smoke
```

## Starter Tasks

Good first issues should stay small, verifiable, and useful to new users:

- Add a preset request with target stack, sensitive paths, CI environment, and validation commands.
- Add a behavior regression case to `tests/ai_behavior_cases*.json` with expected pass/fail signals.
- Add CI provider documentation for a real provider without changing default install behavior.
- Add a small demo fixture that proves one governance rule or failure mode.
- Improve screenshots, release notes, README examples, or docs navigation.

## Rule requirements

A new governance rule must include:

1. A clear problem statement.
2. A deterministic check when possible.
3. A suggested remediation.
4. A fixture or smoke test.
5. A note on whether it should be warning or hard fail.

## Safety rule

Do not add project-specific banned dependencies or business invariants to generic presets without evidence. Use TODO placeholders when facts are unknown.

Hook guard changes must keep policy-provided commands on the allowlist and execute them without shell chaining. `autofix` may create placeholders and hook registrations, but it must not invent business rules.
