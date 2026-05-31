# Release Checklist

- [ ] `python -m pip install -e ".[test]"` passes.
- [ ] pytest pass: `python -m pytest -q`.
- [ ] `claude-md-governance --help` lists all public commands.
- [ ] `claude-md-governance doctor` passes.
- [ ] examples pass.
- [ ] README commands verified.
- [ ] no private paths.
- [ ] no secrets.
- [ ] Optional Claude behavior tests are `PASS` only if they actually ran; otherwise they are `SKIPPED`.
- [ ] package builds:

```bash
python -m pip install build
python -m build
```

- [ ] tag version matches changelog and `pyproject.toml`.

If `python -m build` is unavailable because the optional `build` package is not installed, mark package build as `SKIPPED` and install it before the final release build:

```bash
python -m pip install build
python -m build
```
