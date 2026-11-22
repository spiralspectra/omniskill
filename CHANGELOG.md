# Changelog

All notable changes to **Omni Movie Director** are documented in this file.

## [2.14.0] - 2026-11-22

### Added (Senior Product Manager Roadmap & Autonomous Product Council Release)
- **PM-FEAT-027: Multi-Territory Localization, ADR Dubbing Studio, Lip-Sync Timing & Safe-Supers Engine**:
  - Module: `omni_director/tools/localization_adr.py` with Pydantic contracts in `omni_director/schemas.py` (`LocaleSyncStatus`, `SupersSafeStatus`, `LocalizedLineSpec`, `AdrSpottingCueSpec`, `LocaleAdaptationSpec`, `LocalizationManifestSpec`) and 6-domain calibrations in `omni_director/presets.py` (`get_domain_localization_spec`).
  - Supports deterministic 11-territory linguistic expansion/compression (`en-US`, `de-DE`, `fr-FR`, `es-419`, `ja-JP`, `zh-CN`, `it-IT`, `ko-KR`, `pt-BR`, `ar-SA` [RTL], `da-DK`), syllable/word lip-sync drift gates (`<=1.15x LOCKED`, `1.15x-1.25x STRETCH_CAUTION`, `>1.25x RESCRIPT_REQUIRED`), safe-zone supers expansion audits aligned with `PLATFORM_SAFE_ZONES`, frame-accurate 24fps ADR spotting cues with 3-beep pre-roll, `[LOCALIZATION_ADR: ...]` CRAFT tokens (`compile_clean_omni_prompt` stripped), IMSC1 TTML XML (`subtitles_localized.ttml`), `adr_cue_sheet.csv`, `localization_manifest.json`, localized `subtitles_<locale>.srt`/`.vtt`, CLI export (`omni export --format i18n`, `--locales`, `--i18n-json`, `--adr-csv`, `--ttml`), NLE & `RuntimeTelemetry` SHA-256 registration, and Dark-Room Cinema Animatic Localization & ADR HUD (`#animatic-localization-hud`, hotkey `I`).
- **PM-FEAT-028: Editorial J-Cut / L-Cut Audio Bridge, BPM Beat-Grid Sync & Music/Foley Spotting Engine**:
  - Module: `omni_director/tools/editorial_spotting.py` with Pydantic contracts in `omni_director/schemas.py` (`AudioBridgeType`, `EditBridgeSpec`, `SpottingCueEntry`, `SpottingManifestSpec`) and 6-domain calibrations in `omni_director/presets.py` (`get_domain_spotting_spec`).
  - Computes 24fps BPM beat-grid quantization (`compute_bpm_beat_grid`), domain-calibrated J-Cut / L-Cut / JL-Overlap split-edit bridges (`build_spotting_manifest`), stem-targeted music/foley/room-tone/dialogue cues, `[SPOTTING_SYNC: ...]` CRAFT tokens (`compile_clean_omni_prompt` stripped), CMX 3600 split-edit EDL (`timeline_split_edits.edl`), `spotting_cue_sheet.csv`, `spotting_sheet.md`, `spotting_manifest.json`, FCPXML v1.10 beat-grid `<marker>` annotations in `omni_director/tools/nle_export.py`, CLI export (`omni export --format spotting`, `--spotting-json`, `--spotting-csv`, `--spotting-md`, `--split-edl`), NLE & `RuntimeTelemetry` SHA-256 registration, and Dark-Room Cinema Animatic Editorial Spotting & Beat-Grid HUD (`#animatic-spotting-hud`, hotkey `J`).
- **Cross-Cutting Council, UX, CLI, Telemetry & Doctor Fixes**:
  - **Doctor Compliance**: Fixed `omni_director/doctor.py` to invoke `_validate_model_identifier()` directly so invalid models raise `ValueError` and fail `run_doctor()` validation; bumped `DEFAULT_DOCTOR_VERSION` to `"2.14.0"`.
  - **CLI & Persistence Fixes**: Removed duplicate `export_c2pa_bundle` / `export_safety_bundle` invocations in `omni_director/cli.py` (`handle_export` `--format all` already runs them via `export_all_nle_artifacts`), fixed `handle_council` to re-persist `production_bundle.json` with the attached `council_report` and refresh `telemetry.json` SHA-256 checksums, and wired `i18n` / `spotting` formats and granular flags.
  - **NLE & Telemetry Integration**: Integrated `export_localization_bundle` and `export_spotting_bundle` into `export_all_nle_artifacts`, added beat-grid `<marker>` annotations to `export_fcpxml`, and registered `PM-FEAT-027` / `PM-FEAT-028` deliverables in `KNOWN_PRODUCTION_ARTIFACTS` and `SAFE_KEYS` in `omni_director/telemetry.py`.
  - **Safety & C2PA SSOT**: Added canonical `CSATF_SAFETY_BULLETINS` / `CSATF_SHORT_BULLETINS` (`get_csatf_bulletin_for_category`) in `omni_director/tools/safety_risk.py` and dynamic `__version__` provenance claims in `omni_director/tools/c2pa_provenance.py`.
  - **Dark-Room Cinema HUD & Prompt Auditor**: Aligned C2PA/Safety download filenames in `omni_director/tools/html_hud_v213.py` (`ai_disclosure_certificate.md`, `safety_bulletin.md`, `safety_jsa_matrix.csv`), expanded 5-department toolbar launchers (`[Y]`, `[Z]`, `[I]`, `[J]`) in `omni_director/tools/html_hud_v212.py`, integrated `html_hud_v214.py` in `omni_director/tools/html_compiler.py`, and updated 7-Point Prompt Auditor Rule 4/6 self-healing in `omni_director/tools/prompt_auditor.py`.

## [2.13.0] - 2026-11-21

### Added (Senior Product Manager Roadmap & Autonomous Product Council Release)
- **PM-FEAT-025: Generative AI Provenance, C2PA Content Credentials (v2.1) & Talent Likeness / Synthetic Disclosure Ledger**:
  - Module: `omni_director/tools/c2pa_provenance.py` with Pydantic contracts in `omni_director/schemas.py` (`SyntheticDisclosureTier`, `C2paActionType`, `LikenessConsentStatus`, `C2paIngredientSpec`, `C2paAssertionActionSpec`, `TalentLikenessRecordSpec`, `SceneC2paProvenanceSpec`, `MasterC2paProvenanceSpec`) and 6-domain calibrations in `omni_director/presets.py`.
  - Enforces 2026 Model Matrix lineage verification (`verify_model_lineage_2026`), deterministic prompt lineage SHA-256 digests (`compute_prompt_lineage_digest`), EU AI Act Article 50 & SynthID disclosure compliance, SAG-AFTRA digital replica consent tracking, `[C2PA_PROVENANCE: ...]` CRAFT tokens (`compile_clean_omni_prompt` stripped), CLI export (`omni export --format c2pa`), NLE & `RuntimeTelemetry` checksum registration, and interactive Dark-Room Cinema Animatic C2PA Provenance HUD (`#animatic-c2pa-hud`, `#c2pa-lineage-svg`, hotkey `Y`).
- **PM-FEAT-026: On-Set Stunt, Pyro/SFX, Rigging & Environmental Safety Risk Assessment Matrix (JSA & Call-Sheet Safety Bulletin)**:
  - Module: `omni_director/tools/safety_risk.py` with Pydantic contracts in `omni_director/schemas.py` (`SafetyHazardCategory`, `RiskSeverityLevel`, `SafetySignoffStatus`, `SafetyHazardControlSpec`, `StandbyMedicalAndEmergencySpec`, `SceneSafetyRiskSpec`, `MasterSafetyRiskSpec`) and 6-domain calibrations in `omni_director/presets.py`.
  - Computes physics-derived kinetic exclusion zones (`calculate_kinetic_exclusion_zone_m`), scene hazard assessments (`assess_scene_hazards`) with CSATF Safety Bulletin references, standby medical/emergency plans, `[SAFETY_JSA: ...]` CRAFT tokens (`compile_clean_omni_prompt` stripped), `call_sheet.md` Section 5 On-Set Safety Summary, CLI export (`omni export --format safety`), NLE & `RuntimeTelemetry` checksum registration, and interactive Dark-Room Cinema Animatic Safety JSA & Perimeter HUD (`#animatic-safety-hud`, `#safety-perimeter-svg`, hotkey `Z`).
- **Cross-Cutting Council, CLI, Telemetry & UX/WCAG 2.2 AA Fixes**:
  - Fixed `_buildDynamicReviewFCPXML()` scene duration/relative marker offsets and `_buildDynamicReviewMD()` Markdown pipe escaping in `omni_director/tools/html_hud_v212.py`.
  - Fixed `.hud-sticky-shell` header/transport-bar overlap, `<g>` Spacebar propagation collision, case-insensitive `</script>` & `html.escape` protection, card `audit_rep.score` display, Rule 7 `.audit-drawer` row, `isContentEditable` guard, and `Tab` modal focus trapping across `omni_director/tools/html_compiler.py` and `omni_director/tools/html_hud_v212.py`.
  - Wired `omni council --all-presets` alias deduplication and automatic `telemetry.json` refresh in `omni export` (`--refresh-telemetry`) in `omni_director/cli.py`, added `SECRET_PATTERN` zero-leak telemetry/bundle scanning in `ProductCouncilOrchestrator._review_fde()`, and updated `README.md` to `v2.13.0`.

## [2.12.0] - 2026-11-20

### Added (Senior Product Manager Roadmap & Autonomous Product Council Release)
- **PM-FEAT-023: Inter-Scene Editorial Continuity, 180-Degree Axis & Overhead Blocking Floorplan Engine**:
  - Module: `omni_director/tools/continuity_blocking.py` with corresponding Pydantic schemas in `omni_director/schemas.py` and 6-archetype domain calibrations in `omni_director/presets.py`.
  - Enforces 180-degree line-of-action continuity, screen-direction locks, eyeline match pairs, and overhead 2D stage floorplan blocking coordinates across consecutive scenes.
  - CRAFT prompt token formatting (`[CONTINUITY_AXIS: ...]`), CLI export support (`omni export --format continuity`), NLE & `RuntimeTelemetry` checksum integration, and Dark-Room Cinema Animatic Overhead Blocking & 180° Axis HUD (`#animatic-blocking-hud`, hotkey `W`).
- **PM-FEAT-024: Client Review, Frame-Accurate Pin Annotation, NLE Markers & Revision Sign-Off Engine**:
  - Module: `omni_director/tools/review_notes.py` with corresponding Pydantic schemas in `omni_director/schemas.py`.
  - Supports frame-accurate spatial pin annotations, CMX 3600 `* LOC:` DaVinci Resolve markers, FCPXML `<marker>` timeline annotations, Frame.io JSON review payloads, and Markdown Revision Sign-Off reports.
  - CLI export support (`omni export --format review`), NLE & `RuntimeTelemetry` checksum integration, and Dark-Room Cinema Animatic Client Review & Revision Sign-Off HUD (`#animatic-review-hud`, hotkey `N`).
- **Cross-Cutting Council, Pipeline & UX Fixes**:
  - Fixed `--mode continuous` / `extension` propagation in `CreativeDirectorAgent`.
  - Added `compile_clean_omni_prompt` normalization prior to live `gemini-omni-1.1-flash-preview` video rendering and enforced the `ready_for_live_render` gate.
  - Eliminated duplicate export I/O across `omni_director/cli.py` and `scripts/run_daily_council.py`, and unified `RuntimeTelemetry` SHA-256 artifact checksum discovery.
  - Organized `.hud-actions` into 5 WCAG 2.2 AA departmental toolbar groups via `omni_director/tools/html_hud_v212.py`.

## [2.11.0] - 2026-11-19

### Added (Senior Product Manager Roadmap & Autonomous Product Council Release)
- **PM-FEAT-021: Multi-Aspect Social Reframe, Safe-Zone Cropping & Cutdown Delivery Engine (`16:9` -> `9:16` / `4:5` / `1:1` / `2.39:1` & `:30s` / `:15s` / `:06s` Cutdowns)**:
  - Module: `omni_director/tools/delivery_reframe.py`.
  - Added schemas in `omni_director/schemas.py`: `DeliverableAspectRatio`, `CutdownFormatType`, `SocialDeliveryPlatform`, `ReframePanMode`, `AspectCropWindowSpec`, `CutdownSegmentSpec`, `CutdownVersionSpec`, `SceneReframeSpec`, and `DeliveryReframeManifestSpec` (plus `ReframeManifest` / `SceneReframe` aliases). Bound `reframe_spec` to `ScenePromptSpec` and `master_reframe_manifest` to `MasterProductionBible`.
  - Implemented pan-and-scan crop window calculation (`calculate_aspect_crop_window`), platform UI overlay safe-zone clearance auditing (`check_platform_ui_clearance` for Broadcast TV, TikTok 9:16, Instagram Reels 9:16, YouTube Shorts 9:16, Meta 4:5, Cinema 2.39:1), and automated broadcast/social editorial cutdown synthesis (`synthesize_cutdown_versions`).
  - Implemented multi-format deliverables: crop & safe-zone matrix CSV (`reframe_crop_matrix.csv`), CMX 3600 cutdown EDLs (`cutdown_30s.edl`, `cutdown_15s.edl`, `cutdown_06s.edl`), FCPXML v1.10 vertical reframe timeline (`reframe_9x16.fcpxml`), JSON manifest (`delivery_reframe_manifest.json`), and complete bundle export (`export_reframe_bundle`).
  - CRAFT prompt token formatting (`format_reframe_prompt_token`) and Dark-Room Cinema Animatic Multi-Aspect Social Reframe HUD (`#animatic-reframe-hud`, hotkey `R`).
- **PM-FEAT-022: Broadcast QC, ITU-R BT.1702 / Harding FPA PSE Flash-Safety, ATSC A/85 & EBU R128 Loudness, Ad-ID Trafficking Slate & Legal Rights Clearance Engine**:
  - Module: `omni_director/tools/broadcast_qc.py`.
  - Added schemas in `omni_director/schemas.py`: `BroadcastLoudnessStandard`, `ClearanceCategory`, `ClearanceStatus`, `QcVerdictStatus`, `BroadcastTraffickingSlateSpec`, `LoudnessComplianceSpec`, `PseFlashCheckSpec`, `ClearanceRecordSpec`, `SceneQcProfileSpec`, and `MasterBroadcastQcSpec` (plus `BroadcastQcSpec` / `BroadcastQcManifest` / `SceneQcSpec` aliases). Bound `broadcast_qc` to `ScenePromptSpec` and `master_broadcast_qc` to `MasterProductionBible`.
  - Implemented ITU-R BT.1702 / Ofcom Harding FPA photosensitive epilepsy flash-safety evaluation (`evaluate_scene_pse_safety`), ATSC A/85 / EBU R128 / Streaming AES / DCP loudness validation (`validate_loudness_target`), and rights clearance matrix synthesis (`synthesize_rights_clearances`).
  - Implemented multi-format Broadcast QC deliverables: Executive Markdown QC Certificate (`broadcast_qc_certificate.md`), Rights & Clearances Matrix CSV (`rights_clearance_matrix.csv`), JSON manifest (`broadcast_qc_manifest.json`), and complete bundle export (`export_broadcast_qc_bundle`).
  - CRAFT prompt token formatting (`format_broadcast_qc_prompt_token`) and Dark-Room Cinema Animatic Broadcast QC & Rights Clearance HUD (`#animatic-qc-hud`, hotkey `Q`).
- **CLI, NLE Export, Telemetry & Council Runtime Fixes**:
  - `omni_director/doctor.py`: Replaced hardcoded `"2.6.0"` version in `DoctorReport` with `DEFAULT_DOCTOR_VERSION` (`2.11.0`).
  - `omni_director/telemetry.py`: Extended `known_artifact_names` SHA-256 verification coverage across all PM-FEAT-013..022 artifacts.
  - `omni_director/tools/nle_export.py`: Added PM-FEAT-015..018 (`hdr`, `stripboard`, `film`, `slate`) and PM-FEAT-021..022 (`reframe`, `qc`) bundles to `export_all_nle_artifacts`, coerced `Path -> str`, and replaced silent `except Exception: pass` blocks with `logger.warning`.
  - `omni_director/cli.py`: Added `--format reframe` and `--format qc`, wired missing granular flags (`--webaudio-config`, `--hdr-json`, `--hlg-xml`, `--resolve-hdr`, `--movie-magic-xml`, `--stripboard-csv`, `--dood-csv`, `--reframe-csv`, `--cutdown-edl`, `--reframe-fcpxml`, `--reframe-json`, `--qc-cert`, `--clearance-csv`, `--qc-json`), and unified `--format all` and `--export-nle` parity across PM-FEAT-001..022 with post-export `telemetry.json` manifest refresh.
  - `scripts/run_daily_council.py`: Fixed `export_hdr_bundle(bundle.bible, out_path)` so scene HDR telemetry populates, standardized on `lens_package.csv` (removing duplicate `optical_lens_framing.csv`), deduplicated `nle_artifacts_exported`, and hardened `bump_project_version` with targeted regex replacements.

## [2.10.0] - 2026-11-17

### Added (Senior Product Manager Roadmap & Autonomous Product Council Release)
- **PM-FEAT-019: Aerial Drone Flight Paths, GPS Waypoints, Gimbal Stabilization & Ephemeris Solar Position Calculator (DJI/Freefly KML/GPX Export & FAA Part 107 Airspace Compliance)**:
  - Modules: `omni_director/tools/drone_aerial.py` and `omni_director/tools/drone_flight.py`.
  - Added schemas in `omni_director/schemas.py`: `DroneRigType` (`fpv_racing_drone`, `heavy_lift_octocopter`, `cinema_quadcopter`, `cablecam_hybrid`), `FlightWaypointGPS` (WGS84 lat/lon, altitude AGL & MSL, speed in m/s, heading, pitch/yaw, action cue), `GimbalOrientationSpec` (3-axis gimbal limits, pitch/roll/yaw damping, target POI tracking), `SolarPhase` (`golden_hour`, `blue_hour`, `high_noon`, `civil_twilight`, `night`), `SolarEphemerisSpec` (solar elevation, solar azimuth, shadow length multiplier, CCT Kelvin, golden hour status, lens flare risk), `WindDriftVectorSpec` (wind speed, wind direction, crab angle, lateral drift offset), and `DroneFlightPathSpec`. Bound `drone_flight` to `ScenePromptSpec` and `master_drone_spec` to `MasterProductionBible`.
  - Implemented aeronautical and astronomical algorithms: Jean Meeus / SunCalc solar ephemeris calculations (`calculate_solar_ephemeris`), wind vector resolution and crab angle math (`calculate_wind_drift_vector`), Haversine 3D distance calculations, 3-axis mechanical gimbal angle clamping and point-to-point targeting (`calculate_gimbal_angles`), and multi-waypoint flight path synthesis with FAA Part 107 120m AGL ceiling checks.
  - Implemented multi-format flight plan exports: OGC KML v2.2 with 3D LineString (`generate_drone_flight_kml` / `generate_kml_flight_path` -> `flight_path.kml`), GPX 1.1 route waypoints (`generate_drone_flight_gpx` / `generate_gpx_flight_path` -> `flight_waypoints.gpx`), Showbiz telemetry CSV (`generate_drone_flight_sheet_csv` -> `drone_flight_sheet.csv`), Markdown flight log (`generate_drone_flight_sheet_md` -> `drone_flight_sheet.md`), JSON manifest (`generate_drone_flight_manifest_json` -> `drone_flight_manifest.json`), and complete drone flight bundle packaging (`export_drone_flight_bundle` / `export_drone_bundle`).
  - CRAFT prompt token formatting (`format_drone_flight_prompt_token`) embedding rig type, altitude, flight profile, gimbal pitch, speed, and wind/solar conditions (`[DRONE_FLIGHT: ...]`).
  - CLI export support: `omni export --format drone`, `--format all`, `--drone-kml`, and `--drone-gpx`.
  - Dark-Room Cinema Animatic Interactive Drone Flight HUD (`#animatic-drone-hud`, hotkey `D`, toggle button `#btn-drone-animatic`) featuring 2D flight path canvas (`#drone-path-canvas`), dynamic trajectory glow lines, solar ephemeris SVG compass rose (`#solar-azimuth-line`, `#solar-azimuth-dot`), gimbal pitch and wind drift gauges, FAA Part 107 compliance badges, and instant download buttons for KML, GPX, and CSV flight sheets.
- **PM-FEAT-020: AICP Commercial Production Bid Specification & Line-Item Budget Top-Sheet Engine (Crew Labor Tiers, Equipment Packages, Location Permitting & Cost-per-Second Analytics)**:
  - Module: `omni_director/tools/aicp_budget.py`.
  - Added schemas in `omni_director/schemas.py`: `AicpSectionCode` (Sections A through N covering Above-The-Line, Below-The-Line, Fringes, Insurance, Production Fee, and Contingency), `CrewLaborTier` (`dga_director`, `iatse_600_dp`, `dga_1st_ad`, `iatse_728_gaffer`, `local_80_key_grip`, `local_695_sound_mixer`, `local_600_dit`, `faa_part_107_pilot`), `AicpLineItemSpec`, `AicpTopSheetSummarySpec` (ATL/BTL totals, 23.5% payroll fringes, 3.2% production insurance, 18% production fee, 10% contingency reserve, grand total bid, cost-per-second), and `MasterAicpBidSpec`. Bound `master_aicp_bid` to `MasterProductionBible`.
  - Implemented commercial financial algorithms: Standard union labor rate tables (`UNION_DAY_RATES`), full AICP financial aggregation (`calculate_aicp_top_sheet`), proportional scene budget distribution (`allocate_scene_budgets`), and domain-calibrated budget synthesis.
  - Implemented multi-format commercial bid exports: Showbiz / Hot Budget compatible CSV (`generate_aicp_bid_sheet_csv` -> `aicp_bid_sheet.csv`), Executive C-suite Top Sheet markdown summary (`generate_aicp_topsheet_md` -> `production_budget_topsheet.md`), machine-readable JSON manifest (`generate_aicp_bid_manifest_json` -> `aicp_bid_manifest.json`), and complete commercial budget packaging (`export_aicp_budget_bundle`).
  - CLI export support: `omni export --format aicp`, `--format all`, `--aicp-csv`, and `--aicp-json`.
  - Dark-Room Cinema Animatic Interactive AICP Commercial Bid HUD (`#animatic-aicp-hud`, hotkey `A`, toggle button `#btn-aicp-animatic`) featuring 5-metric executive top-sheet financial cards, HTML5 Canvas financial allocation doughnut chart (`#aicp-doughnut-canvas`), live Cost-Per-Second ticker, interactive Sections A–K line-item accordion, and instant download buttons for AICP CSV, JSON, and Markdown summaries.
- **Autonomous Product Council Governance & Presets Expansion**:
  - Registered `PM-FEAT-019` and `PM-FEAT-020` in `ProductManagerAgent.inspect_product()` as P0 implemented features with full problem statements, solutions, and target modules.
  - Equipped all 6 commercial domain archetypes with domain-calibrated drone flight specs (`get_domain_drone_spec`) and AICP commercial production bids (`get_domain_aicp_bid_spec`) in `omni_director/presets.py`.
  - Updated prompt auditor Rule 4 and self-healing loop in `omni_director/tools/prompt_auditor.py` to evaluate and inject drone flight CRAFT tokens with compliance reward scoring.
  - Integrated full 25.0/25.0 scoring in `ProductCouncilOrchestrator` across `council-fde`, `council-agent-engineer`, `council-strategist`, and `council-ux-designer`.

## [2.9.0] - 2026-11-10

### Added (Senior Product Manager Roadmap & Autonomous Product Council Release)
- **PM-FEAT-017: Cinematic Film Stock, Granular Halation & Gate Weave Physics Emulation Suite (Kodak/Fuji 35mm/16mm/65mm & Resolve DCTL/ALE Export)**:
  - Module: `omni_director/tools/film_emulation.py`.
  - Added schemas in `omni_director/schemas.py`: `FilmStockManufacturer` (`kodak`, `fuji`, `ilford`, `agfa`), `FilmGaugeFormat` (`gauge_16mm`, `gauge_35mm_2perf`, `gauge_35mm_3perf`, `gauge_35mm_4perf`, `gauge_65mm_imax`), `GrainPhysicsSpec` (RMS granularity, grain diameter, shadow/midtone/highlight weights), `HalationPhysicsSpec` (halation radius, intensity, rem-jet opacity, specular threshold, chromatic tint), `GateWeavePhysicsSpec` (lateral drift, vertical judder, pin tolerance, frequency), and `FilmStockSpec` (full emulsion profile). Bound `film_emulation` to `ScenePromptSpec` and `master_film_emulation` to `MasterProductionBible`.
  - Implemented photochemical physics algorithms: microscopic RMS grain density distribution (`calculate_rms_grain_density`), Point Spread Function (PSF) rem-jet halation scattering (`simulate_halation_psf`), and mechanical gate weave transport judder (`calculate_gate_weave_offsets`).
  - Implemented multi-format post-production exports: DaVinci Resolve GPU DCTL shader (`generate_davinci_dctl_shader` -> `film_stock_shader.dctl`), Avid Log Exchange film manifest (`export_film_stock_ale` -> `film_stock.ale`), and complete film emulation bundle packaging (`export_film_emulation_bundle`).
  - CRAFT prompt token formatting (`format_film_emulation_prompt_token`) embedding stock name, gauge, RMS grain density, halation radius, and gate weave drift.
  - CLI export support: `omni export --format film`, `--format all`, `--film-dctl`, and `--film-ale`.
  - Dark-Room Cinema Animatic Interactive Film Stock HUD (`#animatic-film-hud`, hotkey `E`) featuring real-time grain, halation, gate weave, and chemical push/pull sliders, visual specification badges, and instant download buttons for DaVinci Resolve DCTL and Avid ALE.
- **PM-FEAT-018: Smart Clapper Slate, DIT Media Hash List (ASC MHL v2.0) & SMPTE 12M Timecode Sync Suite**:
  - Module: `omni_director/tools/clapper_slate.py`.
  - Added schemas in `omni_director/schemas.py`: `TimecodeDropFrameMode` (`non_drop_frame_ndf`, `drop_frame_df`), `Smpte12MTimecodeSpec` (frame-accurate 24fps timecode), `ClapperSlateSpec` (scene, take, camera roll, sound roll, camera ID, FPS, day/night, int/ext, filter pack, shutter angle, director, DP), `AscMhlHashEntry` (per-file cryptographic digests), `AscMhlManifestSpec` (ASC-MHL v2.0 XML manifest), and `MasterProductionSlateSpec`. Bound `clapper_slate` to `ScenePromptSpec` and `master_slate_spec` to `MasterProductionBible`.
  - Implemented frame-accurate SMPTE 12M timecode arithmetic (`calculate_smpte12m_frames`, `format_smpte12m_timecode`), dual-system sound sync transient offset calculation (`calculate_sound_sync_offset`), and cryptographic ASC-MHL v2.0 XML generation (`generate_asc_mhl_xml`) with xxHash64, SHA-1, and MD5 hashes.
  - Implemented multi-format production slate exports: ASC-MHL v2.0 XML manifest (`asc_mhl_manifest.xml`), dual-system sound sync ALE (`sound_sync.ale`), production clapper slate log CSV (`clapper_slate_log.csv`), and complete slate bundle packaging (`export_slate_bundle`).
  - CRAFT prompt token formatting (`format_clapper_slate_prompt_token`) embedding scene/take, roll IDs, SMPTE timecode, shutter angle, and audio transient markers.
  - CLI export support: `omni export --format slate`, `--format all`, `--mhl-xml`, `--sound-ale`, and `--slate-csv`.
  - Dark-Room Cinema Animatic Interactive Clapper Slate HUD (`#animatic-slate-hud`, hotkey `T`) featuring an animated SVG clapper arm with spring snap animation, Web Audio API acoustic 1.2 kHz wooden clack transient synthesis, live LED SMPTE 12M timecode readout, and instant download buttons for ASC-MHL XML, Sound Sync ALE, and Slate CSV.
- **Autonomous Product Council Governance & Presets Expansion**:
  - Registered `PM-FEAT-017` and `PM-FEAT-018` in `ProductManagerAgent.inspect_product()` as P0 implemented features.
  - Equipped all 6 commercial domain archetypes with domain-calibrated film stocks (`get_domain_film_emulation_spec`) and production clapper slate schedules (`get_domain_clapper_slate_spec`) in `omni_director/presets.py`.
  - Updated prompt auditor Rule 4 and self-healing loop in `omni_director/tools/prompt_auditor.py` to evaluate and inject film stock and clapper slate CRAFT tokens with compliance reward scoring.
  - Integrated 25.0/25.0 scoring in `ProductCouncilOrchestrator` across `council-fde`, `council-agent-engineer`, `council-strategist`, and `council-ux-designer`.

## [2.8.0] - 2026-11-09

### Added (Senior Product Manager Roadmap & Autonomous Product Council Release)
- **PM-FEAT-015: SMPTE ST 2084 PQ & HLG High Dynamic Range (HDR) Video Signal, Tone Mapping & MaxFALL/MaxCLL Metadata Suite**:
  - Module: `omni_director/tools/hdr_signal.py`.
  - Added schemas in `omni_director/schemas.py`: `HdrTransferFunction`, `ColorVolumeGamut`, `ToneMappingOperator`, `HdrMasteringDisplaySpec`, `HdrMetadataSpec`, and `SceneHdrReport`. Bound `hdr_spec` to `ScenePromptSpec` and `master_hdr_spec` to `MasterProductionBible`.
  - Implemented pure-Python optical HDR physics algorithms: SMPTE ST 2084 PQ forward and inverse EOTF conversion (`pq_eotf_to_nits`, `pq_inverse_eotf`), ARIB STD-B67 HLG OETF and EOTF (`hlg_oetf`, `hlg_eotf`), parametric tone mapping operators (`reinhard_extended`, `aces_spline`, `bt_2446_method_a`, `clip`), and dynamic scene photometrics calculating peak luminance, MaxCLL, and MaxFALL from key/fill/rim lighting and material reflectance.
  - Implemented multi-format HDR broadcast exports: SMPTE ST 2086 / CTA-861.3 static metadata JSON (`export_hdr10_json`), ITU-R BT.2100 broadcast transmission manifest XML (`export_hlg_xml`), DaVinci Resolve Color Management timeline XML (`export_resolve_hdr_xml`), and complete HDR bundle packaging (`export_hdr_bundle`).
  - CRAFT camera prompt token formatting (`format_hdr_prompt_token`) embedding transfer function, target gamut, peak mastering luminance, MaxCLL, and MaxFALL.
  - CLI export support: `omni export --format hdr`, `--format all`, `--hdr-json`, `--hlg-xml`, and `--resolve-hdr`.
  - Dark-Room Cinema Animatic Interactive HDR Suite HUD (`#animatic-hdr-hud`, hotkey `H`) featuring live peak nits, MaxCLL/MaxFALL badges, transfer function badges, an interactive HTML5 Canvas waveform monitor (`#hdr-waveform-canvas`), and instant download buttons for HDR10 JSON, HLG XML, and Resolve HDR XML.
- **PM-FEAT-016: Industrial Production Script Breakdown, Stripboard & Call Scheduling Engine (Movie Magic / 1st AD Stripboards)**:
  - Module: `omni_director/tools/stripboard_scheduler.py`.
  - Added schemas in `omni_director/schemas.py`: `BreakdownCategory` (12 industry categories: cast, stunts, silent bits, vehicles, props, SFX, wardrobe, makeup, sound FX, special equipment, production notes, optical VFX), `ProductionDayType` (`int_day`, `int_night`, `ext_day`, `ext_night`), `StripboardColorCode` (`yellow_day_ext`, `blue_night_ext`, `white_day_int`, `green_night_int`), `ScriptBreakdownSheet`, `StripboardStripSpec`, `DayOutOfDaysRecord`, and `MasterStripboardScheduleSpec`. Bound `breakdown_sheet` to `ScenePromptSpec` and `master_stripboard_schedule` to `MasterProductionBible`.
  - Implemented production logistics algorithms: Hollywood 1/8th page fractions calculator (`calculate_page_eighths`), automated 12-category script breakdown extraction from scene beats, dialogue, lighting, camera, and VFX (`extract_script_breakdown_sheet`), Hollywood strip color coding (`determine_strip_color_code`), stripboard schedule sequencing with day breaks (`generate_stripboard_schedule`), and SAG-AFTRA Day-Out-of-Days matrix generator (`generate_dood_matrix`) tracking `SW`, `W`, `H`, `WF`, `SWF` codes and verifying 12-hour turnaround rest compliance.
  - Implemented multi-format production scheduling exports: Movie Magic Scheduling 10.0 XML (`export_movie_magic_xml`), Hollywood production stripboard CSV (`export_stripboard_csv`), Day-Out-of-Days talent tracking CSV (`export_dood_csv`), and scheduling bundle packaging (`export_stripboard_bundle`).
  - CRAFT prompt token formatting (`format_script_breakdown_prompt_token`) embedding scene header, strip color code, 1/8th page count, location, cast IDs, and key breakdown elements.
  - CLI export support: `omni export --format stripboard`, `--format all`, `--movie-magic-xml`, `--stripboard-csv`, and `--dood-csv`.
  - Dark-Room Cinema Animatic Interactive Stripboard HUD (`#animatic-stripboard-hud`, hotkey `B`) displaying color-coded strips (`.strip-yellow`, `.strip-blue`, `.strip-white`, `.strip-green`), day break dividers (`.strip-day-break`), interactive talent DOOD grid (`#dood-talent-table`), and instant download buttons for Movie Magic XML, Stripboard CSV, and DOOD CSV.
- **Autonomous Product Council Governance & Presets Expansion**:
  - Registered `PM-FEAT-015` and `PM-FEAT-016` in `ProductManagerAgent.inspect_product()` as P0 implemented features.
  - Equipped all 6 commercial domain archetypes with domain-calibrated HDR specs (`get_domain_hdr_spec`) and Stripboard production schedules (`get_domain_stripboard_spec`) in `omni_director/presets.py`.
  - Updated prompt auditor Rule 4 and self-healing loop in `omni_director/tools/prompt_auditor.py` to evaluate and inject HDR Signal and 1st AD Breakdown tokens with compliance reward scoring.
  - Integrated full 25.0/25.0 scoring in `ProductCouncilOrchestrator` across `council-fde`, `council-agent-engineer`, `council-strategist`, and `council-ux-designer`.

## [2.7.0] - 2026-11-07

### Added (Senior Product Manager Roadmap & Autonomous Product Council Release)
- **PM-FEAT-013: Spatial Audio & Binaural Soundfield Acoustic Simulation (Dolby Atmos 7.1.4 & Higher-Order Ambisonics)**:
  - Module: `omni_director/tools/spatial_audio.py`.
  - Added schemas in `omni_director/schemas.py`: `SpatialCoordinate3D`, `AcousticMaterialType`, `AcousticRoomImpulseResponse`, `DolbyAtmosBedFormat`, `SpatialAudioObjectSpec`, and `SpatialAudioSoundfieldSpec`. Bound `spatial_audio` to `ScenePromptSpec` and `master_spatial_audio` to `MasterProductionBible`.
  - Implemented acoustic physics algorithms: Sabine RT60 formula (`calculate_sabine_rt60`), Eyring reverberation decay (`calculate_eyring_rt60`), early reflection delay (`calculate_early_reflection_delay_ms`), 1st-order / HOA 3rd-order Ambisonics spherical harmonics B-format weights (`calculate_ambisonic_b_format`), and 3D Vector Base Amplitude Panning across 7.1.4 Dolby Atmos beds (`calculate_vbap_gains_7_1_4`).
  - Implemented multi-format spatial exports: ITU-R BS.2076 Audio Definition Model (ADM) JSON metadata (`export_dolby_atmos_adm_manifest`), Ambisonics B-format panning table CSV (`export_ambisonic_panning_table`), Web Audio API HRTF spatial panner JSON config (`export_webaudio_spatial_config`), and spatial audio bundle packaging (`export_spatial_audio_bundle`).
  - CRAFT diegetic sonic prompt token formatting (`format_spatial_audio_prompt_token`) embedding Atmos bed format, Sabine RT60 decay, wall material absorption, spatial audio object trajectory coordinates, and binaural HRTF flag.
  - CLI export support: `omni export --format spatial`, `--format all`, `--spatial-adm`, `--ambisonic-csv`, and `--webaudio-config`.
  - Dark-Room Cinema Animatic Interactive Spatial Audio & Soundfield Console HUD (`#animatic-spatial-hud`, hotkey `S`) displaying live 7.1.4 Atmos bed channel matrix, 2D radar listener position plot, room acoustics RT60 badges, and instant download buttons for ADM JSON, Ambisonics CSV, and Web Audio config.
- **PM-FEAT-014: Advanced Multi-Pass VFX Compositing & Render Layer Manifest Engine (16/32-bit OpenEXR & Cryptomatte)**:
  - Module: `omni_director/tools/vfx_compositor.py`.
  - Added schemas in `omni_director/schemas.py`: `VfxRenderPassType`, `VfxLayerChannelSpec`, `CryptomatteManifestSpec`, and `VfxCompositingManifestSpec`. Bound `vfx_compositing` to `ScenePromptSpec` and `master_vfx_manifest` to `MasterProductionBible`.
  - Implemented VFX compositing tools: 16-bit half-float and 32-bit float OpenEXR multi-layer channel manifests (`synthesize_openexr_channel_manifest`), 32-bit Murmur3 hex hash generator for Cryptomatte object/material IDs (`hash_identifier_32bit` and `generate_cryptomatte_manifest`), and automated Foundry Nuke composite script (`.nk`) template generation (`generate_nuke_composite_script`) with OCIO ACEScg color management.
  - Implemented multi-format VFX exports: OpenEXR channel manifest JSON, Cryptomatte ID sidecar JSON (`export_cryptomatte_sidecar_json`), Foundry Nuke script template (`export_nuke_comp_script`), and complete VFX compositing bundle packaging (`export_vfx_bundle`).
  - CRAFT visual prompt token formatting (`format_vfx_compositing_prompt_token`) embedding OpenEXR channel decomposition, Cryptomatte layer tags, near/far Z-depth planes, and additive beauty reconstruction formulas.
  - CLI export support: `omni export --format vfx`, `--format all`, `--vfx-manifest`, `--cryptomatte-sidecar`, and `--nuke-script`.
  - Dark-Room Cinema Animatic Interactive Multi-Pass VFX Compositing HUD (`#animatic-vfx-hud`, hotkey `X`) displaying 10-layer OpenEXR channel matrix, Cryptomatte ID badges, and instant download buttons for OpenEXR channel manifest, Cryptomatte sidecar, and Foundry Nuke `.nk` script.
- **Autonomous Product Council Governance & Presets Expansion**:
  - Registered `PM-FEAT-013` and `PM-FEAT-014` in `ProductManagerAgent.inspect_product()`.
  - Equipped all 6 commercial domain archetypes with domain-calibrated spatial audio specs (`get_domain_spatial_audio_spec`) and VFX compositing manifests (`get_domain_vfx_manifest`) in `omni_director/presets.py`.
  - Updated prompt auditor Rule 4 and self-healing loop in `omni_director/tools/prompt_auditor.py` to evaluate and inject spatial audio and VFX compositing tokens with compliance reward scoring.
  - Integrated full 25.0/25.0 scoring in `ProductCouncilOrchestrator` across `council-fde`, `council-agent-engineer`, `council-strategist`, and `council-ux-designer`.

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
