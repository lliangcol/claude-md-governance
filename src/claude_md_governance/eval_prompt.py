#!/usr/bin/env python3
"""Build an isolated LLM evaluation prompt for repository instruction quality."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


def read(path: str) -> str:
    p = Path(path)
    return p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""


def root_doc_from_policy(policy_path: str) -> str:
    try:
        policy = json.loads(read(policy_path))
    except Exception:
        return "CLAUDE.md"
    for key in ("root_doc", "root_agents", "root_claude"):
        value = policy.get(key)
        if isinstance(value, dict) and value.get("path"):
            return str(value["path"])
    return "CLAUDE.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    parser.add_argument("--policy", default=".claude-governance/policy.json")
    parser.add_argument("--static", default=".claude-governance/score.json")
    parser.add_argument("--claude", default=None, help="Legacy root instruction path override.")
    parser.add_argument("--root-doc", default=None)
    args = parser.parse_args()
    os.chdir(Path(args.repo).resolve())
    root_doc = args.root_doc or args.claude or root_doc_from_policy(args.policy)

    prompt = f"""
You are an independent repository-instruction governance evaluator. Evaluate only the content below. Do not assume unstated repository facts. Return JSON only.

Scoring dimensions:
- context_budget: concise, under configured line/token budgets
- project_orientation: product, stack, and new-code placement are clear
- do_not_introduce: banned dependencies/patterns are explicit and evidence-based
- executable_rules: rules are measurable, not vague slogans
- context_routing: long docs are linked by path, not always imported
- local_rules: sensitive modules have local AGENTS.md or CLAUDE.md rules
- hooks_and_quality_gates: deterministic enforcement exists
- memory_and_working_style: stable preferences are short and useful

Return this JSON shape exactly:
{{
  "score": 0,
  "grade": "A|B|C|D|F",
  "hard_fail": false,
  "summary": "one paragraph",
  "findings": [{{"id": "STRING", "severity": "error|warning|info", "evidence": "STRING", "why_it_matters": "STRING", "suggested_rewrite": "STRING"}}],
  "autofix_plan": [{{"action": "STRING", "target": "STRING", "safe_to_apply": true, "needs_human_input": "STRING_OR_EMPTY"}}]
}}

POLICY_JSON:
```json
{read(args.policy)}
```

STATIC_REPORT_JSON:
```json
{read(args.static)}
```

ROOT_INSTRUCTIONS ({root_doc}):
```md
{read(root_doc)}
```
""".strip()
    print(prompt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
