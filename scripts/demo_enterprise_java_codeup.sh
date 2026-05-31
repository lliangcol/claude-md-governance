#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tmp="$(mktemp -d)"
cp -R "$root/examples/enterprise-java-codeup/." "$tmp/"

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

run_gov init --repo "$tmp" --preset enterprise-java-codeup --ci codeup --config-change-mode warn --yes
run_gov lint --repo "$tmp" --output "$score_file"
run_gov verify --repo "$tmp"
test ! -f "$tmp/.github/workflows/claude-md-governance.yml"
test -f "$tmp/docs/ci/codeup-claude-md-governance.md"
config_mode="$("$py" -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["hooks"]["config_change_mode"])' "$tmp/.claude-governance/policy.json")"
test "$config_mode" = "warn"
score="$("$py" -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["score"])' "$score_file")"
echo "score=$score PASS enterprise-java-codeup demo: $tmp"
