# Director's Intake Protocol & Master Production Bible Specification

This reference contains the complete Intake Rubric, conversational heuristics, Pydantic v2 schemas, and JSON serialization format for the **Master Production Bible 2.0 (Single Source of Truth)**.

---

## 1. Director's Intake Protocol & Interrogation Rubric

When initiating a project from a user prompt, script excerpt, brand PDF, or URL, the Lead Director executes a targeted 5-question interrogation. **Never ask more than 5 questions.** Every question must unlock foundational production parameters.

### 1.1 The 5 Essential Intake Questions

1. **Narrative Tone & Physical Regime**:
   - *Question*: "Is this film an **Atmospheric & World-Building** narrative (Regime 1: organic pacing, mood, landscapes, poetic lighting) or a **High-Kinetic / Commercial Precision** sequence (Regime 2: fast camera moves, tactile impacts, sports/combat, crisp product geometry)?"
   - *Purpose*: Determines whether prompts follow low-prescription atmospheric prose or high-prescription Seedance contact chains with 1.0x real-time speed locks.

2. **Delivery Canvas & Aspect Ratio**:
   - *Question*: "What is your primary exhibition canvas: **16:9 Cinema Widescreen** (theatrical/YouTube), **9:16 Vertical Reel** (TikTok/Instagram Reels/SEPHORA storefront), or **1:1 Square Showcase**?"
   - *Purpose*: Sets the optical frame geometry for Nano Banana concept art and Gemini Omni video synthesis.

3. **Storytelling Mode & Runtime**:
   - *Question*: "Do you want **Mode A: Parallel Multi-Scene Montage** (4 distinct 8-10s scenes edited together like a classic commercial trailer) or **Mode B: Continuous Scene Extension** (a seamless 10s base clip extended sequentially up to 40s in a single unbroken take)?"
   - *Purpose*: Dictates the multi-agent orchestration topology (ParallelAgent fan-out vs. sequential Interactions API chaining).

4. **Hero Anchors & Visual Polarity (Characters & Products)**:
   - *Question*: "Who or what are our hero anchors? If characters: what are their high-contrast wardrobe colors and physical silhouettes (to prevent limb/clothing blend)? If a product: what are its rigid materials, logos, and non-negotiable details?"
   - *Purpose*: Populates Character and Prop Bibles with positive invariants and enforces wardrobe polarity.

5. **Sonic Architecture & Musical Pulse**:
   - *Question*: "What is the auditory identity? Specify: (a) Master BGM style (e.g., Scandic Minimalist ASMR, 138 BPM UK Garage, Zimmer-esque Orchestral Crescendo), and (b) Key diegetic sounds (e.g., crisp cardboard snaps, neon hums, tactile clicks, dialogue lines)."
   - *Purpose*: Defines embedded diegetic foley and the standalone Master BGM score prompt.

### 1.2 Conversational Heuristics & Smart Defaults

When running in headless, batch, or dry-run modes (`--auto`), the agent applies these deterministic defaults:
- **Aspect Ratio Default**: `16:9` for narrative, sci-fi, and automotive; `9:16` for fashion, cosmetics, and mobile product sizzles.
- **Regime Default**: Products with moving parts, sports, martial arts, and rapid camera choreography $\to$ `Regime 2`; mood, landscapes, nature, sci-fi vistas $\to$ `Regime 1`.
- **Storytelling Mode Default**: `Mode A` (4-scene montage) for commercial ads; `Mode B` (oner extension) for character drama or continuous choreography.
- **Audio Default**: Synchronized foley + ambient score matching visual tone at 48kHz spatial fidelity.

---

## 2. Complete Pydantic v2 Production Bible Schema

```python
"""
Master Production Bible (SSOT 2.0) Data Contracts.
Built with Pydantic v2.10+.
"""

from enum import Enum
from typing import List, Optional, Dict
from pydantic import BaseModel, Field, HttpUrl

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
    character_id: str = Field(..., description="Unique ID, e.g. CHAR_MAYA")
    name: str = Field(..., description="Character name or subject identifier")
    silhouette: str = Field(..., description="Distinct physical build, height, hair, silhouette")
    wardrobe_polarity: str = Field(
        ..., 
        description="High-contrast clothing colors, textures, and accents designed to prevent multi-subject limb blend"
    )
    movement_signature: str = Field(..., description="Gait, velocity, posture, physical behavior")
    turnaround_prompt: Optional[str] = Field(None, description="Nano Banana prompt for 3-angle turnaround sheet")
    turnaround_artifact_uri: Optional[str] = Field(None, description="Path to generated PNG turnaround")

class EnvironmentSpec(BaseModel):
    environment_id: str = Field(..., description="Unique ID, e.g. ENV_STOCKHOLM_LOFT")
    location_name: str
    spatial_architecture: str = Field(..., description="Room dimensions, depth planes, floor materials")
    lighting_setup: str = Field(..., description="Key light source, rim light, Kelvin color temperature, bounce")
    atmospheric_particles: str = Field(..., description="Air quality, dust motes, rain, mist, smoke, reflections")
    positive_invariants: List[str] = Field(
        ..., 
        description="List of physical laws and immutable fixtures that must never morph or disappear"
    )
    plate_prompt: Optional[str] = Field(None, description="Nano Banana prompt for zero-character plate")
    plate_artifact_uri: Optional[str] = Field(None, description="Path to generated PNG environment plate")

class CameraRigSpec(BaseModel):
    rig_type: str = Field(..., description="Dolly track, Steadicam, Technocrane, Locked-off tripod, Handheld")
    focal_length_mm: int = Field(..., description="e.g. 24, 35, 50, 85, 100")
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
    dynamic_arc: str = Field(..., description="Progression across runtime (Intro, Build, Climax, Outro)")
    lyria_prompt: str = Field(..., description="Ready-to-use text prompt for Lyria / Google Audio generation")

class NanoBananaReference(BaseModel):
    asset_id: str = Field(..., description="e.g. <image_1>, <image_2>, <image_3>")
    job_description: str = Field(..., description="The EXACT single job this reference performs ('One Job Per Reference')")
    exclusion_clause: str = Field(..., description="Explicitly forbidden visual traits to ignore from this reference")
    generation_prompt: str = Field(..., description="Prompt used to generate this reference sheet with gemini-3-pro-image")
    artifact_uri: Optional[str] = Field(None, description="Local or cloud URI to the saved reference image")

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
    keyframe_concept_prompt: Optional[str] = Field(None, description="Nano Banana prompt for First Frame ($t=0.0s$)")
    keyframe_artifact_uri: Optional[str] = Field(None, description="Path to generated PNG keyframe")
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

---

## 3. Strict Rules of the Production Bible

1. **Character Polarity Invariant**: When two or more characters appear in the same scene, they must have contrasting wardrobe colors and silhouettes (e.g., vibrant scarlet patent leather vs. matte dark charcoal with white stripes). Characters must never share similar clothing colors or loose silhouettes, preventing visual blending in video latent space.
2. **Environment Zero-Character Plate Invariant**: The environment plate prompt must describe an empty architectural space with zero humans, animals, or moving vehicles. This guarantees clean background conditioning without ghost figures.
3. **CRAFT Camera Telemetry Invariant**: The camera rig must explicitly state:
   - *Composition*: Starting frame size and angle.
   - *Route*: A single motivated trajectory or sequence (`first push-in, then hold`).
   - *Action Anchor*: Physical trigger initiating the move (e.g., an eyelid closing or a dowel locking).
   - *Focus/Axis Invariant*: Preservation of the 180-degree axis.
   - *Tone/Rig*: Real physical camera hardware emulation.
4. **Clean Prose Invariant**: All scene prompts within the bible must be formatted as continuous natural-language prose with zero internal markdown headers.
