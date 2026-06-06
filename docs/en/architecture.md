# Architecture

Chinese version: [../architecture.md](../architecture.md)

## Components

- `src/claude_md_governance/cli.py`: public CLI entry.
- `installer.py`: installs common templates, policy, hook settings, and CI templates.
- `lint.py`: deterministic scorer.
- `hook_guard.py`: Claude Code hook guard.
- `verify.py`: post-install smoke verification.
- `behavior.py`: optional Claude CLI behavior tests.
- `data/templates/`: common, github, codeup, and policies templates.

## Data flow

1. `init` reads the target repository and selects preset, CI provider, and config mode.
2. The installer copies templates, merges `.claude/settings.json`, and writes or merges policy.
3. `lint` reads policy and the root instruction file, then writes a score report.
4. The hook guard reads the same policy during Claude Code events.
5. CI runs lint and verify to keep the installation executable.

## Command consistency

Public commands are exposed as `codex-md-governance <subcommand>`; `claude-md-governance` remains as a compatibility alias. Templates still use `python scripts/...` because installed target repositories may not have the package installed, but they do contain local scripts.

Failure handling:

- When CLI arguments change, update `cli.py`, templates, README, Chinese docs, and English docs together.
- When template layout changes, run `python -m pytest -q` and at least one init/verify smoke.
