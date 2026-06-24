#!/usr/bin/env python3
"""Claude Code hook guard for repository AI governance.

Reads Claude Code hook JSON from stdin. Exit code 2 blocks events that support
blocking. The behavior is controlled by .claude-governance/policy.json.
"""
from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List

try:
    from claude_md_governance.policy_schema import PolicyValidationError, load_policy_file
except Exception:  # pragma: no cover - used by repository-local copied scripts.
    class PolicyValidationError(ValueError):  # type: ignore[no-redef]
        def __init__(self, path: Path, errors: List[str]) -> None:
            self.path = path
            self.errors = tuple(errors)
            super().__init__(f"Invalid policy file {path}: {'; '.join(errors)}")

    def _is_non_empty_string(value: Any) -> bool:
        return isinstance(value, str) and bool(value.strip())

    def _validate_string_list(errors: List[str], value: Any, key: str) -> None:
        if value is None:
            return
        if not isinstance(value, list) or any(not _is_non_empty_string(item) for item in value):
            errors.append(f"{key} must be an array of non-empty strings")

    def _validate_policy(policy: Any) -> List[str]:
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

DEFAULT_POLICY_PATH = Path(os.environ.get("CLAUDE_GOVERNANCE_POLICY", ".claude-governance/policy.json"))
DEFAULT_COMMAND_TIMEOUT_SECONDS = 300
DEFAULT_LINT_CACHE_SECONDS = 5


def normalize_path(path: str) -> str:
    raw = str(path).strip().replace("\\", "/")
    if not raw:
        return ""
    candidate = Path(raw)
    repo = Path.cwd().resolve()
    resolved = candidate.resolve(strict=False) if candidate.is_absolute() else (repo / candidate).resolve(strict=False)
    try:
        return resolved.relative_to(repo).as_posix()
    except ValueError:
        return resolved.as_posix().replace("\\", "/")


def load_policy() -> Dict[str, Any]:
    try:
        return load_policy_file(DEFAULT_POLICY_PATH)
    except PolicyValidationError as exc:
        print(f"[claude-governance] {exc}", file=sys.stderr)
        sys.exit(2)


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
        print(f"[claude-governance] rejected non-allowlisted policy command: {command}", file=sys.stderr)
        if os.environ.get("CLAUDE_GOVERNANCE_STRICT_COMMANDS", "1").lower() in {"0", "false", "off", "warn"}:
            return 0
        return 2
    print(f"[claude-governance] running: {command}", file=sys.stderr)
    try:
        timeout = int(os.environ.get("CLAUDE_GOVERNANCE_COMMAND_TIMEOUT_SECONDS", DEFAULT_COMMAND_TIMEOUT_SECONDS))
    except ValueError:
        timeout = DEFAULT_COMMAND_TIMEOUT_SECONDS
    try:
        proc = subprocess.run(command_argv(command), shell=False, timeout=timeout, check=False)
        return int(proc.returncode)
    except subprocess.TimeoutExpired:
        print(f"[claude-governance] policy command timed out after {timeout}s: {command}", file=sys.stderr)
        return 124


def split_env_patterns(value: str) -> List[str]:
    if not value:
        return []
    parts = re.split(r"[;\n,]+", value)
    return [part.strip() for part in parts if part.strip()]


def protected_edit_allowed(path: str) -> bool:
    approved_patterns = split_env_patterns(os.environ.get("CLAUDE_GOVERNANCE_APPROVED_PATHS", ""))
    return bool(approved_patterns and matches(path, approved_patterns))


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


def _file_digest(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return f"missing:{path.as_posix()}"
    digest = hashlib.sha256()
    digest.update(path.as_posix().encode("utf-8", errors="replace"))
    digest.update(path.read_bytes())
    return digest.hexdigest()


def lint_cache_key(policy: Dict[str, Any]) -> str:
    root_doc = "CLAUDE.md"
    for key in ("root_doc", "root_agents", "root_claude"):
        value = policy.get(key)
        if isinstance(value, dict) and value.get("path"):
            root_doc = str(value["path"])
            break
    settings_path = str(policy.get("hooks", {}).get("settings_path", ".claude/settings.json"))
    paths = [
        DEFAULT_POLICY_PATH,
        Path(settings_path),
        Path(root_doc),
        Path("scripts/claude_hook_guard.py"),
        Path("scripts/claude_md_lint.py"),
    ]
    digest = hashlib.sha256()
    for path in paths:
        digest.update(_file_digest(path).encode("utf-8", errors="replace"))
    return digest.hexdigest()


def lint_cache_file() -> Path:
    repo_hash = hashlib.sha256(str(Path.cwd().resolve()).encode("utf-8", errors="replace")).hexdigest()[:16]
    return Path(tempfile.gettempdir()) / "claude-md-governance" / f"hook-lint-{repo_hash}.json"


def lint_cache_seconds() -> int:
    try:
        return max(0, int(os.environ.get("CLAUDE_GOVERNANCE_LINT_CACHE_SECONDS", DEFAULT_LINT_CACHE_SECONDS)))
    except ValueError:
        return DEFAULT_LINT_CACHE_SECONDS


def lint_recently_passed(policy: Dict[str, Any]) -> bool:
    ttl = lint_cache_seconds()
    if ttl <= 0:
        return False
    path = lint_cache_file()
    if not path.exists():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return False
    return (
        payload.get("key") == lint_cache_key(policy)
        and payload.get("status") == "pass"
        and time.time() - float(payload.get("timestamp", 0)) <= ttl
    )


def remember_lint_pass(policy: Dict[str, Any]) -> None:
    ttl = lint_cache_seconds()
    if ttl <= 0:
        return
    path = lint_cache_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"key": lint_cache_key(policy), "status": "pass", "timestamp": time.time()}
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def governance_path_changed(path: str) -> bool:
    normalized = normalize_path(path)
    lower = normalized.lower()
    return (
        normalized.endswith("CLAUDE.md")
        or normalized.endswith("AGENTS.md")
        or normalized == ".claude/settings.json"
        or lower == ".codex/hooks.json"
        or lower.startswith(".claude/")
        or lower.startswith(".codex/")
        or lower.startswith(".agents/")
        or lower.startswith(".claude-governance/")
        or lower.startswith(".codex-governance/")
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
        if matches(path, protected_patterns(policy)) and not protected_edit_allowed(path):
            block(
                "Blocked protected edit: " + path + "\n"
                "Reason: this path is covered by repository instruction governance policy. "
                "Set CLAUDE_GOVERNANCE_APPROVED_PATHS to the approved path or glob only after explicit human approval."
            )
        return 0

    if mode == "post":
        if os.environ.get("CLAUDE_GOVERNANCE_LINT_SKIP") == "1":
            return warn("[claude-governance] lint skipped because CLAUDE_GOVERNANCE_LINT_SKIP=1")

        if governance_path_changed(path):
            if lint_recently_passed(policy):
                warn("[claude-governance] lint skipped because an identical governance state passed recently.")
            else:
                code = run_command(lint_command())
                if code != 0:
                    block("Instruction governance lint failed. See .claude-governance/score.json and fix before continuing.")
                remember_lint_pass(policy)

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
