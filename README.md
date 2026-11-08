# Viewpoint Linux DLSS 补丁（非官方）

[English](README.en.md) · [Agent 安装指南](docs/AGENT_INSTALL.md) · [Agent 规则](AGENTS.md) · [测试证据](docs/VALIDATION.md)

为 Linux 原生版 Project Zomboid 的 Project Viewpoint 添加 **DLSS 超分辨率 / DLAA** 和 **2× DLSS 帧生成**。
保留 `Viewpoint` 模组 ID 和原有前置依赖。该项目与 Viewpoint 作者、The Indie Stone 和 NVIDIA 无隶属关系。

这是源码与本地构建工具仓库。构建使用你自己安装的原版 Viewpoint JAR；仓库不提供原模组、反编译源码全集、修改后的 JAR 或 NVIDIA 二进制。

## 已验证的范围

| 项目 | 状态 |
| --- | --- |
| Linux OpenGL ↔ Vulkan 文件描述符共享 | RTX 4060 Laptop / NVIDIA 615.78.08 上通过 |
| DLSS 超分辨率 / DLAA 接口 | 实现，超分辨率 GPU 测试通过 |
| 每个真实帧插入一帧的 DLSS 帧生成 | GPU 移动物体插值测试通过，可与超分辨率共存 |
| 实际游戏 | 使用者确认生效；日志显示输出 2560×1600、引导图像 1715×1072 |
| FSR、XeSS 后端、多帧生成、光线重建 | 未实现 |
| 广泛硬件兼容、长期稳定性、实测帧率和延迟 | 尚未验证 |

**受支持输入：Viewpoint 0.1.6.1、PZ 42.21.0、Linux x86-64、Java 25。**
原版 JAR SHA-256：`096bd37d63cb699ac95e9e7ea5245a1b9b5ff08c5161db35f6733b1d1c42b064`。
版本或指纹不同，构建会停止。不要关闭校验强行安装。

## 交给 Agent 安装

把仓库链接交给你的 Agent，并发送：

> 请先完整阅读 AGENTS.md 和 docs/AGENT_INSTALL.md，再检查我的环境并安装此 Linux 兼容补丁。保留现有模组 ID、依赖、存档和启动选项。可以先检查和构建；需要退出游戏、修改系统或遇到版本不匹配时停下来告诉我。完成后区分离线校验、GPU 测试与游戏实测结果，并保留回滚备份。

安装指南包含路径发现、构建、暂存测试、安装、审批提示和回滚流程。Agent 不应跳过用户的游戏退出确认或修改 ZombieBuddy 的批准记录。

## 手动构建和安装

先通过 Steam 安装 Linux 原生版游戏、ZombieBuddy 和 Viewpoint。需要 Python 3.12+、`g++`、NVIDIA 驱动、Vulkan loader，以及游戏自带的 Java 25。构建下载固定指纹的 CFR、ECJ、Vulkan Headers 和 NVIDIA SDK；第三方组件适用各自条款，见 [NOTICE.md](NOTICE.md)。

克隆仓库后，在仓库根目录执行。以下路径是 Steam 默认布局示例，按实际安装位置调整：

```bash
PZ_GAME_DIR="$HOME/.steam/steam/steamapps/common/ProjectZomboid/projectzomboid"
VIEWPOINT_JAR="$HOME/.steam/steam/steamapps/workshop/content/108600/3809306528/mods/Viewpoint/42/media/java/client/Viewpoint.jar"

python3 scripts/build.py --game-dir "$PZ_GAME_DIR" --viewpoint-jar "$VIEWPOINT_JAR"
```

该命令只在 `_work/` 和 `dist/` 中构建、执行离线校验，不安装或启动游戏。
如果已经装过补丁，构建输入应使用受支持的原版备份，而不是修改后的 JAR。`--viewpoint-jar` 的构建输入与之后的安装目标可以不同。

**退出游戏后**，运行暂存 GPU 测试。测试只创建隐藏的测试图形上下文，不读取游戏存档：

```bash
python3 scripts/test_gpu.py --kind fg --width 1280 --height 720 --game-exited
```

它会验证超分辨率与帧生成共存，以及移动物体是否真正落在两帧之间。测试通过后，先预览安装：

```bash
python3 scripts/manage.py install --viewpoint-jar "$VIEWPOINT_JAR"
```

确认目标路径正确、游戏已退出，再安装：

```bash
python3 scripts/manage.py install --viewpoint-jar "$VIEWPOINT_JAR" --apply --game-exited
```

安装器备份现有 JAR 和库，然后原子替换；不改 `mod.info`、模组 ID、存档、Steam 启动项或审批记录。
启动游戏后，ZombieBuddy 可能要求重新批准修改后的 Viewpoint；请自行查看提示并决定。之后在 Viewpoint 设置中启用 DLSS 和帧生成，检查实际场景、HUD、拖影和流畅度。

日志标志：

```text
[Viewpoint Linux DLSS] NGX initialized: ...
[Viewpoint Linux DLSSG] NGX initialized: ..., 2x
```

初始化日志不等同于正确画面、实测帧率翻倍或更低延迟。

## 回滚

先退出游戏，预览后再恢复：

```bash
python3 scripts/manage.py rollback
python3 scripts/manage.py rollback --apply --game-exited
```

备份和本机路径在忽略的 `state/` 目录中。若文件自安装后发生变化，回滚会停止，避免覆盖 Steam 更新或其他修改。不要删除 `state/` 后再要求自动恢复。

## 已知限制

- 仅在一块 RTX 4060 Laptop、NVIDIA 615.78.08 上测试。帧生成仍需 SDK 检测显卡和驱动能力。
- 反复完整重建 NGX/Vulkan 上下文时，每次约保留 3 个进程文件描述符，包括 2 个 eventfd；原因尚未确定。不要将此版本描述为无泄漏，测试大量设置变化时可重启游戏。
- 未测量实际游戏的端到端延迟、显示帧率或所有场景的画质。2× 是插入帧模式，不是实测性能保证。
- Steam 创意工坊更新可能覆盖补丁；新版本需要重新适配和验证，不能沿用旧指纹绕过校验。
- 新代码使用 AI 辅助开发，需正常代码审查与更多实际测试。

## 源码、贡献与许可证

新写的代码和工具采用 [MIT](LICENSE)。原模组、游戏和 SDK 保留各自权利。
构建过程在本机读取并转换原 JAR，生成文件不得被误标为本仓库的 MIT 源码发布。
欢迎提交可复现问题、硬件测试、句柄生命周期修复和兼容性改进；请对日志中的用户名、路径和其他私人信息进行删减。

官方项目：[Viewpoint Workshop](https://steamcommunity.com/sharedfiles/filedetails/?id=3809306528) · [ZombieBuddy](https://github.com/zed-0xff/ZombieBuddy)。
