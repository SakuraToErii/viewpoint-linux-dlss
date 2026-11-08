# Scope and third-party components

This is an independent, unofficial compatibility patch. It is not affiliated
with or endorsed by the Viewpoint authors, The Indie Stone, or NVIDIA.

The MIT license covers this repository's new adapter code, transformation tools,
tests and documentation. It does not relicense Project Viewpoint, Project Zomboid,
ZombieBuddy, generated local decompilation output, or vendor SDK components.

The repository contains no upstream Viewpoint JAR or complete decompiled upstream
source files, game assets, NVIDIA libraries/headers, or generated patched JARs.
The build reads the user's local supported Viewpoint JAR and makes a local patch.
Generated upstream source and output binaries stay in ignored directories.

External dependencies:

- [Project Viewpoint](https://steamcommunity.com/sharedfiles/filedetails/?id=3809306528)
  by ellu and norkus; original author terms apply.
- [ZombieBuddy](https://github.com/zed-0xff/ZombieBuddy), required by Viewpoint.
- [NVIDIA DLSS SDK](https://github.com/NVIDIA/DLSS) and its
  [SDK license](https://github.com/NVIDIA/DLSS/blob/main/LICENSE.txt).
- [Vulkan-Headers](https://github.com/KhronosGroup/Vulkan-Headers), subject to its
  Apache/MIT notices.
- [CFR](https://www.benf.org/other/cfr/), MIT; used only on the local input.
- [Eclipse ECJ](https://www.eclipse.org/jdt/), EPL-2.0; local build tool.
- Game-bundled LWJGL and JOML: compiled against the user's installation;
  not redistributed here.

Dependency downloads are pinned by SHA-256. Review the upstream terms before
using or redistributing vendor components. Do not publish generated mod JARs as
MIT artifacts: they include upstream material outside this repository's license.
