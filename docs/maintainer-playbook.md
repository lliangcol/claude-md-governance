# Maintainer Playbook

## Reviewing a new rule

Ask:

1. Is the rule deterministic?
2. Is it project-specific or generic?
3. Can it produce false positives?
4. Does it have a suggested fix?
5. Should it be warning or hard fail?

## Reviewing hook changes

Check:

- No destructive commands by default.
- No network calls or data exfiltration.
- Exit code 2 used only for intentional blocking.
- ConfigChange behavior remains policy-driven.
- Protected paths include hook guard and policy file.

## Reviewing preset changes

Run an install test for that preset and inspect generated CLAUDE.md content for fabricated facts.
