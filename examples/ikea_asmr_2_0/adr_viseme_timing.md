# Voice Casting, Viseme Lip-Sync & Sidechain Ducking Script — IKEA: The Living Room Unfolds

- **Music Duck Attenuation**: `-7.5 dB`
- **Ambience Duck Attenuation**: `-4.5 dB`
- **Minimum Dialogue Clarity SNR**: `6.0 dB`
- **Lip-Sync <= 2.5 WPS Pass Rate**: `100.0%`

## Voice Casting Roster

| Character ID | Name | Register | Mic Perspective | Target WPM | Pitch Range |
|---|---|---|---|---:|---|
| `VO_NARRATOR` | Narrator / Audio Description VO | `BASS` | `lavalier_intimate` | 102.0 | 145-220 Hz |

## Per-Scene Viseme Lip-Sync & Sidechain Ducking

| Scene | Speaker | Window (s) | Words | WPS | On-Camera | Dominant Visemes | Line |
|---:|---|---|---:|---:|:---:|---|---|
| 1 | `VO_NARRATOR` | 0.10-3.30 | 4 | 1.25 | No | `KK-OO-NN-KK-OO-NN` | The Awakening Box: Cool concrete echoing footsteps. |
| 2 | `VO_NARRATOR` | 8.10-11.30 | 8 | 2.50 | No | `TH-EE-PP-EE-RR-KK` | The Hyper-Kinetic Self-Assembly: Warm light pooling on timber. |
| 3 | `VO_NARRATOR` | 16.10-19.30 | 8 | 2.50 | No | `OO-PP-OO-NN-SS-DD` | Upholstery & Soft Architecture: Expansive vaulted ceiling distance. |
| 4 | `VO_NARRATOR` | 24.10-27.30 | 8 | 2.50 | No | `TH-EE-FF-EE-NN-AA` | The Final Flourish & The ASMR Stillness: Cool. |
