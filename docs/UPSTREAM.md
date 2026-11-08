# Upstream integration notes

The original Linux failure checked Windows-only GL external-memory/semaphore
extensions and used Win32 exports/imports. The driver on the tested machine
supports the corresponding Linux FD extensions. The original vendor downloader
also selected Windows DLLs, so changing extension names alone was insufficient.

This patch implements:

- OPAQUE_FD image memory and semaphore sharing with ownership transfer on GL import.
- Native Linux NGX Super Resolution instead of the Windows Streamline path.
- Native Linux NGX DLSSG instead of the original Windows FidelityFX FG backend.
- Existing Viewpoint frame capture/presentation retained; one intermediate frame.
- Partial-construction cleanup and real-frame fallback when interpolation is suppressed.

For upstream adoption, platform-specific backend selection should preserve the
existing Windows implementation. This local replacement is Linux-only. FSR/XeSS
need separate Linux backends; this patch intentionally reports them unsupported.
The repeated-context FD observation needs investigation before a stable release.

No verified official public source repository was found when this work was prepared.
The confirmed author-facing entry points are the
[Workshop discussions](https://steamcommunity.com/sharedfiles/filedetails/discussions/3809306528)
and the community listed on the
[original Workshop page](https://steamcommunity.com/sharedfiles/filedetails/?id=3809306528).
This repository does not imply an upstream PR, acceptance or author endorsement.

AI assistance was used to develop the new adapters and tooling. Maintainers should
review normal correctness, platform semantics, lifecycle, performance and licensing
boundaries before adopting any part of this experiment.
