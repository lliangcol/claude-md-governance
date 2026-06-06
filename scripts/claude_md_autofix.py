#!/usr/bin/env python3
"""Conservative autofix helper for repository instruction governance findings.

This script applies only low-risk fixes: creating missing root sections, creating
local instruction templates, and writing a human-readable repair plan. It never
invents project-specific business rules or banned dependencies.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "dist", "build", "target", ".idea", ".gradle"}


def now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def backup(repo: Path, rel: Path, backup_root: Path) -> None:
    target = repo / rel
    if not target.exists():
        return
    dest = backup_root / rel
    if dest.exists():
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    if target.is_dir():
        shutil.copytree(target, dest)
    else:
        shutil.copy2(target, dest)


def read_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except Exception:
        return {}


def root_doc_policy(policy: Dict[str, Any]) -> Dict[str, Any]:
    for key in ("root_doc", "root_agents", "root_claude"):
        value = policy.get(key)
        if isinstance(value, dict):
            return value
    return {}


def root_doc_rel(policy: Dict[str, Any]) -> Path:
    return Path(str(root_doc_policy(policy).get("path", "CLAUDE.md")))


def root_doc_name(policy: Dict[str, Any]) -> str:
    return root_doc_rel(policy).name


def required_names(policy: Dict[str, Any]) -> List[str]:
    names = []
    for spec in policy.get("required_sections", []):
        if isinstance(spec, str):
            names.append(spec)
        else:
            names.append(str(spec.get("name", "")))
    return [n for n in names if n]


def has_heading(text: str, heading: str) -> bool:
    escaped = re.escape(heading)
    return bool(re.search(rf"^\s*#+\s*(?:\d+(?:\.\d+)*\.?\s*)?{escaped}\s*(?:\([^)]*\))?\s*(?:[:：\-].*)?$", text, flags=re.I | re.M))


def walk_repo(repo: Path):
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        yield Path(root), dirs, files


def normalize(path: str) -> str:
    return (lambda x: x[2:] if x.startswith("./") else x)(Path(path).as_posix())


def path_matches(candidate: str, pattern: str) -> bool:
    candidate = normalize(candidate)
    pattern = pattern.replace("\\", "/")
    variants = {candidate, candidate + "/", candidate + "/__file__"}
    return any(fnmatch.fnmatch(v, pattern) for v in variants)


def glob_has_matches(repo: Path, pattern: str) -> bool:
    for root, dirs, files in walk_repo(repo):
        rel_root = root.relative_to(repo).as_posix()
        if rel_root == ".":
            rel_root = ""
        candidates: List[str] = []
        if rel_root:
            candidates.append(rel_root)
        candidates.extend(f"{rel_root}/{d}" if rel_root else d for d in dirs)
        candidates.extend(f"{rel_root}/{f}" if rel_root else f for f in files)
        if any(path_matches(c, pattern) for c in candidates):
            return True
    return False


def find_sensitive_dirs(repo: Path, item: Dict[str, Any]) -> List[str]:
    pattern = str(item.get("path", ""))
    local = str(item.get("local_claude", ""))
    keywords = [str(k).lower() for k in item.get("detect_keywords", [])]
    results: List[str] = []
    if "{dir}" not in local and local:
        base = pattern.split("/**")[0]
        if base and not any(ch in base for ch in "*?["):
            if (repo / base).exists() or glob_has_matches(repo, pattern):
                results.append(base.rstrip("/"))
            return sorted(set(results))
    for root, dirs, files in walk_repo(repo):
        rel = root.relative_to(repo).as_posix()
        if rel == ".":
            continue
        name = root.name.lower()
        if keywords and not any(k in name or k in rel.lower() for k in keywords):
            continue
        if path_matches(rel, pattern):
            results.append(rel)
    return sorted(set(results))


def local_path_for(item: Dict[str, Any], matched_dir: str, doc_name: str = "CLAUDE.md") -> str:
    module = Path(matched_dir).name
    local = str(item.get("local_doc") or item.get("local_agents") or item.get("local_claude", ""))
    if doc_name.upper() == "AGENTS.MD" and "local_agents" not in item and local.endswith("CLAUDE.md"):
        local = local.removesuffix("CLAUDE.md") + "AGENTS.md"
    return local.replace("{dir}", matched_dir).replace("{module}", module)


def maven_modules(repo: Path) -> List[str]:
    pom = repo / "pom.xml"
    if not pom.exists():
        return []
    text = pom.read_text(encoding="utf-8", errors="replace")
    modules = [normalize(match) for match in re.findall(r"<module>\s*([^<]+?)\s*</module>", text)]
    return sorted({module for module in modules if module}, key=len, reverse=True)


def infer_maven_module(repo: Path, matched_dir: str) -> str:
    normalized = normalize(matched_dir)
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


def rendered_tests(repo: Path, matched_dir: str, item: Dict[str, Any]) -> List[str]:
    module = infer_maven_module(repo, matched_dir)
    directory = normalize(matched_dir)
    return [render_quality_command(str(test), module=module, directory=directory) for test in item.get("required_tests", [])]


def file_line_count(path: Path) -> int:
    if not path.exists() or not path.is_file():
        return 0
    return len(path.read_text(encoding="utf-8", errors="replace").splitlines())


def rewrite_long_imports(repo: Path, text: str, policy: Dict[str, Any]) -> tuple[str, List[str]]:
    limit = int(policy.get("context_map", {}).get("allowed_import_max_lines", 40))
    changed: List[str] = []
    lines = []
    for line in text.splitlines():
        match = re.match(r"^(\s*)@([^\s#]+)(.*)$", line)
        if not match:
            lines.append(line)
            continue
        indent, import_path, suffix = match.groups()
        target = (repo / import_path).resolve()
        try:
            target.relative_to(repo.resolve())
        except ValueError:
            lines.append(line)
            continue
        imported_lines = file_line_count(target)
        if imported_lines > limit:
            lines.append(
                f"{indent}- {import_path} (Context Map reference; TODO: summarize the stable contract here instead of importing {imported_lines} lines.)"
            )
            changed.append(import_path)
        else:
            lines.append(line)
    return "\n".join(lines) + ("\n" if text.endswith("\n") else ""), changed


def desired_hooks(config_mode: str) -> Dict[str, Any]:
    hooks = {
        "PreToolUse": [
            {"matcher": "Edit|Write|MultiEdit", "hooks": [{"type": "command", "command": "python scripts/claude_hook_guard.py pre"}]}
        ],
        "PostToolUse": [
            {"matcher": "Edit|Write|MultiEdit", "hooks": [{"type": "command", "command": "python scripts/claude_hook_guard.py post"}]}
        ],
    }
    if config_mode != "off":
        hooks["ConfigChange"] = [
            {"matcher": "", "hooks": [{"type": "command", "command": "python scripts/claude_hook_guard.py config"}]}
        ]
    return {"hooks": hooks}


def merge_hooks(repo: Path, policy: Dict[str, Any], dry_run: bool, backup_root: Path) -> List[str]:
    settings_rel = Path(policy.get("hooks", {}).get("settings_path", ".claude/settings.json"))
    settings_path = repo / settings_rel
    current = read_json(settings_path)
    current.setdefault("hooks", {})
    changed = False
    template = desired_hooks(str(policy.get("hooks", {}).get("config_change_mode", "block")).lower())
    for event, groups in template["hooks"].items():
        current["hooks"].setdefault(event, [])
        existing = [json.dumps(group, sort_keys=True) for group in current["hooks"][event]]
        for group in groups:
            encoded = json.dumps(group, sort_keys=True)
            if encoded not in existing:
                current["hooks"][event].append(group)
                changed = True
    if not changed:
        return []
    if not dry_run:
        if settings_path.exists():
            backup(repo, settings_rel, backup_root)
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(json.dumps(current, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return [f"merge missing hooks into {settings_rel.as_posix()}"]


def section_body(name: str, preset: str) -> str:
    lower = name.lower()
    if "do not" in lower:
        if preset in {"java-maven", "enterprise-java-codeup"}:
            return "- TODO: Add migrated-away dependencies and obsolete patterns with evidence.\n- Do not introduce new frameworks, new MQ types, new databases, or new DTO conventions without explicit approval.\n- Do not upgrade Spring Boot / Spring Cloud major versions without an explicit migration plan and tests.\n- Do not add Maven dependencies without supply-chain review and confirmation."
        return "- TODO: Add banned dependencies, obsolete patterns, and migrated-away technologies with evidence.\n- Do not introduce new frameworks, state managers, UI libraries, databases, or test runners without explicit approval."
    if "stack" in lower:
        return "TODO: Summarize the current stack from package files, build files, README, and existing architecture docs."
    if "context" in lower or "architecture" in lower:
        return "- Architecture overview: docs/architecture.md\n- API contracts: docs/api.md\n- Deployment runbook: docs/deploy.md\n- AI long-form context: docs/ai-context/"
    if "quality" in lower or "change" in lower or "verification" in lower:
        return "- Lint the root instruction file when it changes.\n- Block protected path edits unless explicitly approved.\n- Run related tests for sensitive modules when CLAUDE_GOVERNANCE_RUN_TESTS=1."
    if "rules" in lower:
        return "- Use explicit types at public boundaries.\n- Prefer existing repository patterns over new abstractions.\n- Do not leave debug logs, commented-out code, or unowned TODOs."
    return "TODO: Fill this section with concise, enforceable project rules."


def local_template(module: str, preset: str, tests: List[str] | None = None) -> str:
    tests = tests or []
    test_lines = "\n".join(f"- `{cmd}`" for cmd in tests) or "- TODO: Add required checks for this module."
    if preset in {"java-maven", "enterprise-java-codeup"}:
        return f"""# {module} Module Rules

This directory is treated as sensitive by repository instruction governance.

## Safety Boundaries

- Do not change payment, order, refund, MQ, transaction, or migration behavior without explicit approval.
- Do not weaken idempotency, rollback behavior, validation, authorization, or logging safety.
- Keep @DS / datasource routing behavior explicit and verified before editing.
- Prefer minimal, well-tested changes over broad rewrites.

## Required Checks

After changes in this directory, run or request:

{test_lines}

## Known Traps

- TODO: Document module-specific state machine invariants.
- TODO: Document datasource names and @DS routing requirements.
- TODO: Document MQ topics/tags/idempotency keys if applicable.
"""
    return f"""# {module} Module Rules

This directory is treated as sensitive by repository instruction governance.

## Safety Boundaries

- Do not change security, billing, payment, migration, or infrastructure behavior without explicit approval.
- Do not weaken validation, authorization, idempotency, logging safety, or rollback behavior.
- Prefer minimal, well-tested changes over broad rewrites.

## Required Checks

After changes in this directory, run or request:

{test_lines}

## Known Traps

- TODO: Document module-specific invariants, edge cases, and prior incidents.
"""


def apply(repo: Path, policy: Dict[str, Any], dry_run: bool) -> List[str]:
    actions: List[str] = []
    backup_root = repo / ".claude-governance" / "backups" / now_stamp()
    claude_rel = root_doc_rel(policy)
    claude_path = repo / claude_rel
    preset = str(policy.get("preset", "generic"))
    doc_name = root_doc_name(policy)

    if not dry_run:
        backup_root.mkdir(parents=True, exist_ok=True)

    if not claude_path.exists():
        text = "# Project Overview\n\nTODO: Describe the product, users, and optimization priority.\n"
        for name in required_names(policy):
            if name.lower() != "project overview":
                text += f"\n# {name}\n\n{section_body(name, preset)}\n"
        actions.append(f"create {claude_rel}")
        if not dry_run:
            claude_path.write_text(text, encoding="utf-8")
    else:
        text = claude_path.read_text(encoding="utf-8", errors="replace")
        additions = []
        missing_names = []
        for name in required_names(policy):
            if not has_heading(text, name):
                additions.append(f"\n# {name}\n\n{section_body(name, preset)}\n")
                missing_names.append(name)
        if additions:
            actions.append(f"append missing sections to {claude_rel}: {', '.join(missing_names)}")
            if not dry_run:
                backup(repo, claude_rel, backup_root)
                text = text.rstrip() + "\n" + "\n".join(additions) + "\n"
                claude_path.write_text(text, encoding="utf-8")

        rewritten, imports = rewrite_long_imports(repo, text, policy)
        if imports:
            actions.append(f"replace long @import lines in {claude_rel}: {', '.join(imports)}")
            if not dry_run:
                backup(repo, claude_rel, backup_root)
                claude_path.write_text(rewritten, encoding="utf-8")

    for sensitive in policy.get("sensitive_paths", []):
        for directory in find_sensitive_dirs(repo, sensitive):
            local = local_path_for(sensitive, directory, doc_name)
            if not local:
                continue
            local_path = repo / local
            if not local_path.exists():
                actions.append(f"create local rules {local}")
                if not dry_run:
                    local_path.parent.mkdir(parents=True, exist_ok=True)
                    local_path.write_text(
                        local_template(Path(directory).name, preset, rendered_tests(repo, directory, sensitive)),
                        encoding="utf-8",
                    )

    actions.extend(merge_hooks(repo, policy, dry_run, backup_root))

    report = repo / ".claude-governance/autofix-report.md"
    if not dry_run:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text("# Instruction Governance Autofix Report\n\n" + "\n".join(f"- {a}" for a in actions) + "\n", encoding="utf-8")
    return actions


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    parser.add_argument("--policy", default=".claude-governance/policy.json")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true", help="Apply repairs. This is the default unless --dry-run is set.")
    args = parser.parse_args()
    repo = Path(args.repo).resolve()
    policy = read_json(repo / args.policy)
    actions = apply(repo, policy, args.dry_run)
    print(json.dumps({"dry_run": args.dry_run, "actions": actions}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
