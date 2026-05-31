# Pull Request

## Summary

## Test plan

- [ ] `python -m pip install -e ".[test]"`
- [ ] `python -m pytest -q`
- [ ] `claude-md-governance doctor`
- [ ] Relevant example or preset smoke test

## Safety checklist

- [ ] No project-specific facts added to generic presets without evidence.
- [ ] Hook policy commands stay allowlisted and do not require shell execution.
- [ ] Generated `.claude/settings.json` changes are minimal hook merges.
- [ ] No API keys, tokens, private paths, or local machine details are included.
- [ ] Documentation updated.
- [ ] CHANGELOG updated if user-visible.
