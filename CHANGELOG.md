# Changelog

All notable changes to **Omni Movie Director** are documented in this file.

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
