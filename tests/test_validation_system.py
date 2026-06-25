from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from claude_md_governance import autofix, behavior, hook_guard, installer, lint, verify
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
    assert installer.detect_config_mode("auto", "enterprise-java-codeup") == "warn"
    assert lint.has_section("# 1. Overview\n", ["Project Overview", "Overview"])


def test_cli_init_defaults_are_honored_by_wrapper(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "enterprise-java-codeup-name-should-not-change-cli-default")
    (repo / "pom.xml").write_text("<project></project>", encoding="utf-8")
    proc = run_cli("init", "--repo", str(repo))
    assert proc.returncode == 2
    assert "Use --yes for non-interactive installation." in proc.stderr

    proc = run_cli("init", "--repo", str(repo), "--yes")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    policy = json.loads((repo / ".claude-governance" / "policy.json").read_text(encoding="utf-8"))
    assert policy["preset"] == "generic"
    assert policy["hooks"]["config_change_mode"] == "block"

    enterprise_repo = make_repo(tmp_path, "explicit-enterprise-java-codeup")
    (enterprise_repo / "pom.xml").write_text("<project></project>", encoding="utf-8")
    proc = run_cli("init", "--repo", str(enterprise_repo), "--preset", "enterprise-java-codeup", "--ci", "codeup", "--yes")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    enterprise_policy = json.loads((enterprise_repo / ".claude-governance" / "policy.json").read_text(encoding="utf-8"))
    assert enterprise_policy["hooks"]["config_change_mode"] == "warn"


def test_line_token_vague_import_and_section_rules(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "unit-lint")
    assert install(repo).returncode == 0
    (repo / "docs").mkdir(exist_ok=True)
    (repo / "docs" / "long.md").write_text("\n".join(f"line {i}" for i in range(41)), encoding="utf-8")
    (repo / "AGENTS.md").write_text(
        "# Overview\n\nclean code simple robust high quality maintainable elegant performant\n\n@docs/long.md\n",
        encoding="utf-8",
    )
    policy = json.loads((repo / ".claude-governance" / "policy.json").read_text(encoding="utf-8"))
    report = lint.lint(repo, policy, repo / "AGENTS.md")
    rules = {finding["rule"] for finding in report["findings"]}
    assert report["status"] == "fail"
    assert "MISSING_SECTION" in rules
    assert "TOO_MANY_VAGUE_RULES" in rules
    assert "IMPORT_TOO_LONG" in rules
    assert report["summary"]["root_doc_path"] == "AGENTS.md"
    assert report["summary"]["line_count"] == len((repo / "AGENTS.md").read_text(encoding="utf-8").splitlines())
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
    assert (repo / "src" / "auth" / "AGENTS.md").exists()


def test_init_appends_required_sections_only_when_headings_exist(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "body-mentions")
    (repo / "AGENTS.md").write_text(
        "# Notes\n\n"
        "This paragraph mentions Project Overview, Tech Stack, Do NOT introduce, Code Rules, "
        "Context Map, Quality Gates, and Working Style, but none of them are headings.\n",
        encoding="utf-8",
    )
    proc = install(repo)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    text = (repo / "AGENTS.md").read_text(encoding="utf-8")
    for heading in ["Project Overview", "Tech Stack", "Do NOT introduce", "Code Rules", "Context Map", "Quality Gates", "Working Style"]:
        assert f"# {heading}" in text


def test_integration_sample_repositories(tmp_path: Path) -> None:
    cases = [
        ("generic-repo", "generic", "github", None),
        ("java-maven-repo", "java-maven", "none", "pom.xml"),
        ("enterprise-java-codeup-repo", "enterprise-java-codeup", "codeup", "pom.xml"),
        ("existing-settings-repo", "generic", "none", ".claude/settings.json"),
        ("codeup-mode-repo", "enterprise-java-codeup", "codeup", "pom.xml"),
    ]
    for name, preset, ci, marker in cases:
        repo = make_repo(tmp_path, name)
        if marker == "pom.xml":
            (repo / "pom.xml").write_text("<project><properties><java.version>17</java.version></properties></project>", encoding="utf-8")
        if marker == ".claude/settings.json":
            (repo / ".claude").mkdir()
            (repo / ".claude" / "settings.json").write_text(json.dumps({"hooks": {"PreToolUse": []}}), encoding="utf-8")
        init = install(repo, preset, ci, "--config-change-mode", "warn" if "codeup" in name or preset == "enterprise-java-codeup" else "block")
        assert init.returncode == 0, init.stdout + init.stderr
        assert run_cli("lint", "--repo", str(repo), "--quiet").returncode == 0
        assert run_cli("verify", "--repo", str(repo)).returncode == 0

    bad = make_repo(tmp_path, "bad-repo-with-vague-claude-md")
    (bad / "AGENTS.md").write_text(("# Project Overview\n\nclean code simple robust high quality maintainable elegant performant\n") * 20, encoding="utf-8")
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
    env["CLAUDE_GOVERNANCE_APPROVED_PATHS"] = ".claude/settings.json"
    assert run_cli("hook", "pre", cwd=repo, input_text=protected, env=env).returncode == 0
    assert run_cli("hook", "pre", cwd=repo, input_text=json.dumps({"tool_input": {"file_path": "README.md"}})).returncode == 0

    blocked = run_cli("hook", "config", cwd=repo, input_text=json.dumps({"config_key": "model"}))
    assert blocked.returncode == 2

    warn_repo = make_repo(tmp_path, "hooks-warn")
    assert install(warn_repo, "generic", "none", "--config-change-mode", "warn").returncode == 0
    warned = run_cli("hook", "config", cwd=warn_repo, input_text=json.dumps({"config_key": "model"}))
    assert warned.returncode == 0
    assert "WARNING" in warned.stderr


def test_invalid_policy_blocks_hook_and_verify_reports_schema_error(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "invalid-policy")
    assert install(repo).returncode == 0
    (repo / ".claude-governance" / "policy.json").write_text("{bad json", encoding="utf-8")
    protected = json.dumps({"tool_input": {"file_path": ".claude/settings.json"}})

    blocked = run_cli("hook", "pre", cwd=repo, input_text=protected)
    assert blocked.returncode == 2
    assert "invalid JSON" in blocked.stderr

    lint_proc = run_cli("lint", "--repo", str(repo), "--quiet")
    assert lint_proc.returncode == 2
    assert "invalid JSON" in lint_proc.stderr

    verify_proc = run_cli("verify", "--repo", str(repo))
    assert verify_proc.returncode == 1
    assert "policy schema validates" in verify_proc.stdout
    assert "invalid JSON" in verify_proc.stderr


def test_policy_schema_rejects_invalid_field_types(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "invalid-policy-types")
    assert install(repo).returncode == 0
    policy = json.loads((repo / ".claude-governance" / "policy.json").read_text(encoding="utf-8"))
    policy["score_threshold"] = True
    policy["hooks"]["config_change_mode"] = "silent"
    policy["protected_paths"] = [123]
    (repo / ".claude-governance" / "policy.json").write_text(json.dumps(policy), encoding="utf-8")

    proc = run_cli("lint", "--repo", str(repo), "--quiet")
    assert proc.returncode == 2
    assert "score_threshold" in proc.stderr
    assert "hooks.config_change_mode" in proc.stderr
    assert "protected_paths" in proc.stderr

    verify_proc = run_cli("verify", "--repo", str(repo))
    assert verify_proc.returncode == 1
    assert "policy schema validates" in verify_proc.stdout
    assert "score_threshold" in verify_proc.stderr


def test_verify_script_fallback_policy_validator_matches_core_schema(monkeypatch, tmp_path: Path) -> None:
    import builtins
    import runpy

    real_import = builtins.__import__

    def blocked_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "claude_md_governance.policy_schema":
            raise ImportError("simulate target repo without installed package")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocked_import)
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "verify_claude_governance.py"
    namespace = runpy.run_path(str(script_path))
    load_policy_file = namespace["load_policy_file"]
    validation_error = namespace["PolicyValidationError"]

    policy_path = tmp_path / "policy.json"
    policy_path.write_text(
        json.dumps(
            {
                "version": 1,
                "preset": "generic",
                "score_threshold": True,
                "root_doc": {"path": "AGENTS.md", "max_lines": True},
                "required_sections": [{"name": "", "aliases": [""], "severity": "fatal", "deduction": False}],
                "protected_paths": [".claude/**"],
                "sensitive_paths": [
                    {
                        "path": "src/auth/**",
                        "local_doc": "",
                        "required_tests": ["pytest"],
                        "detect_keywords": [123],
                        "protected": "yes",
                    }
                ],
                "hooks": {"config_change_mode": "block", "require_pretool_guard": "yes"},
                "ci": {"provider": "travis"},
                "behavior_tests": {"enabled_by_default": "yes", "case_file": ""},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(validation_error) as exc_info:
        load_policy_file(policy_path)

    error_text = str(exc_info.value)
    assert "score_threshold" in error_text
    assert "root_doc.max_lines" in error_text
    assert "required_sections[0].name" in error_text
    assert "sensitive_paths[0].detect_keywords" in error_text
    assert "hooks.require_pretool_guard" in error_text
    assert "ci.provider" in error_text
    assert "behavior_tests.enabled_by_default" in error_text


def test_policy_validate_and_migrate_commands(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "policy-cli")
    policy_path = repo / ".claude-governance" / "policy.json"
    policy_path.parent.mkdir()
    policy_path.write_text(
        json.dumps({"version": 1, "preset": "legacy", "root_claude": {"path": "CLAUDE.md"}, "hooks": {}}),
        encoding="utf-8",
    )

    invalid = run_cli("policy", "validate", "--repo", str(repo))
    assert invalid.returncode == 1
    assert "config_change_mode" in invalid.stdout

    migrated = run_cli("policy", "migrate", "--repo", str(repo), "--write")
    assert migrated.returncode == 0, migrated.stdout + migrated.stderr
    payload = json.loads(migrated.stdout)
    assert payload["changed"] is True
    assert payload["written"] is True

    valid = run_cli("policy", "validate", "--repo", str(repo))
    assert valid.returncode == 0, valid.stdout + valid.stderr
    updated = json.loads(policy_path.read_text(encoding="utf-8"))
    assert updated["root_doc"]["path"] == "CLAUDE.md"
    assert updated["hooks"]["config_change_mode"] == "block"


def test_doctor_explain_prints_diagnostic_summary(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "doctor-explain")
    assert install(repo).returncode == 0
    proc = run_cli("doctor", "--repo", str(repo), "--explain")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "Diagnostic explanation:" in proc.stdout
    assert "- status: pass" in proc.stdout
    assert "- root_doc: AGENTS.md" in proc.stdout


def test_repo_index_helpers_reuse_scan_results(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "repo-index")
    (repo / "src" / "payments").mkdir(parents=True)
    (repo / "src" / "payments" / "service.py").write_text("x = 1\n", encoding="utf-8")
    (repo / "package.json").write_text(json.dumps({"dependencies": {"left-pad": "1.0.0"}}), encoding="utf-8")
    index = lint.build_repo_index(repo)

    assert "src/payments" in index.dirs
    assert "src/payments/service.py" in index.files
    assert lint.glob_has_matches(repo, "src/payments/**", index)
    assert lint.dependency_mentions(repo, "left-pad", index) == ["package.json"]
    sensitive = {"path": "src/payments/**", "local_claude": "src/payments/CLAUDE.md", "protected": True}
    assert lint.find_sensitive_dirs(repo, sensitive, index) == ["src/payments"]


def test_hook_lint_cache_is_keyed_by_governance_state(tmp_path: Path, monkeypatch) -> None:
    repo = make_repo(tmp_path, "hook-cache")
    assert install(repo).returncode == 0
    monkeypatch.chdir(repo)
    monkeypatch.setenv("CLAUDE_GOVERNANCE_LINT_CACHE_SECONDS", "30")
    policy = json.loads((repo / ".claude-governance" / "policy.json").read_text(encoding="utf-8"))

    assert not hook_guard.lint_recently_passed(policy)
    hook_guard.remember_lint_pass(policy)
    assert hook_guard.lint_recently_passed(policy)

    (repo / "AGENTS.md").write_text((repo / "AGENTS.md").read_text(encoding="utf-8") + "\n", encoding="utf-8")
    assert not hook_guard.lint_recently_passed(policy)


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


def test_lint_accepts_supported_hook_command_forms(tmp_path: Path) -> None:
    command_sets = [
        (
            "bare-python",
            {
                "pre": "python scripts/claude_hook_guard.py pre",
                "post": "python scripts/claude_hook_guard.py post",
                "config": "python scripts/claude_hook_guard.py config",
            },
        ),
        (
            "module-cli",
            {
                "pre": "python -m claude_md_governance.cli hook pre",
                "post": "python -m claude_md_governance.cli hook post",
                "config": "python -m claude_md_governance.cli hook config",
            },
        ),
        (
            "codex-cli",
            {
                "pre": "codex-md-governance hook pre",
                "post": "codex-md-governance hook post",
                "config": "codex-md-governance hook config",
            },
        ),
        (
            "node-wrapper",
            {
                "pre": 'node "$CLAUDE_PROJECT_DIR/.claude/hooks/run-python-hook.js" "$CLAUDE_PROJECT_DIR/scripts/claude_hook_guard.py" pre',
                "post": 'node "$CLAUDE_PROJECT_DIR/.claude/hooks/run-python-hook.js" "$CLAUDE_PROJECT_DIR/scripts/claude_hook_guard.py" post',
                "config": 'node "$CLAUDE_PROJECT_DIR/.claude/hooks/run-python-hook.js" "$CLAUDE_PROJECT_DIR/scripts/claude_hook_guard.py" config',
            },
        ),
    ]
    for name, commands in command_sets:
        repo = make_repo(tmp_path, name)
        assert install(repo).returncode == 0
        settings = repo / ".claude" / "settings.json"
        settings.write_text(
            json.dumps(
                {
                    "hooks": {
                        "PreToolUse": [
                            {"matcher": "Edit|Write|MultiEdit", "hooks": [{"type": "command", "command": commands["pre"]}]}
                        ],
                        "PostToolUse": [
                            {"matcher": "Edit|Write|MultiEdit", "hooks": [{"type": "command", "command": commands["post"]}]}
                        ],
                        "ConfigChange": [
                            {"matcher": "", "hooks": [{"type": "command", "command": commands["config"]}]}
                        ],
                    }
                }
            ),
            encoding="utf-8",
        )
        proc = run_cli("lint", "--repo", str(repo), "--quiet")
        assert proc.returncode == 0, name + proc.stdout + proc.stderr


def test_verify_warn_config_change_accepts_warning_output(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "verify-warn")
    init = install(repo, "enterprise-java-codeup", "codeup", "--config-change-mode", "warn")
    assert init.returncode == 0, init.stdout + init.stderr
    verify = run_cli("verify", "--repo", str(repo))
    assert verify.returncode == 0, verify.stdout + verify.stderr
    assert "PASS: ConfigChange warn emits warning and does not block" in verify.stdout


def test_verify_compatibility_defaults_and_optional_autofix(tmp_path: Path) -> None:
    assert verify.config_change_mode({"hooks": {"config_change_mode": "block", "protected_config_review_required": False}}) == "block"
    assert verify.config_change_mode({"hooks": {"config_change_mode": "warn"}}) == "warn"
    assert verify.config_change_mode({"hooks": {"config_change_mode": "off"}}) == "off"
    assert verify.config_change_mode({"hooks": {"protected_config_review_required": False}}) == "warn"

    repo = make_repo(tmp_path, "missing-autofix")
    assert install(repo).returncode == 0
    (repo / "scripts" / "claude_md_autofix.py").unlink()
    proc = run_cli("verify", "--repo", str(repo))
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_backups_keep_first_snapshot_when_same_file_changes_twice(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "backup")
    target = repo / "AGENTS.md"
    target.write_text("original", encoding="utf-8")
    backup_root = repo / ".claude-governance" / "backups" / "stamp"

    autofix.backup(repo, Path("AGENTS.md"), backup_root)
    target.write_text("modified", encoding="utf-8")
    autofix.backup(repo, Path("AGENTS.md"), backup_root)

    assert (backup_root / "AGENTS.md").read_text(encoding="utf-8") == "original"


def test_existing_policy_sensitive_paths_are_preserved(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "existing-policy")
    policy_path = repo / ".claude-governance" / "policy.json"
    policy_path.parent.mkdir()
    exact_sensitive_paths = [
        {
            "id": "exact-payment-service",
            "path": "services/payment/src/main/java/**",
            "local_claude": "services/payment/CLAUDE.md",
            "required_tests": ["mvn -pl services/payment test"],
            "protected": True,
        }
    ]
    policy_path.write_text(
        json.dumps({"version": 99, "preset": "custom", "sensitive_paths": exact_sensitive_paths}, ensure_ascii=False),
        encoding="utf-8",
    )
    proc = run_cli(
        "init",
        "--repo",
        str(repo),
        "--preset",
        "enterprise-java-codeup",
        "--ci",
        "codeup",
        "--config-change-mode",
        "warn",
        "--yes",
        "--skip-verify",
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    merged = json.loads(policy_path.read_text(encoding="utf-8"))
    assert exact_sensitive_paths[0] in merged["sensitive_paths"]
    assert any(item.get("id") == "payment" for item in merged["sensitive_paths"])
    assert merged["hooks"]["config_change_mode"] == "warn"


def test_maven_quality_commands_use_real_module_or_root(tmp_path: Path, monkeypatch) -> None:
    repo = make_repo(tmp_path, "maven-commands")
    policy = json.loads(policy_path("enterprise-java-codeup").read_text(encoding="utf-8"))
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
    root_local = root_repo / "src" / "main" / "java" / "example" / "payment" / "AGENTS.md"
    assert "- `mvn test`" in root_local.read_text(encoding="utf-8")

    module_repo = make_repo(tmp_path, "module-maven")
    (module_repo / "pom.xml").write_text("<project><modules><module>payment-service</module></modules></project>", encoding="utf-8")
    (module_repo / "payment-service" / "src" / "main" / "java" / "example" / "payment").mkdir(parents=True)
    assert install(module_repo, "java-maven").returncode == 0
    module_local = module_repo / "payment-service" / "src" / "main" / "java" / "example" / "payment" / "AGENTS.md"
    assert "- `mvn -pl payment-service -am test`" in module_local.read_text(encoding="utf-8")


def test_policy_commands_are_tokenized_and_never_shell_chained() -> None:
    assert hook_guard.command_allowed("python scripts/check.py")
    assert hook_guard.command_allowed("mvn -pl service test")
    assert hook_guard.command_allowed("npm run test:unit")
    assert not hook_guard.command_allowed("python scripts/check.py; echo leaked")
    assert not hook_guard.command_allowed("python -c 'print(1)'")
    assert not hook_guard.command_allowed("bash scripts/check.sh")


def test_non_allowlisted_policy_command_fails_strictly_by_default(monkeypatch) -> None:
    monkeypatch.delenv("CLAUDE_GOVERNANCE_STRICT_COMMANDS", raising=False)
    assert hook_guard.run_command("bash scripts/check.sh") == 2

    monkeypatch.setenv("CLAUDE_GOVERNANCE_STRICT_COMMANDS", "warn")
    assert hook_guard.run_command("bash scripts/check.sh") == 0


def test_mutation_vague_claude_md_must_fail(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "mutation")
    assert install(repo).returncode == 0
    bad_text = "# Project Overview\n\n" + " ".join(
        ["clean code", "best practices", "simple", "elegant", "robust", "performant", "maintainable", "high quality"] * 3
    )
    (repo / "AGENTS.md").write_text(bad_text, encoding="utf-8")
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
    governance_workflow = Path(".github/workflows/claude-md-governance.yml").read_text(encoding="utf-8")
    assert "os: [ubuntu-latest, windows-latest]" in workflow
    assert 'python-version: ["3.10", "3.11", "3.12"]' in workflow
    assert 'requires-python = ">=3.10"' in Path("pyproject.toml").read_text(encoding="utf-8")
    assert 'python -m pip install -e ".[test]"' in workflow
    assert "python -m pytest -q" in workflow
    assert "codex-md-governance doctor" in workflow
    assert 'codex-md-governance = "claude_md_governance.cli:main"' in Path("pyproject.toml").read_text(encoding="utf-8")
    assert 'claude-md-governance = "claude_md_governance.cli:main"' in Path("pyproject.toml").read_text(encoding="utf-8")
    assert "AGENTS.md" in governance_workflow
    assert ".agents/**" in governance_workflow
    assert "windows-latest" in governance_workflow
    assert policy_path("generic").exists()
