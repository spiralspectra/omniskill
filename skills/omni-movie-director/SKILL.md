---
name: omni-movie-director
description: Complete commercial and film director suite orchestrating 2026 multi-agent pipelines with Gemini 4 Argon, Gemini 3.8 Flash, Nano Banana Pro concept art, and Gemini Omni 1.1 video/audio synthesis.
---

# Omni Movie Director Suite (2026 Industrial Edition)

The `omni-movie-director` skill equips any AI agent, creative engineer, or automated system to act as a world-class commercial and narrative film director. It upgrades Ashik Kay's 2025 Opal "Beyond the Single Prompt" and `VidAgent` architecture into an industrial multi-agent pipeline powered by Google DeepMind's 2026 model generation.

---

## 1. Executive Overview & System Architecture

### 1.1 The Context-Rot Dilemma & The 2026 Multi-Agent Solution
In AI cinematography, monolithic "God-Prompts" reliably fail across five distinct failure modes:
1. **Context Rot & Token Saturation**: Shoving character turnarounds, lighting setups, narrative beats, shot geography, audio foley, and camera motion into a single prompt blows the model's reasoning budget, causing it to drop fine-grained constraints.
2. **Cross-Scene Visual Hallucination**: Without an immutable, authoritative contract, sequential scenes subtly alter character attire, facial features, or environment scale relative to prior scenes.
3. **Prompt Interference**: Audio instructions bleed into camera framing; negative prompt directives clash with character styling.
4. **Execution Bottlenecks**: Generating assets serially wastes minutes of wall-clock time and compounds failure risk.
5. **Format Non-Determinism**: Free-form text outputs corrupt structured pipeline handoffs.

The **Omni Movie Director Suite** resolves this by decomposing film production into six distinct, typed stages orchestrated across specialized model tiers:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     OMNI MOVIE DIRECTOR SUITE ARCHITECTURE                      │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   [User Creative Brief / Brand Assets / PDFs / Reference URLs]                 │
│                                │                                                │
│                                ▼                                                │
│   STAGE 1: RESOURCE GROUNDING & THE 5-QUESTION INTAKE PROTOCOL                  │
│   Model: gemini-4-argon / gemini-3.8-flash (Search & Scrape Grounding)          │
│                                │                                                │
│                                ▼                                                │
│   STAGE 2: MASTER PRODUCTION BIBLE 2.0 (SINGLE SOURCE OF TRUTH)                 │
│   Model: gemini-4-argon (Pydantic v2 JSON Contract)                             │
│   - Character Bibles (Wardrobe Polarity & Positive Invariants)                  │
│   - Environment Bibles (Kelvin Color Script & Zero-Character Plate)             │
│   - CRAFT Camera Rigs & Sonic Blueprints                                        │
│   - Mode Selection: Mode A (Parallel Montage) vs. Mode B (Continuous Oner)      │
│                                │                                                │
│                                ▼                                                │
│   STAGE 3: NANO BANANA 3-ANCHOR PRE-VISUALIZATION & STORYBOARDING               │
│   Model: gemini-3-pro-image (Nano Banana Pro)                                   │
│   - Anchor 1: Character Turnaround (3-panel orthographic sheet on 18% gray)    │
│   - Anchor 2: Master Environment Plate (Zero-character lighting plate)          │
│   - Anchor 3: Scene Keyframes (First/Last frames, 2x2 storyboard grids)         │
│                                │                                                │
│                                ▼                                                │
│   STAGE 4: DUAL-LAYER SONIC & BGM DIRECTION                                     │
│   - Layer 1: Embedded Diegetic Foley & Dialogue (Inside Video Prompts)          │
│   - Layer 2: Master BGM Track Prompt (Lyria / Google Audio / <audio> track)     │
│                                │                                                │
│                                ▼                                                │
│   STAGE 5: PARALLEL GEMINI OMNI SCENE PROMPT SYNTHESIS & AUDIT                  │
│   Model: gemini-3.8-flash (Parallel Fan-Out)                                    │
│   - 5 Core Elements & Seedance 5-Part Kinetic Contact Chains                    │
│   - 1.0x Real-Time Speed & Gravity Invariant Locks                              │
│   - "One Job Per Reference" (<image_1>, <image_2>, <image_3>) Inclusion Clause  │
│   - Clean Natural Prose (Zero Internal Markdown Headings)                       │
│                                │                                                │
│                                ▼                                                │
│   STAGE 6: CINEMA DARKROOM HTML TREATMENT & PRODUCTION BUNDLE                   │
│   - Interactive dark-room HTML player (storyboard_preview.html)                 │
│   - Complete production_bundle.json export                                      │
│   - Optional Live Video Render: gemini-omni-1.1-flash-preview                   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Strict Model Tiering Directive (2026 Standards)
All legacy Gemini 1.5, 3.1, and Veo 3.1 models are deprecated. Active production must bind strictly to the following 2026 models:

| Pipeline Role | Model Identifier | Environment Variable & Default | Rationale |
| :--- | :--- | :--- | :--- |
| **Lead Creative Director** | `gemini-4-argon` | `DIRECTOR_MODEL="gemini-4-argon"` | Complex multi-scene narrative reasoning, Pydantic schema synthesis, cinematic spatial consistency. |
| **Parallel Prompt & Sonic Specialists** | `gemini-3.8-flash` | `FAST_MODEL="gemini-3.8-flash"` | Sub-second latency, deterministic prompt formatting, rule verification. |
| **Visual Concept Art & Storyboard** | `gemini-3-pro-image` (Nano Banana Pro) | `IMAGE_MODEL="gemini-3-pro-image"` | 2K photorealistic character sheets, environment plates, and keyframes. |
| **Video & Multimodal Audio Synthesis** | `gemini-omni-1.1-flash-preview` | `OMNI_VIDEO_MODEL="gemini-omni-1.1-flash-preview"` | 720p/1080p generation, native 48kHz audio, `reference_to_video`, and continuous extension. |

---

## 2. Stage 1: Resource Grounding & The 5-Question Director's Intake Protocol

When a user provides a concept, script snippet, or brand deck, the agent grounds the project using available search tools and conducts a targeted interrogation.

### 2.1 The 5 Essential Intake Dimensions
Never overwhelm the user with open-ended questionnaires. Ask at most 5 high-leverage clarifying questions that resolve foundational parameters:

1. **Narrative Tone & Physical Regime**:
   > *"Is this film an **Atmospheric & World-Building** narrative (Regime 1: organic pacing, mood, landscapes, poetic lighting) or a **High-Kinetic / Commercial Precision** sequence (Regime 2: fast camera moves, tactile impacts, sports/combat, crisp product geometry)?"*
2. **Delivery Canvas & Aspect Ratio**:
   > *"What is your primary exhibition canvas: **16:9 Cinema Widescreen** (theatrical/YouTube), **9:16 Vertical Reel** (TikTok/Instagram Reels/SEPHORA storefront), or **1:1 Square Showcase**?"*
3. **Storytelling Mode & Runtime**:
   > *"Do you want **Mode A: Parallel Multi-Scene Montage** (4 distinct 8-10s scenes edited together like a classic commercial trailer) or **Mode B: Continuous Scene Extension** (a seamless 10s base clip extended sequentially up to 40s in a single unbroken take)?"*
4. **Hero Anchors & Visual Polarity (Characters & Products)**:
   > *"Who or what are our hero anchors? If characters: what are their high-contrast wardrobe colors and physical silhouettes (to prevent limb/clothing blend)? If a product: what are its rigid materials, logos, and non-negotiable details?"*
5. **Sonic Architecture & Musical Pulse**:
   > *"What is the auditory identity? Specify: (a) Master BGM style (e.g., Scandic Minimalist ASMR, 138 BPM UK Garage, Zimmer-esque Orchestral Crescendo), and (b) Key diegetic sounds (e.g., crisp cardboard snaps, neon hums, tactile clicks, dialogue lines)."*

### 2.2 Conversational Heuristics & Smart Defaults
If the user provides an unguided brief or runs in automated mode (`--auto` / `--dry-run`), apply these intelligent defaults:
- **Default Aspect Ratio**: `16:9` for narrative, sci-fi, and automotive; `9:16` for fashion, cosmetics, retail, and mobile sizzles.
- **Default Regime**: Commercial products with moving parts, sports, and combat $\to$ `Regime 2`; mood, landscapes, and contemplative drama $\to$ `Regime 1`.
- **Default Storytelling Mode**: `Mode A` (4 parallel scenes) for commercials and trailers; `Mode B` (continuous extension) for single-character drama or continuous action choreography.
- **Default Audio**: Synchronized diegetic foley + warm ambient cinematic score at 48kHz fidelity.

---

## 3. Stage 2: Master Production Bible 2.0 (Single Source of Truth)

The Master Production Bible is the immutable creative contract. Once sealed by `gemini-4-argon`, every downstream agent reads from it without altering foundational parameters.

### 3.1 Pydantic v2 Core Data Schema
The production bible is strictly validated using Pydantic v2:

```python
from enum import Enum
from typing import List, Optional, Dict
from pydantic import BaseModel, Field

class RegimeType(str, Enum):
    REGIME_1_ATMOSPHERIC = "Regime 1: World-Knowledge & Atmospheric Flow"
    REGIME_2_KINETIC = "Regime 2: High-Kinetic & Precision Commercial"

class StorytellingMode(str, Enum):
    MODE_A_PARALLEL_CUT = "Mode A: Parallel Multi-Scene Cut (Montage)"
    MODE_B_CONTINUOUS_CHAIN = "Mode B: Continuous Scene Extension Chain (Oner)"

class AspectRatio(str, Enum):
    RATIO_16_9 = "16:9"
    RATIO_9_16 = "9:16"
    RATIO_1_1 = "1:1"
    RATIO_2_39_1 = "2.39:1"

class CharacterWardrobe(BaseModel):
    name: str = Field(..., description="Character name or subject identifier")
    silhouette: str = Field(..., description="Distinct physical build, height, hair, silhouette")
    wardrobe_polarity: str = Field(
        ..., 
        description="High-contrast clothing colors, textures, and accents designed to prevent multi-subject limb blend"
    )
    movement_signature: str = Field(..., description="Gait, velocity, posture, physical behavior")

class EnvironmentSpec(BaseModel):
    location_name: str
    spatial_architecture: str = Field(..., description="Room dimensions, depth planes, floor materials")
    lighting_setup: str = Field(..., description="Key light source, rim light, color temperature, bounce")
    atmospheric_particles: str = Field(..., description="Air quality, dust motes, rain, mist, smoke, reflections")
    positive_invariants: List[str] = Field(
        ..., 
        description="List of physical laws and immutable fixtures that must never morph or disappear"
    )

class CameraRigSpec(BaseModel):
    rig_type: str = Field(..., description="Dolly track, Steadicam, Technocrane, Locked-off tripod, Smartphone")
    focal_length_mm: int = Field(..., description="e.g. 24mm wide, 35mm street, 50mm natural, 85mm portrait, 100mm macro")
    craft_profile: str = Field(
        ..., 
        description="CRAFT rule: Composition, Route, Action Anchor, Focus/Axis Invariant, Tone/Rig"
    )

class DiegeticSonicSpec(BaseModel):
    foley_cues: List[str] = Field(..., description="Tactile material sounds (snaps, footsteps, friction, clicks)")
    dialogue_lines: Optional[List[str]] = Field(default=[], description="Exact spoken dialogue with speaker attribution")
    room_acoustics: str = Field(..., description="Reverb decay, space dampening, environmental rumble")

class MasterBgmSpec(BaseModel):
    track_title: str
    genre_style: str = Field(..., description="e.g. Minimalist Neo-Classical ASMR, UK Garage, Cyberpunk Industrial")
    tempo_bpm: int
    key_signature: str
    instrumentation: List[str]
    dynamic_arc: str = Field(..., description="Progression across the 32-40s runtime (Intro, Build, Climax, Outro)")
    lyria_prompt: str = Field(..., description="Ready-to-use text prompt for Lyria / Google Audio generation")

class NanoBananaReference(BaseModel):
    asset_id: str = Field(..., description="e.g. <image_1>, <image_2>, <image_3>")
    job_description: str = Field(..., description="The EXACT single job this reference performs ('One Job Per Reference')")
    exclusion_clause: str = Field(..., description="Explicitly forbidden visual traits to ignore from this reference")
    generation_prompt: str = Field(..., description="Prompt used to generate this reference sheet with gemini-3-pro-image")

class ScenePromptSpec(BaseModel):
    scene_index: int = Field(..., description="1-indexed scene number")
    timestamp_range: str = Field(..., description="e.g. '00:00-00:08' or '+10s extension'")
    scene_title: str
    regime: RegimeType
    action_beats: List[str] = Field(
        ..., 
        max_length=3, 
        description="Maximum 3 serialized cause-and-effect action beats for this 8-10s window"
    )
    kinetic_contact_chain: Optional[str] = Field(
        None, 
        description="Initiation -> Contact Point -> Force Transfer -> Environmental Evidence -> Recovery Stance"
    )
    omni_prose_prompt: str = Field(
        ..., 
        description="The clean natural-language prose prompt ready to feed into Gemini Omni (NO markdown headers inside!)"
    )
    conversational_edit_deltas: Optional[List[str]] = Field(
        default=[], 
        description="Curated single-turn edit variations (e.g. Turn 2 subject/light swap)"
    )

class MasterProductionBible(BaseModel):
    project_title: str
    logline: str
    creative_regime: RegimeType
    storytelling_mode: StorytellingMode
    aspect_ratio: AspectRatio
    total_runtime_seconds: int
    characters: List[CharacterWardrobe]
    environment: EnvironmentSpec
    camera_rig: CameraRigSpec
    sonic_blueprint: DiegeticSonicSpec
    master_bgm: MasterBgmSpec
    nano_banana_assets: List[NanoBananaReference] = Field(
        ..., 
        max_length=3, 
        description="Gemini Omni accepts a maximum ceiling of 3 image references"
    )
    scenes: List[ScenePromptSpec]
```

### 3.2 Dual-Mode Storytelling Mechanics
The Creative Director selects between two fundamental modes:

```
                        ┌────────────────────────────────────────────────────────┐
                        │          Master Production Bible (SSOT 2.0)            │
                        └───────────────────────────┬────────────────────────────┘
                                                    │
                        ┌───────────────────────────┴────────────────────────────┐
                        ▼                                                        ▼
          [MODE A: Parallel Multi-Scene Cut]                      [MODE B: Continuous Extension Chain]
         Commercial Montages, Dynamic Trailers                     Cinematic Oners, Choreographed Sequences
                        │                                                        │
          ┌─────────────┴─────────────┐                                          ▼
          ▼             ▼             ▼                             [Base Clip: 00:00 - 00:10]
     [Scene 1]      [Scene 2]     [Scene 3] ... (Parallel)                       │  Interactions API
     (00-08s)       (08-16s)      (16-24s)                                       ▼
          │             │             │                             [Extension 1: +10s (00:10 - 00:20)]
          └─────────────┬─────────────┘                                          │
                        ▼                                                        ▼
            [Shared Nano Banana Assets]                             [Extension 2: +10s (00:20 - 00:30)]
            (<image_1>, <image_2>, etc.)                                         │
                        │                                                        ▼
                        ▼                                           [Extension 3: +10s (00:30 - 00:40)]
                [Montage Compiler]                                               │
              (HTML Preview / Edit Suite)                                        ▼
                                                                      [Seamless 40s Master Oner]
```

- **Mode A (Parallel Multi-Scene Cut)**:
  * Generates 4 (or $N$) discrete 8-10 second scenes concurrently via ADK `ParallelAgent`.
  * Injects identical `nano_banana_assets` (`<image_1>`, `<image_2>`, `<image_3>`) into each scene prompt to enforce cross-scene visual invariance.
  * Assembles clips in an interactive HTML5 storyboard preview with synchronized audio playback, J-cut/L-cut transitions, and prompt tuning.
- **Mode B (Continuous Scene Extension Chain)**:
  * Uses Gemini Omni 1.1's native **+10s Scene Extension** capability via the Interactions API (`interactions.create` with parent interaction chaining).
  * Starts with a 10s Base Clip establishing initial state, space, and lighting.
  * Turn 1 (+10s, 10-20s): Prompt describes the physical delta and next action beat while continuing camera trajectory.
  * Turn 2 (+10s, 20-30s): Next physical beat, dialogue exchange, and musical progression.
  * Turn 3 (+10s, 30-40s): Climax, final action resolution, and resting stance.
  * Delivers a single, fluid, 40-second continuous video without cut-points.

---

## 4. Stage 3: Nano Banana 3-Anchor Pre-Visualization & Storyboarding

### 4.1 The Rule of Pre-Visualization
> **A complete visual storyboard MUST be rendered deterministically using Nano Banana (`gemini-3-pro-image`) BEFORE generating Gemini Omni video prompts and triggering live video renders.**

Rendering visual anchors first freezes character faces, wardrobe, materials, and lighting in pixel space. Gemini Omni then operates in `reference_to_video` mode, eliminating character drift and visual pop across sequential cuts.

### 4.2 The 3-Anchor Reference Ceiling
Gemini Omni enforces an architectural ceiling of **at most 3 reference images (`<image_1>`, `<image_2>`, `<image_3>`)**. The 3-Anchor System maps strictly 1:1 to this ceiling:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     THE 3-TIER VISUAL CONTINUITY ANCHORS                        │
├────────────────────────┬────────────────────────┬───────────────────────────────┤
│ ANCHOR 1: TURNAROUND   │ ANCHOR 2: MASTER PLATE │ ANCHOR 3: SCENE KEYFRAME      │
│ Tag: <image_1>         │ Tag: <image_2>         │ Tag: <image_3>                │
├────────────────────────┼────────────────────────┼───────────────────────────────┤
│ 3-Panel Orthographic   │ Zero-Character         │ Shot-by-Shot First Frame      │
│ (Front, 3/4, Profile)  │ Architectural &        │ ($t=0.0s$) or 2x2 Storyboard  │
│ on 18% Neutral Gray    │ Lighting Ground Truth  │ Grid with CRAFT Blocking      │
└────────────────────────┴────────────────────────┴───────────────────────────────┘
```

#### Anchor 1: Character & Product Turnaround (`CHAR_TURNAROUND` / `<image_1>`)
- **Format**: 3-panel orthographic composite sheet on neutral 18% photography gray (`#7F7F7F`).
  * Panel 1 (Left): Full-body front eye-level view.
  * Panel 2 (Center): Medium 3/4 dynamic perspective.
  * Panel 3 (Right): Close-up profile portrait.
- **Lighting**: Soft diffuse 5600K balanced lighting, 1:1 ratio, zero colored gels, zero dramatic cast shadows.
- **Job Description**: Locks facial bone structure, ethnic identity, hairstyle, and wardrobe silhouette.
- **Exclusion Clause**: *"Inherit solely character features and wardrobe from <image_1>; do not copy the neutral gray studio background."*

#### Anchor 2: Master Environment & Lighting Plate (`ENV_MASTER_PLATE` / `<image_2>`)
- **Format**: Ultra-wide establishing architectural plate of the location.
- **Zero-Character Rule**: Completely empty with zero human figures or pets.
- **Lighting**: Explicit Kelvin temperature, key light angles, window shadow geometry, and atmospheric particles.
- **Job Description**: Locks room architecture, wall/floor materials, and volumetric light paths.
- **Exclusion Clause**: *"Inherit solely architectural geometry and lighting from <image_2>; do not introduce new subjects or props."*

#### Anchor 3: Scene Keyframe / Storyboard Panel (`SCENE_KEYFRAME` / `<image_3>`)
- **Format**: Shot-by-shot First Frame ($t=0.0s$) binding the Character (from Anchor 1) into the Environment (from Anchor 2).
- **Composition**: Exactly matches the CRAFT camera framing specified by the Director.
- **Job Description**: Locks camera perspective, subject placement, and initial physical posture at second 0.0.
- **Mode G Option**: A 2x2 4-panel storyboard grid illustrating the 4 narrative beats in reading order.

---

## 5. Stage 4: Dual-Layer Sonic & BGM Direction

Gemini Omni 1.1 renders video and audio jointly. To achieve commercial-grade sound, the Director orchestrates two synchronized audio layers:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                               SONIC ARCHITECTURE                                │
├────────────────────────────────────────┬────────────────────────────────────────┤
│ LAYER 1: Embedded Diegetic Sound       │ LAYER 2: Standalone Master BGM Track   │
│ (Inside Gemini Omni Video Prompt)      │ (For Lyria / Google Audio / <audio>)   │
├────────────────────────────────────────┼────────────────────────────────────────┤
│ • Tactile contact foley (clicks, snaps)│ • Master musical composition prompt    │
│ • Surface friction (wet asphalt, wood) │ • Precise BPM, Key Signature, Tempo    │
│ • Room acoustic reverberation          │ • Dynamic arc mapped to runtime        │
│ • Spoken dialogue lines with timing    │ • Instrumentation breakdown & stems    │
└────────────────────────────────────────┴────────────────────────────────────────┘
```

### 5.1 Layer 1: Embedded Diegetic Foley & Dialogue
Must be scripted directly into the Gemini Omni prose prompt:
- **Physical Contact Sounds**: Dowel snaps, cardboard tears, magnetic lipstick clicks, stiletto impacts on wet pavement.
- **Acoustic Environment**: Room size, reverberation decay (e.g., *"bright empty wooden room acoustics transitioning into warm dampened textile acoustics"*).
- **Dialogue Lines**: Exact spoken quotes with speaker tags and timestamp offsets (e.g., *"At second 02, Maya whispers: 'London, wake up.' "*).

### 5.2 Layer 2: Master BGM Track Prompt
Generates a standalone, exportable musical cue prompt suitable for Lyria or conditioning as an input `<audio>` reference:
- Musical style and subgenre.
- Explicit BPM and key signature (e.g., `84 BPM, D Major` for IKEA; `138 BPM, F Minor` for Sephora).
- Instrumentation stems (pizzicato cello, felted piano, Moog bass, skipping 2-step drums).
- 32-40s dynamic progression (Intro $\to$ Build $\to$ Peak $\to$ Outro drop).

### 5.3 Audio Failure-Mode Mitigation: Joint Coupling Rule
Because video and audio are coupled in Gemini Omni's latent space, conversational audio edits can accidentally mutate visual frames. If an audio modification is required, always prepend:
> *"Keep all visual elements, character appearance, and camera motion 100% identical. Update only the audio track..."*

---

## 6. Stage 5: Parallel Gemini Omni Scene Prompt Synthesis & Audit

Using the Master Production Bible and generated visual anchors, `gemini-3.8-flash` synthesizes scene prompts concurrently for Scene 1 through $N$.

### 6.1 Prompt Composition Standards (Adhering to `gemini-omni-prompting`)
Every scene prompt must incorporate:
1. **The 5 Core Elements**: Shot Framing & Motion, Action, Location, Lighting, Style & Audio.
2. **Seedance 5-Part Kinetic Contact Chain** (for Regime 2):
   $$\text{Initiation} \longrightarrow \text{Contact Point} \longrightarrow \text{Force Transfer} \longrightarrow \text{Environmental Evidence} \longrightarrow \text{Recovery Stance}$$
3. **Speed & Gravity Lock**:
   > *"All action occurs at natural, real-time 1.0x playback speed with no slow motion, no time-ramping, and no floating. Heavy physical gravity and unyielding ground friction govern the scene."*
4. **CRAFT Camera Telemetry**:
   - **C (Composition)**: Initial framing & subject placement.
   - **R (Route)**: Exactly one dominant trajectory per shot.
   - **A (Action Anchor)**: Camera move triggered by an on-screen physical action.
   - **F (Focus & Axis Invariant)**: Protection of the 180-degree axis and focal plane.
   - **T (Tone / Rig)**: Concrete physical hardware feel (e.g., 50mm lens on stabilized dolly track).
5. **Serialized 3-Beat Action Lanes**: Maximum 3 cause-and-effect beats across the 8-10s window (Seconds 0-3, 3-6, 6-10).
6. **"One Job Per Reference" Contract**: Clear boundary statements for `<image_1>`, `<image_2>`, and `<image_3>`.
7. **Clean Natural Prose Formatting Rule**:
   - The final output must be a single cohesive paragraph of natural-language prose.
   - **NEVER include raw markdown headings (`### Camera:`, `### Lighting:`) inside the generation prompt.**

---

## 7. Stage 6: Cinema Darkroom HTML Treatment & Production Bundle

### 7.1 Dark-Room Cinema HTML Treatment (`storyboard_preview.html`)
The compiler generates a zero-dependency, self-contained HTML/CSS/JS file providing an A24/Frame.io style review interface:
- **Canvas / Styling**: Pitch Cinema Black (`#08090D`), surface cards (`#0F111A`), Director Cyan telemetry (`#00F0FF`), Cinema Amber lighting notes (`#FFB703`), and Speed Lock Emerald (`#10B981`).
- **Header HUD**: Project title, logline, total runtime, framerate (`24fps`), aspect ratio badge, and interactive color script swatches with click-to-copy hex values.
- **Reference Bible Cards**: Interactive visual cards for Character Turnarounds and Master Environment Plates with collapsible prompt drawers.
- **Sonic Blueprint Player**: Interactive BGM audio player with waveform visualization and scene transition cues.
- **Shot-by-Shot Timeline Cards**:
  * Dual-mode media viewport (Nano Banana pre-vis keyframe vs. live video player).
  * Monospace CRAFT camera telemetry HUD (Sensor, Rig, Lens, Angle, Track).
  * Serialized 3-beat action step badges.
  * Clickable reference binding tags (`<image_1>`, `<image_2>`, `<image_3>`).
  * Prose prompt code block with a glowing **"Copy Omni Prompt"** button providing toast feedback.
- **Cinema Theater Mode**: Hotkey-driven fullscreen presentation (`F` to toggle, `Left`/`Right` arrows to navigate shots, `Spacebar` to play, `C` to copy prompt).

### 7.2 Machine-Readable Bundle (`production_bundle.json`)
The system simultaneously serializes the entire project state into `production_bundle.json`, including the complete Pydantic Production Bible, scene prompt strings, asset file paths, and execution logs.

### 7.3 Optional Live Video Generation (`gemini-omni-1.1-flash-preview`)
When `--render-video` is enabled:
- **Mode A (Parallel Multi-Scene Cut)**: Dispatches `client.interactions.create` calls concurrently for all scenes using `reference_to_video` mode, attaching the generated PNG anchors as image parts.
- **Mode B (Continuous +10s Extension Chain)**: Dispatches Scene 1 as a base clip, captures `interaction.id`, and chains subsequent scenes sequentially via `previous_interaction_id`, producing a single seamless 40s oner.

---

## 8. Summary Checklist for Creative Director Agents

When deploying the `omni-movie-director` skill in production:
1. **Never skip Director's Intake**: Ask the 4-5 high-leverage questions or infer smart defaults.
2. **Lock the Master Production Bible**: Ensure the Character Bible mandates high-contrast wardrobe polarity, the Environment Bible specifies spatial dimensions and light angles, and the Camera Rig follows CRAFT.
3. **Enforce the Prescription Spectrum**: Apply Regime 1 flowing prose to atmospheric scenes; mandate the 5-part Kinetic Contact Chain and 1.0x real-time speed locks on Regime 2 kinetic/commercial scenes.
4. **Respect Multimodal Limits**: Never exceed 3 reference images (`<image_1>`, `<image_2>`, `<image_3>`), and always bind them with explicit single-duty contracts and exclusion clauses.
5. **Strip All Markdown Headers**: Deliver the final prompt to Gemini Omni as pure natural-language cinematic prose.
6. **Harmonize Sound**: Generate synchronized diegetic foley in the scene prompt while providing a standalone Lyria prompt for master musical score generation.
7. **Compile Darkroom HTML**: Guarantee that every production run emits both `storyboard_preview.html` and `production_bundle.json`.

---

## 9. Reference Documentation Index

For deep-dive technical implementations and golden reference assets, consult:

1. [references/director-intake-and-bible.md](references/director-intake-and-bible.md): Complete Pydantic v2 schemas, JSON contracts, and intake interview rubric.
2. [references/nano-banana-storyboard-system.md](references/nano-banana-storyboard-system.md): 3-Anchor Nano Banana prompt templates, optics matrices, and darkroom cinema HTML template code.
3. [references/adk-2-architecture.md](references/adk-2-architecture.md): Google ADK 2.0 multi-agent DAG implementation (`SequentialAgent`, `ParallelAgent`, `Workflow`).
4. [references/golden-demos.md](references/golden-demos.md): Full production bibles and prompt suites for **IKEA ASMR 2.0 ("The Living Room Unfolds")** and **SEPHORA London Pulse 2.0 ("Midnight Velvet" in both Mode A Parallel and Mode B 40s Continuous Extension)**.
