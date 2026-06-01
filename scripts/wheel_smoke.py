#!/usr/bin/env python3
"""Black-box wheel smoke test for release artifacts."""
from __future__ import annotations

import argparse
import glob
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


REQUIRED_WHEEL_PATHS = [
    "claude_md_governance/data/templates/policies/generic.json",
    "claude_md_governance/data/templates/policies/java-maven.json",
    "claude_md_governance/data/templates/policies/enterprise-java-codeup.json",
    "claude_md_governance/data/templates/common/.claude/skills/claude-md-governance/SKILL.md",
    "claude_md_governance/data/templates/common/scripts/claude_md_lint.py",
    "claude_md_governance/data/templates/common/scripts/claude_hook_guard.py",
    "claude_md_governance/data/templates/common/scripts/verify_claude_governance.py",
    "claude_md_governance/data/templates/github/workflows/claude-md-governance.yml",
]

CACHE_MARKERS = (
    "__pycache__/",
    ".pytest_cache/",
    ".ruff_cache/",
    ".mypy_cache/",
    ".pyc",
    ".pyo",
)


def resolve_wheel(value: str) -> Path:
    matches = [Path(match) for match in glob.glob(value)]
    if not matches:
        path = Path(value)
        if path.exists():
            return path
        raise SystemExit(f"wheel not found: {value}")
    if len(matches) != 1:
        joined = ", ".join(str(match) for match in matches)
        raise SystemExit(f"expected exactly one wheel, found {len(matches)}: {joined}")
    return matches[0]


def run(cmd: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    print("+ " + " ".join(cmd))
    proc = subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if proc.stdout:
        print(proc.stdout)
    if proc.stderr:
        print(proc.stderr, file=sys.stderr)
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)
    return proc


def venv_python(venv: Path) -> Path:
    if sys.platform == "win32":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def assert_wheel_contents(wheel: Path) -> None:
    with zipfile.ZipFile(wheel) as zf:
        names = {name.replace("\\", "/") for name in zf.namelist()}

    missing = [name for name in REQUIRED_WHEEL_PATHS if name not in names]
    if missing:
        raise SystemExit("wheel is missing required files:\n" + "\n".join(f"- {name}" for name in missing))

    cache_files = [
        name
        for name in sorted(names)
        if any(marker in name or name.endswith(marker) for marker in CACHE_MARKERS)
    ]
    if cache_files:
        raise SystemExit("wheel contains cache files:\n" + "\n".join(f"- {name}" for name in cache_files[:50]))


def assert_no_cache_files(root: Path) -> None:
    cache_files = [
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if "__pycache__" in path.parts or path.suffix.lower() in {".pyc", ".pyo"}
    ]
    if cache_files:
        raise SystemExit("installed template copied cache files:\n" + "\n".join(f"- {path}" for path in cache_files[:50]))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", required=True, help="Wheel file or glob, for example dist/*.whl")
    args = parser.parse_args()

    wheel = resolve_wheel(args.wheel).resolve()
    assert_wheel_contents(wheel)

    with tempfile.TemporaryDirectory(prefix="claude-md-wheel-smoke-") as tmp:
        root = Path(tmp)
        venv = root / ".venv"
        repo = root / "consumer-repo"
        repo.mkdir()

        run([sys.executable, "-m", "venv", str(venv)])
        py = venv_python(venv)
        run([str(py), "-m", "pip", "install", str(wheel)])
        run([str(py), "-m", "claude_md_governance", "--help"])
        run(
            [
                str(py),
                "-m",
                "claude_md_governance",
                "init",
                "--repo",
                str(repo),
                "--preset",
                "generic",
                "--ci",
                "github",
                "--yes",
            ]
        )
        run([str(py), "-m", "claude_md_governance", "verify", "--repo", str(repo)])

        required_generated = [
            repo / "CLAUDE.md",
            repo / ".claude-governance" / "policy.json",
            repo / ".claude" / "settings.json",
            repo / ".claude" / "skills" / "claude-md-governance" / "SKILL.md",
            repo / ".github" / "workflows" / "claude-md-governance.yml",
            repo / "scripts" / "claude_md_lint.py",
            repo / "scripts" / "claude_hook_guard.py",
            repo / "scripts" / "verify_claude_governance.py",
        ]
        missing_generated = [path.relative_to(repo).as_posix() for path in required_generated if not path.exists()]
        if missing_generated:
            raise SystemExit("installed repo is missing expected files:\n" + "\n".join(f"- {path}" for path in missing_generated))
        assert_no_cache_files(repo)

    if shutil.which("python") is None:
        print("WARN: python executable not found on PATH; venv smoke used current interpreter only.")
    print("WHEEL_SMOKE_PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
