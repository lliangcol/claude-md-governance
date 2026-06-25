# Reports

Chinese version: [../reports.md](../reports.md)

`report` renders an existing lint score JSON file as review-friendly Markdown.
It does not rerun lint and does not change pass/fail semantics; CI gates should
still use `lint` or `verify`.

## Markdown Report

Create the score JSON first:

```bash
codex-md-governance lint --repo . --policy .claude-governance/policy.json --output .claude-governance/score.json
```

Then render Markdown:

```bash
codex-md-governance report --repo . --score .claude-governance/score.json --output .claude-governance/report.md
```

When `--output` is omitted, the report is printed to stdout:

```bash
codex-md-governance report --repo .
```

Supported formats:

- `--format markdown`: default; renders summary, findings table, and detected sensitive paths.

## Exit Codes

- `0`: report generated successfully, even when the score JSON status is `fail`.
- `2`: score file is missing, not a JSON object, or invalid JSON.

The report command is presentation-only. To block a workflow on failure, keep
using:

```bash
codex-md-governance lint --repo .
codex-md-governance verify --repo .
```
