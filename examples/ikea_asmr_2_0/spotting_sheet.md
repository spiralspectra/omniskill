# Editorial Spotting & Audio Bridge Sheet: IKEA: The Living Room Unfolds

- **FPS**: `24 fps` (Non-Drop Frame)
- **Tempo**: `84.0 BPM` (`17.14` frames/beat, `4/4` meter)
- **Beat Alignment Score**: `80.2 / 100.0`
- **Total Split Edits**: `3` | **Recommended NLE Audio Tracks**: `6`

## 1. J-Cut / L-Cut Scene Transitions

| Cut | Timecode | Bridge Type | J-Prelap (f) | L-Overhang (f) | Beat Offset (f) | Locked | Sonic Anchor |
|---|---|---|---:|---:|---:|---|---|
| S01->S02 | `00:00:08:00` | `l_cut` | 0 | 30 | +3 | YES | Timber & stone room-tone 30f ambience L-Cut |
| S02->S03 | `00:00:16:00` | `l_cut` | 0 | 30 | +7 | DRIFT | Timber & stone room-tone 30f ambience L-Cut |
| S03->S04 | `00:00:24:00` | `l_cut` | 0 | 30 | -7 | DRIFT | Timber & stone room-tone 30f ambience L-Cut |

## 2. Music, Foley & Room-Tone Spotting Cues

| Cue ID | Scene | Category | In TC | Out TC | Dur (f) | Stem Target | Bar | LUFS | Description |
|---|---:|---|---|---|---:|---|---:|---:|---|
| `SPOT-MUS-S01` | 1 | `music_stem` | `00:00:00:00` | `00:00:08:15` | 207 | A4 (BGM Score) | 1 | -18.0 | Nordic Serenity: Tactile Pulse @ 84 BPM | Bar 1 |
| `SPOT-SFX-S01` | 1 | `foley_hard` | `00:00:00:00` | `00:00:08:00` | 192 | A2 (Foley / SFX) | 1 | -24.0 | The Awakening Box tactile Foley (J-prelap 0f) |
| `SPOT-AMB-S01` | 1 | `room_tone` | `00:00:00:00` | `00:00:09:06` | 222 | A3 (Room Ambience) | 1 | -22.0 | Calibrated production room tone (L-overhang 30f) |
| `SPOT-MUS-S02` | 2 | `music_stem` | `00:00:08:00` | `00:00:16:15` | 207 | A4 (BGM Score) | 3 | -18.0 | Nordic Serenity: Tactile Pulse @ 84 BPM | Bar 3 |
| `SPOT-SFX-S02` | 2 | `foley_hard` | `00:00:08:00` | `00:00:16:00` | 192 | A2 (Foley / SFX) | 3 | -24.0 | The Hyper-Kinetic Self-Assembly tactile Foley (J-prelap 0f) |
| `SPOT-AMB-S02` | 2 | `room_tone` | `00:00:08:00` | `00:00:17:06` | 222 | A3 (Room Ambience) | 3 | -22.0 | Calibrated production room tone (L-overhang 30f) |
| `SPOT-MUS-S03` | 3 | `music_stem` | `00:00:16:00` | `00:00:24:15` | 207 | A4 (BGM Score) | 6 | -18.0 | Nordic Serenity: Tactile Pulse @ 84 BPM | Bar 6 |
| `SPOT-SFX-S03` | 3 | `foley_hard` | `00:00:16:00` | `00:00:24:00` | 192 | A2 (Foley / SFX) | 6 | -24.0 | Upholstery & Soft Architecture tactile Foley (J-prelap 0f) |
| `SPOT-AMB-S03` | 3 | `room_tone` | `00:00:16:00` | `00:00:25:06` | 222 | A3 (Room Ambience) | 6 | -22.0 | Calibrated production room tone (L-overhang 30f) |
| `SPOT-MUS-S04` | 4 | `music_stem` | `00:00:24:00` | `00:00:32:00` | 192 | A4 (BGM Score) | 9 | -18.0 | Nordic Serenity: Tactile Pulse @ 84 BPM | Bar 9 |
| `SPOT-SFX-S04` | 4 | `foley_hard` | `00:00:24:00` | `00:00:32:00` | 192 | A2 (Foley / SFX) | 9 | -24.0 | The Final Flourish & The ASMR Stillness tactile Foley (J-prelap 0f) |
| `SPOT-AMB-S04` | 4 | `room_tone` | `00:00:24:00` | `00:00:32:00` | 192 | A3 (Room Ambience) | 9 | -22.0 | Calibrated production room tone (L-overhang 0f) |
