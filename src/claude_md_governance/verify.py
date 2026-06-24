#!/usr/bin/env python3
"""Automated smoke tests for repository instruction governance installation."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List

try:
    from claude_md_governance.policy_schema import PolicyValidationError, load_policy_file
except Exception:  # pragma: no cover - used by repository-local copied scripts.
    class PolicyValidationError(ValueError):  # type: ignore[no-redef]
        def __init__(self, path: Path, errors: List[str]) -> None:
            self.path = path
            self.errors = tuple(errors)
            super().__init__(f"Invalid policy file {path}: {'; '.join(errors)}")

    def _is_non_empty_string(value: object) -> bool:
        return isinstance(value, str) and bool(value.strip())

    def _validate_string_list(errors: List[str], value: object, key: str) -> None:
        if value is None:
            return
        if not isinstance(value, list) or any(not _is_non_empty_string(item) for item in value):
            errors.append(f"{key} must be an array of non-empty strings")

    def _validate_policy(policy: object) -> List[str]:
        if not isinstance(policy, dict):
            return ["policy root must be a JSON object"]
        errors: List[str] = []
        version = policy.get("version")
        if not isinstance(version, int) or isinstance(version, bool) or version < 1:
            errors.append("version must be a positive integer")
        if not _is_non_empty_string(policy.get("preset")):
            errors.append("preset must be a non-empty string")
        hooks = policy.get("hooks")
        if not isinstance(hooks, dict):
            errors.append("hooks must be an object")
        else:
            if "config_change_mode" not in hooks:
                errors.append("hooks.config_change_mode is required")
            mode = hooks.get("config_change_mode", "block")
            if mode not in {"block", "warn", "off"}:
                errors.append("hooks.config_change_mode must be one of: block, warn, off")
        _validate_string_list(errors, policy.get("protected_paths", []), "protected_paths")
        sensitive = policy.get("sensitive_paths", [])
        if not isinstance(sensitive, list):
            errors.append("sensitive_paths must be an array")
        else:
            for index, item in enumerate(sensitive):
                item_path = f"sensitive_paths[{index}]"
                if not isinstance(item, dict):
                    errors.append(f"{item_path} must be an object")
                    continue
                if not _is_non_empty_string(item.get("path")):
                    errors.append(f"{item_path}.path must be a non-empty string")
                _validate_string_list(errors, item.get("required_tests", []), f"{item_path}.required_tests")
                if "protected" in item and not isinstance(item.get("protected"), bool):
                    errors.append(f"{item_path}.protected must be a boolean")
        return errors

    def load_policy_file(path: Path) -> Dict[str, Any]:
        if not path.exists():
            raise PolicyValidationError(path, ["policy file is missing"])
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise PolicyValidationError(path, [f"invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"]) from exc
        errors = _validate_policy(data)
        if errors:
            raise PolicyValidationError(path, errors)
        return data


def run(cmd: List[str], *, input_text: str | None = None, env: Dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, input=input_text, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)


def assert_true(condition: bool, message: str, failures: List[str]) -> None:
    if condition:
        print(f"PASS: {message}")
    else:
        print(f"FAIL: {message}")
        failures.append(message)


def load_policy() -> tuple[Dict, List[str]]:
    path = Path(".claude-governance/policy.json")
    try:
        return load_policy_file(path), []
    except PolicyValidationError as exc:
        return {}, [str(exc)]


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


def root_doc_path(policy: Dict) -> str:
    for key in ("root_doc", "root_agents", "root_claude"):
        value = policy.get(key)
        if isinstance(value, dict) and value.get("path"):
            return str(value["path"])
    return "CLAUDE.md"


def explain_result(policy: Dict, failures: List[str], *, with_claude: bool) -> None:
    print("\nDiagnostic explanation:")
    if failures:
        print("- status: fail")
        for failure in failures:
            print(f"- unresolved: {failure}")
    else:
        print("- status: pass")
    print(f"- root_doc: {root_doc_path(policy)}")
    print(f"- config_change_mode: {config_change_mode(policy)}")
    print(f"- ci_provider: {policy.get('ci', {}).get('provider', 'none')}")
    print(f"- behavior_tests_requested: {with_claude}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    parser.add_argument("--with-claude", action="store_true", help="Also run optional AI behavior tests through Claude CLI if available")
    parser.add_argument("--require-claude", action="store_true", help="Fail if Claude CLI behavior tests cannot run")
    parser.add_argument("--explain", action="store_true", help="Print a concise diagnostic explanation of pass/fail state")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    os.chdir(repo)
    failures: List[str] = []
    policy, policy_errors = load_policy()
    assert_true(not policy_errors, "policy schema validates", failures)
    for error in policy_errors:
        print(error, file=sys.stderr)

    required = [
        root_doc_path(policy),
        ".claude/settings.json",
        ".claude-governance/policy.json",
        "scripts/claude_md_lint.py",
        "scripts/claude_hook_guard.py",
    ]
    for rel in required:
        assert_true(Path(rel).exists(), f"required file exists: {rel}", failures)

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
    env["CLAUDE_GOVERNANCE_APPROVED_PATHS"] = ".claude/settings.json"
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

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix="_instructions.md", delete=False) as f:
        f.write(("# Project Overview\n\n保持简洁。高质量。注重性能。\n") * 80)
        bad_path = f.name
    try:
        bad = run([sys.executable, "scripts/claude_md_lint.py", "--policy", ".claude-governance/policy.json", "--root-doc", bad_path, "--fail-under", "75", "--quiet"])
        assert_true(bad.returncode != 0, "mutation test catches bad root instructions", failures)
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
        if args.explain:
            explain_result(policy, failures, with_claude=args.with_claude)
        print("\nGovernance verification failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    if args.explain:
        explain_result(policy, failures, with_claude=args.with_claude)

    print("\nGovernance verification passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
