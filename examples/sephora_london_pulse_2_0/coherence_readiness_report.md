# OpenTimelineIO & Cross-Department Coherence Report — SEPHORA: London Pulse (Midnight Velvet)

- **OTIO Schema Version**: `OTIO_0.16_COMPAT`
- **Domain Archetype**: `luxury_fashion`
- **Frame Rate / Total Frames**: `24 fps` / `768 frames`
- **Coherence Score**: `100.0 / 100.0`
- **Conflicts / Warnings**: `0` / `0`
- **Shoot-Day Ready**: `True`
- **OTIO SHA-256**: `1af0c991eb09a83c1ca98db836be7714eb35c99c8544efe744512f0ae55baab1`

## 7-Track OpenTimelineIO Assembly
| Track | Kind | Clips | Markers | Frames (24fps) |
|---|---|---|---|---|
| `V1_Picture_Master` | Video | 4 | 19 | 768 |
| `V2_VFX_GFX_Overlay` | Video | 4 | 4 | 768 |
| `A1_Dialogue` | Audio | 0 | 0 | 768 |
| `A2_Foley_SFX` | Audio | 4 | 0 | 768 |
| `A3_Ambience` | Audio | 4 | 0 | 768 |
| `A4_Music_Score` | Audio | 4 | 3 | 828 |
| `A5_Audio_Description` | Audio | 4 | 4 | 768 |

## 7-Pair Cross-Department Coherence Matrix
| Check ID | Pair | Status | Measured | Bound | Remediation |
|---|---|---|---|---|---|
| `CHK-01-OPTICS-DOF` | `optics_vs_dof` | `PASS` | 0.0mm / 0.0T | <= 12.0mm / <= 1.5T | None |
| `CHK-02-KELVIN-BLOCKING` | `lighting_kelvin_vs_blocking` | `PASS` | 800K | <= 800K | None |
| `CHK-03-AUDIO-SPOTTING` | `audio_stems_vs_spotting` | `PASS` | LUFS 0.0 / 0.00 WPS | LUFS <= 2.5 / WPS <= 2.4 | None |
| `CHK-04-REFRAME-GRAPHICS` | `reframe_vs_graphics_blocking` | `PASS` | 9:16+16:9 CLEAR | y in [0.14, 0.64], x in [0.06, 0.80], 9:16 cleared | None |
| `CHK-05-MODEB-ECONOMICS` | `mode_b_vs_runtime_economics` | `PASS` | 32s / $16.59 | Mode B <= 40s & est <= $25.00 | None |
| `CHK-06-AICP-COMPUTE` | `aicp_post_vs_render_compute` | `PASS` | $24700.00 | >= $16.59 | None |
| `CHK-07-C2PA-SAFETY` | `c2pa_vs_cast_safety` | `PASS` | CLEARED | 2026 Model Matrix + consents + QC + JSA cleared | None |
