# Voice Casting, Viseme Lip-Sync & Sidechain Ducking Script — SEPHORA: London Pulse (Midnight Velvet)

- **Music Duck Attenuation**: `-6.5 dB`
- **Ambience Duck Attenuation**: `-5.0 dB`
- **Minimum Dialogue Clarity SNR**: `6.0 dB`
- **Lip-Sync <= 2.5 WPS Pass Rate**: `100.0%`

## Voice Casting Roster

| Character ID | Name | Register | Mic Perspective | Target WPM | Pitch Range |
|---|---|---|---|---:|---|
| `CHAR_01_MODEL_MAYA_THE_NEO` | Model Maya (The Neon Siren) | `MEZZO_SOPRANO` | `vo_booth_neumann_u87` | 108.0 | 155-235 Hz |
| `CHAR_02_MODEL_KAELEN_THE_S` | Model Kaelen (The Shimmer Rebel) | `BARITONE` | `vo_booth_neumann_u87` | 108.0 | 95-155 Hz |
| `VO_NARRATOR` | Narrator / Audio Description VO | `MEZZO_SOPRANO` | `vo_booth_neumann_u87` | 108.0 | 165-245 Hz |

## Per-Scene Viseme Lip-Sync & Sidechain Ducking

| Scene | Speaker | Window (s) | Words | WPS | On-Camera | Dominant Visemes | Line |
|---:|---|---|---:|---:|:---:|---|---|
| 1 | `VO_NARRATOR` | 0.10-3.30 | 8 | 2.50 | No | `TH-EE-SS-OO-SS-DD` | The Soho Stare & The Night Pan: Smooth. |
| 2 | `VO_NARRATOR` | 8.10-11.30 | 5 | 1.56 | No | `DD-AA-KK-DD-EE-NN` | The Flagship Infiltration: Tactile Glamour: Heavy drape of. |
| 3 | `VO_NARRATOR` | 16.10-19.30 | 4 | 1.25 | No | `KK-AA-DD-CH-EE-NN` | The Soho Runway Strut: Catching the light on. |
| 4 | `VO_NARRATOR` | 24.10-27.30 | 8 | 2.50 | No | `TH-EE-PP-AA-KK-NN` | The Bag Lock & The Soho Freeze: Smooth. |
