---
id: "001-omni-movie-director"
title: "Omni Movie Director: 2026 Commercial & Film Multi-Agent Pipeline"
version: "2.0.0"
status: "in-progress"
owner: "Ashik Kay <ashikkay@google.com>"
repo: "spiralspectra/omniskill"
created_at: "2026-10-27"
target_models:
  lead_director: "gemini-4-argon"
  prompt_workers: "gemini-3.8-flash"
  visual_artist: "gemini-3-pro-image"
  video_audio: "gemini-omni-1.1-flash-preview"
---

# Specification: 001-omni-movie-director

## 1. Overview & Objectives
The `001-omni-movie-director` specification establishes the end-to-end creative and technical framework for AI-directed commercial, narrative, and social video production. It bridges portable in-editor prompt intelligence (`skills/`) and an autonomous Google ADK 2.0 multi-agent system (`omni_director/`) to eliminate context rot, prevent visual drift across cuts, enforce physical realism, and synchronize multimodal audio.

## 2. User Stories
- **US-1 (Creative Director)**: As a creative director, I want to convert raw commercial briefs into a structured, typed Master Production Bible defining character profiles, environment plates, camera rigs, and sonic curves.
- **US-2 (Storyboard Artist)**: As a storyboard artist, I want to generate 3-anchor concept art using Nano Banana (`gemini-3-pro-image`) that strictly abides by Gemini Omni's 3-reference image ceiling and prevents multi-subject feature bleed.
- **US-3 (Prompt Director)**: As a prompt director, I want to generate seamless natural-prose Gemini Omni prompts that enforce Seedance 5-part kinetic contact chains, CRAFT camera telemetry, and 1.0x real-time speed locks.
- **US-4 (Sonic Specialist)**: As a sound designer, I want to generate embedded diegetic foley and dialogue within video prompts alongside a standalone Master BGM score prompt for Lyria / `<audio>` reference.
- **US-5 (Reviewer / Producer)**: As a reviewer, I want to view an interactive dark-room HTML animatic player (`storyboard_preview.html`) that allows timeline scrubbing, prompt copying, and audio-visual verification before rendering live video.
- **US-6 (Developer / Systems Engineer)**: As an engineer, I want an ADK 2.0 package runnable via CLI with `--dry-run`, `--hybrid`, and `--render-video` options and automated pytest coverage.

## 3. Observable User Flows

### Flow 1: Interactive Agent Skill Execution (In-IDE / Chat)
1. User supplies a logline, product concept, or URL.
2. The agent executes the 5-Question Director's Intake Protocol (or applies smart defaults if in non-interactive mode).
3. The agent outputs the Master Production Bible JSON.
4. The agent writes prompt specifications for Nano Banana 3-Anchor generation (Turnaround, Master Environment Plate, Scene Keyframes).
5. The agent synthesizes Gemini Omni scene prompts for Scene 1 through $N$ abiding by `gemini-omni-prompting`.
6. The agent delivers `storyboard_preview.html` and `production_bundle.json`.

### Flow 2: ADK 2.0 Automated Pipeline Run (CLI / Headless)
1. User invokes `omni run --input brief.json --mode hybrid`.
2. `IntakeAndResearchAgent` enriches the brief via `google_search` and `load_web_page`.
3. `CreativeDirectorAgent` (`gemini-4-argon`) generates the Pydantic `ProductionBible`.
4. `VisualBibleGeneratorAgent` and `StoryboardParallelAgent` generate PNG visual anchors via Nano Banana.
5. `ScenePromptFanOutAgent` (`ParallelAgent` over `gemini-3.8-flash`) concurrently writes prompt recipes for all scenes while `BGMComposerAgent` generates the musical score.
6. `StoryboardHTMLCompilerAgent` compiles the standalone `storyboard_preview.html` and exports `production_bundle.json`.
7. If `--render-video` is active, `OptionalOmniVideoRenderAgent` calls `gemini-omni-1.1-flash-preview` to render final MP4 clips with synchronized audio.

## 4. Functional Requirements

### 4.1 Intake & Creative Bible (Stage 1 & 2)
- **FR-1.1**: The intake protocol must ask at most 5 high-leverage clarifying questions covering: Narrative Tone/Regime, Aspect Ratio, Storytelling Mode (Mode A vs Mode B), Hero Anchors/Wardrobe Polarity, and Sonic Architecture.
- **FR-1.2**: If input is unguided, the system must apply smart defaults (16:9 for cinema, 9:16 for fashion/beauty, Regime 2 for commercial products/combat, Mode A for commercials, Mode B for continuous action).
- **FR-1.3**: The Master Production Bible must serialize into strict Pydantic v2 / JSON Schema adhering to `ProductionBible`.
- **FR-1.4**: All character profiles must mandate High-Contrast Wardrobe Polarity to prevent limb blending in multi-subject scenes.
- **FR-1.5**: All environment plates must enforce the Zero-Character Isolation Rule.

### 4.2 Visual Continuity & Pre-Visualization (Stage 3)
- **FR-2.1**: The system must enforce Gemini Omni's ceiling of at most 3 reference images:
  * `<image_1>`: Character Turnaround (`CHAR_TURNAROUND`) — 3-panel orthographic sheet (Front, 3/4, Profile) on 18% gray.
  * `<image_2>`: Master Environment Plate (`ENV_MASTER_PLATE`) — Zero-character architectural and lighting plate.
  * `<image_3>`: Scene Keyframe (`SCENE_KEYFRAME`) — Shot-by-shot $t=0.0s$ composition and blocking.
- **FR-2.2**: Every video prompt must include an explicit "One Job Per Reference" inclusion and exclusion clause.
- **FR-2.3**: Concept art generation must support 2x2 storyboard grids (Mode G) and boundary frame pairs (Mode F) where applicable.

### 4.3 Sonic Architecture (Stage 4)
- **FR-3.1**: The system must synthesize a dual-layer audio architecture:
  * Layer 1: Synchronized diegetic sound effects (foley, dialogue, acoustics) embedded directly in the Gemini Omni prompt.
  * Layer 2: Standalone Master BGM score prompt specifying BPM, key signature, instrumentation, dynamic curve, and Lyria prompt.
- **FR-3.2**: Audio edit instructions must include visual protection clauses to prevent latent re-rolling.

### 4.4 Scene Prompt Synthesis & Seedance Kinetic Engine (Stage 5)
- **FR-4.1**: Scene prompts must strictly comply with the 5 Core Elements of `gemini-omni-prompting`: Framing & Motion, Action, Location, Lighting, Style & Audio.
- **FR-4.2**: Kinetic scenes (Regime 2) must include:
  * The 5-Part Kinetic Contact Chain ($\text{Initiation} \to \text{Contact Point} \to \text{Force Transfer} \to \text{Environmental Evidence} \to \text{Recovery Stance}$).
  * CRAFT Camera Routing Telemetry (Composition, Route, Action Anchor, Focus/Axis Invariant, Tone/Rig).
  * Explicit Real-Time Speed & Gravity Lock: `"All action occurs at natural, real-time 1.0x playback speed with no slow motion, no time-ramping, and no floating. Heavy physical gravity and unyielding ground friction govern the scene."`
  * Maximum 3 serialized cause-and-effect action beats per 8-10s window.
  * Positive physical invariants statement: `"One continuous shot, no jump cuts, no slow motion, no duplicated limbs, and no object morphing."`
- **FR-4.3**: Gemini Omni prose prompts must contain **zero internal markdown headings** to prevent text rendering artifacts.

### 4.5 Packaging, Preview & Delivery (Stage 6)
- **FR-5.1**: The compiler must generate an interactive dark-room cinema HTML animatic player (`storyboard_preview.html`) containing:
  * Project header and color script swatches with click-to-copy hex codes.
  * Character and Environment Reference Bible visual cards with prompt reveal drawers.
  * Sonic Blueprint HUD and BGM audio player.
  * Shot-by-shot widescreen cards featuring Nano Banana pre-vis images, CRAFT camera telemetry HUD, 3-beat action timelines, reference tags, and one-click copy prompt buttons with toast feedback.
  * Fullscreen cinema theater mode with keyboard navigation (`Left`/`Right` arrows, `Spacebar`, `C`).
- **FR-5.2**: The compiler must export a machine-readable `production_bundle.json` containing the complete bible, prompts, asset paths, and metadata.

## 5. Non-Functional Requirements
- **NFR-1 (Model Tiering)**: Strictly use `gemini-4-argon` for creative direction, `gemini-3.8-flash` for prompt specialists, `gemini-3-pro-image` for concept art, and `gemini-omni-1.1-flash-preview` for video. Zero active usage of legacy 3.1 models.
- **NFR-2 (Latency & Cost Control)**: Dry-run execution must finish in under 3 seconds with zero billable API requests. Hybrid runs must complete in under 45 seconds without triggering expensive video rendering.
- **NFR-3 (Portability)**: Skills under `skills/` must be 100% self-contained Markdown files compatible with standard Agent Skill specifications.
- **NFR-4 (Packaging & Quality)**: Built on `uv` with PEP 621 metadata, comprehensive unit/mock tests, and strict linting.

## 6. Testable Acceptance Criteria (AC-1 through AC-10)

| ID | Category | Requirement Description | Verification Method |
| :--- | :--- | :--- | :--- |
| **AC-1** | Registry & Spec | `specs/registry.md` lists `001-omni-movie-director` as dedicated/medium/building, accompanied by complete brief, spec, plan, and tasks. | File presence and content verification. |
| **AC-2** | Foundational Skill | `skills/gemini-omni-prompting/SKILL.md` contains valid YAML frontmatter and all 7 core sections (Prescription Spectrum, 5 Core Elements, DeepMind Capabilities, Seedance Upgrades 4.1-4.6, 4-Step LLM Workflow, 10 Templates, 7-Item Checklist). Active models prescribe `gemini-omni-1.1-flash-preview`. | Static inspection and rule check. |
| **AC-3** | Director Skill Scope | `skills/omni-movie-director/SKILL.md` is an exhaustive (400+ lines) production skill covering all 6 stages, prohibiting 3.1 models, and referencing sub-specifications. | Line count and content audit. |
| **AC-4** | Intake Protocol | The Director skill documents the 5 high-leverage intake questions and smart default heuristics for unguided inputs. | Text audit of Stage 1. |
| **AC-5** | Master Production Bible | Stage 2 and `references/director-intake-and-bible.md` provide complete Pydantic v2 schemas and JSON schemas for Character, Environment, CRAFT Rig, Sonic Blueprint, and Scene Prompts. | Schema parsing and validation test. |
| **AC-6** | Nano Banana 3-Anchor System | Stage 3 and `references/nano-banana-storyboard-system.md` provide exact templates for Anchor 1 (Turnaround on 18% gray), Anchor 2 (Zero-Character Master Plate), and Anchor 3 (Scene Keyframe), enforcing the $\le 3$ reference image ceiling. | Prompt template and tag audit. |
| **AC-7** | Dual-Layer Sonic Design | Stage 4 specifies embedded diegetic sound in video prompts and standalone Master BGM score prompt with Lyria prompt string. | Content verification. |
| **AC-8** | Seedance Kinetic Prompting | Stage 5 enforces 5-part contact chain, CRAFT telemetry, 1.0x real-time speed lock, serialized 3-beat lanes, and zero internal markdown headers in final Omni prompts. | Regex and prompt formatting audit. |
| **AC-9** | Reference Libraries | All 4 reference markdown files exist under `skills/omni-movie-director/references/` covering intake/bible, storyboard system, ADK 2.0 DAG, and golden demos (IKEA ASMR 2.0 + SEPHORA Mode A & Mode B). | File presence and markdown audit. |
| **AC-10** | Dual-Mode Support | Both Mode A (Parallel Montage) and Mode B (Continuous +10s Scene Extension Chain up to 40s) are fully documented with complete operational examples. | Content inspection of golden demos. |
