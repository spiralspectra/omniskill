# OpenTimelineIO & Cross-Department Coherence Report — Artisanal Japanese Culinary Ceremonial M

- **OTIO Schema Version**: `OTIO_0.16_COMPAT`
- **Domain Archetype**: `culinary_asmr`
- **Frame Rate / Total Frames**: `24 fps` / `240 frames`
- **Coherence Score**: `100.0 / 100.0`
- **Conflicts / Warnings**: `0` / `0`
- **Shoot-Day Ready**: `True`
- **OTIO SHA-256**: `f23e4155681c0e220629c817480cf61293d534235923e681e303aa522c88f687`

## 7-Track OpenTimelineIO Assembly
| Track | Kind | Clips | Markers | Frames (24fps) |
|---|---|---|---|---|
| `V1_Picture_Master` | Video | 2 | 13 | 240 |
| `V2_VFX_GFX_Overlay` | Video | 2 | 2 | 240 |
| `A1_Dialogue` | Audio | 0 | 0 | 240 |
| `A2_Foley_SFX` | Audio | 2 | 0 | 240 |
| `A3_Ambience` | Audio | 2 | 0 | 240 |
| `A4_Music_Score` | Audio | 2 | 1 | 272 |
| `A5_Audio_Description` | Audio | 2 | 2 | 240 |

## 7-Pair Cross-Department Coherence Matrix
| Check ID | Pair | Status | Measured | Bound | Remediation |
|---|---|---|---|---|---|
| `CHK-01-OPTICS-DOF` | `optics_vs_dof` | `PASS` | 0.0mm / 1.4T | <= 10.0mm / <= 1.5T | None |
| `CHK-02-KELVIN-BLOCKING` | `lighting_kelvin_vs_blocking` | `PASS` | 0K | <= 600K | None |
| `CHK-03-AUDIO-SPOTTING` | `audio_stems_vs_spotting` | `PASS` | LUFS 0.0 / 0.00 WPS | LUFS <= 2.0 / WPS <= 2.2 | None |
| `CHK-04-REFRAME-GRAPHICS` | `reframe_vs_graphics_blocking` | `PASS` | 9:16+16:9 CLEAR | y in [0.14, 0.64], x in [0.06, 0.80], 9:16 cleared | None |
| `CHK-05-MODEB-ECONOMICS` | `mode_b_vs_runtime_economics` | `PASS` | 10s / $7.75 | Mode B <= 40s & est <= $50.00 | None |
| `CHK-06-AICP-COMPUTE` | `aicp_post_vs_render_compute` | `PASS` | $14820.00 | >= $7.75 | None |
| `CHK-07-C2PA-SAFETY` | `c2pa_vs_cast_safety` | `PASS` | CLEARED | 2026 Model Matrix + consents + QC + JSA cleared | None |
