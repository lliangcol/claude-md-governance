#!/usr/bin/env python3
"""Claude Code hook guard for repository AI governance.

Reads Claude Code hook JSON from stdin. Exit code 2 blocks events that support
blocking. The behavior is controlled by .claude-governance/policy.json.
"""
from __future__ import annotations

import fnmatch
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List

DEFAULT_POLICY_PATH = Path(os.environ.get("CLAUDE_GOVERNANCE_POLICY", ".claude-governance/policy.json"))


def normalize_path(path: str) -> str:
    raw = str(path).strip()
    if not raw:
        return ""
    candidate = Path(raw)
    repo = Path.cwd().resolve()
    resolved = candidate.resolve(strict=False) if candidate.is_absolute() else (repo / candidate).resolve(strict=False)
    try:
        return resolved.relative_to(repo).as_posix()
    except ValueError:
        return resolved.as_posix().replace("\\", "/")


def read_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def load_policy() -> Dict[str, Any]:
    return read_json(DEFAULT_POLICY_PATH)


def read_event() -> Dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {}


def event_path(event: Dict[str, Any]) -> str:
    tool_input = event.get("tool_input") or event.get("input") or {}
    for key in ("file_path", "path", "notebook_path", "filePath"):
        value = tool_input.get(key)
        if isinstance(value, str) and value:
            return normalize_path(value)
    # Some editor tools include the target in a nested payload.
    for key in ("edits", "changes"):
        value = tool_input.get(key)
        if isinstance(value, list) and value:
            first = value[0] if isinstance(value[0], dict) else {}
            for nested_key in ("file_path", "path", "filePath"):
                nested = first.get(nested_key)
                if isinstance(nested, str) and nested:
                    return normalize_path(nested)
    return ""


def matches(path: str, patterns: Iterable[str]) -> bool:
    normalized = normalize_path(path)
    variants = {normalized, normalized + "/", normalized + "/__file__"}
    for pattern in patterns:
        if not pattern:
            continue
        p = str(pattern).replace("\\", "/")
        if any(fnmatch.fnmatch(v, p) for v in variants):
            return True
    return False


def block(message: str) -> None:
    print(message, file=sys.stderr)
    sys.exit(2)


def warn(message: str) -> int:
    print(message, file=sys.stderr)
    return 0


ALLOWED_COMMAND_PREFIXES = (
    "python scripts/",
    "python3 scripts/",
    "py scripts/",
    "mvn ",
    "./mvnw ",
    "mvnw ",
    "npm test",
    "npm run ",
    "pnpm test",
    "pnpm run ",
    "yarn test",
    "yarn run ",
)


def command_argv(command: str) -> List[str]:
    try:
        return shlex.split(command, posix=os.name != "nt")
    except ValueError:
        return []


def _exe_name(token: str) -> str:
    return Path(token.strip("\"'")).name.lower()


def command_allowed(command: str) -> bool:
    argv = command_argv(command)
    if not argv:
        return False
    exe = _exe_name(argv[0])
    if exe in {"python", "python.exe", "python3", "python3.exe", "py", "py.exe"}:
        if len(argv) < 2:
            return False
        script = argv[1].strip("\"'").replace("\\", "/")
        return script.startswith("scripts/") and script.endswith(".py")
    if exe in {"mvn", "mvn.cmd", "mvnw", "mvnw.cmd"} or argv[0].replace("\\", "/") == "./mvnw":
        return True
    if exe in {"npm", "npm.cmd", "pnpm", "pnpm.cmd", "yarn", "yarn.cmd"}:
        return len(argv) >= 2 and argv[1] in {"test", "run"}
    return False


def run_command(command: str) -> int:
    if not command_allowed(command):
        print(f"[claude-governance] skipped non-allowlisted policy command: {command}", file=sys.stderr)
        return 0
    print(f"[claude-governance] running: {command}", file=sys.stderr)
    return subprocess.call(command_argv(command), shell=False)


def protected_patterns(policy: Dict[str, Any]) -> List[str]:
    patterns = list(policy.get("protected_paths", []))
    for item in policy.get("sensitive_paths", []):
        if item.get("protected"):
            patterns.append(str(item.get("path", "")))
    return [p for p in patterns if p]


def related_quality_commands(policy: Dict[str, Any], path: str) -> List[str]:
    commands: List[str] = []
    normalized = normalize_path(path)
    module = infer_maven_module(normalized)
    directory = str(Path(normalized).parent).replace("\\", "/")
    for item in policy.get("sensitive_paths", []):
        pattern = str(item.get("path", ""))
        if pattern and matches(normalized, [pattern]):
            for raw in item.get("required_tests", []):
                commands.append(render_quality_command(str(raw), module=module, directory=directory))
    return commands


def maven_modules(repo: Path) -> List[str]:
    pom = repo / "pom.xml"
    if not pom.exists():
        return []
    text = pom.read_text(encoding="utf-8", errors="replace")
    modules = [normalize_path(match) for match in re.findall(r"<module>\s*([^<]+?)\s*</module>", text)]
    return sorted({module for module in modules if module}, key=len, reverse=True)


def infer_maven_module(path: str, repo: Path | None = None) -> str:
    repo = repo or Path.cwd()
    normalized = normalize_path(path)
    for module in maven_modules(repo):
        if normalized == module or normalized.startswith(module + "/"):
            return module
    first = Path(normalized).parts[0] if Path(normalized).parts else ""
    if first and first not in {"src", "test", "tests"} and (repo / first / "pom.xml").exists():
        return first
    return ""


def render_quality_command(raw: str, *, module: str, directory: str) -> str:
    command = str(raw)
    if "{module}" in command:
        if module:
            command = command.replace("{module}", module)
        else:
            command = command.replace(" -pl {module} -am", "")
            command = command.replace(" -pl {module}", "")
            command = command.replace("{module}", ".")
    command = command.replace("{dir}", directory)
    return " ".join(command.split())


def config_mode(policy: Dict[str, Any]) -> str:
    mode = str(policy.get("hooks", {}).get("config_change_mode", "block")).lower()
    return mode if mode in {"block", "warn", "off"} else "block"


def lint_command() -> str:
    py = os.environ.get("PYTHON", "python")
    return f"{py} scripts/claude_md_lint.py --policy .claude-governance/policy.json --output .claude-governance/score.json --quiet"


def governance_path_changed(path: str) -> bool:
    normalized = normalize_path(path)
    return (
        normalized.endswith("CLAUDE.md")
        or normalized == ".claude/settings.json"
        or normalized.startswith(".claude/")
        or normalized.startswith(".claude-governance/")
        or normalized in {
            "scripts/claude_hook_guard.py",
            "scripts/claude_md_lint.py",
            "scripts/claude_md_autofix.py",
            "scripts/verify_claude_governance.py",
        }
        or normalized.startswith("src/claude_md_governance/")
    )


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "pre"
    policy = load_policy()
    event = read_event()
    path = event_path(event)

    if mode == "config":
        cfg_mode = config_mode(policy)
        msg = "Claude Code configuration changed during session; review .claude/settings.json and governance policy before continuing."
        if cfg_mode == "block":
            block(msg)
        if cfg_mode == "warn":
            return warn("[claude-governance] WARNING: " + msg)
        return 0

    if not path:
        return 0

    if mode == "pre":
        if matches(path, protected_patterns(policy)) and os.environ.get("ALLOW_PROTECTED_EDIT") != "1":
            block(
                "Blocked protected edit: " + path + "\n"
                "Reason: this path is covered by CLAUDE.md governance policy. "
                "Set ALLOW_PROTECTED_EDIT=1 only after explicit human approval or in CI-controlled setup."
            )
        return 0

    if mode == "post":
        if os.environ.get("CLAUDE_GOVERNANCE_LINT_SKIP") == "1":
            return warn("[claude-governance] lint skipped because CLAUDE_GOVERNANCE_LINT_SKIP=1")

        if governance_path_changed(path):
            code = run_command(lint_command())
            if code != 0:
                block("CLAUDE.md governance lint failed. See .claude-governance/score.json and fix before continuing.")

        commands = related_quality_commands(policy, path)
        if commands and os.environ.get("CLAUDE_GOVERNANCE_RUN_TESTS") == "1":
            for command in commands:
                code = run_command(command)
                if code != 0:
                    block(f"Quality gate failed for {path}: {command}")
        elif commands:
            warn("[claude-governance] related tests are configured but skipped. Set CLAUDE_GOVERNANCE_RUN_TESTS=1 to enforce: " + "; ".join(commands))
        return 0

    return warn(f"[claude-governance] unknown mode: {mode}")


if __name__ == "__main__":
    sys.exit(main())
