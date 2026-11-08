# Contributing

Please read `AGENTS.md`, `NOTICE.md`, and `docs/VALIDATION.md` first.
This is an experimental Linux compatibility layer, not an upstream Viewpoint fork.

- Keep original/decompiled upstream files, patched JARs, SDK binaries and machine
  state out of commits. Transform a supported local input during a build.
- Describe exact versions and reproduce failures with the staging fixture before
  suggesting changes to an installed game.
- Preserve Windows upstream behavior conceptually when proposing adoption by the
  original authors; this repository's replacement itself is Linux-only.
- Include appropriate offline and GPU evidence, noting what was not tested.
  New GPU tests must not run automatically while a user is playing a game.
- Record measurable interpolation results; do not infer a performance gain from
  successful API calls or an enabled setting.
- Redact personal paths and identifiers in shared logs. Small relevant excerpts
  are preferable to an unreviewed full game log.

Useful development commands:

```bash
python3 scripts/build.py --game-dir "$PZ_GAME_DIR" --viewpoint-jar "$ORIGINAL_VIEWPOINT_JAR"
python3 tests/test_installation.py
```

The installation test operates on disposable files under `_work/`; it does not
replace the actual game. GPU testing is separate and requires confirmed game exit.

Contributions to this repository's new code are under its MIT license. Do not
include material covered only by an upstream or vendor license.
