# Digital Colorimetry Scopes & Shot-Match QC Report — IKEA: The Living Room Unfolds

- **Manifest ID**: `scopes-d1f81522`
- **Signal Standard**: `rec709_24`
- **Mean CIEDE2000**: `1.48` (Ceiling `<= 3.00`)
- **Max Exposure Jump**: `<= 0.70 EV`
- **All Cuts Matched**: `PASS`

## Per-Scene Waveform & Gamut Telemetry

| Scene | Min IRE | Avg IRE | Peak IRE | RGB Balance (%) | Gamut Util (%) | Dominant Hex |
|---:|---:|---:|---:|---|---:|---|
| 1 | 1.0 | 21.2 | 49.2 | 23.1 / 31.5 / 45.4 | 84.5% | `#1E293B` |
| 2 | 1.0 | 21.8 | 49.8 | 24.8 / 31.8 / 43.4 | 84.5% | `#212B3A` |
| 3 | 1.0 | 21.5 | 49.5 | 22.2 / 31.8 / 45.9 | 84.5% | `#1E2A3D` |
| 4 | 1.0 | 22.2 | 50.2 | 23.9 / 31.7 / 44.4 | 84.5% | `#212C3E` |

## Adjacent-Cut Shot-Match Deltas

| Cut | dE2000 | EV Delta | Kelvin Delta | CDL Offset (R, G, B) | Status |
|---|---:|---:|---:|---|---|
| SC01 -> SC02 | 1.67 | +0.04 EV | 0 K | `(-0.0118, -0.0078, +0.0039)` | `matched` |
| SC02 -> SC03 | 1.94 | -0.02 EV | 0 K | `(+0.0118, +0.0039, -0.0118)` | `matched` |
| SC03 -> SC04 | 0.82 | +0.05 EV | 0 K | `(-0.0118, -0.0078, -0.0039)` | `matched` |
