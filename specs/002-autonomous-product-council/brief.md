# Clarity Brief: 002-autonomous-product-council

## 1. Outcome & Non-Goals

### Outcome
Upgrade `omniskill` (`omni-movie-director` v2.1.0) into a self-auditing, continuously improving multi-agent production studio governed by a four-discipline **Product Council** (Forward Deployed Engineer, Agent Systems Engineer, Agent Strategist, and UX/UI Storyboard Designer). This specification resolves critical Python 3.12 and Google ADK 2.0 runtime blockers, introduces preflight diagnostics (`omni doctor`), adds direct custom `MasterProductionBible` JSON ingestion (`--bible-file`), replaces generic fallback brief synthesis with a 6-archetype Domain-Aware Synthesizer, upgrades the Dark-Room Cinema HTML viewer into a 60fps interactive animatic screening room with a dynamic beat playhead scrubber and Council Quality Scorecard, codifies repository law (`AGENTS.md`) and a portable council skill (`skills/omni-product-council/SKILL.md`), and establishes an automated daily Product Council routine.

### Non-Goals
- Modifying or weakening the 2026 Model Matrix (`gemini-4-argon`, `gemini-3.8-flash`, `gemini-3-pro-image`, `gemini-omni-1.1-flash-preview`) or permitting legacy 3.1 models (`gemini-3.1-*`, `veo-3.1-*`).
- Introducing external server or CDN dependencies into `storyboard_preview.html` (must remain 100% standalone single-file HTML).
- Replacing the core 6-stage pipeline contract established in `001-omni-movie-director`.

---

## 2. User Stories

- **US-1 (Forward Deployed Engineer — FDE)**: As an FDE deploying `omni-movie-director` into customer environments and CI/CD pipelines, I want to run `omni doctor` (or `omni --doctor`) to verify Python runtime, ADK 2.0 compatibility, 2026 model compliance, and filesystem permissions, ingest pre-authored `MasterProductionBible` JSON files via `--bible-file`, and collect structured `telemetry.json` traces on every run.
- **US-2 (Agent Systems Engineer)**: As an agent engineer, I want all ADK 2.0 agent classes to work seamlessly with `google-adk`'s Pydantic v2 `BaseAgent` (`extra="forbid"`), execute a hardened 7-Point Prompt Auditor with automatic self-healing retry loops (`heal_omni_scene_prompt`), and invoke a programmatic `ProductCouncilOrchestrator` (`omni council` / `--council` / `--council-strict`) that scores and heals production bundles across all 4 council personas.
- **US-3 (Agent Strategist)**: As an agent strategist, I want custom user briefs to be classified into 6 rich commercial archetypes (*Automotive & Robotics*, *Culinary ASMR & Beverage*, *Luxury Fashion & Beauty*, *Architectural & Spatial Sanctuary*, *Kinetic Action & Extreme Sports*, *Tech Hardware & CMF Design*) with deterministic tie-breaking and fallback, governed by a binding `AGENTS.md` constitution and a portable `skills/omni-product-council/SKILL.md` skill.
- **US-4 (Cinema & Developer UX/UI Designer)**: As a creative reviewer or director, I want an interactive 60fps animatic timeline scrubber in `storyboard_preview.html` that steps through each scene across `bible.total_runtime_seconds` and illuminates the defined beats in real time, displays an expandable 7-Point & Product Council Quality Scorecard drawer, supports one-click JSON Bible export, and meets WCAG 2.2 AA accessibility (`role`, `aria-label`, `aria-live`, non-blocking cinema toast notifications).
- **US-5 (Autonomous Product Operations)**: As the repository maintainer, I want a daily recurring Product Council routine (`scripts/run_daily_council.py` + scheduled automation) that audits all presets and custom archetypes, executes self-healing, verifies the test suite, and emits a dated council health report.

---

## 3. Observable User Flows

### Flow 1: FDE Preflight Diagnostics & Custom Bible Ingestion
1. Operator runs `omni doctor` (or `omni-director --doctor`).
2. `run_doctor()` inspects Python version (`>=3.11`), `pydantic`, `google-genai`, `rich`, `google.adk` BaseAgent compatibility, 2026 Model Matrix compliance, API key status, and output directory write permissions.
3. Terminal displays a Rich diagnostic table with `PASS` / `WARN` / `FAIL` badges and exits `0` when healthy (or `1` if a mandatory check fails, such as a banned `3.1` model).
4. Operator runs `omni --bible-file path/to/bible.json --output-dir ./outputs/custom_bible --council`.
5. CLI loads and validates the `MasterProductionBible` JSON, skips Stage 1 & 2 synthesis, runs Stages 3–6, writes `telemetry.json` and `council_audit_report.json`, and exits `0`.

### Flow 2: Programmatic & CLI Product Council Audit with Auto-Healing
1. User or daily automation runs `omni council` (which defaults to auditing all 4 built-in Golden Presets when no single preset/brief/bible is passed) or `omni --preset ikea-asmr --council`.
2. `ProductCouncilOrchestrator` fans out evaluation across four specialist personas:
   - **Forward Deployed Engineer (FDE)** (25 pts)
   - **Agent Systems Engineer (AE)** (25 pts)
   - **Agent Strategist (AS)** (25 pts)
   - **UX/UI Storyboard Designer (UX)** (25 pts)
3. If a scene prompt or bible contains remediable defects (e.g., markdown headers, missing `1.0x` real-time speed lock, missing foley cue, or missing Mode B continuity phrase), `auto_heal=True` iteratively repairs defects via `heal_omni_scene_prompt` (up to `max_attempts=3`, re-auditing after each rule pass).
4. `ProductCouncilOrchestrator` returns a typed `ProductCouncilReport` (0–100 score, persona breakdowns, findings, healed actions) and saves `council_audit_report.json`.
5. If `--council-strict` is passed and `overall_score < 88.0` (or `critical_findings_count > 0`), the CLI exits with code `2`.

### Flow 3: Domain-Aware Custom Brief Synthesis
1. User runs `omni --prompt "A high-speed autonomous carbon-fiber hypercar drifting through a rain-slicked Tokyo tunnel at night"`.
2. `classify_brief_domain(brief_text)` counts keyword matches across the 6 commercial archetypes in deterministic priority order (`["automotive_robotics", "culinary_asmr", "luxury_fashion", "kinetic_action", "tech_hardware", "architectural_sanctuary"]`), selecting the highest match count (breaking ties by priority order) and falling back to `"architectural_sanctuary"` when zero keywords match.
3. `synthesize_custom_bible()` constructs a `MasterProductionBible` with domain-specific CRAFT camera rigs, colour script hexes, diegetic acoustic foley, and positive physical invariants that pass all 7 points of the Prompt Auditor without hijacking preset titles.

### Flow 4: Interactive 60fps Animatic Screening Room & Council Scorecard UX
1. Reviewer opens `storyboard_preview.html` in any browser with zero network or local server dependencies.
2. Reviewer clicks `▶ PLAY ANIMATIC` (or presses `P` / `Space`).
3. The timeline playhead advances across `totalDuration = bible.total_runtime_seconds` (falling back to `len(bible.scenes) * 10.0`), updating the SMPTE timecode display (`00:00:00.0`), spotlighting the active scene card, and dynamically illuminating the scene's defined `action_beats` (e.g., `[0.0s–3.0s]`, `[3.0s–7.0s]`, `[7.0s–10.0s]` for a 3-beat 10s scene, or proportional sub-windows for $K \in \{1, 2, 3\}$ beats) in real time.
4. Reviewer opens the **Product Council & 7-Point Quality Scorecard Drawer** to inspect per-scene rule compliance and clicks **EXPORT BIBLE JSON** (or presses `D`) to download the standalone `MasterProductionBible` JSON blob, triggering a non-blocking ARIA-accessible cinema toast notification.

---

## 4. Constraints, Data Touched & Assumptions

- **Binding 2026 Model Matrix**: `gemini-4-argon`, `gemini-3.8-flash`, `gemini-3-pro-image`, `gemini-omni-1.1-flash-preview`. Zero `3.1` models permitted anywhere in code or config.
- **Assumptions Recorded (`assumed:` for unattended `/goal` execution)**:
  - `assumed`: Daily recurring Product Council routine should be scheduled at `09:00` local time via both Antigravity's scheduled sidecar config and an active daemon schedule, plus a standalone CLI entry `omni council` / `scripts/run_daily_council.py`.
  - `assumed`: The Product Council merge/readiness gate threshold is `88.0 / 100.0` (with zero `CRITICAL` findings).

---

## 5. Complexity Assessment

- **Overall Complexity**: `Medium`
- **Drivers**:
  - **Blast Radius**: Touches `omni_director/schemas.py`, `omni_director/agents/agent.py`, `omni_director/tools/nano_banana.py`, `omni_director/tools/prompt_auditor.py`, `omni_director/tools/html_compiler.py`, `omni_director/cli.py`, and adds `omni_director/doctor.py`, `omni_director/telemetry.py`, `omni_director/agents/council.py`, `AGENTS.md`, `skills/omni-product-council/SKILL.md`, `scripts/run_daily_council.py`, and expanded tests in `tests/test_director_suite.py`.
  - **Novelty**: Extends the existing Pydantic v2 and ADK 2.0 patterns cleanly without breaking any existing public API exports.
  - **Risk**: Low; all changes are deterministic, backwards-compatible with existing tests, and verified offline in dry-run mode.
