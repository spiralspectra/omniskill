# Omni Movie Director Law & Constitution (`AGENTS.md`)

This repository is governed by the constitutional rules set forth in this file. All agents, subagents, and human contributors working within this codebase MUST strictly adhere to these invariant laws without exception.

---

## 1. Purpose & Architecture of Omni-Director (`v2.1.0`)

Omni Movie Director is an industrial-grade **Google Agent Development Kit 2.0 (`google.adk`)** multi-agent cinematic production system orchestrating the 2026 Gemini Model Matrix. It synthesizes full-length cinematic treatments, visual continuity bibles, synchronized diegetic audio specifications, and SMPTE-accurate interactive animatics from raw creative briefs.

### Core Architectural Hierarchy
1. **Single Source of Truth (SSOT)**: The `MasterProductionBible` is synthesized by `CreativeDirectorAgent` and remains immutable throughout the downstream pipeline.
2. **Specialized Agent Topology**:
   - `IntakeAndResearchAgent`: Parses creative brief, genre tags, and classifies commercial domains.
   - `CreativeDirectorAgent`: Formulates the `MasterProductionBible`, 3-tier visual contracts, and regime rules.
   - `VisualStoryboardAgent`: Generates Nano Banana SVG visual plates for characters, environments, and keyframes.
   - `ParallelScenePromptAgent` & `ScenePromptAgent`: Fan out parallel scene prompts with CRAFT camera grammar and kinetic chains.
   - `BGMComposerAgent`: Authors musical blueprints with tempo, key, stems, and Lyria prompts.
   - `PromptAuditorAgent`: Evaluates prompts against the 7-Point Gemini Omni Prompting Standard and applies self-healing.
   - `OptionalOmniVideoRenderAgent`: Zero-credit offline simulation by default; live render only when explicitly requested.
   - `StoryboardHTMLCompilerAgent`: Generates dark-room cinema HTML5 animatic with SMPTE scrubber and exportable JSON.
   - `ProductCouncilOrchestrator`: Multi-persona governance board auditing technical, architectural, strategic, and UX excellence.

---

## 2. Strict 2026 Model Matrix Law

Under DeepMind 2026 architectural directives, legacy models are strictly deprecated and prohibited.

### Permitted Models
| Pipeline Role | Model Identifier | Config Key |
|---|---|---|
| **Lead Creative Director** | `gemini-4-argon` | `DIRECTOR_MODEL` |
| **Fast Workhorse Fan-Out** | `gemini-3.8-flash` | `FAST_MODEL` |
| **Visual Concept & Continuity** | `gemini-3-pro-image` | `IMAGE_MODEL` |
| **Video & Multimodal Audio** | `gemini-omni-1.1-flash-preview` | `VIDEO_MODEL` |

### Invariant Prohibition Law
- **Strictly Prohibited**: NEVER introduce, reference, configure, or test any legacy third-generation point-one model string in any code, prompt, configuration, test, or documentation file.
- Any attempt to use unapproved models will immediately fail runtime validation via `omni_director.doctor.run_doctor()`.

---

## 3. Autonomous Product Council Protocol

All production bundles and codebase modifications are subject to review by the autonomous 4-persona Product Council:

### The Four Personas (100-Point Rubric)
1. **Forward Deployed Engineer (`council-fde`, 25 Points)**:
   - Validates Python compatibility, dependency health, zero-leak telemetry, and preflight doctor status.
2. **Agent Systems Engineer (`council-agent-engineer`, 25 Points)**:
   - Enforces Pydantic contract integrity, 7-point prompt compliance, self-healing loop convergence, and ADK agent isolation.
3. **Agent Strategist (`council-strategist`, 25 Points)**:
   - Evaluates commercial viability across the 6 domain archetypes (`automotive_robotics`, `culinary_asmr`, `luxury_fashion`, `kinetic_action`, `tech_hardware`, `architectural_sanctuary`), brand alignment, and storytelling mode adherence.
4. **UX/UI Storyboard Designer (`council-ux-designer`, 25 Points)**:
   - Audits the dark-room cinema animatic, SMPTE timecode accuracy at 24fps, beat timeline illumination, WCAG 2.2 AA accessibility, keyboard navigation, and zero-alert non-blocking UI.

### Quality Gates
- **Passing Threshold**: Composite score $\ge 88.0 / 100.0$ and `critical_findings_count == 0`.
- **Excellence Standard**: Canonical showcase bundles must maintain a composite score $\ge 90.0 / 100.0$.
- **Per-Scene Quality Gate**: Every scene prompt must achieve an audit score $\ge 90 / 100$ before reaching the compiler.
- **Strict Enforcement**: CLI `--council-strict` exits with status `2` on any bundle failing the quality gate.

---

## 4. Zero-Video-Before-Storyboard Invariant

- Video rendering (`gemini-omni-1.1-flash-preview`) is never executed until the storyboard, visual plates, prompt audits, and production bible are completely synthesized and validated.
- Default pipeline execution operates in dry-run/simulation mode (`render_video=False`), generating crisp SVG vector plates and zero API billable costs.
- Live video rendering requires explicit user intent (`--render-video`).

---

## 5. Verification Commands & Daily Council Runner

Every change in this repository must be verified by running the canonical test commands:

```bash
# 1. Full Pytest Verification Suite
python3 -m pytest tests/test_director_suite.py -v

# 2. Daily Autonomous Product Council Routine
python3 scripts/run_daily_council.py
```

"Done" claims require both commands to exit `0` with concrete evidence displayed.
