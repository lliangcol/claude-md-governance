#!/usr/bin/env python3
"""Optional isolated LLM evaluator for CLAUDE.md using Claude CLI --bare."""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=".claude-governance/llm-report.json")
    parser.add_argument("--require-claude", action="store_true")
    args = parser.parse_args()

    claude_cmd = shutil.which("claude")
    if claude_cmd is None:
        print("Claude CLI not found; skipping LLM evaluation.")
        return 1 if args.require_claude else 0

    prompt_proc = subprocess.run([sys.executable, "scripts/build_claude_md_eval_prompt.py"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if prompt_proc.returncode != 0:
        print(prompt_proc.stderr, file=sys.stderr)
        return prompt_proc.returncode

    proc = subprocess.run([claude_cmd, "--bare", "-p", prompt_proc.stdout], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(proc.stdout, encoding="utf-8")
    if proc.stderr:
        print(proc.stderr, file=sys.stderr)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
