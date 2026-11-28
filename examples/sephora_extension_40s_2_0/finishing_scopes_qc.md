# Digital Colorimetry Scopes & Shot-Match QC Report — SEPHORA: London Pulse (Continuous 40s Oner)

- **Manifest ID**: `scopes-43a8e5b7`
- **Signal Standard**: `p3_d65`
- **Mean CIEDE2000**: `2.63` (Ceiling `<= 2.00`)
- **Max Exposure Jump**: `<= 0.50 EV`
- **All Cuts Matched**: `PASS`

## Per-Scene Waveform & Gamut Telemetry

| Scene | Min IRE | Avg IRE | Peak IRE | RGB Balance (%) | Gamut Util (%) | Dominant Hex |
|---:|---:|---:|---:|---|---:|---|
| 1 | 1.0 | 12.4 | 41.2 | 30.5 / 31.5 / 38.0 | 96.0% | `#0D0D10` |
| 2 | 1.0 | 12.6 | 41.4 | 34.4 / 28.4 / 37.1 | 96.0% | `#100D11` |
| 3 | 1.0 | 13.3 | 42.1 | 25.9 / 33.9 / 40.2 | 96.0% | `#0D1114` |
| 4 | 1.0 | 13.4 | 42.2 | 32.7 / 34.4 / 32.9 | 96.0% | `#101110` |

## Adjacent-Cut Shot-Match Deltas

| Cut | dE2000 | EV Delta | Kelvin Delta | CDL Offset (R, G, B) | Status |
|---|---:|---:|---:|---|---|
| SC01 -> SC02 | 1.68 | +0.03 EV | 0 K | `(-0.0118, +0.0000, -0.0039)` | `matched` |
| SC02 -> SC03 | 1.70 | +0.08 EV | 0 K | `(+0.0118, -0.0157, -0.0118)` | `matched` |
| SC03 -> SC04 | 1.70 | +0.01 EV | 0 K | `(-0.0118, +0.0000, +0.0157)` | `matched` |
