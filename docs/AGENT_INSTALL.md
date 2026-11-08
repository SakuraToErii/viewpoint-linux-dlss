# Agent installation playbook / Agent 安装说明

Read this entire file and `AGENTS.md` before acting. Instructions here describe
the patch workflow; the user's explicit instructions and authorization take
precedence. This project does not grant permission to publish private files or
change unrelated machine state.

完整阅读本文件和 `AGENTS.md` 后再操作。用户的明确要求优先。安装请求不授权上传私人文件或改动无关系统设置。

## 1. Discover; do not mutate / 只读发现环境

Record these facts without printing secrets:

- Linux x86-64, NVIDIA RTX GPU and official NVIDIA user-space driver version.
- Whether games are running. Use process inspection and, when available,
  `nvidia-smi`; sandbox failures are not proof of a broken driver.
- Steam libraries from `steamapps/libraryfolders.vdf` and app 108600's manifest.
- Native game folder containing `projectzomboid.jar`, `ProjectZomboid64` (ELF),
  `natives/` and `jre64/bin/java`. A Windows `.exe` plus a Proton prefix is not a
  native installation; stop and explain if this is the installed platform.
- Viewpoint item 3809306528, usually
  `steamapps/workshop/content/108600/3809306528/mods/Viewpoint/42/media/java/client/Viewpoint.jar`.
- `mods/Viewpoint/common/mod.info`: expected `id=Viewpoint`, version 0.1.6.1.
- The game's actual cache directory (`~/Zomboid` by default); existing launch
  options can override it or `viewpoint.natives`. Preserve them. Stop to resolve
  a custom native-library destination instead of writing to a guessed folder.
- Bundled Java must support Java 25; Python 3.12+, `g++`, Vulkan loader required.

只读检查显卡、驱动、Steam 库、Linux 原生启动程序、模组版本和缓存路径。不要把受限环境中无法访问驱动误判为驱动损坏。遇到 Windows/Proton 安装、非 NVIDIA 显卡、缺少依赖或自定义缓存路径，应说明具体差异，避免自动修改系统来凑环境。

## 2. Pin the input / 锁定输入版本

Read `config/versions.json`. Hash the original JAR and compare it exactly.
Do not use an already patched JAR as the build input. If the user previously
installed this patch, use their preserved original backup, with the same hash.
If a Steam update changed the input, stop and report expected/actual version and
fingerprint. Do not silently roll back the user's Workshop version or disable
the guard. A source rebase is a separate development task.

对照配置文件中的原版 SHA-256。已修改版本只能作为安装目标，不能作为重建输入；使用受支持的原版备份。指纹不符时停止并报告，不强行覆盖更新。

## 3. Build without touching the game / 独立构建

From the cloned repository root:

```bash
python3 scripts/build.py --game-dir "$PZ_GAME_DIR" --viewpoint-jar "$ORIGINAL_VIEWPOINT_JAR"
```

Use actual absolute paths for the two variables; do not overwrite `HOME` or
other system variables. The builder fetches hash-pinned dependencies, decompiles
only local inputs under ignored `_work/`, applies the local transformations,
compiles the adapters, packages `dist/`, then runs offline checks. It does not
install, launch a game, or submit GPU work. `--deps-dir` selects a dependency
cache; `--offline` requires it to be complete and checksum-valid.

The output manifest records file fingerprints. Never commit or upload `_work/`,
`dist/`, `state/`, full generated source, game JARs or SDK binaries. The public
repository's MIT license does not apply to those upstream artifacts.

构建不安装、不启动游戏、不运行 GPU 工作。依赖缓存可用 `--deps-dir` 指定，`--offline` 禁止下载。新机器仍需按自身工具权限处理网络或安装依赖的授权，不能借指南绕过审批。

## 4. Ask for game exit, then test / 确认退出后测试

If the user is playing, complete the read-only/build work, then explain that a
GPU test or file replacement requires game exit. Wait for their answer. Do not
infer it from elapsed time. If exit was already confirmed and no game has been
restarted, do not ask for the same confirmation again. Check visible processes.

Run against staging first:

```bash
python3 scripts/test_gpu.py --kind fg --width 1280 --height 720 --game-exited
```

`--game-exited` is an acknowledgement, not permission to stop a game. Never kill
the user's game. The test opens only a hidden fixture context and does not read
saves. It selects the NVIDIA GPU for its own process. Use an available desktop
session; do not change system display settings to make the test start.

Successful FG output must include actual midpoint movement and SR/FG coexistence.
The fixture rejects repeated current frames. A capability check, initialized
SDK, logged 2x mode, or successful build alone is not sufficient.

GPU 测试或替换文件前需要用户确认已退出游戏，并检查可见进程。不要结束用户游戏。测试必须验证真正插值和 SR/FG 共存，不能把重复真实帧算成成功。

## 5. Preview and apply / 预览并安装

```bash
python3 scripts/manage.py install --viewpoint-jar "$INSTALLED_VIEWPOINT_JAR" --zomboid-dir "$ZOMBOID_CACHE_DIR"
```

Check every destination. Confirm the install is in the user's authorized scope,
game exit is still valid, and `dist/manifest.json` matches the built files. Then:

```bash
python3 scripts/manage.py install --viewpoint-jar "$INSTALLED_VIEWPOINT_JAR" --zomboid-dir "$ZOMBOID_CACHE_DIR" --apply --game-exited
```

The script backs up and atomically replaces the internal JAR and native libraries.
Keep the original name, `id=Viewpoint`, Workshop layout and dependency declarations.
Do not rename or enable a second copy with the same ID. Do not change launch
options just to add this patch; normal ZombieBuddy installation must already work.
The backup path is reported and retained under ignored `state/backups/`.

先检查 dry run 的目标，再在用户授权范围内执行。保留模组名和 ID，不制造重复 ID 副本；不改存档、现有依赖和启动项。保留备份和状态文件。

## 6. User approval and real scene check / 用户审批及游戏验证

Ask the user to start the game normally. ZombieBuddy can request approval for the
changed Viewpoint JAR; the user must review that dialog. Do not edit approvals,
set allow-all, or claim to have approved it for them.

Ask them to enable DLSS and frame generation, then inspect camera turns, movement,
HUD, ghosting, frame pacing and input feel. Read only relevant log lines, redacting
personal data if sharing them. Look for:

```text
[Viewpoint Linux DLSS] NGX initialized: ...
[Viewpoint Linux DLSSG] NGX initialized: ..., 2x
```

Record separately: offline checks; staged GPU test; game initialization; user's
visual confirmation; measured FPS/latency, if actually measured. Never fabricate
the latter from initialization or the 2x setting.

让用户正常启动、亲自审批新 JAR，并观察实际场景。初始化、用户确认和性能测量是不同证据，分别报告。

## 7. Failure and rollback / 失败及回滚

Do not repeatedly force a failing GPU path. Capture the complete relevant error
and the hardware/version context. Preserve the existing installation if the
staging test fails. Report unexpected behavior or unsupported versions before
dependent changes. Read `README.md`'s known FD-retention limitation.

After confirmed game exit, preview and restore the prior install:

```bash
python3 scripts/manage.py rollback
python3 scripts/manage.py rollback --apply --game-exited
```

If installed file hashes changed, stop and inspect rather than overwriting a
Steam update. Newly introduced libraries are moved into the backup directory;
prior files are restored. No untracked save directories should ever be removed.

暂存测试失败时不要安装。回滚也先确认退出游戏；指纹变化时停止，防止覆盖更新。不删除存档或其他不相关目录。

## Completion report / 完成报告

State installed version, preserved mod ID, checks performed, game-test status,
backup/rollback location and material limitations. A blocked step remains pending;
do not report a prepared build as an installed or validated result.

完成时说明版本、ID、真实验证结果、游戏实测状态、备份路径和局限；未完成步骤必须明确标为待办。
