import json
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
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
    beat_index: int = Field(default=1, ge=1, le=3)
    timestamp: str = Field(default="00:00 - 00:03", description="Timing marker, e.g. '00:00 - 00:03'")
    description: str = Field(default="", description="Concrete physical event or action")
    beat_title: Optional[str] = None
    timecode: Optional[str] = None
    action_description: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_beat(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "timecode" in data and ("timestamp" not in data or not data["timestamp"]):
                data["timestamp"] = data["timecode"]
            if "action_description" in data and ("description" not in data or not data["description"]):
                data["description"] = data["action_description"]
            if "beat_title" in data and ("description" not in data or not data["description"]):
                data["description"] = data["beat_title"]
        return data

    def __str__(self) -> str:
        desc = self.description or self.action_description or self.beat_title or ""
        title = self.beat_title or f"Beat {self.beat_index}"
        return f"{title}: {desc}".strip()


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
    keyframe_spec: Optional[Any] = Field(
        default=None,
        description="Optional pre-rendered keyframe or SVG plate spec"
    )

    @model_validator(mode="before")
    @classmethod
    def normalize_scene_inputs(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "prompt_text" in data and "omni_prose_prompt" not in data:
                data["omni_prose_prompt"] = data["prompt_text"]
            if "camera_spec" in data and "craft_camera" not in data:
                data["craft_camera"] = data["camera_spec"]
            if "diegetic_sound" in data and "diegetic_sonic" not in data:
                data["diegetic_sonic"] = data["diegetic_sound"]
            if "action_beats" in data and isinstance(data["action_beats"], list):
                norm_beats = []
                for b in data["action_beats"]:
                    if isinstance(b, str):
                        norm_beats.append(b)
                    elif isinstance(b, ActionBeatSpec):
                        norm_beats.append(str(b))
                    elif isinstance(b, dict):
                        desc = b.get("description") or b.get("action_description") or b.get("beat_title") or ""
                        title = b.get("beat_title") or f"Beat {b.get('beat_index', 1)}"
                        norm_beats.append(f"{title}: {desc}".strip())
                    else:
                        norm_beats.append(str(b))
                data["action_beats"] = norm_beats
        return data

    @property
    def scene_prompt(self) -> str:
        return self.omni_prose_prompt

    @scene_prompt.setter
    def scene_prompt(self, value: str) -> None:
        self.omni_prose_prompt = value

    @property
    def prompt_text(self) -> str:
        return self.omni_prose_prompt

    @prompt_text.setter
    def prompt_text(self, value: str) -> None:
        self.omni_prose_prompt = value

    @property
    def camera_spec(self) -> Optional[CraftCameraSpec]:
        return self.craft_camera

    @camera_spec.setter
    def camera_spec(self, value: Optional[CraftCameraSpec]) -> None:
        self.craft_camera = value

    @property
    def diegetic_sound(self) -> Optional[DiegeticSonicSpec]:
        return self.diegetic_sonic

    @diegetic_sound.setter
    def diegetic_sound(self, value: Optional[DiegeticSonicSpec]) -> None:
        self.diegetic_sonic = value

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
    domain_archetype: Optional[str] = None

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
    score: float = Field(default=100.0, ge=0.0, le=100.0)
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)

    @property
    def rule_details(self) -> Dict[str, Any]:
        return {
            "rule_1_no_markdown_headers": {
                "passed": not any("Rule 1" in e for e in self.errors),
            },
            "rule_2_action_beats_cap": {
                "passed": not any("Rule 2" in e for e in self.errors),
            },
            "rule_3_speed_lock_regime_2": {
                "passed": not any("Rule 3" in e for e in self.errors),
            },
            "rule_4_craft_camera": {
                "passed": not any("Rule 4" in e for e in self.errors),
            },
            "rule_5_nano_banana_references": {
                "passed": not any("Rule 5" in e for e in self.errors),
            },
            "rule_6_diegetic_audio_cues": {
                "passed": not any("Rule 6" in e for e in self.errors),
            },
            "rule_7_continuous_continuity": {
                "passed": not any("Rule 7" in e for e in self.errors),
            },
        }


PromptAuditResult = AuditResult


class CouncilPersona(str, Enum):
    """The four disciplines of the Autonomous Product Council."""
    FORWARD_DEPLOYED_ENGINEER = "council-fde"
    AGENT_SYSTEMS_ENGINEER = "council-agent-engineer"
    AGENT_STRATEGIST = "council-strategist"
    UX_UI_DESIGNER = "council-ux-designer"

    # Aliases
    COUNCIL_FDE = "council-fde"
    COUNCIL_AGENT_ENGINEER = "council-agent-engineer"
    COUNCIL_STRATEGIST = "council-strategist"
    COUNCIL_UX_DESIGNER = "council-ux-designer"


class CouncilFindingSeverity(str, Enum):
    """Severity classification for Product Council audit findings."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    # Aliases
    HIGH = "warning"
    MEDIUM = "warning"
    LOW = "info"


class CouncilFinding(BaseModel):
    """A specific evaluation finding produced by a Council persona."""
    severity: CouncilFindingSeverity = CouncilFindingSeverity.INFO
    category: str
    message: str
    remediation: Optional[str] = None
    suggested_fix: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

    @model_validator(mode="after")
    def sync_remediation(self) -> "CouncilFinding":
        if self.suggested_fix and not self.remediation:
            self.remediation = self.suggested_fix
        elif self.remediation and not self.suggested_fix:
            self.suggested_fix = self.remediation
        return self


class PersonaReviewResult(BaseModel):
    """Evaluation score and findings from a single council persona (max 25.0 pts)."""
    persona: CouncilPersona
    score: float = Field(default=25.0, ge=0.0, le=25.0)
    max_score: float = 25.0
    passed: bool = True
    persona_title: str = ""
    findings: List[CouncilFinding] = Field(default_factory=list)
    summary: str = ""

    @property
    def critical_count(self) -> int:
        return sum(
            1 for f in self.findings
            if str(f.severity).lower() in ("critical", "councilfindingseverity.critical")
        )


class ProductCouncilReport(BaseModel):
    """Unified 100-point 4-persona Product Council evaluation report."""
    version: str = "2.1.0"
    project_title: str = ""
    timestamp: str = ""
    overall_score: float = Field(default=100.0, ge=0.0, le=100.0)
    passed: bool = True
    critical_findings_count: int = 0
    reviews: List[PersonaReviewResult] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)

    @property
    def persona_reviews(self) -> Dict[str, PersonaReviewResult]:
        res: Dict[str, PersonaReviewResult] = {}
        for r in self.reviews:
            key = r.persona.value if hasattr(r.persona, "value") else str(r.persona)
            res[key] = r
        return res

    @property
    def persona_results(self) -> Dict[str, PersonaReviewResult]:
        return self.persona_reviews


class ProductionBundle(BaseModel):
    """Complete compiled production output bundle."""
    bible: MasterProductionBible
    storyboard_html_path: str
    bundle_json_path: str
    visual_plates: Dict[str, str] = Field(default_factory=dict, description="Asset ID -> file path or SVG")
    rendered_videos: Optional[List[Dict[str, Any]]] = Field(default=None)
    audit_reports: List[AuditResult] = Field(default_factory=list)
    mode: str = Field(default="dry-run", description="dry-run, hybrid, or full-render")
    telemetry: Optional[Dict[str, Any]] = Field(default=None)
    council_report: Optional[ProductCouncilReport] = Field(default=None)

    def __getitem__(self, key: str) -> Any:
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(key)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def __contains__(self, key: str) -> bool:
        return hasattr(self, key)


def load_bible_from_json(path_or_payload: Union[MasterProductionBible, ProductionBundle, str, Path, Dict[str, Any]]) -> MasterProductionBible:
    """Loads and validates a MasterProductionBible from a file path, JSON string, dict, or object.

    Accepts either a raw MasterProductionBible dictionary or a ProductionBundle dictionary
    containing a "bible" key. Raises ValueError on invalid inputs or missing files.
    """
    if isinstance(path_or_payload, MasterProductionBible):
        return path_or_payload
    if isinstance(path_or_payload, ProductionBundle):
        return path_or_payload.bible

    if isinstance(path_or_payload, (str, Path)):
        path = Path(path_or_payload)
        if path.is_file():
            try:
                content = path.read_text(encoding="utf-8")
                data = json.loads(content)
            except Exception as e:
                raise ValueError(f"Failed to read or parse JSON file '{path}': {e}") from e
        else:
            raw_str = str(path_or_payload).strip()
            if raw_str.startswith("{"):
                try:
                    data = json.loads(raw_str)
                except Exception as e:
                    raise ValueError(f"Failed to parse JSON string: {e}") from e
            else:
                raise ValueError(f"Bible file not found: {path_or_payload}")
    elif isinstance(path_or_payload, dict):
        data = path_or_payload
    else:
        raise ValueError(f"Unsupported payload type for load_bible_from_json: {type(path_or_payload)}")

    if not isinstance(data, dict):
        raise ValueError("Decoded JSON payload must be an object/dict")

    try:
        if "bible" in data and isinstance(data["bible"], dict):
            return MasterProductionBible.model_validate(data["bible"])
        return MasterProductionBible.model_validate(data)
    except Exception as e:
        raise ValueError(f"Invalid MasterProductionBible schema: {e}") from e

