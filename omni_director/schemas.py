import json
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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


class AscCdlSpec(BaseModel):
    """ASC CDL (American Society of Cinematographers Color Decision List) grading parameters."""
    slope: Tuple[float, float, float] = Field(default=(1.0, 1.0, 1.0), description="RGB Slope multiplier (gain)")
    offset: Tuple[float, float, float] = Field(default=(0.0, 0.0, 0.0), description="RGB Offset offset (lift)")
    power: Tuple[float, float, float] = Field(default=(1.0, 1.0, 1.0), description="RGB Power exponent (gamma)")
    saturation: float = Field(default=1.0, ge=0.0, le=4.0, description="Color saturation multiplier")


class ColorLookPreset(str, Enum):
    """Cinematic Look & Film Stock Presets."""
    REC709_NEUTRAL = "rec709_neutral"
    KODAK_5219_VISION3 = "kodak_5219_vision3"
    FUJI_ETERNA_500T = "fuji_eterna_500t"
    BLEACH_BYPASS_SILVER = "bleach_bypass_silver"
    TEAL_AND_ORANGE_BLOCKBUSTER = "teal_and_orange_blockbuster"
    MONOCHROME_PANATOMIC_X = "monochrome_panatomic_x"

    # Lowercase aliases
    rec709_neutral = "rec709_neutral"
    kodak_5219_vision3 = "kodak_5219_vision3"
    fuji_eterna_500t = "fuji_eterna_500t"
    bleach_bypass_silver = "bleach_bypass_silver"
    teal_and_orange_blockbuster = "teal_and_orange_blockbuster"
    monochrome_panatomic_x = "monochrome_panatomic_x"


class LutGridDimension(str, Enum):
    """3D LUT cube grid mesh resolution (PM-FEAT-012)."""
    GRID_17 = "17x17x17"
    GRID_33 = "33x33x33"
    GRID_65 = "65x65x65"

    # Shorthand aliases
    grid_17 = "17x17x17"
    grid_33 = "33x33x33"
    grid_65 = "65x65x65"
    dim_17 = "17x17x17"
    dim_33 = "33x33x33"
    dim_65 = "65x65x65"

    @property
    def cube_size(self) -> int:
        if "17" in self.value:
            return 17
        if "65" in self.value:
            return 65
        return 33


class ColorGamutTransform(str, Enum):
    """Camera sensor color space to display transform (PM-FEAT-012)."""
    ACESCG_TO_REC709 = "ACEScg to Rec.709 Gamma 2.4"
    ARRI_LOGC4_TO_REC709 = "ARRI LogC4 to Rec.709"
    RED_LOG3G10_TO_REC709 = "RED Log3G10 to Rec.709"
    SONY_SLOG3_TO_REC709 = "Sony S-Log3 to Rec.709"
    CANON_CLOG2_TO_REC709 = "Canon C-Log2 to Rec.709"
    BMD_FILM_GEN5_TO_REC709 = "Blackmagic Film Gen5 to Rec.709"
    REC709_NEUTRAL = "Rec.709 Neutral Passthrough"

    # Lowercase aliases
    acescg_to_rec709 = "ACEScg to Rec.709 Gamma 2.4"
    arri_logc4_to_rec709 = "ARRI LogC4 to Rec.709"
    red_log3g10_to_rec709 = "RED Log3G10 to Rec.709"
    sony_slog3_to_rec709 = "Sony S-Log3 to Rec.709"
    canon_clog2_to_rec709 = "Canon C-Log2 to Rec.709"
    bmd_film_gen5_to_rec709 = "Blackmagic Film Gen5 to Rec.709"
    rec709_neutral = "Rec.709 Neutral Passthrough"


class ThreeDimensionalLutSpec(BaseModel):
    """Professional 3D Cube Color Grading LUT Specification (PM-FEAT-012)."""
    model_config = ConfigDict(extra="allow")

    lut_title: str = Field(default="OMNI_DIRECTOR_MASTER_3DLUT", description="LUT title identifier in .cube file header")
    grid_dimension: LutGridDimension = Field(default=LutGridDimension.GRID_33, description="3D LUT cube resolution")
    gamut_transform: ColorGamutTransform = Field(default=ColorGamutTransform.ACESCG_TO_REC709, description="Input log color space to target display transform")
    domain_min: Tuple[float, float, float] = Field(default=(0.0, 0.0, 0.0), description="Input domain minimum limits (R, G, B)")
    domain_max: Tuple[float, float, float] = Field(default=(1.0, 1.0, 1.0), description="Input domain maximum limits (R, G, B)")
    cube_file_path: Optional[str] = Field(default=None, description="Relative or absolute path to generated .cube file")
    cdl_applied: Optional[AscCdlSpec] = Field(default=None, description="Baked ASC CDL grading transfer function")
    tetrahedral_interpolation: bool = Field(default=True, description="Enable tetrahedral hardware interpolation flag")
    shaper_lut_enabled: bool = Field(default=False, description="Enable 1D log shaper curve pre-allocation")
    colorist_notes: str = Field(default="", description="DIT / Supervising Colorist technical notes")

    @field_validator("grid_dimension", mode="before")
    @classmethod
    def normalize_grid_dimension(cls, v: Any) -> Any:
        if isinstance(v, int):
            if v <= 17:
                return LutGridDimension.GRID_17
            elif v >= 65:
                return LutGridDimension.GRID_65
            else:
                return LutGridDimension.GRID_33
        if isinstance(v, str):
            v_clean = v.strip().lower()
            if "17" in v_clean:
                return LutGridDimension.GRID_17
            if "65" in v_clean:
                return LutGridDimension.GRID_65
            if "33" in v_clean:
                return LutGridDimension.GRID_33
        return v

    @field_validator("gamut_transform", mode="before")
    @classmethod
    def normalize_gamut_transform(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_clean = v.strip().lower()
            for member in ColorGamutTransform:
                if v_clean == member.value.lower() or v_clean == member.name.lower():
                    return member
            if "arri" in v_clean:
                return ColorGamutTransform.ARRI_LOGC4_TO_REC709
            if "red" in v_clean:
                return ColorGamutTransform.RED_LOG3G10_TO_REC709
            if "sony" in v_clean:
                return ColorGamutTransform.SONY_SLOG3_TO_REC709
            if "canon" in v_clean:
                return ColorGamutTransform.CANON_CLOG2_TO_REC709
            if "blackmagic" in v_clean or "bmd" in v_clean:
                return ColorGamutTransform.BMD_FILM_GEN5_TO_REC709
            if "aces" in v_clean:
                return ColorGamutTransform.ACESCG_TO_REC709
            if "rec709" in v_clean or "rec.709" in v_clean:
                return ColorGamutTransform.REC709_NEUTRAL
        return v


class SceneColorContinuityReport(BaseModel):
    """Scene-to-scene color grade continuity and perceptual delta audit report (PM-FEAT-012)."""
    model_config = ConfigDict(extra="allow")

    is_continuous: bool = Field(default=True, description="Flag indicating whether color variance is within commercial broadcast tolerances")
    max_slope_delta: float = Field(default=0.0, description="Maximum RGB slope variance across consecutive scene cuts")
    max_offset_delta: float = Field(default=0.0, description="Maximum RGB offset variance")
    max_power_delta: float = Field(default=0.0, description="Maximum RGB power variance")
    saturation_delta: float = Field(default=0.0, description="Maximum color saturation variance")
    perceptual_delta_e_estimate: float = Field(default=0.0, description="Estimated CIEDE2000 color delta across consecutive scenes")
    warning_messages: List[str] = Field(default_factory=list, description="List of color continuity warnings or recommendations")
    scenes_evaluated: int = Field(default=0, description="Number of scenes analyzed in continuity audit")


# Alias for backward compatibility and tool integration
ColorContinuityAudit = SceneColorContinuityReport


class ColorLookSpec(BaseModel):
    """Scene or Master Color Grading specification."""
    look_preset: ColorLookPreset = Field(default=ColorLookPreset.REC709_NEUTRAL)
    working_color_space: str = Field(default="ACEScg", description="ACEScg, Rec.709, ARRI Wide Gamut 4")
    target_display: str = Field(default="Rec.709 Gamma 2.4", description="Target viewing transform")
    cdl: AscCdlSpec = Field(default_factory=AscCdlSpec)
    contrast_pivot: float = Field(default=0.435, ge=0.0, le=1.0)
    halation_bloom: float = Field(default=0.0, ge=0.0, le=1.0, description="Analog film halation level")
    lut_spec: Optional[ThreeDimensionalLutSpec] = Field(default=None, description="3D LUT .cube specification (PM-FEAT-012)")


class SpeedRampMode(str, Enum):
    """Dynamic speed ramping and time-warp modes."""
    CONSTANT_REALTIME = "constant_realtime"
    DECELERATION_IMPACT = "deceleration_impact"
    ACCELERATION_BURST = "acceleration_burst"
    SNAP_FREEZE_RESUME = "snap_freeze_resume"
    PULSE_TIME_DILATION = "pulse_time_dilation"

    # Lowercase aliases
    constant_realtime = "constant_realtime"
    deceleration_impact = "deceleration_impact"
    acceleration_burst = "acceleration_burst"
    snap_freeze_resume = "snap_freeze_resume"
    pulse_time_dilation = "pulse_time_dilation"


class SpeedRampCurveSpec(BaseModel):
    """Dynamic speed ramp and motion timing specification."""
    mode: SpeedRampMode = Field(default=SpeedRampMode.CONSTANT_REALTIME)
    base_fps: int = Field(default=24, ge=12, le=120)
    peak_capture_fps: int = Field(default=120, ge=24, le=1000)
    shutter_angle_deg: float = Field(default=180.0, ge=11.25, le=360.0)
    curve_keyframe_points: List[Tuple[float, float]] = Field(
        default_factory=lambda: [(0.0, 1.0), (1.0, 1.0)],
        description="List of (normalized_time_0_to_1, speed_multiplier)"
    )
    motion_blur_character: str = Field(
        default="natural 180-degree cinematic blur",
        description="Deterministic kinetic motion blur descriptor"
    )


class SensorFormat(str, Enum):
    """Cinematic camera sensor formats and physical active sensor gate dimensions."""
    SUPER_35 = "Super35 (24.89 x 18.66mm)"
    FULL_FRAME = "Full Frame (36.00 x 24.00mm)"
    ARRI_LF = "Large Format / ARRI LF (36.70 x 25.54mm)"
    IMAX_70MM = "IMAX 15/70mm (70.41 x 52.63mm)"
    VISTAVISION = "VistaVision (40.96 x 21.60mm)"

    # Lowercase / canonical aliases for resilient deserialization
    super_35 = "Super35 (24.89 x 18.66mm)"
    full_frame = "Full Frame (36.00 x 24.00mm)"
    arri_lf = "Large Format / ARRI LF (36.70 x 25.54mm)"
    imax_70mm = "IMAX 15/70mm (70.41 x 52.63mm)"
    vistavision = "VistaVision (40.96 x 21.60mm)"


class AnamorphicSqueeze(float, Enum):
    """Anamorphic optical squeeze ratio factors."""
    SPHERICAL_1_0X = 1.0
    ANAMORPHIC_1_33X = 1.33
    ANAMORPHIC_1_5X = 1.5
    ANAMORPHIC_1_8X = 1.8
    ANAMORPHIC_2_0X = 2.0


class OpticalLensSpec(BaseModel):
    """Cinematic optical lens and sensor framing specification (PM-FEAT-007)."""
    sensor_format: SensorFormat = Field(default=SensorFormat.FULL_FRAME)
    anamorphic_squeeze: float = Field(default=1.0, ge=1.0, le=2.0)
    focal_length_mm: int = Field(default=35, ge=10, le=500)
    aperture_t_stop: float = Field(default=2.8, ge=1.3, le=22.0)
    lens_series: str = Field(default="Cooke S4/i Prime")
    bokeh_characteristic: str = Field(default="circular 9-blade buttery falloff")
    chromatic_aberration: str = Field(default="zero-dispersion apochromatic")
    distortion_profile: str = Field(default="barrel 0.2% edge compression")
    horizontal_fov_deg: Optional[float] = None
    vertical_fov_deg: Optional[float] = None
    hyperfocal_distance_m: Optional[float] = None

    @field_validator("sensor_format", mode="before")
    @classmethod
    def normalize_sensor_format(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_clean = v.strip().lower()
            if "super35" in v_clean or "super_35" in v_clean or "super 35" in v_clean:
                return SensorFormat.SUPER_35
            if "arri" in v_clean or "large format" in v_clean:
                return SensorFormat.ARRI_LF
            if "imax" in v_clean:
                return SensorFormat.IMAX_70MM
            if "vistavision" in v_clean or "vista" in v_clean:
                return SensorFormat.VISTAVISION
            if "full" in v_clean or "frame" in v_clean:
                return SensorFormat.FULL_FRAME
        return v


class ApertureIrisGeometry(str, Enum):
    """Aperture iris blade count and optical bokeh geometry (PM-FEAT-011)."""
    CIRCULAR = "circular_9_blade"
    CIRCULAR_9_BLADE = "circular_9_blade"
    CIRCULAR_11_BLADE = "circular_11_blade"
    POLYGONAL_7_BLADE = "polygonal_7_blade"
    ANAMORPHIC_OVAL_2X = "anamorphic_oval_2x"
    CAT_EYE_PERIPHERAL = "cat_eye_peripheral"
    STAR_6_POINT = "star_6_point"

    # Lowercase aliases
    circular = "circular_9_blade"
    circular_9_blade = "circular_9_blade"
    circular_11_blade = "circular_11_blade"
    polygonal_7_blade = "polygonal_7_blade"
    anamorphic_oval_2x = "anamorphic_oval_2x"
    cat_eye_peripheral = "cat_eye_peripheral"
    star_6_point = "star_6_point"


class OpticalAberrationProfile(BaseModel):
    """Optical lens aberration and imperfection profile (PM-FEAT-011)."""
    model_config = ConfigDict(extra="allow")

    chromatic_aberration: float = Field(default=0.15, ge=0.0, le=1.0, description="Lateral and axial chromatic dispersion fringing")
    spherical_aberration: float = Field(default=0.10, ge=0.0, le=1.0, description="Spherical aberration softness at wide aperture")
    coma: float = Field(default=0.05, ge=0.0, le=1.0, description="Comatic flare on peripheral point highlights")
    astigmatism: float = Field(default=0.05, ge=0.0, le=1.0, description="Sagittal vs tangential optical defocus variance")
    optical_vignetting: float = Field(default=0.20, ge=0.0, le=1.0, description="Mechanical cat-eye optical vignetting at frame edges")
    field_curvature: float = Field(default=0.08, ge=0.0, le=1.0, description="Petzval field curvature of focal plane")


class RackFocusTransitionCurve(str, Enum):
    """Rack focus timing and focus puller interpolation curves (PM-FEAT-011)."""
    CUBIC_EASE_IN_OUT = "cubic_ease_in_out"
    SMOOTHSTEP = "smoothstep"
    LINEAR = "linear"
    EXPONENTIAL_DECEL = "exponential_decel"
    S_CURVE = "s_curve"

    # Lowercase aliases
    cubic_ease_in_out = "cubic_ease_in_out"
    smoothstep = "smoothstep"
    linear = "linear"
    exponential_decel = "exponential_decel"
    s_curve = "s_curve"


class DepthOfFieldSpec(BaseModel):
    """Cinematic Depth of Field, Optical Physics & Focus Pulling specification (PM-FEAT-011)."""
    model_config = ConfigDict(extra="allow")

    focus_distance_m: float = Field(default=2.5, ge=0.1, le=1000.0, description="Critical subject plane focus distance in meters")
    aperture_f_stop: float = Field(default=2.0, ge=0.5, le=32.0, description="Working optical aperture (F-stop / T-stop)")
    focal_length_mm: int = Field(default=50, ge=10, le=500, description="Lens focal length in millimeters")
    sensor_format: SensorFormat = Field(default=SensorFormat.FULL_FRAME, description="Active camera sensor gate format")
    circle_of_confusion_mm: float = Field(default=0.030, ge=0.001, le=0.1, description="Circle of Confusion limit in millimeters")
    near_limit_m: Optional[float] = Field(default=None, description="Near depth of field limit in meters")
    far_limit_m: Optional[float] = Field(default=None, description="Far depth of field limit in meters (float or inf)")
    total_dof_m: Optional[float] = Field(default=None, description="Total depth of field range in meters")
    hyperfocal_m: Optional[float] = Field(default=None, description="Calculated optical hyperfocal distance in meters")
    iris_geometry: ApertureIrisGeometry = Field(default=ApertureIrisGeometry.CIRCULAR_9_BLADE, description="Aperture diaphragm blade geometry")
    aberration_profile: Optional[OpticalAberrationProfile] = Field(default_factory=OpticalAberrationProfile, description="Lens optical aberration characteristics")
    rack_focus_target_m: Optional[float] = Field(default=None, description="Secondary focus distance in meters for rack-focus transition")
    rack_focus_start_time: float = Field(default=0.0, ge=0.0, description="Start timestamp of focus transition in seconds")
    rack_focus_duration_s: float = Field(default=1.5, ge=0.1, le=10.0, description="Duration of rack-focus transition in seconds")
    rack_focus_curve: RackFocusTransitionCurve = Field(default=RackFocusTransitionCurve.CUBIC_EASE_IN_OUT, description="Interpolation curve for rack focus")
    bokeh_descriptor: str = Field(default="creamy circular specular highlights with soft gaussian roll-off", description="Bokeh texture descriptor")
    is_deep_focus: bool = Field(default=False, description="Whether shot utilizes deep focus (stopping down to hyperfocal)")

    @field_validator("iris_geometry", mode="before")
    @classmethod
    def normalize_iris(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_clean = v.strip().lower().replace("-", "_").replace(" ", "_")
            for member in ApertureIrisGeometry:
                if v_clean == member.value:
                    return member
        return v

    @field_validator("rack_focus_curve", mode="before")
    @classmethod
    def normalize_curve(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_clean = v.strip().lower().replace("-", "_").replace(" ", "_")
            for member in RackFocusTransitionCurve:
                if v_clean == member.value:
                    return member
        return v

    @field_validator("sensor_format", mode="before")
    @classmethod
    def normalize_sensor(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_clean = v.strip().lower()
            if "super35" in v_clean or "super_35" in v_clean or "super 35" in v_clean:
                return SensorFormat.SUPER_35
            if "arri" in v_clean or "large format" in v_clean:
                return SensorFormat.ARRI_LF
            if "imax" in v_clean:
                return SensorFormat.IMAX_70MM
            if "vistavision" in v_clean or "vista" in v_clean:
                return SensorFormat.VISTAVISION
            if "full" in v_clean or "frame" in v_clean:
                return SensorFormat.FULL_FRAME
        return v


class DomainDofSpec(BaseModel):
    """Domain archetype depth of field and iris geometry specification (PM-FEAT-011)."""
    model_config = ConfigDict(extra="allow")

    focus_style: str = Field(..., description="Optical focus depth style descriptor")
    aperture_t_stop: float = Field(..., ge=0.5, le=32.0, description="Lens aperture T-stop")
    focal_length_mm: int = Field(..., ge=10, le=500, description="Lens focal length in mm")
    iris_geometry: str = Field(..., description="Aperture blade and iris bokeh geometry (e.g. nonagonal iris)")
    depth_character: str = Field(..., description="Depth of field behavior and focus transition character")
    description: str = Field(..., description="Summary string for prompt synthesis and reporting")

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)


class DomainLutSpec(BaseModel):
    """Domain archetype 3D LUT color science and film stock emulation specification (PM-FEAT-012)."""
    model_config = ConfigDict(extra="allow")

    lut_name: str = Field(..., description="Descriptive 3D LUT profile name")
    film_emulation: str = Field(..., description="Film stock or color science emulation profile")
    grid_size: int = Field(default=33, ge=17, le=65, description="3D LUT cube dimension grid (e.g. 33x33x33)")
    format: str = Field(default=".cube", description="LUT file format specification")
    cube_filename: str = Field(..., description="Exportable .cube file name")
    description: str = Field(..., description="Summary string for prompt synthesis and grading metadata")

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)


class LedWallGeometry(BaseModel):
    """Physical and digital geometry of the Virtual Production LED Volume."""
    shape: str = Field(default="curved_horseshoe")
    diameter_meters: float = Field(default=24.0, ge=5.0, le=100.0)
    height_meters: float = Field(default=6.5, ge=2.5, le=25.0)
    pixel_pitch_mm: float = Field(default=2.3)
    resolution_width_px: int = Field(default=15360)
    resolution_height_px: int = Field(default=2880)
    has_ceiling_led: bool = Field(default=True)
    has_floor_led: bool = Field(default=False)


class DmxLightingFixture(BaseModel):
    """DMX512 intelligent lighting fixture mapped to the stage."""
    fixture_id: str
    fixture_type: str = Field(default="Arri SkyPanel S360-C")
    dmx_universe: int = Field(default=1, ge=1, le=255)
    dmx_channel_start: int = Field(default=1, ge=1, le=512)
    intensity_percent: float = Field(default=85.0, ge=0.0, le=100.0)
    color_temp_kelvin: int = Field(default=5600, ge=2000, le=10000)
    gel_tint_cie_xy: Optional[Tuple[float, float]] = None

    @property
    def color_temperature_k(self) -> int:
        return self.color_temp_kelvin


class VirtualProductionStageSpec(BaseModel):
    """Virtual Production LED Volume and Unreal Engine ICVFX Stage manifest (PM-FEAT-008)."""
    stage_name: str = Field(default="StageCraft Volume Alpha")
    led_wall: LedWallGeometry = Field(default_factory=LedWallGeometry)
    frustum_tracking_protocol: str = Field(default="FreeD / OptiTrack Active Optical")
    ue_ndisplay_config_version: str = Field(default="5.4")
    parallax_depth_planes: Dict[str, float] = Field(
        default_factory=lambda: {
            "foreground_prop_m": 1.5,
            "actor_stage_m": 3.5,
            "led_wall_m": 8.0,
            "virtual_bg_infinity_m": 500.0,
        }
    )
    dmx_lighting_rig: List[DmxLightingFixture] = Field(default_factory=list)
    lut_calibration_profile: str = Field(default="ACEScg_OCIO_v1.3")

    @property
    def dmx_fixtures(self) -> List[DmxLightingFixture]:
        return self.dmx_lighting_rig


class MotionControlRigType(str, Enum):
    """Robotic Motion Control (MoCo) camera rig types (PM-FEAT-009)."""
    BOLT_CINEBOT = "bolt_cinebot"
    TECHNOCRANE = "technocrane"
    CABLECAM = "cablecam"
    STEADICAM = "steadicam"
    DRONE_FPV = "drone_fpv"
    RUSSIAN_ARM = "russian_arm"
    MOTORIZED_DOLLY = "motorized_dolly"

    # Lowercase aliases
    bolt_cinebot = "bolt_cinebot"
    technocrane = "technocrane"
    cablecam = "cablecam"
    steadicam = "steadicam"
    drone_fpv = "drone_fpv"
    russian_arm = "russian_arm"
    motorized_dolly = "motorized_dolly"


class TrajectoryWaypoint6DOF(BaseModel):
    """6-DOF spatial waypoint for high-speed motion control camera trajectories."""
    timecode_sec: float = Field(default=0.0, ge=0.0, description="Timecode timestamp in seconds from shot start")
    x_meters: float = Field(default=0.0, description="X translation coordinate in meters (stage coordinate space)")
    y_meters: float = Field(default=0.0, description="Y translation coordinate in meters (stage coordinate space)")
    z_meters: float = Field(default=1.5, description="Z elevation coordinate in meters above stage floor")
    roll_deg: float = Field(default=0.0, description="Camera roll angle in degrees")
    pitch_deg: float = Field(default=0.0, description="Camera pitch angle in degrees")
    yaw_deg: float = Field(default=0.0, description="Camera yaw angle in degrees")
    velocity_mps: float = Field(default=0.0, ge=0.0, description="Camera instantaneous velocity in meters per second")


class MocoRigSpec(BaseModel):
    """Motion Control (MoCo) robotic camera rig specification (PM-FEAT-009)."""
    rig_type: MotionControlRigType = Field(default=MotionControlRigType.BOLT_CINEBOT)
    payload_kg: float = Field(default=15.0, ge=0.5, le=100.0, description="Maximum camera package payload in kilograms")
    track_length_meters: float = Field(default=6.0, ge=0.0, le=100.0, description="Linear track length in meters (0 if stationary arm)")
    max_velocity_mps: float = Field(default=4.5, ge=0.1, le=25.0, description="Peak track / arm velocity in meters per second")
    waypoints: List[TrajectoryWaypoint6DOF] = Field(default_factory=list, description="6-DOF trajectory waypoints")
    locked_roll_stabilization: bool = Field(default=True, description="True if 3-axis horizon / roll lock is mechanically active")
    mechanical_backlash_mm: float = Field(default=0.05, ge=0.0, le=5.0, description="Repeatability tolerance / gear backlash in millimeters")

    @field_validator("rig_type", mode="before")
    @classmethod
    def normalize_rig_type(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_clean = v.strip().lower().replace("-", "_").replace(" ", "_")
            for member in MotionControlRigType:
                if v_clean == member.value:
                    return member
            for member in MotionControlRigType:
                if member.value in v_clean:
                    return member
        return v


class LightingFixtureRole(str, Enum):
    """Calibrated studio lighting fixture functional roles (PM-FEAT-010)."""
    KEY_LIGHT = "key_light"
    FILL_LIGHT = "fill_light"
    RIM_BACKLIGHT = "rim_backlight"
    KICKER = "kicker"
    PRACTICALS = "practicals"
    OVERHEAD_AMBIENT = "overhead_ambient"

    # Lowercase aliases
    key_light = "key_light"
    fill_light = "fill_light"
    rim_backlight = "rim_backlight"
    kicker = "kicker"
    practicals = "practicals"
    overhead_ambient = "overhead_ambient"


class DiffusionGrade(str, Enum):
    """Studio lighting diffusion materials and grades (PM-FEAT-010)."""
    HARD_SPECULAR = "hard_specular"
    QUARTER_GRID = "quarter_grid"
    HALF_GRID = "half_grid"
    FULL_GRID = "full_grid"
    HAMPSHIRE_FROST = "hampshire_frost"
    BLEACHED_MUSLIN = "bleached_muslin"
    CHIMERA_SOFTBOX = "chimera_softbox"

    # Lowercase aliases
    hard_specular = "hard_specular"
    quarter_grid = "quarter_grid"
    half_grid = "half_grid"
    full_grid = "full_grid"
    hampshire_frost = "hampshire_frost"
    bleached_muslin = "bleached_muslin"
    chimera_softbox = "chimera_softbox"


class ParticulateHazeType(str, Enum):
    """Volumetric atmospheric haze and particulate suspension types (PM-FEAT-010)."""
    CLEAN_AIR = "clean_air"
    MINERAL_HAZE = "mineral_haze"
    OIL_FOG = "oil_fog"
    CRYOGENIC_SMOKE = "cryogenic_smoke"
    ATMOSPHERIC_DUST = "atmospheric_dust"

    # Lowercase aliases
    clean_air = "clean_air"
    mineral_haze = "mineral_haze"
    oil_fog = "oil_fog"
    cryogenic_smoke = "cryogenic_smoke"
    atmospheric_dust = "atmospheric_dust"


class StudioLightFixtureSpec(BaseModel):
    """Individual calibrated studio lighting fixture specification (PM-FEAT-010)."""
    fixture_id: str = Field(..., description="Unique fixture identifier (e.g. 'KEY_01', 'RIM_02')")
    role: LightingFixtureRole = Field(default=LightingFixtureRole.KEY_LIGHT)
    fixture_type: str = Field(default="ARRI SkyPanel S360-C", description="Fixture model or lamphead type")
    cct_kelvin: int = Field(default=5600, ge=1800, le=12000, description="Correlated Color Temperature in Kelvin")
    lux_intensity: float = Field(default=2500.0, ge=0.0, description="Incident illumination intensity in lux at target")
    beam_angle_deg: float = Field(default=45.0, ge=5.0, le=180.0, description="Beam spread angle in degrees")
    diffusion_grade: DiffusionGrade = Field(default=DiffusionGrade.HALF_GRID)
    distance_meters: float = Field(default=3.5, ge=0.1, le=50.0, description="Physical distance from subject in meters")
    dmx_channel: int = Field(default=1, ge=1, le=512, description="DMX512 start channel address")

    @field_validator("role", mode="before")
    @classmethod
    def normalize_role(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_clean = v.strip().lower().replace("-", "_").replace(" ", "_")
            for member in LightingFixtureRole:
                if v_clean == member.value:
                    return member
        return v

    @field_validator("diffusion_grade", mode="before")
    @classmethod
    def normalize_diffusion(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_clean = v.strip().lower().replace("-", "_").replace(" ", "_")
            for member in DiffusionGrade:
                if v_clean == member.value:
                    return member
        return v


class AtmosphericHazeSpec(BaseModel):
    """Volumetric atmospheric haze and optical scattering specification (PM-FEAT-010)."""
    haze_type: ParticulateHazeType = Field(default=ParticulateHazeType.MINERAL_HAZE)
    particulate_density: float = Field(default=0.15, ge=0.0, le=1.0, description="Normalized particulate suspension density (0.0=none, 1.0=dense)")
    scattering_coefficient: float = Field(default=0.45, ge=0.0, le=1.0, description="Rayleigh/Mie forward scattering coefficient")
    shaft_visibility: float = Field(default=0.6, ge=0.0, le=1.0, description="Volumetric light shaft visibility ratio")

    @field_validator("haze_type", mode="before")
    @classmethod
    def normalize_haze(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_clean = v.strip().lower().replace("-", "_").replace(" ", "_")
            for member in ParticulateHazeType:
                if v_clean == member.value:
                    return member
        return v


class LightingRigSpec(BaseModel):
    """Complete calibrated multi-fixture lighting rig and atmospheric environment (PM-FEAT-010)."""
    fixtures: List[StudioLightFixtureSpec] = Field(default_factory=list, description="Calibrated lighting fixtures")
    key_to_fill_ratio: float = Field(default=4.0, ge=1.0, le=64.0, description="Key-to-fill contrast lighting ratio (e.g. 4.0 for 4:1)")
    key_to_rim_ratio: float = Field(default=2.0, ge=0.1, le=32.0, description="Key-to-rim accent separation ratio")
    total_lux: float = Field(default=5000.0, ge=0.0, description="Estimated total aggregate incident lux at key subject plane")
    atmospheric_haze: Optional[AtmosphericHazeSpec] = Field(default=None, description="Volumetric particulate atmospheric haze profile")


class CraftCameraSpec(BaseModel):
    """Kinetic Camera Grammar (CRAFT Framework)."""
    rig_type: str = Field(..., description="Locked-off tripod, Dolly track, Steadicam, Technocrane, etc.")
    focal_length_mm: int = Field(default=35, ge=10, le=500, description="Focal length in millimeters (10mm to 500mm)")
    composition: str = Field(..., description="Framing geometry, horizon line, rule of thirds, subject placement")
    route: str = Field(..., description="Trajectory vector, pan/tilt/roll axis, dolly speed")
    action_anchor: str = Field(..., description="Physical subject or contact point that guides tracking")
    focus_axis: str = Field(..., description="Depth of field, rack focus timing, 180-degree axis lock")
    tone_rig: str = Field(..., description="Lens characteristics, anamorphic bokeh, optical texture")
    shutter_angle_deg: float = Field(default=180.0, ge=11.25, le=360.0, description="Shutter angle in degrees (e.g. 180.0 standard, 90.0 staccato)")
    shutter_timing_token: Optional[str] = Field(default=None, description="Cinematic shutter timing prompt token (e.g. '180° shutter at 1/48s')")
    optical_lens: Optional[OpticalLensSpec] = Field(default=None, description="Detailed optical lens and sensor framing specification")
    moco_rig: Optional[MocoRigSpec] = Field(default=None, description="Robotic motion control rig specification (PM-FEAT-009)")
    dof_spec: Optional[DepthOfFieldSpec] = Field(default=None, description="Depth of field, optical physics, and rack focus specification (PM-FEAT-011)")

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
    stems: Dict[str, str] = Field(
        default_factory=lambda: {
            "percussion": "Rhythmic pulse and transient acoustic hits",
            "bass": "Sub-harmonic foundation and low-end drone",
            "harmony": "Mid-range chord progression and ambient pads",
            "lead": "Hero melodic motif or lead arpeggio",
        },
        description="Acoustic stem layers for dynamic mixing and foley sidechaining"
    )
    dynamic_arc: str = Field(..., description="Progression across runtime (Intro, Build, Climax, Outro)")
    lyria_prompt: str = Field(..., description="Ready-to-use text prompt for Lyria / audio model")


class StemType(str, Enum):
    """Post-production audio stem types."""
    DIALOGUE = "dialogue"
    FOLEY = "foley"
    AMBIENCE = "ambience"
    MUSIC = "music"

    # Lowercase aliases
    dialogue = "dialogue"
    foley = "foley"
    ambience = "ambience"
    music = "music"


class StemChannelStrip(BaseModel):
    """Individual audio stem mixer channel settings."""
    stem: StemType
    label: str
    gain_db: float = Field(default=0.0, ge=-60.0, le=12.0)
    pan: float = Field(default=0.0, ge=-1.0, le=1.0)
    muted: bool = False
    solo: bool = False
    target_lufs: float = Field(default=-24.0, ge=-36.0, le=-12.0)


def _default_audio_stem_channels() -> Dict[str, StemChannelStrip]:
    return {
        "dialogue": StemChannelStrip(stem=StemType.DIALOGUE, label="Dialogue", gain_db=0.0, pan=0.0, target_lufs=-18.0),
        "foley": StemChannelStrip(stem=StemType.FOLEY, label="Foley / SFX", gain_db=0.0, pan=0.0, target_lufs=-20.0),
        "ambience": StemChannelStrip(stem=StemType.AMBIENCE, label="Ambience", gain_db=-3.0, pan=0.0, target_lufs=-24.0),
        "music": StemChannelStrip(stem=StemType.MUSIC, label="BGM Score", gain_db=-2.0, pan=0.0, target_lufs=-18.0),
    }


class AudioStemMixerSpec(BaseModel):
    """Complete 4-stem post-production audio mixing blueprint."""
    master_gain_db: float = Field(default=0.0, ge=-60.0, le=6.0)
    master_lufs_target: float = Field(default=-23.0, description="EBU R128 (-23 LUFS) or ATSC A/85 (-24 LUFS)")
    channels: Dict[str, StemChannelStrip] = Field(default_factory=_default_audio_stem_channels)

    @model_validator(mode="before")
    @classmethod
    def normalize_channels(cls, data: Any) -> Any:
        if isinstance(data, dict) and "channels" in data and isinstance(data["channels"], dict):
            norm_channels = {}
            for k, v in data["channels"].items():
                key_str = k.value if hasattr(k, "value") else str(k)
                norm_channels[key_str] = v
            data["channels"] = norm_channels
        return data

    def __getitem__(self, key: Union[str, StemType]) -> StemChannelStrip:
        key_str = key.value if hasattr(key, "value") else str(key)
        return self.channels[key_str]

    def __contains__(self, key: Union[str, StemType]) -> bool:
        key_str = key.value if hasattr(key, "value") else str(key)
        return key_str in self.channels

    def get(self, key: Union[str, StemType], default: Any = None) -> Any:
        key_str = key.value if hasattr(key, "value") else str(key)
        return self.channels.get(key_str, default)

    @classmethod
    def create_default(cls) -> "AudioStemMixerSpec":
        return cls(
            master_gain_db=0.0,
            master_lufs_target=-23.0,
            channels=_default_audio_stem_channels(),
        )


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
    speed_ramp: Optional[SpeedRampCurveSpec] = Field(
        default=None,
        description="Dynamic speed ramp and motion timing specification"
    )
    scene_color_look: Optional[ColorLookSpec] = Field(
        default=None,
        description="Scene-specific ASC CDL color grading specification"
    )
    optical_lens: Optional[OpticalLensSpec] = Field(
        default=None,
        description="Scene-specific optical lens and sensor framing specification (PM-FEAT-007)"
    )
    virtual_production: Optional[VirtualProductionStageSpec] = Field(
        default=None,
        description="In-camera VFX / Virtual Production LED volume stage manifest (PM-FEAT-008)"
    )
    moco_rig: Optional[MocoRigSpec] = Field(
        default=None,
        description="Scene-specific motion control rig specification (PM-FEAT-009)"
    )
    lighting_rig: Optional[LightingRigSpec] = Field(
        default=None,
        description="Scene-specific studio lighting rig specification (PM-FEAT-010)"
    )
    dof_spec: Optional[Union[DepthOfFieldSpec, DomainDofSpec]] = Field(
        default=None,
        description="Scene-specific depth of field and rack focus specification (PM-FEAT-011)"
    )
    lut_spec: Optional[Union[ThreeDimensionalLutSpec, DomainLutSpec]] = Field(
        default=None,
        description="Scene-specific 3D LUT specification (PM-FEAT-012)"
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
            if "color_look" in data and "scene_color_look" not in data:
                data["scene_color_look"] = data["color_look"]
            if "speed_ramp_spec" in data and "speed_ramp" not in data:
                data["speed_ramp"] = data["speed_ramp_spec"]
            if "speed_ramp_curve" in data and "speed_ramp" not in data:
                data["speed_ramp"] = data["speed_ramp_curve"]
            if "lens_spec" in data and "optical_lens" not in data:
                data["optical_lens"] = data["lens_spec"]
            if "optical_lens_spec" in data and "optical_lens" not in data:
                data["optical_lens"] = data["optical_lens_spec"]
            if "virtual_production_spec" in data and "virtual_production" not in data:
                data["virtual_production"] = data["virtual_production_spec"]
            if "vp_stage" in data and "virtual_production" not in data:
                data["virtual_production"] = data["vp_stage"]
            if "moco_rig_spec" in data and "moco_rig" not in data:
                data["moco_rig"] = data["moco_rig_spec"]
            if "moco" in data and "moco_rig" not in data:
                data["moco_rig"] = data["moco"]
            if "lighting_rig_spec" in data and "lighting_rig" not in data:
                data["lighting_rig"] = data["lighting_rig_spec"]
            if "lighting" in data and "lighting_rig" not in data and isinstance(data["lighting"], (dict, LightingRigSpec)):
                data["lighting_rig"] = data["lighting"]
            if "kinetic_contact_chain" in data and isinstance(data["kinetic_contact_chain"], KineticContactChain):
                data["kinetic_contact_chain"] = data["kinetic_contact_chain"].to_prompt_string()
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

    @property
    def lens_spec(self) -> Optional[OpticalLensSpec]:
        return self.optical_lens

    @lens_spec.setter
    def lens_spec(self, value: Optional[OpticalLensSpec]) -> None:
        self.optical_lens = value

    @property
    def vp_stage(self) -> Optional[VirtualProductionStageSpec]:
        return self.virtual_production

    @vp_stage.setter
    def vp_stage(self, value: Optional[VirtualProductionStageSpec]) -> None:
        self.virtual_production = value

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
    master_color_look: Optional[ColorLookSpec] = Field(
        default=None,
        description="Master ASC CDL color grading specification and look preset"
    )
    master_audio_mixer: Optional[AudioStemMixerSpec] = Field(
        default=None,
        description="Master 4-stem post-production audio mixing blueprint"
    )
    master_lens_package: Optional[OpticalLensSpec] = Field(
        default=None,
        description="Master optical lens package and sensor framing specification (PM-FEAT-007)"
    )
    virtual_production: Optional[VirtualProductionStageSpec] = Field(
        default=None,
        description="Virtual Production LED Volume & Unreal Engine Stage Manifest (PM-FEAT-008)"
    )
    master_moco_rig: Optional[MocoRigSpec] = Field(
        default=None,
        description="Master motion control camera rig specification (PM-FEAT-009)"
    )
    master_lighting_rig: Optional[LightingRigSpec] = Field(
        default=None,
        description="Master studio lighting rig specification (PM-FEAT-010)"
    )
    master_dof_spec: Optional[Union[DepthOfFieldSpec, DomainDofSpec]] = Field(
        default=None,
        description="Master depth of field and optical focus specification (PM-FEAT-011)"
    )
    dof_spec: Optional[Union[DepthOfFieldSpec, DomainDofSpec]] = Field(
        default=None,
        description="Master depth of field and optical focus specification alias (PM-FEAT-011)"
    )
    master_lut_spec: Optional[Union[ThreeDimensionalLutSpec, DomainLutSpec]] = Field(
        default=None,
        description="Master 3D LUT grading profile specification (PM-FEAT-012)"
    )
    lut_spec: Optional[Union[ThreeDimensionalLutSpec, DomainLutSpec]] = Field(
        default=None,
        description="Master 3D LUT grading profile specification alias (PM-FEAT-012)"
    )

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
        if self.storytelling_mode == StorytellingMode.MODE_B_CONTINUOUS_CHAIN and self.total_runtime_seconds > 40:
            raise ValueError(
                f"Mode B continuous chain runtime violation: total_runtime_seconds={self.total_runtime_seconds} "
                "exceeds the 40-second ceiling (maximum 4 continuous 10s extensions)."
            )
        # Synchronize DoF and LUT spec aliases
        if self.master_dof_spec is not None and self.dof_spec is None:
            object.__setattr__(self, "dof_spec", self.master_dof_spec)
        elif self.dof_spec is not None and self.master_dof_spec is None:
            object.__setattr__(self, "master_dof_spec", self.dof_spec)

        if self.master_lut_spec is not None and self.lut_spec is None:
            object.__setattr__(self, "lut_spec", self.master_lut_spec)
        elif self.lut_spec is not None and self.master_lut_spec is None:
            object.__setattr__(self, "master_lut_spec", self.lut_spec)

        return self


    @property
    def is_mode_b_continuous(self) -> bool:
        """Validates that a Mode B production bible preserves continuity and runtime invariants."""
        if self.storytelling_mode != StorytellingMode.MODE_B_CONTINUOUS_CHAIN:
            return False
        if len(self.scenes) <= 1:
            return True
        # Mode B maximum runtime is capped at 40s (4x 10s extensions)
        if self.total_runtime_seconds > 40:
            return False
        return True


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


SENIOR_PM_PERSONA_PROMPT = (
    "You are a world-class senior product manager that recently joined this project "
    "from a top software company. You will inspect everything about this product and "
    "recommend new features and improvements to the product council who will then implement it."
)


class CouncilPersona(str, Enum):
    """The four scoring disciplines of the Autonomous Product Council plus the Senior Product Manager."""
    FORWARD_DEPLOYED_ENGINEER = "council-fde"
    AGENT_SYSTEMS_ENGINEER = "council-agent-engineer"
    AGENT_STRATEGIST = "council-strategist"
    UX_UI_DESIGNER = "council-ux-designer"
    PRODUCT_MANAGER = "council-product-manager"

    # Aliases
    COUNCIL_FDE = "council-fde"
    COUNCIL_AGENT_ENGINEER = "council-agent-engineer"
    COUNCIL_STRATEGIST = "council-strategist"
    COUNCIL_UX_DESIGNER = "council-ux-designer"
    COUNCIL_PRODUCT_MANAGER = "council-product-manager"


class ProductFeatureProposal(BaseModel):
    """A feature or product improvement recommended by the Senior Product Manager."""
    feature_id: str
    title: str
    problem_statement: str
    proposed_solution: str
    target_modules: List[str] = Field(default_factory=list)
    priority: str = "P0"
    status: str = "implemented"


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
    """Unified 100-point 4-persona Product Council evaluation report with Senior PM roadmap."""
    version: str = "2.6.0"
    project_title: str = ""
    timestamp: str = ""
    overall_score: float = Field(default=100.0, ge=0.0, le=100.0)
    passed: bool = True
    critical_findings_count: int = 0
    reviews: List[PersonaReviewResult] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    pm_persona_prompt: str = SENIOR_PM_PERSONA_PROMPT
    pm_recommendations: List[ProductFeatureProposal] = Field(default_factory=list)

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


# ADK 2.0 Architectural Schema Aliases
ScenePromptPayload = ScenePromptSpec


