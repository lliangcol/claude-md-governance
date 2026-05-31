# FAQ

Chinese version: [../faq.md](../faq.md)

## Does this write CLAUDE.md for me?

`init` creates a skeleton and fills missing sections, but maintainers still need to add real architecture, banned dependencies, and sensitive boundaries.

## Why does PostToolUse not undo writes?

Because `PostToolUse` runs after the tool action. It can fail and stop the next flow, but files already written are not automatically restored.

## Can I skip CI?

Yes:

```bash
claude-md-governance init --repo . --preset generic --ci none --yes
```

Output: no GitHub or Codeup CI files.
Failure handling: still run `claude-md-governance verify --repo .` locally.

## How do I generate only a Codeup example?

```bash
claude-md-governance init --repo . --preset onm-agent --ci codeup --config-change-mode warn --yes
```

Failure handling: use `--force` if managed files already exist.

## Why were behavior tests skipped?

They skip by default when Claude CLI is missing. To require them:

```bash
claude-md-governance behavior-test --repo . --require-claude
```

Failure handling: install and log in to Claude CLI, or remove `--require-claude`.

## How do I contribute a preset?

Add policy JSON, Chinese docs, English docs, tests, and examples. Run at least:

```bash
python -m pytest -q
claude-md-governance verify --repo .
```
