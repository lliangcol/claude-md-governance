# Release Notes: v0.1.0

`v0.1.0` is the first public release candidate for CLAUDE.md Governance.

## What Ships

- Python CLI: `claude-md-governance`.
- Presets: `generic`, `java-maven`, `enterprise-java-codeup`.
- CI modes: `github`, `gitlab`, `jenkins`, `buildkite`, `codeup`, `none`, and conservative `auto` detection.
- Deterministic commands: `init`, `lint`, `autofix`, `hook`, `verify`, `eval`, `behavior-test`, and `doctor`.
- Package-managed templates for policy files, Claude Code hooks, governance scripts, GitHub Actions, GitLab CI, Jenkins, Buildkite, Codeup docs, and the Claude Code skill.

## Verified Commands

Run before creating the tag:

```bash
python -m pip install -e ".[test,build]"
python -m pytest -q
python -m claude_md_governance doctor
python -m build
python -m twine check dist/*
python scripts/wheel_smoke.py --wheel dist/claude_md_governance-0.1.0-py3-none-any.whl
```

## Known Limitations

- Claude CLI behavior tests are optional. If Claude CLI is not installed or not logged in, behavior tests must report `SKIPPED`, not `PASS`.
- PyPI installation must not be advertised until the package is actually published.
- GitHub Release assets are the first public binary distribution path for this release.
- Until `v1.0`, policy schema and installer behavior may change with documented migration notes.

## Safety Boundaries

- Hook commands are allowlisted and executed without shell chaining.
- Hooks run in the target repository and do not send telemetry.
- `autofix` performs mechanical repairs only; it must not invent business rules.
- This tool does not replace human code review, secret scanning, or dependency review.

## GitHub Release Checklist

- Tag matches `pyproject.toml` and `CHANGELOG.md`.
- Release workflow uploads `dist/*` to the matching GitHub Release.
- Release description links to README, demo, release checklist, and security model.
- Social preview and topics are configured manually in GitHub repository settings.
