# Validation record

Tested locally on 2026-11-08, RTX 4060 Laptop 8 GiB / NVIDIA 615.78.08,
Linux x86-64, Omarchy 4.5.0, native PZ 42.21.0, Viewpoint 0.1.6.1, Java 25.0.1.

## Completed

- Native libraries built with external-symbol resolution.
- Java classes compiled against the installed game's APIs; JVM verification.
- Both foreign-function ABIs, invalid-context rejection and worker calls.
- Camera near/far mapping, image-origin conversion and inverse transforms.
- Pinned NVIDIA SDK downloads checked against their expected hashes.
- SR constant-color reconstruction and output readback.
- Simultaneous SR/FG contexts with alternating calls.
- Moving-object interpolation at 512x512 and at 1280x720 with 858x482 guides.
  The object advanced 6 pixels per real frame. Generated positions lagged the
  current frame by 2.962–3.002 pixels, matching the expected midpoint of 3.
  The test rejects copied current frames.
- User confirmed the combined patch works in the actual game. Selected log lines:

```text
[Viewpoint Linux DLSS] NGX initialized: 1715x1072 -> 2560x1600
[Viewpoint Linux DLSSG] NGX initialized: 2560x1600, guides 1715x1072, 2x
```

The later source-only build workflow also rebuilt locally from the pinned original
input and passed the packaged offline checks. The original GPU tests validate the
backend implementation, not every future rebuild, driver or supported machine.

## Unresolved / not established

- Approximately 3 retained process FDs per complete repeated SR context
  recreation, including 2 eventfds. Origin is unresolved; do not call this leak-free.
- Broad hardware/driver support, long-session stability and all camera/HUD artifacts.
- End-to-end latency, achieved display FPS and pacing in real game scenes.
- FSR/XeSS, multi-frame generation and ray reconstruction.

See [gpu-verification.json](gpu-verification.json) for the sanitized measured
fixture summary. No full personal game log or proprietary binary is included.
