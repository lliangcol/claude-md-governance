"""Policy inspection and migration commands."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .hook_guard import command_allowlist_report
from .policy import PolicyValidationError, load_policy_file, migrate_policy, resolve_policy_path, validate_policy


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    validate_cmd = sub.add_parser("validate", help="Validate policy JSON and print machine-readable status.")
    validate_cmd.add_argument("--repo", default=".")
    validate_cmd.add_argument("--policy", default=".claude-governance/policy.json")

    migrate_cmd = sub.add_parser("migrate", help="Apply conservative policy shape migrations.")
    migrate_cmd.add_argument("--repo", default=".")
    migrate_cmd.add_argument("--policy", default=".claude-governance/policy.json")
    migrate_cmd.add_argument("--write", action="store_true", help="Write migrated policy in place.")

    sub.add_parser("command-allowlist", help="Print the hook policy command allowlist as JSON.")

    args = parser.parse_args()

    if args.command == "command-allowlist":
        print(json.dumps(command_allowlist_report(), ensure_ascii=False, indent=2))
        return 0

    repo = Path(args.repo).resolve()
    policy_path = resolve_policy_path(repo, args.policy)

    if args.command == "validate":
        try:
            load_policy_file(policy_path)
        except PolicyValidationError as exc:
            print(json.dumps({"status": "fail", "errors": list(exc.errors)}, ensure_ascii=False, indent=2))
            return 1
        print(json.dumps({"status": "pass", "errors": []}, ensure_ascii=False, indent=2))
        return 0

    if args.command == "migrate":
        try:
            policy = load_policy_file(policy_path)
        except PolicyValidationError:
            if not policy_path.exists():
                print(json.dumps({"status": "fail", "errors": ["policy file is missing"]}, ensure_ascii=False, indent=2))
                return 1
            try:
                policy = json.loads(policy_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                print(
                    json.dumps(
                        {"status": "fail", "errors": [f"invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"]},
                        ensure_ascii=False,
                        indent=2,
                    )
                )
                return 1
        migrated, actions = migrate_policy(policy)
        errors = validate_policy(migrated)
        if errors:
            print(json.dumps({"status": "fail", "actions": actions, "errors": errors}, ensure_ascii=False, indent=2))
            return 1
        if args.write and actions:
            policy_path.write_text(json.dumps(migrated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(
            json.dumps(
                {"status": "pass", "changed": bool(actions), "written": bool(args.write and actions), "actions": actions},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    print(f"unknown policy command: {args.command}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
