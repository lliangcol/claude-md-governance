# Demo

Demo fixtures are under `examples/`. Each fixture is intentionally small enough
to copy into a temporary directory and validate from a local checkout.

## Assets

The public README uses generated visual assets under `docs/assets/`:

- `demo-governance-flow.gif`: `init` -> `verify` -> bad repo failure.
- `quickstart-pass.png`: successful install and verification output.
- `bad-repo-fail.png`: deterministic failure from the bad fixture.
- `score-output.png`: score/report excerpt.
- `social-preview.png`: GitHub social preview image.

These images are generated from deterministic transcript text. They do not
contain private paths, shell history, auth state, or real user secrets.

## Reproduce the Demo

Run:

```bash
bash scripts/demo_generic.sh
bash scripts/demo_enterprise_java_codeup.sh
bash scripts/demo_bad_repo.sh
```

Expected behavior:

- Generic demo copies `examples/generic-node-like`, runs `init`, `lint`, and
  `verify`, installs `.github/workflows/claude-md-governance.yml`, and prints
  `score=<n> PASS ...`.
- enterprise-java-codeup demo copies `examples/enterprise-java-codeup`, runs `init`, `lint`,
  and `verify`, installs Codeup documentation, does not install GitHub Actions,
  keeps `ConfigChange` in warning-only mode, and prints `score=<n> PASS ...`.
- Bad repo demo copies `examples/bad-claude-md`, runs `init --skip-verify`,
  then proves both `lint` and `verify` fail. It still writes
  `.claude-governance/score.json` and prints `score=<n> PASS ...` when the
  expected failure is detected.

## Minimal Release Demo Flow

Use this shorter script when recording the README GIF or a 60-90 second launch
video:

```bash
python -m pip install -e ".[test]"
claude-md-governance init --repo <tmp-repo> --preset generic --ci github --yes
claude-md-governance verify --repo <tmp-repo>
python -m claude_md_governance lint --repo examples/bad-claude-md --quiet
```

Expected highlights:

- `init` installs `CLAUDE.md`, `.claude-governance/policy.json`,
  `.claude/settings.json`, local scripts, and GitHub Actions.
- `verify` prints `Governance verification passed.` after checking hooks,
  static lint, ConfigChange behavior, and mutation failure detection.
- The bad fixture fails lint/verify, proving the checks are deterministic.

Fixture-level smoke tests:

```bash
bash examples/generic-node-like/scripts/smoke.sh
bash examples/java-maven-like/scripts/smoke.sh
bash examples/enterprise-java-codeup/scripts/smoke.sh
bash examples/bad-claude-md/scripts/smoke.sh
```
