# Demo

Demo fixtures are under `examples/`. Each fixture is intentionally small enough
to copy into a temporary directory and validate from a local checkout.

Run:

```bash
bash scripts/demo_generic.sh
bash scripts/demo_onm_agent_like.sh
bash scripts/demo_bad_repo.sh
```

Expected behavior:

- Generic demo copies `examples/generic-node-like`, runs `init`, `lint`, and
  `verify`, installs `.github/workflows/claude-md-governance.yml`, and prints
  `score=<n> PASS ...`.
- onm-agent-like demo copies `examples/onm-agent-like`, runs `init`, `lint`,
  and `verify`, installs Codeup documentation, does not install GitHub Actions,
  keeps `ConfigChange` in warning-only mode, and prints `score=<n> PASS ...`.
- Bad repo demo copies `examples/bad-claude-md`, runs `init --skip-verify`,
  then proves both `lint` and `verify` fail. It still writes
  `.claude-governance/score.json` and prints `score=<n> PASS ...` when the
  expected failure is detected.

Fixture-level smoke tests:

```bash
bash examples/generic-node-like/scripts/smoke.sh
bash examples/java-maven-like/scripts/smoke.sh
bash examples/onm-agent-like/scripts/smoke.sh
bash examples/bad-claude-md/scripts/smoke.sh
```
