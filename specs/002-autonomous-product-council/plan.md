# Implementation Plan: 002-autonomous-product-council

## 1. Executive Summary & Council Synthesis
This plan implements the recommendations of the four-persona **OmniSkill Product Council** (`council-fde`, `council-agent-engineer`, `council-strategist`, `council-ux-designer`):
1. **Forward Deployed Engineer (FDE) Track**:
   - Resolve Python 3.12 and `google-adk` `BaseAgent` runtime crashes.
   - Add `omni_director/doctor.py` (`run_doctor`, `omni doctor`, `omni --doctor`).
   - Add `load_bible_from_json()` and `--bible-file` / `-b` direct Bible JSON ingestion.
   - Add `omni_director/telemetry.py` (`RuntimeTelemetry`, `<output_dir>/telemetry.json`, `--json`).
2. **Agent Systems Engineer Track**:
   - Harden `omni_director/tools/prompt_auditor.py` with HTML header checks, Mode B scene index checks, and iterative `heal_omni_scene_prompt(max_attempts=3)`.
   - Add `CouncilPersona`, `CouncilFindingSeverity`, `CouncilFinding`, `PersonaReviewResult`, and `ProductCouncilReport` schemas to `omni_director/schemas.py`.
   - Implement `ProductCouncilOrchestrator` in `omni_director/agents/council.py` with 4 persona evaluators, 100-point rubric (`25` points each), and auto-healing loop.
3. **Agent Strategist Track**:
   - Implement `classify_brief_domain()` and 6 commercial domain archetypes (`automotive_robotics`, `culinary_asmr`, `luxury_fashion`, `kinetic_action`, `tech_hardware`, `architectural_sanctuary`) with deterministic priority tie-breaking and fallback to `architectural_sanctuary` in `omni_director/presets.py` and `CreativeDirectorAgent`.
   - Create `AGENTS.md` constitutional law at repository root.
   - Create `skills/omni-product-council/SKILL.md` portable skill.
4. **UX/UI Storyboard Designer Track**:
   - Upgrade `omni_director/tools/html_compiler.py` with a 60fps interactive `AnimaticPlayer` (`#btn-play-animatic`, `#smpte-timecode` scaled to `bible.total_runtime_seconds`, `.scrubber-track`, dynamic beat illumination adapted to `len(scene.action_beats)`), expandable per-scene 7-Point & Council Scorecard drawers, aspect-ratio-aware viewfinders, one-click `#btn-export-bible` JSON download, non-blocking `.cinema-toast` notifications, and WCAG 2.2 AA ARIA attributes.
   - Add safe-action/title guides to `omni_director/tools/nano_banana.py` and Rich CLI polish to `omni_director/cli.py`.
5. **Autonomous Daily Routine Track**:
   - Create `scripts/run_daily_council.py` and configure daily recurring automation.

---

## 2. Changes by Area (Mapped to Acceptance Criteria)

| Area / File Path | Planned Changes | Served ACs |
| :--- | :--- | :--- |
| `omni_director/tools/nano_banana.py` | Replace `scene: SceneKeyframeSpec \| any` with `Union[SceneKeyframeSpec, Any]`; add subtle broadcast safe-action (90%) and safe-title (80%) SVG guides. | AC-1, AC-8 |
| `omni_director/agents/agent.py` | Add `model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)` to all 9 agent classes; map `instruction` kwarg to `description` on `BaseAgent.__init__`; integrate `heal_omni_scene_prompt`, 6-archetype synthesis, `run_from_bible()`, `RuntimeTelemetry`, and optional `ProductCouncilOrchestrator` execution. | AC-1, AC-3, AC-4, AC-5, AC-6, AC-7 |
| `omni_director/schemas.py` | Add `load_bible_from_json()`, `CouncilPersona`, `CouncilFindingSeverity`, `CouncilFinding`, `PersonaReviewResult`, and `ProductCouncilReport`. | AC-3, AC-6 |
| `omni_director/doctor.py` | Implement `CheckStatus`, `DiagnosticCheck`, `DoctorReport`, and `run_doctor(config)` checking Python `>=3.11`, packages, 2026 Model Matrix, API keys, and output dir write access. | AC-2 |
| `omni_director/telemetry.py` | Implement `StageTiming` and `RuntimeTelemetry` with `to_dict()` and `write_json()` emitting `<output_dir>/telemetry.json` without secret leakage. | AC-4 |
| `omni_director/tools/prompt_auditor.py` | Harden 7-Point checks (HTML `<h1..6>`, Mode B `scene_index > 1`) and implement iterative `heal_omni_scene_prompt(max_attempts=3)` to repair failing prompts. | AC-5 |
| `omni_director/agents/council.py` | Implement `ProductCouncilOrchestrator` (subclassing `BaseAgent` with `extra="allow"`) evaluating FDE (25 pts), Agent Engineer (25 pts), Agent Strategist (25 pts), and UX/UI Designer (25 pts), plus `auto_heal()`. | AC-1, AC-6 |
| `omni_director/presets.py` | Add `DOMAIN_ARCHETYPES` and `classify_brief_domain(brief_text)` supporting 6 commercial domains with deterministic priority order `["automotive_robotics", "culinary_asmr", "luxury_fashion", "kinetic_action", "tech_hardware", "architectural_sanctuary"]` and fallback to `"architectural_sanctuary"`. | AC-7 |
| `omni_director/tools/html_compiler.py` | Add 60fps `AnimaticPlayer` (`#btn-play-animatic`, `#smpte-timecode` using `bible.total_runtime_seconds`, `.scrubber-track`, dynamic beat timecode badges matching `len(scene.action_beats)`, `.active-beat`), expandable `.audit-drawer` & Council scorecard, `#btn-export-bible` JSON blob download, `.cinema-toast` (zero `alert()`), and WCAG 2.2 AA ARIA landmarks/live regions. | AC-8 |
| `omni_director/cli.py` | Support `omni doctor` / `--doctor`, `omni council` (defaulting to `--all-presets` when no single target is passed) / `--council` / `--council-strict` (exiting `2` when `overall_score < 88.0` or `critical_findings_count > 0`), `--bible-file` / `-b`, and `--json` telemetry output. | AC-2, AC-3, AC-4, AC-6 |
| `omni_director/__init__.py` & `omni_director/agents/__init__.py` | Export `ProductCouncilOrchestrator`, `ProductCouncilReport`, `CouncilPersona`, `CouncilFinding`, `run_doctor`, `DoctorReport`, `RuntimeTelemetry`, `load_bible_from_json`, `classify_brief_domain`, `heal_omni_scene_prompt`. | AC-1, AC-2, AC-3, AC-5, AC-6, AC-7 |
| `AGENTS.md` & `skills/omni-product-council/SKILL.md` | Author binding repository constitution and portable Product Council skill. | AC-9 |
| `scripts/run_daily_council.py` & `examples/` | Author daily council runner script and regenerate all example bundles with v2.1 artifacts. | AC-9, AC-10 |
| `tests/test_director_suite.py` | Expand test suite to verify AC-1 through AC-10 (including `--council-strict` exit code `2` falsification, classifier fallback/tie-breaking, and variable runtime/beat animatic checks) without weakening any existing tests. | AC-1 to AC-10 |
