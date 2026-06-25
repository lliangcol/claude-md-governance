#!/usr/bin/env python3
"""Optional Claude CLI behavior regression tests.

Runs prompts through `claude --bare -p` and emits machine-readable JSON.
This script is optional because CI may not have Claude CLI credentials.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, List


SCHEMA_VERSION = 1
DEFAULT_EVALUATOR = "claude-cli"
DETERMINISTIC_EVALUATOR = "deterministic"
OUTPUT_PREVIEW_LIMIT = 2000


def contains_all(text: str, needles: List[str]) -> bool:
    t = text.lower()
    return all(str(n).lower() in t for n in needles)


def contains_any(text: str, needles: List[str]) -> bool:
    t = text.lower()
    return any(str(n).lower() in t for n in needles)


def auth_unavailable(output: str) -> bool:
    lowered = output.lower()
    return any(
        marker in lowered
        for marker in (
            "not logged in",
            "please run /login",
            "please login",
            "authentication required",
            "no claude account",
        )
    )


def result_status(ok: bool) -> str:
    return "pass" if ok else "fail"


def build_payload(
    *,
    status: str,
    evaluator: str,
    cases_path: Path,
    case_count: int,
    results: list[dict[str, Any]],
    reason: str | None = None,
) -> dict[str, Any]:
    passed = sum(1 for result in results if result.get("status") == "pass")
    failed_count = sum(1 for result in results if result.get("status") == "fail")
    skipped = case_count - passed - failed_count if status == "skipped" else 0
    if skipped < 0:
        skipped = 0
    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "evaluator": evaluator,
        "case_file": cases_path.as_posix(),
        "case_count": case_count,
        "summary": {"passed": passed, "failed": failed_count, "skipped": skipped},
        "failed": status == "fail",
        "reason": reason,
        "results": results,
    }


def print_payload(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def load_cases(cases_path: Path) -> list[dict[str, Any]] | None:
    if not cases_path.exists():
        print(f"Behavior case file not found: {cases_path}", file=sys.stderr)
        return None
    return json.loads(cases_path.read_text(encoding="utf-8"))


def case_result(case: dict[str, Any], output: str, *, returncode: int, error: str | None = None) -> dict[str, Any]:
    ok = (
        error is None
        and returncode == 0
        and contains_all(output, case.get("expected_contains", []))
        and not contains_any(output, case.get("forbidden_contains", []))
    )
    result = {
        "id": case.get("id"),
        "status": result_status(ok),
        "ok": ok,
        "returncode": returncode,
        "expected_contains": case.get("expected_contains", []),
        "forbidden_contains": case.get("forbidden_contains", []),
        "output_preview": output[:OUTPUT_PREVIEW_LIMIT],
    }
    if error is not None:
        result["error"] = error
    return result


def run_deterministic(cases_path: Path, cases: list[dict[str, Any]]) -> int:
    results = []
    for case in cases:
        if "deterministic_output" not in case:
            results.append(
                case_result(
                    case,
                    "",
                    returncode=2,
                    error="deterministic_output is required for deterministic evaluator",
                )
            )
            continue
        results.append(case_result(case, str(case.get("deterministic_output", "")), returncode=0))
    failed = any(not result["ok"] for result in results)
    print_payload(
        build_payload(
            status="fail" if failed else "pass",
            evaluator=DETERMINISTIC_EVALUATOR,
            cases_path=cases_path,
            case_count=len(cases),
            results=results,
        )
    )
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    parser.add_argument("--cases", default="tests/ai_behavior_cases.json")
    parser.add_argument("--evaluator", default=DEFAULT_EVALUATOR, choices=[DEFAULT_EVALUATOR, DETERMINISTIC_EVALUATOR])
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--require-claude", action="store_true")
    args = parser.parse_args()
    os.chdir(Path(args.repo).resolve())

    cases_path = Path(args.cases)
    if args.evaluator == DETERMINISTIC_EVALUATOR:
        cases = load_cases(cases_path)
        if cases is None:
            return 1
        return run_deterministic(cases_path, cases)

    claude_cmd = shutil.which("claude")
    if claude_cmd is None:
        print_payload(
            build_payload(
                status="skipped",
                evaluator=DEFAULT_EVALUATOR,
                cases_path=cases_path,
                case_count=0,
                reason="Claude CLI not found",
                results=[],
            )
        )
        return 1 if args.require_claude else 0

    cases = load_cases(cases_path)
    if cases is None:
        return 1
    results = []
    failed = False
    for case in cases:
        proc = subprocess.run(
            [claude_cmd, "--bare", "-p", case["prompt"]],
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=args.timeout,
        )
        output = proc.stdout + "\n" + proc.stderr
        if proc.returncode != 0 and auth_unavailable(output):
            print_payload(
                build_payload(
                    status="skipped",
                    evaluator=DEFAULT_EVALUATOR,
                    cases_path=cases_path,
                    case_count=len(cases),
                    reason="Claude CLI is installed but not logged in",
                    results=[
                        {
                            "id": case.get("id"),
                            "status": "skipped",
                            "ok": None,
                            "returncode": proc.returncode,
                            "output_preview": output[:OUTPUT_PREVIEW_LIMIT],
                        }
                    ],
                )
            )
            return 1 if args.require_claude else 0
        result = case_result(case, output, returncode=proc.returncode)
        results.append(result)
        failed = failed or not result["ok"]
    print_payload(
        build_payload(
            status="fail" if failed else "pass",
            evaluator=DEFAULT_EVALUATOR,
            cases_path=cases_path,
            case_count=len(cases),
            results=results,
        )
    )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
