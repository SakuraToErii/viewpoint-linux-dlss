# Instructions for coding and installation agents

Read `docs/AGENT_INSTALL.md` completely before performing an installation.
Read `README.md` or `README.en.md` for scope and limitations.

## Boundaries

- This is an unofficial Linux x86-64 compatibility patch for the exact versions
  and original JAR fingerprint in `config/versions.json`.
- Preserve mod ID/name `Viewpoint`, its existing Workshop directory, dependencies,
  saves and user's launch options. Patch the internal JAR; do not create two
  simultaneously enabled mods with the same ID.
- The public repo contains our adapters and local transformation scripts only.
  Never commit or upload the original/patched Viewpoint JAR, full decompiled
  upstream files, game assets, vendor SDK files, private logs, credentials or
  local state. Keep `_work/`, `dist/`, `state/` and `vendor/` ignored.
- Do not edit mod approval records, use allow-all policies, or click approval
  dialogs for the user. Explain that a changed JAR requires user review.

## Running games and installation

- Read-only inspection and CPU builds may proceed while a game runs, using
  bounded resources. Do not replace active files or run GPU tests while the user
  is playing. Tell the user when game exit is required, then wait for confirmation.
- Check visible game processes as well; do not infer user confirmation from time.
- `manage.py` defaults to a dry run. Apply only within a user-authorized install,
  after confirmed game exit. Keep its backups and rollback metadata.
- Never disable hash guards to force an unsupported version. If upstream or an
  installed file changed, stop, explain the mismatch and inspect/rebase first.
- Do not update drivers, change GPU/system settings, switch game branches, edit
  desktop configuration or install root packages merely to hide a failure.

## Verification and reporting

- Build/offline checks do not establish GPU support. Run the staged GPU fixture
  before installation when user availability permits.
- The FG test must show actual midpoint interpolation; duplicate real frames do
  not count. Check simultaneous SR/FG and different guide/output resolutions.
- After installation, ask the user to launch normally, approve the changed JAR
  if prompted, then test scene movement, HUD, pacing, latency and artifacts.
- Distinguish compile success, offline ABI checks, GPU fixture success, log
  initialization, user's visual confirmation and measured FPS/latency.
- Report the known repeated-context FD-retention observation and other material
  limitations honestly. Do not claim the patch is official, broadly tested,
  leak-free or guaranteed to double achieved FPS.

## Development

- Keep all modifications scoped to the compatibility layer. Use pinned external
  dependencies and the supported user's JAR as local input.
- Run `python3 scripts/build.py ...`; this runs the meaningful offline checks.
  GPU tests require a separate explicit command and confirmed game exit.
- Never publish generated binaries under this repo's MIT license: they incorporate
  upstream/vendor material with separate terms. See `NOTICE.md`.
