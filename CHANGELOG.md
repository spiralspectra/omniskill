# Changelog

All notable changes to **Omni Movie Director** are documented in this file.

## [2.6.0] - 2026-11-06

### Added (Senior Product Manager Roadmap & Autonomous Product Council Release)
- **PM-FEAT-011: Cinematic Depth-of-Field, Bokeh Geometry & Anamorphic Optical Aberration Simulator with Rack-Focus Transition Curves and Focus Puller Cue Sheets**:
  - Module: `omni_director/tools/dof_simulator.py`.
  - Added `ApertureIrisGeometry` enum (`circular`, `octagonal_8_blade`, `nonagonal_9_blade`, `undecagonal_11_blade`, `anamorphic_oval_2x`), `OpticalAberrationProfile`, `RackFocusTransitionCurve`, and `DepthOfFieldSpec` schemas.
  - Implemented optical physics calculations: Circle of Confusion (`resolve_circle_of_confusion`) across sensor formats (Super35, Full Frame, ARRI LF, IMAX 70mm, VistaVision), hyperfocal distance (`calculate_hyperfocal_distance`), near/far focus limits and total depth of field (`calculate_dof_limits`), and kinematic rack-focus curve interpolation (`interpolate_rack_focus`).
  - CRAFT camera grammar prompt token formatting (`format_dof_prompt_token`) embedding focal length, aperture T-stop, focus distance, near/far depth range, iris geometry, and rack-focus timing.
  - Multi-format optical exports: 1st AC Focus Puller cue sheet CSV (`export_focus_puller_cue_sheet`), optical chart JSON (`export_optical_chart_json`), and optical bundle packaging (`export_dof_bundle`).
  - CLI export support: `omni export --format dof`, `--format all`, `--dof-chart`, and `--cue-sheet`.
  - Dark-Room Cinema Animatic Interactive Optical Depth of Field HUD (`#animatic-dof-hud`, hotkey `F`) displaying interactive ray-tracing SVG geometry, parametric focal length / T-stop / focus distance sliders, rack-focus easing scrubber, dynamic bokeh badge (`#bokeh-geometry-badge`), and live tabular 1st AC cue sheet.
- **PM-FEAT-012: DIT 3D LUT (.cube) Generator & Production Continuity Engine with ASC CDL to 3D LUT .cube Matrix Compilation for DaVinci Resolve & SmallHD On-Set Monitors**:
  - Module: `omni_director/tools/dit_lut.py`.
  - Added `LutGridDimension` enum (`cube_17`, `cube_33`, `cube_65`), `ColorGamutTransform`, `ThreeDimensionalLutSpec`, and `SceneColorContinuityReport` schemas.
  - Implemented pure-Python 3D LUT `.cube` matrix generator (`generate_3d_lut_cube_data` and `generate_3d_cube_lut`) compiling ASC CDL transfer functions (Slope, Offset, Power, Saturation) into industry-standard Adobe/Resolve `.cube` lattice files with luminance preservation.
  - Multi-scene color continuity validation (`verify_color_continuity` and `calculate_color_continuity_audit`) detecting uncalibrated gamut transitions and delta-E drift.
  - Production LUT exports: Master 3D LUT `.cube` (`export_master_cube_lut`), per-scene `.cube` LUTs (`export_scene_cube_lut`), DIT cart manifest JSON (`export_dit_cart_manifest_json`), and DIT bundle packaging (`export_dit_bundle` / `export_lut_bundle`).
  - CLI export support: `omni export --format lut`, `--format all`, `--cube-lut`, and `--dit-manifest`.
  - Dark-Room Cinema Animatic Interactive DIT 3D LUT Suite HUD (`#animatic-dit-lut-hud`, hotkey `L`) displaying draggable split-screen wipe (`#lut-split-wipe`), client-side `.cube` generation and instant downloads (`#btn-download-master-cube`, `#btn-download-scene-cube`), and live color continuity status telemetry.
- **Autonomous Product Council Governance & Presets Expansion**:
  - Registered `PM-FEAT-011` and `PM-FEAT-012` in `ProductManagerAgent.inspect_product()`.
  - Equipped all 6 commercial domain archetypes with domain-calibrated DoF optical specs (`get_domain_dof_spec`) and 3D LUT profiles (`get_domain_lut_spec`) in `omni_director/presets.py`.
  - Updated prompt auditor Rule 4 and self-healing loop in `omni_director/tools/prompt_auditor.py` to evaluate and inject DoF and 3D LUT tokens with audit score >= 90.0.
  - Integrated full 25.0/25.0 scoring in `ProductCouncilOrchestrator` across `council-fde`, `council-agent-engineer`, `council-strategist`, and `council-ux-designer`.

## [2.5.0] - 2026-11-05

### Added (Senior Product Manager Roadmap & Autonomous Product Council Release)
- **PM-FEAT-009: Kinetic Motion Control (MoCo) Rig & 6-DOF Camera Kinematics Engine**:
  - Module: `omni_director/tools/moco_kinematics.py`.
  - Added `MotionControlRigType` enum (`bolt_cinebot`, `technocrane`, `cablecam`, `steadicam`, `drone_fpv`, `russian_arm`, `motorized_dolly`), `TrajectoryWaypoint6DOF`, and `MocoRigSpec` schemas.
  - Implemented 6-DOF spatial waypoint calculations: Euclidean trajectory distance (`calculate_trajectory_distance`), peak velocity (`calculate_peak_velocity`), mean acceleration (`calculate_mean_acceleration`), and sub-frame waypoint interpolation (`interpolate_waypoints_6dof`).
  - CRAFT camera grammar prompt token formatting (`format_moco_prompt_token`) embedding rig type, track distance, peak velocity, repeatability, and stabilization mode.
  - Multi-format MoCo track exports: JSON (`export_moco_track_json`), CSV (`export_moco_track_csv`), and FBX 7.4.0 ASCII camera transform curves (`export_moco_fbx_ascii`).
  - CLI support: `omni export --format moco` and `--format all`.
  - Dark-Room Cinema Animatic Interactive MoCo Trajectory HUD (`#animatic-moco-hud`, hotkey `K`) displaying 6-DOF coordinate telemetry ($X, Y, Z, \text{Roll}, \text{Pitch}, \text{Yaw}$), peak velocity gauge, interactive waypoint selectors, and animated SVG isometric trajectory visualization.
- **PM-FEAT-010: Volumetric Atmospheric & Studio Lighting Rig Simulator**:
  - Module: `omni_director/tools/lighting_rig.py`.
  - Added `LightingFixtureRole`, `DiffusionGrade`, `ParticulateHazeType`, `StudioLightFixtureSpec`, `AtmosphericHazeSpec`, and `LightingRigSpec` schemas.
  - Implemented studio photometric calculations: Key-to-Fill illuminance contrast ratio (`calculate_key_to_fill_ratio`), Key-to-Rim separation ratio (`calculate_key_to_rim_ratio`), aggregate scene Lux (`calculate_total_lux`), and per-fixture CCT Kelvin delta mapping (`calculate_cct_deltas`).
  - CRAFT lighting prompt token formatting (`format_lighting_prompt_token`) embedding Key:Fill ratios, aggregate incident Lux, Kelvin CCT balance, and volumetric haze scattering coefficients.
  - Lighting plot artifact exports: Studio lighting plot JSON (`export_lighting_plot_json`) and Gaffer crew call sheet CSV (`export_gaffer_callsheet_csv`).
  - CLI support: `omni export --format lighting` and `--format all`.
  - Dark-Room Cinema Animatic Interactive Studio Gaffer HUD (`#animatic-gaffer-hud`, hotkey `G`) displaying Key/Fill/Rim 3-point lighting sliders, dynamic Key:Fill contrast ratio badge, Kelvin CCT color temperature slider with tungsten/daylight presets, and atmospheric haze density slider with status badge.
- **Autonomous Product Council Governance & Presets Expansion**:
  - Registered `PM-FEAT-009` and `PM-FEAT-010` in `ProductManagerAgent.inspect_product()`.
  - Equipped all 6 commercial domain archetypes with domain-calibrated MoCo rigs and studio lighting rigs in `omni_director/presets.py` (`get_domain_moco_rig` and `get_domain_lighting_rig`).
  - Updated prompt auditor self-healing to recognize MoCo and Lighting tokens with compliance reward scoring.
  - Remapped animatic hotkeys cleanly: Loop playback to `O` / `o`, Safe Guides to `U` / `u`, MoCo HUD to `K` / `k`, and Gaffer HUD to `G` / `g`.

## [2.4.0] - 2026-11-04

### Added (Senior Product Manager Roadmap & Autonomous Product Council Release)
- **PM-FEAT-007: Cinematic Optical Lens & Sensor Framing Suite**:
  - Module: `omni_director/tools/optical_lens.py`.
  - Added `SensorFormat`, `AnamorphicSqueeze`, and `OpticalLensSpec` schemas modeling standard physical sensor dimensions (Super35, Full Frame, ARRI LF, IMAX 70mm, VistaVision) and anamorphic squeeze factors (1.0x to 2.0x).
  - Exact trigonometric Field of View (`calculate_sensor_fov`) and hyperfocal distance calculations (`calculate_hyperfocal_distance`).
  - CRAFT camera grammar prompt token formatting (`format_optical_prompt_token`) embedding sensor size, lens series, focal length, T-stop, squeeze factor, and distortion profile.
  - Optical lens metadata CSV export (`export_lens_metadata_csv` and `export_lens_metadata_file`) via `omni export --format lens` and `--format all`.
  - Dark-Room Cinema Animatic Interactive Viewfinder HUD (`#animatic-viewfinder-overlay`, hotkey `V`) displaying 90% action-safe, 80% title-safe, 2.39:1 / 1.85:1 aspect crop lines, center crosshairs, and live optical badges (`.badge-lens`).
- **PM-FEAT-008: Virtual Production LED Volume & Unreal Engine Stage Manifest / In-Camera VFX (ICVFX) Config**:
  - Module: `omni_director/tools/virtual_production.py`.
  - Added `LedWallGeometry`, `DmxLightingFixture`, and `VirtualProductionStageSpec` schemas modeling curved LED volumes, active ceiling canopies, DMX512 intelligent lighting rigs, and ACEScg OCIO color calibration.
  - Unreal Engine 5.4 nDisplay stage configuration manifest generator (`export_ue_ndisplay_manifest`).
  - GrandMA3 / Avolites DMX lighting patch sheet CSV generator (`export_dmx_patch_csv`).
  - Virtual Production production bundle packaging (`export_virtual_production_bundle`) via `omni export --format vp` and `--format all`.
  - Dark-Room Cinema Animatic Virtual Production Stage Modal (`#animatic-vp-stage-modal`, hotkey `P`) rendering an interactive top-down vector schematic of curved LED walls, active ceiling canopy, tracked camera position, and dynamic frustum.
- **Autonomous Product Council Governance Expansion**:
  - Integrated `PM-FEAT-007` and `PM-FEAT-008` verification into `ProductCouncilOrchestrator` across `council-strategist` and `council-ux-designer`.
  - Added `convene_council` entrypoint to `ProductCouncilOrchestrator`.
  - Equipped all 6 commercial domain archetypes with domain-calibrated optical lens packages and virtual production stage specifications.

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
