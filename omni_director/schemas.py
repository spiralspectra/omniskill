"""Pydantic V2 state contracts and schema models for omni-movie-director."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class RegimeType(str, Enum):
    """The Prescription Spectrum: Low Prescription (Regime 1) vs High Prescription (Regime 2)."""
    REGIME_1_ATMOSPHERIC = "Regime 1: World-Knowledge & Atmospheric Flow"
    REGIME_2_KINETIC = "Regime 2: High-Kinetic & Precision Commercial"


class StorytellingMode(str, Enum):
    """Dual-Mode Storytelling: Parallel montage cuts vs continuous extension chains."""
    MODE_A_PARALLEL_CUT = "Mode A: Parallel Multi-Scene Cut (Montage)"
    MODE_B_CONTINUOUS_CHAIN = "Mode B: Continuous Scene Extension Chain (Oner)"


class AspectRatio(str, Enum):
    """Supported cinematic aspect ratios."""
    RATIO_16_9 = "16:9"
    RATIO_9_16 = "9:16"
    RATIO_1_1 = "1:1"
    RATIO_2_39_1 = "2.39:1"


class DirectorIntakeQuestion(BaseModel):
    """High-leverage intake interrogation question."""
    question_id: int
    dimension: str
    question_text: str
    smart_default: str


class DirectorIntakeAnswers(BaseModel):
    """Synthesized answers from the 5-Question Intake Protocol."""
    raw_prompt: str = Field(..., description="Original user prompt or logline")
    regime: RegimeType = Field(default=RegimeType.REGIME_2_KINETIC)
    aspect_ratio: AspectRatio = Field(default=AspectRatio.RATIO_16_9)
    storytelling_mode: StorytellingMode = Field(default=StorytellingMode.MODE_A_PARALLEL_CUT)
    hero_anchors: str = Field(default="", description="Character wardrobe or product details")
    sonic_identity: str = Field(default="", description="Auditory style, tempo, and key foley")
    brand_guidelines: Optional[Dict[str, Any]] = Field(default_factory=dict)
    reference_urls: List[str] = Field(default_factory=list)


class CharacterTurnaroundSpec(BaseModel):
    """Anchor 1: Character & Wardrobe Turnaround Sheet (CHAR_TURNAROUND)."""
    name: str = Field(..., description="Character name or hero subject identifier")
    silhouette: str = Field(..., description="Physical build, height, hair, silhouette")
    wardrobe_polarity: str = Field(
        ...,
        description="High-contrast clothing colors and textures to prevent multi-character visual bleed"
    )
    movement_signature: str = Field(..., description="Gait, velocity, posture, physical behavior")
    generation_prompt: Optional[str] = Field(default=None, description="Nano Banana prompt")
    image_path: Optional[str] = Field(default=None, description="Local path or URI to rendered turnaround plate")
    svg_markup: Optional[str] = Field(default=None, description="Crisp SVG storyboard plate for dry-run/preview")


class MasterEnvironmentSpec(BaseModel):
    """Anchor 2: Master Architectural Environment Plate (ENV_MASTER_PLATE)."""
    location_name: str
    spatial_architecture: str = Field(..., description="Room dimensions, depth planes, floor materials")
    lighting_setup: str = Field(..., description="Key light angle, Kelvin temperature, bounce, fill")
    atmospheric_particles: str = Field(..., description="Air quality, dust motes, rain, mist, smoke")
    positive_invariants: List[str] = Field(
        default_factory=list,
        description="Physical fixtures that must remain geometrically rigid"
    )
    generation_prompt: Optional[str] = Field(default=None, description="Nano Banana prompt")
    image_path: Optional[str] = Field(default=None, description="Local path or URI to master environment plate")
    svg_markup: Optional[str] = Field(default=None, description="Crisp SVG storyboard plate for dry-run/preview")


class CraftCameraSpec(BaseModel):
    """Kinetic Camera Grammar (CRAFT Framework)."""
    rig_type: str = Field(..., description="Locked-off tripod, Dolly track, Steadicam, Technocrane, etc.")
    focal_length_mm: int = Field(default=35, description="Focal length in millimeters")
    composition: str = Field(..., description="Framing geometry, horizon line, rule of thirds, subject placement")
    route: str = Field(..., description="Trajectory vector, pan/tilt/roll axis, dolly speed")
    action_anchor: str = Field(..., description="Physical subject or contact point that guides tracking")
    focus_axis: str = Field(..., description="Depth of field, rack focus timing, 180-degree axis lock")
    tone_rig: str = Field(..., description="Lens characteristics, anamorphic bokeh, optical texture")

    def to_summary(self) -> str:
        return f"{self.rig_type} ({self.focal_length_mm}mm) | {self.composition} | Route: {self.route}"


class KineticContactChain(BaseModel):
    """Seedance 2.5 5-Stage Physical Kinetic Contact Chain."""
    initiation: str = Field(..., description="Starting posture, pre-motion anticipation, velocity vector")
    contact_point: str = Field(..., description="Exact microscopic physical interface where force applies")
    force_transfer: str = Field(..., description="Newtonian energy transfer: deformation, acceleration, impulse")
    environmental_evidence: str = Field(..., description="Physical marks, sound wave, dust puffs, skid marks")
    recovery_stance: str = Field(..., description="Momentum dissipation, settling oscillation, static equilibrium")

    def to_chain_str(self) -> str:
        return (
            f"1. Initiation: {self.initiation} -> "
            f"2. Contact: {self.contact_point} -> "
            f"3. Transfer: {self.force_transfer} -> "
            f"4. Evidence: {self.environmental_evidence} -> "
            f"5. Recovery: {self.recovery_stance}"
        )


class ActionBeatSpec(BaseModel):
    """A single serialized cause-and-effect action beat within a 10s window."""
    beat_index: int = Field(..., ge=1, le=3)
    timestamp: str = Field(..., description="Timing marker, e.g. '00:00 - 00:03'")
    description: str = Field(..., description="Concrete physical event or action")


class DiegeticSonicSpec(BaseModel):
    """Synchronized diegetic audio and foley generated natively inside Gemini Omni."""
    foley_cues: List[str] = Field(default_factory=list, description="Tactile material sounds (snaps, friction, thuds)")
    dialogue_lines: List[str] = Field(default_factory=list, description="Exact spoken dialogue with speaker attribution")
    room_acoustics: str = Field(..., description="Reverb decay, space dampening, environmental rumble")


class MasterBgmSpec(BaseModel):
    """Master musical score blueprint for Lyria / Google Audio / <audio> reference."""
    track_title: str
    genre_style: str = Field(..., description="Musical genre and aesthetic")
    tempo_bpm: int = Field(..., ge=40, le=220)
    key_signature: str = Field(..., description="e.g. D Major, F Minor")
    instrumentation: List[str] = Field(default_factory=list)
    dynamic_arc: str = Field(..., description="Progression across runtime (Intro, Build, Climax, Outro)")
    lyria_prompt: str = Field(..., description="Ready-to-use text prompt for Lyria / audio model")


class NanoBananaReference(BaseModel):
    """Single reference image specification honoring the 3-image ceiling and 'One Job' contract."""
    asset_id: str = Field(..., description="e.g. <image_1>, <image_2>, <image_3>")
    job_description: str = Field(..., description="The EXACT single duty this reference performs")
    exclusion_clause: str = Field(..., description="Explicitly forbidden visual traits to ignore from this reference")
    generation_prompt: str = Field(..., description="Prompt used to generate this reference with gemini-3-pro-image")
    local_path: Optional[str] = Field(default=None, description="Local file path or URL to generated image")
    svg_markup: Optional[str] = Field(default=None, description="SVG visual representation")


class SceneKeyframeSpec(BaseModel):
    """Anchor 3: Scene Keyframe / Boundary Plate (SCENE_KEYFRAME)."""
    scene_index: int
    scene_title: str
    timestamp_range: str
    craft_camera: Optional[CraftCameraSpec] = None
    initial_blocking: str = Field(..., description="Camera framing, actor posture, depth at second 0.0")
    generation_prompt: Optional[str] = None
    image_path: Optional[str] = None
    svg_markup: Optional[str] = None


class ScenePromptSpec(BaseModel):
    """Complete specification for a single 8-10 second video scene."""
    scene_index: int = Field(..., description="1-indexed scene number")
    timestamp_range: str = Field(..., description="e.g. '00:00 - 00:08' or '+10s extension'")
    scene_title: str
    regime: RegimeType
    action_beats: List[str] = Field(
        ...,
        max_length=3,
        description="Maximum 3 serialized cause-and-effect action beats for this 8-10s window"
    )
    kinetic_contact_chain: Optional[str] = Field(
        default=None,
        description="Initiation -> Contact Point -> Force Transfer -> Environmental Evidence -> Recovery Stance"
    )
    craft_camera: Optional[CraftCameraSpec] = Field(
        default=None,
        description="CRAFT camera specification for this shot"
    )
    diegetic_sonic: Optional[DiegeticSonicSpec] = Field(
        default=None,
        description="Scene-specific synchronized audio details"
    )
    omni_prose_prompt: str = Field(
        ...,
        description="The clean natural-language prose prompt ready to feed into Gemini Omni (NO markdown headers inside!)"
    )
    conversational_edit_deltas: List[str] = Field(
        default_factory=list,
        description="Curated single-turn edit variations (e.g. Turn 2 lighting adjustment)"
    )

    @field_validator("action_beats")
    @classmethod
    def validate_action_beats_cap(cls, beats: List[str]) -> List[str]:
        if len(beats) > 3:
            raise ValueError(
                f"Action beats cap exceeded: found {len(beats)} beats. "
                f"Gemini Omni enforces a strict maximum of 3 serialized beats per 10-second window."
            )
        return beats


class MasterProductionBible(BaseModel):
    """Master Production Bible (Single Source of Truth 2.0)."""
    project_title: str
    logline: str
    creative_regime: RegimeType
    storytelling_mode: StorytellingMode
    aspect_ratio: AspectRatio
    total_runtime_seconds: int = Field(default=32, ge=8, le=60)
    color_palette: List[str] = Field(
        default_factory=lambda: ["#2C3E50", "#E74C3C", "#ECF0F1", "#F39C12"],
        description="Hex color script codes"
    )
    characters: List[CharacterTurnaroundSpec] = Field(default_factory=list)
    environment: MasterEnvironmentSpec
    camera_rig: Optional[CraftCameraSpec] = None
    sonic_blueprint: DiegeticSonicSpec
    master_bgm: MasterBgmSpec
    nano_banana_assets: List[NanoBananaReference] = Field(
        ...,
        max_length=3,
        description="Gemini Omni accepts a maximum ceiling of 3 image references"
    )
    scenes: List[ScenePromptSpec]

    @field_validator("nano_banana_assets")
    @classmethod
    def validate_reference_ceiling(cls, assets: List[NanoBananaReference]) -> List[NanoBananaReference]:
        if len(assets) > 3:
            raise ValueError(
                f"Reference ceiling exceeded: {len(assets)} image references provided. "
                f"Gemini Omni enforces an architectural ceiling of at most 3 image references (<image_1>, <image_2>, <image_3>)."
            )
        return assets

    @model_validator(mode="after")
    def validate_character_wardrobe_polarity(self) -> "MasterProductionBible":
        """Enforces high-contrast wardrobe polarity when 2 or more characters are present."""
        if len(self.characters) >= 2:
            polarities = [c.wardrobe_polarity.strip().lower() for c in self.characters if c.wardrobe_polarity]
            if len(polarities) < len(self.characters):
                raise ValueError(
                    "High-contrast wardrobe polarity violation: When 2+ characters are present, "
                    "every character MUST define an explicit wardrobe_polarity to prevent visual entanglement in Gemini Omni."
                )
            if len(set(polarities)) < len(polarities):
                raise ValueError(
                    "High-contrast wardrobe polarity collision: Multiple characters have identical wardrobe descriptions. "
                    "Distinct colors/fabrics are required to prevent limb/identity blend in video generation."
                )
        return self


class AuditResult(BaseModel):
    """Results from auditing a scene prompt against the 7-Point Gemini Omni prompt standards."""
    scene_index: int
    passed: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)


class ProductionBundle(BaseModel):
    """Complete compiled production output bundle."""
    bible: MasterProductionBible
    storyboard_html_path: str
    bundle_json_path: str
    visual_plates: Dict[str, str] = Field(default_factory=dict, description="Asset ID -> file path or SVG")
    rendered_videos: Optional[List[Dict[str, Any]]] = Field(default=None)
    audit_reports: List[AuditResult] = Field(default_factory=list)
    mode: str = Field(default="dry-run", description="dry-run, hybrid, or full-render")
