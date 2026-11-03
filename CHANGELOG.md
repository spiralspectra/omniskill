# Changelog

All notable changes to **Omni Movie Director** are documented in this file.

## [2.3.0] - 2026-11-03

### Added (Senior Product Manager Roadmap & Autonomous Product Council Release)
- **PM-FEAT-004: ASC CDL Color Science, Cinematic Look Presets & SVG Filter Grading Engine**:
  - Module: `omni_director/tools/color_grade.py`.
  - Added `AscCdlSpec` (RGB Slope, Offset, Power, Saturation) and `ColorLookSpec` schemas with ACEScg/Rec.709 color space profiles.
  - 6 Calibrated Film Stock / Look Presets: `rec709_neutral`, `kodak_5219_vision3`, `fuji_eterna_500t`, `bleach_bypass_silver`, `teal_and_orange_blockbuster`, `monochrome_panatomic_x`.
  - DaVinci Resolve ASC CDL XML v1.2 sidecar export (`export_asc_cdl_xml` and `production_grade.cdl`).
  - CMX 3600 EDL color decision comment embedding (`*ASC_SOP` and `*ASC_SAT` metadata lines per event).
  - Dark-Room Cinema Animatic SVG Filter Matrix (`<feColorMatrix>` / `<feComponentTransfer>`) with interactive Look Selector dropdown (`#look-selector`) and keyboard shortcut `L`.
  - CLI support: `omni export --format cdl` and `--format all`.
- **PM-FEAT-005: Dynamic Speed Ramping, Shutter Angle & Motion Timing Engine**:
  - Module: `omni_director/tools/speed_ramp.py`.
  - Added `SpeedRampCurveSpec` schema with 5 ramping modes (`constant_realtime`, `deceleration_impact`, `acceleration_burst`, `snap_freeze_resume`, `pulse_time_dilation`) and SMPTE time-warp keyframe curves.
  - CRAFT Camera Grammar Shutter Angle calibration (`shutter_angle_deg`: 180° standard, 90° staccato action, 360° motion blur) and shutter timing tokens.
  - Final Cut Pro XML (`sequence.fcpxml`) time-warp integration emitting valid `<timeMap><timept .../></timeMap>` tags.
  - Prompt Auditor enhancements recognizing shutter angle compliance and enforcing physical momentum conservation invariants.
  - Animatic Scrubber Velocity Track (`.velocity-track-container`) with real-time speed ramp indicators and badges.
- **PM-FEAT-006: Interactive Diegetic Stem Audio Mixer & Metering Console**:
  - Module: `omni_director/tools/audio_mixer.py`.
  - Added `AudioStemMixerSpec` and `StemChannelStrip` schemas modeling 4 calibrated stems: `[DIA]` Dialogue, `[SFX]` Foley, `[AMB]` Ambience, `[MUS]` Music with Gain (dB), Pan, Mute, Solo, and target LUFS.
  - Broadcast loudness estimation (integrated LUFS and peak dBFS) adhering to EBU R128 (-23 LUFS) and ATSC A/85 (-24 LUFS) standards.
  - Resolve Fairlight & Premiere Pro track layout manifest export (`audio_stems_manifest.json`) via `omni export --format stems`.
  - Dark-Room Cinema Animatic Audio Console (`#animatic-audio-mixer`, hotkey `M`) featuring 4 channel strips, rotary pan knobs, vertical dB faders, M/S toggles, and dual canvas LED VU meters.
  - Integrated Web Audio API sound synthesis engine generating ambient acoustic previews and driving 60fps VU meter ballistics with 300ms decay.
- **Commercial Domain Archetype Deterministic Alignment**:
  - Updated all 6 commercial archetypes (`automotive_robotics`, `culinary_asmr`, `luxury_fashion`, `kinetic_action`, `tech_hardware`, `architectural_sanctuary`) to deterministically equip calibrated CDL looks, speed ramp modes, shutter angles, and stem mixer balances.
  - Expanded `ProductCouncilOrchestrator` strategist review to award full marks for aligned visual/sonic specifications.

## [2.2.0] - 2026-11-02

### Added (Senior Product Manager Roadmap & Feature Release)
- **Senior Product Manager Persona (`council-product-manager`)**: Integrated `ProductManagerAgent` into the Autonomous Product Council with the world-class Senior Product Manager persona (`SENIOR_PM_PERSONA_PROMPT`). The daily council routine now always consults the Senior Product Manager, implements product features, updates tests, performs a version release, and pushes to `origin`.
- **NLE Post-Production Exporter (`omni_director/tools/nle_export.py` & `omni export`)**:
  - `export_cmx3600_edl`: Generates frame-accurate CMX 3600 Edit Decision Lists (`timeline.edl`) at 24fps for DaVinci Resolve, Premiere Pro, and Avid Media Composer.
  - `export_fcpxml`: Generates valid Final Cut Pro XML v1.10 (`sequence.fcpxml`) timelines with spine asset clips and camera/audio metadata.
  - `export_shot_list_csv`: Exports a spreadsheet-ready DP/1st AD shot list (`shot_list.csv`).
  - `export_production_callsheet_md`: Generates a formatted physical production Call Sheet (`call_sheet.md`).
  - Added CLI subcommand `omni export --preset <name> --format [all|edl|fcpxml|csv|md|srt|vtt] -o <dir>` and `--export-nle` flag.
- **Dialogue Pacing Guardrail & Subtitle Compiler (`omni_director/tools/dialogue.py` & Animatic CC HUD)**:
  - `audit_dialogue_pacing`: Enforces the 2.5 words-per-second (20 words per 8s scene) speech-rate ceiling to prevent rushed lip-sync in Gemini Omni 1.1.
  - `compile_subtitles_srt` & `compile_subtitles_vtt`: Generates frame-accurate SubRip (`.srt`) and WebVTT (`.vtt`) caption tracks with speaker attribution and diegetic foley annotations.
  - Added live Closed Caption (`CC [C]`) HUD overlay (`#animatic-cc-hud`) and keyboard shortcut `C` to the Dark-Room Cinema HTML5 animatic.
- **Multi-Cam Coverage & Conversational Iteration Engine (`omni_director/tools/coverage.py`)**:
  - `generate_scene_coverage`: Synthesizes 3 parallel camera coverage variants per scene (`[A: Master 24mm]`, `[B: Dynamic Hero]`, `[C: Macro 100mm]`) compliant with the 7-Point Gemini Omni Prompting Standard.
  - `synthesize_conversational_deltas`: Automatically generates Turn 2 (Lighting/Atmosphere), Turn 3 (Camera/Framing), and Turn 4 (Acoustic Polish) delta prompts for every scene.
  - Added interactive multi-cam coverage selector tabs (`.coverage-selector`) to each scene card in `storyboard_preview.html`.

## [2.1.0] - 2026-11-01

### Added
- Autonomous 4-Persona Product Council (`council-fde`, `council-agent-engineer`, `council-strategist`, `council-ux-designer`) with 100-point rubric and strict quality gates.
- 6 Commercial Domain Archetypes (`automotive_robotics`, `culinary_asmr`, `luxury_fashion`, `kinetic_action`, `tech_hardware`, `architectural_sanctuary`).
- Dark-Room Cinema HTML5 Animatic with 24fps SMPTE scrubber, dynamic beat timeline, WCAG 2.2 AA accessibility, and SHA-256 bundle checksum verification.
