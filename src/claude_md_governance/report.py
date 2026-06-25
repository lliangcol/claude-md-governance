#!/usr/bin/env python3
"""Render governance score JSON as review-friendly reports."""
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

DEFAULT_SCORE_PATH = ".claude-governance/score.json"


def _repo_path(repo: Path, path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else repo / path


def _display_path(repo: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _as_findings(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _markdown_cell(value: Any) -> str:
    if value is None or value == "":
        return "-"
    text = str(value).replace("|", "\\|")
    return " ".join(text.splitlines()) or "-"


def _format_bool(value: Any) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    return "unknown"


def _format_count(value: Any) -> str:
    if isinstance(value, bool):
        return "unknown"
    if isinstance(value, int):
        return str(value)
    return "unknown" if value is None else str(value)


def read_score_report(path: Path) -> Mapping[str, Any]:
    """Read and validate the JSON score report shape enough for reporting."""
    if not path.exists():
        raise FileNotFoundError(f"Score report not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid score report JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}") from exc
    if not isinstance(data, Mapping):
        raise ValueError("Score report root must be a JSON object")
    return data


def render_markdown_report(score_report: Mapping[str, Any], *, source_path: str | None = None) -> str:
    """Render a deterministic Markdown report from lint score JSON."""
    summary = _as_mapping(score_report.get("summary"))
    findings = _as_findings(score_report.get("findings"))
    status = str(score_report.get("status", "unknown")).upper()
    score = _format_count(score_report.get("score"))
    threshold = _format_count(score_report.get("threshold"))
    error_count = summary.get("errors", sum(1 for finding in findings if finding.get("severity") == "error"))
    warning_count = summary.get("warnings", sum(1 for finding in findings if finding.get("severity") == "warning"))
    errors = _format_count(error_count)
    warnings = _format_count(warning_count)
    root_doc = summary.get("root_doc_path") or summary.get("claude_path") or "unknown"
    sensitive_dirs = _as_findings(summary.get("detected_sensitive_dirs"))

    lines = [
        "# AGENTS.md Governance Report",
        "",
        "## Summary",
    ]
    if source_path:
        lines.append(f"- Source: `{source_path}`")
    lines.extend(
        [
            f"- Status: `{status}`",
            f"- Score: `{score} / {threshold}`",
            f"- Hard fail: `{_format_bool(score_report.get('hard_fail'))}`",
            f"- Root document: `{root_doc}`",
            f"- Lines: `{_format_count(summary.get('line_count'))}`",
            f"- Estimated tokens: `{_format_count(summary.get('estimated_tokens'))}`",
            f"- Findings: `{errors} error(s), {warnings} warning(s), {len(findings)} total`",
        ]
    )

    lines.extend(["", "## Findings", ""])
    if not findings:
        lines.append("No findings.")
    else:
        lines.extend(
            [
                "| Severity | Rule | Line | Deduction | Message | Suggestion |",
                "| --- | --- | ---: | ---: | --- | --- |",
            ]
        )
        for finding in findings:
            lines.append(
                "| "
                + " | ".join(
                    [
                        _markdown_cell(finding.get("severity")),
                        _markdown_cell(finding.get("rule")),
                        _markdown_cell(finding.get("line")),
                        _markdown_cell(finding.get("deduction")),
                        _markdown_cell(finding.get("message")),
                        _markdown_cell(finding.get("suggestion")),
                    ]
                )
                + " |"
            )

    if sensitive_dirs:
        lines.extend(
            [
                "",
                "## Sensitive Paths",
                "",
                "| ID | Directory | Local document |",
                "| --- | --- | --- |",
            ]
        )
        for item in sensitive_dirs:
            lines.append(
                "| "
                + " | ".join(
                    [
                        _markdown_cell(item.get("id")),
                        _markdown_cell(item.get("dir")),
                        _markdown_cell(item.get("local_doc")),
                    ]
                )
                + " |"
            )

    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render governance score reports.")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--score", default=DEFAULT_SCORE_PATH)
    parser.add_argument("--output", default=None)
    parser.add_argument("--format", default="markdown", choices=["markdown"])
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    repo = Path(args.repo).resolve()
    score_path = _repo_path(repo, args.score).resolve()

    try:
        score_report = read_score_report(score_path)
        markdown = render_markdown_report(score_report, source_path=_display_path(repo, score_path))
    except (FileNotFoundError, OSError, ValueError) as exc:
        print(f"[claude-governance] {exc}", file=sys.stderr)
        return 2

    if args.output:
        output_path = _repo_path(repo, args.output).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown + "\n", encoding="utf-8")
    else:
        print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
