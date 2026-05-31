#!/usr/bin/env python3
"""Install CLAUDE.md governance starter kit into a repository.

Usage:
  python install.py --repo /path/to/repo --yes
  python install.py --repo /path/to/repo --yes --preset enterprise-java-codeup --ci codeup --config-change-mode warn

The installer is conservative:
- It never deletes existing content.
- Existing files are backed up before being overwritten or merged.
- Existing CLAUDE.md gets missing governance sections appended, not replaced.
- CI provider and ConfigChange behavior are policy-driven, so Aliyun Codeup or
  Java/Maven repositories do not accidentally receive GitHub-only assumptions.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

KIT_ROOT = Path(__file__).resolve().parent
TEMPLATE_ROOT = KIT_ROOT / "data" / "templates"
COMMON_ROOT = TEMPLATE_ROOT / "common"
POLICY_ROOT = TEMPLATE_ROOT / "policies"
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "dist", "build", "target", ".idea", ".gradle"}
TEMPLATE_SKIP_DIRS = {"__pycache__"}
TEMPLATE_SKIP_SUFFIXES = {".pyc", ".pyo"}


def now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def backup(repo: Path, rel: Path, backup_root: Path) -> None:
    target = repo / rel
    if not target.exists():
        return
    dest = backup_root / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    if target.is_dir():
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(target, dest)
    else:
        shutil.copy2(target, dest)


def copy_file(src: Path, dst: Path, backup_root: Path, repo: Path, force: bool = False) -> None:
    rel = dst.relative_to(repo)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and not force:
        return
    if dst.exists():
        backup(repo, rel, backup_root)
    shutil.copy2(src, dst)


def should_copy_template_file(path: Path) -> bool:
    return not (
        any(part in TEMPLATE_SKIP_DIRS for part in path.parts)
        or path.suffix.lower() in TEMPLATE_SKIP_SUFFIXES
    )


def copy_tree_files(src_root: Path, repo: Path, backup_root: Path, force: bool = False) -> None:
    for src in src_root.rglob("*"):
        if src.is_dir() or not should_copy_template_file(src):
            continue
        rel = src.relative_to(src_root)
        copy_file(src, repo / rel, backup_root, repo, force=force)


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def git_remote(repo: Path) -> str:
    try:
        proc = subprocess.run(["git", "remote", "-v"], cwd=repo, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        return proc.stdout.lower()
    except Exception:
        return ""


def detect_preset(repo: Path, requested: str) -> str:
    if requested != "auto":
        return requested
    if (repo / "pom.xml").exists():
        # Keep enterprise Codeup behavior explicit; repo names should not imply a team preset.
        return "java-maven"
    if (repo / "package.json").exists():
        return "generic"
    return "generic"


def detect_ci(repo: Path, requested: str, preset: str) -> str:
    if requested != "auto":
        return requested
    remote = git_remote(repo)
    if "codeup.aliyun" in remote or preset == "enterprise-java-codeup":
        return "codeup"
    if "github.com" in remote or (repo / ".github").exists():
        return "github"
    return "none"


def detect_config_mode(requested: str, preset: str) -> str:
    if requested != "auto":
        return requested
    return "warn" if preset in {"java-maven", "enterprise-java-codeup"} else "block"


def load_policy_template(preset: str) -> Dict[str, Any]:
    path = POLICY_ROOT / f"{preset}.json"
    if not path.exists():
        path = POLICY_ROOT / "generic.json"
    return read_json(path)


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


def merge_settings(repo: Path, backup_root: Path, config_mode: str) -> None:
    rel = Path(".claude/settings.json")
    dst = repo / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    template = desired_hooks(config_mode)
    if not dst.exists():
        write_json(dst, template)
        return
    backup(repo, rel, backup_root)
    try:
        current = read_json(dst)
    except Exception:
        current = {}
    current.setdefault("hooks", {})
    for event, items in template.get("hooks", {}).items():
        current["hooks"].setdefault(event, [])
        for item in items:
            item_json = json.dumps(item, sort_keys=True)
            existing = [json.dumps(x, sort_keys=True) for x in current["hooks"].get(event, [])]
            if item_json not in existing:
                current["hooks"][event].append(item)
    write_json(dst, current)


def detect_stack(repo: Path, preset: str) -> List[str]:
    stack: List[str] = []
    if (repo / "pom.xml").exists():
        text = (repo / "pom.xml").read_text(encoding="utf-8", errors="replace")
        stack.append("Java / Maven")
        if re.search(r"<java.version>\s*17\s*</java.version>", text) or "<maven.compiler.release>17" in text:
            stack.append("Java 17")
        if "spring-boot" in text.lower():
            stack.append("Spring Boot")
        if "spring-cloud" in text.lower():
            stack.append("Spring Cloud")
        if "rocketmq" in text.lower():
            stack.append("RocketMQ")
        if "kafka" in text.lower():
            stack.append("Kafka")
    package_json = repo / "package.json"
    if package_json.exists():
        try:
            pkg = json.loads(package_json.read_text(encoding="utf-8"))
            deps: Dict[str, str] = {}
            for key in ("dependencies", "devDependencies"):
                deps.update(pkg.get(key, {}))
            for dep, label in [("next", "Next.js"), ("react", "React"), ("typescript", "TypeScript"), ("tailwindcss", "Tailwind CSS"), ("vitest", "Vitest"), ("jest", "Jest"), ("@playwright/test", "Playwright")]:
                if dep in deps:
                    stack.append(label)
            scripts = pkg.get("scripts", {})
            if scripts:
                stack.append("package scripts: " + ", ".join(sorted(scripts.keys())[:8]))
        except Exception:
            stack.append("Node.js project")
    if (repo / "pyproject.toml").exists():
        stack.append("Python / pyproject.toml")
    if (repo / "go.mod").exists():
        stack.append("Go")
    if (repo / "Cargo.toml").exists():
        stack.append("Rust")
    if (repo / "Dockerfile").exists():
        stack.append("Docker")
    return sorted(set(stack)) or ["TODO: detect and document project stack"]


def section_names(spec: Any) -> List[str]:
    if isinstance(spec, str):
        return [spec]
    names = [str(spec.get("name", ""))]
    names.extend([str(x) for x in spec.get("aliases", [])])
    return [x for x in names if x]


def has_heading(text: str, names: Iterable[str]) -> bool:
    for name in names:
        escaped = re.escape(name)
        patterns = [
            rf"^\s*#+\s*(?:\d+(?:\.\d+)*\.?\s*)?{escaped}\b",
            rf"^\s*#+\s*(?:\d+(?:\.\d+)*\.?\s*)?.*{escaped}.*$",
        ]
        if any(re.search(pattern, text, flags=re.I | re.M) for pattern in patterns):
            return True
    return False


def section_body(name: str, stack: List[str], preset: str) -> str:
    lower = name.lower()
    if "overview" in lower or "priority" in lower:
        return "TODO: Describe the product/service in 2-3 sentences. Include primary users and the core job-to-be-done.\nOptimization priority: correctness > security > maintainability > speed."
    if "stack" in lower:
        return "\n".join(f"- {item}" for item in stack)
    if "do not" in lower:
        if preset in {"java-maven", "enterprise-java-codeup"}:
            return "- TODO: Add migrated-away dependencies and obsolete patterns with evidence.\n- Do not introduce new frameworks, new MQ types, new databases, or new DTO conventions without explicit approval.\n- Do not upgrade Spring Boot / Spring Cloud major versions without an explicit migration plan and tests.\n- Do not add Maven dependencies without supply-chain review and confirmation."
        return "- TODO: Add banned dependencies, obsolete patterns, and migrated-away technologies with evidence.\n- Do not introduce new frameworks, state managers, UI libraries, databases, or test runners without explicit approval."
    if "architecture" in lower or "context" in lower:
        return "- Architecture overview: docs/architecture.md\n- API contracts: docs/api.md\n- Deployment runbook: docs/deploy.md\n- AI long-form context: docs/ai-context/\n- Archive/deprecated docs: docs/archive/ — do not read unless explicitly requested."
    if "rules" in lower:
        if preset in {"java-maven", "enterprise-java-codeup"}:
            return "- Controllers must not call persistence mappers directly.\n- Keep transaction boundaries explicit and avoid external network calls inside transactions.\n- Do not leave debug logs, commented-out code, or unowned TODOs.\n- Prefer existing repository patterns over introducing new abstractions."
        return "- Use explicit types at public boundaries.\n- Keep functions focused; split large functions when one function mixes validation, I/O, and transformation.\n- Do not leave commented-out code, debug logs, or unowned TODOs.\n- Prefer existing repository patterns over introducing new abstractions."
    if "change" in lower or "quality" in lower or "validation" in lower:
        return "- Lint CLAUDE.md when it changes.\n- Block protected path edits unless explicitly approved.\n- Run related tests for sensitive modules when CLAUDE_GOVERNANCE_RUN_TESTS=1.\n- Keep root CLAUDE.md under the configured line and token budget."
    if "working" in lower or "workflow" in lower:
        return "- For complex changes, propose a short plan before editing.\n- For trivial fixes, edit directly and summarize the diff.\n- If uncertain, state assumptions and choose the conservative path."
    return "TODO: Fill this section with concise, enforceable project rules."


def root_claude_skeleton(policy: Dict[str, Any], stack: List[str], preset: str) -> str:
    chunks = []
    for spec in policy.get("required_sections", []):
        name = section_names(spec)[0]
        chunks.append(f"# {name}\n\n{section_body(name, stack, preset)}\n")
    if not any("Sensitive" in c for c in chunks):
        chunks.append("# Sensitive Areas\n\n- Read local CLAUDE.md files before editing sensitive modules.\n- Ask before modifying public APIs, auth, billing/payment, database schema, migrations, or infrastructure.\n")
    return "\n".join(chunks)


def ensure_root_claude(repo: Path, policy: Dict[str, Any], backup_root: Path, preset: str) -> None:
    rel = Path(policy.get("root_claude", {}).get("path", "CLAUDE.md"))
    path = repo / rel
    stack = detect_stack(repo, preset)
    if not path.exists():
        path.write_text(root_claude_skeleton(policy, stack, preset), encoding="utf-8")
        return
    text = path.read_text(encoding="utf-8", errors="replace")
    additions: List[str] = []
    for spec in policy.get("required_sections", []):
        names = section_names(spec)
        if not has_heading(text, names):
            name = names[0]
            additions.append(f"\n# {name}\n\n{section_body(name, stack, preset)}\n")
    if additions:
        backup(repo, rel, backup_root)
        path.write_text(text.rstrip() + "\n" + "\n".join(additions) + "\n", encoding="utf-8")


def walk_repo(repo: Path):
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        yield Path(root), dirs, files


def path_matches(candidate: str, pattern: str) -> bool:
    candidate = Path(candidate).as_posix().replace("\\", "/")
    if candidate.startswith("./"):
        candidate = candidate[2:]
    variants = {candidate, candidate + "/", candidate + "/__file__"}
    return any(fnmatch.fnmatch(v, pattern.replace("\\", "/")) for v in variants)


def find_sensitive_dirs(repo: Path, item: Dict[str, Any]) -> List[str]:
    pattern = str(item.get("path", ""))
    local = str(item.get("local_claude", ""))
    keywords = [str(k).lower() for k in item.get("detect_keywords", [])]
    results: List[str] = []
    if "{dir}" not in local and local:
        base = pattern.split("/**")[0]
        if base and not any(ch in base for ch in "*?["):
            if (repo / base).exists():
                return [base.rstrip("/")]
        return []
    for root, dirs, files in walk_repo(repo):
        rel = root.relative_to(repo).as_posix()
        if rel == ".":
            continue
        name = root.name.lower()
        if keywords and not any(k in name or k in rel.lower() for k in keywords):
            continue
        if path_matches(rel, pattern) or (keywords and any(k in name for k in keywords)):
            results.append(rel)
    return sorted(set(results))


def local_path_for(item: Dict[str, Any], matched_dir: str) -> str:
    module = Path(matched_dir).name
    return str(item.get("local_claude", "")).replace("{dir}", matched_dir).replace("{module}", module)


def maven_modules(repo: Path) -> List[str]:
    pom = repo / "pom.xml"
    if not pom.exists():
        return []
    text = pom.read_text(encoding="utf-8", errors="replace")
    modules = [normalize_rel_path(match) for match in re.findall(r"<module>\s*([^<]+?)\s*</module>", text)]
    return sorted({module for module in modules if module}, key=len, reverse=True)


def normalize_rel_path(path: str) -> str:
    normalized = Path(str(path).strip()).as_posix().replace("\\", "/")
    return normalized[2:] if normalized.startswith("./") else normalized


def infer_maven_module(repo: Path, matched_dir: str) -> str:
    normalized = normalize_rel_path(matched_dir)
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


def rendered_tests(repo: Path, matched_dir: str, tests: Iterable[str]) -> List[str]:
    module = infer_maven_module(repo, matched_dir)
    directory = normalize_rel_path(matched_dir)
    return [render_quality_command(str(test), module=module, directory=directory) for test in tests]


def local_claude_template(module: str, tests: Iterable[str], preset: str) -> str:
    tests = [str(t) for t in tests]
    test_lines = "\n".join(f"- `{cmd}`" for cmd in tests) or "- TODO: Add required checks for this module."
    if preset in {"java-maven", "enterprise-java-codeup"}:
        return f"""# {module} Module Rules

This directory is treated as sensitive by CLAUDE.md governance.

## Safety Boundaries

- Do not change payment, order, refund, MQ, transaction, or migration behavior without explicit approval.
- Do not weaken idempotency, rollback behavior, validation, authorization, or logging safety.
- Keep @DS / datasource routing behavior explicit and verified before editing.
- Any API response shape or state-transition change requires explicit confirmation.

## Required Checks

After changes in this directory, run or request:

{test_lines}

## Known Traps

- TODO: Document module-specific state machine invariants.
- TODO: Document datasource names and @DS routing requirements.
- TODO: Document MQ topics/tags/idempotency keys if applicable.
"""
    return f"""# {module} Module Rules

This directory is treated as sensitive by CLAUDE.md governance.

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


def ensure_local_claudes(repo: Path, policy: Dict[str, Any], preset: str) -> None:
    for item in policy.get("sensitive_paths", []):
        for d in find_sensitive_dirs(repo, item):
            local = local_path_for(item, d)
            if not local:
                continue
            local_path = repo / local
            if not local_path.exists():
                local_path.parent.mkdir(parents=True, exist_ok=True)
                module = Path(d).name
                local_path.write_text(local_claude_template(module, rendered_tests(repo, d, item.get("required_tests", [])), preset), encoding="utf-8")


def install_policy(repo: Path, policy: Dict[str, Any], backup_root: Path, force: bool, ci: str, config_mode: str) -> None:
    policy["ci"] = {"provider": ci}
    policy.setdefault("hooks", {})["config_change_mode"] = config_mode
    dst = repo / ".claude-governance/policy.json"
    if dst.exists() and not force:
        # Merge non-destructively: keep existing user policy, but update versioned safe defaults if missing.
        backup(repo, Path(".claude-governance/policy.json"), backup_root)
        existing = read_json(dst)
        for key, value in policy.items():
            existing.setdefault(key, value)
        existing.setdefault("hooks", {}).setdefault("config_change_mode", config_mode)
        existing.setdefault("ci", {}).setdefault("provider", ci)
        write_json(dst, existing)
    else:
        if dst.exists():
            backup(repo, Path(".claude-governance/policy.json"), backup_root)
        write_json(dst, policy)


def copy_ci(repo: Path, backup_root: Path, force: bool, ci: str) -> None:
    if ci == "github":
        workflow_src = TEMPLATE_ROOT / "github" / "workflows" / "claude-md-governance.yml"
        if workflow_src.exists():
            copy_file(
                workflow_src,
                repo / ".github" / "workflows" / "claude-md-governance.yml",
                backup_root,
                repo,
                force=force,
            )
        else:
            copy_tree_files(TEMPLATE_ROOT / "github", repo, backup_root, force=force)
    elif ci == "codeup":
        copy_tree_files(TEMPLATE_ROOT / "codeup", repo, backup_root, force=force)


def chmod_scripts(repo: Path) -> None:
    scripts_dir = repo / "scripts"
    if not scripts_dir.exists():
        return
    for script in scripts_dir.glob("*.py"):
        script.chmod(script.stat().st_mode | 0o111)


def run_verify(repo: Path) -> int:
    verify = repo / "scripts/verify_claude_governance.py"
    if not verify.exists():
        return 1
    return subprocess.call([sys.executable, str(verify)], cwd=repo)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".", help="Target repository root")
    parser.add_argument("--yes", action="store_true", help="Non-interactive mode")
    parser.add_argument("--force", action="store_true", help="Overwrite starter-kit managed files after backup")
    parser.add_argument("--skip-verify", action="store_true")
    parser.add_argument("--preset", default="auto", choices=["auto", "generic", "java-maven", "enterprise-java-codeup"])
    parser.add_argument("--ci", default="auto", choices=["auto", "github", "codeup", "none"])
    parser.add_argument("--config-change-mode", default="auto", choices=["auto", "block", "warn", "off"])
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    if not repo.exists():
        print(f"Repo not found: {repo}", file=sys.stderr)
        return 1
    if not args.yes:
        print("Use --yes for non-interactive installation.", file=sys.stderr)
        return 2

    preset = detect_preset(repo, args.preset)
    ci = detect_ci(repo, args.ci, preset)
    config_mode = detect_config_mode(args.config_change_mode, preset)
    policy = load_policy_template(preset)

    backup_root = repo / ".claude-governance" / "backups" / now_stamp()
    backup_root.mkdir(parents=True, exist_ok=True)

    copy_tree_files(COMMON_ROOT, repo, backup_root, force=args.force)
    copy_ci(repo, backup_root, force=args.force, ci=ci)
    install_policy(repo, policy, backup_root, force=args.force, ci=ci, config_mode=config_mode)
    merge_settings(repo, backup_root, config_mode=config_mode)
    # Re-load policy in case it merged with an existing file.
    policy = read_json(repo / ".claude-governance/policy.json")
    ensure_root_claude(repo, policy, backup_root, preset)
    ensure_local_claudes(repo, policy, preset)
    chmod_scripts(repo)

    print(f"Installed CLAUDE.md governance into {repo}")
    print(f"Preset: {preset}; CI provider: {ci}; ConfigChange mode: {config_mode}")
    print(f"Backups, if any, are under {backup_root}")

    if not args.skip_verify:
        return run_verify(repo)
    return 0


if __name__ == "__main__":
    sys.exit(main())
