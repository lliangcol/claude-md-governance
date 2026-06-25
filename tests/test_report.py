from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from claude_md_governance import report


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "claude_md_governance.cli", *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_render_markdown_report_includes_pass_summary() -> None:
    markdown = report.render_markdown_report(
        {
            "status": "pass",
            "score": 100,
            "threshold": 75,
            "hard_fail": False,
            "findings": [],
            "summary": {
                "errors": 0,
                "warnings": 0,
                "root_doc_path": "AGENTS.md",
                "line_count": 46,
                "estimated_tokens": 761,
            },
        },
        source_path=".claude-governance/score.json",
    )

    assert markdown.startswith("# AGENTS.md Governance Report")
    assert "- Source: `.claude-governance/score.json`" in markdown
    assert "- Status: `PASS`" in markdown
    assert "- Score: `100 / 75`" in markdown
    assert "No findings." in markdown


def test_render_markdown_report_escapes_finding_table_cells() -> None:
    markdown = report.render_markdown_report(
        {
            "status": "fail",
            "score": 70,
            "threshold": 75,
            "hard_fail": True,
            "findings": [
                {
                    "severity": "error",
                    "rule": "ROOT_TOO_LONG",
                    "line": 12,
                    "deduction": 18,
                    "message": "line budget | exceeded\ntrim root instructions",
                    "suggestion": "move details to docs",
                }
            ],
            "summary": {
                "errors": 1,
                "warnings": 0,
                "root_doc_path": "AGENTS.md",
                "line_count": 240,
                "estimated_tokens": 4000,
                "detected_sensitive_dirs": [
                    {"id": "auth", "dir": "src/auth", "local_doc": "src/auth/AGENTS.md"}
                ],
            },
        }
    )

    assert "- Status: `FAIL`" in markdown
    expected_row = (
        "| error | ROOT_TOO_LONG | 12 | 18 | line budget \\| exceeded trim root instructions "
        "| move details to docs |"
    )
    assert expected_row in markdown
    assert "| auth | src/auth | src/auth/AGENTS.md |" in markdown


def test_report_cli_writes_markdown_from_score_json(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    score_dir = repo / ".claude-governance"
    score_dir.mkdir(parents=True)
    (score_dir / "score.json").write_text(
        json.dumps(
            {
                "status": "pass",
                "score": 98,
                "threshold": 75,
                "hard_fail": False,
                "findings": [],
                "summary": {"errors": 0, "warnings": 0, "root_doc_path": "AGENTS.md"},
            }
        ),
        encoding="utf-8",
    )

    proc = run_cli("report", "--repo", str(repo), "--output", ".claude-governance/report.md")

    assert proc.returncode == 0, proc.stdout + proc.stderr
    output = (score_dir / "report.md").read_text(encoding="utf-8")
    assert "- Source: `.claude-governance/score.json`" in output
    assert "- Score: `98 / 75`" in output


def test_report_cli_returns_zero_for_failed_score_json(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    score_dir = repo / ".claude-governance"
    score_dir.mkdir(parents=True)
    (score_dir / "score.json").write_text(
        json.dumps(
            {
                "status": "fail",
                "score": 60,
                "threshold": 75,
                "hard_fail": True,
                "findings": [{"severity": "error", "rule": "ROOT_MISSING", "message": "Root file missing"}],
            }
        ),
        encoding="utf-8",
    )

    proc = run_cli("report", "--repo", str(repo))

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "- Status: `FAIL`" in proc.stdout
    assert "- Findings: `1 error(s), 0 warning(s), 1 total`" in proc.stdout


def test_report_cli_fails_for_missing_score_json(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()

    proc = run_cli("report", "--repo", str(repo))

    assert proc.returncode == 2
    assert "Score report not found" in proc.stderr
