from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from importlib import resources
from pathlib import Path

from claude_md_governance import lint
from claude_md_governance.policy_schema import validate_policy
from claude_md_governance.templates import policy_path, template_root


REPO_ROOT = Path(__file__).resolve().parents[1]

RELEASE_CRITICAL_PACKAGE_DATA = [
    "data/schemas/policy.schema.json",
    "data/templates/policies/generic.json",
    "data/templates/policies/java-maven.json",
    "data/templates/policies/enterprise-java-codeup.json",
    "data/templates/common/.agents/skills/claude-md-governance/SKILL.md",
    "data/templates/common/.claude/skills/claude-md-governance/SKILL.md",
    "data/templates/common/.codex/hooks.json",
    "data/templates/common/scripts/claude_md_lint.py",
    "data/templates/common/scripts/claude_hook_guard.py",
    "data/templates/common/scripts/claude_md_autofix.py",
    "data/templates/common/scripts/verify_claude_governance.py",
    "data/templates/common/scripts/build_claude_md_eval_prompt.py",
    "data/templates/common/scripts/run_ai_behavior_tests.py",
    "data/templates/common/tests/ai_behavior_cases.json",
    "data/templates/common/tests/ai_behavior_cases.enterprise-java-codeup.json",
    "data/templates/github/workflows/claude-md-governance.yml",
    "data/templates/codeup/ci/codeup/claude-md-governance-step.yml",
    "data/templates/codeup/docs/ci/codeup-claude-md-governance.md",
    "data/templates/gitlab/.gitlab-ci.yml",
    "data/templates/gitlab/docs/ci/gitlab-claude-md-governance.md",
    "data/templates/jenkins/Jenkinsfile",
    "data/templates/jenkins/docs/ci/jenkins-claude-md-governance.md",
    "data/templates/buildkite/.buildkite/pipeline.yml",
    "data/templates/buildkite/docs/ci/buildkite-claude-md-governance.md",
]


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


def copy_example_fixture(tmp_path: Path, name: str) -> Path:
    dest = tmp_path / name
    shutil.copytree(REPO_ROOT / "examples" / name, dest, ignore=shutil.ignore_patterns("scripts"))
    return dest


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
    assert (root / "common" / ".agents" / "skills" / "claude-md-governance" / "SKILL.md").exists()
    assert (root / "common" / ".codex" / "hooks.json").exists()
    assert (root / "common" / ".claude" / "skills" / "claude-md-governance" / "SKILL.md").exists()
    assert (root / "github" / "workflows" / "claude-md-governance.yml").exists()
    assert not (root / "github" / ".github" / "workflows" / "claude-md-governance.yml").exists()
    assert (root / "gitlab" / ".gitlab-ci.yml").exists()
    assert (root / "gitlab" / "docs" / "ci" / "gitlab-claude-md-governance.md").exists()
    assert (root / "jenkins" / "Jenkinsfile").exists()
    assert (root / "jenkins" / "docs" / "ci" / "jenkins-claude-md-governance.md").exists()
    assert (root / "buildkite" / ".buildkite" / "pipeline.yml").exists()
    assert (root / "buildkite" / "docs" / "ci" / "buildkite-claude-md-governance.md").exists()
    assert policy_path("missing").name == "generic.json"


def test_installed_package_data_exposes_release_critical_resources() -> None:
    package_root = resources.files("claude_md_governance")
    missing = [path for path in RELEASE_CRITICAL_PACKAGE_DATA if not (package_root / path).is_file()]
    assert missing == []
    assert "stages:" in (package_root / "data/templates/gitlab/.gitlab-ci.yml").read_text(encoding="utf-8")
    assert "steps:" in (package_root / "data/templates/buildkite/.buildkite/pipeline.yml").read_text(encoding="utf-8")


def test_wheel_smoke_required_paths_cover_release_critical_resources() -> None:
    spec = importlib.util.spec_from_file_location("wheel_smoke", REPO_ROOT / "scripts" / "wheel_smoke.py")
    assert spec is not None and spec.loader is not None
    wheel_smoke = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wheel_smoke)

    expected = {f"claude_md_governance/{path}" for path in RELEASE_CRITICAL_PACKAGE_DATA}
    assert expected.issubset(set(wheel_smoke.REQUIRED_WHEEL_PATHS))


def test_init_copies_skill_and_filters_template_cache(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "skill-template")
    proc = run_cli("init", "--repo", str(repo), "--preset", "generic", "--ci", "none", "--yes", "--skip-verify")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert (repo / "AGENTS.md").exists()
    assert (repo / ".agents" / "skills" / "claude-md-governance" / "SKILL.md").exists()
    assert (repo / ".codex" / "hooks.json").exists()
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
    (repo / "AGENTS.md").write_text(
        "# Project Overview\n\nx\n# Tech Stack\n\nx\n# Do NOT introduce\n\nx\n# Code Rules\n\nx\n# Context Map\n\n@docs/long.md\n# Quality Gates\n\nx\n# Working Style\n\nx\n",
        encoding="utf-8",
    )
    proc = run_cli("lint", "--repo", str(repo), "--quiet")
    assert proc.returncode == 1


def test_banned_dependency_present_in_dependency_file_fails(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "banned-dep")
    assert run_cli("init", "--repo", str(repo), "--preset", "generic", "--ci", "none", "--yes").returncode == 0
    policy = json.loads((repo / ".claude-governance" / "policy.json").read_text(encoding="utf-8"))
    policy["banned_dependencies"] = ["left-pad"]
    (repo / ".claude-governance" / "policy.json").write_text(json.dumps(policy), encoding="utf-8")
    (repo / "package.json").write_text(json.dumps({"dependencies": {"left-pad": "1.3.0"}}), encoding="utf-8")

    proc = run_cli("lint", "--repo", str(repo), "--quiet")
    assert proc.returncode == 1


def test_sensitive_keywords_do_not_create_false_positive_without_path_match(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "sensitive-keywords")
    policy = json.loads(policy_path("generic").read_text(encoding="utf-8"))
    policy["sensitive_paths"] = [
        {
            "id": "payment",
            "path": "src/payments/**",
            "detect_keywords": ["payment"],
            "local_agents": "src/payments/AGENTS.md",
            "protected": True,
        }
    ]
    (repo / "docs" / "payment-notes").mkdir(parents=True)
    assert lint.find_sensitive_dirs(repo, policy["sensitive_paths"][0]) == []


def test_lint_reports_missing_agents_only_sensitive_local_doc(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "agents-only-sensitive")
    init = run_cli("init", "--repo", str(repo), "--preset", "generic", "--ci", "none", "--yes", "--skip-verify")
    assert init.returncode == 0, init.stdout + init.stderr
    (repo / "src" / "payments").mkdir(parents=True)
    policy = json.loads((repo / ".claude-governance" / "policy.json").read_text(encoding="utf-8"))
    policy["sensitive_paths"] = [
        {
            "id": "payments",
            "path": "src/payments/**",
            "local_agents": "src/payments/AGENTS.md",
            "protected": True,
        }
    ]
    (repo / ".claude-governance" / "policy.json").write_text(json.dumps(policy), encoding="utf-8")

    proc = run_cli("lint", "--repo", str(repo))
    assert proc.returncode == 1
    report = json.loads(proc.stdout)
    assert any(finding["rule"] == "MISSING_LOCAL_DOC" for finding in report["findings"])
    assert report["summary"]["detected_sensitive_dirs"] == [
        {"id": "payments", "dir": "src/payments", "local_doc": "src/payments/AGENTS.md"}
    ]


def test_lint_reports_root_local_instruction_conflict(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "root-local-conflict")
    init = run_cli("init", "--repo", str(repo), "--preset", "generic", "--ci", "none", "--yes", "--skip-verify")
    assert init.returncode == 0, init.stdout + init.stderr
    (repo / "src" / "payments").mkdir(parents=True)
    policy = json.loads((repo / ".claude-governance" / "policy.json").read_text(encoding="utf-8"))
    policy["sensitive_paths"] = [
        {
            "id": "payments",
            "path": "src/payments/**",
            "local_agents": "AGENTS.md",
            "protected": True,
        }
    ]
    (repo / ".claude-governance" / "policy.json").write_text(json.dumps(policy), encoding="utf-8")

    proc = run_cli("lint", "--repo", str(repo))

    assert proc.returncode == 1
    report = json.loads(proc.stdout)
    rules = {finding["rule"] for finding in report["findings"]}
    assert "ROOT_LOCAL_DOC_CONFLICT" in rules
    assert "MISSING_LOCAL_DOC" not in rules
    assert report["summary"]["detected_sensitive_dirs"] == [
        {"id": "payments", "dir": "src/payments", "local_doc": "AGENTS.md"}
    ]

    standalone = subprocess.run(
        [sys.executable, "scripts/claude_md_lint.py"],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert standalone.returncode == 1, standalone.stdout + standalone.stderr
    standalone_report = json.loads(standalone.stdout)
    assert any(finding["rule"] == "ROOT_LOCAL_DOC_CONFLICT" for finding in standalone_report["findings"])


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
    (repo / "AGENTS.md").write_text("# Project Overview\n\n@docs/long.md\n", encoding="utf-8")
    (repo / ".claude" / "settings.json").write_text(json.dumps({"hooks": {}}), encoding="utf-8")

    dry = run_cli("autofix", "--repo", str(repo), "--dry-run")
    assert dry.returncode == 0, dry.stdout + dry.stderr
    assert not (repo / "src" / "auth" / "AGENTS.md").exists()

    applied = run_cli("autofix", "--repo", str(repo), "--apply")
    assert applied.returncode == 0, applied.stdout + applied.stderr
    assert (repo / "src" / "auth" / "AGENTS.md").exists()
    assert "@docs/long.md" not in (repo / "AGENTS.md").read_text(encoding="utf-8")
    settings = json.loads((repo / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert "PreToolUse" in settings["hooks"]
    assert "PostToolUse" in settings["hooks"]


def test_codeup_init_does_not_create_github_actions(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "codeup")
    proc = run_cli("init", "--repo", str(repo), "--preset", "enterprise-java-codeup", "--ci", "codeup", "--config-change-mode", "warn", "--yes")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert not (repo / ".github" / "workflows" / "claude-md-governance.yml").exists()
    assert (repo / "ci" / "codeup" / "claude-md-governance-step.yml").exists()
    assert (repo / "docs" / "ci" / "codeup-claude-md-governance.md").exists()
    policy = json.loads((repo / ".claude-governance" / "policy.json").read_text(encoding="utf-8"))
    assert policy["ci"]["provider"] == "codeup"

    step = (repo / "ci" / "codeup" / "claude-md-governance-step.yml").read_text(encoding="utf-8")
    assert "python scripts/claude_md_lint.py" in step
    assert "python scripts/verify_claude_governance.py" in step

    verify = run_cli("verify", "--repo", str(repo))
    assert verify.returncode == 0, verify.stdout + verify.stderr
    assert "PASS: Codeup CI instructions exist" in verify.stdout


def test_gitlab_init_installs_pipeline_and_verifies(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "gitlab")
    proc = run_cli("init", "--repo", str(repo), "--preset", "generic", "--ci", "gitlab", "--yes")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert (repo / ".gitlab-ci.yml").exists()
    assert (repo / "docs" / "ci" / "gitlab-claude-md-governance.md").exists()
    assert not (repo / ".github" / "workflows" / "claude-md-governance.yml").exists()
    policy = json.loads((repo / ".claude-governance" / "policy.json").read_text(encoding="utf-8"))
    assert policy["ci"]["provider"] == "gitlab"

    verify = run_cli("verify", "--repo", str(repo))
    assert verify.returncode == 0, verify.stdout + verify.stderr
    assert "PASS: GitLab CI pipeline exists" in verify.stdout


def test_gitlab_pipeline_rules_require_merge_request_and_governance_changes(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "gitlab-rules")
    proc = run_cli("init", "--repo", str(repo), "--preset", "generic", "--ci", "gitlab", "--yes", "--skip-verify")
    assert proc.returncode == 0, proc.stdout + proc.stderr

    pipeline = (repo / ".gitlab-ci.yml").read_text(encoding="utf-8")
    assert "    - if: '$CI_PIPELINE_SOURCE == \"merge_request_event\"'\n      changes:\n" in pipeline
    assert "    - if: '$CI_PIPELINE_SOURCE == \"merge_request_event\"'\n  script:\n" not in pipeline
    assert '        - ".claude-governance/**/*"' in pipeline
    assert '        - "scripts/verify_claude_governance.py"' in pipeline


def test_installed_verify_script_validates_policy_without_package_import(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "standalone-verify")
    proc = run_cli("init", "--repo", str(repo), "--preset", "generic", "--ci", "none", "--yes", "--skip-verify")
    assert proc.returncode == 0, proc.stdout + proc.stderr

    policy_path = repo / ".claude-governance" / "policy.json"
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    policy["hooks"]["config_change_mode"] = "invalid"
    policy_path.write_text(json.dumps(policy), encoding="utf-8")

    verify = subprocess.run(
        [sys.executable, "-S", "scripts/verify_claude_governance.py"],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert verify.returncode == 1
    output = verify.stdout + verify.stderr
    assert "policy schema validates" in output
    assert "hooks.config_change_mode must be one of: block, warn, off" in output


def test_installed_verify_script_allows_parallel_runs(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "parallel-verify")
    proc = run_cli("init", "--repo", str(repo), "--preset", "generic", "--ci", "none", "--yes", "--skip-verify")
    assert proc.returncode == 0, proc.stdout + proc.stderr

    procs = [
        subprocess.Popen(
            [sys.executable, "scripts/verify_claude_governance.py"],
            cwd=repo,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        for _ in range(2)
    ]
    results = [proc.communicate(timeout=30) for proc in procs]

    for proc, (stdout, stderr) in zip(procs, results):
        assert proc.returncode == 0, stdout + stderr
        assert "Governance verification passed." in stdout
    assert not list((repo / "scripts").glob(".verify_allowlist_*.py"))


def test_installed_lint_script_validates_policy_without_package_import(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "standalone-lint")
    proc = run_cli("init", "--repo", str(repo), "--preset", "generic", "--ci", "none", "--yes", "--skip-verify")
    assert proc.returncode == 0, proc.stdout + proc.stderr

    policy_path = repo / ".claude-governance" / "policy.json"
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    policy["root_doc"]["max_lines"] = True
    policy["required_sections"] = [{"name": "", "aliases": [""], "severity": "fatal", "deduction": False}]
    policy["ci"] = {"provider": "travis"}
    policy["behavior_tests"] = {"enabled_by_default": "yes", "case_file": ""}
    policy_path.write_text(json.dumps(policy), encoding="utf-8")

    lint = subprocess.run(
        [sys.executable, "-S", "scripts/claude_md_lint.py", "--policy", ".claude-governance/policy.json", "--quiet"],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert lint.returncode == 2
    output = lint.stdout + lint.stderr
    assert "root_doc.max_lines must be a non-negative integer" in output
    assert "required_sections[0].name must be a non-empty string" in output
    assert "ci.provider must be one of: auto, github, gitlab, jenkins, buildkite, codeup, none" in output
    assert "behavior_tests.enabled_by_default must be a boolean" in output


def test_jenkins_init_installs_pipeline_and_verifies(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "jenkins")
    proc = run_cli("init", "--repo", str(repo), "--preset", "generic", "--ci", "jenkins", "--yes")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert (repo / "Jenkinsfile").exists()
    assert (repo / "docs" / "ci" / "jenkins-claude-md-governance.md").exists()
    assert not (repo / ".github" / "workflows" / "claude-md-governance.yml").exists()
    assert not (repo / ".gitlab-ci.yml").exists()
    policy = json.loads((repo / ".claude-governance" / "policy.json").read_text(encoding="utf-8"))
    assert policy["ci"]["provider"] == "jenkins"

    verify = run_cli("verify", "--repo", str(repo))
    assert verify.returncode == 0, verify.stdout + verify.stderr
    assert "PASS: Jenkins pipeline exists" in verify.stdout


def test_jenkins_pipeline_requires_change_request_and_governance_changes(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "jenkins-rules")
    proc = run_cli("init", "--repo", str(repo), "--preset", "generic", "--ci", "jenkins", "--yes", "--skip-verify")
    assert proc.returncode == 0, proc.stdout + proc.stderr

    pipeline = (repo / "Jenkinsfile").read_text(encoding="utf-8")
    assert "allOf {\n          changeRequest()\n          anyOf {" in pipeline
    assert "changeset '.claude-governance/**'" in pipeline
    assert "changeset 'scripts/verify_claude_governance.py'" in pipeline
    assert "anyOf {\n          changeRequest()\n          changeset" not in pipeline


def test_buildkite_init_installs_pipeline_and_verifies(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "buildkite")
    proc = run_cli("init", "--repo", str(repo), "--preset", "generic", "--ci", "buildkite", "--yes")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert (repo / ".buildkite" / "pipeline.yml").exists()
    assert (repo / "docs" / "ci" / "buildkite-claude-md-governance.md").exists()
    assert not (repo / ".github" / "workflows" / "claude-md-governance.yml").exists()
    assert not (repo / ".gitlab-ci.yml").exists()
    assert not (repo / "Jenkinsfile").exists()
    policy = json.loads((repo / ".claude-governance" / "policy.json").read_text(encoding="utf-8"))
    assert policy["ci"]["provider"] == "buildkite"
    pipeline = (repo / ".buildkite" / "pipeline.yml").read_text(encoding="utf-8")
    assert "python scripts/claude_md_lint.py" in pipeline
    assert "python scripts/verify_claude_governance.py" in pipeline
    assert '".claude-governance/score.json"' in pipeline

    verify = run_cli("verify", "--repo", str(repo))
    assert verify.returncode == 0, verify.stdout + verify.stderr
    assert "PASS: Buildkite pipeline exists" in verify.stdout


def test_documented_good_example_fixtures_install_lint_and_verify(tmp_path: Path) -> None:
    cases = [
        (
            "generic-node-like",
            ("generic", "github", None),
            [".github/workflows/claude-md-governance.yml", "src/auth/AGENTS.md"],
            [],
        ),
        (
            "java-maven-like",
            ("java-maven", "none", None),
            ["src/main/java/example/order/AGENTS.md"],
            [".github/workflows/claude-md-governance.yml"],
        ),
        (
            "enterprise-java-codeup",
            ("enterprise-java-codeup", "codeup", "warn"),
            ["docs/ci/codeup-claude-md-governance.md", "src/main/java/example/payment/AGENTS.md"],
            [".github/workflows/claude-md-governance.yml"],
        ),
    ]
    for name, (preset, ci, config_mode), expected_paths, absent_paths in cases:
        repo = copy_example_fixture(tmp_path, name)
        args = ["init", "--repo", str(repo), "--preset", preset, "--ci", ci, "--yes"]
        if config_mode is not None:
            args.extend(["--config-change-mode", config_mode])
        init = run_cli(*args)
        assert init.returncode == 0, name + init.stdout + init.stderr
        score_file = repo / ".claude-governance" / "score.json"
        lint_proc = run_cli("lint", "--repo", str(repo), "--output", str(score_file), "--quiet")
        assert lint_proc.returncode == 0, name + lint_proc.stdout + lint_proc.stderr
        verify = run_cli("verify", "--repo", str(repo))
        assert verify.returncode == 0, name + verify.stdout + verify.stderr
        assert json.loads(score_file.read_text(encoding="utf-8"))["status"] == "pass"
        for expected in expected_paths:
            assert (repo / expected).exists(), f"{name} missing {expected}"
        for absent in absent_paths:
            assert not (repo / absent).exists(), f"{name} unexpectedly created {absent}"
        if config_mode is not None:
            policy = json.loads((repo / ".claude-governance" / "policy.json").read_text(encoding="utf-8"))
            assert policy["hooks"]["config_change_mode"] == config_mode


def test_documented_bad_example_fixture_fails_lint_and_verify(tmp_path: Path) -> None:
    repo = copy_example_fixture(tmp_path, "bad-claude-md")
    init = run_cli("init", "--repo", str(repo), "--preset", "generic", "--ci", "none", "--skip-verify", "--yes")
    assert init.returncode == 0, init.stdout + init.stderr

    score_file = repo / ".claude-governance" / "score.json"
    lint_proc = run_cli("lint", "--repo", str(repo), "--output", str(score_file), "--quiet")
    assert lint_proc.returncode == 1
    report = json.loads(score_file.read_text(encoding="utf-8"))
    rules = {finding["rule"] for finding in report["findings"]}
    assert "TOO_MANY_VAGUE_RULES" in rules

    verify = run_cli("verify", "--repo", str(repo))
    assert verify.returncode == 1
    assert "FAIL: static linter passes" in verify.stdout


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
    env["CLAUDE_GOVERNANCE_APPROVED_PATHS"] = ".claude/settings.json"
    allowed = run_cli("hook", "pre", cwd=repo, input_text=event, env=env)
    assert allowed.returncode == 0
    open_path = run_cli("hook", "pre", cwd=repo, input_text=json.dumps({"tool_input": {"file_path": "README.md"}}))
    assert open_path.returncode == 0

    nested_event = json.dumps(
        {"tool_input": {"edits": [{"file_path": "README.md"}, {"file_path": ".claude/settings.json"}]}}
    )
    nested_blocked = run_cli("hook", "pre", cwd=repo, input_text=nested_event)
    assert nested_blocked.returncode == 2
    assert "Blocked protected edit: .claude/settings.json" in nested_blocked.stderr
    nested_allowed = run_cli("hook", "pre", cwd=repo, input_text=nested_event, env=env)
    assert nested_allowed.returncode == 0


def test_installed_hook_guard_validates_policy_without_package_import(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "standalone-hook")
    proc = run_cli("init", "--repo", str(repo), "--preset", "generic", "--ci", "none", "--yes", "--skip-verify")
    assert proc.returncode == 0, proc.stdout + proc.stderr

    policy_path = repo / ".claude-governance" / "policy.json"
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    policy["hooks"]["config_change_mode"] = "invalid"
    policy_path.write_text(json.dumps(policy), encoding="utf-8")

    event = json.dumps({"tool_input": {"file_path": "README.md"}})
    hook = subprocess.run(
        [sys.executable, "-S", "scripts/claude_hook_guard.py", "pre"],
        cwd=repo,
        input=event,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert hook.returncode == 2
    output = hook.stdout + hook.stderr
    assert "Invalid policy file" in output
    assert "hooks.config_change_mode must be one of: block, warn, off" in output


def test_post_hook_runs_sensitive_checks_for_nested_paths(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "nested-post")
    assert run_cli("init", "--repo", str(repo), "--preset", "generic", "--ci", "none", "--yes").returncode == 0
    policy_path = repo / ".claude-governance" / "policy.json"
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    for item in policy["sensitive_paths"]:
        if item["id"] == "auth":
            item["required_tests"] = ["python scripts/check_auth.py"]
    policy_path.write_text(json.dumps(policy), encoding="utf-8")
    check_script = repo / "scripts" / "check_auth.py"
    check_script.write_text(
        "from pathlib import Path\nPath('.claude-governance/auth-check-ran').write_text('ok', encoding='utf-8')\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["CLAUDE_GOVERNANCE_RUN_TESTS"] = "1"
    env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")

    nested_event = json.dumps(
        {"tool_input": {"edits": [{"file_path": "README.md"}, {"file_path": "src/auth/service.py"}]}}
    )
    post = run_cli("hook", "post", cwd=repo, input_text=nested_event, env=env)

    assert post.returncode == 0, post.stdout + post.stderr
    assert (repo / ".claude-governance" / "auth-check-ran").read_text(encoding="utf-8") == "ok"


def test_post_hook_rejects_non_allowlisted_sensitive_check_without_execution(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "post-rejects-chained-command")
    assert run_cli("init", "--repo", str(repo), "--preset", "generic", "--ci", "none", "--yes").returncode == 0
    (repo / "src" / "auth").mkdir(parents=True, exist_ok=True)
    policy_path = repo / ".claude-governance" / "policy.json"
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    for item in policy["sensitive_paths"]:
        if item["id"] == "auth":
            item["required_tests"] = ["python scripts/malicious.py && python scripts/allowed.py"]
    policy_path.write_text(json.dumps(policy), encoding="utf-8")

    malicious = repo / "scripts" / "malicious.py"
    malicious.write_text(
        "from pathlib import Path\nPath('.claude-governance/malicious-ran').write_text('bad', encoding='utf-8')\n",
        encoding="utf-8",
    )
    allowed = repo / "scripts" / "allowed.py"
    allowed.write_text(
        "from pathlib import Path\nPath('.claude-governance/allowed-ran').write_text('bad', encoding='utf-8')\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["CLAUDE_GOVERNANCE_RUN_TESTS"] = "1"
    env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")

    event = json.dumps({"tool_input": {"file_path": "src/auth/service.py"}})
    post = run_cli("hook", "post", cwd=repo, input_text=event, env=env)

    assert post.returncode == 2
    assert "rejected non-allowlisted policy command" in post.stderr
    assert "Quality gate failed for hook event" in post.stderr
    assert not (repo / ".claude-governance" / "malicious-ran").exists()
    assert not (repo / ".claude-governance" / "allowed-ran").exists()


def test_post_hook_message_does_not_claim_rollback(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "post")
    assert run_cli("init", "--repo", str(repo), "--preset", "generic", "--ci", "none", "--yes").returncode == 0
    post = run_cli("hook", "post", cwd=repo, input_text=json.dumps({"tool_input": {"file_path": "AGENTS.md"}}))
    assert "rollback" not in (post.stdout + post.stderr).lower()


def test_generic_install_verify_passes(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "generic")
    proc = run_cli("init", "--repo", str(repo), "--preset", "generic", "--ci", "github", "--yes")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert (repo / ".github" / "workflows" / "claude-md-governance.yml").exists()
    verify = run_cli("verify", "--repo", str(repo))
    assert verify.returncode == 0, verify.stdout + verify.stderr
    assert "PASS: PostToolUse rejects non-allowlisted policy command without execution" in verify.stdout


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
    (repo / "AGENTS.md").write_text(("# Project Overview\n\n保持简洁。高质量。注重性能。\n") * 80, encoding="utf-8")
    proc = run_cli("lint", "--repo", str(repo), "--quiet")
    assert proc.returncode == 1


def test_eval_prompt_uses_policy_root_doc_and_static_report(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "eval")
    assert run_cli("init", "--repo", str(repo), "--preset", "generic", "--ci", "none", "--yes").returncode == 0
    (repo / ".claude-governance" / "score.json").write_text(json.dumps({"status": "pass", "score": 99}), encoding="utf-8")

    proc = run_cli("eval", "--repo", str(repo), "--static", ".claude-governance/score.json")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "POLICY_JSON" in proc.stdout
    assert "STATIC_REPORT_JSON" in proc.stdout
    assert "ROOT_INSTRUCTIONS (AGENTS.md)" in proc.stdout
    assert '"score": 99' in proc.stdout


def test_behavior_test_pass_and_fail_with_fake_claude(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "behavior")
    cases = repo / "cases.json"
    cases.write_text(
        json.dumps(
            [
                {"id": "ok", "prompt": "ok prompt", "expected_contains": ["allowed"], "forbidden_contains": ["blocked"]},
            ]
        ),
        encoding="utf-8",
    )
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    if os.name == "nt":
        fake = bin_dir / "claude.cmd"
        fake.write_text("@echo off\necho allowed response\nexit /b 0\n", encoding="utf-8")
    else:
        fake = bin_dir / "claude"
        fake.write_text("#!/bin/sh\necho allowed response\nexit 0\n", encoding="utf-8")
        fake.chmod(0o755)
    env = os.environ.copy()
    env["PATH"] = str(bin_dir)

    passed = run_cli("behavior-test", "--repo", str(repo), "--cases", "cases.json", env=env)
    assert passed.returncode == 0, passed.stdout + passed.stderr
    passed_payload = json.loads(passed.stdout)
    assert passed_payload["schema_version"] == 1
    assert passed_payload["status"] == "pass"
    assert passed_payload["evaluator"] == "claude-cli"
    assert passed_payload["case_file"] == "cases.json"
    assert passed_payload["case_count"] == 1
    assert passed_payload["summary"] == {"passed": 1, "failed": 0, "skipped": 0}
    assert passed_payload["failed"] is False
    assert passed_payload["reason"] is None
    assert passed_payload["results"][0]["status"] == "pass"

    cases.write_text(
        json.dumps(
            [
                {"id": "bad", "prompt": "bad prompt", "expected_contains": ["missing"], "forbidden_contains": []},
            ]
        ),
        encoding="utf-8",
    )
    failed = run_cli("behavior-test", "--repo", str(repo), "--cases", "cases.json", env=env)
    assert failed.returncode == 1
    payload = json.loads(failed.stdout)
    assert payload["status"] == "fail"
    assert payload["case_count"] == 1
    assert payload["summary"] == {"passed": 0, "failed": 1, "skipped": 0}
    assert payload["failed"] is True
    assert payload["results"][0]["status"] == "fail"
    assert payload["results"][0]["ok"] is False


def test_behavior_test_skip_has_stable_json_shape(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "behavior-skip")
    env = os.environ.copy()
    env["PATH"] = str(tmp_path / "missing-bin")

    proc = run_cli("behavior-test", "--repo", str(repo), "--cases", "cases.json", env=env)
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload == {
        "schema_version": 1,
        "status": "skipped",
        "evaluator": "claude-cli",
        "case_file": "cases.json",
        "case_count": 0,
        "summary": {"passed": 0, "failed": 0, "skipped": 0},
        "failed": False,
        "reason": "Claude CLI not found",
        "results": [],
    }


def test_behavior_test_deterministic_evaluator_passes_without_claude(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "behavior-deterministic")
    cases = repo / "cases.json"
    cases.write_text(
        json.dumps(
            [
                {
                    "id": "ok",
                    "prompt": "ignored in deterministic mode",
                    "deterministic_output": "BLOCK. approval required",
                    "expected_contains": ["BLOCK", "approval"],
                    "forbidden_contains": ["ALLOW"],
                }
            ]
        ),
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["PATH"] = str(tmp_path / "missing-bin")

    proc = run_cli("behavior-test", "--repo", str(repo), "--cases", "cases.json", "--evaluator", "deterministic", env=env)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["status"] == "pass"
    assert payload["evaluator"] == "deterministic"
    assert payload["summary"] == {"passed": 1, "failed": 0, "skipped": 0}
    assert payload["results"][0]["output_preview"] == "BLOCK. approval required"

    cases.write_text(
        json.dumps([{"id": "missing-output", "prompt": "x", "expected_contains": ["BLOCK"], "forbidden_contains": []}]),
        encoding="utf-8",
    )
    failed = run_cli("behavior-test", "--repo", str(repo), "--cases", "cases.json", "--evaluator", "deterministic", env=env)
    assert failed.returncode == 1
    failed_payload = json.loads(failed.stdout)
    assert failed_payload["status"] == "fail"
    assert failed_payload["evaluator"] == "deterministic"
    assert failed_payload["results"][0]["error"] == "deterministic_output is required for deterministic evaluator"


def test_installed_behavior_script_deterministic_uses_template_cases(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "installed-behavior-deterministic")
    init = run_cli("init", "--repo", str(repo), "--preset", "generic", "--ci", "none", "--yes", "--skip-verify")
    assert init.returncode == 0, init.stdout + init.stderr

    proc = subprocess.run(
        [
            sys.executable,
            str(repo / "scripts" / "run_ai_behavior_tests.py"),
            "--repo",
            str(repo),
            "--evaluator",
            "deterministic",
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert proc.returncode == 0, proc.stdout + proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["evaluator"] == "deterministic"
    assert payload["case_file"] == "tests/ai_behavior_cases.json"
    assert payload["summary"] == {"passed": 3, "failed": 0, "skipped": 0}


def test_behavior_test_missing_cases_fails_when_claude_exists(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "behavior-missing-cases")
    bin_dir = tmp_path / "bin-missing"
    bin_dir.mkdir()
    if os.name == "nt":
        fake = bin_dir / "claude.cmd"
        fake.write_text("@echo off\necho should-not-run\nexit /b 0\n", encoding="utf-8")
    else:
        fake = bin_dir / "claude"
        fake.write_text("#!/bin/sh\necho should-not-run\nexit 0\n", encoding="utf-8")
        fake.chmod(0o755)
    env = os.environ.copy()
    env["PATH"] = str(bin_dir)

    proc = run_cli("behavior-test", "--repo", str(repo), "--cases", "missing.json", env=env)
    assert proc.returncode == 1
    assert "Behavior case file not found" in proc.stderr


def test_policy_schema_reports_multiple_invalid_shapes() -> None:
    invalid = {
        "version": 0,
        "preset": "",
        "score_threshold": 101,
        "root_doc": {"path": "", "warn_lines": -1},
        "required_sections": [{"name": "", "aliases": [""], "severity": "note", "deduction": -1}, 42],
        "protected_paths": [""],
        "sensitive_paths": [{"path": "", "required_tests": [1], "protected": "yes"}, 1],
        "hooks": {"settings_path": "", "config_change_mode": "silent", "require_pretool_guard": "yes"},
        "ci": {"provider": "unknown"},
        "behavior_tests": {"enabled_by_default": "yes", "case_file": ""},
    }

    errors = validate_policy(invalid)
    assert "version must be a positive integer" in errors
    assert "preset must be a non-empty string" in errors
    assert "hooks.config_change_mode must be one of: block, warn, off" in errors
    assert "ci.provider must be one of: auto, github, gitlab, jenkins, buildkite, codeup, none" in errors


def test_policy_schema_rejects_container_shape_edges() -> None:
    invalid = {
        "version": 1,
        "preset": "generic",
        "root_agents": [],
        "root_claude": {"path": "CLAUDE.md", "warn_tokens": True},
        "required_sections": "Project Overview",
        "sensitive_paths": "src/auth/**",
        "hooks": [],
        "ci": "github",
        "behavior_tests": [],
    }

    errors = validate_policy(invalid)
    assert "root_agents must be an object" in errors
    assert "root_claude.warn_tokens must be a non-negative integer" in errors
    assert "required_sections must be an array" in errors
    assert "sensitive_paths must be an array" in errors
    assert "hooks must be an object" in errors
    assert "ci must be an object" in errors
    assert "behavior_tests must be an object" in errors
