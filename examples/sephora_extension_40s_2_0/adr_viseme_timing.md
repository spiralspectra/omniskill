# Voice Casting, Viseme Lip-Sync & Sidechain Ducking Script — SEPHORA: London Pulse (Continuous 40s Oner)

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
| 1 | `VO_NARRATOR` | 0.10-3.30 | 4 | 1.25 | No | `SS-PP-OO-TH-KK-NN` | The Soho Approach: Smooth glide of silk. |
| 2 | `VO_NARRATOR` | 10.10-13.30 | 4 | 1.25 | No | `EE-FF-EE-DD-RR-AA` | The Store Transition: Heavy drape of cashmere. |
| 3 | `VO_NARRATOR` | 20.10-23.30 | 5 | 1.56 | No | `KK-AA-DD-CH-EE-NN` | The Product Flourish: Catching the light on beadwork. |
| 4 | `VO_NARRATOR` | 30.10-33.30 | 4 | 1.25 | No | `SS-PP-OO-TH-KK-NN` | The Climactic Hero Lock: Smooth glide of silk. |
