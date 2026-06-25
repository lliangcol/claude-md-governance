from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys


def installed_script(command: str) -> str:
    script_dir = Path(sys.executable).resolve().parent
    path = shutil.which(command, path=str(script_dir))
    assert path is not None, f"{command} entry point not found in {script_dir}"
    return path


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
    for command in ["init", "lint", "report", "autofix", "hook", "verify", "eval", "behavior-test", "doctor", "policy"]:
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


def test_installed_console_scripts_include_primary_and_legacy_aliases() -> None:
    for command in ["codex-md-governance", "claude-md-governance"]:
        script = installed_script(command)
        version = subprocess.run(
            [script, "--version"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        assert version.returncode == 0, version.stderr
        assert version.stdout.startswith(f"{command} ")

        validate = subprocess.run(
            [script, "policy", "validate", "--repo", "."],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        assert validate.returncode == 0, validate.stdout + validate.stderr
        assert json.loads(validate.stdout) == {"status": "pass", "errors": []}

        allowlist = subprocess.run(
            [script, "policy", "command-allowlist"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        assert allowlist.returncode == 0, allowlist.stdout + allowlist.stderr
        payload = json.loads(allowlist.stdout)
        assert payload["shell"] is False
        assert payload["strict_by_default"] is True


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
