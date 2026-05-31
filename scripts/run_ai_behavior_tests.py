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
from typing import List


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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    parser.add_argument("--cases", default="tests/ai_behavior_cases.json")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--require-claude", action="store_true")
    args = parser.parse_args()
    os.chdir(Path(args.repo).resolve())

    claude_cmd = shutil.which("claude")
    if claude_cmd is None:
        print(json.dumps({"status": "skipped", "reason": "Claude CLI not found", "results": []}, ensure_ascii=False))
        return 1 if args.require_claude else 0

    cases_path = Path(args.cases)
    if not cases_path.exists():
        print(f"Behavior case file not found: {cases_path}", file=sys.stderr)
        return 1
    cases = json.loads(cases_path.read_text(encoding="utf-8"))
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
            print(
                json.dumps(
                    {
                        "status": "skipped",
                        "reason": "Claude CLI is installed but not logged in",
                        "results": [
                            {
                                "id": case.get("id"),
                                "returncode": proc.returncode,
                                "output_preview": output[:2000],
                            }
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 1 if args.require_claude else 0
        ok = proc.returncode == 0 and contains_all(output, case.get("expected_contains", [])) and not contains_any(output, case.get("forbidden_contains", []))
        results.append({
            "id": case.get("id"),
            "ok": ok,
            "returncode": proc.returncode,
            "expected_contains": case.get("expected_contains", []),
            "forbidden_contains": case.get("forbidden_contains", []),
            "output_preview": output[:2000],
        })
        failed = failed or not ok
    print(json.dumps({"status": "fail" if failed else "pass", "failed": failed, "results": results}, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
