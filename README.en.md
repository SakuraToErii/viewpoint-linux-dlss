# Viewpoint Linux DLSS patch (unofficial)

[中文](README.md) · [Agent installation guide](docs/AGENT_INSTALL.md) · [Agent rules](AGENTS.md) · [Validation](docs/VALIDATION.md)

Adds native Linux **DLSS Super Resolution / DLAA** and **2× DLSS Frame Generation**
to Project Viewpoint for Project Zomboid. It preserves the `Viewpoint` mod ID and
existing dependency declarations. This project is independent of the Viewpoint
authors, The Indie Stone and NVIDIA.

This is a source and local-build repository. Build against your own installed
original Viewpoint JAR. It contains no upstream mod, complete decompiled upstream
source files, patched JAR, game assets or NVIDIA binaries.

## Verified scope

| Component | Status |
| --- | --- |
| Linux OpenGL/Vulkan FD image sharing | Passed on RTX 4060 Laptop / NVIDIA 615.78.08 |
| DLSS Super Resolution / DLAA interface | Implemented; Super Resolution GPU fixture passed |
| One generated frame per rendered frame | Moving-object midpoint test passed alongside Super Resolution |
| Actual game | User confirmed operation; logs show 2560×1600 output with 1715×1072 guides |
| FSR/XeSS backends, multi-frame generation, ray reconstruction | Not implemented |
| Broad hardware coverage, long sessions, measured FPS and latency | Not verified |

**Supported input: Viewpoint 0.1.6.1, PZ 42.21.0, Linux x86-64, Java 25.**
Original JAR SHA-256:
`096bd37d63cb699ac95e9e7ea5245a1b9b5ff08c5161db35f6733b1d1c42b064`.
Builds stop on a different fingerprint. Do not bypass the guard for an update.

## Install through an agent

Give your agent the repository link and this prompt:

> Read AGENTS.md and docs/AGENT_INSTALL.md completely, inspect my environment, then install this Linux compatibility patch. Preserve mod IDs, dependencies, saves and existing launch options. You may inspect and build first. Stop and tell me when game exit or system changes are required, or if a version does not match. Keep rollback backups and distinguish offline checks, GPU fixtures and actual game validation in your report.

The guide covers discovery, build, staged tests, installation, approval prompts and
rollback. An agent must not infer game-exit confirmation or edit ZombieBuddy's
approval records.

## Manual build and installation

Install the native Linux game, ZombieBuddy and Viewpoint through Steam first.
Prerequisites: Python 3.12+, `g++`, NVIDIA driver, Vulkan loader, and the bundled
Java 25 runtime. The build downloads hash-pinned CFR, ECJ, Vulkan Headers and
NVIDIA SDK dependencies. Their own terms apply; see [NOTICE.md](NOTICE.md).

After cloning, run from the repository root. Adjust these default-layout examples
to your actual Steam library:

```bash
PZ_GAME_DIR="$HOME/.steam/steam/steamapps/common/ProjectZomboid/projectzomboid"
VIEWPOINT_JAR="$HOME/.steam/steam/steamapps/workshop/content/108600/3809306528/mods/Viewpoint/42/media/java/client/Viewpoint.jar"

python3 scripts/build.py --game-dir "$PZ_GAME_DIR" --viewpoint-jar "$VIEWPOINT_JAR"
```

This builds and checks offline under `_work/` and `dist/`. It does not install or
launch the game. If already patched, build from a supported original backup;
the build input and installation target may be different paths.

**Exit running games first**, then test the staging files:

```bash
python3 scripts/test_gpu.py --kind fg --width 1280 --height 720 --game-exited
```

The hidden-context fixture reads no saves. It checks SR/FG coexistence and real
midpoint interpolation of a moving object; copied current frames do not count.
After it passes, preview installation:

```bash
python3 scripts/manage.py install --viewpoint-jar "$VIEWPOINT_JAR"
```

Check the paths, confirm game exit, then apply:

```bash
python3 scripts/manage.py install --viewpoint-jar "$VIEWPOINT_JAR" --apply --game-exited
```

The installer backs up the existing JAR/libraries and replaces files atomically.
It does not edit mod metadata, mod IDs, saves, Steam launch options or approval
records. Start normally and review any changed-JAR approval prompt yourself.
Enable DLSS and frame generation in Viewpoint, then inspect real scenes, HUD,
ghosting and pacing.

Initialization markers:

```text
[Viewpoint Linux DLSS] NGX initialized: ...
[Viewpoint Linux DLSSG] NGX initialized: ..., 2x
```

These markers alone do not prove correct reconstruction, doubled achieved FPS or
reduced latency.

## Rollback

Exit the game, preview, then restore:

```bash
python3 scripts/manage.py rollback
python3 scripts/manage.py rollback --apply --game-exited
```

Backups and machine-specific metadata stay in ignored `state/`. Rollback refuses
files changed since installation, so it will not silently overwrite a Steam
update or another patch. Retain `state/` for automatic recovery.

## Known limitations

- Tested on one RTX 4060 Laptop and NVIDIA 615.78.08. NGX still checks the GPU and
  driver for frame-generation support.
- Repeated complete NGX/Vulkan context recreation retained about three process
  FDs per cycle, including two eventfds. The cause is unresolved. Do not call this
  leak-free; restart the game when testing many setting changes.
- End-to-end latency, displayed game FPS and all scene artifacts are unmeasured.
  2× describes the insertion mode, not a measured performance guarantee.
- Workshop updates can overwrite the patch. A changed upstream version needs a
  reviewed rebase and fresh validation, rather than a disabled hash guard.
- New code was developed with AI assistance and needs normal review and more
  hardware/game coverage.

## Source, contributions and license

New adapter code and tools use [MIT](LICENSE). Upstream mod, game and vendor SDK
rights remain separate. Locally generated patched mod JARs must not be published
as this repository's MIT source artifacts. Reproducible issues, hardware results,
lifecycle fixes and compatibility improvements are welcome. Redact personal
paths, names and other private data from logs.

Original projects: [Viewpoint Workshop](https://steamcommunity.com/sharedfiles/filedetails/?id=3809306528),
[ZombieBuddy](https://github.com/zed-0xff/ZombieBuddy).
