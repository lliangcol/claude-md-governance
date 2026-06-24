"""Command line entry point for repository instruction governance."""
from __future__ import annotations

import argparse
import shlex
import sys
from collections.abc import Sequence
from pathlib import Path

from . import __version__


def _dispatch(module_name: str, argv: Sequence[str]) -> int:
    module = __import__(f"claude_md_governance.{module_name}", fromlist=["main"])
    old_argv = sys.argv[:]
    try:
        sys.argv = [f"codex-md-governance {module_name}", *argv]
        return int(module.main())
    finally:
        sys.argv = old_argv


def _has_option(argv: Sequence[str], name: str) -> bool:
    return any(arg == name or arg.startswith(f"{name}=") for arg in argv)


def _print_eval_command(argv: Sequence[str]) -> int:
    prompt_args = [arg for arg in argv if arg != "--print-command"]
    if not _has_option(prompt_args, "--bare"):
        prompt_args.append("--bare")
    inner = ["codex-md-governance", "eval", *prompt_args]
    print(f"claude --bare -p \"$({' '.join(shlex.quote(arg) for arg in inner)})\"")
    return 0


def _default_prog() -> str:
    name = Path(sys.argv[0]).name
    if name in {"codex-md-governance", "codex-md-governance.exe", "claude-md-governance", "claude-md-governance.exe"}:
        return name
    return "codex-md-governance"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=_default_prog(),
        description="Install, lint, repair, and verify AGENTS.md / CLAUDE.md governance.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    init_cmd = sub.add_parser("init", help="Install governance templates into a target repository.")
    init_cmd.add_argument("--repo", default=".")
    init_cmd.add_argument("--yes", action="store_true", help="Run non-interactively.")
    init_cmd.add_argument("--force", action="store_true", help="Overwrite managed files after backup.")
    init_cmd.add_argument("--skip-verify", action="store_true")
    init_cmd.add_argument("--preset", default="generic", choices=["auto", "generic", "java-maven", "enterprise-java-codeup"])
    init_cmd.add_argument("--ci", default="auto", choices=["auto", "github", "codeup", "none"])
    init_cmd.add_argument("--config-change-mode", default="auto", choices=["auto", "block", "warn", "off"])

    lint_cmd = sub.add_parser("lint", help="Run deterministic root instruction scoring.")
    lint_cmd.add_argument("--repo", default=".")
    lint_cmd.add_argument("--policy", default=".claude-governance/policy.json")
    lint_cmd.add_argument("--root-doc", default=None)
    lint_cmd.add_argument("--claude", default=None)
    lint_cmd.add_argument("--output", default=None)
    lint_cmd.add_argument("--fail-under", type=int, default=None)
    lint_cmd.add_argument("--quiet", action="store_true")

    autofix_cmd = sub.add_parser("autofix", help="Apply conservative repair actions.")
    autofix_cmd.add_argument("--repo", default=".")
    autofix_cmd.add_argument("--policy", default=".claude-governance/policy.json")
    autofix_cmd.add_argument("--dry-run", action="store_true")
    autofix_cmd.add_argument("--apply", action="store_true", help="Apply repairs. This is the default unless --dry-run is set.")

    hook_cmd = sub.add_parser("hook", help="Run hook guard mode.")
    hook_cmd.add_argument("mode", choices=["pre", "post", "config"])

    verify_cmd = sub.add_parser("verify", help="Verify an installed governance setup.")
    verify_cmd.add_argument("--repo", default=".")
    verify_cmd.add_argument("--with-claude", action="store_true")
    verify_cmd.add_argument("--require-claude", action="store_true")

    eval_cmd = sub.add_parser("eval", help="Build a copyable LLM evaluation prompt.")
    eval_cmd.add_argument("--bare", action="store_true", help="Print the prompt directly.")
    eval_cmd.add_argument("--repo", default=".")
    eval_cmd.add_argument("--print-command", action="store_true")
    eval_cmd.add_argument("--policy", default=".claude-governance/policy.json")
    eval_cmd.add_argument("--static", default=".claude-governance/score.json")
    eval_cmd.add_argument("--claude", default=None)

    behavior_cmd = sub.add_parser("behavior-test", help="Run optional Claude CLI behavior tests.")
    behavior_cmd.add_argument("--repo", default=".")
    behavior_cmd.add_argument("--cases", default="tests/ai_behavior_cases.json")
    behavior_cmd.add_argument("--timeout", type=int, default=120)
    behavior_cmd.add_argument("--require-claude", action="store_true")

    doctor_cmd = sub.add_parser("doctor", help="Alias for verify.")
    doctor_cmd.add_argument("--repo", default=".")
    doctor_cmd.add_argument("--with-claude", action="store_true")
    doctor_cmd.add_argument("--require-claude", action="store_true")
    doctor_cmd.add_argument("--explain", action="store_true")

    policy_cmd = sub.add_parser("policy", help="Validate or migrate policy JSON.")
    policy_sub = policy_cmd.add_subparsers(dest="policy_command", required=True)
    policy_validate = policy_sub.add_parser("validate", help="Validate policy JSON.")
    policy_validate.add_argument("--repo", default=".")
    policy_validate.add_argument("--policy", default=".claude-governance/policy.json")
    policy_migrate = policy_sub.add_parser("migrate", help="Conservatively migrate policy JSON.")
    policy_migrate.add_argument("--repo", default=".")
    policy_migrate.add_argument("--policy", default=".claude-governance/policy.json")
    policy_migrate.add_argument("--write", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args, unknown = parser.parse_known_args(argv)
    command = args.command
    forwarded = list(argv if argv is not None else sys.argv[1:])
    forwarded = forwarded[1:]

    if command == "init":
        if not _has_option(forwarded, "--preset"):
            forwarded.extend(["--preset", args.preset])
        if not _has_option(forwarded, "--ci"):
            forwarded.extend(["--ci", args.ci])
        if not _has_option(forwarded, "--config-change-mode"):
            forwarded.extend(["--config-change-mode", args.config_change_mode])
        return _dispatch("installer", forwarded)
    if command == "lint":
        return _dispatch("lint", forwarded)
    if command == "autofix":
        forwarded = [arg for arg in forwarded if arg != "--apply"]
        return _dispatch("autofix", forwarded)
    if command == "hook":
        return _dispatch("hook_guard", forwarded)
    if command == "verify":
        return _dispatch("verify", forwarded)
    if command == "eval":
        if args.print_command:
            return _print_eval_command(forwarded)
        forwarded = [arg for arg in forwarded if arg not in {"--bare", "--print-command"}]
        return _dispatch("eval_prompt", forwarded)
    if command == "behavior-test":
        return _dispatch("behavior", forwarded)
    if command == "doctor":
        return _dispatch("verify", forwarded)
    if command == "policy":
        return _dispatch("policy_cli", forwarded)
    parser.error(f"unknown command: {command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
