#!/usr/bin/env bash
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
root="$(cd "$repo/../.." && pwd)"
tmp="$(mktemp -d)"
cp -R "$repo/." "$tmp/"
rm -rf "$tmp/scripts"

run_gov() {
  if command -v claude-md-governance >/dev/null 2>&1; then
    claude-md-governance "$@"
  elif command -v python3 >/dev/null 2>&1; then
    PYTHONPATH="$root/src${PYTHONPATH:+:$PYTHONPATH}" python3 -m claude_md_governance.cli "$@"
  else
    PYTHONPATH="$root/src${PYTHONPATH:+:$PYTHONPATH}" python -m claude_md_governance.cli "$@"
  fi
}

score_file="$tmp/.claude-governance/score.json"
if command -v python3 >/dev/null 2>&1; then
  py=python3
else
  py=python
fi
run_gov init --repo "$tmp" --preset generic --ci none --skip-verify --yes
if run_gov lint --repo "$tmp" --output "$score_file" --quiet; then
  echo "FAIL bad-claude-md smoke unexpectedly passed lint"
  exit 1
fi
if run_gov verify --repo "$tmp"; then
  echo "FAIL bad-claude-md smoke unexpectedly passed verify"
  exit 1
fi
score="$("$py" -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["score"])' "$score_file")"
echo "score=$score PASS bad-claude-md smoke failed lint and verify as expected: $tmp"
