#!/usr/bin/env python3
"""Static linter for repository instruction governance.

Zero-dependency, repository-local, deterministic. Produces a JSON report and
exits non-zero when hard failures exist or the score falls below threshold.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import shlex
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

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
        threshold = policy.get("score_threshold", 75)
        if not isinstance(threshold, int) or isinstance(threshold, bool) or not 0 <= threshold <= 100:
            errors.append("score_threshold must be an integer between 0 and 100")
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

DEFAULT_POLICY_PATH = ".claude-governance/policy.json"
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "dist", "build", "target", ".idea", ".gradle"}
DEPENDENCY_FILE_NAMES = {
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "requirements.txt",
    "requirements-dev.txt",
    "pyproject.toml",
}


@dataclass(frozen=True)
class RepoIndex:
    files: Tuple[str, ...]
    dirs: Tuple[str, ...]
    dependency_files: Tuple[Path, ...]

    @property
    def candidates(self) -> Tuple[str, ...]:
        return self.dirs + self.files


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Policy file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def display_path(repo: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError:
        return f"<outside-repo>/{path.name}"


def root_doc_policy(policy: Dict[str, Any]) -> Dict[str, Any]:
    for key in ("root_doc", "root_agents", "root_claude"):
        value = policy.get(key)
        if isinstance(value, dict):
            return value
    return {}


def root_doc_path(policy: Dict[str, Any]) -> str:
    return str(root_doc_policy(policy).get("path", "CLAUDE.md"))


def resolve_root_doc_path(repo: Path, policy: Dict[str, Any], explicit_path: str | None = None) -> Path:
    rel = explicit_path or root_doc_path(policy)
    if not explicit_path and rel == "CLAUDE.md" and not (repo / rel).exists() and (repo / "AGENTS.md").exists():
        rel = "AGENTS.md"
    return (repo / rel).resolve() if not Path(rel).is_absolute() else Path(rel)


def root_doc_name(policy: Dict[str, Any]) -> str:
    return Path(root_doc_path(policy)).name


def estimate_tokens(text: str) -> int:
    # Approximation only: good enough for budget regression gates.
    ascii_words = len(re.findall(r"[A-Za-z0-9_]+", text))
    cjk_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    other_chars = max(0, len(text) - cjk_chars)
    return int(ascii_words * 1.2 + cjk_chars * 1.1 + other_chars / 4)


def normalize(path: str) -> str:
    normalized = Path(path).as_posix().replace("\\", "/")
    return normalized[2:] if normalized.startswith("./") else normalized


def line_number_for(text: str, needle: str) -> int:
    idx = text.lower().find(needle.lower())
    return 0 if idx < 0 else text[:idx].count("\n") + 1


def line_number_at(text: str, index: int) -> int:
    return 0 if index < 0 else text[:index].count("\n") + 1


def section_names(spec: Any) -> List[str]:
    if isinstance(spec, str):
        return [spec]
    names = [str(spec.get("name", ""))]
    names.extend([str(x) for x in spec.get("aliases", [])])
    return [x for x in names if x]


def section_severity(spec: Any) -> str:
    if isinstance(spec, str):
        return "error" if spec.lower().startswith("do not") else "warning"
    return str(spec.get("severity", "warning"))


def section_deduction(spec: Any) -> int:
    if isinstance(spec, str):
        return 8 if spec.lower().startswith("do not") else 4
    return int(spec.get("deduction", 4))


def has_section(text: str, names: Iterable[str]) -> bool:
    for name in names:
        escaped = re.escape(name)
        # Accept numbered headings while keeping matches anchored to headings.
        patterns = [
            rf"^\s*#+\s*(?:\d+(?:\.\d+)*\.?\s*)?{escaped}\s*(?:\([^)]*\))?\s*(?:[:：\-].*)?$",
        ]
        if any(re.search(p, text, flags=re.I | re.M) for p in patterns):
            return True
    return False


def phrase_hits(text: str, phrase: str) -> List[re.Match[str]]:
    escaped = re.escape(phrase)
    if re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_ ]*[A-Za-z0-9_]", phrase):
        pattern = rf"(?<![A-Za-z0-9_]){escaped}(?![A-Za-z0-9_])"
    else:
        pattern = escaped
    return list(re.finditer(pattern, text, flags=re.I))


def find_imports(text: str) -> List[Tuple[int, str]]:
    imports: List[Tuple[int, str]] = []
    for i, line in enumerate(text.splitlines(), start=1):
        m = re.match(r"^\s*@([^\s#]+)", line)
        if m:
            imports.append((i, m.group(1).strip()))
    return imports


def count_file_lines(path: Path) -> int:
    if not path.exists() or not path.is_file():
        return 0
    return len(read_text(path).splitlines())


def walk_repo(repo: Path):
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        yield Path(root), dirs, files


def build_repo_index(repo: Path) -> RepoIndex:
    files: List[str] = []
    dirs_found: List[str] = []
    dependency_files: List[Path] = []
    for root, dirs, filenames in walk_repo(repo):
        rel_root = root.relative_to(repo).as_posix()
        if rel_root != ".":
            dirs_found.append(rel_root)
        for dirname in dirs:
            rel = f"{rel_root}/{dirname}" if rel_root != "." else dirname
            dirs_found.append(rel)
        for filename in filenames:
            rel = f"{rel_root}/{filename}" if rel_root != "." else filename
            files.append(rel)
            if filename in DEPENDENCY_FILE_NAMES:
                dependency_files.append(root / filename)
    return RepoIndex(
        files=tuple(sorted(set(files))),
        dirs=tuple(sorted(set(dirs_found))),
        dependency_files=tuple(sorted(dependency_files)),
    )


def dependency_mentions(repo: Path, dep: str, index: RepoIndex | None = None) -> List[str]:
    index = index or build_repo_index(repo)
    hits: List[str] = []
    for path in index.dependency_files:
        if phrase_hits(read_text(path), dep):
            hits.append(display_path(repo, path))
    return sorted(set(hits))


def path_matches(candidate: str, pattern: str) -> bool:
    candidate = normalize(candidate)
    pattern = pattern.replace("\\", "/")
    variants = {candidate, candidate + "/", candidate + "/__file__"}
    return any(fnmatch.fnmatch(v, pattern) for v in variants)


def glob_has_matches(repo: Path, pattern: str, index: RepoIndex | None = None) -> bool:
    index = index or build_repo_index(repo)
    return any(path_matches(candidate, pattern) for candidate in index.candidates)


def configured_local_doc(item: Dict[str, Any]) -> str:
    return str(item.get("local_doc") or item.get("local_agents") or item.get("local_claude") or "")


def find_sensitive_dirs(repo: Path, item: Dict[str, Any], index: RepoIndex | None = None) -> List[str]:
    index = index or build_repo_index(repo)
    pattern = str(item.get("path", ""))
    local = configured_local_doc(item)
    keywords = [str(k).lower() for k in item.get("detect_keywords", [])]
    results: List[str] = []

    if "{dir}" not in local and local:
        base = pattern.split("/**")[0]
        if base and not any(ch in base for ch in "*?["):
            if (repo / base).exists() or glob_has_matches(repo, pattern, index):
                results.append(base.rstrip("/"))
            return sorted(set(results))

    for rel in index.dirs:
        name = Path(rel).name.lower()
        if keywords and not any(k in name or k in rel.lower() for k in keywords):
            continue
        if path_matches(rel, pattern):
            results.append(rel)
    return sorted(set(results))


def local_path_for(item: Dict[str, Any], matched_dir: str, doc_name: str = "CLAUDE.md") -> str:
    local = configured_local_doc(item)
    if doc_name.upper() == "AGENTS.MD" and "local_agents" not in item and local.endswith("CLAUDE.md"):
        local = local.removesuffix("CLAUDE.md") + "AGENTS.md"
    module = Path(matched_dir).name
    return local.replace("{dir}", matched_dir).replace("{module}", module)


def add_finding(findings: List[Dict[str, Any]], *, rule: str, severity: str, message: str, deduction: int = 0, line: int = 0, suggestion: str = "") -> None:
    findings.append({
        "rule": rule,
        "severity": severity,
        "message": message,
        "deduction": deduction,
        "line": line,
        "suggestion": suggestion,
    })


def matcher_covers(matcher: str, tool: str) -> bool:
    matcher = matcher or "*"
    if matcher in {"*", ""}:
        return True
    if re.fullmatch(r"[A-Za-z0-9_|]+", matcher):
        return tool in matcher.split("|")
    try:
        return re.search(matcher, tool) is not None
    except re.error:
        return False


def guard_command_matches(command: str, mode: str) -> bool:
    try:
        argv = shlex.split(str(command), posix=os.name != "nt")
    except ValueError:
        return False
    argv = [arg.strip("\"'").replace("\\", "/") for arg in argv]
    if not argv:
        return False
    exe = Path(argv[0]).name.lower()
    def path_endswith(arg: str, suffix: str) -> bool:
        normalized = arg.strip("\"'").replace("\\", "/")
        return normalized == suffix or normalized.endswith("/" + suffix)

    if exe in {"python", "python.exe", "python3", "python3.exe", "py", "py.exe"}:
        if len(argv) == 3 and path_endswith(argv[1], "scripts/claude_hook_guard.py"):
            return argv[2] == mode
        if len(argv) == 5 and argv[1] == "-m" and argv[2] in {"claude_md_governance.cli", "claude_md_governance"}:
            return argv[3] == "hook" and argv[4] == mode
        return False
    if exe in {"node", "node.exe"}:
        return (
            len(argv) == 4
            and path_endswith(argv[1], ".claude/hooks/run-python-hook.js")
            and path_endswith(argv[2], "scripts/claude_hook_guard.py")
            and argv[3] == mode
        )
    return (
        len(argv) == 3
        and exe in {"codex-md-governance", "codex-md-governance.exe", "claude-md-governance", "claude-md-governance.exe"}
        and argv[1] == "hook"
        and argv[2] == mode
    )


def has_guard_hook(settings: Dict[str, Any], event: str, mode: str, required_tools: List[str]) -> bool:
    covered_tools: set[str] = set()
    for group in settings.get("hooks", {}).get(event, []):
        matcher = str(group.get("matcher", "*"))
        for hook in group.get("hooks", []):
            if str(hook.get("type", "")) != "command":
                continue
            cmd = str(hook.get("command", ""))
            if guard_command_matches(cmd, mode):
                covered_tools.update(tool for tool in required_tools if matcher_covers(matcher, tool))
    return set(required_tools).issubset(covered_tools)


def lint(repo: Path, policy: Dict[str, Any], claude_path: Path) -> Dict[str, Any]:
    findings: List[Dict[str, Any]] = []
    hard_fail = False
    score = 100
    detected_sensitive_dirs: List[Dict[str, str]] = []
    doc_name = root_doc_name(policy)
    repo_index = build_repo_index(repo)

    text = read_text(claude_path)
    if not text:
        add_finding(
            findings,
            rule="ROOT_MISSING",
            severity="error",
            message=f"Root instruction file not found: {display_path(repo, claude_path)}",
            deduction=40,
            suggestion=f"Create a concise root {doc_name} using the starter template.",
        )
        hard_fail = True
        score -= 40
    else:
        lines = len(text.splitlines())
        tokens = estimate_tokens(text)
        root_policy = root_doc_policy(policy)
        warn_lines = int(root_policy.get("warn_lines", 160))
        max_lines = int(root_policy.get("max_lines", 200))
        hard_fail_lines = int(root_policy.get("hard_fail_lines", 220))
        warn_tokens = int(root_policy.get("warn_tokens", 3500))
        hard_fail_tokens = int(root_policy.get("hard_fail_tokens", 5000))

        if lines > hard_fail_lines:
            add_finding(findings, rule="ROOT_TOO_LONG", severity="error", message=f"{doc_name} has {lines} lines; hard limit is {hard_fail_lines}.", deduction=18, suggestion=f"Move long procedures into docs or skills and keep root {doc_name} as a context map.")
            hard_fail = True
            score -= 18
        elif lines > max_lines:
            add_finding(findings, rule="ROOT_TOO_LONG", severity="error", message=f"{doc_name} has {lines} lines; max is {max_lines}.", deduction=12, suggestion="Reduce to configured max_lines.")
            hard_fail = True
            score -= 12
        elif lines > warn_lines:
            add_finding(findings, rule="ROOT_LINE_BUDGET", severity="warning", message=f"{doc_name} has {lines} lines; warning threshold is {warn_lines}.", deduction=5, suggestion="Trim non-global or long-form content.")
            score -= 5

        if tokens > hard_fail_tokens:
            add_finding(findings, rule="ROOT_TOKEN_BUDGET", severity="error", message=f"Estimated token count is {tokens}; hard limit is {hard_fail_tokens}.", deduction=12, suggestion="Reduce always-loaded context.")
            hard_fail = True
            score -= 12
        elif tokens > warn_tokens:
            add_finding(findings, rule="ROOT_TOKEN_BUDGET", severity="warning", message=f"Estimated token count is {tokens}; warning threshold is {warn_tokens}.", deduction=5, suggestion="Trim or move long sections to docs/skills.")
            score -= 5

        for spec in policy.get("required_sections", []):
            names = section_names(spec)
            if not has_section(text, names):
                sev = section_severity(spec)
                deduction = section_deduction(spec)
                add_finding(findings, rule="MISSING_SECTION", severity=sev, message=f"Missing required section: {names[0]}", deduction=deduction, suggestion=f"Add a concise '{names[0]}' heading or an accepted alias.")
                score -= deduction
                if sev == "error":
                    hard_fail = True

        vague_phrases: List[str] = []
        for phrases in policy.get("vague_phrases", {}).values():
            vague_phrases.extend([str(p) for p in phrases])
        vague_hits: List[Tuple[str, int, int]] = []
        for phrase in vague_phrases:
            hits = phrase_hits(text, phrase)
            if hits:
                vague_hits.append((phrase, len(hits), line_number_at(text, hits[0].start())))
        total_vague = sum(c for _, c, _ in vague_hits)
        for phrase, count, line in vague_hits:
            deduction = min(2 * count, 4)
            add_finding(findings, rule="VAGUE_RULE", severity="warning", message=f"Vague phrase '{phrase}' appears {count} time(s).", deduction=deduction, line=line, suggestion="Rewrite as a measurable, testable rule.")
            score -= deduction
        if total_vague > 5:
            hard_fail = True
            add_finding(findings, rule="TOO_MANY_VAGUE_RULES", severity="error", message=f"Found {total_vague} vague-rule hits; hard limit is 5.", deduction=5, suggestion="Replace abstract quality language with numeric or binary rules.")
            score -= 5

        allowed_import_lines = int(policy.get("context_map", {}).get("allowed_import_max_lines", 40))
        for line, import_path in find_imports(text):
            target = (repo / import_path).resolve()
            try:
                target.relative_to(repo.resolve())
            except ValueError:
                add_finding(findings, rule="IMPORT_OUTSIDE_REPO", severity="error", message=f"@import points outside repo: {import_path}", deduction=6, line=line, suggestion="Replace with a safe repository-relative Context Map link.")
                score -= 6
                hard_fail = True
                continue
            imported_lines = count_file_lines(target)
            if imported_lines > allowed_import_lines:
                add_finding(findings, rule="IMPORT_TOO_LONG", severity="error", message=f"@{import_path} imports {imported_lines} lines; limit is {allowed_import_lines}.", deduction=8, line=line, suggestion="Replace @import with a plain path in Context Map or migrate to a skill.")
                score -= 8
                hard_fail = True

        for dep in policy.get("banned_dependencies", []):
            dep_text = str(dep)
            locations = dependency_mentions(repo, dep_text, repo_index)
            if locations:
                add_finding(
                    findings,
                    rule="BANNED_DEP_PRESENT",
                    severity="error",
                    message=f"Policy-banned dependency '{dep_text}' appears in dependency files: {', '.join(locations[:5])}.",
                    deduction=12,
                    suggestion="Remove the dependency or change policy with explicit review.",
                )
                hard_fail = True
                score -= 12
            elif not phrase_hits(text, dep_text):
                add_finding(findings, rule="BANNED_DEP_NOT_DOCUMENTED", severity="warning", message=f"Policy bans '{dep_text}' but {doc_name} does not mention it.", deduction=3, suggestion="Add it under Do NOT introduce with a reason.")
                score -= 3

    for item in policy.get("sensitive_paths", []):
        pattern = item.get("path")
        local = configured_local_doc(item)
        if not pattern or not local:
            continue
        dirs = find_sensitive_dirs(repo, item, repo_index)
        for d in dirs:
            local_rel = local_path_for(item, d, doc_name)
            detected_sensitive_dirs.append({"id": str(item.get("id", "")), "dir": d, "local_doc": local_rel})
            if not (repo / local_rel).exists():
                add_finding(findings, rule="MISSING_LOCAL_DOC", severity="error", message=f"Sensitive path exists but local instruction file is missing: {local_rel}", deduction=10, suggestion=f"Create local {Path(local_rel).name} with safety boundaries and required checks.")
                hard_fail = True
                score -= 10

    settings_path = repo / policy.get("hooks", {}).get("settings_path", ".claude/settings.json")
    if not settings_path.exists():
        add_finding(findings, rule="HOOKS_MISSING", severity="error", message=f"Claude settings not found: {settings_path.relative_to(repo)}", deduction=12, suggestion="Install .claude/settings.json with PreToolUse and PostToolUse hooks.")
        hard_fail = True
        score -= 12
    else:
        try:
            settings = load_json(settings_path)
            if policy.get("hooks", {}).get("require_pretool_guard", True) and not has_guard_hook(settings, "PreToolUse", "pre", ["Edit", "Write", "MultiEdit"]):
                add_finding(findings, rule="PRE_HOOK_MISSING", severity="error", message="PreToolUse guard hook for Edit/Write/MultiEdit is missing.", deduction=8, suggestion="Add python scripts/claude_hook_guard.py pre.")
                hard_fail = True
                score -= 8
            if policy.get("hooks", {}).get("require_posttool_quality_gate", True) and not has_guard_hook(settings, "PostToolUse", "post", ["Edit", "Write", "MultiEdit"]):
                add_finding(findings, rule="POST_HOOK_MISSING", severity="error", message="PostToolUse quality-gate hook for Edit/Write/MultiEdit is missing.", deduction=8, suggestion="Add python scripts/claude_hook_guard.py post.")
                hard_fail = True
                score -= 8
            mode = str(policy.get("hooks", {}).get("config_change_mode", "block"))
            if policy.get("hooks", {}).get("protected_config_review_required", True) and mode != "off":
                if not has_guard_hook(settings, "ConfigChange", "config", ["project_settings", "local_settings", "user_settings", "policy_settings", "skills"]):
                    sev = "warning" if mode == "warn" else "error"
                    add_finding(findings, rule="CONFIG_HOOK_MISSING", severity=sev, message=f"ConfigChange hook is missing while config_change_mode={mode}.", deduction=4, suggestion="Add python scripts/claude_hook_guard.py config or set config_change_mode=off.")
                    score -= 4
                    if sev == "error":
                        hard_fail = True
        except Exception as exc:
            add_finding(findings, rule="SETTINGS_INVALID", severity="error", message=f"Invalid settings JSON: {exc}", deduction=10, suggestion="Fix .claude/settings.json.")
            hard_fail = True
            score -= 10

    score = max(0, min(100, score))
    threshold = int(policy.get("score_threshold", 75))
    status = "pass" if not hard_fail and score >= threshold else "fail"
    return {
        "status": status,
        "score": score,
        "threshold": threshold,
        "hard_fail": hard_fail,
        "findings": findings,
        "summary": {
            "errors": sum(1 for f in findings if f["severity"] == "error"),
            "warnings": sum(1 for f in findings if f["severity"] == "warning"),
            "claude_path": display_path(repo, claude_path),
            "root_doc_path": display_path(repo, claude_path),
            "line_count": len(text.splitlines()) if text else 0,
            "estimated_tokens": estimate_tokens(text) if text else 0,
            "detected_sensitive_dirs": detected_sensitive_dirs,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    parser.add_argument("--policy", default=DEFAULT_POLICY_PATH)
    parser.add_argument("--root-doc", default=None, help="Root instruction file to lint, for example AGENTS.md or CLAUDE.md.")
    parser.add_argument("--claude", default=None, help="Legacy alias for --root-doc.")
    parser.add_argument("--output", default=None)
    parser.add_argument("--fail-under", type=int, default=None)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    policy_path = (repo / args.policy).resolve() if not Path(args.policy).is_absolute() else Path(args.policy)
    try:
        policy = load_policy_file(policy_path)
    except PolicyValidationError as exc:
        print(f"[claude-governance] {exc}", file=sys.stderr)
        return 2
    if args.fail_under is not None:
        policy["score_threshold"] = args.fail_under
    claude_path = resolve_root_doc_path(repo, policy, args.root_doc or args.claude)

    report = lint(repo, policy, claude_path)
    report_json = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        out_path = (repo / args.output).resolve() if not Path(args.output).is_absolute() else Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report_json + "\n", encoding="utf-8")
    if not args.quiet:
        print(report_json)
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
