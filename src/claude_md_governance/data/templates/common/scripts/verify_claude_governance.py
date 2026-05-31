#!/usr/bin/env python3
"""Automated smoke tests for CLAUDE.md governance installation."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List


def run(cmd: List[str], *, input_text: str | None = None, env: Dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, input=input_text, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)


def assert_true(condition: bool, message: str, failures: List[str]) -> None:
    if condition:
        print(f"PASS: {message}")
    else:
        print(f"FAIL: {message}")
        failures.append(message)


def load_policy() -> Dict:
    try:
        return json.loads(Path(".claude-governance/policy.json").read_text(encoding="utf-8"))
    except Exception:
        return {}


def json_status(output: str) -> str:
    try:
        payload = json.loads(output)
    except Exception:
        return ""
    return str(payload.get("status", ""))


def config_change_mode(policy: Dict) -> str:
    hooks = policy.get("hooks", {})
    configured = str(hooks.get("config_change_mode", "")).lower()
    if configured in {"block", "warn", "off"}:
        return configured
    if hooks.get("protected_config_review_required") is False:
        return "warn"
    return "block"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    parser.add_argument("--with-claude", action="store_true", help="Also run optional AI behavior tests through Claude CLI if available")
    parser.add_argument("--require-claude", action="store_true", help="Fail if Claude CLI behavior tests cannot run")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    os.chdir(repo)
    failures: List[str] = []

    required = [
        "CLAUDE.md",
        ".claude/settings.json",
        ".claude-governance/policy.json",
        "scripts/claude_md_lint.py",
        "scripts/claude_hook_guard.py",
    ]
    for rel in required:
        assert_true(Path(rel).exists(), f"required file exists: {rel}", failures)

    policy = load_policy()

    ci_provider = policy.get("ci", {}).get("provider", "none")
    if ci_provider == "github":
        assert_true(Path(".github/workflows/claude-md-governance.yml").exists(), "GitHub Actions workflow exists", failures)
    if ci_provider == "codeup":
        assert_true(Path("docs/ci/codeup-claude-md-governance.md").exists(), "Codeup CI instructions exist", failures)

    lint = run([sys.executable, "scripts/claude_md_lint.py", "--policy", ".claude-governance/policy.json", "--output", ".claude-governance/score.json", "--quiet"])
    assert_true(lint.returncode == 0, "static linter passes", failures)
    if lint.returncode != 0:
        print(lint.stdout)
        print(lint.stderr, file=sys.stderr)

    protected_event = json.dumps({"tool_input": {"file_path": ".claude/settings.json"}})
    proc = run([sys.executable, "scripts/claude_hook_guard.py", "pre"], input_text=protected_event)
    assert_true(proc.returncode == 2, "PreToolUse blocks protected settings edit", failures)

    env = os.environ.copy()
    env["ALLOW_PROTECTED_EDIT"] = "1"
    proc_allowed = run([sys.executable, "scripts/claude_hook_guard.py", "pre"], input_text=protected_event, env=env)
    assert_true(proc_allowed.returncode == 0, "PreToolUse allows protected edit when explicitly approved", failures)

    unprotected_event = json.dumps({"tool_input": {"file_path": "README.md"}})
    proc_open = run([sys.executable, "scripts/claude_hook_guard.py", "pre"], input_text=unprotected_event)
    assert_true(proc_open.returncode == 0, "PreToolUse allows unprotected edit", failures)

    cfg_mode = config_change_mode(policy)
    cfg_event = json.dumps({"config_key": "model", "new_value": "example"})
    cfg_proc = run([sys.executable, "scripts/claude_hook_guard.py", "config"], input_text=cfg_event)
    if cfg_mode == "block":
        assert_true(cfg_proc.returncode == 2, "ConfigChange blocks", failures)
    elif cfg_mode == "warn":
        output = cfg_proc.stdout + cfg_proc.stderr
        assert_true(cfg_proc.returncode == 0 and "WARNING" in output, "ConfigChange warn emits warning and does not block", failures)
    else:
        assert_true(cfg_proc.returncode == 0, f"ConfigChange is {cfg_mode} (non-blocking)", failures)

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix="_CLAUDE.md", delete=False) as f:
        f.write(("# Project Overview\n\n保持简洁。高质量。注重性能。\n") * 80)
        bad_path = f.name
    try:
        bad = run([sys.executable, "scripts/claude_md_lint.py", "--policy", ".claude-governance/policy.json", "--claude", bad_path, "--fail-under", "75", "--quiet"])
        assert_true(bad.returncode != 0, "mutation test catches bad CLAUDE.md", failures)
    finally:
        Path(bad_path).unlink(missing_ok=True)

    if args.with_claude:
        if shutil.which("claude") is None:
            print("SKIPPED: Claude CLI not found; optional behavior tests were not run.")
            if args.require_claude:
                failures.append("Claude CLI behavior tests required but Claude CLI is not installed")
        else:
            case_file = policy.get("behavior_tests", {}).get("case_file", "tests/ai_behavior_cases.json")
            behavior_cmd = [sys.executable, "scripts/run_ai_behavior_tests.py", "--repo", str(repo), "--cases", case_file]
            if args.require_claude:
                behavior_cmd.append("--require-claude")
            behavior = run(behavior_cmd)
            print(behavior.stdout)
            print(behavior.stderr, file=sys.stderr)
            status = json_status(behavior.stdout)
            if behavior.returncode == 0 and status == "skipped":
                print("SKIPPED: Claude CLI behavior tests did not run.")
            elif status == "skipped":
                assert_true(False, "AI behavior tests are required but were skipped", failures)
            else:
                assert_true(behavior.returncode == 0, "AI behavior tests pass", failures)

    if failures:
        print("\nGovernance verification failed:")
        for f in failures:
            print(f"- {f}")
        return 1

    print("\nGovernance verification passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
