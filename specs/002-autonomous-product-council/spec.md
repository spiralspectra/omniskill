---
id: "002-autonomous-product-council"
title: "Autonomous Product Council, Field Diagnostics, Domain Synthesis & Interactive Animatic Studio (v2.1)"
version: "2.1.0"
status: "done"
size: "standard"
complexity: "medium"
owner: "OmniSkill Product Council"
repo: "spiralspectra/omniskill"
created_at: "2026-10-28"
target_models:
  lead_director: "gemini-4-argon"
  prompt_workers: "gemini-3.8-flash"
  visual_artist: "gemini-3-pro-image"
  video_audio: "gemini-omni-1.1-flash-preview"
---

# Specification: 002-autonomous-product-council

## 1. Overview & Why
While `001-omni-movie-director` established the core 6-stage multi-agent pipeline and 4 Golden Presets, an initial four-persona Product Council audit (Forward Deployed Engineer, Agent Systems Engineer, Agent Strategist, and UX/UI Storyboard Designer) uncovered critical field, architectural, strategic, and UX gaps:
1. **Runtime Blockers in Python 3.12 & ADK 2.0**: `omni_director/tools/nano_banana.py` crashes at import time due to `scene: SceneKeyframeSpec | any` (evaluating built-in `any` instead of `typing.Any`), and `omni_director/agents/agent.py` fails under installed `google-adk` because `BaseAgent` uses Pydantic `extra="forbid"`.
2. **FDE Field Gaps**: No preflight diagnostic command (`omni doctor`), no ability to ingest pre-authored `MasterProductionBible` JSON files (`--bible-file`), and no structured execution telemetry (`telemetry.json`).
3. **Agent Engineering & Council Governance Gaps**: No programmatic `ProductCouncilOrchestrator` or prompt self-healing retry loop (`heal_omni_scene_prompt`) to automatically audit, score, and repair production bundles across the four council disciplines.
4. **Strategic Custom Brief Chasm**: Custom user briefs fall back to generic camera rigs and foley rather than domain-specific commercial cinematography, and the repo lacks a binding `AGENTS.md` law file and portable `skills/omni-product-council/SKILL.md` skill.
5. **Static Storyboard UX**: `storyboard_preview.html` lacks an interactive real-time animatic playhead scrubber that steps through scenes and beat timelines, lacks a 7-Point / Council Scorecard inspection drawer, uses blocking browser `alert()`, and misses WCAG 2.2 AA ARIA semantics and one-click JSON export.

## 2. User Stories
- **US-1 (Forward Deployed Engineer)**: As an FDE, I want `omni doctor` preflight diagnostics, `--bible-file <path.json>` direct ingestion, and structured `telemetry.json` emission so enterprise deployments and CI/CD pipelines run reliably with zero silent failures.
- **US-2 (Agent Systems Engineer)**: As an agent engineer, I want full compatibility with installed `google-adk` (`BaseAgent` with `extra="allow"`), a hardened 7-Point Prompt Auditor with automatic self-healing (`heal_omni_scene_prompt`), and a first-class `ProductCouncilOrchestrator` (`omni council` / `--council` / `--council-strict`).
- **US-3 (Agent Strategist)**: As an agent strategist, I want a 6-archetype Domain-Aware Brief Synthesizer in `CreativeDirectorAgent` with deterministic priority and fallback rules, a binding `AGENTS.md` constitution at the repo root, and a portable `skills/omni-product-council/SKILL.md` skill.
- **US-4 (UX/UI Designer)**: As a creative reviewer, I want an interactive 60fps animatic playhead scrubber in `storyboard_preview.html` that respects `bible.total_runtime_seconds` and dynamically illuminates defined scene beats, an expandable Council & 7-Point Quality Scorecard drawer, one-click JSON Bible export, and WCAG 2.2 AA accessibility with non-blocking cinema toast notifications.
- **US-5 (Autonomous Daily Routine)**: As the product owner, I want a daily recurring Product Council routine (`scripts/run_daily_council.py` + scheduled automation) that runs all 4 council evaluators across presets and custom domains, verifies tests, and outputs a structured council health report.

## 3. Observable User Flows

### Flow 1: Preflight Doctor & Custom Bible Ingestion (US-1)
1. User executes `omni doctor` or `omni-director --doctor`.
2. `run_doctor()` checks Python `>=3.11`, core packages (`pydantic`, `google-genai`, `rich`, `google-adk`), 2026 Model Matrix compliance (failing if any `3.1` model is configured), API key availability, and output directory write access.
3. If all mandatory checks pass, CLI prints a Rich status table and exits `0`; if a mandatory check fails (e.g., `DIRECTOR_MODEL="gemini-3.1-pro"`), CLI prints remediation guidance and exits `1`.
4. User executes `omni --bible-file <path_to_bible.json> -o <output_dir>`.
5. `load_bible_from_json()` validates the file against `MasterProductionBible` (accepting either a raw `MasterProductionBible` JSON or a `ProductionBundle` JSON containing a `"bible"` key).
6. If validation fails, CLI prints field-level validation errors and exits `1`. If valid, `DirectorPipeline.run_from_bible()` executes Stages 3–6, writes `storyboard_preview.html`, `production_bundle.json`, and `telemetry.json`, and exits `0`.

### Flow 2: Product Council Evaluation & Self-Healing Loop (US-2)
1. User or automation executes `omni council` (when invoked without `--preset`, `--prompt`/`--input`, or `--bible-file`, it defaults to `--all-presets` and audits all 4 built-in Golden Presets) or `omni --preset ikea-asmr --council` (or calls `ProductCouncilOrchestrator().audit(result, auto_heal=True)`).
2. If any scene prompt fails the hardened 7-Point Prompt Auditor (e.g., markdown header `#` or HTML `<h1..6>`, missing `1.0x` real-time speed lock, missing foley cue, or missing Mode B continuity marker on scene index `> 1`), `heal_omni_scene_prompt()` runs an iterative pass up to `max_attempts=3` (re-running `audit_omni_scene_prompt()` on each pass and repairing remaining failed rule checks).
3. `ProductCouncilOrchestrator` evaluates the bundle across all 4 council personas (FDE: 25 pts, Agent Engineer: 25 pts, Agent Strategist: 25 pts, UX/UI Designer: 25 pts -> 100 pts total) and emits a typed `ProductCouncilReport`.
4. CLI displays the Rich Council Scorecard table and writes `<output_dir>/council_audit_report.json`.
5. If `--council-strict` is enabled and `report.overall_score < 88.0` or `report.critical_findings_count > 0`, CLI exits with code `2`.

### Flow 3: 6-Archetype Domain-Aware Custom Brief Synthesis (US-3)
1. User executes `omni --prompt "<custom brief>" -o <output_dir>`.
2. `classify_brief_domain(brief_text)` counts keyword matches across the 6 commercial archetypes in deterministic priority order:
   1. `automotive_robotics` (vehicles, drones, robotics, hypercars, motorsports)
   2. `culinary_asmr` (food, coffee, matcha, cooking, beverage, kitchen)
   3. `luxury_fashion` (fashion, runway, cosmetics, perfume, couture, jewelry)
   4. `kinetic_action` (sports, running, martial arts, parkour, athletics, dance)
   5. `tech_hardware` (semiconductors, smartphones, laptops, CNC aluminum, optics, wearables)
   6. `architectural_sanctuary` (architecture, interior, furniture, brutalist, home, pavilion)
   It selects the archetype with the highest match count (breaking ties by the priority list above) and falls back to `"architectural_sanctuary"` when zero keywords match.
3. `synthesize_custom_bible()` populates genre-authentic CRAFT camera rigs (e.g., Russian Arm 28mm Anamorphic, 100mm Macro Probe Lens, 24mm Tilt-Shift, CNC Motion Control Arm), lighting Kelvin palettes, diegetic foley cues, and positive invariants while preserving the user's custom subject and never hijacking built-in preset brand titles.

### Flow 4: Interactive 60fps Animatic Screening Room & Accessibility (US-4)
1. User opens `storyboard_preview.html` in a browser.
2. User clicks `#btn-play-animatic` (`▶ PLAY ANIMATIC`) or presses `P` / `Space`.
3. JavaScript `AnimaticPlayer` runs a 60fps timer across `totalDuration = bible.total_runtime_seconds || (bible.scenes.length * 10.0)`, apportioning `sceneDuration = totalDuration / bible.scenes.length` per scene, updating `#smpte-timecode`, advancing `.scrubber-fill`, highlighting the active `.scene-card`, and toggling `.active-beat` on the scene's actual defined `action_beats` (using `[0.0s - 3.0s]`, `[3.0s - 7.0s]`, `[7.0s - 10.0s]` for 3-beat 10s scenes, or proportional windows `[i * sceneDuration / K, (i + 1) * sceneDuration / K]` for $K = \text{len}(\text{action\_beats})$ so ghost beats are never illuminated).
4. User clicks the **7-Point & Council Scorecard** toggle on any scene card (or header badge) to inspect the 7-rule verification checklist and Council persona scores.
5. User clicks `#btn-export-bible` (`EXPORT BIBLE JSON`) or presses `D` to download the embedded `MasterProductionBible` JSON via a client-side `Blob`, triggering a non-blocking `.cinema-toast` notification and updating `#a11y-announcer` (`aria-live="polite"`).

### Flow 5: Autonomous Daily Council Routine (US-5)
1. Daily cron automation or operator runs `python3 scripts/run_daily_council.py` (or `omni council --all-presets`).
2. The runner executes `run_doctor()`, audits all 4 Golden Presets plus custom domain briefs through `ProductCouncilOrchestrator(auto_heal=True)`, verifies all scores $\ge 88.0 / 100$, and writes `outputs/council_daily_report.json` and `outputs/council_daily_summary.md`.

## 4. Functional Requirements

### 4.1 Core Runtime & ADK 2.0 Compatibility (FR-1)
- **FR-1.1 (Flow 1, Flow 2)**: Fix `omni_director/tools/nano_banana.py` line 332 so `render_scene_keyframe_svg` uses `Union[SceneKeyframeSpec, Any]` from `typing` instead of built-in `any`.
- **FR-1.2 (Flow 2)**: Configure `model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)` on all ADK agent classes in `omni_director/agents/agent.py` and `omni_director/agents/council.py`, and map `instruction` kwargs cleanly to `description` when calling `super().__init__()` on `google.adk.agents.BaseAgent`.

### 4.2 FDE Diagnostics, Bible Ingestion & Telemetry (FR-2)
- **FR-2.1 (Flow 1)**: Implement `omni_director/doctor.py` with `CheckStatus`, `DiagnosticCheck`, `DoctorReport`, and `run_doctor(config)` verifying Python `>=3.11`, packages, 2026 Model Matrix, credentials, and output directory permissions.
- **FR-2.2 (Flow 1)**: Implement `load_bible_from_json(file_path)` in `omni_director/schemas.py` and `DirectorPipeline.run_from_bible(bible, ...)` in `omni_director/agents/agent.py`, exposed via `--bible-file` / `-b` in `omni_director/cli.py`.
- **FR-2.3 (Flow 1)**: Implement `omni_director/telemetry.py` with `StageTiming` and `RuntimeTelemetry`, writing `<output_dir>/telemetry.json` on every pipeline run and supporting `--json` stdout output in `omni_director/cli.py`.

### 4.3 Hardened Prompt Auditor, Self-Healing & Product Council Engine (FR-3)
- **FR-3.1 (Flow 2)**: Harden `audit_omni_scene_prompt()` in `omni_director/tools/prompt_auditor.py` to detect HTML heading tags (`<h1>`–`<h6>`), enforce Mode B continuity on any scene with `scene_index > 1` when `storytelling_mode == StorytellingMode.MODE_B_CONTINUOUS_CHAIN`, and provide `heal_omni_scene_prompt(scene, audit_result, regime, storytelling_mode, max_attempts=3)` that iteratively repairs failing rules and re-verifies after each pass.
- **FR-3.2 (Flow 2)**: Add `CouncilPersona`, `CouncilFindingSeverity`, `CouncilFinding`, `PersonaReviewResult`, and `ProductCouncilReport` Pydantic v2 models to `omni_director/schemas.py`.
- **FR-3.3 (Flow 2, Flow 5)**: Implement `ProductCouncilOrchestrator` in `omni_director/agents/council.py` evaluating FDE (25 pts), Agent Engineer (25 pts), Agent Strategist (25 pts), and UX/UI Designer (25 pts) for a 100-point rubric (`passed = overall_score >= 88.0 and critical_findings_count == 0`), integrated into `DirectorPipeline` and CLI (`omni council` defaulting to all 4 presets when no single target is given, `--council`, and `--council-strict` exiting with code `2` on failure).

### 4.4 Domain-Aware Brief Synthesis, Law & Portable Council Skill (FR-4)
- **FR-4.1 (Flow 3)**: Implement `classify_brief_domain(brief_text)` and 6-archetype synthesis templates (`automotive_robotics`, `culinary_asmr`, `luxury_fashion`, `kinetic_action`, `tech_hardware`, `architectural_sanctuary`) in `omni_director/presets.py` with deterministic keyword match counting, priority tie-breaking, and fallback to `"architectural_sanctuary"` when zero keywords match, wired into `CreativeDirectorAgent.synthesize_custom_bible()`.
- **FR-4.2 (US-3)**: Create `AGENTS.md` at the repository root codifying the 2026 Model Matrix, Spark Spec workflow, Zero-Video-Before-Storyboard rule, and Product Council 88/100 quality gate.
- **FR-4.3 (US-3)**: Create `skills/omni-product-council/SKILL.md` defining the portable 4-persona Product Council skill, 100-point rubric, and self-improvement workflow.

### 4.5 Interactive 60fps Animatic Screening Room & WCAG 2.2 AA UX (FR-5)
- **FR-5.1 (Flow 4)**: Upgrade `compile_storyboard_html()` in `omni_director/tools/html_compiler.py` with:
  - Interactive animatic playhead controls (`#btn-play-animatic`, `#smpte-timecode`, `.scrubber-track`, speed selector `0.5x`/`1.0x`/`1.5x`/`2.0x`, hotkeys `P`/`Space`/`[`/`]`/`R`/`D`/`?`) scaled to `bible.total_runtime_seconds`.
  - Dynamic beat timecode tags (`[0.0s - 3.0s]`, `[3.0s - 7.0s]`, `[7.0s - 10.0s]` for 3-beat 10s scenes, or proportional windows for variable runtime/beat counts) and `.active-beat` illumination only on defined beats in `scene.action_beats`.
  - Per-scene expandable **7-Point Audit & Council Scorecard Drawer** and header readiness badge.
  - Aspect-ratio-aware `.scene-visual-frame` (`16:9`, `9:16`, `1:1`, `2.39:1`) and safe-action/title guides in `nano_banana.py`.
  - One-click `#btn-export-bible` JSON download button, non-blocking `.cinema-toast` notifications (zero `alert()` calls), and WCAG 2.2 AA ARIA attributes (`role="banner"`, `role="main"`, `role="region"`, `role="timer"`, `aria-live="polite"`).

### 4.6 Daily Product Council Routine (FR-6)
- **FR-6.1 (Flow 5)**: Create `scripts/run_daily_council.py` (and `omni council --all-presets`) to execute daily council audits across all Golden Presets and custom domain briefs, regenerate `examples/` with the upgraded v2.1 HTML/SVG/JSON/Council artifacts, and configure the daily recurring schedule.

## 5. Testable Acceptance Criteria (AC-1 through AC-10)

| ID | Flow / Story | Acceptance Criterion | Verification Method |
| :--- | :--- | :--- | :--- |
| **AC-1** | Flow 1, Flow 2 | Importing `omni_director` and instantiating all 9 agent classes + `ProductCouncilOrchestrator` succeeds under Python 3.12 with real `google-adk` installed (`extra="forbid"` on `BaseAgent` handled cleanly). | `pytest tests/test_director_suite.py` |
| **AC-2** | Flow 1 | `run_doctor()` and `omni doctor` / `omni --doctor` validate Python version, packages, 2026 Model Matrix, and output dir permissions, returning exit code `0` on valid config and `1` when a legacy `3.1` model is supplied. | Automated unit & CLI tests in `test_director_suite.py`. |
| **AC-3** | Flow 1 | `load_bible_from_json()` and `omni --bible-file <path.json>` load and compile both raw `MasterProductionBible` JSON and `ProductionBundle` JSON files end-to-end, and raise descriptive `ValueError` on malformed JSON. | Automated test in `test_director_suite.py`. |
| **AC-4** | Flow 1 | Every `DirectorPipeline` run emits `<output_dir>/telemetry.json` containing `session_id`, `model_matrix`, `stage_timings`, `total_duration_ms`, and `audit_summary` with zero leaked API keys. | Automated test in `test_director_suite.py`. |
| **AC-5** | Flow 2 | `heal_omni_scene_prompt()` iteratively repairs prompts containing markdown/HTML headers (`#`, `<h1>`), missing `1.0x` real-time locks, missing foley cues, or missing Mode B continuity transitions so they pass all 7 points of `audit_omni_scene_prompt()`. | Automated unit test in `test_director_suite.py`. |
| **AC-6** | Flow 2, Flow 5 | `ProductCouncilOrchestrator.audit()` evaluates FDE, Agent Engineer, Agent Strategist, and UX/UI Designer personas (25 pts each = 100 pts), scores all 4 Golden Presets $\ge 90.0 / 100.0$ with `passed=True` (exit code `0`), writes `council_audit_report.json`, and causes CLI `--council-strict` to exit with code `2` when evaluating an unhealed defective bundle (`overall_score < 88.0` or `critical_findings_count > 0`). | Automated positive & negative falsification tests in `test_director_suite.py`. |
| **AC-7** | Flow 3 | `classify_brief_domain()` and `synthesize_custom_bible()` accurately classify briefs across all 6 commercial archetypes (`automotive_robotics`, `culinary_asmr`, `luxury_fashion`, `kinetic_action`, `tech_hardware`, `architectural_sanctuary`), respect priority tie-breaking and fallback to `architectural_sanctuary` on unmatched prompts, and pass 7-point audit without hijacking preset titles. | Automated test in `test_director_suite.py`. |
| **AC-8** | Flow 4 | Compiled `storyboard_preview.html` contains `#btn-play-animatic`, `#smpte-timecode` scaled to `bible.total_runtime_seconds`, `.scrubber-track`, dynamic beat timecode badges matching `len(scene.action_beats)`, `.audit-drawer` 7-point breakdown, `#btn-export-bible`, `aria-live="polite"`, and zero blocking `alert(` calls. | Automated DOM/string assertion tests in `test_director_suite.py`. |
| **AC-9** | US-3, US-5 | `AGENTS.md`, `skills/omni-product-council/SKILL.md`, and `scripts/run_daily_council.py` exist, are complete, and `python3 scripts/run_daily_council.py` exits `0`. | File existence & subprocess execution test. |
| **AC-10** | All | Full test suite (`python3 -m pytest tests/test_director_suite.py -v`) exits `0` with 100% pass rate, and all `examples/*_2_0/` bundles are updated with v2.1 artifacts. | `python3 -m pytest tests/test_director_suite.py -v` |
