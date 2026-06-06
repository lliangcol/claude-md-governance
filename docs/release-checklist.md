# Release Checklist

- [ ] `python -m pip install -e ".[test]"` passes.
- [ ] pytest pass: `python -m pytest -q`.
- [ ] `codex-md-governance --help` lists all public commands.
- [ ] `codex-md-governance doctor` passes.
- [ ] examples pass.
- [ ] README commands verified.
- [ ] no private paths.
- [ ] no secrets.
- [ ] Optional Claude behavior tests are `PASS` only if they actually ran; otherwise they are `SKIPPED`.
- [ ] package builds from a clean tree:

```bash
python -m pip install ".[build]"
python -m build
```

- [ ] package metadata and long description pass:

```bash
python -m twine check dist/*
```

- [ ] wheel install smoke passes from a fresh venv:

```bash
python scripts/wheel_smoke.py --wheel dist/claude_md_governance-0.1.0-py3-none-any.whl
```

- [ ] GitHub Release asset upload is enabled in `.github/workflows/release.yml`.
- [ ] The release page contains the wheel and sdist assets after the tag workflow finishes.
- [ ] release notes include presets, CI modes, verified commands, known limitations, and safety boundaries.
- [ ] tag version matches changelog and `pyproject.toml`.
- [ ] PyPI commands are documented only after the package is actually published.

If `python -m build` is unavailable because the optional `build` package is not installed, mark package build as `SKIPPED` and install it before the final release build:

```bash
python -m pip install ".[build]"
python -m build
```

## Public Safety Scan

Run before tagging:

```bash
git grep -nE "([A-Za-z]:\\\\|/(Users|home)/|token|secret|api[_-]?key)"
git ls-files -i -o --exclude-standard
```

Review any matches manually. Build caches, `__pycache__`, `.pytest_cache`,
`dist/`, `*.egg-info`, and `.claude-governance/score.json` must remain ignored.
