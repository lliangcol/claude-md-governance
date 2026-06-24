from __future__ import annotations

import subprocess
import sys


def test_package_importable() -> None:
    import claude_md_governance

    assert claude_md_governance.__version__


def test_cli_help_lists_commands() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "claude_md_governance.cli", "--help"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    for command in ["init", "lint", "autofix", "hook", "verify", "eval", "behavior-test", "doctor", "policy"]:
        assert command in proc.stdout


def test_module_entrypoint_help_lists_commands() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "claude_md_governance", "--help"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "codex-md-governance" in proc.stdout or "claude-md-governance" in proc.stdout
    assert "behavior-test" in proc.stdout


def test_eval_print_command_outputs_command_not_prompt() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "claude_md_governance.cli", "eval", "--print-command", "--repo", "."],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.startswith("claude --bare -p ")
    assert "codex-md-governance eval" in proc.stdout
    assert "independent CLAUDE.md governance evaluator" not in proc.stdout
