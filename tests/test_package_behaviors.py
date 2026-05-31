from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from claude_md_governance import lint
from claude_md_governance.templates import policy_path, template_root


def run_cli(*args: str, cwd: Path | None = None, input_text: str | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "claude_md_governance.cli", *args],
        cwd=cwd,
        input=input_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        check=False,
    )


def make_repo(tmp_path: Path, name: str) -> Path:
    repo = tmp_path / name
    repo.mkdir()
    return repo


def assert_no_python_cache_files(root: Path) -> None:
    cache_files = [
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if "__pycache__" in path.parts or path.suffix.lower() in {".pyc", ".pyo"}
    ]
    assert cache_files == []


def test_template_resources_exist() -> None:
    root = template_root()
    assert (root / "policies" / "generic.json").exists()
    assert (root / "policies" / "java-maven.json").exists()
    assert (root / "policies" / "enterprise-java-codeup.json").exists()
    assert (root / "common" / "scripts" / "claude_md_lint.py").exists()
    assert (root / "common" / ".claude" / "skills" / "claude-md-governance" / "SKILL.md").exists()
    assert (root / "github" / "workflows" / "claude-md-governance.yml").exists()
    assert not (root / "github" / ".github" / "workflows" / "claude-md-governance.yml").exists()
    assert policy_path("missing").name == "generic.json"


def test_init_copies_skill_and_filters_template_cache(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "skill-template")
    proc = run_cli("init", "--repo", str(repo), "--preset", "generic", "--ci", "none", "--yes", "--skip-verify")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert (repo / ".claude" / "skills" / "claude-md-governance" / "SKILL.md").exists()
    assert_no_python_cache_files(repo)


def test_token_estimate_and_required_aliases() -> None:
    text = "# Overview\n\nDo NOT introduce new frameworks.\n"
    assert lint.estimate_tokens(text) > 0
    assert lint.has_section(text, ["Project Overview", "Overview"])


def test_import_too_long_fails(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "import-too-long")
    (repo / ".claude").mkdir()
    (repo / ".claude-governance").mkdir()
    (repo / "docs").mkdir(exist_ok=True)
    (repo / "docs" / "long.md").write_text("\n".join(f"line {i}" for i in range(45)), encoding="utf-8")
    policy = json.loads(policy_path("generic").read_text(encoding="utf-8"))
    (repo / ".claude-governance" / "policy.json").write_text(json.dumps(policy), encoding="utf-8")
    (repo / ".claude" / "settings.json").write_text(
        json.dumps(
            {
                "hooks": {
                    "PreToolUse": [{"matcher": "Edit|Write|MultiEdit", "hooks": [{"type": "command", "command": "python scripts/claude_hook_guard.py pre"}]}],
                    "PostToolUse": [{"matcher": "Edit|Write|MultiEdit", "hooks": [{"type": "command", "command": "python scripts/claude_hook_guard.py post"}]}],
                    "ConfigChange": [{"matcher": "", "hooks": [{"type": "command", "command": "python scripts/claude_hook_guard.py config"}]}],
                }
            }
        ),
        encoding="utf-8",
    )
    (repo / "CLAUDE.md").write_text(
        "# Project Overview\n\nx\n# Tech Stack\n\nx\n# Do NOT introduce\n\nx\n# Code Rules\n\nx\n# Context Map\n\n@docs/long.md\n# Quality Gates\n\nx\n# Working Style\n\nx\n",
        encoding="utf-8",
    )
    proc = run_cli("lint", "--repo", str(repo), "--quiet")
    assert proc.returncode == 1


def test_lint_requires_hook_matcher_coverage_for_all_edit_tools(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "hook-coverage")
    assert run_cli("init", "--repo", str(repo), "--preset", "generic", "--ci", "none", "--yes").returncode == 0
    settings = repo / ".claude" / "settings.json"
    settings.write_text(
        json.dumps(
            {
                "hooks": {
                    "PreToolUse": [
                        {"matcher": "Edit", "hooks": [{"type": "command", "command": "claude-md-governance hook pre"}]}
                    ],
                    "PostToolUse": [
                        {"matcher": "Edit|Write|MultiEdit", "hooks": [{"type": "command", "command": "claude-md-governance hook post"}]}
                    ],
                    "ConfigChange": [
                        {"matcher": "", "hooks": [{"type": "command", "command": "claude-md-governance hook config"}]}
                    ],
                }
            }
        ),
        encoding="utf-8",
    )
    bad = run_cli("lint", "--repo", str(repo), "--quiet")
    assert bad.returncode == 1

    data = json.loads(settings.read_text(encoding="utf-8"))
    data["hooks"]["PreToolUse"][0]["matcher"] = "Edit|Write|MultiEdit"
    settings.write_text(json.dumps(data), encoding="utf-8")
    good = run_cli("lint", "--repo", str(repo), "--quiet")
    assert good.returncode == 0, good.stdout + good.stderr


def test_autofix_repairs_current_repo_without_score_file(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "autofix")
    assert run_cli("init", "--repo", str(repo), "--preset", "generic", "--ci", "none", "--yes").returncode == 0
    (repo / ".claude-governance" / "score.json").unlink(missing_ok=True)
    (repo / "src" / "auth").mkdir(parents=True)
    (repo / "docs").mkdir(exist_ok=True)
    (repo / "docs" / "long.md").write_text("\n".join(f"line {i}" for i in range(45)), encoding="utf-8")
    (repo / "CLAUDE.md").write_text("# Project Overview\n\n@docs/long.md\n", encoding="utf-8")
    (repo / ".claude" / "settings.json").write_text(json.dumps({"hooks": {}}), encoding="utf-8")

    dry = run_cli("autofix", "--repo", str(repo), "--dry-run")
    assert dry.returncode == 0, dry.stdout + dry.stderr
    assert not (repo / "src" / "auth" / "CLAUDE.md").exists()

    applied = run_cli("autofix", "--repo", str(repo), "--apply")
    assert applied.returncode == 0, applied.stdout + applied.stderr
    assert (repo / "src" / "auth" / "CLAUDE.md").exists()
    assert "@docs/long.md" not in (repo / "CLAUDE.md").read_text(encoding="utf-8")
    settings = json.loads((repo / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert "PreToolUse" in settings["hooks"]
    assert "PostToolUse" in settings["hooks"]


def test_codeup_init_does_not_create_github_actions(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "codeup")
    proc = run_cli("init", "--repo", str(repo), "--preset", "enterprise-java-codeup", "--ci", "codeup", "--config-change-mode", "warn", "--yes")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert not (repo / ".github" / "workflows" / "claude-md-governance.yml").exists()
    assert (repo / "docs" / "ci" / "codeup-claude-md-governance.md").exists()


def test_settings_merge_preserves_existing_hooks(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "merge-settings")
    settings = repo / ".claude" / "settings.json"
    settings.parent.mkdir()
    settings.write_text(
        json.dumps({"hooks": {"PreToolUse": [{"matcher": "Read", "hooks": [{"type": "command", "command": "echo keep"}]}]}}),
        encoding="utf-8",
    )
    proc = run_cli("init", "--repo", str(repo), "--preset", "generic", "--ci", "none", "--yes")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    data = json.loads(settings.read_text(encoding="utf-8"))
    commands = [hook["command"] for group in data["hooks"]["PreToolUse"] for hook in group["hooks"]]
    assert "echo keep" in commands
    assert any("claude_hook_guard.py pre" in command for command in commands)


def test_config_warn_mode_is_non_blocking(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "warn")
    proc = run_cli("init", "--repo", str(repo), "--preset", "generic", "--ci", "none", "--config-change-mode", "warn", "--yes")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    event = json.dumps({"config_key": "model", "new_value": "example"})
    hook = run_cli("hook", "config", cwd=repo, input_text=event)
    assert hook.returncode == 0
    assert "WARNING" in hook.stderr


def test_pre_hook_blocks_and_allows_protected_path(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "hooks")
    assert run_cli("init", "--repo", str(repo), "--preset", "generic", "--ci", "none", "--yes").returncode == 0
    event = json.dumps({"tool_input": {"file_path": ".claude/settings.json"}})
    blocked = run_cli("hook", "pre", cwd=repo, input_text=event)
    assert blocked.returncode == 2
    env = os.environ.copy()
    env["ALLOW_PROTECTED_EDIT"] = "1"
    allowed = run_cli("hook", "pre", cwd=repo, input_text=event, env=env)
    assert allowed.returncode == 0
    open_path = run_cli("hook", "pre", cwd=repo, input_text=json.dumps({"tool_input": {"file_path": "README.md"}}))
    assert open_path.returncode == 0


def test_post_hook_message_does_not_claim_rollback(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "post")
    assert run_cli("init", "--repo", str(repo), "--preset", "generic", "--ci", "none", "--yes").returncode == 0
    post = run_cli("hook", "post", cwd=repo, input_text=json.dumps({"tool_input": {"file_path": "CLAUDE.md"}}))
    assert "rollback" not in (post.stdout + post.stderr).lower()


def test_generic_install_verify_passes(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "generic")
    proc = run_cli("init", "--repo", str(repo), "--preset", "generic", "--ci", "github", "--yes")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert (repo / ".github" / "workflows" / "claude-md-governance.yml").exists()
    verify = run_cli("verify", "--repo", str(repo))
    assert verify.returncode == 0, verify.stdout + verify.stderr


def test_java_maven_preset_thresholds(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "java")
    (repo / "pom.xml").write_text("<project><properties><java.version>17</java.version></properties></project>", encoding="utf-8")
    proc = run_cli("init", "--repo", str(repo), "--preset", "java-maven", "--ci", "none", "--yes")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    policy = json.loads((repo / ".claude-governance" / "policy.json").read_text(encoding="utf-8"))
    assert policy["root_claude"]["max_lines"] == 230
    assert run_cli("verify", "--repo", str(repo)).returncode == 0


def test_bad_claude_md_fails(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "bad")
    assert run_cli("init", "--repo", str(repo), "--preset", "generic", "--ci", "none", "--yes").returncode == 0
    (repo / "CLAUDE.md").write_text(("# Project Overview\n\n保持简洁。高质量。注重性能。\n") * 80, encoding="utf-8")
    proc = run_cli("lint", "--repo", str(repo), "--quiet")
    assert proc.returncode == 1
