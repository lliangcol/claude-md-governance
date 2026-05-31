from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from claude_md_governance import behavior, hook_guard, installer, lint
from claude_md_governance.templates import policy_path


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


def install(repo: Path, preset: str = "generic", ci: str = "none", *extra: str) -> subprocess.CompletedProcess[str]:
    return run_cli("init", "--repo", str(repo), "--preset", preset, "--ci", ci, "--yes", *extra)


def test_policy_loading_defaults_and_aliases() -> None:
    policy = installer.load_policy_template("missing")
    assert policy["preset"] == "generic"
    assert policy["root_claude"]["max_lines"] == 200
    assert installer.detect_config_mode("auto", "generic") == "block"
    assert installer.detect_config_mode("auto", "onm-agent") == "warn"
    assert lint.has_section("# 1. Overview\n", ["Project Overview", "Overview"])


def test_cli_init_defaults_are_honored_by_wrapper(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "onm-agent-name-should-not-change-cli-default")
    (repo / "pom.xml").write_text("<project></project>", encoding="utf-8")
    proc = run_cli("init", "--repo", str(repo))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    policy = json.loads((repo / ".claude-governance" / "policy.json").read_text(encoding="utf-8"))
    assert policy["preset"] == "generic"
    assert policy["hooks"]["config_change_mode"] == "block"

    onm_repo = make_repo(tmp_path, "explicit-onm-agent")
    (onm_repo / "pom.xml").write_text("<project></project>", encoding="utf-8")
    proc = run_cli("init", "--repo", str(onm_repo), "--preset", "onm-agent", "--ci", "codeup", "--yes")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    onm_policy = json.loads((onm_repo / ".claude-governance" / "policy.json").read_text(encoding="utf-8"))
    assert onm_policy["hooks"]["config_change_mode"] == "warn"


def test_line_token_vague_import_and_section_rules(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "unit-lint")
    assert install(repo).returncode == 0
    (repo / "docs").mkdir(exist_ok=True)
    (repo / "docs" / "long.md").write_text("\n".join(f"line {i}" for i in range(41)), encoding="utf-8")
    (repo / "CLAUDE.md").write_text(
        "# Overview\n\nclean code simple robust high quality maintainable elegant performant\n\n@docs/long.md\n",
        encoding="utf-8",
    )
    policy = json.loads((repo / ".claude-governance" / "policy.json").read_text(encoding="utf-8"))
    report = lint.lint(repo, policy, repo / "CLAUDE.md")
    rules = {finding["rule"] for finding in report["findings"]}
    assert report["status"] == "fail"
    assert "MISSING_SECTION" in rules
    assert "TOO_MANY_VAGUE_RULES" in rules
    assert "IMPORT_TOO_LONG" in rules
    assert report["summary"]["claude_path"] == "CLAUDE.md"
    assert report["summary"]["line_count"] == len((repo / "CLAUDE.md").read_text(encoding="utf-8").splitlines())
    assert report["summary"]["estimated_tokens"] > 0


def test_settings_merge_path_normalization_and_sensitive_scan(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "sensitive")
    settings = repo / ".claude" / "settings.json"
    settings.parent.mkdir()
    settings.write_text(
        json.dumps({"hooks": {"PreToolUse": [{"matcher": "Read", "hooks": [{"type": "command", "command": "echo keep"}]}]}}),
        encoding="utf-8",
    )
    (repo / "src" / "auth").mkdir(parents=True)
    assert install(repo).returncode == 0

    merged = json.loads(settings.read_text(encoding="utf-8"))
    commands = [hook["command"] for group in merged["hooks"]["PreToolUse"] for hook in group["hooks"]]
    assert "echo keep" in commands
    assert lint.normalize(r".\src\auth\service.py") == "src/auth/service.py"
    assert hook_guard.event_path({"tool_input": {"file_path": r".\src\auth\service.py"}}) == "src/auth/service.py"
    assert (repo / "src" / "auth" / "CLAUDE.md").exists()


def test_init_appends_required_sections_only_when_headings_exist(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "body-mentions")
    (repo / "CLAUDE.md").write_text(
        "# Notes\n\n"
        "This paragraph mentions Project Overview, Tech Stack, Do NOT introduce, Code Rules, "
        "Context Map, Quality Gates, and Working Style, but none of them are headings.\n",
        encoding="utf-8",
    )
    proc = install(repo)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    text = (repo / "CLAUDE.md").read_text(encoding="utf-8")
    for heading in ["Project Overview", "Tech Stack", "Do NOT introduce", "Code Rules", "Context Map", "Quality Gates", "Working Style"]:
        assert f"# {heading}" in text


def test_integration_sample_repositories(tmp_path: Path) -> None:
    cases = [
        ("generic-repo", "generic", "github", None),
        ("java-maven-repo", "java-maven", "none", "pom.xml"),
        ("onm-agent-like-repo", "onm-agent", "codeup", "pom.xml"),
        ("existing-settings-repo", "generic", "none", ".claude/settings.json"),
        ("codeup-mode-repo", "onm-agent", "codeup", "pom.xml"),
    ]
    for name, preset, ci, marker in cases:
        repo = make_repo(tmp_path, name)
        if marker == "pom.xml":
            (repo / "pom.xml").write_text("<project><properties><java.version>17</java.version></properties></project>", encoding="utf-8")
        if marker == ".claude/settings.json":
            (repo / ".claude").mkdir()
            (repo / ".claude" / "settings.json").write_text(json.dumps({"hooks": {"PreToolUse": []}}), encoding="utf-8")
        init = install(repo, preset, ci, "--config-change-mode", "warn" if "codeup" in name or preset == "onm-agent" else "block")
        assert init.returncode == 0, init.stdout + init.stderr
        assert run_cli("lint", "--repo", str(repo), "--quiet").returncode == 0
        assert run_cli("verify", "--repo", str(repo)).returncode == 0

    bad = make_repo(tmp_path, "bad-repo-with-vague-claude-md")
    (bad / "CLAUDE.md").write_text(("# Project Overview\n\nclean code simple robust high quality maintainable elegant performant\n") * 20, encoding="utf-8")
    init_bad = install(bad)
    assert init_bad.returncode == 1
    assert run_cli("lint", "--repo", str(bad), "--quiet").returncode == 1
    assert run_cli("verify", "--repo", str(bad)).returncode == 1


def test_hook_behavior_matrix(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "hooks")
    assert install(repo, "generic", "none", "--config-change-mode", "block").returncode == 0
    protected = json.dumps({"tool_input": {"file_path": ".claude/settings.json"}})
    assert run_cli("hook", "pre", cwd=repo, input_text=protected).returncode == 2

    env = os.environ.copy()
    env["ALLOW_PROTECTED_EDIT"] = "1"
    assert run_cli("hook", "pre", cwd=repo, input_text=protected, env=env).returncode == 0
    assert run_cli("hook", "pre", cwd=repo, input_text=json.dumps({"tool_input": {"file_path": "README.md"}})).returncode == 0

    blocked = run_cli("hook", "config", cwd=repo, input_text=json.dumps({"config_key": "model"}))
    assert blocked.returncode == 2

    warn_repo = make_repo(tmp_path, "hooks-warn")
    assert install(warn_repo, "generic", "none", "--config-change-mode", "warn").returncode == 0
    warned = run_cli("hook", "config", cwd=warn_repo, input_text=json.dumps({"config_key": "model"}))
    assert warned.returncode == 0
    assert "WARNING" in warned.stderr


def test_pre_hook_blocks_absolute_protected_path(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "absolute-hook")
    assert install(repo).returncode == 0
    protected = json.dumps({"tool_input": {"file_path": str((repo / ".claude" / "settings.json").resolve())}})
    assert run_cli("hook", "pre", cwd=repo, input_text=protected).returncode == 2
    parent_relative = json.dumps({"tool_input": {"file_path": f"../{repo.name}/.claude/settings.json"}})
    assert run_cli("hook", "pre", cwd=repo, input_text=parent_relative).returncode == 2


def test_lint_rejects_invalid_hook_type_and_mode_prefix(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "invalid-hooks")
    assert install(repo).returncode == 0
    settings = repo / ".claude" / "settings.json"
    data = json.loads(settings.read_text(encoding="utf-8"))

    for groups in data["hooks"].values():
        for group in groups:
            for hook in group["hooks"]:
                hook["command"] += "check"
    settings.write_text(json.dumps(data), encoding="utf-8")
    assert run_cli("lint", "--repo", str(repo), "--quiet").returncode == 1

    data = {
        "hooks": {
            "PreToolUse": [
                {"matcher": "Edit|Write|MultiEdit", "hooks": [{"type": "not-command", "command": "python scripts/claude_hook_guard.py pre"}]}
            ],
            "PostToolUse": [
                {"matcher": "Edit|Write|MultiEdit", "hooks": [{"type": "command", "command": "python scripts/claude_hook_guard.py post"}]}
            ],
            "ConfigChange": [
                {"matcher": "", "hooks": [{"type": "command", "command": "python scripts/claude_hook_guard.py config"}]}
            ],
        }
    }
    settings.write_text(json.dumps(data), encoding="utf-8")
    assert run_cli("lint", "--repo", str(repo), "--quiet").returncode == 1


def test_maven_quality_commands_use_real_module_or_root(tmp_path: Path, monkeypatch) -> None:
    repo = make_repo(tmp_path, "maven-commands")
    policy = json.loads(policy_path("onm-agent").read_text(encoding="utf-8"))
    (repo / "pom.xml").write_text("<project></project>", encoding="utf-8")
    monkeypatch.chdir(repo)
    assert hook_guard.related_quality_commands(policy, "src/main/java/example/payment/PaymentService.java") == ["mvn test"]

    (repo / "pom.xml").write_text("<project><modules><module>payment-service</module></modules></project>", encoding="utf-8")
    assert hook_guard.related_quality_commands(policy, "payment-service/src/main/java/example/payment/PaymentService.java") == [
        "mvn -pl payment-service -am test"
    ]


def test_installer_local_maven_checks_use_module_or_root(tmp_path: Path) -> None:
    root_repo = make_repo(tmp_path, "root-maven")
    (root_repo / "pom.xml").write_text("<project></project>", encoding="utf-8")
    (root_repo / "src" / "main" / "java" / "example" / "payment").mkdir(parents=True)
    assert install(root_repo, "java-maven").returncode == 0
    root_local = root_repo / "src" / "main" / "java" / "example" / "payment" / "CLAUDE.md"
    assert "- `mvn test`" in root_local.read_text(encoding="utf-8")

    module_repo = make_repo(tmp_path, "module-maven")
    (module_repo / "pom.xml").write_text("<project><modules><module>payment-service</module></modules></project>", encoding="utf-8")
    (module_repo / "payment-service" / "src" / "main" / "java" / "example" / "payment").mkdir(parents=True)
    assert install(module_repo, "java-maven").returncode == 0
    module_local = module_repo / "payment-service" / "src" / "main" / "java" / "example" / "payment" / "CLAUDE.md"
    assert "- `mvn -pl payment-service -am test`" in module_local.read_text(encoding="utf-8")


def test_policy_commands_are_tokenized_and_never_shell_chained() -> None:
    assert hook_guard.command_allowed("python scripts/check.py")
    assert hook_guard.command_allowed("mvn -pl service test")
    assert hook_guard.command_allowed("npm run test:unit")
    assert not hook_guard.command_allowed("python scripts/check.py; echo leaked")
    assert not hook_guard.command_allowed("python -c 'print(1)'")
    assert not hook_guard.command_allowed("bash scripts/check.sh")


def test_mutation_vague_claude_md_must_fail(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "mutation")
    assert install(repo).returncode == 0
    bad_text = "# Project Overview\n\n" + " ".join(
        ["clean code", "best practices", "simple", "elegant", "robust", "performant", "maintainable", "high quality"] * 3
    )
    (repo / "CLAUDE.md").write_text(bad_text, encoding="utf-8")
    proc = run_cli("lint", "--repo", str(repo), "--quiet")
    assert proc.returncode == 1


def test_optional_claude_cli_skip_is_machine_readable_json(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "optional-claude")
    assert install(repo).returncode == 0
    env = os.environ.copy()
    env["PATH"] = ""
    proc = run_cli("behavior-test", "--repo", str(repo), env=env)
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["status"] == "skipped"
    assert "PASS" not in proc.stdout


def test_optional_claude_cli_not_logged_in_is_skipped(tmp_path: Path) -> None:
    assert behavior.auth_unavailable("Not logged in - Please run /login")
    if os.name == "nt":
        return

    repo = make_repo(tmp_path, "optional-claude-auth")
    assert install(repo).returncode == 0
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    claude = bin_dir / "claude"
    claude.write_text("#!/bin/sh\necho 'Not logged in - Please run /login' >&2\nexit 1\n", encoding="utf-8")
    claude.chmod(0o755)
    env = os.environ.copy()
    env["PATH"] = str(bin_dir)
    proc = run_cli("behavior-test", "--repo", str(repo), env=env)
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["status"] == "skipped"
    assert "not logged in" in payload["reason"].lower()


def test_verify_require_claude_fails_when_auth_unavailable(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "require-claude-auth")
    assert install(repo).returncode == 0
    bin_dir = tmp_path / "bin-require"
    bin_dir.mkdir()
    if os.name == "nt":
        fake = bin_dir / "claude.cmd"
        fake.write_text("@echo off\necho Not logged in - Please run /login 1>&2\nexit /b 1\n", encoding="utf-8")
    else:
        fake = bin_dir / "claude"
        fake.write_text("#!/bin/sh\necho 'Not logged in - Please run /login' >&2\nexit 1\n", encoding="utf-8")
        fake.chmod(0o755)
    env = os.environ.copy()
    env["PATH"] = str(bin_dir)

    proc = run_cli("verify", "--repo", str(repo), "--with-claude", "--require-claude", env=env)
    assert proc.returncode == 1
    assert "Claude CLI is installed but not logged in" in proc.stdout
    assert "Governance verification failed" in proc.stdout


def test_ci_workflow_contract() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert 'python-version: ["3.10", "3.11", "3.12"]' in workflow
    assert 'requires-python = ">=3.10"' in Path("pyproject.toml").read_text(encoding="utf-8")
    assert 'python -m pip install -e ".[test]"' in workflow
    assert "python -m pytest -q" in workflow
    assert "claude-md-governance doctor" in workflow
    assert policy_path("generic").exists()
