import hashlib
import math
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from omni_director.schemas import (
    AcousticMaterialType,
    AcousticRoomImpulseResponse,
    ActionBeatSpec,
    AicpLineItemSpec,
    AicpSectionCode,
    AicpTopSheetSummarySpec,
    AnamorphicSqueeze,
    AscMhlHashEntry,
    AscMhlManifestSpec,
    AspectRatio,
    AudioStemMixerSpec,
    BroadcastLoudnessStandard,
    BroadcastTraffickingSlateSpec,
    CameraAxisPlacement,
    CharacterTurnaroundSpec,
    ClapperSlateSpec,
    ClearanceRecordSpec,
    ClearanceStatus,
    ColorLookPreset,
    ColorLookSpec,
    ColorVolumeGamut,
    CraftCameraSpec,
    CrewLaborTier,
    CryptomatteManifestSpec,
    CutdownFormatType,
    DeliverableAspectRatio,
    DeliveryReframeManifestSpec,
    DiegeticSonicSpec,
    DmxLightingFixture,
    DolbyAtmosBedFormat,
    DomainArchetype,
    DomainDofSpec,
    DomainLutSpec,
    DroneFlightPathSpec,
    DroneRigType,
    EditorialCutType,
    FilmGaugeFormat,
    FilmStockManufacturer,
    FilmStockSpec,
    FlightWaypointGPS,
    GateWeavePhysicsSpec,
    GimbalOrientationSpec,
    GrainPhysicsSpec,
    HalationPhysicsSpec,
    HdrMasteringDisplaySpec,
    HdrMetadataSpec,
    HdrTransferFunction,
    InterSceneCutCheckSpec,
    LedWallGeometry,
    LightingRigSpec,
    LoudnessComplianceSpec,
    MarkerColorTag,
    MasterAicpBidSpec,
    MasterBgmSpec,
    MasterBroadcastQcSpec,
    MasterClientReviewSpec,
    MasterContinuityBlockingSpec,
    MasterEnvironmentSpec,
    MasterProductionBible,
    MasterProductionSlateSpec,
    MasterStripboardScheduleSpec,
    MocoRigSpec,
    MotionControlRigType,
    NanoBananaReference,
    OpticalLensSpec,
    PseFlashCheckSpec,
    QcVerdictStatus,
    ReframePanMode,
    RegimeType,
    ReviewAnnotationSpec,
    ReviewApprovalStatus,
    ReviewerRole,
    ReviewPinCoordinate,
    SceneBlockingSpec,
    ScenePromptSpec,
    SceneQcProfileSpec,
    SceneReframeSpec,
    SceneReviewSignoffSpec,
    ScreenDirection,
    ScriptBreakdownSheet,
    SensorFormat,
    ShotScaleSize,
    Smpte12MTimecodeSpec,
    SocialDeliveryPlatform,
    SolarEphemerisSpec,
    SpatialAudioObjectSpec,
    SpatialAudioSoundfieldSpec,
    SpatialCoordinate3D,
    SpeedRampCurveSpec,
    SpeedRampMode,
    StageBlockingEntity,
    StemChannelStrip,
    StemType,
    StorytellingMode,
    ToneMappingOperator,
    VfxCompositingManifestSpec,
    VfxLayerChannelSpec,
    VfxRenderPassType,
    VirtualProductionStageSpec,
    WindDriftVectorSpec,
)
from omni_director.tools.aicp_budget import calculate_aicp_top_sheet
from omni_director.tools.clapper_slate import (
    calculate_smpte12m_frames,
    format_smpte12m_timecode,
)
from omni_director.tools.drone_flight import (
    format_drone_flight_prompt_token,
    synthesize_default_drone_flight,
)
from omni_director.tools.color_grade import get_preset_color_look
from omni_director.tools.lighting_rig import synthesize_default_lighting_rig
from omni_director.tools.moco_kinematics import synthesize_default_moco_rig
from omni_director.tools.optical_lens import calculate_hyperfocal_distance, calculate_sensor_fov
from omni_director.tools.spatial_audio import calculate_eyring_rt60, calculate_sabine_rt60
from omni_director.tools.speed_ramp import synthesize_speed_ramp_curve
from omni_director.tools.stripboard_scheduler import (
    extract_script_breakdown_sheet,
    generate_stripboard_schedule,
)
from omni_director.tools.vfx_compositor import generate_cryptomatte_manifest
from omni_director.tools.virtual_production import synthesize_default_vp_stage
from omni_director.tools.delivery_reframe import (
    calculate_aspect_crop_window,
    format_reframe_prompt_token,
    synthesize_cutdown_versions,
    synthesize_default_reframe_manifest,
    synthesize_default_scene_reframe,
)
from omni_director.tools.broadcast_qc import (
    LOUDNESS_STANDARDS,
    evaluate_scene_pse_safety,
    format_broadcast_qc_prompt_token,
    synthesize_default_broadcast_qc_spec,
    synthesize_default_scene_qc,
    synthesize_rights_clearances,
    validate_loudness_target,
)
from omni_director.tools.continuity_blocking import (
    evaluate_180_axis_and_30_rule,
    format_continuity_prompt_token,
    synthesize_default_continuity_blocking,
    synthesize_scene_blocking,
)
from omni_director.tools.review_notes import (
    compile_review_note_to_delta,
    format_review_prompt_token,
    synthesize_default_client_review,
    synthesize_scene_review_signoff,
)

DOMAIN_PRIORITY: List[str] = [
    "automotive_robotics",
    "culinary_asmr",
    "luxury_fashion",
    "kinetic_action",
    "tech_hardware",
    "architectural_sanctuary",
]

DOMAIN_ARCHETYPES: Dict[str, Dict[str, Any]] = {
    "automotive_robotics": {
        "keywords": [
            "vehicle", "vehicles", "drone", "drones", "robot", "robotics", "hypercar", "hypercars", "car", "cars",
            "motorsport", "motorsports", "motorcycle", "motorcycles", "pursuit", "engine", "chassis", "autonomous",
            "telemetry", "hydraulic", "suspension", "carbon fiber", "speedway", "racing", "supercar", "drivetrain"
        ],
        "default_camera": "Russian Arm 28mm Anamorphic with dynamic low-angle tracking",
        "camera_rigs": [
            "Russian Arm 28mm Anamorphic with dynamic low-angle tracking",
            "Technocrane 35mm Prime tracking lateral drift arc",
        ],
        "default_focal_length": 28,
        "default_lighting": "Cool 6500K high-contrast industrial LED with sharp metallic rim highlights",
        "default_character": {
            "name": "Lead Test Pilot / Telematics Specialist",
            "silhouette": "Aerodynamic high-speed racing posture with locked kinetic poise",
            "wardrobe_polarity": "Matte graphite fire-retardant racing suit with reflective telemetry piping",
            "movement_signature": "Instantaneous micrometric steering corrections and decisive torque control",
        },
        "default_invariants": [
            "Carbon fiber aerodynamic chassis maintains unyielding physical rigidity",
            "Wet tarmac surface reflects neon horizon with true raytraced consistency"
        ],
        "default_foley": [
            "High-torque electric motor whine",
            "Tire friction on slick asphalt",
            "Pneumatic valve hiss",
            "Mechanical robotic servo snaps"
        ],
        "default_bpm": 130,
        "default_key": "F Minor",
        "default_bgm_genre": "Industrial Electronic & Cybernetic Kinetic Score",
        "color_palette": ["#0B0E14", "#00F0FF", "#FF3B30", "#8E8E93"],
        "regime": RegimeType.REGIME_2_KINETIC,
        "color_look_preset": ColorLookPreset.BLEACH_BYPASS_SILVER,
        "speed_ramp_mode": SpeedRampMode.SNAP_FREEZE_RESUME,
        "default_shutter_angle": 90.0,
        "default_stem_levels": {
            "dialogue": {"gain_db": 0.0, "target_lufs": -18.0},
            "foley": {"gain_db": 2.0, "target_lufs": -18.0},
            "ambience": {"gain_db": -3.0, "target_lufs": -24.0},
            "music": {"gain_db": -2.0, "target_lufs": -18.0},
        },
        "optical_lens": {
            "sensor_format": SensorFormat.ARRI_LF,
            "anamorphic_squeeze": 1.8,
            "focal_length_mm": 28,
            "aperture_t_stop": 2.0,
            "lens_series": "ARRI Rental DNA Anamorphic",
            "bokeh_characteristic": "oval horizontal streak anamorphic flare",
            "chromatic_aberration": "controlled blue lateral chromatic fringing",
            "distortion_profile": "barrel 1.2% anamorphic edge compression",
        },
        "dof_spec": DomainDofSpec(
            focus_style="Dynamic deep focus",
            aperture_t_stop=5.6,
            focal_length_mm=24,
            iris_geometry="circular iris",
            depth_character="hyperfocal tracking",
            description="Dynamic deep focus (T5.6, 24mm, circular iris, hyperfocal tracking)",
        ),
        "lut_spec": DomainLutSpec(
            lut_name="Teal & Orange high-velocity metallic",
            film_emulation="teal_and_orange_metallic",
            grid_size=33,
            format=".cube",
            cube_filename="teal_orange_metallic_33x33.cube",
            description="Teal & Orange high-velocity metallic 33x33 .cube",
        ),
    },
    "culinary_asmr": {
        "keywords": [
            "food", "coffee", "matcha", "cooking", "beverage", "kitchen", "culinary", "chef", "sizzle",
            "caramelization", "knife", "ingredient", "recipe", "baking", "espresso", "dining", "texture",
            "crunch", "taste", "flavor", "dough", "tea", "asmr", "whisk", "gastronomy", "pour", "plate",
            "roast", "brew", "steam", "cocktail"
        ],
        "default_camera": "100mm Macro Probe Lens with micro-fluidic pan and tilt",
        "camera_rigs": [
            "100mm Macro Probe Lens with micro-fluidic pan and tilt",
            "50mm Overhead Top-Down Rig with locked vertical axis",
        ],
        "default_focal_length": 100,
        "default_lighting": "Warm 3200K tungsten backlight emphasizing surface steam and glistening oils",
        "default_character": {
            "name": "Master Artisanal Chef / Tea Master",
            "silhouette": "Minimalist focused posture with steady hands and rolled linen sleeves",
            "wardrobe_polarity": "Unbleached raw natural linen apron over matte charcoal tunic",
            "movement_signature": "Deliberate, rhythmic, micro-fluidic hand gestures with zero tremor",
        },
        "default_invariants": [
            "Handmade ceramic vessel lip retains exact physical geometry",
            "Natural hinoki cedar countertop surface grain remains mechanically rigid"
        ],
        "default_foley": [
            "Crisp blade cutting through textured crust",
            "Gentle butter sizzle in cast iron",
            "Tactile ceramic clink",
            "Subtle simmering bubble pops"
        ],
        "default_bpm": 68,
        "default_key": "C Major",
        "default_bgm_genre": "Intimate Acoustic & Organic Ambient ASMR",
        "color_palette": ["#1C1917", "#D97706", "#F59E0B", "#FEF3C7"],
        "regime": RegimeType.REGIME_2_KINETIC,
        "color_look_preset": ColorLookPreset.KODAK_5219_VISION3,
        "speed_ramp_mode": SpeedRampMode.DECELERATION_IMPACT,
        "default_shutter_angle": 180.0,
        "default_stem_levels": {
            "dialogue": {"gain_db": 0.0, "target_lufs": -18.0},
            "foley": {"gain_db": 2.5, "target_lufs": -20.0},
            "ambience": {"gain_db": -4.0, "target_lufs": -26.0},
            "music": {"gain_db": -4.0, "target_lufs": -22.0},
        },
        "optical_lens": {
            "sensor_format": SensorFormat.FULL_FRAME,
            "anamorphic_squeeze": 1.0,
            "focal_length_mm": 100,
            "aperture_t_stop": 2.8,
            "lens_series": "Zeiss Supreme 100mm Macro Prime",
            "bokeh_characteristic": "buttery circular 9-blade macro falloff",
            "chromatic_aberration": "apochromatic zero-dispersion fluorite",
            "distortion_profile": "zero geometric distortion rectilinear",
        },
        "dof_spec": DomainDofSpec(
            focus_style="Macro shallow focus",
            aperture_t_stop=1.4,
            focal_length_mm=100,
            iris_geometry="nonagonal iris",
            depth_character="razor-thin DoF",
            description="Macro shallow focus (T1.4, 100mm, nonagonal iris, razor-thin DoF)",
        ),
        "lut_spec": DomainLutSpec(
            lut_name="Warm Kodak 5219 Vision3 emulation",
            film_emulation="kodak_5219_vision3",
            grid_size=33,
            format=".cube",
            cube_filename="kodak_5219_vision3_33x33.cube",
            description="Warm Kodak 5219 Vision3 emulation 33x33 .cube",
        ),
    },
    "luxury_fashion": {
        "keywords": [
            "fashion", "runway", "cosmetics", "perfume", "couture", "jewelry", "model", "models", "haute",
            "makeup", "velvet", "silk", "wardrobe", "strut", "editorial", "beauty", "lipstick", "fragrance",
            "vogue", "glamour", "apparel", "luxury", "monogram", "flagship"
        ],
        "default_camera": "50mm Prime on Steadicam Ultra with gentle vertical float",
        "camera_rigs": [
            "50mm Prime on Steadicam Ultra with gentle vertical float",
            "85mm Portrait Prime tracking eye-level beauty framing",
        ],
        "default_focal_length": 50,
        "default_lighting": "5600K diffused commercial beauty illumination with reflective mirror bounce",
        "default_character": {
            "name": "Haute Couture Runway Model",
            "silhouette": "Statuesque architectural posture with dynamic high-fashion stride",
            "wardrobe_polarity": "Sculptural black velvet evening coat with structured iridescent silk lapels",
            "movement_signature": "Fluid, confident, momentum-conserving runway cadence",
        },
        "default_invariants": [
            "Haute couture garment maintains structural textile tension and crisp drape",
            "Polished runway mirror floor reflects silhouettes with optical clarity"
        ],
        "default_foley": [
            "Rhythmic stiletto heel clicks on polished marble",
            "Crisp textile rustle of silk taffeta",
            "Metallic snap of luxury compact",
            "Subtle perfume atomizer mist spray"
        ],
        "default_bpm": 118,
        "default_key": "A Minor",
        "default_bgm_genre": "Deep House Runway & Parisian Haute Couture Pulse",
        "color_palette": ["#09090B", "#F43F5E", "#E2E8F0", "#D4AF37"],
        "regime": RegimeType.REGIME_2_KINETIC,
        "color_look_preset": ColorLookPreset.FUJI_ETERNA_500T,
        "speed_ramp_mode": SpeedRampMode.PULSE_TIME_DILATION,
        "default_shutter_angle": 180.0,
        "default_stem_levels": {
            "dialogue": {"gain_db": 0.0, "target_lufs": -18.0},
            "foley": {"gain_db": 0.0, "target_lufs": -20.0},
            "ambience": {"gain_db": -3.0, "target_lufs": -24.0},
            "music": {"gain_db": 1.0, "target_lufs": -16.0},
        },
        "optical_lens": {
            "sensor_format": SensorFormat.ARRI_LF,
            "anamorphic_squeeze": 1.5,
            "focal_length_mm": 50,
            "aperture_t_stop": 1.8,
            "lens_series": "Cooke Anamorphic /i Full Frame Plus",
            "bokeh_characteristic": "creamy organic Cooke look with subtle oval flares",
            "chromatic_aberration": "delicate warm axial flare roll-off",
            "distortion_profile": "subtle pincushion 0.4% flattering portrait geometry",
        },
        "dof_spec": DomainDofSpec(
            focus_style="Anamorphic shallow portraiture",
            aperture_t_stop=1.8,
            focal_length_mm=85,
            iris_geometry="2x oval bokeh",
            depth_character="rack-focus",
            description="Anamorphic shallow portraiture (T1.8, 85mm, 2x oval bokeh, rack-focus)",
        ),
        "lut_spec": DomainLutSpec(
            lut_name="Bleach Bypass Silver high-contrast",
            film_emulation="bleach_bypass_silver",
            grid_size=33,
            format=".cube",
            cube_filename="bleach_bypass_silver_33x33.cube",
            description="Bleach Bypass Silver high-contrast 33x33 .cube",
        ),
    },
    "kinetic_action": {
        "keywords": [
            "sport", "sports", "running", "martial arts", "parkour", "athletics", "dance", "athlete",
            "jump", "boxing", "climbing", "kick", "sprint", "workout", "fitness", "dynamic movement",
            "stunt", "acrobatic", "action", "kinetic", "velocity", "aerodynamic", "speed", "agility", "impact"
        ],
        "default_camera": "High-Speed Wire Rig with 24mm Ultra-Wide lens and zero horizon roll",
        "camera_rigs": [
            "High-Speed Wire Rig with 24mm Ultra-Wide lens and zero horizon roll",
            "Cable-Cam 35mm Prime following ballistic trajectory",
        ],
        "default_focal_length": 24,
        "default_lighting": "Dynamic high-noon direct daylight with deep hard directional shadows",
        "default_character": {
            "name": "Elite Parkour / Calisthenics Athlete",
            "silhouette": "Athletic minimalist silhouette with sharp aerodynamic contours",
            "wardrobe_polarity": "Matte black performance composite with high-visibility amber accents",
            "movement_signature": "Explosive, decisive, momentum-conserving kinetic vaults and landings",
        },
        "default_invariants": [
            "Reinforced concrete ledge structure remains completely unyielding",
            "Friction contact point exhibits micro-surface dust without floating"
        ],
        "default_foley": [
            "Athletic shoe sole squeak and ground impact",
            "Heavy synchronized breath cadence",
            "Wind rush over aerodynamic limbs",
            "Resonant physical force transfer thud"
        ],
        "default_bpm": 140,
        "default_key": "E Minor",
        "default_bgm_genre": "High-Velocity Orchestral Breakbeat & Hybrid Trap",
        "color_palette": ["#18181B", "#22C55E", "#3B82F6", "#FAFAFA"],
        "regime": RegimeType.REGIME_2_KINETIC,
        "color_look_preset": ColorLookPreset.TEAL_AND_ORANGE_BLOCKBUSTER,
        "speed_ramp_mode": SpeedRampMode.ACCELERATION_BURST,
        "default_shutter_angle": 180.0,
        "default_stem_levels": {
            "dialogue": {"gain_db": 0.0, "target_lufs": -18.0},
            "foley": {"gain_db": 2.0, "target_lufs": -18.0},
            "ambience": {"gain_db": -3.0, "target_lufs": -24.0},
            "music": {"gain_db": 1.0, "target_lufs": -16.0},
        },
        "optical_lens": {
            "sensor_format": SensorFormat.IMAX_70MM,
            "anamorphic_squeeze": 1.33,
            "focal_length_mm": 35,
            "aperture_t_stop": 2.0,
            "lens_series": "Panavision Ultra Vista Large Format",
            "bokeh_characteristic": "dynamic wide-angle elliptical focus falloff",
            "chromatic_aberration": "apochromatic high-contrast edge rendering",
            "distortion_profile": "low-dispersion edge compression 0.8%",
        },
        "dof_spec": DomainDofSpec(
            focus_style="Wide action depth",
            aperture_t_stop=4.0,
            focal_length_mm=35,
            iris_geometry="octagonal iris",
            depth_character="fast focus pull",
            description="Wide action depth (T4.0, 35mm, octagonal iris, fast focus pull)",
        ),
        "lut_spec": DomainLutSpec(
            lut_name="High-contrast Fuji Eterna dynamic",
            film_emulation="fuji_eterna_dynamic",
            grid_size=33,
            format=".cube",
            cube_filename="fuji_eterna_dynamic_33x33.cube",
            description="High-contrast Fuji Eterna dynamic 33x33 .cube",
        ),
    },
    "tech_hardware": {
        "keywords": [
            "semiconductor", "semiconductors", "smartphone", "smartphones", "laptop", "laptops", "cnc aluminum",
            "aluminum", "optics", "wearables", "wearable", "hardware", "chip", "silicon", "circuit", "processor",
            "device", "gadget", "anodized", "microchip", "chassis", "motherboard", "cleanroom", "quantum",
            "nanoscale", "etching", "wafer", "pcb", "transistor", "fabrication"
        ],
        "default_camera": "CNC Motion Control Arm with 85mm Macro Prime and laser-guided rack focus",
        "camera_rigs": [
            "CNC Motion Control Arm with 85mm Macro Prime and laser-guided rack focus",
            "Telecentric 100mm Inspection Rig with zero optical distortion",
        ],
        "default_focal_length": 85,
        "default_lighting": "Cleanroom 5000K pure white illumination with razor-thin linear specular highlights",
        "default_character": {
            "name": "Cleanroom Nanotech Systems Engineer",
            "silhouette": "Methodical ergonomic posture inside sterile cleanroom envelope",
            "wardrobe_polarity": "Cleanroom white Gore-Tex antistatic suit with matte sapphire visor",
            "movement_signature": "Micrometric, steady-handed vacuum wand positioning with sub-millimeter precision",
        },
        "default_invariants": [
            "Silicon wafer mirror finish reflects sterile yellow lithography lighting",
            "CNC unibody chamfered edges retain micron-level geometric tolerance"
        ],
        "default_foley": [
            "Precision magnetic latch click",
            "Anodized aluminum bevel contact",
            "Subtle ultrasonic cleanroom hum",
            "Haptic motor vibration pulse"
        ],
        "default_bpm": 110,
        "default_key": "D Minor",
        "default_bgm_genre": "Minimalist Glitch & Micro-Acoustic Electronic Pulse",
        "color_palette": ["#030712", "#38BDF8", "#94A3B8", "#F8FAFC"],
        "regime": RegimeType.REGIME_2_KINETIC,
        "color_look_preset": ColorLookPreset.REC709_NEUTRAL,
        "speed_ramp_mode": SpeedRampMode.CONSTANT_REALTIME,
        "default_shutter_angle": 180.0,
        "default_stem_levels": {
            "dialogue": {"gain_db": 0.0, "target_lufs": -18.0},
            "foley": {"gain_db": 0.5, "target_lufs": -20.0},
            "ambience": {"gain_db": -4.0, "target_lufs": -26.0},
            "music": {"gain_db": -2.0, "target_lufs": -18.0},
        },
        "optical_lens": {
            "sensor_format": SensorFormat.FULL_FRAME,
            "anamorphic_squeeze": 1.0,
            "focal_length_mm": 85,
            "aperture_t_stop": 2.8,
            "lens_series": "Leitz Prime Apochromatic Macro Rig",
            "bokeh_characteristic": "razor-sharp clean telecentric falloff",
            "chromatic_aberration": "zero chromatic fringing under lithography lighting",
            "distortion_profile": "zero geometric distortion 0.05%",
        },
        "dof_spec": DomainDofSpec(
            focus_style="Cleanroom macro isolation",
            aperture_t_stop=2.0,
            focal_length_mm=90,
            iris_geometry="nonagonal iris",
            depth_character="tight CoC",
            description="Cleanroom macro isolation (T2.0, 90mm, nonagonal iris, tight CoC)",
        ),
        "lut_spec": DomainLutSpec(
            lut_name="Neutral surgical Rec.709 cold precision",
            film_emulation="rec709_cold_precision",
            grid_size=33,
            format=".cube",
            cube_filename="rec709_cold_precision_33x33.cube",
            description="Neutral surgical Rec.709 cold precision 33x33 .cube",
        ),
    },
    "architectural_sanctuary": {
        "keywords": [
            "architecture", "interior", "furniture", "brutalist", "home", "pavilion", "sanctuary",
            "building", "concrete", "travertine", "limestone", "space", "facade", "gallery", "atrium",
            "minimalist living", "structure", "courtyard", "zen", "residence", "sculpture"
        ],
        "default_camera": "24mm Tilt-Shift Prime on heavy hydraulic dolly with perspective control",
        "camera_rigs": [
            "24mm Tilt-Shift Prime on heavy hydraulic dolly with perspective control",
            "Slow Motion 35mm Dolly along central reflecting pool",
        ],
        "default_focal_length": 24,
        "default_lighting": "Low-angle golden hour sunlight casting geometric window shadows through dust motes",
        "default_character": {
            "name": "Resident Spatial Architect / Meditator",
            "silhouette": "Serene contemplative silhouette framed by monumental spatial geometry",
            "wardrobe_polarity": "Monochrome architectural linen tunic in warm ecru and charcoal",
            "movement_signature": "Calm, deliberate pacing along cardinal spatial axes",
        },
        "default_invariants": [
            "Monolithic board-formed concrete walls remain immovable and textured",
            "Travertine stone floor slabs maintain continuous geometric perspective"
        ],
        "default_foley": [
            "Acoustic reverberation in tall stone hall",
            "Subtle distant wind through bamboo atrium",
            "Soft leather creak on timber seat",
            "Gentle water fountain trickle"
        ],
        "default_bpm": 60,
        "default_key": "G Major",
        "default_bgm_genre": "Neo-Classical Piano & Spatial Drone Sanctuary",
        "color_palette": ["#1C1917", "#78716C", "#D6D3D1", "#E7E5E4"],
        "regime": RegimeType.REGIME_1_ATMOSPHERIC,
        "color_look_preset": ColorLookPreset.REC709_NEUTRAL,
        "speed_ramp_mode": SpeedRampMode.CONSTANT_REALTIME,
        "default_shutter_angle": 180.0,
        "default_stem_levels": {
            "dialogue": {"gain_db": 0.0, "target_lufs": -18.0},
            "foley": {"gain_db": -2.0, "target_lufs": -24.0},
            "ambience": {"gain_db": -1.0, "target_lufs": -22.0},
            "music": {"gain_db": -2.0, "target_lufs": -18.0},
        },
        "optical_lens": {
            "sensor_format": SensorFormat.ARRI_LF,
            "anamorphic_squeeze": 1.0,
            "focal_length_mm": 24,
            "aperture_t_stop": 4.0,
            "lens_series": "ARRI Signature Prime Tilt-Shift Perspective Rig",
            "bokeh_characteristic": "pristine planar depth with zero field curvature",
            "chromatic_aberration": "zero-dispersion apochromatic glass",
            "distortion_profile": "perspective-corrected rectilinear 0.1%",
        },
        "dof_spec": DomainDofSpec(
            focus_style="Panoramic deep focus",
            aperture_t_stop=8.0,
            focal_length_mm=18,
            iris_geometry="circular iris",
            depth_character="infinite far limit",
            description="Panoramic deep focus (T8.0, 18mm, circular iris, infinite far limit)",
        ),
        "lut_spec": DomainLutSpec(
            lut_name="Verdant warm daylight organic",
            film_emulation="verdant_warm_daylight",
            grid_size=33,
            format=".cube",
            cube_filename="verdant_warm_daylight_33x33.cube",
            description="Verdant warm daylight organic 33x33 .cube",
        ),
    },
}


def classify_brief_domain(brief_text: str) -> str:
    """Classifies a user creative brief into one of 6 commercial domain archetypes."""
    clean_text = brief_text.lower()
    scores: Dict[str, int] = {}

    for domain in DOMAIN_PRIORITY:
        data = DOMAIN_ARCHETYPES[domain]
        count = 0
        for kw in data["keywords"]:
            pattern = r"\b" + re.escape(kw) + r"\b"
            matches = re.findall(pattern, clean_text)
            count += len(matches)
        scores[domain] = count

    max_score = max(scores.values()) if scores else 0
    if max_score == 0:
        return "architectural_sanctuary"

    for domain in DOMAIN_PRIORITY:
        if scores.get(domain, 0) == max_score:
            return domain

    return "architectural_sanctuary"


def get_domain_color_look(domain: str) -> ColorLookSpec:
    """Retrieves the deterministically mapped ASC CDL color look spec for a commercial domain archetype."""
    archetype = DOMAIN_ARCHETYPES.get(domain, DOMAIN_ARCHETYPES["architectural_sanctuary"])
    preset = archetype.get("color_look_preset", ColorLookPreset.REC709_NEUTRAL)
    return get_preset_color_look(preset)


def get_domain_speed_ramp(domain: str) -> SpeedRampCurveSpec:
    """Retrieves the deterministically mapped speed ramp curve spec for a commercial domain archetype."""
    archetype = DOMAIN_ARCHETYPES.get(domain, DOMAIN_ARCHETYPES["architectural_sanctuary"])
    mode = archetype.get("speed_ramp_mode", SpeedRampMode.CONSTANT_REALTIME)
    shutter = archetype.get("default_shutter_angle", 180.0)
    return synthesize_speed_ramp_curve(mode=mode, shutter_angle_deg=shutter)


def get_domain_audio_mixer(domain: str) -> AudioStemMixerSpec:
    """Retrieves the calibrated 4-stem post-production audio mixer for a commercial domain archetype."""
    archetype = DOMAIN_ARCHETYPES.get(domain, DOMAIN_ARCHETYPES["architectural_sanctuary"])
    stem_levels = archetype.get("default_stem_levels", {})

    channels = {
        "dialogue": StemChannelStrip(
            stem=StemType.DIALOGUE,
            label="Dialogue",
            gain_db=stem_levels.get("dialogue", {}).get("gain_db", 0.0),
            pan=0.0,
            target_lufs=stem_levels.get("dialogue", {}).get("target_lufs", -18.0),
        ),
        "foley": StemChannelStrip(
            stem=StemType.FOLEY,
            label="Foley / SFX",
            gain_db=stem_levels.get("foley", {}).get("gain_db", 0.0),
            pan=0.0,
            target_lufs=stem_levels.get("foley", {}).get("target_lufs", -20.0),
        ),
        "ambience": StemChannelStrip(
            stem=StemType.AMBIENCE,
            label="Room Ambience",
            gain_db=stem_levels.get("ambience", {}).get("gain_db", -3.0),
            pan=0.0,
            target_lufs=stem_levels.get("ambience", {}).get("target_lufs", -24.0),
        ),
        "music": StemChannelStrip(
            stem=StemType.MUSIC,
            label="BGM Score",
            gain_db=stem_levels.get("music", {}).get("gain_db", -2.0),
            pan=0.0,
            target_lufs=stem_levels.get("music", {}).get("target_lufs", -18.0),
        ),
    }
    return AudioStemMixerSpec(
        master_gain_db=0.0,
        master_lufs_target=-23.0,
        channels=channels,
    )


def get_domain_optical_lens(domain: str) -> OpticalLensSpec:
    """Retrieves the calibrated optical lens & sensor framing spec for a commercial domain archetype."""
    archetype = DOMAIN_ARCHETYPES.get(domain, DOMAIN_ARCHETYPES["architectural_sanctuary"])
    lens_data = archetype.get("optical_lens", {})
    if isinstance(lens_data, OpticalLensSpec):
        return lens_data.model_copy(deep=True)

    sensor = lens_data.get("sensor_format", SensorFormat.FULL_FRAME)
    squeeze = lens_data.get("anamorphic_squeeze", 1.0)
    focal = lens_data.get("focal_length_mm", archetype.get("default_focal_length", 35))
    aperture = lens_data.get("aperture_t_stop", 2.8)
    series = lens_data.get("lens_series", "Cooke S4/i Prime")
    bokeh = lens_data.get("bokeh_characteristic", "circular 9-blade buttery falloff")
    ca = lens_data.get("chromatic_aberration", "zero-dispersion apochromatic")
    dist = lens_data.get("distortion_profile", "barrel 0.2% edge compression")

    h_fov, v_fov = calculate_sensor_fov(sensor, focal, squeeze)
    hyper = calculate_hyperfocal_distance(focal, aperture)

    return OpticalLensSpec(
        sensor_format=sensor,
        anamorphic_squeeze=squeeze,
        focal_length_mm=focal,
        aperture_t_stop=aperture,
        lens_series=series,
        bokeh_characteristic=bokeh,
        chromatic_aberration=ca,
        distortion_profile=dist,
        horizontal_fov_deg=h_fov,
        vertical_fov_deg=v_fov,
        hyperfocal_distance_m=hyper,
    )


def get_domain_virtual_production(domain: str) -> VirtualProductionStageSpec:
    """Retrieves the virtual production LED volume stage spec for a commercial domain archetype."""
    archetype = DOMAIN_ARCHETYPES.get(domain, DOMAIN_ARCHETYPES["architectural_sanctuary"])
    vp_data = archetype.get("virtual_production")
    if isinstance(vp_data, VirtualProductionStageSpec):
        return vp_data.model_copy(deep=True)

    stage_name_map = {
        "automotive_robotics": "StageCraft Volume Apex (Automotive Dynamic)",
        "culinary_asmr": "Micro-Acoustic Tabletop Volume Beta",
        "luxury_fashion": "High-CRI Runway Prism Volume Gamma",
        "kinetic_action": "Deep Horseshoe High-Velocity Volume Delta",
        "tech_hardware": "Cleanroom Micron LED Chamber Epsilon",
        "architectural_sanctuary": "Panoramic 180 Cyclorama Volume Zeta",
    }
    stage_name = stage_name_map.get(domain, "StageCraft LED Volume Alpha")
    return synthesize_default_vp_stage(stage_name=stage_name)


def get_domain_moco_rig(domain: str) -> MocoRigSpec:
    """Retrieves the calibrated 6-DOF robotic motion control rig for a commercial domain archetype (PM-FEAT-009)."""
    archetype = DOMAIN_ARCHETYPES.get(domain, DOMAIN_ARCHETYPES["architectural_sanctuary"])
    moco_data = archetype.get("moco_rig")
    if isinstance(moco_data, MocoRigSpec):
        return moco_data.model_copy(deep=True)

    rig_map = {
        "automotive_robotics": (MotionControlRigType.RUSSIAN_ARM, 12.0, 8.5),
        "culinary_asmr": (MotionControlRigType.BOLT_CINEBOT, 3.0, 2.5),
        "luxury_fashion": (MotionControlRigType.TECHNOCRANE, 8.0, 3.5),
        "kinetic_action": (MotionControlRigType.CABLECAM, 15.0, 10.0),
        "tech_hardware": (MotionControlRigType.BOLT_CINEBOT, 4.0, 3.0),
        "architectural_sanctuary": (MotionControlRigType.MOTORIZED_DOLLY, 6.0, 1.5),
    }
    rig_type, track_len, max_vel = rig_map.get(domain, (MotionControlRigType.BOLT_CINEBOT, 6.0, 4.5))
    return synthesize_default_moco_rig(rig_type=rig_type, track_length_meters=track_len, max_velocity_mps=max_vel)


def get_domain_lighting_rig(domain: str) -> LightingRigSpec:
    """Retrieves the calibrated studio lighting rig for a commercial domain archetype (PM-FEAT-010)."""
    archetype = DOMAIN_ARCHETYPES.get(domain, DOMAIN_ARCHETYPES["architectural_sanctuary"])
    lighting_data = archetype.get("lighting_rig")
    if isinstance(lighting_data, LightingRigSpec):
        return lighting_data.model_copy(deep=True)

    return synthesize_default_lighting_rig(style=domain)


def get_domain_dof_spec(archetype: Any) -> DomainDofSpec:
    """Retrieves the calibrated depth of field, aperture T-stop, and optical focus spec for a commercial domain archetype (PM-FEAT-011)."""
    domain_key = "architectural_sanctuary"
    if isinstance(archetype, str):
        domain_key = archetype
    elif isinstance(archetype, dict):
        if "dof_spec" in archetype:
            spec = archetype["dof_spec"]
            if isinstance(spec, DomainDofSpec):
                return spec.model_copy(deep=True)
            if isinstance(spec, dict):
                return DomainDofSpec(**spec)
        for k, v in DOMAIN_ARCHETYPES.items():
            if v is archetype:
                domain_key = k
                break
    elif hasattr(archetype, "master_dof_spec") and getattr(archetype, "master_dof_spec"):
        return getattr(archetype, "master_dof_spec")
    elif hasattr(archetype, "domain_archetype") and getattr(archetype, "domain_archetype"):
        domain_key = getattr(archetype, "domain_archetype")

    arch_data = DOMAIN_ARCHETYPES.get(domain_key, DOMAIN_ARCHETYPES["architectural_sanctuary"])
    dof_data = arch_data.get("dof_spec")
    if isinstance(dof_data, DomainDofSpec):
        return dof_data.model_copy(deep=True)
    if isinstance(dof_data, dict):
        return DomainDofSpec(**dof_data)
    return DomainDofSpec(
        focus_style="Panoramic deep focus",
        aperture_t_stop=8.0,
        focal_length_mm=18,
        iris_geometry="circular iris",
        depth_character="infinite far limit",
        description="Panoramic deep focus (T8.0, 18mm, circular iris, infinite far limit)",
    )


def get_domain_lut_spec(archetype: Any) -> DomainLutSpec:
    """Retrieves the calibrated 3D LUT color science and film stock emulation spec for a commercial domain archetype (PM-FEAT-012)."""
    domain_key = "architectural_sanctuary"
    if isinstance(archetype, str):
        domain_key = archetype
    elif isinstance(archetype, dict):
        if "lut_spec" in archetype:
            spec = archetype["lut_spec"]
            if isinstance(spec, DomainLutSpec):
                return spec.model_copy(deep=True)
            if isinstance(spec, dict):
                return DomainLutSpec(**spec)
        for k, v in DOMAIN_ARCHETYPES.items():
            if v is archetype:
                domain_key = k
                break
    elif hasattr(archetype, "master_lut_spec") and getattr(archetype, "master_lut_spec"):
        return getattr(archetype, "master_lut_spec")
    elif hasattr(archetype, "domain_archetype") and getattr(archetype, "domain_archetype"):
        domain_key = getattr(archetype, "domain_archetype")

    arch_data = DOMAIN_ARCHETYPES.get(domain_key, DOMAIN_ARCHETYPES["architectural_sanctuary"])
    lut_data = arch_data.get("lut_spec")
    if isinstance(lut_data, DomainLutSpec):
        return lut_data.model_copy(deep=True)
    if isinstance(lut_data, dict):
        return DomainLutSpec(**lut_data)
    return DomainLutSpec(
        lut_name="Verdant warm daylight organic",
        film_emulation="verdant_warm_daylight",
        grid_size=33,
        format=".cube",
        cube_filename="verdant_warm_daylight_33x33.cube",
        description="Verdant warm daylight organic 33x33 .cube",
    )


def _default_domain_passes(domain_key: str) -> List[VfxLayerChannelSpec]:
    near = 0.05 if ("culinary" in domain_key or "hardware" in domain_key) else 0.1
    far = 10.0 if ("culinary" in domain_key or "hardware" in domain_key) else (200.0 if ("kinetic" in domain_key or "automotive" in domain_key) else 50.0)
    return [
        VfxLayerChannelSpec(pass_type=VfxRenderPassType.BEAUTY_RGB, channel_name="beauty.RGB", bit_depth="16-bit half float", color_space="ACEScg", description="Final beauty combined render"),
        VfxLayerChannelSpec(pass_type=VfxRenderPassType.DIFFUSE_ALBEDO, channel_name="diffuse.RGB", bit_depth="16-bit half float", color_space="ACEScg", description="Diffuse albedo direct + indirect bounce"),
        VfxLayerChannelSpec(pass_type=VfxRenderPassType.SPECULAR_ROUGHNESS, channel_name="specular.RGB", bit_depth="16-bit half float", color_space="ACEScg", description="Specular gloss reflections and highlights"),
        VfxLayerChannelSpec(pass_type=VfxRenderPassType.SURFACE_NORMALS, channel_name="normals.RGB", bit_depth="16-bit half float", color_space="Raw", description="World space surface normal vectors"),
        VfxLayerChannelSpec(pass_type=VfxRenderPassType.DEPTH_Z_PASS, channel_name="depth.Z", bit_depth="32-bit full float", color_space="Raw", description=f"Linear depth distance ({near}m to {far}m)"),
        VfxLayerChannelSpec(pass_type=VfxRenderPassType.AMBIENT_OCCLUSION, channel_name="ao.RGB", bit_depth="16-bit half float", color_space="Linear sRGB", description="Contact shadow ambient occlusion"),
        VfxLayerChannelSpec(pass_type=VfxRenderPassType.CRYPTOMATTE_OBJECT, channel_name="crypto_object.RGBA", bit_depth="32-bit full float", color_space="Raw", description="Cryptomatte 32-bit object identifier hashes"),
    ]


def get_domain_spatial_audio_spec(archetype: Any) -> SpatialAudioSoundfieldSpec:
    """Retrieves the calibrated 3D spatial audio soundfield and acoustic RIR spec for a commercial domain archetype (PM-FEAT-013)."""
    domain_key = "architectural_sanctuary"
    if isinstance(archetype, str):
        domain_key = archetype
    elif isinstance(archetype, dict):
        if "spatial_audio" in archetype:
            spec = archetype["spatial_audio"]
            if isinstance(spec, SpatialAudioSoundfieldSpec):
                return spec.model_copy(deep=True)
            if isinstance(spec, dict):
                return SpatialAudioSoundfieldSpec(**spec)
        for k, v in DOMAIN_ARCHETYPES.items():
            if v is archetype:
                domain_key = k
                break
    elif hasattr(archetype, "master_spatial_audio") and getattr(archetype, "master_spatial_audio"):
        return getattr(archetype, "master_spatial_audio")
    elif hasattr(archetype, "domain_archetype") and getattr(archetype, "domain_archetype"):
        domain_key = getattr(archetype, "domain_archetype")

    arch_data = DOMAIN_ARCHETYPES.get(domain_key, DOMAIN_ARCHETYPES["architectural_sanctuary"])
    sa_data = arch_data.get("spatial_audio")
    if isinstance(sa_data, SpatialAudioSoundfieldSpec):
        return sa_data.model_copy(deep=True)
    if isinstance(sa_data, dict):
        return SpatialAudioSoundfieldSpec(**sa_data)

    if domain_key == "automotive_robotics":
        return SpatialAudioSoundfieldSpec(
            bed_format=DolbyAtmosBedFormat.BED_7_1_4,
            room_acoustics=AcousticRoomImpulseResponse(
                room_name="High-Speed Raceway Acoustic Envelope",
                room_volume_m3=250.0,
                surface_area_m2=280.0,
                rt60_decay_sec=0.38,
                early_reflections_ms=12.0,
                air_absorption_hf_db_per_m=0.025,
                wall_material=AcousticMaterialType.AUTOMOTIVE_CABIN,
            ),
            audio_objects=[
                SpatialAudioObjectSpec(
                    object_id="obj_chassis_torque_rumble",
                    stem_type=StemType.FOLEY,
                    label="Chassis torque and tire friction rumble",
                    initial_position=SpatialCoordinate3D(azimuth_deg=0.0, elevation_deg=-15.0, distance_meters=2.0, spread_deg=45.0),
                    lfe_send_db=0.0,
                ),
                SpatialAudioObjectSpec(
                    object_id="obj_pursuit_drone_flyby",
                    stem_type=StemType.FOLEY,
                    label="Pursuit chase drone lateral flyby",
                    initial_position=SpatialCoordinate3D(azimuth_deg=-60.0, elevation_deg=15.0, distance_meters=4.5, spread_deg=20.0),
                    trajectory_waypoints=[
                        SpatialCoordinate3D(azimuth_deg=-60.0, elevation_deg=15.0, distance_meters=4.5),
                        SpatialCoordinate3D(azimuth_deg=0.0, elevation_deg=25.0, distance_meters=2.0),
                        SpatialCoordinate3D(azimuth_deg=75.0, elevation_deg=10.0, distance_meters=6.0),
                    ],
                    lfe_send_db=-18.0,
                ),
            ],
            binaural_rendering_enabled=True,
        )
    elif domain_key == "culinary_asmr":
        return SpatialAudioSoundfieldSpec(
            bed_format=DolbyAtmosBedFormat.BINAURAL_HRTF,
            room_acoustics=AcousticRoomImpulseResponse(
                room_name="Intimate Micro-Acoustic Kitchen Stage",
                room_volume_m3=45.0,
                surface_area_m2=65.0,
                rt60_decay_sec=0.25,
                early_reflections_ms=6.5,
                air_absorption_hf_db_per_m=0.015,
                wall_material=AcousticMaterialType.MARBLE_GLASS,
            ),
            audio_objects=[
                SpatialAudioObjectSpec(
                    object_id="obj_knife_slice_contact",
                    stem_type=StemType.FOLEY,
                    label="Artisanal knife blade slice contact",
                    initial_position=SpatialCoordinate3D(azimuth_deg=-10.0, elevation_deg=-5.0, distance_meters=0.35, spread_deg=15.0),
                    lfe_send_db=-24.0,
                ),
                SpatialAudioObjectSpec(
                    object_id="obj_cast_iron_sizzle",
                    stem_type=StemType.FOLEY,
                    label="Cast iron surface butter sizzle",
                    initial_position=SpatialCoordinate3D(azimuth_deg=20.0, elevation_deg=-10.0, distance_meters=0.5, spread_deg=45.0),
                    lfe_send_db=-12.0,
                ),
            ],
            binaural_rendering_enabled=True,
        )
    elif domain_key == "luxury_fashion":
        return SpatialAudioSoundfieldSpec(
            bed_format=DolbyAtmosBedFormat.BED_7_1_4,
            room_acoustics=AcousticRoomImpulseResponse(
                room_name="Parisian Marble Flagship Runway Hall",
                room_volume_m3=1200.0,
                surface_area_m2=850.0,
                rt60_decay_sec=1.45,
                early_reflections_ms=28.0,
                air_absorption_hf_db_per_m=0.02,
                wall_material=AcousticMaterialType.FURNISHED_RESIDENTIAL,
            ),
            audio_objects=[
                SpatialAudioObjectSpec(
                    object_id="obj_couture_silk_rustle",
                    stem_type=StemType.FOLEY,
                    label="Couture silk gown dynamic rustle",
                    initial_position=SpatialCoordinate3D(azimuth_deg=15.0, elevation_deg=0.0, distance_meters=1.8, spread_deg=30.0),
                    lfe_send_db=-20.0,
                ),
                SpatialAudioObjectSpec(
                    object_id="obj_runway_sub_bass",
                    stem_type=StemType.MUSIC,
                    label="Catwalk runway deep sub bass pulse",
                    initial_position=SpatialCoordinate3D(azimuth_deg=0.0, elevation_deg=10.0, distance_meters=12.0, spread_deg=180.0),
                    lfe_send_db=-3.0,
                ),
            ],
            binaural_rendering_enabled=True,
        )
    elif domain_key == "kinetic_action":
        return SpatialAudioSoundfieldSpec(
            bed_format=DolbyAtmosBedFormat.AMBISONIC_HOA_3RD_ORDER,
            room_acoustics=AcousticRoomImpulseResponse(
                room_name="Monumental Concrete Wind & Canyon Arena",
                room_volume_m3=8000.0,
                surface_area_m2=3200.0,
                rt60_decay_sec=2.10,
                early_reflections_ms=35.0,
                air_absorption_hf_db_per_m=0.03,
                wall_material=AcousticMaterialType.HARDWOOD_CONCRETE,
            ),
            audio_objects=[
                SpatialAudioObjectSpec(
                    object_id="obj_kinetic_impact_shockwave",
                    stem_type=StemType.FOLEY,
                    label="Kinetic impact compression shockwave",
                    initial_position=SpatialCoordinate3D(azimuth_deg=-35.0, elevation_deg=-10.0, distance_meters=3.0, spread_deg=60.0),
                    lfe_send_db=0.0,
                ),
                SpatialAudioObjectSpec(
                    object_id="obj_ricochet_debris_whizz",
                    stem_type=StemType.FOLEY,
                    label="High-velocity ricochet debris whizz",
                    initial_position=SpatialCoordinate3D(azimuth_deg=110.0, elevation_deg=25.0, distance_meters=1.2, spread_deg=15.0),
                    lfe_send_db=-18.0,
                ),
            ],
            binaural_rendering_enabled=True,
        )
    elif domain_key == "tech_hardware":
        return SpatialAudioSoundfieldSpec(
            bed_format=DolbyAtmosBedFormat.BED_5_1_2,
            room_acoustics=AcousticRoomImpulseResponse(
                room_name="ISO-5 Acoustic-Damped Cleanroom Chamber",
                room_volume_m3=85.0,
                surface_area_m2=110.0,
                rt60_decay_sec=0.18,
                early_reflections_ms=8.0,
                air_absorption_hf_db_per_m=0.01,
                wall_material=AcousticMaterialType.STUDIO_ACOUSTIC_FOAM,
            ),
            audio_objects=[
                SpatialAudioObjectSpec(
                    object_id="obj_precision_haptic_click",
                    stem_type=StemType.FOLEY,
                    label="Sub-millimeter precision haptic click",
                    initial_position=SpatialCoordinate3D(azimuth_deg=0.0, elevation_deg=-5.0, distance_meters=0.45, spread_deg=10.0),
                    lfe_send_db=-24.0,
                ),
                SpatialAudioObjectSpec(
                    object_id="obj_cleanroom_laminar_fan",
                    stem_type=StemType.AMBIENCE,
                    label="Sterile cleanroom laminar flow purr",
                    initial_position=SpatialCoordinate3D(azimuth_deg=45.0, elevation_deg=30.0, distance_meters=2.5, spread_deg=90.0),
                    lfe_send_db=-12.0,
                ),
            ],
            binaural_rendering_enabled=True,
        )
    else:  # architectural_sanctuary
        return SpatialAudioSoundfieldSpec(
            bed_format=DolbyAtmosBedFormat.AMBISONIC_B_FORMAT,
            room_acoustics=AcousticRoomImpulseResponse(
                room_name="Monolithic Stone Sanctuary & Atrium",
                room_volume_m3=3500.0,
                surface_area_m2=1900.0,
                rt60_decay_sec=1.85,
                early_reflections_ms=32.0,
                air_absorption_hf_db_per_m=0.02,
                wall_material=AcousticMaterialType.HARDWOOD_CONCRETE,
            ),
            audio_objects=[
                SpatialAudioObjectSpec(
                    object_id="obj_reflecting_pool_trickle",
                    stem_type=StemType.AMBIENCE,
                    label="Reflecting pool water droplet trickle",
                    initial_position=SpatialCoordinate3D(azimuth_deg=-40.0, elevation_deg=-15.0, distance_meters=6.0, spread_deg=45.0),
                    lfe_send_db=-24.0,
                ),
                SpatialAudioObjectSpec(
                    object_id="obj_cathedral_stone_reverb",
                    stem_type=StemType.FOLEY,
                    label="Acoustic heel contact stone reverberation",
                    initial_position=SpatialCoordinate3D(azimuth_deg=60.0, elevation_deg=0.0, distance_meters=4.0, spread_deg=90.0),
                    lfe_send_db=-18.0,
                ),
            ],
            binaural_rendering_enabled=True,
        )


def get_domain_vfx_manifest(archetype: Any) -> VfxCompositingManifestSpec:
    """Retrieves the calibrated multi-pass VFX compositing and OpenEXR manifest for a commercial domain archetype (PM-FEAT-014)."""
    domain_key = "architectural_sanctuary"
    if isinstance(archetype, str):
        domain_key = archetype
    elif isinstance(archetype, dict):
        if "vfx_manifest" in archetype:
            spec = archetype["vfx_manifest"]
            if isinstance(spec, VfxCompositingManifestSpec):
                return spec.model_copy(deep=True)
            if isinstance(spec, dict):
                return VfxCompositingManifestSpec(**spec)
        for k, v in DOMAIN_ARCHETYPES.items():
            if v is archetype:
                domain_key = k
                break
    elif hasattr(archetype, "master_vfx_manifest") and getattr(archetype, "master_vfx_manifest"):
        return getattr(archetype, "master_vfx_manifest")
    elif hasattr(archetype, "domain_archetype") and getattr(archetype, "domain_archetype"):
        domain_key = getattr(archetype, "domain_archetype")

    arch_data = DOMAIN_ARCHETYPES.get(domain_key, DOMAIN_ARCHETYPES["architectural_sanctuary"])
    vfx_data = arch_data.get("vfx_manifest")
    if isinstance(vfx_data, VfxCompositingManifestSpec):
        return vfx_data.model_copy(deep=True)
    if isinstance(vfx_data, dict):
        return VfxCompositingManifestSpec(**vfx_data)

    passes = _default_domain_passes(domain_key)
    if domain_key == "automotive_robotics":
        crypto = generate_cryptomatte_manifest(
            objects=["supercar_chassis", "carbon_fiber_diffuser", "pursuit_drone", "tarmac_surface"],
            materials=["clearcoat_metallic_lacquer", "carbon_fiber_twill", "rubber_tread", "asphalt_slick"],
        )
        return VfxCompositingManifestSpec(
            manifest_version="2.0",
            openexr_compression="ZIP_SCANLINE",
            passes=passes,
            cryptomatte=crypto,
            depth_near_plane_m=0.2,
            depth_far_plane_m=150.0,
            reconstruction_formula="(Diffuse * AO) + Specular + Emissive",
        )
    elif domain_key == "culinary_asmr":
        crypto = generate_cryptomatte_manifest(
            objects=["santoku_blade", "cutting_board_endgrain", "salmon_fillet", "cast_iron_pan"],
            materials=["stainless_steel_damascus", "wood_walnut_oiled", "flesh_translucent", "seasoned_cast_iron"],
        )
        return VfxCompositingManifestSpec(
            manifest_version="2.0",
            openexr_compression="PIZ",
            passes=passes,
            cryptomatte=crypto,
            depth_near_plane_m=0.05,
            depth_far_plane_m=5.0,
            reconstruction_formula="(Diffuse * AO) + Specular",
        )
    elif domain_key == "luxury_fashion":
        crypto = generate_cryptomatte_manifest(
            objects=["couture_gown", "hero_model_silhouette", "catwalk_mirror_floor", "spotlight_housing"],
            materials=["silk_charmeuse_specular", "gold_lame_metallic", "lacquered_floor_reflective", "velvet_absorptive"],
        )
        return VfxCompositingManifestSpec(
            manifest_version="2.0",
            openexr_compression="ZIP_SCANLINE",
            passes=passes,
            cryptomatte=crypto,
            depth_near_plane_m=0.5,
            depth_far_plane_m=40.0,
            reconstruction_formula="(Diffuse * AO) + Specular + Emissive",
        )
    elif domain_key == "kinetic_action":
        crypto = generate_cryptomatte_manifest(
            objects=["kinetic_athlete", "reinforced_concrete_pillar", "shattered_debris", "dust_cloud_volumetric"],
            materials=["matte_performance_fabric", "concrete_fractured", "steel_rebar", "micro_dust_particulate"],
        )
        return VfxCompositingManifestSpec(
            manifest_version="2.0",
            openexr_compression="DWAA",
            passes=passes,
            cryptomatte=crypto,
            depth_near_plane_m=0.1,
            depth_far_plane_m=200.0,
            reconstruction_formula="(Diffuse * AO) + Specular + Emissive",
        )
    elif domain_key == "tech_hardware":
        crypto = generate_cryptomatte_manifest(
            objects=["chassis_unibody", "gorilla_glass_display", "silicon_die", "copper_heatpipe"],
            materials=["anodized_aluminum_matte", "anti_glare_glass", "silicon_lithography", "pure_copper_specular"],
        )
        return VfxCompositingManifestSpec(
            manifest_version="2.0",
            openexr_compression="ZIP_SCANLINE",
            passes=passes,
            cryptomatte=crypto,
            depth_near_plane_m=0.02,
            depth_far_plane_m=10.0,
            reconstruction_formula="(Diffuse * AO) + Specular + Emissive",
        )
    else:  # architectural_sanctuary
        crypto = generate_cryptomatte_manifest(
            objects=["cantilever_roof", "reflecting_pool_basin", "monolithic_concrete_wall", "travertine_floor"],
            materials=["board_formed_concrete", "still_water_fresnel", "travertine_limestone", "low_iron_glass"],
        )
        return VfxCompositingManifestSpec(
            manifest_version="2.0",
            openexr_compression="ZIP_SCANLINE",
            passes=passes,
            cryptomatte=crypto,
            depth_near_plane_m=0.2,
            depth_far_plane_m=80.0,
            reconstruction_formula="(Diffuse * AO) + Specular",
        )


def get_domain_hdr_spec(domain: Union[DomainArchetype, str]) -> HdrMetadataSpec:
    """Calibrate realistic mastering display, peak nits, MaxCLL, MaxFALL, and tone mapping across all 6 commercial domain archetypes."""
    domain_key = domain.value if hasattr(domain, "value") else str(domain).lower()

    if "automotive" in domain_key:
        return HdrMetadataSpec(
            transfer_function=HdrTransferFunction.SMPTE_ST_2084_PQ,
            mastering_display=HdrMasteringDisplaySpec(
                peak_luminance_nits=1500.0,
                black_level_nits=0.0001,
                color_volume=ColorVolumeGamut.BT_2020,
            ),
            max_cll_nits=1450.0,
            max_fall_nits=520.0,
            tone_mapping=ToneMappingOperator.ACES_SPLINE,
            target_gamut=ColorVolumeGamut.BT_2020,
        )
    elif "culinary" in domain_key:
        return HdrMetadataSpec(
            transfer_function=HdrTransferFunction.ARIB_STD_B67_HLG,
            mastering_display=HdrMasteringDisplaySpec(
                peak_luminance_nits=1000.0,
                black_level_nits=0.0001,
                color_volume=ColorVolumeGamut.BT_2020,
            ),
            max_cll_nits=920.0,
            max_fall_nits=310.0,
            tone_mapping=ToneMappingOperator.REINHARD_EXTENDED,
            target_gamut=ColorVolumeGamut.BT_2020,
        )
    elif "luxury" in domain_key or "fashion" in domain_key:
        return HdrMetadataSpec(
            transfer_function=HdrTransferFunction.SMPTE_ST_2084_PQ,
            mastering_display=HdrMasteringDisplaySpec(
                peak_luminance_nits=1000.0,
                black_level_nits=0.0001,
                color_volume=ColorVolumeGamut.DCI_P3_D65,
            ),
            max_cll_nits=880.0,
            max_fall_nits=280.0,
            tone_mapping=ToneMappingOperator.REINHARD_EXTENDED,
            target_gamut=ColorVolumeGamut.DCI_P3_D65,
        )
    elif "kinetic" in domain_key:
        return HdrMetadataSpec(
            transfer_function=HdrTransferFunction.SMPTE_ST_2084_PQ,
            mastering_display=HdrMasteringDisplaySpec(
                peak_luminance_nits=2000.0,
                black_level_nits=0.0001,
                color_volume=ColorVolumeGamut.BT_2020,
            ),
            max_cll_nits=1950.0,
            max_fall_nits=680.0,
            tone_mapping=ToneMappingOperator.BT_2446_METHOD_A,
            target_gamut=ColorVolumeGamut.BT_2020,
        )
    elif "hardware" in domain_key or "tech" in domain_key:
        return HdrMetadataSpec(
            transfer_function=HdrTransferFunction.SMPTE_ST_2084_PQ,
            mastering_display=HdrMasteringDisplaySpec(
                peak_luminance_nits=1200.0,
                black_level_nits=0.0001,
                color_volume=ColorVolumeGamut.BT_2020,
            ),
            max_cll_nits=1150.0,
            max_fall_nits=420.0,
            tone_mapping=ToneMappingOperator.ACES_SPLINE,
            target_gamut=ColorVolumeGamut.BT_2020,
        )
    else:  # architectural_sanctuary
        return HdrMetadataSpec(
            transfer_function=HdrTransferFunction.SMPTE_ST_2084_PQ,
            mastering_display=HdrMasteringDisplaySpec(
                peak_luminance_nits=1000.0,
                black_level_nits=0.0001,
                color_volume=ColorVolumeGamut.BT_2020,
            ),
            max_cll_nits=980.0,
            max_fall_nits=360.0,
            tone_mapping=ToneMappingOperator.ACES_SPLINE,
            target_gamut=ColorVolumeGamut.BT_2020,
        )


def get_domain_stripboard_spec(
    domain: Union[DomainArchetype, str],
    scenes: Optional[List[ScenePromptSpec]] = None,
) -> MasterStripboardScheduleSpec:
    """Generate calibrated stripboard schedules with strips and DOOD records tailored for each domain."""
    domain_key = domain.value if hasattr(domain, "value") else str(domain).lower()

    if scenes is not None and len(scenes) > 0:
        from types import SimpleNamespace
        temp_obj = SimpleNamespace(
            project_title=f"{domain_key.replace('_', ' ').title()} Production",
            scenes=scenes,
            characters=[],
        )
        return generate_stripboard_schedule(temp_obj)

    clean_domain = domain_key.replace("_", "-")
    preset_key = ARCHETYPE_PRESET_FALLBACKS.get(clean_domain, "ikea-asmr")
    if preset_key in PRESETS:
        preset_bible = PRESETS[preset_key].model_copy(deep=True)
        return generate_stripboard_schedule(preset_bible)

    craft = CraftCameraSpec(
        rig_type="Studio Tripod Prime",
        focal_length_mm=35,
        composition="Wide architectural framing",
        route="Locked-off observational static frame",
        action_anchor="Subject anchor",
        focus_axis="Deep focus",
        tone_rig="Cinematic standard",
    )
    fallback_scenes = [
        ScenePromptSpec(
            scene_index=1,
            scene_title="Initial Establishing Frame",
            timestamp_range="00:00 - 00:05",
            craft_camera=craft,
            omni_prose_prompt=f"EXT. {domain_key.upper()} LOCATION - DAY. The scene opens on an expansive establishing shot.",
            action_beats=["Beat 1: Establishing wide shot", "Beat 2: Core action begins"],
        ),
        ScenePromptSpec(
            scene_index=2,
            scene_title="Kinetic Climax Sequence",
            timestamp_range="00:05 - 00:10",
            craft_camera=craft,
            omni_prose_prompt=f"INT. {domain_key.upper()} STUDIO - NIGHT. Close-up detailed kinetic action unfolds under dynamic lighting.",
            action_beats=["Beat 1: Movement accelerates", "Beat 2: Kinetic climax and hero resolve"],
        ),
    ]
    fallback_bible = MasterProductionBible(
        project_title=f"{domain_key.replace('_', ' ').title()} Master Schedule",
        logline=f"Master production schedule for {domain_key}",
        domain_archetype=domain_key,
        scenes=fallback_scenes,
    )
    return generate_stripboard_schedule(fallback_bible)


def get_domain_film_emulation_spec(domain: Union[DomainArchetype, str]) -> FilmStockSpec:
    """Calibrate physical film stock chemistry, grain, halation, and gate weave across commercial domain archetypes (PM-FEAT-017)."""
    domain_key = domain.value if hasattr(domain, "value") else str(domain).lower()

    if "culinary" in domain_key:
        return FilmStockSpec(
            stock_name="Kodak Vision3 500T",
            stock_code="5219",
            manufacturer=FilmStockManufacturer.KODAK,
            gauge=FilmGaugeFormat.GAUGE_35MM_4PERF,
            iso_rating=500,
            color_temp_k=3200,
            push_pull_stops=0.0,
            grain=GrainPhysicsSpec(
                rms_granularity=4.2,
                grain_size_microns=8.5,
                shadow_grain_weight=1.1,
                midtone_grain_weight=1.4,
                highlight_grain_weight=0.6,
            ),
            halation=HalationPhysicsSpec(
                halation_radius_pixels=6.0,
                halation_intensity=0.40,
                rem_jet_opacity=0.88,
                specular_threshold_nits=350.0,
                chromatic_tint_rgb=[1.0, 0.35, 0.08],
            ),
            gate_weave=GateWeavePhysicsSpec(
                lateral_drift_microns=0.8,
                vertical_judder_microns=0.5,
                registration_pin_type="bell_howell_2709",
                frequency_hz=24.0,
            ),
            description="Kodak Vision3 500T 5219 (35mm 4-perf, warm rich tones, RMS 4.2, subtle amber halation, minimal gate weave 0.8μm)",
        )
    elif "luxury" in domain_key:
        return FilmStockSpec(
            stock_name="Fuji Eterna 500T",
            stock_code="8543",
            manufacturer=FilmStockManufacturer.FUJI,
            gauge=FilmGaugeFormat.GAUGE_35MM_4PERF,
            iso_rating=500,
            color_temp_k=3200,
            push_pull_stops=0.0,
            grain=GrainPhysicsSpec(
                rms_granularity=4.0,
                grain_size_microns=8.0,
                shadow_grain_weight=1.1,
                midtone_grain_weight=1.3,
                highlight_grain_weight=0.7,
            ),
            halation=HalationPhysicsSpec(
                halation_radius_pixels=7.5,
                halation_intensity=0.42,
                rem_jet_opacity=0.82,
                specular_threshold_nits=320.0,
                chromatic_tint_rgb=[0.95, 0.35, 0.15],
            ),
            gate_weave=GateWeavePhysicsSpec(
                lateral_drift_microns=0.6,
                vertical_judder_microns=0.4,
                registration_pin_type="mitchell_dual_pin",
                frequency_hz=24.0,
            ),
            description="Fuji Eterna 500T 8543 (35mm 4-perf, soft pastel desaturation, creamy halation radius 7.5px, smooth gate weave 0.6μm)",
        )
    elif "automotive" in domain_key:
        return FilmStockSpec(
            stock_name="Kodak Vision3 250D",
            stock_code="5207",
            manufacturer=FilmStockManufacturer.KODAK,
            gauge=FilmGaugeFormat.GAUGE_65MM_IMAX,
            iso_rating=250,
            color_temp_k=5500,
            push_pull_stops=0.0,
            grain=GrainPhysicsSpec(
                rms_granularity=2.8,
                grain_size_microns=5.5,
                shadow_grain_weight=0.8,
                midtone_grain_weight=1.1,
                highlight_grain_weight=0.5,
            ),
            halation=HalationPhysicsSpec(
                halation_radius_pixels=4.5,
                halation_intensity=0.30,
                rem_jet_opacity=0.92,
                specular_threshold_nits=420.0,
                chromatic_tint_rgb=[1.0, 0.22, 0.05],
            ),
            gate_weave=GateWeavePhysicsSpec(
                lateral_drift_microns=0.4,
                vertical_judder_microns=0.3,
                registration_pin_type="mitchell_dual_pin",
                frequency_hz=24.0,
            ),
            description="Kodak Vision3 250D 5207 (65mm IMAX, micro-fine grain RMS 2.8, sharp edge registration, gate weave 0.4μm)",
        )
    elif "kinetic" in domain_key:
        return FilmStockSpec(
            stock_name="Kodak Vision3 500T",
            stock_code="5219",
            manufacturer=FilmStockManufacturer.KODAK,
            gauge=FilmGaugeFormat.GAUGE_35MM_2PERF,
            iso_rating=500,
            color_temp_k=3200,
            push_pull_stops=0.0,
            grain=GrainPhysicsSpec(
                rms_granularity=4.8,
                grain_size_microns=9.5,
                shadow_grain_weight=1.3,
                midtone_grain_weight=1.5,
                highlight_grain_weight=0.8,
            ),
            halation=HalationPhysicsSpec(
                halation_radius_pixels=8.0,
                halation_intensity=0.55,
                rem_jet_opacity=0.78,
                specular_threshold_nits=290.0,
                chromatic_tint_rgb=[1.0, 0.25, 0.05],
            ),
            gate_weave=GateWeavePhysicsSpec(
                lateral_drift_microns=1.4,
                vertical_judder_microns=1.0,
                registration_pin_type="bell_howell_2709",
                frequency_hz=24.0,
            ),
            description="Kodak Vision3 500T 5219 (35mm 2-perf Techniscope, gritty punchy grain RMS 4.8, dynamic red halation 8.0px, rapid gate weave 1.4μm)",
        )
    elif "hardware" in domain_key:
        return FilmStockSpec(
            stock_name="Kodak Vision3 50D",
            stock_code="5203",
            manufacturer=FilmStockManufacturer.KODAK,
            gauge=FilmGaugeFormat.GAUGE_35MM_4PERF,
            iso_rating=50,
            color_temp_k=5500,
            push_pull_stops=0.0,
            grain=GrainPhysicsSpec(
                rms_granularity=2.1,
                grain_size_microns=4.2,
                shadow_grain_weight=0.7,
                midtone_grain_weight=1.0,
                highlight_grain_weight=0.4,
            ),
            halation=HalationPhysicsSpec(
                halation_radius_pixels=3.5,
                halation_intensity=0.25,
                rem_jet_opacity=0.95,
                specular_threshold_nits=480.0,
                chromatic_tint_rgb=[1.0, 0.20, 0.05],
            ),
            gate_weave=GateWeavePhysicsSpec(
                lateral_drift_microns=0.3,
                vertical_judder_microns=0.2,
                registration_pin_type="mitchell_dual_pin",
                frequency_hz=24.0,
            ),
            description="Kodak Vision3 50D 5203 (35mm 4-perf, ultra-fine grain RMS 2.1, cleanroom precision, crisp specular preservation, gate weave 0.3μm)",
        )
    elif "architectural" in domain_key:
        return FilmStockSpec(
            stock_name="Kodak Vision3 250D",
            stock_code="5207",
            manufacturer=FilmStockManufacturer.KODAK,
            gauge=FilmGaugeFormat.GAUGE_65MM_IMAX,
            iso_rating=250,
            color_temp_k=5500,
            push_pull_stops=0.0,
            grain=GrainPhysicsSpec(
                rms_granularity=2.6,
                grain_size_microns=5.0,
                shadow_grain_weight=0.8,
                midtone_grain_weight=1.1,
                highlight_grain_weight=0.4,
            ),
            halation=HalationPhysicsSpec(
                halation_radius_pixels=5.0,
                halation_intensity=0.32,
                rem_jet_opacity=0.90,
                specular_threshold_nits=400.0,
                chromatic_tint_rgb=[1.0, 0.25, 0.06],
            ),
            gate_weave=GateWeavePhysicsSpec(
                lateral_drift_microns=0.3,
                vertical_judder_microns=0.2,
                registration_pin_type="mitchell_dual_pin",
                frequency_hz=24.0,
            ),
            description="Kodak Vision3 250D 5207 (65mm IMAX, wide dynamic range, balanced natural halation, rock-solid registration 0.3μm)",
        )
    else:
        return FilmStockSpec(
            stock_name="Kodak Vision3 500T",
            stock_code="5219",
            manufacturer=FilmStockManufacturer.KODAK,
            gauge=FilmGaugeFormat.GAUGE_35MM_4PERF,
            iso_rating=500,
            color_temp_k=3200,
            push_pull_stops=0.0,
            grain=GrainPhysicsSpec(
                rms_granularity=4.2,
                grain_size_microns=8.5,
                shadow_grain_weight=1.1,
                midtone_grain_weight=1.4,
                highlight_grain_weight=0.6,
            ),
            halation=HalationPhysicsSpec(
                halation_radius_pixels=6.5,
                halation_intensity=0.45,
                rem_jet_opacity=0.85,
                specular_threshold_nits=350.0,
                chromatic_tint_rgb=[1.0, 0.28, 0.08],
            ),
            gate_weave=GateWeavePhysicsSpec(
                lateral_drift_microns=1.2,
                vertical_judder_microns=0.8,
                registration_pin_type="bell_howell_2709",
                frequency_hz=24.0,
            ),
            description="Kodak Vision3 500T 5219 35mm fallback stock",
        )


def get_domain_clapper_slate_spec(
    domain: Union[DomainArchetype, str],
    scenes: Optional[List[ScenePromptSpec]] = None,
    project_title: str = "Omni Production",
    director: str = "Omni Director",
    dp: str = "Omni DP",
) -> MasterProductionSlateSpec:
    """Calibrate SMPTE 12M production clapper slates and ASC-MHL v2.0 offload manifest across domain archetypes (PM-FEAT-018)."""
    domain_key = domain.value if hasattr(domain, "value") else str(domain).lower()

    if "culinary" in domain_key:
        def_day_night = "DAY"
        def_int_ext = "INT"
        def_shutter = 180.0
        def_filter = "Clear / Linear Polarizer"
        def_cam_roll_prefix = "A"
    elif "luxury" in domain_key:
        def_day_night = "NIGHT"
        def_int_ext = "INT"
        def_shutter = 180.0
        def_filter = "Black Pro-Mist 1/4"
        def_cam_roll_prefix = "A"
    elif "automotive" in domain_key:
        def_day_night = "DAY"
        def_int_ext = "EXT"
        def_shutter = 90.0
        def_filter = "ND 0.9 / Ultra Polarizer"
        def_cam_roll_prefix = "A"
    elif "kinetic" in domain_key:
        def_day_night = "DAY"
        def_int_ext = "EXT"
        def_shutter = 90.0
        def_filter = "Clear / ND 0.6"
        def_cam_roll_prefix = "A"
    elif "hardware" in domain_key:
        def_day_night = "DAY"
        def_int_ext = "INT"
        def_shutter = 180.0
        def_filter = "Clear Macro Optical"
        def_cam_roll_prefix = "A"
    elif "architectural" in domain_key:
        def_day_night = "DAY"
        def_int_ext = "INT"
        def_shutter = 180.0
        def_filter = "Ultra Pol / ND 0.3"
        def_cam_roll_prefix = "A"
    else:
        def_day_night = "DAY"
        def_int_ext = "INT"
        def_shutter = 180.0
        def_filter = "Clear"
        def_cam_roll_prefix = "A"

    slates: List[ClapperSlateSpec] = []
    current_frame = 24 * 3600  # 01:00:00:00

    if scenes is not None and len(scenes) > 0:
        for idx, sc in enumerate(scenes):
            dur = getattr(sc, "duration_frames", 240)
            existing_slate = getattr(sc, "clapper_slate", None)
            if existing_slate is not None:
                slates.append(existing_slate.model_copy(deep=True))
                tc = getattr(existing_slate, "timecode", None)
                if tc and hasattr(tc, "timecode_out"):
                    try:
                        current_frame = calculate_smpte12m_frames(tc.timecode_out, fps=tc.frame_rate)
                    except Exception:
                        current_frame += dur
                else:
                    current_frame += dur
            else:
                prompt_text = (getattr(sc, "omni_prose_prompt", "") or getattr(sc, "scene_prompt", "")).upper()
                day_night = def_day_night
                if "NIGHT" in prompt_text:
                    day_night = "NIGHT"
                elif "DAY" in prompt_text:
                    day_night = "DAY"

                int_ext = def_int_ext
                if "EXT." in prompt_text or "EXTERIOR" in prompt_text:
                    int_ext = "EXT"
                elif "INT." in prompt_text or "INTERIOR" in prompt_text:
                    int_ext = "INT"

                shutter = def_shutter
                craft = getattr(sc, "craft_camera", None)
                if craft and getattr(craft, "shutter_angle", None) is not None:
                    try:
                        shutter = float(craft.shutter_angle)
                    except (ValueError, TypeError):
                        pass

                tc_in = format_smpte12m_timecode(current_frame, fps=24.0)
                tc_out = format_smpte12m_timecode(current_frame + dur, fps=24.0)

                roll_num = idx + 1
                cam_roll = f"{def_cam_roll_prefix}{roll_num:02d}"
                snd_roll = f"SR{roll_num:02d}"

                slates.append(
                    ClapperSlateSpec(
                        scene_number=idx + 1,
                        take_number=1,
                        camera_roll=cam_roll,
                        sound_roll=snd_roll,
                        camera_id=def_cam_roll_prefix,
                        fps=24.0,
                        day_night=day_night,
                        int_ext=int_ext,
                        filter_pack=def_filter,
                        shutter_angle=shutter,
                        director=director,
                        dp=dp,
                        timecode=Smpte12MTimecodeSpec(
                            timecode_in=tc_in,
                            timecode_out=tc_out,
                            duration_frames=dur,
                            frame_rate=24.0,
                            drop_frame=False,
                        ),
                    )
                )
                current_frame += dur
    else:
        for i in range(1, 4):
            dur = 240
            tc_in = format_smpte12m_timecode(current_frame, fps=24.0)
            tc_out = format_smpte12m_timecode(current_frame + dur, fps=24.0)
            cam_roll = f"{def_cam_roll_prefix}{i:02d}"
            snd_roll = f"SR{i:02d}"

            slates.append(
                ClapperSlateSpec(
                    scene_number=i,
                    take_number=1,
                    camera_roll=cam_roll,
                    sound_roll=snd_roll,
                    camera_id=def_cam_roll_prefix,
                    fps=24.0,
                    day_night=def_day_night,
                    int_ext=def_int_ext,
                    filter_pack=def_filter,
                    shutter_angle=def_shutter,
                    director=director,
                    dp=dp,
                    timecode=Smpte12MTimecodeSpec(
                        timecode_in=tc_in,
                        timecode_out=tc_out,
                        duration_frames=dur,
                        frame_rate=24.0,
                        drop_frame=False,
                    ),
                )
            )
            current_frame += dur

    hash_entries: List[AscMhlHashEntry] = []
    for idx, sl in enumerate(slates):
        f_name = f"{sl.camera_roll}_{sl.scene_number:02d}_take{sl.take_number:02d}.mov"
        mock_seed = f"{project_title}_{f_name}".encode("utf-8")
        hash_entries.append(
            AscMhlHashEntry(
                file_path=f_name,
                file_size_bytes=104857600 * (idx + 1),
                xxhash64=hashlib.sha256(mock_seed).hexdigest()[:16],
                sha1=hashlib.sha1(mock_seed).hexdigest(),
                md5=hashlib.md5(mock_seed).hexdigest(),
                hash_timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )

    asc_mhl = AscMhlManifestSpec(
        mhl_version="2.0",
        project_title=project_title,
        creation_date=datetime.now(timezone.utc).isoformat(),
        hash_entries=hash_entries,
    )

    return MasterProductionSlateSpec(
        project_title=project_title,
        director=director,
        dp=dp,
        scenes=slates,
        asc_mhl=asc_mhl,
    )


def get_domain_drone_spec(domain: Union[DomainArchetype, str]) -> DroneFlightPathSpec:
    """Calibrate aerial drone flight paths, GPS waypoints, gimbal telemetry, and Part 107 compliance (PM-FEAT-019)."""
    domain_key = domain.value if hasattr(domain, "value") else str(domain).lower()

    base_lat = 34.0522
    base_lon = -118.2437
    base_msl = 120.0

    if "automotive" in domain_key:
        aircraft_model = "Freefly Systems Alta X / RED V-Raptor 8K"
        rig = DroneRigType.HEAVY_LIFTER_ALTA_X
        profile = "high_speed_vehicle_pursuit"
        min_alt = 18.0
        max_alt = 35.0  # 35m AGL
        speed = 18.0    # 18 m/s
        duration = 12.0
        dist = round(speed * duration, 1)
        gimbal = GimbalOrientationSpec(
            pitch_deg=-18.0,
            yaw_deg=0.0,
            roll_deg=0.0,
            stabilization_mode="follow_yaw",
            focal_length_equiv_mm=35.0,
        )
        solar = SolarEphemerisSpec(
            solar_elevation_deg=14.5,
            solar_azimuth_deg=248.0,
            golden_hour_active=True,
            lens_flare_risk="moderate",
            color_temperature_kelvin=3200,
        )
        wind = WindDriftVectorSpec(
            wind_speed_knots=9.0,
            wind_direction_deg=260.0,
            gust_speed_knots=14.0,
            drift_compensation_deg=3.5,
            turbulence_rating="light",
        )
        desc = "Freefly Alta X heavy lift cinema quadcopter high-speed vehicle tracking at 18 m/s, 35m AGL with golden hour raking lighting."

    elif "culinary" in domain_key:
        aircraft_model = "Micro Cablecam Hybrid / Sony FX3"
        rig = DroneRigType.CABLE_CAM_HYBRID
        profile = "indoor_slow_orbital_reveal"
        min_alt = 1.2
        max_alt = 3.0   # 3m AGL
        speed = 1.5     # 1.5 m/s
        duration = 16.0
        dist = round(speed * duration, 1)
        gimbal = GimbalOrientationSpec(
            pitch_deg=-38.0,
            yaw_deg=15.0,
            roll_deg=0.0,
            stabilization_mode="follow_yaw",
            focal_length_equiv_mm=50.0,
        )
        solar = SolarEphemerisSpec(
            solar_elevation_deg=50.0,
            solar_azimuth_deg=180.0,
            golden_hour_active=False,
            lens_flare_risk="low",
            color_temperature_kelvin=3200,
        )
        wind = WindDriftVectorSpec(
            wind_speed_knots=0.5,
            wind_direction_deg=0.0,
            gust_speed_knots=1.0,
            drift_compensation_deg=0.0,
            turbulence_rating="none",
        )
        desc = "Micro-quadcopter cablecam hybrid indoor low-altitude (3m AGL) smooth slow orbital reveal (1.5 m/s) with studio lighting."

    elif "luxury" in domain_key:
        aircraft_model = "DJI Inspire 3 / Zenmuse X9-8K Air"
        rig = DroneRigType.COMPACT_CINEMA_INSPIRE3
        profile = "architectural_fashion_sweep"
        min_alt = 8.0
        max_alt = 20.0  # 20m AGL
        speed = 4.5     # smooth pan
        duration = 15.0
        dist = round(speed * duration, 1)
        gimbal = GimbalOrientationSpec(
            pitch_deg=-12.0,
            yaw_deg=-5.0,
            roll_deg=0.0,
            stabilization_mode="follow_yaw",
            focal_length_equiv_mm=40.0,
        )
        solar = SolarEphemerisSpec(
            solar_elevation_deg=11.0,
            solar_azimuth_deg=262.0,
            golden_hour_active=True,
            lens_flare_risk="moderate",
            color_temperature_kelvin=3400,
        )
        wind = WindDriftVectorSpec(
            wind_speed_knots=6.0,
            wind_direction_deg=275.0,
            gust_speed_knots=9.0,
            drift_compensation_deg=2.2,
            turbulence_rating="light",
        )
        desc = "DJI Inspire 3 cinema quadcopter architectural location sweep, 20m AGL with golden hour raking light and smooth horizontal pan."

    elif "kinetic" in domain_key:
        aircraft_model = "Shendrones Thicc FPV Cinelifter / RED Komodo 6K"
        rig = DroneRigType.FPV_CINELIFTER_ACRO
        profile = "dynamic_fpv_canyon_dive"
        min_alt = 6.0
        max_alt = 38.0  # dynamic dive
        speed = 25.0    # 25 m/s
        duration = 10.0
        dist = round(speed * duration, 1)
        gimbal = GimbalOrientationSpec(
            pitch_deg=-42.0,  # aggressive gimbal pitch
            yaw_deg=0.0,
            roll_deg=5.0,
            stabilization_mode="fpv_lock",
            focal_length_equiv_mm=18.0,
        )
        solar = SolarEphemerisSpec(
            solar_elevation_deg=38.0,
            solar_azimuth_deg=220.0,
            golden_hour_active=False,
            lens_flare_risk="moderate",
            color_temperature_kelvin=5600,
        )
        wind = WindDriftVectorSpec(
            wind_speed_knots=14.0,
            wind_direction_deg=285.0,
            gust_speed_knots=22.0,
            drift_compensation_deg=5.8,
            turbulence_rating="moderate",
        )
        desc = "FPV racing cinelifter drone dynamic dive and canyon carve at 25 m/s with aggressive gimbal pitch and high battery draw."

    elif "hardware" in domain_key:
        aircraft_model = "Precision Cleanroom Cablecam / Sony FX3"
        rig = DroneRigType.CABLE_CAM_HYBRID
        profile = "linear_cleanroom_flyover"
        min_alt = 2.0
        max_alt = 5.0   # 5m AGL
        speed = 5.0     # steady 5 m/s
        duration = 14.0
        dist = round(speed * duration, 1)
        gimbal = GimbalOrientationSpec(
            pitch_deg=-45.0,
            yaw_deg=0.0,
            roll_deg=0.0,
            stabilization_mode="follow_yaw",
            focal_length_equiv_mm=28.0,
        )
        solar = SolarEphemerisSpec(
            solar_elevation_deg=62.0,
            solar_azimuth_deg=180.0,
            golden_hour_active=False,
            lens_flare_risk="low",
            color_temperature_kelvin=5500,
        )
        wind = WindDriftVectorSpec(
            wind_speed_knots=1.0,
            wind_direction_deg=0.0,
            gust_speed_knots=2.0,
            drift_compensation_deg=0.0,
            turbulence_rating="none",
        )
        desc = "Precision cablecam cleanroom quadcopter linear flyover at steady 5 m/s with studio high noon top-light illumination."

    elif "architectural" in domain_key:
        aircraft_model = "DJI Inspire 3 / Zenmuse X9-8K Air"
        rig = DroneRigType.COMPACT_CINEMA_INSPIRE3
        profile = "monolithic_orbital_reveal"
        min_alt = 22.0
        max_alt = 45.0  # 45m AGL, FAA Part 107 compliant <= 120m
        speed = 4.0
        duration = 18.0
        dist = round(speed * duration, 1)
        gimbal = GimbalOrientationSpec(
            pitch_deg=-20.0,
            yaw_deg=-10.0,
            roll_deg=0.0,
            stabilization_mode="follow_yaw",
            focal_length_equiv_mm=24.0,
        )
        solar = SolarEphemerisSpec(
            solar_elevation_deg=7.5,
            solar_azimuth_deg=272.0,
            golden_hour_active=True,
            lens_flare_risk="moderate",
            color_temperature_kelvin=3000,
        )
        wind = WindDriftVectorSpec(
            wind_speed_knots=7.0,
            wind_direction_deg=280.0,
            gust_speed_knots=11.0,
            drift_compensation_deg=2.8,
            turbulence_rating="light",
        )
        desc = "DJI Inspire 3 cinema quadcopter slow orbital reveal at 45m AGL under magic hour / golden hour, FAA Part 107 compliant."

    else:
        aircraft_model = "DJI Inspire 3 / Zenmuse X9-8K Air"
        rig = DroneRigType.COMPACT_CINEMA_INSPIRE3
        profile = "cinematic_establishing_sweep"
        min_alt = 10.0
        max_alt = 25.0
        speed = 6.0
        duration = 15.0
        dist = round(speed * duration, 1)
        gimbal = GimbalOrientationSpec(
            pitch_deg=-15.0,
            yaw_deg=0.0,
            roll_deg=0.0,
            stabilization_mode="follow_yaw",
            focal_length_equiv_mm=35.0,
        )
        solar = SolarEphemerisSpec(
            solar_elevation_deg=20.0,
            solar_azimuth_deg=240.0,
            golden_hour_active=True,
            lens_flare_risk="low",
            color_temperature_kelvin=4000,
        )
        wind = WindDriftVectorSpec(
            wind_speed_knots=5.0,
            wind_direction_deg=270.0,
            gust_speed_knots=8.0,
            drift_compensation_deg=1.5,
            turbulence_rating="light",
        )
        desc = f"Calibrated aerial drone flight path for {domain_key}, FAA Part 107 compliant."

    waypoints: List[FlightWaypointGPS] = []
    num_wp = 4
    for i in range(num_wp):
        frac = i / max(1, num_wp - 1)
        cur_lat = round(base_lat + (frac * 0.0018), 6)
        cur_lon = round(base_lon + (frac * 0.0022), 6)
        cur_agl = round(min_alt + (math.sin(frac * math.pi) * (max_alt - min_alt)), 1)
        cur_msl = round(base_msl + cur_agl, 1)
        cur_time = round(frac * duration, 1)
        cue = (
            "Waypoint 1: Aircraft takeoff & camera vector acquisition" if i == 0
            else "Waypoint 2: Mid-flight kinetic sweep & subject lock" if i == 1
            else "Waypoint 3: Apex framing reveal & light glint" if i == 2
            else "Waypoint 4: Terminal deceleration & hero composition hold"
        )
        waypoints.append(
            FlightWaypointGPS(
                waypoint_id=i + 1,
                latitude=cur_lat,
                longitude=cur_lon,
                altitude_m_agl=cur_agl,
                altitude_m_msl=cur_msl,
                speed_mps=speed,
                timestamp_s=cur_time,
                heading_deg=round(frac * 45.0, 1),
                action_cue=cue,
            )
        )

    return DroneFlightPathSpec(
        flight_id=f"DRONE_{domain_key.upper()[:4]}_01",
        aircraft_model=aircraft_model,
        drone_rig=rig,
        flight_profile=profile,
        min_altitude_agl_m=min_alt,
        max_altitude_agl_m=max_alt,
        total_distance_m=dist,
        flight_duration_s=duration,
        waypoints=waypoints,
        gimbal=gimbal,
        solar_ephemeris=solar,
        wind_drift=wind,
        faa_part_107_compliant=True,
        description=desc,
    )


def get_domain_aicp_bid_spec(
    bible_or_domain: Union[MasterProductionBible, DomainArchetype, str],
    total_runtime_seconds: Optional[int] = None,
) -> MasterAicpBidSpec:
    """Calibrate AICP commercial production bid packages and budgets across domain archetypes (PM-FEAT-020)."""
    if isinstance(bible_or_domain, MasterProductionBible):
        domain = bible_or_domain.domain_archetype or classify_brief_domain(f"{bible_or_domain.project_title} {bible_or_domain.logline}")
        title = bible_or_domain.project_title
        runtime = total_runtime_seconds or bible_or_domain.total_runtime_seconds
    elif hasattr(bible_or_domain, "domain_archetype"):
        domain = getattr(bible_or_domain, "domain_archetype", "culinary_asmr")
        title = getattr(bible_or_domain, "project_title", "Commercial Production")
        runtime = total_runtime_seconds or getattr(bible_or_domain, "total_runtime_seconds", 30)
    else:
        domain = bible_or_domain
        title = f"{str(domain).replace('_', ' ').title()} Commercial"
        runtime = total_runtime_seconds or 30

    domain_key = domain.value if hasattr(domain, "value") else str(domain).lower()

    if "automotive" in domain_key:
        # Senior PM Spec: $320k - $480k -> Target Grand Total: $385,000 (Direct: $308,000)
        labor_tier = CrewLaborTier.TIER_UNION_DGA_IATSE
        days = 3
        brand = "AeroDynamics Hypercar Group"
        loc = "Willow Springs Raceway & Mojave Desert, CA"
        line_items = [
            AicpLineItemSpec(account_number="A-101", section=AicpSectionCode.SECTION_A, description="Executive Producer / Line Producer (Prep & Wrap)", crew_tier=labor_tier, rate_basis="prep_wrap", units_count=5.0, unit_rate_usd=2800.0, fringes_pct=0.0, total_cost_usd=14000.0),
            AicpLineItemSpec(account_number="A-102", section=AicpSectionCode.SECTION_A, description="Production Manager & 1st AD", crew_tier=labor_tier, rate_basis="prep_wrap", units_count=4.0, unit_rate_usd=1800.0, fringes_pct=0.0, total_cost_usd=7200.0),
            AicpLineItemSpec(account_number="B-101", section=AicpSectionCode.SECTION_B, description="Director of Photography (DGA/Local 600, 3 Shoot Days)", crew_tier=labor_tier, rate_basis="day", units_count=3.0, unit_rate_usd=4500.0, fringes_pct=0.0, total_cost_usd=13500.0),
            AicpLineItemSpec(account_number="B-102", section=AicpSectionCode.SECTION_B, description="1st AC & 2nd AC Focus Puller Unit", crew_tier=labor_tier, rate_basis="day", units_count=3.0, unit_rate_usd=2200.0, fringes_pct=0.0, total_cost_usd=6600.0),
            AicpLineItemSpec(account_number="B-103", section=AicpSectionCode.SECTION_B, description="Chief Lighting Technician (Gaffer) & Best Boy Electric", crew_tier=labor_tier, rate_basis="day", units_count=3.0, unit_rate_usd=2600.0, fringes_pct=0.0, total_cost_usd=7800.0),
            AicpLineItemSpec(account_number="B-104", section=AicpSectionCode.SECTION_B, description="Key Grip & Precision Rigging Grips", crew_tier=labor_tier, rate_basis="day", units_count=3.0, unit_rate_usd=2600.0, fringes_pct=0.0, total_cost_usd=7800.0),
            AicpLineItemSpec(account_number="B-105", section=AicpSectionCode.SECTION_B, description="Production Sound Mixer & Telemetry Recordist", crew_tier=labor_tier, rate_basis="day", units_count=3.0, unit_rate_usd=1600.0, fringes_pct=0.0, total_cost_usd=4800.0),
            AicpLineItemSpec(account_number="B-106", section=AicpSectionCode.SECTION_B, description="Digital Imaging Technician (DIT) & On-Set Colorist", crew_tier=labor_tier, rate_basis="day", units_count=3.0, unit_rate_usd=1600.0, fringes_pct=0.0, total_cost_usd=4800.0),
            AicpLineItemSpec(account_number="B-107", section=AicpSectionCode.SECTION_B, description="Precision Pursuit Stunt Driver & Russian Arm Tech", crew_tier=labor_tier, rate_basis="day", units_count=3.0, unit_rate_usd=3600.0, fringes_pct=0.0, total_cost_usd=10800.0),
            AicpLineItemSpec(account_number="B-108", section=AicpSectionCode.SECTION_B, description="Heavy Lift Cinema Drone RPIC & Gimbal Operator", crew_tier=labor_tier, rate_basis="day", units_count=3.0, unit_rate_usd=3200.0, fringes_pct=0.0, total_cost_usd=9600.0),
            AicpLineItemSpec(account_number="C-101", section=AicpSectionCode.SECTION_C, description="Raceway Track Rental, Desert BLM Permits & CHP Escort", crew_tier=labor_tier, rate_basis="flat", units_count=1.0, unit_rate_usd=18000.0, fringes_pct=0.0, total_cost_usd=18000.0),
            AicpLineItemSpec(account_number="C-102", section=AicpSectionCode.SECTION_C, description="Crew Lodging, Remote Location Travel & Fuel Logistics", crew_tier=labor_tier, rate_basis="flat", units_count=1.0, unit_rate_usd=10000.0, fringes_pct=0.0, total_cost_usd=10000.0),
            AicpLineItemSpec(account_number="D-101", section=AicpSectionCode.SECTION_D, description="Hero Hypercar Detailing, Carbon Fiber Armor & Racing Wardrobe", crew_tier=labor_tier, rate_basis="flat", units_count=1.0, unit_rate_usd=12000.0, fringes_pct=0.0, total_cost_usd=12000.0),
            AicpLineItemSpec(account_number="E-101", section=AicpSectionCode.SECTION_E, description="ARRI Alexa 35 High-Speed Package & Cooke S7/i Primes", crew_tier=labor_tier, rate_basis="day", units_count=3.0, unit_rate_usd=4800.0, fringes_pct=0.0, total_cost_usd=14400.0),
            AicpLineItemSpec(account_number="E-102", section=AicpSectionCode.SECTION_E, description="10-Ton Grip/Electric Truck & ARRI Skypanel X / Vortex8 Package", crew_tier=labor_tier, rate_basis="day", units_count=3.0, unit_rate_usd=4200.0, fringes_pct=0.0, total_cost_usd=12600.0),
            AicpLineItemSpec(account_number="E-103", section=AicpSectionCode.SECTION_E, description="Russian Arm Flight Head Pursuit Vehicle System Rental", crew_tier=labor_tier, rate_basis="day", units_count=3.0, unit_rate_usd=6800.0, fringes_pct=0.0, total_cost_usd=20400.0),
            AicpLineItemSpec(account_number="E-104", section=AicpSectionCode.SECTION_E, description="Freefly Alta X Octocopter Drone Package & Ground Station", crew_tier=labor_tier, rate_basis="day", units_count=3.0, unit_rate_usd=2800.0, fringes_pct=0.0, total_cost_usd=8400.0),
            AicpLineItemSpec(account_number="F-101", section=AicpSectionCode.SECTION_F, description="Practical Dust/Sparks Atmosphere & Safety Stunt Rigging", crew_tier=labor_tier, rate_basis="flat", units_count=1.0, unit_rate_usd=9000.0, fringes_pct=0.0, total_cost_usd=9000.0),
            AicpLineItemSpec(account_number="G-101", section=AicpSectionCode.SECTION_G, description="Production Catering, Craft Services & Environmental Safety", crew_tier=labor_tier, rate_basis="day", units_count=3.0, unit_rate_usd=2200.0, fringes_pct=0.0, total_cost_usd=6600.0),
            AicpLineItemSpec(account_number="H-101", section=AicpSectionCode.SECTION_H, description="SAG-AFTRA Principal Stunt Pilot / Driver Session Fees", crew_tier=labor_tier, rate_basis="day", units_count=3.0, unit_rate_usd=2600.0, fringes_pct=0.0, total_cost_usd=7800.0),
            AicpLineItemSpec(account_number="I-101", section=AicpSectionCode.SECTION_I, description="Talent Fitted Nomex Racing Suits & Ground Transport", crew_tier=labor_tier, rate_basis="flat", units_count=1.0, unit_rate_usd=3800.0, fringes_pct=0.0, total_cost_usd=3800.0),
            AicpLineItemSpec(account_number="J-101", section=AicpSectionCode.SECTION_J, description="Commercial Offline Picture Editorial & High-Speed Conform", crew_tier=labor_tier, rate_basis="flat", units_count=1.0, unit_rate_usd=11000.0, fringes_pct=0.0, total_cost_usd=11000.0),
            AicpLineItemSpec(account_number="K-101", section=AicpSectionCode.SECTION_K, description="Dyno Engine Foley, Diegetic Spatial Audio & Dolby Atmos Mix", crew_tier=labor_tier, rate_basis="flat", units_count=1.0, unit_rate_usd=10000.0, fringes_pct=0.0, total_cost_usd=10000.0),
            AicpLineItemSpec(account_number="L-101", section=AicpSectionCode.SECTION_L, description="Automotive Paint Rig Removal & Baselight HDR 3D LUT Grade", crew_tier=labor_tier, rate_basis="flat", units_count=1.0, unit_rate_usd=11000.0, fringes_pct=0.0, total_cost_usd=11000.0),
            AicpLineItemSpec(account_number="M-101", section=AicpSectionCode.SECTION_M, description="Precision Vehicle Damage Liability & Negative Insurance", crew_tier=labor_tier, rate_basis="flat", units_count=1.0, unit_rate_usd=6500.0, fringes_pct=0.0, total_cost_usd=6500.0),
        ]

    elif "culinary" in domain_key:
        # Senior PM Spec: $95k - $165k -> Target Grand Total: $125,000 (Direct: $100,000)
        labor_tier = CrewLaborTier.TIER_COMMERCIAL_TIER_2
        days = 1
        brand = "Nordic Gastronomy Artisans"
        loc = "Culinary Soundstage, Stockholm / Brooklyn, NY"
        line_items = [
            AicpLineItemSpec(account_number="A-101", section=AicpSectionCode.SECTION_A, description="Line Producer & Food Production Coordinator", crew_tier=labor_tier, rate_basis="prep_wrap", units_count=4.0, unit_rate_usd=2125.0, fringes_pct=0.0, total_cost_usd=8500.0),
            AicpLineItemSpec(account_number="B-101", section=AicpSectionCode.SECTION_B, description="Director of Photography & Tabletop Macro Specialist", crew_tier=labor_tier, rate_basis="day", units_count=1.0, unit_rate_usd=5000.0, fringes_pct=0.0, total_cost_usd=5000.0),
            AicpLineItemSpec(account_number="B-102", section=AicpSectionCode.SECTION_B, description="Master Food Stylist & Culinary Prep Chefs", crew_tier=labor_tier, rate_basis="day", units_count=1.0, unit_rate_usd=8500.0, fringes_pct=0.0, total_cost_usd=8500.0),
            AicpLineItemSpec(account_number="B-103", section=AicpSectionCode.SECTION_B, description="1st AC & Focus Puller (Macro Probe Precision)", crew_tier=labor_tier, rate_basis="day", units_count=1.0, unit_rate_usd=1800.0, fringes_pct=0.0, total_cost_usd=1800.0),
            AicpLineItemSpec(account_number="B-104", section=AicpSectionCode.SECTION_B, description="Gaffer & Tabletop Fiber Optic Lighting Technician", crew_tier=labor_tier, rate_basis="day", units_count=1.0, unit_rate_usd=2200.0, fringes_pct=0.0, total_cost_usd=2200.0),
            AicpLineItemSpec(account_number="B-105", section=AicpSectionCode.SECTION_B, description="Key Grip & Motion Control Arm Operator", crew_tier=labor_tier, rate_basis="day", units_count=1.0, unit_rate_usd=2500.0, fringes_pct=0.0, total_cost_usd=2500.0),
            AicpLineItemSpec(account_number="B-106", section=AicpSectionCode.SECTION_B, description="High-Resolution Binaural Audio Specialist (ASMR)", crew_tier=labor_tier, rate_basis="day", units_count=1.0, unit_rate_usd=2800.0, fringes_pct=0.0, total_cost_usd=2800.0),
            AicpLineItemSpec(account_number="B-107", section=AicpSectionCode.SECTION_B, description="DIT / ASC CDL Tabletop Color Specialist", crew_tier=labor_tier, rate_basis="day", units_count=1.0, unit_rate_usd=2200.0, fringes_pct=0.0, total_cost_usd=2200.0),
            AicpLineItemSpec(account_number="B-108", section=AicpSectionCode.SECTION_B, description="Micro-Drone Cablecam Indoor Pilot", crew_tier=labor_tier, rate_basis="day", units_count=1.0, unit_rate_usd=7000.0, fringes_pct=0.0, total_cost_usd=7000.0),
            AicpLineItemSpec(account_number="C-101", section=AicpSectionCode.SECTION_C, description="Commercial Kitchen Soundstage Rental & Prep Facility", crew_tier=labor_tier, rate_basis="day", units_count=1.0, unit_rate_usd=11500.0, fringes_pct=0.0, total_cost_usd=11500.0),
            AicpLineItemSpec(account_number="D-101", section=AicpSectionCode.SECTION_D, description="Culinary Hero Props, Artisan Ceramics & Organic Ingredients", crew_tier=labor_tier, rate_basis="flat", units_count=1.0, unit_rate_usd=9000.0, fringes_pct=0.0, total_cost_usd=9000.0),
            AicpLineItemSpec(account_number="E-101", section=AicpSectionCode.SECTION_E, description="Phantom Flex 4K High-Speed & Laowa 24mm Macro Probe Package", crew_tier=labor_tier, rate_basis="day", units_count=1.0, unit_rate_usd=14000.0, fringes_pct=0.0, total_cost_usd=14000.0),
            AicpLineItemSpec(account_number="F-101", section=AicpSectionCode.SECTION_F, description="Piston Pour Rig, Liquid Nitrogen FX & Induction Surfaces", crew_tier=labor_tier, rate_basis="flat", units_count=1.0, unit_rate_usd=4000.0, fringes_pct=0.0, total_cost_usd=4000.0),
            AicpLineItemSpec(account_number="G-101", section=AicpSectionCode.SECTION_G, description="Kitchen Prep Supplies, Commercial Sanitation & Catering", crew_tier=labor_tier, rate_basis="day", units_count=1.0, unit_rate_usd=3000.0, fringes_pct=0.0, total_cost_usd=3000.0),
            AicpLineItemSpec(account_number="H-101", section=AicpSectionCode.SECTION_H, description="SAG-AFTRA Hand Model & Chef Talent Session Fees", crew_tier=labor_tier, rate_basis="day", units_count=1.0, unit_rate_usd=3000.0, fringes_pct=0.0, total_cost_usd=3000.0),
            AicpLineItemSpec(account_number="I-101", section=AicpSectionCode.SECTION_I, description="Talent Wardrobe Styling & Linen Apron Fittings", crew_tier=labor_tier, rate_basis="flat", units_count=1.0, unit_rate_usd=1000.0, fringes_pct=0.0, total_cost_usd=1000.0),
            AicpLineItemSpec(account_number="J-101", section=AicpSectionCode.SECTION_J, description="Tabletop Rhythmic Macro Editorial & Speed-Ramp Assembly", crew_tier=labor_tier, rate_basis="flat", units_count=1.0, unit_rate_usd=4500.0, fringes_pct=0.0, total_cost_usd=4500.0),
            AicpLineItemSpec(account_number="K-101", section=AicpSectionCode.SECTION_K, description="Binaural ASMR Foley Mixing, Liquid Sizzle & Atmos Mastering", crew_tier=labor_tier, rate_basis="flat", units_count=1.0, unit_rate_usd=4500.0, fringes_pct=0.0, total_cost_usd=4500.0),
            AicpLineItemSpec(account_number="L-101", section=AicpSectionCode.SECTION_L, description="Organic Food Color Grading & Microscopic Clean-up", crew_tier=labor_tier, rate_basis="flat", units_count=1.0, unit_rate_usd=3000.0, fringes_pct=0.0, total_cost_usd=3000.0),
            AicpLineItemSpec(account_number="M-101", section=AicpSectionCode.SECTION_M, description="Production Equipment & Tabletop Soundstage Liability Insurance", crew_tier=labor_tier, rate_basis="flat", units_count=1.0, unit_rate_usd=2000.0, fringes_pct=0.0, total_cost_usd=2000.0),
        ]

    elif "luxury" in domain_key:
        # Senior PM Spec: $220k - $380k -> Target Grand Total: $295,000 (Direct: $236,000)
        labor_tier = CrewLaborTier.TIER_COMMERCIAL_TIER_1
        days = 2
        brand = "Maison de Haute Horlogerie Paris"
        loc = "Architectural Villa & Parisian Modernist Studio"
        line_items = [
            AicpLineItemSpec(account_number="A-101", section=AicpSectionCode.SECTION_A, description="Executive Producer & Parisian Line Producer", crew_tier=labor_tier, rate_basis="prep_wrap", units_count=5.0, unit_rate_usd=4400.0, fringes_pct=0.0, total_cost_usd=22000.0),
            AicpLineItemSpec(account_number="B-101", section=AicpSectionCode.SECTION_B, description="Director of Photography (Vogue / Harper's Bazaar Cinematographer)", crew_tier=labor_tier, rate_basis="day", units_count=2.0, unit_rate_usd=8000.0, fringes_pct=0.0, total_cost_usd=16000.0),
            AicpLineItemSpec(account_number="B-102", section=AicpSectionCode.SECTION_B, description="Haute Couture Fashion Stylist & Tailoring Team", crew_tier=labor_tier, rate_basis="day", units_count=2.0, unit_rate_usd=7000.0, fringes_pct=0.0, total_cost_usd=14000.0),
            AicpLineItemSpec(account_number="B-103", section=AicpSectionCode.SECTION_B, description="Celebrity Hair, Makeup & SFX Beauty Team", crew_tier=labor_tier, rate_basis="day", units_count=2.0, unit_rate_usd=6000.0, fringes_pct=0.0, total_cost_usd=12000.0),
            AicpLineItemSpec(account_number="B-104", section=AicpSectionCode.SECTION_B, description="Gaffer & Chic Chiaroscuro Lighting Electricians", crew_tier=labor_tier, rate_basis="day", units_count=2.0, unit_rate_usd=4000.0, fringes_pct=0.0, total_cost_usd=8000.0),
            AicpLineItemSpec(account_number="B-105", section=AicpSectionCode.SECTION_B, description="Key Grip & Dolly Grip Master", crew_tier=labor_tier, rate_basis="day", units_count=2.0, unit_rate_usd=3500.0, fringes_pct=0.0, total_cost_usd=7000.0),
            AicpLineItemSpec(account_number="B-106", section=AicpSectionCode.SECTION_B, description="DIT / Film Emulation Look Technician", crew_tier=labor_tier, rate_basis="day", units_count=2.0, unit_rate_usd=2500.0, fringes_pct=0.0, total_cost_usd=5000.0),
            AicpLineItemSpec(account_number="B-107", section=AicpSectionCode.SECTION_B, description="DJI Inspire 3 Aerial Cinema Drone Pilot & Spotter", crew_tier=labor_tier, rate_basis="day", units_count=2.0, unit_rate_usd=3000.0, fringes_pct=0.0, total_cost_usd=6000.0),
            AicpLineItemSpec(account_number="C-101", section=AicpSectionCode.SECTION_C, description="Modernist Architectural Estate Location Fee & Permits", crew_tier=labor_tier, rate_basis="flat", units_count=1.0, unit_rate_usd=28000.0, fringes_pct=0.0, total_cost_usd=28000.0),
            AicpLineItemSpec(account_number="D-101", section=AicpSectionCode.SECTION_D, description="Hero Archive Wardrobe, Haute Jewelry & Silk Fabric Scenics", crew_tier=labor_tier, rate_basis="flat", units_count=1.0, unit_rate_usd=24000.0, fringes_pct=0.0, total_cost_usd=24000.0),
            AicpLineItemSpec(account_number="E-101", section=AicpSectionCode.SECTION_E, description="RED V-Raptor XL 8K VV & Anamorphic ARRI Master Prime Lenses", crew_tier=labor_tier, rate_basis="day", units_count=2.0, unit_rate_usd=19000.0, fringes_pct=0.0, total_cost_usd=38000.0),
            AicpLineItemSpec(account_number="F-101", section=AicpSectionCode.SECTION_F, description="Diffused Silk Overhead Flyswatter & Wind Machine Rig", crew_tier=labor_tier, rate_basis="flat", units_count=1.0, unit_rate_usd=8000.0, fringes_pct=0.0, total_cost_usd=8000.0),
            AicpLineItemSpec(account_number="G-101", section=AicpSectionCode.SECTION_G, description="Executive VIP Hospitality, Green Room & Artisanal Catering", crew_tier=labor_tier, rate_basis="day", units_count=2.0, unit_rate_usd=3000.0, fringes_pct=0.0, total_cost_usd=6000.0),
            AicpLineItemSpec(account_number="H-101", section=AicpSectionCode.SECTION_H, description="International Runway Supermodel Session Fee (SAG-AFTRA)", crew_tier=labor_tier, rate_basis="day", units_count=2.0, unit_rate_usd=7000.0, fringes_pct=0.0, total_cost_usd=14000.0),
            AicpLineItemSpec(account_number="I-101", section=AicpSectionCode.SECTION_I, description="VIP First Class Travel, Security Escort & Dressing Suite", crew_tier=labor_tier, rate_basis="flat", units_count=1.0, unit_rate_usd=5000.0, fringes_pct=0.0, total_cost_usd=5000.0),
            AicpLineItemSpec(account_number="J-101", section=AicpSectionCode.SECTION_J, description="High-Fashion Rhythmic Editorial Assembly & Beauty Cut", crew_tier=labor_tier, rate_basis="flat", units_count=1.0, unit_rate_usd=9000.0, fringes_pct=0.0, total_cost_usd=9000.0),
            AicpLineItemSpec(account_number="K-101", section=AicpSectionCode.SECTION_K, description="Bespoke Minimalist Neoclassical Score & Spatial Audio Mix", crew_tier=labor_tier, rate_basis="flat", units_count=1.0, unit_rate_usd=6000.0, fringes_pct=0.0, total_cost_usd=6000.0),
            AicpLineItemSpec(account_number="L-101", section=AicpSectionCode.SECTION_L, description="35mm Film Grain Emulation & Golden Hour 3D LUT Color Grade", crew_tier=labor_tier, rate_basis="flat", units_count=1.0, unit_rate_usd=5000.0, fringes_pct=0.0, total_cost_usd=5000.0),
            AicpLineItemSpec(account_number="M-101", section=AicpSectionCode.SECTION_M, description="High-Value Haute Horlogerie Guarding & Commercial Production Insurance", crew_tier=labor_tier, rate_basis="flat", units_count=1.0, unit_rate_usd=3000.0, fringes_pct=0.0, total_cost_usd=3000.0),
        ]

    elif "kinetic" in domain_key:
        # Senior PM Spec: $280k - $450k -> Target Grand Total: $360,000 (Direct: $288,000)
        labor_tier = CrewLaborTier.TIER_UNION_DGA_IATSE
        days = 2
        brand = "Vanguard Kinetic Athletics"
        loc = "Red Rock Canyon & Industrial Airfield, NV"
        line_items = [
            AicpLineItemSpec(account_number="A-101", section=AicpSectionCode.SECTION_A, description="Executive Producer & Action Stunt Coordinator", crew_tier=labor_tier, rate_basis="prep_wrap", units_count=4.0, unit_rate_usd=4500.0, fringes_pct=0.0, total_cost_usd=18000.0),
            AicpLineItemSpec(account_number="B-101", section=AicpSectionCode.SECTION_B, description="Director of Photography (Action Sports Specialist, 2 Days)", crew_tier=labor_tier, rate_basis="day", units_count=2.0, unit_rate_usd=6500.0, fringes_pct=0.0, total_cost_usd=13000.0),
            AicpLineItemSpec(account_number="B-102", section=AicpSectionCode.SECTION_B, description="World Champion FPV Racing Drone Pilots (Dual Unit)", crew_tier=labor_tier, rate_basis="day", units_count=2.0, unit_rate_usd=6500.0, fringes_pct=0.0, total_cost_usd=13000.0),
            AicpLineItemSpec(account_number="B-103", section=AicpSectionCode.SECTION_B, description="Wire Rigging & Extreme Stunt Safety Coordinators", crew_tier=labor_tier, rate_basis="day", units_count=2.0, unit_rate_usd=5500.0, fringes_pct=0.0, total_cost_usd=11000.0),
            AicpLineItemSpec(account_number="B-104", section=AicpSectionCode.SECTION_B, description="1st AC & High-Speed Optical Remote Technicians", crew_tier=labor_tier, rate_basis="day", units_count=2.0, unit_rate_usd=3200.0, fringes_pct=0.0, total_cost_usd=6400.0),
            AicpLineItemSpec(account_number="B-105", section=AicpSectionCode.SECTION_B, description="Gaffer & Heavy Sun Guns High-Speed Lighting Unit", crew_tier=labor_tier, rate_basis="day", units_count=2.0, unit_rate_usd=4200.0, fringes_pct=0.0, total_cost_usd=8400.0),
            AicpLineItemSpec(account_number="B-106", section=AicpSectionCode.SECTION_B, description="Key Grip & Kinetic Track Arm Riggers", crew_tier=labor_tier, rate_basis="day", units_count=2.0, unit_rate_usd=4200.0, fringes_pct=0.0, total_cost_usd=8400.0),
            AicpLineItemSpec(account_number="C-101", section=AicpSectionCode.SECTION_C, description="Airfield Tarmac & Red Rock Canyon Film Permits / EMT Medical", crew_tier=labor_tier, rate_basis="flat", units_count=1.0, unit_rate_usd=26000.0, fringes_pct=0.0, total_cost_usd=26000.0),
            AicpLineItemSpec(account_number="D-101", section=AicpSectionCode.SECTION_D, description="Kinetic Performance Suits, Stunt Harnesses & Custom Hardware", crew_tier=labor_tier, rate_basis="flat", units_count=1.0, unit_rate_usd=13000.0, fringes_pct=0.0, total_cost_usd=13000.0),
            AicpLineItemSpec(account_number="E-101", section=AicpSectionCode.SECTION_E, description="ARRI Alexa Mini LF, Freefly Wave High-Speed & FPV Cinelifter Rigs", crew_tier=labor_tier, rate_basis="day", units_count=2.0, unit_rate_usd=24000.0, fringes_pct=0.0, total_cost_usd=48000.0),
            AicpLineItemSpec(account_number="F-101", section=AicpSectionCode.SECTION_F, description="Pneumatic Air Ratchet Stunt Rigs & Crash Mats", crew_tier=labor_tier, rate_basis="flat", units_count=1.0, unit_rate_usd=11000.0, fringes_pct=0.0, total_cost_usd=11000.0),
            AicpLineItemSpec(account_number="G-101", section=AicpSectionCode.SECTION_G, description="Desert Mobile Craft Services, Hydration & Medical Safety", crew_tier=labor_tier, rate_basis="day", units_count=2.0, unit_rate_usd=2800.0, fringes_pct=0.0, total_cost_usd=5600.0),
            AicpLineItemSpec(account_number="H-101", section=AicpSectionCode.SECTION_H, description="SAG-AFTRA Olympic Parkour / Acrobat Talent Session Fees", crew_tier=labor_tier, rate_basis="day", units_count=2.0, unit_rate_usd=7200.0, fringes_pct=0.0, total_cost_usd=14400.0),
            AicpLineItemSpec(account_number="I-101", section=AicpSectionCode.SECTION_I, description="Talent Physiotherapy, Custom Padding & Ground Transportation", crew_tier=labor_tier, rate_basis="flat", units_count=1.0, unit_rate_usd=5000.0, fringes_pct=0.0, total_cost_usd=5000.0),
            AicpLineItemSpec(account_number="J-101", section=AicpSectionCode.SECTION_J, description="Dynamic Kinetic Editorial Assembly & Speed Ramp Post-Production", crew_tier=labor_tier, rate_basis="flat", units_count=1.0, unit_rate_usd=10000.0, fringes_pct=0.0, total_cost_usd=10000.0),
            AicpLineItemSpec(account_number="K-101", section=AicpSectionCode.SECTION_K, description="Industrial Electronic Kinetic Beat & 3D Spatial Audio Soundfield", crew_tier=labor_tier, rate_basis="flat", units_count=1.0, unit_rate_usd=8000.0, fringes_pct=0.0, total_cost_usd=8000.0),
            AicpLineItemSpec(account_number="L-101", section=AicpSectionCode.SECTION_L, description="Wire Rig Paint Removal, Speed Blur VFX & Punchy Contrast Grade", crew_tier=labor_tier, rate_basis="flat", units_count=1.0, unit_rate_usd=8000.0, fringes_pct=0.0, total_cost_usd=8000.0),
            AicpLineItemSpec(account_number="M-101", section=AicpSectionCode.SECTION_M, description="Aviation & High-Risk Stunt Commercial Production Insurance", crew_tier=labor_tier, rate_basis="flat", units_count=1.0, unit_rate_usd=5000.0, fringes_pct=0.0, total_cost_usd=5000.0),
        ]

    elif "hardware" in domain_key:
        # Senior PM Spec: $140k - $240k -> Target Grand Total: $185,000 (Direct: $148,000)
        labor_tier = CrewLaborTier.TIER_COMMERCIAL_TIER_1
        days = 2
        brand = "Quantum Nanotech Semiconductor Labs"
        loc = "ISO-5 Cleanroom Facility, Silicon Valley, CA"
        line_items = [
            AicpLineItemSpec(account_number="A-101", section=AicpSectionCode.SECTION_A, description="Line Producer & Cleanroom Protocol Coordinator", crew_tier=labor_tier, rate_basis="prep_wrap", units_count=4.0, unit_rate_usd=3500.0, fringes_pct=0.0, total_cost_usd=14000.0),
            AicpLineItemSpec(account_number="B-101", section=AicpSectionCode.SECTION_B, description="Director of Photography (Macro Tech Specialist, 2 Days)", crew_tier=labor_tier, rate_basis="day", units_count=2.0, unit_rate_usd=6000.0, fringes_pct=0.0, total_cost_usd=12000.0),
            AicpLineItemSpec(account_number="B-102", section=AicpSectionCode.SECTION_B, description="Motion Control Robotic Cinebot Operator (Bolt Jr+)", crew_tier=labor_tier, rate_basis="day", units_count=2.0, unit_rate_usd=5500.0, fringes_pct=0.0, total_cost_usd=11000.0),
            AicpLineItemSpec(account_number="B-103", section=AicpSectionCode.SECTION_B, description="1st AC & Focus Puller (Microscopic Depth of Field)", crew_tier=labor_tier, rate_basis="day", units_count=2.0, unit_rate_usd=2500.0, fringes_pct=0.0, total_cost_usd=5000.0),
            AicpLineItemSpec(account_number="B-104", section=AicpSectionCode.SECTION_B, description="Gaffer & Anti-Reflective Cleanroom Lighting Tech", crew_tier=labor_tier, rate_basis="day", units_count=2.0, unit_rate_usd=3000.0, fringes_pct=0.0, total_cost_usd=6000.0),
            AicpLineItemSpec(account_number="B-105", section=AicpSectionCode.SECTION_B, description="Precision Cleanroom Cablecam Operator", crew_tier=labor_tier, rate_basis="day", units_count=2.0, unit_rate_usd=3000.0, fringes_pct=0.0, total_cost_usd=6000.0),
            AicpLineItemSpec(account_number="B-106", section=AicpSectionCode.SECTION_B, description="DIT / Semiconductor Visual Telemetry Specialist", crew_tier=labor_tier, rate_basis="day", units_count=2.0, unit_rate_usd=2500.0, fringes_pct=0.0, total_cost_usd=5000.0),
            AicpLineItemSpec(account_number="C-101", section=AicpSectionCode.SECTION_C, description="ISO-5 Cleanroom Stage Rental & Bunny Suit Air Shower Protocol", crew_tier=labor_tier, rate_basis="flat", units_count=1.0, unit_rate_usd=12000.0, fringes_pct=0.0, total_cost_usd=12000.0),
            AicpLineItemSpec(account_number="D-101", section=AicpSectionCode.SECTION_D, description="Silicon Wafer Scenics, Laser Anodized Aluminum Fixtures & Props", crew_tier=labor_tier, rate_basis="flat", units_count=1.0, unit_rate_usd=11000.0, fringes_pct=0.0, total_cost_usd=11000.0),
            AicpLineItemSpec(account_number="E-101", section=AicpSectionCode.SECTION_E, description="Sony Venice 2 8K Cinema Camera & Bolt Jr+ High-Speed Cinebot", crew_tier=labor_tier, rate_basis="day", units_count=2.0, unit_rate_usd=14000.0, fringes_pct=0.0, total_cost_usd=28000.0),
            AicpLineItemSpec(account_number="F-101", section=AicpSectionCode.SECTION_F, description="Laser Alignment Optics, Coherent Ray Effects & Ion Cleaners", crew_tier=labor_tier, rate_basis="flat", units_count=1.0, unit_rate_usd=6000.0, fringes_pct=0.0, total_cost_usd=6000.0),
            AicpLineItemSpec(account_number="G-101", section=AicpSectionCode.SECTION_G, description="Electrostatic Discharge (ESD) Protection Gear & Crew Catering", crew_tier=labor_tier, rate_basis="day", units_count=2.0, unit_rate_usd=2000.0, fringes_pct=0.0, total_cost_usd=4000.0),
            AicpLineItemSpec(account_number="H-101", section=AicpSectionCode.SECTION_H, description="SAG-AFTRA Lead Scientist / Research Engineer Talent", crew_tier=labor_tier, rate_basis="day", units_count=2.0, unit_rate_usd=2000.0, fringes_pct=0.0, total_cost_usd=4000.0),
            AicpLineItemSpec(account_number="I-101", section=AicpSectionCode.SECTION_I, description="Cleanroom ESD Uniform Custom Tailoring", crew_tier=labor_tier, rate_basis="flat", units_count=1.0, unit_rate_usd=2000.0, fringes_pct=0.0, total_cost_usd=2000.0),
            AicpLineItemSpec(account_number="J-101", section=AicpSectionCode.SECTION_J, description="Clean Geometric Editorial & CAD Schematic Alignment", crew_tier=labor_tier, rate_basis="flat", units_count=1.0, unit_rate_usd=8000.0, fringes_pct=0.0, total_cost_usd=8000.0),
            AicpLineItemSpec(account_number="K-101", section=AicpSectionCode.SECTION_K, description="Minimalist Micro-Mechanical ASMR Foley & Resonant Sub-Bass Mix", crew_tier=labor_tier, rate_basis="flat", units_count=1.0, unit_rate_usd=5000.0, fringes_pct=0.0, total_cost_usd=5000.0),
            AicpLineItemSpec(account_number="L-101", section=AicpSectionCode.SECTION_L, description="Semiconductor Wafer Cryptomatte Pass & Clean Blue/White Grade", crew_tier=labor_tier, rate_basis="flat", units_count=1.0, unit_rate_usd=6000.0, fringes_pct=0.0, total_cost_usd=6000.0),
            AicpLineItemSpec(account_number="M-101", section=AicpSectionCode.SECTION_M, description="Cleanroom Equipment & Robotic System Liability Insurance", crew_tier=labor_tier, rate_basis="flat", units_count=1.0, unit_rate_usd=3000.0, fringes_pct=0.0, total_cost_usd=3000.0),
        ]

    elif "architectural" in domain_key:
        # Senior PM Spec: $120k - $210k -> Target Grand Total: $160,000 (Direct: $128,000)
        labor_tier = CrewLaborTier.TIER_COMMERCIAL_TIER_2
        days = 2
        brand = "Atelier Sanctuary Works"
        loc = "Brutalist Concrete Pavilion & Zen Water Sanctuary, Kyoto / Switzerland"
        line_items = [
            AicpLineItemSpec(account_number="A-101", section=AicpSectionCode.SECTION_A, description="Line Producer & Architectural Access Permits Supervisor", crew_tier=labor_tier, rate_basis="prep_wrap", units_count=4.0, unit_rate_usd=3000.0, fringes_pct=0.0, total_cost_usd=12000.0),
            AicpLineItemSpec(account_number="B-101", section=AicpSectionCode.SECTION_B, description="Director of Photography (Architectural & Natural Light Master)", crew_tier=labor_tier, rate_basis="day", units_count=2.0, unit_rate_usd=5500.0, fringes_pct=0.0, total_cost_usd=11000.0),
            AicpLineItemSpec(account_number="B-102", section=AicpSectionCode.SECTION_B, description="1st AC & Geometrical Lens Technician (Shift/Tilt Specialists)", crew_tier=labor_tier, rate_basis="day", units_count=2.0, unit_rate_usd=2500.0, fringes_pct=0.0, total_cost_usd=5000.0),
            AicpLineItemSpec(account_number="B-103", section=AicpSectionCode.SECTION_B, description="Gaffer & Bounce Board / Negative Fill Grips", crew_tier=labor_tier, rate_basis="day", units_count=2.0, unit_rate_usd=2500.0, fringes_pct=0.0, total_cost_usd=5000.0),
            AicpLineItemSpec(account_number="B-104", section=AicpSectionCode.SECTION_B, description="Key Grip & Heavy Precision Slider Dolly Operator", crew_tier=labor_tier, rate_basis="day", units_count=2.0, unit_rate_usd=2500.0, fringes_pct=0.0, total_cost_usd=5000.0),
            AicpLineItemSpec(account_number="B-105", section=AicpSectionCode.SECTION_B, description="DJI Inspire 3 Aerial Drone RPIC (Part 107 Compliant)", crew_tier=labor_tier, rate_basis="day", units_count=2.0, unit_rate_usd=3500.0, fringes_pct=0.0, total_cost_usd=7000.0),
            AicpLineItemSpec(account_number="B-106", section=AicpSectionCode.SECTION_B, description="DIT / ACES Photographic Colorist", crew_tier=labor_tier, rate_basis="day", units_count=2.0, unit_rate_usd=2500.0, fringes_pct=0.0, total_cost_usd=5000.0),
            AicpLineItemSpec(account_number="C-101", section=AicpSectionCode.SECTION_C, description="Pritzker Landmark Pavilion Location Fee & Drone Heritage Clearance", crew_tier=labor_tier, rate_basis="flat", units_count=1.0, unit_rate_usd=16000.0, fringes_pct=0.0, total_cost_usd=16000.0),
            AicpLineItemSpec(account_number="D-101", section=AicpSectionCode.SECTION_D, description="Minimalist Bronze Furnishings & Architectural Flora Styling", crew_tier=labor_tier, rate_basis="flat", units_count=1.0, unit_rate_usd=8000.0, fringes_pct=0.0, total_cost_usd=8000.0),
            AicpLineItemSpec(account_number="E-101", section=AicpSectionCode.SECTION_E, description="ARRI Alexa Mini LF & Arri Signature Prime / Tilt-Shift Lens Package", crew_tier=labor_tier, rate_basis="day", units_count=2.0, unit_rate_usd=12000.0, fringes_pct=0.0, total_cost_usd=24000.0),
            AicpLineItemSpec(account_number="F-101", section=AicpSectionCode.SECTION_F, description="Water Mirror Reflection Rig & Micro-Mist Atmosphere", crew_tier=labor_tier, rate_basis="flat", units_count=1.0, unit_rate_usd=4000.0, fringes_pct=0.0, total_cost_usd=4000.0),
            AicpLineItemSpec(account_number="G-101", section=AicpSectionCode.SECTION_G, description="Quiet Environmental Power Generation & Boutique Catering", crew_tier=labor_tier, rate_basis="day", units_count=2.0, unit_rate_usd=2000.0, fringes_pct=0.0, total_cost_usd=4000.0),
            AicpLineItemSpec(account_number="H-101", section=AicpSectionCode.SECTION_H, description="Solo Contemplative Figure Talent (SAG-AFTRA)", crew_tier=labor_tier, rate_basis="day", units_count=2.0, unit_rate_usd=2000.0, fringes_pct=0.0, total_cost_usd=4000.0),
            AicpLineItemSpec(account_number="I-101", section=AicpSectionCode.SECTION_I, description="Architectural Linen Garments & Custom Sandal Fittings", crew_tier=labor_tier, rate_basis="flat", units_count=1.0, unit_rate_usd=2000.0, fringes_pct=0.0, total_cost_usd=2000.0),
            AicpLineItemSpec(account_number="J-101", section=AicpSectionCode.SECTION_J, description="Contemplative Static Framing Editorial Assembly", crew_tier=labor_tier, rate_basis="flat", units_count=1.0, unit_rate_usd=6000.0, fringes_pct=0.0, total_cost_usd=6000.0),
            AicpLineItemSpec(account_number="K-101", section=AicpSectionCode.SECTION_K, description="Acoustic Room Impulse Response & Monastic Drone Soundscape", crew_tier=labor_tier, rate_basis="flat", units_count=1.0, unit_rate_usd=4000.0, fringes_pct=0.0, total_cost_usd=4000.0),
            AicpLineItemSpec(account_number="L-101", section=AicpSectionCode.SECTION_L, description="Pure Concrete Texture Preservation & Zen Neutral Color Grade", crew_tier=labor_tier, rate_basis="flat", units_count=1.0, unit_rate_usd=4000.0, fringes_pct=0.0, total_cost_usd=4000.0),
            AicpLineItemSpec(account_number="M-101", section=AicpSectionCode.SECTION_M, description="Architectural Heritage Site Preservation & Liability Insurance", crew_tier=labor_tier, rate_basis="flat", units_count=1.0, unit_rate_usd=2000.0, fringes_pct=0.0, total_cost_usd=2000.0),
        ]

    else:
        # Default Commercial Production Package
        labor_tier = CrewLaborTier.TIER_COMMERCIAL_TIER_1
        days = 2
        brand = "Global Commercial Advertiser"
        loc = "Universal Studios Soundstage, Los Angeles, CA"
        line_items = [
            AicpLineItemSpec(account_number="A-101", section=AicpSectionCode.SECTION_A, description="Executive Producer & Production Supervisor", crew_tier=labor_tier, rate_basis="prep_wrap", units_count=4.0, unit_rate_usd=3000.0, fringes_pct=0.0, total_cost_usd=12000.0),
            AicpLineItemSpec(account_number="B-101", section=AicpSectionCode.SECTION_B, description="Director of Photography & Camera Operators", crew_tier=labor_tier, rate_basis="day", units_count=2.0, unit_rate_usd=6000.0, fringes_pct=0.0, total_cost_usd=12000.0),
            AicpLineItemSpec(account_number="B-102", section=AicpSectionCode.SECTION_B, description="Lighting, Grip & Sound Technicians", crew_tier=labor_tier, rate_basis="day", units_count=2.0, unit_rate_usd=7500.0, fringes_pct=0.0, total_cost_usd=15000.0),
            AicpLineItemSpec(account_number="B-103", section=AicpSectionCode.SECTION_B, description="Aerial Drone Pilot & DIT Offload Specialist", crew_tier=labor_tier, rate_basis="day", units_count=2.0, unit_rate_usd=4500.0, fringes_pct=0.0, total_cost_usd=9000.0),
            AicpLineItemSpec(account_number="C-101", section=AicpSectionCode.SECTION_C, description="Studio Soundstage & City Filming Permits", crew_tier=labor_tier, rate_basis="flat", units_count=1.0, unit_rate_usd=14000.0, fringes_pct=0.0, total_cost_usd=14000.0),
            AicpLineItemSpec(account_number="D-101", section=AicpSectionCode.SECTION_D, description="Art Direction, Props & Wardrobe Package", crew_tier=labor_tier, rate_basis="flat", units_count=1.0, unit_rate_usd=10000.0, fringes_pct=0.0, total_cost_usd=10000.0),
            AicpLineItemSpec(account_number="E-101", section=AicpSectionCode.SECTION_E, description="Cinema Camera Package, Lighting Truck & Drone System", crew_tier=labor_tier, rate_basis="day", units_count=2.0, unit_rate_usd=11000.0, fringes_pct=0.0, total_cost_usd=22000.0),
            AicpLineItemSpec(account_number="F-101", section=AicpSectionCode.SECTION_F, description="Practical Effects & Stage Rigging", crew_tier=labor_tier, rate_basis="flat", units_count=1.0, unit_rate_usd=5000.0, fringes_pct=0.0, total_cost_usd=5000.0),
            AicpLineItemSpec(account_number="G-101", section=AicpSectionCode.SECTION_G, description="Production Expenses, Catering & Craft Services", crew_tier=labor_tier, rate_basis="day", units_count=2.0, unit_rate_usd=2500.0, fringes_pct=0.0, total_cost_usd=5000.0),
            AicpLineItemSpec(account_number="H-101", section=AicpSectionCode.SECTION_H, description="SAG-AFTRA Principal On-Camera Talent", crew_tier=labor_tier, rate_basis="day", units_count=2.0, unit_rate_usd=3000.0, fringes_pct=0.0, total_cost_usd=6000.0),
            AicpLineItemSpec(account_number="I-101", section=AicpSectionCode.SECTION_I, description="Talent Wardrobe Styling & Travel", crew_tier=labor_tier, rate_basis="flat", units_count=1.0, unit_rate_usd=3000.0, fringes_pct=0.0, total_cost_usd=3000.0),
            AicpLineItemSpec(account_number="J-101", section=AicpSectionCode.SECTION_J, description="Offline Editorial & Master Assembly", crew_tier=labor_tier, rate_basis="flat", units_count=1.0, unit_rate_usd=8000.0, fringes_pct=0.0, total_cost_usd=8000.0),
            AicpLineItemSpec(account_number="K-101", section=AicpSectionCode.SECTION_K, description="Diegetic Sound Design, Score & 5.1 Re-Recording Mix", crew_tier=labor_tier, rate_basis="flat", units_count=1.0, unit_rate_usd=6000.0, fringes_pct=0.0, total_cost_usd=6000.0),
            AicpLineItemSpec(account_number="L-101", section=AicpSectionCode.SECTION_L, description="3D LUT Color Grade & Flame Finishing", crew_tier=labor_tier, rate_basis="flat", units_count=1.0, unit_rate_usd=5000.0, fringes_pct=0.0, total_cost_usd=5000.0),
            AicpLineItemSpec(account_number="M-101", section=AicpSectionCode.SECTION_M, description="Production General Liability & Equipment Insurance", crew_tier=labor_tier, rate_basis="flat", units_count=1.0, unit_rate_usd=3000.0, fringes_pct=0.0, total_cost_usd=3000.0),
        ]

    top_sheet = calculate_aicp_top_sheet(line_items, production_fee_pct=15.0, contingency_pct=10.0)

    return MasterAicpBidSpec(
        project_title=title,
        client_brand=brand,
        agency_name="Omni Creative Partners",
        production_company="Omni Studio Productions",
        shoot_days_count=days,
        shoot_location=loc,
        currency="USD",
        labor_tier=labor_tier,
        line_items=line_items,
        top_sheet=top_sheet,
    )


def _normalize_domain_key(bible_or_domain: Union[MasterProductionBible, DomainArchetype, str]) -> str:
    """Resolve a MasterProductionBible, DomainArchetype, or raw string to one of the 6 domain keys."""
    if isinstance(bible_or_domain, MasterProductionBible):
        domain = bible_or_domain.domain_archetype or classify_brief_domain(
            f"{bible_or_domain.project_title} {bible_or_domain.logline}"
        )
    elif hasattr(bible_or_domain, "domain_archetype"):
        domain = getattr(bible_or_domain, "domain_archetype", "architectural_sanctuary") or "architectural_sanctuary"
    else:
        domain = bible_or_domain
    raw = str(domain.value if hasattr(domain, "value") else domain).lower()
    if "automotive" in raw:
        return "automotive_robotics"
    if "culinary" in raw or "asmr" in raw:
        return "culinary_asmr"
    if "luxury" in raw or "fashion" in raw:
        return "luxury_fashion"
    if "kinetic" in raw or "action" in raw:
        return "kinetic_action"
    if "hardware" in raw or "tech" in raw:
        return "tech_hardware"
    return "architectural_sanctuary"


_DOMAIN_REFRAME_CALIBRATIONS: Dict[str, Dict[str, Any]] = {
    "automotive_robotics": {
        "platforms": [
            SocialDeliveryPlatform.YOUTUBE_SHORTS_9X16,
            SocialDeliveryPlatform.REELS_9X16,
            SocialDeliveryPlatform.TIKTOK_9X16,
            SocialDeliveryPlatform.META_FEED_4X5,
            SocialDeliveryPlatform.CINEMA_239,
        ],
        "pan_mode": ReframePanMode.LINEAR_TRACK,
        "coi_x": 0.50,
        "coi_y": 0.48,
        "cta_endcard_sec": 2.5,
    },
    "culinary_asmr": {
        "platforms": [
            SocialDeliveryPlatform.TIKTOK_9X16,
            SocialDeliveryPlatform.REELS_9X16,
            SocialDeliveryPlatform.META_FEED_4X5,
            SocialDeliveryPlatform.YOUTUBE_SHORTS_9X16,
            SocialDeliveryPlatform.BROADCAST_TV,
        ],
        "pan_mode": ReframePanMode.STATIC_LOCK,
        "coi_x": 0.50,
        "coi_y": 0.48,
        "cta_endcard_sec": 2.0,
    },
    "luxury_fashion": {
        "platforms": [
            SocialDeliveryPlatform.REELS_9X16,
            SocialDeliveryPlatform.META_FEED_4X5,
            SocialDeliveryPlatform.TIKTOK_9X16,
            SocialDeliveryPlatform.CINEMA_239,
            SocialDeliveryPlatform.BROADCAST_TV,
        ],
        "pan_mode": ReframePanMode.EASE_IN_OUT_COI,
        "coi_x": 0.48,
        "coi_y": 0.44,
        "cta_endcard_sec": 2.5,
    },
    "kinetic_action": {
        "platforms": [
            SocialDeliveryPlatform.TIKTOK_9X16,
            SocialDeliveryPlatform.YOUTUBE_SHORTS_9X16,
            SocialDeliveryPlatform.REELS_9X16,
            SocialDeliveryPlatform.META_FEED_4X5,
            SocialDeliveryPlatform.BROADCAST_TV,
        ],
        "pan_mode": ReframePanMode.LINEAR_TRACK,
        "coi_x": 0.50,
        "coi_y": 0.46,
        "cta_endcard_sec": 2.0,
    },
    "tech_hardware": {
        "platforms": [
            SocialDeliveryPlatform.YOUTUBE_SHORTS_9X16,
            SocialDeliveryPlatform.META_FEED_4X5,
            SocialDeliveryPlatform.REELS_9X16,
            SocialDeliveryPlatform.TIKTOK_9X16,
            SocialDeliveryPlatform.BROADCAST_TV,
        ],
        "pan_mode": ReframePanMode.STATIC_LOCK,
        "coi_x": 0.50,
        "coi_y": 0.48,
        "cta_endcard_sec": 2.5,
    },
    "architectural_sanctuary": {
        "platforms": [
            SocialDeliveryPlatform.REELS_9X16,
            SocialDeliveryPlatform.META_FEED_4X5,
            SocialDeliveryPlatform.YOUTUBE_SHORTS_9X16,
            SocialDeliveryPlatform.TIKTOK_9X16,
            SocialDeliveryPlatform.CINEMA_239,
        ],
        "pan_mode": ReframePanMode.PILLARBOX_SAFE,
        "coi_x": 0.50,
        "coi_y": 0.46,
        "cta_endcard_sec": 2.5,
    },
}

_PLATFORM_TO_RATIO: Dict[SocialDeliveryPlatform, DeliverableAspectRatio] = {
    SocialDeliveryPlatform.BROADCAST_TV: DeliverableAspectRatio.RATIO_16_9,
    SocialDeliveryPlatform.TIKTOK_9X16: DeliverableAspectRatio.RATIO_9_16,
    SocialDeliveryPlatform.REELS_9X16: DeliverableAspectRatio.RATIO_9_16,
    SocialDeliveryPlatform.YOUTUBE_SHORTS_9X16: DeliverableAspectRatio.RATIO_9_16,
    SocialDeliveryPlatform.META_FEED_4X5: DeliverableAspectRatio.RATIO_4_5,
    SocialDeliveryPlatform.CINEMA_239: DeliverableAspectRatio.RATIO_2_39_1,
}


def get_domain_reframe_manifest(
    bible_or_domain: Union[MasterProductionBible, DomainArchetype, str],
    scenes: Optional[List[ScenePromptSpec]] = None,
) -> DeliveryReframeManifestSpec:
    """Calibrate multi-aspect social reframe, safe-zone crop windows, and cutdown timelines across all 6 domain archetypes (PM-FEAT-021)."""
    domain_key = _normalize_domain_key(bible_or_domain)
    cfg = _DOMAIN_REFRAME_CALIBRATIONS[domain_key]
    manifest = synthesize_default_reframe_manifest(bible_or_domain, scenes=scenes)
    platforms: List[SocialDeliveryPlatform] = list(cfg["platforms"])
    pan_mode: ReframePanMode = cfg["pan_mode"]
    coi_x: float = cfg["coi_x"]
    coi_y: float = cfg["coi_y"]

    manifest.target_platforms = platforms
    for sr in manifest.scene_reframes:
        sr.center_of_interest_x = coi_x
        sr.center_of_interest_y = coi_y
        sr.pan_mode = pan_mode
        if pan_mode in (ReframePanMode.STATIC_LOCK, ReframePanMode.PILLARBOX_SAFE):
            sr.pan_start_coi_x = coi_x
            sr.pan_end_coi_x = coi_x
        else:
            sr.pan_start_coi_x = max(0.0, round(coi_x - 0.04, 3))
            sr.pan_end_coi_x = min(1.0, round(coi_x + 0.04, 3))
        windows = [
            calculate_aspect_crop_window(
                target_aspect_ratio=_PLATFORM_TO_RATIO[plat],
                center_of_interest_x=coi_x,
                center_of_interest_y=coi_y,
                platform=plat,
                pan_mode=pan_mode,
            )
            for plat in platforms
        ]
        # Include 1:1 social square feed crop alongside primary platform deliverables
        windows.append(
            calculate_aspect_crop_window(
                target_aspect_ratio=DeliverableAspectRatio.RATIO_1_1,
                center_of_interest_x=coi_x,
                center_of_interest_y=coi_y,
                platform=SocialDeliveryPlatform.META_FEED_4X5,
                pan_mode=pan_mode,
            )
        )
        sr.crop_windows = windows
        sr.all_platforms_cleared = all(w.ui_clearance_ok for w in sr.crop_windows)
        sr.prompt_token = format_reframe_prompt_token(sr)

    for cut in manifest.cutdown_versions:
        cut.target_platform = platforms[0]
        cut.cta_endcard_sec = float(cfg["cta_endcard_sec"])

    manifest.safe_zone_audit_passed = all(sr.all_platforms_cleared for sr in manifest.scene_reframes)
    manifest.deliverable_matrix_count = sum(len(sr.crop_windows) for sr in manifest.scene_reframes)
    manifest.prompt_token = format_reframe_prompt_token(manifest)
    return manifest


_DOMAIN_BROADCAST_QC_CALIBRATIONS: Dict[str, Dict[str, Any]] = {
    "automotive_robotics": {
        "standard": BroadcastLoudnessStandard.ATSC_A85,
        "ad_id_prefix": "AUTO",
        "audio_config": "Stereo L/R + 5.1 Surround (ATSC A/85)",
        "codec_profile": "Apple ProRes 422 HQ / XDCAM HD422 50Mbps",
        "legal_disclaimer": True,
        "territory": "North America Broadcast + Global Paid Digital",
    },
    "culinary_asmr": {
        "standard": BroadcastLoudnessStandard.EBU_R128,
        "ad_id_prefix": "CULN",
        "audio_config": "Binaural Stereo L/R + 5.1 ASMR Bed (EBU R128)",
        "codec_profile": "Apple ProRes 422 HQ 10-bit Rec.709",
        "legal_disclaimer": False,
        "territory": "North America, EMEA & APAC Broadcast + Social",
    },
    "luxury_fashion": {
        "standard": BroadcastLoudnessStandard.EBU_R128,
        "ad_id_prefix": "LUXF",
        "audio_config": "Stereo L/R + 7.1.4 Cinema Master (EBU R128)",
        "codec_profile": "Apple ProRes 4444 XQ / DCP-Ready",
        "legal_disclaimer": False,
        "territory": "Worldwide Flagship, Broadcast & EMEA Cinema",
    },
    "kinetic_action": {
        "standard": BroadcastLoudnessStandard.ATSC_A85,
        "ad_id_prefix": "KINT",
        "audio_config": "Stereo L/R + 5.1 Ambisonic Surround (ATSC A/85)",
        "codec_profile": "Apple ProRes 422 HQ / Broadcast MXF OP1a",
        "legal_disclaimer": True,
        "territory": "Global Broadcast, Stadium & Paid Social",
    },
    "tech_hardware": {
        "standard": BroadcastLoudnessStandard.EBU_R128,
        "ad_id_prefix": "TECH",
        "audio_config": "Stereo L/R + 5.1 Precision Stem (EBU R128)",
        "codec_profile": "Apple ProRes 422 HQ / Keynote 4K60 Master",
        "legal_disclaimer": False,
        "territory": "Worldwide Product Launch, OTT & Keynote",
    },
    "architectural_sanctuary": {
        "standard": BroadcastLoudnessStandard.EBU_R128,
        "ad_id_prefix": "ARCH",
        "audio_config": "B-Format Ambisonic + Stereo L/R (EBU R128)",
        "codec_profile": "Apple ProRes 422 HQ / EBU R103 Broadcast",
        "legal_disclaimer": False,
        "territory": "Global Broadcast, Museum & Architectural Press",
    },
}


def get_domain_broadcast_qc_spec(
    bible_or_domain: Union[MasterProductionBible, DomainArchetype, str],
    scenes: Optional[List[ScenePromptSpec]] = None,
) -> MasterBroadcastQcSpec:
    """Calibrate Broadcast QC, PSE flash-safety, loudness compliance, and rights clearances across all 6 domain archetypes (PM-FEAT-022)."""
    domain_key = _normalize_domain_key(bible_or_domain)
    cfg = _DOMAIN_BROADCAST_QC_CALIBRATIONS[domain_key]
    spec = synthesize_default_broadcast_qc_spec(
        bible_or_domain,
        scenes=scenes,
        standard=cfg["standard"],
    )
    spec.trafficking_slate.ad_id_isci = f"OMNI{cfg['ad_id_prefix']}{spec.trafficking_slate.spot_length_sec:02d}H"
    spec.trafficking_slate.audio_config = cfg["audio_config"]
    spec.trafficking_slate.video_codec_profile = cfg["codec_profile"]
    spec.trafficking_slate.legal_disclaimer_required = bool(cfg["legal_disclaimer"])
    for rec in spec.clearance_records:
        rec.territory = cfg["territory"]
    spec.prompt_token = format_broadcast_qc_prompt_token(spec)
    return spec


_DOMAIN_CONTINUITY_CALIBRATIONS: Dict[str, Dict[str, Any]] = {
    "culinary_asmr": {
        "screen_direction": ScreenDirection.STATIC_CENTERED,
        "axis_side": "A_SIDE",
        "master_axis_deg": 0.0,
        "shot_scales": [ShotScaleSize.MS, ShotScaleSize.MCU, ShotScaleSize.CU, ShotScaleSize.ECU],
        "cut_type_followup": EditorialCutType.MATCH_ON_ACTION,
        "aim_azimuths": [90.0, 56.0, 122.0, 88.0],
        "focal_lengths": [50, 65, 85, 100],
        "eyeline_deg": 0.0,
        "stage_width": 4.5,
        "stage_depth": 3.5,
        "cam_height": 1.25,
        "cam_distances": [1.8, 1.5, 1.2, 0.9],
        "kelvin": 3600,
        "default_scene_titles": [
            "Tabletop Mise-en-Place",
            "Artisan Prep & Heat",
            "Tactile Pour & Glaze",
            "Hero Garnish & Steam",
        ],
        "primary_entity": ("Chef Prep Hands", "talent", -0.4, 0.1, 0.0, 0.0, 0.0, "#38BDF8"),
        "anchor_entity": ("Hero Culinary Plating Dish", "hero_product", 0.3, 0.4, 180.0, 0.0, 0.0, "#F59E0B"),
        "notes_label": "Tabletop locked A-side axis",
    },
    "automotive_robotics": {
        "screen_direction": ScreenDirection.LEFT_TO_RIGHT,
        "axis_side": "A_SIDE",
        "master_axis_deg": 0.0,
        "shot_scales": [ShotScaleSize.EWS, ShotScaleSize.WS, ShotScaleSize.MLS, ShotScaleSize.MS],
        "cut_type_followup": EditorialCutType.MATCH_ON_ACTION,
        "aim_azimuths": [64.0, 98.0, 60.0, 102.0],
        "focal_lengths": [24, 28, 35, 50],
        "eyeline_deg": 15.0,
        "stage_width": 24.0,
        "stage_depth": 14.0,
        "cam_height": 1.1,
        "cam_distances": [5.2, 4.2, 3.4, 2.8],
        "kelvin": 5600,
        "default_scene_titles": [
            "Rolling Telemetry Ignition",
            "Lateral Pursuit Acceleration",
            "Robotic Chassis Apex",
            "Wet Tarmac Horizon Lock",
        ],
        "primary_entity": ("Autonomous Hypercar Chassis", "vehicle", -2.4, 0.5, 0.0, 4.2, 0.0, "#38BDF8"),
        "anchor_entity": ("Russian Arm Pursuit Rig", "prop", -3.2, -1.8, 0.0, 4.2, 0.0, "#F59E0B"),
        "notes_label": "Lateral left-to-right pursuit vector",
    },
    "luxury_fashion": {
        "screen_direction": ScreenDirection.TOWARD_CAMERA,
        "axis_side": "A_SIDE",
        "master_axis_deg": 0.0,
        "shot_scales": [ShotScaleSize.MCU, ShotScaleSize.CU, ShotScaleSize.MCU, ShotScaleSize.CU],
        "cut_type_followup": EditorialCutType.EYELINE_CUT,
        "aim_azimuths": [90.0, 56.0, 122.0, 88.0],
        "focal_lengths": [65, 85, 50, 85],
        "eyeline_deg": 0.0,
        "stage_width": 10.0,
        "stage_depth": 8.0,
        "cam_height": 1.55,
        "cam_distances": [2.2, 1.7, 2.2, 1.7],
        "kelvin": 4800,
        "default_scene_titles": [
            "Symmetrical Runway Approach",
            "Couture Eyeline Close-Up",
            "Flagship Corridor Stride",
            "Climactic Hero Silhouette",
        ],
        "primary_entity": ("Lead Runway Talent", "talent", 0.0, 0.2, 270.0, 0.0, 1.1, "#38BDF8"),
        "anchor_entity": ("Hero Couture Accessory", "hero_product", 0.5, 0.6, 270.0, 0.0, 0.0, "#F59E0B"),
        "notes_label": "Symmetrical eyeline MCU->CU progression",
    },
    "kinetic_action": {
        "screen_direction": ScreenDirection.LEFT_TO_RIGHT,
        "axis_side": "A_SIDE",
        "master_axis_deg": 0.0,
        "shot_scales": [ShotScaleSize.WS, ShotScaleSize.MS, ShotScaleSize.MCU, ShotScaleSize.CU],
        "cut_type_followup": EditorialCutType.MATCH_ON_ACTION,
        "aim_azimuths": [56.0, 92.0, 126.0, 74.0],
        "focal_lengths": [28, 35, 50, 85],
        "eyeline_deg": 15.0,
        "stage_width": 16.0,
        "stage_depth": 12.0,
        "cam_height": 1.4,
        "cam_distances": [4.0, 3.0, 2.2, 1.8],
        "kelvin": 5200,
        "default_scene_titles": [
            "Kinetic Launch & Vector",
            "Match-on-Action Drive",
            "Aerodynamic Peak Tension",
            "Impact Lock & Settle",
        ],
        "primary_entity": ("Kinetic Athlete / Performer", "talent", -1.4, 0.2, 0.0, 2.6, 0.0, "#38BDF8"),
        "anchor_entity": ("Technical Impact Anchor", "hero_product", 1.6, 0.5, 180.0, 0.0, 0.0, "#F59E0B"),
        "notes_label": "Dynamic match-on-action axis",
    },
    "tech_hardware": {
        "screen_direction": ScreenDirection.STATIC_CENTERED,
        "axis_side": "A_SIDE",
        "master_axis_deg": 0.0,
        "shot_scales": [ShotScaleSize.MS, ShotScaleSize.MCU, ShotScaleSize.CU, ShotScaleSize.ECU],
        "cut_type_followup": EditorialCutType.MATCH_ON_ACTION,
        "aim_azimuths": [55.0, 89.0, 123.0, 72.0],
        "focal_lengths": [50, 65, 85, 100],
        "eyeline_deg": 0.0,
        "stage_width": 6.0,
        "stage_depth": 6.0,
        "cam_height": 1.35,
        "cam_distances": [2.4, 1.9, 1.5, 1.1],
        "kelvin": 6000,
        "default_scene_titles": [
            "Cleanroom Chassis Reveal",
            "Orbital Chamfer Sweep",
            "Precision Hinge Articulation",
            "Silicon Macro Specular",
        ],
        "primary_entity": ("Anodized Hardware Flagship", "hero_product", 0.0, 0.3, 270.0, 0.0, 0.0, "#38BDF8"),
        "anchor_entity": ("Precision Moco Turntable", "prop", 0.0, -0.4, 90.0, 0.0, 0.0, "#F59E0B"),
        "notes_label": "Cleanroom precision orbital axis",
    },
    "architectural_sanctuary": {
        "screen_direction": ScreenDirection.TOWARD_CAMERA,
        "axis_side": "A_SIDE",
        "master_axis_deg": 0.0,
        "shot_scales": [ShotScaleSize.WS, ShotScaleSize.MLS, ShotScaleSize.MS, ShotScaleSize.MCU],
        "cut_type_followup": EditorialCutType.HARD_CUT,
        "aim_azimuths": [90.0, 56.0, 122.0, 88.0],
        "focal_lengths": [24, 35, 50, 65],
        "eyeline_deg": 0.0,
        "stage_width": 14.0,
        "stage_depth": 10.0,
        "cam_height": 1.5,
        "cam_distances": [4.2, 3.3, 2.6, 2.0],
        "kelvin": 5400,
        "default_scene_titles": [
            "Wide Spatial Sanctuary",
            "Architectural Daylight Reveal",
            "Medium Material Harmony",
            "Tactile Sanctuary Anchor",
        ],
        "primary_entity": ("Sanctuary Architectural Anchor", "hero_product", 0.0, 0.8, 270.0, 0.0, 0.0, "#F59E0B"),
        "anchor_entity": ("Bespoke Interior Element", "prop", -1.0, 0.2, 0.0, 0.0, 0.6, "#38BDF8"),
        "notes_label": "Architectural wide-to-medium axial reveal",
    },
}


def get_domain_continuity_blocking_spec(
    bible_or_domain: Union[MasterProductionBible, DomainArchetype, str],
    scenes: Optional[List[ScenePromptSpec]] = None,
    project_title: str = "Omni Production",
) -> MasterContinuityBlockingSpec:
    """Calibrate 180-degree axis lock, shot scale progression, screen direction, and blocking entities across all 6 domain archetypes (PM-FEAT-023)."""
    domain_key = _normalize_domain_key(bible_or_domain)
    cfg = _DOMAIN_CONTINUITY_CALIBRATIONS[domain_key]

    if isinstance(bible_or_domain, MasterProductionBible):
        eff_title = bible_or_domain.project_title if project_title == "Omni Production" else project_title
        eff_scenes: List[Optional[ScenePromptSpec]] = list(scenes if scenes is not None else (bible_or_domain.scenes or []))
        is_mode_b = bible_or_domain.storytelling_mode == StorytellingMode.MODE_B_CONTINUOUS_CHAIN
    else:
        eff_title = project_title
        eff_scenes = list(scenes) if scenes is not None else []
        is_mode_b = False

    if not eff_scenes:
        eff_scenes = [None] * len(cfg["default_scene_titles"])

    screen_dir: ScreenDirection = cfg["screen_direction"]
    axis_side: str = cfg["axis_side"]
    axis_deg: float = float(cfg["master_axis_deg"])
    eyeline_deg: float = float(cfg["eyeline_deg"])
    base_kelvin: int = int(cfg["kelvin"])

    blockings: List[SceneBlockingSpec] = []
    prev_kelvin: Optional[int] = None

    for idx, sc in enumerate(eff_scenes, start=1):
        slot = (idx - 1) % len(cfg["shot_scales"])
        eff_idx = sc.scene_index if sc is not None else idx
        eff_scene_title = (
            (sc.scene_title if sc is not None and sc.scene_title else None)
            or cfg["default_scene_titles"][(idx - 1) % len(cfg["default_scene_titles"])]
        )
        shot_scale: ShotScaleSize = cfg["shot_scales"][slot]
        aim_deg: float = float(cfg["aim_azimuths"][slot])
        focal_mm = (
            int(getattr(sc.craft_camera, "focal_length_mm", 0) or 0)
            if sc is not None and getattr(sc, "craft_camera", None) is not None
            else 0
        ) or int(cfg["focal_lengths"][slot])
        fov_deg = round(math.degrees(2.0 * math.atan(36.0 / (2.0 * max(8.0, float(focal_mm))))), 1)

        is_ext = bool(
            is_mode_b
            or (
                sc is not None
                and re.search(r"\+10s|extension", getattr(sc, "timestamp_range", "") or "", re.IGNORECASE)
            )
        )
        if idx == 1:
            cut_in = EditorialCutType.HARD_CUT
        elif is_ext:
            cut_in = EditorialCutType.CONTINUOUS_EXTENSION
        else:
            cut_in = cfg["cut_type_followup"]

        # Resolve Kelvin while guaranteeing <= 1500K continuity across cuts
        scene_kelvin = base_kelvin
        if sc is not None:
            lighting = getattr(sc, "lighting_rig", None)
            if lighting is not None and getattr(lighting, "fixtures", None):
                k_vals = [
                    float(k)
                    for f in lighting.fixtures
                    for k in (getattr(f, "cct_kelvin", getattr(f, "color_temp_k", None)),)
                    if k is not None
                ]
                if k_vals:
                    scene_kelvin = int(round(sum(k_vals) / len(k_vals)))
            else:
                m_k = re.search(r"\b(\d{4})K\b", getattr(sc, "omni_prose_prompt", "") or "")
                if m_k:
                    parsed_k = int(m_k.group(1))
                    if 2000 <= parsed_k <= 12000:
                        scene_kelvin = parsed_k
        if prev_kelvin is not None and abs(scene_kelvin - prev_kelvin) > 1500:
            scene_kelvin = prev_kelvin + (1200 if scene_kelvin > prev_kelvin else -1200)
        prev_kelvin = scene_kelvin

        rad = math.radians(aim_deg)
        cam_dist = float(cfg["cam_distances"][slot])
        cam_x = round(-cam_dist * math.cos(rad), 2)
        cam_y = round(-abs(cam_dist * math.sin(rad)) - 0.5, 2)

        p_label, p_role, px, py, pface, pdx, pdy, phex = cfg["primary_entity"]
        a_label, a_role, ax, ay, aface, adx, ady, ahex = cfg["anchor_entity"]
        entities = [
            StageBlockingEntity(
                entity_id=f"{domain_key}_primary_s{eff_idx}",
                label=p_label,
                role=p_role,
                x_meters=float(px),
                y_meters=float(py),
                facing_deg=float(pface),
                eyeline_deg=eyeline_deg,
                motion_dx_meters=float(pdx),
                motion_dy_meters=float(pdy),
                screen_direction=screen_dir,
                color_hex=phex,
            ),
            StageBlockingEntity(
                entity_id=f"{domain_key}_anchor_s{eff_idx}",
                label=a_label,
                role=a_role,
                x_meters=float(ax),
                y_meters=float(ay),
                facing_deg=float(aface),
                eyeline_deg=-eyeline_deg if eyeline_deg else 0.0,
                motion_dx_meters=float(adx),
                motion_dy_meters=float(ady),
                screen_direction=ScreenDirection.STATIC_CENTERED if adx == 0.0 and ady == 0.0 else screen_dir,
                color_hex=ahex,
            ),
        ]

        cam = CameraAxisPlacement(
            camera_id=f"CAM_{domain_key[:4].upper()}_S{eff_idx}",
            x_meters=cam_x,
            y_meters=cam_y,
            aim_azimuth_deg=round(aim_deg, 1),
            fov_deg=fov_deg,
            focal_length_mm=focal_mm,
            axis_side=axis_side,
            axis_angle_deg=axis_deg,
            height_meters=float(cfg["cam_height"]),
        )

        blk = SceneBlockingSpec(
            scene_index=eff_idx,
            scene_title=eff_scene_title,
            screen_direction=screen_dir,
            shot_scale=shot_scale,
            cut_type_in=cut_in,
            line_of_action_deg=axis_deg,
            axis_side=axis_side,
            eyeline_angle_deg=eyeline_deg,
            one_eighty_lock_ok=True,
            color_temp_kelvin=scene_kelvin,
            stage_width_meters=float(cfg["stage_width"]),
            stage_depth_meters=float(cfg["stage_depth"]),
            camera=cam,
            entities=entities,
            blocking_notes=(
                f"{cfg['notes_label']} ({domain_key}): {axis_side} at {aim_deg:.0f}deg, "
                f"{shot_scale.value} ({focal_mm}mm), dir={screen_dir.value}."
            ),
        )
        blk.prompt_token = format_continuity_prompt_token(blk)
        blockings.append(blk)

    cut_checks: List[InterSceneCutCheckSpec] = []
    for i in range(len(blockings) - 1):
        chk = evaluate_180_axis_and_30_rule(
            blockings[i],
            blockings[i + 1],
            prev_kelvin=blockings[i].color_temp_kelvin,
            next_kelvin=blockings[i + 1].color_temp_kelvin,
        )
        cut_checks.append(chk)

    axis_violations_count = sum(len(c.violations) for c in cut_checks)
    warnings_count = sum(len(c.warnings) for c in cut_checks)
    all_180 = all(b.one_eighty_lock_ok for b in blockings) and all(c.axis_preserved for c in cut_checks)
    all_30 = all(c.thirty_degree_rule_ok for c in cut_checks)
    all_kelvin = all(c.kelvin_continuity_ok for c in cut_checks)
    continuity_passed = all_180 and all_30 and all_kelvin and axis_violations_count == 0
    overall_continuity_score = round(
        max(0.0, 100.0 - (15.0 * axis_violations_count) - (2.0 * warnings_count)),
        2,
    )

    manifest = MasterContinuityBlockingSpec(
        project_title=eff_title,
        dominant_screen_direction=screen_dir,
        master_axis_deg=axis_deg,
        master_axis_side=axis_side,
        scene_blockings=blockings,
        cut_checks=cut_checks,
        all_180_axis_locked=all_180,
        all_30_rule_passed=all_30,
        all_kelvin_continuous=all_kelvin,
        continuity_passed=continuity_passed,
        overall_continuity_score=overall_continuity_score,
        axis_violations_count=axis_violations_count,
    )
    manifest.prompt_token = format_continuity_prompt_token(manifest)
    return manifest


_DOMAIN_CLIENT_REVIEW_CALIBRATIONS: Dict[str, Dict[str, Any]] = {
    "culinary_asmr": {
        "signoff_by": "Culinary Director & Brand Producer",
        "annotations": [
            (ReviewerRole.DIRECTOR, "Lead Creative Director", "lighting", 0.50, 0.44, "Warm 3600K tungsten key and tactile steam specular highlights verified for appetite appeal."),
            (ReviewerRole.AGENCY_CREATIVE, "Agency Creative Lead", "audio", 0.48, 0.52, "Binaural ASMR sizzle, ceramic clink, and room tone floor verified clean."),
            (ReviewerRole.CLIENT_BRAND, "Brand Creative Lead", "framing", 0.52, 0.46, "Hero dish plating centered in tabletop A-side frame; garnish and packaging legible."),
            (ReviewerRole.POST_PRODUCER, "Finishing Post Producer", "pacing", 0.50, 0.50, "1.0x real-time pour physics and match-on-action cadence signed off."),
        ],
    },
    "automotive_robotics": {
        "signoff_by": "Automotive Director & OEM Brand Lead",
        "annotations": [
            (ReviewerRole.DIRECTOR, "Lead Creative Director", "camera", 0.46, 0.50, "Russian Arm lateral left-to-right pursuit velocity and low-angle horizon lock verified."),
            (ReviewerRole.VFX_SUPERVISOR, "Senior VFX Supervisor", "lighting", 0.54, 0.48, "Raytraced wet tarmac neon reflections and carbon-fiber chassis speculars cleared."),
            (ReviewerRole.CLIENT_BRAND, "OEM Brand Lead", "framing", 0.50, 0.44, "Hero vehicle badge emblem and aerodynamic silhouette clear of social safe-zone HUD margins."),
            (ReviewerRole.AGENCY_CREATIVE, "Agency Creative Lead", "audio", 0.50, 0.54, "Electric torque whine and pneumatic servo transient sync approved for broadcast."),
        ],
    },
    "luxury_fashion": {
        "signoff_by": "Fashion Director & Maison Brand Lead",
        "annotations": [
            (ReviewerRole.DIRECTOR, "Lead Creative Director", "framing", 0.48, 0.40, "Symmetrical eyeline MCU-to-CU progression and 2x anamorphic oval bokeh approved."),
            (ReviewerRole.CLIENT_BRAND, "Maison Brand Director", "wardrobe", 0.52, 0.46, "Hero couture textile sheen and signature brand silhouette verified on talent."),
            (ReviewerRole.AGENCY_CREATIVE, "Agency Creative Lead", "lighting", 0.50, 0.42, "High-contrast key-to-fill edge separation and skin-tone highlight rolloff cleared."),
            (ReviewerRole.POST_PRODUCER, "Finishing Post Producer", "pacing", 0.50, 0.50, "Runway stride inertia and freeze-frame hero product lock signed off."),
        ],
    },
    "kinetic_action": {
        "signoff_by": "Action Director & Global Brand Producer",
        "annotations": [
            (ReviewerRole.DIRECTOR, "Lead Creative Director", "pacing", 0.50, 0.48, "1.0x real-time kinetic contact chain and match-on-action axis continuity verified."),
            (ReviewerRole.VFX_SUPERVISOR, "Senior VFX Supervisor", "camera", 0.46, 0.46, "90-degree shutter motion clarity and aerodynamic streamline particles cleared."),
            (ReviewerRole.AGENCY_CREATIVE, "Agency Creative Lead", "audio", 0.52, 0.52, "Transient impact foley punch and percussive score lock verified at -24 LKFS."),
            (ReviewerRole.CLIENT_BRAND, "Brand Creative Lead", "framing", 0.50, 0.44, "Performance textile tension and hero brand mark legible across all social crops."),
        ],
    },
    "tech_hardware": {
        "signoff_by": "Hardware Industrial Director & Product Lead",
        "annotations": [
            (ReviewerRole.DIRECTOR, "Lead Creative Director", "lighting", 0.50, 0.46, "Cleanroom 6000K precision rim highlight across chamfered metal edges verified."),
            (ReviewerRole.CLIENT_BRAND, "Hardware Product Lead", "framing", 0.50, 0.48, "Hero industrial design proportions and display UI sharpness signed off."),
            (ReviewerRole.VFX_SUPERVISOR, "Senior VFX Supervisor", "camera", 0.48, 0.50, "Orbital motion-control sweep and zero optical distortion on rectilinear lines cleared."),
            (ReviewerRole.AGENCY_CREATIVE, "Agency Creative Lead", "audio", 0.50, 0.52, "Precision mechanical hinge click and minimalist tonal pulse approved."),
        ],
    },
    "architectural_sanctuary": {
        "signoff_by": "Architectural Director & Brand Producer",
        "annotations": [
            (ReviewerRole.DIRECTOR, "Lead Creative Director", "framing", 0.50, 0.46, "Architectural wide-to-medium axial reveal and plumb vertical perspective verified."),
            (ReviewerRole.AGENCY_CREATIVE, "Agency Creative Lead", "lighting", 0.44, 0.48, "Daylight shaft balance across pale ash flooring and matte limewashed walls approved."),
            (ReviewerRole.CLIENT_BRAND, "Brand Creative Lead", "wardrobe", 0.54, 0.50, "Bespoke furniture geometry, textile drape, and brand color palette fidelity signed off."),
            (ReviewerRole.POST_PRODUCER, "Finishing Post Producer", "audio", 0.50, 0.52, "Acoustic room-tone transition from resonant space to dampened sanctuary cleared."),
        ],
    },
}


def get_domain_client_review_spec(
    bible_or_domain: Union[MasterProductionBible, DomainArchetype, str],
    scenes: Optional[List[ScenePromptSpec]] = None,
    project_title: str = "Omni Production",
) -> MasterClientReviewSpec:
    """Calibrate domain-specific director/agency/client pin annotations and resolved approval signoff gate across all 6 domain archetypes (PM-FEAT-024)."""
    domain_key = _normalize_domain_key(bible_or_domain)
    cfg = _DOMAIN_CLIENT_REVIEW_CALIBRATIONS[domain_key]
    cont_cfg = _DOMAIN_CONTINUITY_CALIBRATIONS[domain_key]

    if isinstance(bible_or_domain, MasterProductionBible):
        eff_title = bible_or_domain.project_title if project_title == "Omni Production" else project_title
        eff_scenes: List[Optional[ScenePromptSpec]] = list(scenes if scenes is not None else (bible_or_domain.scenes or []))
        total_runtime = float(bible_or_domain.total_runtime_seconds or 32)
    else:
        eff_title = project_title
        eff_scenes = list(scenes) if scenes is not None else []
        total_runtime = 32.0

    if not eff_scenes:
        eff_scenes = [None] * len(cont_cfg["default_scene_titles"])

    fps = 24
    total_scenes = max(1, len(eff_scenes))
    per_scene_sec = max(2.0, total_runtime / total_scenes)
    scene_reviews: List[SceneReviewSignoffSpec] = []

    for idx, sc in enumerate(eff_scenes, start=1):
        eff_idx = sc.scene_index if sc is not None else idx
        eff_scene_title = (
            (sc.scene_title if sc is not None and sc.scene_title else None)
            or cont_cfg["default_scene_titles"][(idx - 1) % len(cont_cfg["default_scene_titles"])]
        )

        start_s = (idx - 1) * per_scene_sec
        end_s = idx * per_scene_sec
        if sc is not None and getattr(sc, "timestamp_range", None):
            m = re.search(r"(\d+):(\d+)\s*[-–—]\s*(\d+):(\d+)", sc.timestamp_range)
            if m:
                m1, s1, m2, s2 = map(int, m.groups())
                cand_s = float(m1 * 60 + s1)
                cand_e = float(m2 * 60 + s2)
                if cand_e > cand_s:
                    start_s, end_s = cand_s, cand_e

        mid_s = round(start_s + max(0.5, (end_s - start_s) * 0.4), 2)
        frame_num = max(0, int(round(mid_s * fps)))
        tc_smpte = format_smpte12m_timecode(frame_num, fps=fps)

        role, reviewer_name, param, px, py, comment = cfg["annotations"][(idx - 1) % len(cfg["annotations"])]
        note = ReviewAnnotationSpec(
            note_id=f"REV-{domain_key[:4].upper()}-S{eff_idx:02d}-01",
            scene_index=eff_idx,
            timecode_smpte=tc_smpte,
            timecode_sec=mid_s,
            frame_number=frame_num,
            reviewer_role=role,
            reviewer_name=reviewer_name,
            marker_color=MarkerColorTag.GREEN,
            comment=comment,
            target_parameter=param,
            resolved=True,
            blocking_gate=False,
            pin=ReviewPinCoordinate(x_norm=float(px), y_norm=float(py), radius_norm=0.06),
        )
        note.compiled_edit_delta = compile_review_note_to_delta(note, sc)

        sr = SceneReviewSignoffSpec(
            scene_index=eff_idx,
            scene_title=eff_scene_title,
            revision=1,
            approval_status=ReviewApprovalStatus.APPROVED,
            annotations=[note],
            open_notes_count=0,
            resolved_notes_count=1,
            signoff_by=cfg["signoff_by"],
        )
        sr.prompt_token = format_review_prompt_token(sr)
        scene_reviews.append(sr)

    total_notes = sum(len(sr.annotations) for sr in scene_reviews)
    manifest = MasterClientReviewSpec(
        project_title=eff_title,
        revision=1,
        overall_status=ReviewApprovalStatus.APPROVED,
        overall_approval_status=ReviewApprovalStatus.APPROVED,
        scene_reviews=scene_reviews,
        total_notes_count=total_notes,
        open_notes_count=0,
        blocking_notes_count=0,
        unresolved_blockers=0,
        ready_for_live_render=True,
        signoff_summary=(
            f"Revision 1 approved across {len(scene_reviews)} scene(s) ({domain_key}); "
            "all stakeholder pin annotations resolved and live render gate cleared."
        ),
    )
    manifest.prompt_token = format_review_prompt_token(manifest)
    return manifest


DOMAINS_6: List[str] = list(DOMAIN_ARCHETYPES.keys())


# 1. IKEA ASMR Golden Preset
IKEA_ASMR_BIBLE = MasterProductionBible(
    project_title="IKEA: The Living Room Unfolds",
    logline="In an empty sunlit Scandinavian apartment, an iconic flat-pack IKEA box violently trembles, then mechanically unpacks and self-assembles into a pristine, serene living sanctuary with hyper-tactile ASMR foley.",
    creative_regime=RegimeType.REGIME_2_KINETIC,
    storytelling_mode=StorytellingMode.MODE_A_PARALLEL_CUT,
    aspect_ratio=AspectRatio.RATIO_16_9,
    total_runtime_seconds=32,
    color_palette=["#1E293B", "#F59E0B", "#0284C7", "#F8FAFC"],
    characters=[],
    environment=MasterEnvironmentSpec(
        location_name="Minimalist Stockholm Loft",
        spatial_architecture="An expansive 8x6 meter open-plan apartment with ultra-smooth pale blonde ash hardwood floors, matte-white limewashed walls, and floor-to-ceiling multi-pane Nordic windows on the left wall looking out to quiet birch trees.",
        lighting_setup="Soft, low-angled morning Scandinavian sunlight streaming through the windows at 5200K daylight balance, casting elongated warm rectangular light pools across the floor, filled with soft 6500K ambient room bounce.",
        atmospheric_particles="Delicate, slow-drifting micro-motes of atmospheric dust illuminated in the light beam; zero haze, zero smoke.",
        positive_invariants=[
            "The pale blonde ash floorboards remain mechanically rigid with realistic wood grain that never distorts or changes direction.",
            "The walls remain pristine matte-white with consistent architectural baseboards.",
            "All furniture pieces retain exact Scandinavian minimalist geometry and color-true IKEA fabrics once assembled."
        ]
    ),
    camera_rig=CraftCameraSpec(
        rig_type="Locked-off Studio Tripod on 35mm Prime Lens",
        focal_length_mm=35,
        composition="Wide-angle eye-level architectural framing showing 80% of the room with the flat-pack box dead-center.",
        route="Completely locked-off static camera for the entire duration with zero drift, zero pan, and zero handheld shake.",
        action_anchor="Static frame holds observational discipline while hyper-kinetic assembly erupts within it.",
        focus_axis="Deep f/8 depth of field keeping the center box and back walls tack-sharp.",
        tone_rig="High-end architectural photography."
    ),
    sonic_blueprint=DiegeticSonicSpec(
        foley_cues=[
            "Low resonant cardboard vibration on wood floor",
            "Sharp, satisfying high-frequency tape tear and cardboard seam pop",
            "Crisp wood dowel clicks, rapid mechanical drawer slide swooshes, and solid pine locking thuds",
            "Soft, airy, deep 'fwoomp' of down-filled textiles settling onto wood",
            "Pristine, dead-silent room tone with gentle morning bird chirps outside glass"
        ],
        dialogue_lines=[],
        room_acoustics="Bright, reverberant empty wooden room acoustics during the initial box opening, transitioning smoothly into a warm, dampened, acoustically insulated soundscape as fabrics, rugs, and cushions populate the space."
    ),
    master_bgm=MasterBgmSpec(
        track_title="Nordic Serenity: Tactile Pulse",
        genre_style="Minimalist Acoustic Neo-Classical ASMR",
        tempo_bpm=84,
        key_signature="D Major",
        instrumentation=[
            "Plucked acoustic cello pizzicato",
            "Felted upright piano playing delicate sparse arpeggios",
            "Subtle wooden xylophone clicks tuned to foley impacts",
            "Warm analog sub-bass drone resolving into absolute stillness"
        ],
        dynamic_arc="Seconds 00-08: Tense, playful pizzicato rhythm ticking like a clockwork box. Seconds 08-16: Rapid, polyrhythmic wooden mallet pulses synchronizing with furniture clicks. Seconds 16-24: Swelling warm cello and piano harmony. Seconds 24-32: All music decrescendos instantly on the final blanket drop, leaving only a sustained pure piano chord and serene silence.",
        lyria_prompt="Minimalist Scandinavian ASMR neo-classical acoustic cue, 84 BPM, D Major. Opens with delicate plucked cello pizzicato and light woodblock clicks. Builds into an intricate, satisfying, rhythmic clockwork pattern with felted upright piano. Resolves gracefully into a lush, peaceful ambient string chord that rings out into pristine silence."
    ),
    nano_banana_assets=[
        NanoBananaReference(
            asset_id="<image_1>",
            job_description="Defines the exact cardboard texture, proportions, blue-printed IKEA logo, and packing tape styling of the sealed flat-pack box.",
            exclusion_clause="Do not copy the studio background or white seamless floor from <image_1>.",
            generation_prompt="Commercial product photograph of a pristine, sealed flat-pack IKEA cardboard furniture box resting on a neutral background, sharp corners, kraft corrugated paper texture, classic blue IKEA logo clearly printed on top surface, reinforced brown paper packing tape along seams, clean architectural studio lighting."
        ),
        NanoBananaReference(
            asset_id="<image_2>",
            job_description="Defines the exact Scandinavian living room interior palette, pale ash wood flooring, and floor-to-ceiling window architecture.",
            exclusion_clause="Do not copy any people, pets, or outdoor weather conditions from <image_2>.",
            generation_prompt="Architectural interior photograph of an empty, bright Scandinavian room with wide pale blonde ash plank flooring, pristine matte-white walls, high ceilings, large black-framed multi-pane windows on the left wall with morning sunlight casting geometric light pools across the clean floor, 8k resolution, shot on Hasselblad."
        ),
        NanoBananaReference(
            asset_id="<image_3>",
            job_description="Defines the complete finished furniture suite (grey fabric sofa, oak coffee table, mustard-yellow wool throw blanket, minimalist white bookcase, potted fiddle-leaf fig).",
            exclusion_clause="Do not copy the room layout from <image_3>; use only the furniture design and fabric specifications.",
            generation_prompt="Catalog showcase photograph of a curated IKEA living room set: an ash-grey textured fabric two-seater sofa, a low solid oak oval coffee table, a folded mustard-yellow waffle-knit wool throw blanket, an open white-lacquered shelf unit with art books, and a terracotta potted green fiddle-leaf plant, photorealistic Scandinavian design."
        )
    ],
    scenes=[
        ScenePromptSpec(
            scene_index=1,
            timestamp_range="00:00 - 00:08",
            scene_title="The Awakening Box",
            regime=RegimeType.REGIME_2_KINETIC,
            action_beats=[
                "The sealed IKEA box sits dead-center on the bare ash floor in total stillness under morning sunlight.",
                "At second 03, the box begins to shudder rapidly with high-frequency tactile micro-vibrations.",
                "At second 07, the reinforced packing tape along the top center seam suddenly splits open with a crisp pop and a tiny puff of kraft paper dust."
            ],
            kinetic_contact_chain="Stillness -> Micro-oscillation of box edges against ash floorboards -> High-tension seam split -> Cardboard flaps spring open 15 degrees -> Settles into open posture.",
            omni_prose_prompt="A locked-off wide-angle architectural shot captures an empty, pristine Scandinavian room with pale blonde ash wood floors and sunlit white walls, based on the spatial layout of <image_2>. In the exact dead-center of the floor rests a sealed kraft cardboard IKEA flat-pack box matching the design in <image_1>. All action occurs at natural, real-time 1.0x playback speed with unyielding physical gravity. For the first three seconds, the box sits in dead stillness under warm morning sunlight streaming through the tall left windows. At second 03, the box begins to tremble and vibrate with intense, tactile micro-tremors, rattling crisply against the rigid hardwood floor without shifting location. At second 07, the center packing tape violently splits open, releasing a small puff of kraft dust as the top cardboard flaps spring slightly upward. The camera remains completely fixed on its tripod with zero movement, zero drift, and tack-sharp deep focus. Synchronized diegetic audio begins with dead-silent empty room tone, followed by the dry resonant woody rattling of cardboard against ash flooring, culminating in a sharp, hyper-tactile cardboard POP and tearing tape sound.",
            conversational_edit_deltas=[
                "Turn 2: Make the box tremble more violently and add visible paper dust curling into the sunbeam.",
                "Turn 3: Change the morning sun to soft overcast afternoon daylight while keeping the box action identical."
            ]
        ),
        ScenePromptSpec(
            scene_index=2,
            timestamp_range="00:08 - 00:16",
            scene_title="The Hyper-Kinetic Self-Assembly",
            regime=RegimeType.REGIME_2_KINETIC,
            action_beats=[
                "The cardboard flaps fold flat onto the floor like blooming origami petals.",
                "Precision-cut solid oak furniture legs, white shelf panels, and frame components levitate out in structured order.",
                "Components interlock at high velocity into a low coffee table and a minimalist shelving unit with rigid mechanical clicks."
            ],
            kinetic_contact_chain="Flaps burst outward -> Wooden pieces slide on air trajectories -> Dovetail joints collide and snap together -> Base legs strike the hardwood floor with solid acoustic thuds -> Stable resting lock.",
            omni_prose_prompt="A locked-off wide-angle architectural shot from the exact same fixed camera position in the empty Scandinavian room. Continuing at 1.0x real-time speed with no slow motion, the cardboard box flaps instantly burst fully open, laying flat on the blonde ash floor. In a rapid, hyper-satisfying burst of choreographed kinetic assembly, flat-pack components derived from <image_3> erupt in crisp sequence: precision-cut solid oak table legs shoot outward and lock with rigid mechanical authority into an oval coffee table tabletop, while white-lacquered shelf panels slide and click into a vertical bookcase against the rear wall. Every wooden dowel, joint, and cam-lock snaps into place with zero elastic warping or rubbery bending, obeying rigid solid-state geometry. The camera holds perfectly static on its tripod, framing the explosive self-building choreography in tack-sharp focus. Synchronized diegetic ASMR audio features a rapid cascade of hyper-detailed mechanical sounds: high-speed sliding wood panels, sharp rhythmic CLICK-CLACK dowel snaps, metallic fastener clicks, and the deep, solid THUD of oak table legs planting firmly onto the hardwood floorboards, accompanied by playful acoustic cello pizzicato from the master score.",
            conversational_edit_deltas=[
                "Turn 2: Increase the speed of the shelf assembly and add subtle sawdust motes catching the sunlight.",
                "Turn 3: Ensure the bookcase locks against the wall with an audible resonant tap."
            ]
        ),
        ScenePromptSpec(
            scene_index=3,
            timestamp_range="00:16 - 00:24",
            scene_title="Upholstery & Soft Architecture",
            regime=RegimeType.REGIME_2_KINETIC,
            action_beats=[
                "A textured grey fabric sofa expands smoothly from the center staging area, cushions billowing outward.",
                "A woven natural wool area rug unrolls across the ash floor with rhythmic momentum.",
                "A ceramic table lamp and a potted green fiddle-leaf fig slide gracefully onto their finished surfaces."
            ],
            kinetic_contact_chain="Rug unrolls across floorboards with surface friction -> Sofa cushions drop under gravity -> Potted plant bases contact oak tabletop with ceramic clinks -> Secondary leaf settling oscillation.",
            omni_prose_prompt="The locked-off wide-angle shot maintains unbroken continuous framing of the evolving Scandinavian room. At natural real-time 1.0x speed, a large textured oat-grey fabric two-seater sofa matching <image_3> unfolds with solid mechanical grace in the center-left living space, its dense foam cushions plumping and expanding into taut upholstery. Simultaneously, a dense woven natural wool area rug unrolls rapidly across the ash floorboards from right to left, coming to a dead stop beneath the sofa legs with crisp surface friction. In the background, a white ceramic table lamp with a pleated paper shade and a potted fiddle-leaf plant glide smoothly into position onto the finished oak coffee table and bookcase surfaces, their bases landing with micro-second precision. Maintain rigid prop geometry and lighting continuity from the low morning sun. Synchronized diegetic audio layers the satisfying heavy unrolling friction of thick wool rug against hardwood, the deep, muffled FWUMP of heavy sofa cushions settling, the delicate ceramic tink of the lamp touching wood, and the subtle rustle of green plant leaves coming to rest.",
            conversational_edit_deltas=[
                "Turn 2: Add a soft warm light turning on inside the pleated paper table lamp upon landing.",
                "Turn 3: Make the fiddle-leaf fig leaves oscillate gently for 2 seconds after touching down."
            ]
        ),
        ScenePromptSpec(
            scene_index=4,
            timestamp_range="00:24 - 00:32",
            scene_title="The Final Flourish & The ASMR Stillness",
            regime=RegimeType.REGIME_2_KINETIC,
            action_beats=[
                "A folded mustard-yellow waffle-knit wool throw blanket arcs gracefully through the air over the sofa.",
                "The blanket lands dead-center on the grey sofa corner, sending a soft, visible air ripple through its knit folds.",
                "All motion abruptly freezes into an immaculate, serene, fully furnished architectural living room."
            ],
            kinetic_contact_chain="Throw blanket trajectory -> Gentle gravitational descent -> Impact with sofa cushion -> Micro-compression of textile knit -> Total static equilibrium.",
            omni_prose_prompt="The fixed wide-angle camera remains perfectly locked on the fully assembled Scandinavian living room under warm morning sunlight. Filmed at real-time 1.0x playback speed, the final missing element—a vibrant mustard-yellow waffle-knit wool throw blanket from <image_3>—descends smoothly through the sunlit air in a gentle, gravity-bound arc. At second 28, the blanket lands gracefully across the right armrest of the textured grey sofa, its soft wool folds settling with natural fabric weight and creating a momentary gentle compression in the seat cushion before coming to complete rest. As the blanket touches down, every moving element in the room reaches absolute, motionless stillness: the plants are static, the furniture is pristine, and warm sunlight bathes the peaceful sanctuary. The camera holds unbroken static discipline with no jump cuts and no morphing. Synchronized diegetic audio captures the gentle, airy fwoosh of the descending wool, followed by a singular, supremely soft and satisfying fwoomp as it cushions onto the sofa fabric. Instantly, all musical and mechanical sounds cut out, leaving only pristine, hushed Scandinavian room tone and the faint, distant chirp of morning birds outside.",
            conversational_edit_deltas=[
                "Turn 2: Add a small steaming white ceramic coffee mug resting on the oak coffee table in the final second.",
                "Turn 3: Softly rack focus to the mustard throw blanket texture in the final 2 seconds."
            ]
        )
    ],
    domain_archetype="architectural_sanctuary",
)

# 2. SEPHORA London Pulse (Mode A Parallel Cut)
SEPHORA_PULSE_BIBLE = MasterProductionBible(
    project_title="SEPHORA: London Pulse (Midnight Velvet)",
    logline="A high-octane, 9:16 vertical fashion collision through rainy midnight Soho, where two avant-garde models strut from London street grit into a gleaming SEPHORA flagship, culminating in a hero product lock.",
    creative_regime=RegimeType.REGIME_2_KINETIC,
    storytelling_mode=StorytellingMode.MODE_A_PARALLEL_CUT,
    aspect_ratio=AspectRatio.RATIO_9_16,
    total_runtime_seconds=32,
    color_palette=["#0A0A10", "#FF0055", "#00F0FF", "#FCEE09"],
    characters=[
        CharacterTurnaroundSpec(
            name="Model Maya (The Neon Siren)",
            silhouette="Tall, athletic, razor-sharp high cheekbones, graphic slicked-back raven architectural bob.",
            wardrobe_polarity="HIGH POLARITY A: Vivid high-gloss scarlet-red patent trench coat with oversized structured lapels, sheer black mesh collar, and metallic silver pointed-toe stiletto boots.",
            movement_signature="Aggressive, predatory, fast-tempo runway stride with zero hip sway and sharp head pivots."
        ),
        CharacterTurnaroundSpec(
            name="Model Kaelen (The Shimmer Rebel)",
            silhouette="Androgynous, dark glowing skin, cropped bleached-platinum buzz cut, sharp jawline.",
            wardrobe_polarity="HIGH POLARITY B: Matte charcoal-grey tailored wool blazer with chalk-white pinstripes on sleeves, jet-black silk camisole, and heavy distressed combat boots.",
            movement_signature="Fluid, rhythm-locked street bounce with syncopated shoulder dips matching the UK Garage groove."
        )
    ],
    environment=MasterEnvironmentSpec(
        location_name="Midnight Soho to SEPHORA Flagship",
        spatial_architecture="Exterior: Rain-slicked London cobblestones and wet asphalt reflecting neon signage. Interior: High-gloss black lacquer and mirrored vanity aisles bathed in brilliant 5600K beauty lighting.",
        lighting_setup="Exterior: Moody 3200K tungsten streetlamps with electric magenta and cyan neon rim light. Interior: 5600K high-CRI diffused beauty lighting.",
        atmospheric_particles="Fine airborne London rain drizzle, water droplets on patent leather, cosmetic shimmer powder catching light.",
        positive_invariants=[
            "The black-and-white SEPHORA shopping bag retains exact vertical stripe geometry and clean typography.",
            "Maya's scarlet trench coat remains high-gloss patent leather without texture drift.",
            "Kaelen's charcoal blazer maintains chalk-white stripe accents without color bleeding."
        ]
    ),
    camera_rig=CraftCameraSpec(
        rig_type="9:16 Vertical Steadicam on 50mm Anamorphic Lens",
        focal_length_mm=50,
        composition="Dynamic vertical framing emphasizing towering model silhouettes, high-fashion angles, and macro beauty details.",
        route="Rapid tracking shots, snappy whip-pans, and stabilizing push-ins.",
        action_anchor="Model facial expressions and tactile product interactions.",
        focus_axis="Shallow f/1.8 depth of field creating vertical oval anamorphic bokeh in wet city lights.",
        tone_rig="High-fashion commercial editorial."
    ),
    sonic_blueprint=DiegeticSonicSpec(
        foley_cues=[
            "Rapid rhythmic stiletto heel clicks on wet cobblestone",
            "Passing double-decker bus wet tire spray and diesel roar",
            "Pneumatic whoosh of glass sliding doors opening",
            "Metallic magnetic click of luxury lipstick cap disengaging",
            "Crisp paper bag snap and handle tension sound"
        ],
        dialogue_lines=["Maya: 'London, wake up.'"],
        room_acoustics="Wet, reverberant London street exterior transitioning sharply into hyper-clean, acoustically dampened luxury retail interior."
    ),
    master_bgm=MasterBgmSpec(
        track_title="Midnight Velvet: UK Garage Pulse",
        genre_style="Syncopated UK Garage / Hyper-Pop Runway Sizzle",
        tempo_bpm=138,
        key_signature="F Minor",
        instrumentation=[
            "Syncopated 2-step drum groove with punchy kick and crisp rimshots",
            "Deep rolling Moog Reese bassline",
            "Glittering hyper-pop synth arpeggios and vocal chops",
            "Dramatic snare roll risers and white-noise sweeps"
        ],
        dynamic_arc="Seconds 00-08: Snappy 2-step rhythm kicks in on the wink. Seconds 08-16: Heavy bassline drops inside flagship. Seconds 16-24: Massive riser sweep building energy. Seconds 24-32: Sudden cut to dead silence on final freeze-frame bag snap, leaving only a sub-bass decay.",
        lyria_prompt="High-energy UK Garage fashion runway track, 138 BPM, F Minor. Syncopated skipping 2-step beats, punchy kick drum, driving Moog bassline, glittering hyper-pop synth arpeggios, and edgy vocal chops. Builds rapidly with dramatic snare roll risers into an explosive, sleek high-fashion drop, ending abruptly on a crisp impact hit."
    ),
    nano_banana_assets=[
        NanoBananaReference(
            asset_id="<image_1>",
            job_description="Defines the exact facial structure, avant-garde graphic eyeliner, and scarlet patent trench coat for Model Maya.",
            exclusion_clause="Do not copy the studio lighting or plain grey background from <image_1>.",
            generation_prompt="Fashion editorial portrait of a striking woman with high cheekbones and slicked-back raven hair, wearing avant-garde metallic holographic graphic eyeliner and bold matte crimson lipstick, dressed in a high-gloss scarlet-red patent leather trench coat, vertical 9:16 framing, Hasselblad high-fashion beauty lighting."
        ),
        NanoBananaReference(
            asset_id="<image_2>",
            job_description="Defines the androgynous facial features, bleached platinum hair, and striped-cuff charcoal blazer for Model Kaelen.",
            exclusion_clause="Do not copy the pose or static background from <image_2>.",
            generation_prompt="Fashion editorial portrait of an androgynous model with dark glowing skin, bleached-platinum short hair, subtle holographic shimmer across cheekbones, wearing an oversized matte-charcoal tailored blazer with chalk-white striped cuffs, confident fierce expression, vertical 9:16 format, sleek editorial aesthetic."
        ),
        NanoBananaReference(
            asset_id="<image_3>",
            job_description="Defines the exact physical construction, black-and-white vertical stripe pattern, braided rope handle, and embossed logo of the SEPHORA shopping bag.",
            exclusion_clause="Do not copy any store background from <image_3>; maintain only the bag's rigid geometry and texture.",
            generation_prompt="Product photograph of an iconic SEPHORA retail shopping bag made of thick matte paper with clean black and vertical white stripes, black braided rope handles, crisp rectangular folds, embossed black SEPHORA logo centered, studio lighting, photorealistic commercial product shot."
        )
    ],
    scenes=[
        ScenePromptSpec(
            scene_index=1,
            timestamp_range="00:00 - 00:08",
            scene_title="The Soho Stare & The Night Pan",
            regime=RegimeType.REGIME_2_KINETIC,
            action_beats=[
                "Extreme vertical macro close-up on Model Maya's eye with shimmering holographic eyeshadow in Soho rain.",
                "Maya executes a sharp, deliberate runway wink directly into lens at second 02.",
                "On the wink, camera whip-pans 90 degrees right to reveal a rain-slicked Soho street with a motion-blurred red double-decker bus streaking past."
            ],
            kinetic_contact_chain="Micro-eye movement -> High-velocity eyelid closure (wink) -> Triggered camera whip-pan acceleration -> Rapid rotational deceleration -> Wet asphalt perspective stabilization.",
            omni_prose_prompt="A 9:16 vertical high-fashion cinematic sequence begins in an extreme macro close-up on Model Maya's face matching <image_1>, focusing on her left eye adorned with shimmering emerald and gold holographic eyeshadow and immaculate winged eyeliner. Raindrops glisten on her cheek under wet Soho neon lighting at real-time 1.0x playback speed with zero slow motion. At second 02, Maya delivers a sharp, confident wink directly into the lens and whispers: 'London, wake up.' Triggered precisely by the eyelid closing, the vertical 50mm camera executes a high-speed horizontal whip-pan to the right, blurring neon lights into electric streaks before snapping to a halt in a medium-wide shot of a rain-slicked Soho cobblestone avenue, where an iconic red London double-decker bus streaks past in the background with wet asphalt tire hiss. Preserving continuous kinetic momentum and rotational inertia across the rapid whip-pan. Maintain crisp focal planes, rich saturated magenta and cyan reflections, and zero digital artifacting. Synchronized diegetic audio starts with the intimate, dry sound of an eyelid blink and whispered vocal close to mic, slamming instantly into a punching 138 BPM UK Garage drum hit, a whooshing whip-pan sound effect, and the wet tire spray of the passing bus.",
            conversational_edit_deltas=[
                "Turn 2: Enhance the neon reflections in the street puddles and add more visible rain mist.",
                "Turn 3: Change the lipstick color on Maya to a deeper midnight burgundy while keeping the wink identical."
            ]
        ),
        ScenePromptSpec(
            scene_index=2,
            timestamp_range="00:08 - 00:16",
            scene_title="The Flagship Infiltration: Tactile Glamour",
            regime=RegimeType.REGIME_2_KINETIC,
            action_beats=[
                "Camera pushes forward through glowing glass sliding doors into the hyper-bright SEPHORA flagship.",
                "Model Kaelen slides a metallic gold lipstick casing open, revealing a vibrant crimson bullet.",
                "A large soft makeup brush sweeps across Maya's cheekbone in a rapid beauty montage, dusting fine shimmering particles."
            ],
            kinetic_contact_chain="Door glide -> Hand grips weighted lipstick tube -> Thumb drives cap removal with magnetic click -> Brush fibers compress against cheek skin -> Shimmer cloud dispersion.",
            omni_prose_prompt="Continuing in 9:16 vertical format at 1.0x real-time speed, the camera glides smoothly forward on a stabilized Steadicam through the automatic sliding glass doors of the SEPHORA flagship, transitioning instantly from wet dark Soho into brilliant, 5600K multi-point beauty lighting. Over seconds 08 to 11, Model Kaelen from <image_2> in his charcoal blazer with white-striped cuffs lifts a heavyweight gold metal lipstick tube with precision thumb flick, sliding the cap off with rigid mechanical alignment. Forward camera glide preserves continuous kinetic momentum conservation and physical inertia as the models enter. Over seconds 11 to 14, in a snappy two-beat montage, Maya turns into frame and a plush black makeup brush sweeps firmly across her cheekbone, releasing a delicate micro-burst of golden cosmetic shimmer that catches the ring light. Over seconds 14 to 16, both models exchange a fierce, synchronized side-profile smile in front of a gleaming black lacquer cosmetic display. Keep cosmetics mechanically rigid and textures true to high-end beauty advertising. Synchronized diegetic audio features the heavy pneumatic whoosh of sliding glass doors, the loud, satisfying metallic CLACK of the lipstick cap disengaging, the soft fibrous swoosh of brush on skin, and high-energy driving UK Garage bassline.",
            conversational_edit_deltas=[
                "Turn 2: Make the cosmetic shimmer dust reflect rainbow sparkles under the beauty lights.",
                "Turn 3: Rack focus from the lipstick bullet directly to Kaelen's smiling eyes."
            ]
        ),
        ScenePromptSpec(
            scene_index=3,
            timestamp_range="00:16 - 00:24",
            scene_title="The Soho Runway Strut",
            regime=RegimeType.REGIME_2_KINETIC,
            action_beats=[
                "Maya and Kaelen strut in synchronized lockstep out of the store entrance onto the wet London sidewalk.",
                "Maya's stiletto heels plant firmly onto the wet pavement with zero slip or float.",
                "Maya swings the iconic black-and-white SEPHORA shopping bag forward in an assertive arc toward camera."
            ],
            kinetic_contact_chain="Stiletto strike on wet cobblestone -> Ground reaction force pushes hip forward -> Arm swings bag from shoulder -> Centrifugal arc of braided handle -> Forward presentation.",
            omni_prose_prompt="A tracking 9:16 vertical Steadicam shot moves backward at a rapid walking pace 2 meters ahead of Maya and Kaelen as they burst through the store exit onto the rainy London pavement in synchronized runway cadence at natural 1.0x speed. Maya and Kaelen preserve forward kinetic momentum conservation and continuous physical inertia with rhythmic stride cadence. Maya wears her glossy scarlet trench coat from <image_1> and Kaelen wears his charcoal blazer from <image_2>, creating stark visual polarity against the night background. Maya's metallic stiletto heels plant firmly onto the wet asphalt with unmistakable physical weight, kicking up micro-droplets of water with each step. At second 21, Maya swings the black-and-white striped SEPHORA shopping bag from <image_3> smoothly forward toward the lens with runway attitude, holding the braided rope handle tight in her leather-gloved fingers. The camera keeps both models centered in vertical profile without crossing the action axis, capturing the glowing neon storefront behind them melting into creamy vertical anamorphic bokeh. Synchronized diegetic audio layers rapid, rhythmic stiletto clicks reverberating off brick walls, wet street splash foley, the crisp cardstock rustle of the shopping bag, and a soaring synth-pop riser sweep peaking in intensity.",
            conversational_edit_deltas=[
                "Turn 2: Increase the stride speed slightly and add dramatic billow to Maya's red trench coat hem.",
                "Turn 3: Add steam rising from a nearby underground subway grate in the background."
            ]
        ),
        ScenePromptSpec(
            scene_index=4,
            timestamp_range="00:24 - 00:32",
            scene_title="The Bag Lock & The Soho Freeze",
            regime=RegimeType.REGIME_2_KINETIC,
            action_beats=[
                "The camera punches in 60 centimeters directly toward the SEPHORA shopping bag held firmly in Maya's hand.",
                "The bag halts dead-center in the vertical frame, perfectly upright with sharp paper edges.",
                "At second 30, the video cuts to a crisp editorial freeze-frame on the bag and SEPHORA logo, with blurred glowing Soho neon behind."
            ],
            kinetic_contact_chain="Punch-in camera motion -> Arm locks bag at chest height -> Rope handles tension under gravity -> Abrupt momentum cessation -> Total frozen frame.",
            omni_prose_prompt="The vertical 9:16 camera executes a rapid, stabilized punch-in push of 60 centimeters directly toward the iconic black-and-white striped SEPHORA bag held firmly in Maya's gloved hand at chest height. Filmed at real-time 1.0x speed, the punch-in camera preserves kinetic momentum conservation before locking into the static freeze. The bag from <image_3> swings into the exact center of the vertical frame: its braided black rope handles are taut, its folded paper gussets are crisp and unwrinkled, and the embossed black SEPHORA typography is rendered in tack-sharp macro clarity. In the background, the glowing store portal and the wet London night street dissolve into beautiful out-of-focus bokeh circles. At exactly second 30, all motion abruptly halts into a pristine, high-resolution editorial freeze-frame on the bag, holding dead-still for the final two seconds with zero text distortion and zero geometric warping. Synchronized audio reaches its climax as the UK Garage track hits a massive final snare and bass drop, instantly cutting to absolute dead silence punctuated only by a single, crisp, mechanical SNAP sound effect as the frame freezes, with a faint, luxurious reverb tail decaying into the silence.",
            conversational_edit_deltas=[
                "Turn 2: Add a bold white sans-serif kinetic text overlay in the center that pops in reading 'FEEL THE PULSE'.",
                "Turn 3: Shift the background bokeh color balance to rich ambers and golds."
            ]
        )
    ],
    domain_archetype="luxury_fashion",
)

# 3. SEPHORA Continuous Extension 40s (Mode B)
SEPHORA_EXTENSION_40S_BIBLE = MasterProductionBible(
    project_title="SEPHORA: London Pulse (Continuous 40s Oner)",
    logline="A seamless, unbroken 40-second continuous 9:16 vertical Steadicam oner tracking two avant-garde models through rainy midnight Soho into the SEPHORA flagship and back to the wet pavement, linked across four +10s Gemini Omni extensions.",
    creative_regime=RegimeType.REGIME_2_KINETIC,
    storytelling_mode=StorytellingMode.MODE_B_CONTINUOUS_CHAIN,
    aspect_ratio=AspectRatio.RATIO_9_16,
    total_runtime_seconds=40,
    color_palette=["#0A0A10", "#FF0055", "#00F0FF", "#FCEE09"],
    characters=SEPHORA_PULSE_BIBLE.characters,
    environment=SEPHORA_PULSE_BIBLE.environment,
    camera_rig=SEPHORA_PULSE_BIBLE.camera_rig,
    sonic_blueprint=SEPHORA_PULSE_BIBLE.sonic_blueprint,
    master_bgm=MasterBgmSpec(
        track_title="Midnight Velvet: UK Garage Pulse (40s Continuous Oner)",
        genre_style="Syncopated UK Garage / Hyper-Pop Runway Sizzle",
        tempo_bpm=138,
        key_signature="F Minor",
        instrumentation=SEPHORA_PULSE_BIBLE.master_bgm.instrumentation,
        stems={
            "percussion": "Syncopated 2-step garage kicks, snappy rimshots, and shaker syncopations",
            "bass": "Heavy rolling Reese bassline and sub drone",
            "harmony": "Glittering hyper-pop synth arpeggios and atmospheric pads",
            "lead": "Processed vocal chops and staccato melodic hooks",
        },
        dynamic_arc=(
            "Seconds 00-10: Intimate street rain ambiance and skipping 2-step groove during Soho approach. "
            "Seconds 10-20: Rolling Reese bass drops as models enter the flagship, whispering 'London, wake up'. "
            "Seconds 20-30: Soaring hyper-pop synth arpeggios and white-noise riser as bag is lifted. "
            "Seconds 30-40: Climactic percussion impact at second 38 snapping into dead silence on bag freeze."
        ),
        lyria_prompt=SEPHORA_PULSE_BIBLE.master_bgm.lyria_prompt,
    ),
    nano_banana_assets=SEPHORA_PULSE_BIBLE.nano_banana_assets,
    scenes=[
        ScenePromptSpec(
            scene_index=1,
            timestamp_range="00:00 - 00:10 (Base Clip)",
            scene_title="The Soho Approach",
            regime=RegimeType.REGIME_2_KINETIC,
            action_beats=[
                "Model Maya struts down rain-slicked Soho cobblestones at midnight under glowing neon signage.",
                "A red double-decker bus streaks past with wet tire spray in the background.",
                "Maya reaches the glowing glass facade of the SEPHORA flagship, heels clicking firmly on wet stone."
            ],
            kinetic_contact_chain="Stiletto strike -> Ground reaction force -> Arm swing momentum -> Controlled approach -> Hand touches entrance door handle.",
            omni_prose_prompt="A 10-second continuous 9:16 vertical tracking shot glides backward at natural 1.0x real-time speed ahead of Model Maya matching <image_1>, who struts down a rain-slicked Soho cobblestone avenue at midnight. Maya wears a high-gloss scarlet-red patent trench coat with metallic stiletto boots, her eyes adorned with vivid holographic emerald eyeshadow. Maya's stride preserves forward kinetic momentum conservation and continuous physical inertia with crisp ground contact. Neon signage from vintage clubs reflects across the wet asphalt with genuine physical reflections as an iconic red London bus streaks past in the background with wet asphalt tire hiss. Maya approaches the glowing glass facade of a SEPHORA flagship, her heels clicking crisply against the stones with unyielding physical gravity. Synchronized diegetic audio features rhythmic stiletto clicks, wet tire hisses, city rain mist, and a skipping 138 BPM UK Garage drum rhythm, ending as Maya extends her hand to push open the store entrance.",
            conversational_edit_deltas=["Turn 2: Enhance neon puddle reflections."]
        ),
        ScenePromptSpec(
            scene_index=2,
            timestamp_range="+10s extension (00:10 - 00:20)",
            scene_title="The Store Transition",
            regime=RegimeType.REGIME_2_KINETIC,
            action_beats=[
                "Camera glides backward without jump cuts through opening glass doors into brilliant 5600K beauty light.",
                "Model Kaelen in charcoal blazer steps into frame alongside Maya.",
                "Kaelen flicks open a gold lipstick case with a crisp mechanical snap as Maya whispers 'London, wake up.'"
            ],
            kinetic_contact_chain="Door glide momentum -> Footfall cadence unchanged -> Thumb drives lipstick cap removal -> Snappy mechanical disengagement -> Side-by-side synchronized stride.",
            omni_prose_prompt="The camera continues backward in one unbroken continuous shot through the opening glass doors as Maya struts inside without missing a beat, continuing at 1.0x real-time speed. The unbroken camera preserves continuous kinetic momentum conservation and physical inertia as both models advance. The lighting shifts dynamically from wet moody London night into brilliant 5600K diffused beauty lighting bouncing off black-lacquered mirrored aisles. Model Kaelen from <image_2>, wearing a tailored charcoal blazer with chalk-white striped cuffs, steps smoothly into frame alongside her. Kaelen flicks open a gold lipstick case with a crisp mechanical snap, smiling as Maya whispers: 'London, wake up.' The 138 BPM music drops into a heavy Moog bassline as both models strut in side-by-side synchronization down the central cosmetics corridor with rigid physical postures. One continuous shot, no jump cuts.",
            conversational_edit_deltas=["Turn 2: Increase beauty light bounce off mirrors."]
        ),
        ScenePromptSpec(
            scene_index=3,
            timestamp_range="+10s extension (00:20 - 00:30)",
            scene_title="The Product Flourish",
            regime=RegimeType.REGIME_2_KINETIC,
            action_beats=[
                "Vertical tracking camera arcs 45 degrees to frame Maya from a low-angle three-quarter angle.",
                "Maya smoothly picks up the striped SEPHORA shopping bag by its braided rope handles in stride.",
                "The bag swings forward in a controlled arc, catching overhead beauty lights with rigid paper folds."
            ],
            kinetic_contact_chain="Tracking arc -> Fingers grasp braided rope handle -> Upward impulse lifts bag -> Centrifugal acceleration swings bag forward -> Stable chest-height carry.",
            omni_prose_prompt="The camera continues its unbroken vertical tracking movement at 1.0x real-time speed, arcing 45 degrees to frame Maya from a low-angle three-quarter perspective as she reaches a central vanity display. Maya's fluid stride preserves continuous kinetic momentum conservation and physical inertia as the shopping bag swings forward. In one fluid motion without stopping her stride, she picks up the iconic black-and-white striped SEPHORA shopping bag from <image_3> by its braided black rope handles. The bag swings forward in a controlled arc, its sharp paper folds and clean monochrome stripes catching the overhead beauty lights with pristine geometric rigidity and natural fabric weight. Kaelen pivots smoothly in the background, examining a shimmering powder compact. Synchronized diegetic audio features the crisp rustle of thick luxury paper, rope handle tension, stiletto clicks echoing on mirrored tiles, and a building bassline with white-noise sweeps. One continuous shot, no jump cuts.",
            conversational_edit_deltas=["Turn 2: Enhance white-noise sweep intensity."]
        ),
        ScenePromptSpec(
            scene_index=4,
            timestamp_range="+10s extension (00:30 - 00:40)",
            scene_title="The Climactic Hero Lock",
            regime=RegimeType.REGIME_2_KINETIC,
            action_beats=[
                "Camera punches in 50 centimeters directly toward the SEPHORA bag.",
                "Embossed brand logo locks dead-center at chest height as Maya reaches the outdoor threshold.",
                "At second 38, motion snaps into a high-fashion freeze-frame on the bag, with neon bokeh behind."
            ],
            kinetic_contact_chain="Punch-in deceleration -> Arm locks bag upright -> Rope handles hold vertical tension -> Immediate kinetic freeze -> Sustained static frame.",
            omni_prose_prompt="The camera executes a smooth 50-centimeter punch-in toward the SEPHORA bag from <image_3>, locking the embossed brand logo dead-center in the vertical frame at 1.0x real-time playback speed. The smooth camera move preserves continuous kinetic momentum conservation and physical inertia before snapping into the final static freeze-frame. Maya holds the bag firmly at chest height as she reaches the outdoor threshold once more, glancing over her shoulder directly into the lens. At second 38, all motion snaps into an immaculate high-fashion freeze-frame on the crisp bag with unyielding geometric precision, with Maya's scarlet trench and the glowing store interior blurring into lush bokeh behind. Synchronized audio hits a climactic percussion impact and cuts instantly to dead silence, leaving only a single crisp SNAP and a faint decaying sub-bass hum. One continuous shot, no jump cuts.",
            conversational_edit_deltas=["Turn 2: Shift background bokeh to warm ambers."]
        )
    ],
    domain_archetype="luxury_fashion",
)

# 4. Kinetic Fabric Golden Preset
KINETIC_FABRIC_BIBLE = MasterProductionBible(
    project_title="The Kinetic Fabric: Grounded Innovation",
    logline="A dynamic material exploration of high-performance technical fabric moving from microscopic weave tension to high-velocity athletic aerodynamic turbulence.",
    creative_regime=RegimeType.REGIME_2_KINETIC,
    storytelling_mode=StorytellingMode.MODE_A_PARALLEL_CUT,
    aspect_ratio=AspectRatio.RATIO_16_9,
    total_runtime_seconds=32,
    color_palette=["#0F172A", "#38BDF8", "#F43F5E", "#E2E8F0"],
    characters=[],
    environment=MasterEnvironmentSpec(
        location_name="Aerodynamic Wind Tunnel Test Lab",
        spatial_architecture="High-tech wind tunnel facility with matte-black carbon-fiber walls, illuminated laminar flow nozzles, and a mirror-finish titanium test stage.",
        lighting_setup="High-contrast precision 5600K laser line lighting combined with deep blue ambient wash.",
        atmospheric_particles="Ultra-fine white condensation smoke tracing aerodynamic streamlines with zero random turbulence.",
        positive_invariants=[
            "The woven carbon-fiber grid structure remains mathematically consistent without digital warping.",
            "Laser illumination ribbons maintain clean geometric parallelism."
        ]
    ),
    camera_rig=CraftCameraSpec(
        rig_type="High-Speed Robotic Motion Control Track on 100mm Macro Prime",
        focal_length_mm=100,
        composition="Extreme macro geometric framing focusing on microfiber elasticity, tension vectors, and aerodynamic deflection.",
        route="High-precision linear tracking along the air velocity axis with micro-rotational rolls.",
        action_anchor="Woven yarn contact points and laser streamline vortices.",
        focus_axis="Razor-thin f/2.8 macro depth of field with micro-racks across thread layers.",
        tone_rig="Hyper-technical industrial commercial."
    ),
    sonic_blueprint=DiegeticSonicSpec(
        foley_cues=[
            "High-tension textile stretch creak and microfiber friction",
            "Pneumatic wind tunnel airflow whoosh and turbine hum",
            "High-frequency laser hum and ultrasonic resonance",
            "Tactile snap of fabric reaching maximum tensile load"
        ],
        dialogue_lines=[],
        room_acoustics="Acoustically treated industrial aerodynamic testing chamber with dead reflections and heavy sub-bass air pressure."
    ),
    master_bgm=MasterBgmSpec(
        track_title="Tensile Dynamics: Kinetic Pulse",
        genre_style="Futuristic Minimalist Glitch & Cinematic Sub-Bass",
        tempo_bpm=120,
        key_signature="C Minor",
        instrumentation=[
            "Pulsing analog modular synthesizer bassline",
            "Textured metallic percussion clicks tuned to micro-foley",
            "Granular synth pads that expand with airflow velocity",
            "Low sub-bass drops at maximum tension markers"
        ],
        dynamic_arc="Seconds 00-08: Micro-clicks and quiet sub-hum. Seconds 08-16: Rhythmic drive kicks in. Seconds 16-24: High-energy polyrhythms. Seconds 24-32: Sudden sharp deceleration leaving resonant metallic ring.",
        lyria_prompt="Futuristic industrial electronic score, 120 BPM, C Minor. Crisp tactile clicks, modular synth pulses, deep sub-bass drops, and precise microscopic rhythms. High-tech and aerodynamic aesthetic."
    ),
    nano_banana_assets=[
        NanoBananaReference(
            asset_id="<image_1>",
            job_description="Defines the exact microscopic weave pattern, iridescent cyan and scarlet yarn fibers, and tensile thread geometry.",
            exclusion_clause="Do not copy any human hands or background lab equipment from <image_1>.",
            generation_prompt="Macro photograph of high-performance technical athletic fabric: intricate interlocking weave of matte-black carbon fibers and luminous electric-cyan microfibers, 100mm macro lens, ultra-sharp thread details, precision studio rim lighting."
        ),
        NanoBananaReference(
            asset_id="<image_2>",
            job_description="Defines the titanium test stage, wind tunnel nozzle geometry, and laser illumination setup.",
            exclusion_clause="Do not introduce any human operators or unrelated tools from <image_2>.",
            generation_prompt="Architectural interior of an advanced aerodynamic wind tunnel testing facility: mirror-finish dark titanium floor, matte-black composite walls, high-velocity wind nozzle bathed in electric-blue LED rim lights, clean high-tech industrial aesthetic."
        ),
        NanoBananaReference(
            asset_id="<image_3>",
            job_description="Defines the finished aerodynamic winglet drape showing the fabric under maximum aerodynamic deflection.",
            exclusion_clause="Do not change the fabric weave from <image_1>; inherit only the aerodynamic curve geometry.",
            generation_prompt="Product design photograph of a streamlined athletic aerodynamic fabric winglet mounted on a carbon-fiber arm, flexing under high-speed laminar airflow with visible white smoke streamlines, high-speed photography."
        )
    ],
    scenes=[
        ScenePromptSpec(
            scene_index=1,
            timestamp_range="00:00 - 00:08",
            scene_title="The Microscopic Weave",
            regime=RegimeType.REGIME_2_KINETIC,
            action_beats=[
                "Extreme macro view of the interlocking cyan and carbon weave in complete stillness.",
                "At second 03, tension applies and individual yarn microfibers stretch taut with visible physical elongation.",
                "Laser line sweeps across the weave, highlighting microscopic fiber textures."
            ],
            kinetic_contact_chain="Relaxed fibers -> Tensile load applied -> Yarn elongation under force -> Surface micro-flattening -> Stable high-tension lock.",
            omni_prose_prompt="An extreme macro 100mm camera shot frames the intricate technical fabric weave from <image_1> resting on the titanium stage of <image_2>. Filmed at 1.0x real-time speed with rigid physics, the intertwined matte-black carbon yarns and luminous cyan microfibers sit in sharp stillness for the first three seconds under deep blue lab lighting. At second 03, mechanical tension applies from the edges, causing the interlocking threads to pull taut with realistic elasticity, elongating slightly without tearing or morphing while maintaining continuous kinetic momentum conservation and tensile inertia under physical load. A crisp emerald laser scan line sweeps smoothly across the surface at second 06, catching the micro-ridges of each fiber in tack-sharp focus. Synchronized diegetic audio layers a deep, tactile microfiber stretch sound, a soft pneumatic pressure release, and high-precision electronic equipment hum.",
            conversational_edit_deltas=["Turn 2: Add visible micro-dust particle displacement upon tension snap."]
        ),
        ScenePromptSpec(
            scene_index=2,
            timestamp_range="00:08 - 00:16",
            scene_title="The Airflow Ignition",
            regime=RegimeType.REGIME_2_KINETIC,
            action_beats=[
                "Camera pulls back to a medium shot as wind tunnel nozzles ignite with high-speed laminar airflow.",
                "White condensation streamlines wrap smoothly over the taut fabric sheet with zero turbulence.",
                "The fabric ripples rhythmically with high-frequency aerodynamic waves."
            ],
            kinetic_contact_chain="Nozzle airflow discharge -> Air pressure boundary layer forms -> Fluid-structure interaction on fabric -> Aerodynamic ripple wave propagation -> Stable laminar wave state.",
            omni_prose_prompt="The camera executes a smooth backward robotic dolly move at 1.0x real-time playback speed, transitioning from macro into a medium-wide shot of the aerodynamic wind tunnel test bench from <image_2>. At second 09, high-velocity laminar airflow surges from the circular intake nozzle: smooth, parallel ribbons of white condensation smoke glide over the taut cyan-and-black fabric sheet matching <image_1>, adhering perfectly to its surface without turbulent separation while maintaining continuous kinetic momentum conservation and aerodynamic inertia across the high-speed flow. The fabric vibrates with ultra-precise, high-frequency aerodynamic micro-ripples, displaying authentic mass and aerodynamic resistance. The robotic camera holds a perfectly stabilized low-angle tracking position. Synchronized diegetic audio captures the rising pneumatic whoosh of high-speed laminar wind, deep acoustic turbine hum, and the rapid, crisp fluttering friction of synthetic fabric in air.",
            conversational_edit_deltas=["Turn 2: Enhance the brightness of the smoke streamlines under the blue laser light."]
        ),
        ScenePromptSpec(
            scene_index=3,
            timestamp_range="00:16 - 00:24",
            scene_title="The Aerodynamic Deflection",
            regime=RegimeType.REGIME_2_KINETIC,
            action_beats=[
                "Camera tracks laterally around the fabric as it flexes into an aerodynamic winglet curve.",
                "Laser illumination reveals vortices rolling smoothly off the trailing edge.",
                "The material maintains rigid structural integrity under maximum velocity."
            ],
            kinetic_contact_chain="Peak wind velocity -> Aerodynamic lift force generates deflection -> Flexible composite arm reaches planned bend angle -> Trailing edge sheds micro-vortex -> Dynamic equilibrium under load.",
            omni_prose_prompt="A dynamic lateral tracking arc shot sweeps 90 degrees around the testing rig at natural 1.0x speed. Dynamic tracking preserves continuous kinetic momentum conservation and steady aerodynamic inertia as the winglet flexes under aerodynamic load. The technical fabric sheet, mounted on a sleek carbon-fiber arm like <image_3>, flexes smoothly under extreme aerodynamic pressure into a graceful, low-drag winglet profile. Twin violet laser sheets slice across the trailing edge, illuminating micro-vortices of smoke that curl gracefully off the fabric lip without fluttering into chaotic turbulence. Maintain exact thread pattern geometry and pristine lighting reflections on the dark titanium floor. Synchronized diegetic audio features a powerful, resonant wind tunnel roar, the high-pitch harmonic whistle of shedding vortices, and heavy sub-bass air compression pulses.",
            conversational_edit_deltas=["Turn 2: Increase the camber of the fabric winglet curve."]
        ),
        ScenePromptSpec(
            scene_index=4,
            timestamp_range="00:24 - 00:32",
            scene_title="The Deceleration & The Form Lock",
            regime=RegimeType.REGIME_2_KINETIC,
            action_beats=[
                "Wind tunnel airflow suddenly cuts off with a deep pneumatic thud.",
                "The fabric springs back into its pristine planar resting position with a satisfying tactile snap.",
                "Laser illumination freezes on the pristine weave as smoke gently dissipates into stillness."
            ],
            kinetic_contact_chain="Airflow cutoff -> Pressure drop -> Elastic restoring force snaps fabric -> Momentum damping oscillation -> Absolute static resting state.",
            omni_prose_prompt="The camera punches in smoothly on the fabric center from the front at 1.0x real-time speed, tracking continuous kinetic momentum conservation and physical inertia until the turbines power down and elastic restoring forces bring the textile into static rest. At second 27, the wind tunnel turbines instantly power down with a solid acoustic drop: the high-speed smoke ribbons dissipate into thin air, and the flexed fabric springs crisply back to its initial flat resting plane with a singular, satisfying physical SNAP. The material settles instantly into flawless, motionless stillness, its black-and-cyan weave catching the steady ambient blue glow of the lab with razor-sharp macro clarity. Zero camera drift and zero digital artifacting. Synchronized diegetic audio captures the heavy pneumatic clunk of the wind valves closing, the crisp, singular SNAP of the taut textile rebounding, and the smooth decay of turbine whine into dead-silent lab room tone.",
            conversational_edit_deltas=["Turn 2: Rack focus to the central carbon fiber thread in the final second."]
        )
    ],
    domain_archetype="kinetic_action",
)

SEPHORA_LONDON_PULSE_BIBLE = SEPHORA_PULSE_BIBLE


def _hydrate_bible_domain_specs(bible: MasterProductionBible) -> MasterProductionBible:
    """Populate any unset master and per-scene technical specs using domain archetype calibrators."""
    arch = bible.domain_archetype or classify_brief_domain(f"{bible.project_title} {bible.logline}")
    bible.domain_archetype = arch

    if not bible.master_color_look:
        bible.master_color_look = get_domain_color_look(arch)
    if not bible.master_audio_mixer:
        bible.master_audio_mixer = get_domain_audio_mixer(arch)
    if not bible.master_lens_package:
        bible.master_lens_package = get_domain_optical_lens(arch)
    if not bible.virtual_production:
        bible.virtual_production = get_domain_virtual_production(arch)
    if not getattr(bible, "master_moco_rig", None):
        bible.master_moco_rig = get_domain_moco_rig(arch)
    if not getattr(bible, "master_lighting_rig", None):
        bible.master_lighting_rig = get_domain_lighting_rig(arch)
    if not getattr(bible, "master_dof_spec", None):
        bible.master_dof_spec = get_domain_dof_spec(arch)
    if not getattr(bible, "master_lut_spec", None):
        bible.master_lut_spec = get_domain_lut_spec(arch)
    if not getattr(bible, "master_spatial_audio", None):
        bible.master_spatial_audio = get_domain_spatial_audio_spec(arch)
    if not getattr(bible, "master_vfx_manifest", None):
        bible.master_vfx_manifest = get_domain_vfx_manifest(arch)
    if not getattr(bible, "master_hdr_spec", None):
        bible.master_hdr_spec = get_domain_hdr_spec(arch)
    if not getattr(bible, "master_stripboard_schedule", None):
        bible.master_stripboard_schedule = get_domain_stripboard_spec(arch, bible.scenes)
    if not getattr(bible, "master_film_emulation", None):
        bible.master_film_emulation = get_domain_film_emulation_spec(arch)
    if not getattr(bible, "master_slate_spec", None):
        bible.master_slate_spec = get_domain_clapper_slate_spec(
            arch, bible.scenes, project_title=bible.project_title
        )
    if not getattr(bible, "master_drone_spec", None):
        bible.master_drone_spec = get_domain_drone_spec(arch)
    if not getattr(bible, "master_aicp_bid", None):
        bible.master_aicp_bid = get_domain_aicp_bid_spec(bible)
    if not getattr(bible, "master_reframe_manifest", None):
        bible.master_reframe_manifest = get_domain_reframe_manifest(bible, bible.scenes)
    if not getattr(bible, "master_broadcast_qc", None):
        bible.master_broadcast_qc = get_domain_broadcast_qc_spec(bible, bible.scenes)
    if not getattr(bible, "master_continuity_blocking", None):
        bible.master_continuity_blocking = get_domain_continuity_blocking_spec(
            bible, bible.scenes, project_title=bible.project_title
        )
    if not getattr(bible, "master_client_review", None):
        bible.master_client_review = get_domain_client_review_spec(
            bible, bible.scenes, project_title=bible.project_title
        )

    for idx, scene in enumerate(bible.scenes, 1):
        if not scene.speed_ramp:
            scene.speed_ramp = get_domain_speed_ramp(arch)
        if not scene.scene_color_look:
            scene.scene_color_look = bible.master_color_look
        if not scene.optical_lens:
            scene.optical_lens = bible.master_lens_package
        if not scene.virtual_production:
            scene.virtual_production = bible.virtual_production
        if not getattr(scene, "moco_rig", None):
            scene.moco_rig = bible.master_moco_rig
        if not getattr(scene, "lighting_rig", None):
            scene.lighting_rig = bible.master_lighting_rig
        if not getattr(scene, "dof_spec", None):
            scene.dof_spec = bible.master_dof_spec
        if not getattr(scene, "lut_spec", None):
            scene.lut_spec = bible.master_lut_spec
        if not getattr(scene, "spatial_audio", None):
            scene.spatial_audio = bible.master_spatial_audio
        if not getattr(scene, "vfx_compositing", None):
            scene.vfx_compositing = bible.master_vfx_manifest
        if not getattr(scene, "hdr_spec", None):
            scene.hdr_spec = bible.master_hdr_spec
        if not getattr(scene, "breakdown_sheet", None):
            scene.breakdown_sheet = extract_script_breakdown_sheet(scene, idx)
        if not getattr(scene, "film_emulation", None):
            scene.film_emulation = bible.master_film_emulation
        if not getattr(scene, "clapper_slate", None) and bible.master_slate_spec and len(bible.master_slate_spec.scenes) >= idx:
            scene.clapper_slate = bible.master_slate_spec.scenes[idx - 1]
        if not getattr(scene, "drone_flight", None):
            scene.drone_flight = bible.master_drone_spec
        if not getattr(scene, "reframe_spec", None):
            if bible.master_reframe_manifest and len(bible.master_reframe_manifest.scene_reframes) >= idx:
                scene.reframe_spec = bible.master_reframe_manifest.scene_reframes[idx - 1]
            else:
                scene.reframe_spec = synthesize_default_scene_reframe(
                    scene=scene, scene_index=idx, scene_title=scene.scene_title, domain=arch
                )
        if not getattr(scene, "broadcast_qc", None):
            if bible.master_broadcast_qc and len(bible.master_broadcast_qc.scene_qc_profiles) >= idx:
                scene.broadcast_qc = bible.master_broadcast_qc.scene_qc_profiles[idx - 1]
            else:
                scene.broadcast_qc = synthesize_default_scene_qc(
                    scene=scene, scene_index=idx, scene_title=scene.scene_title
                )
        if not getattr(scene, "blocking_spec", None):
            if bible.master_continuity_blocking and len(bible.master_continuity_blocking.scene_blockings) >= idx:
                scene.blocking_spec = bible.master_continuity_blocking.scene_blockings[idx - 1]
            else:
                prev_blk = bible.scenes[idx - 2].blocking_spec if idx > 1 else None
                scene.blocking_spec = synthesize_scene_blocking(
                    scene=scene, scene_index=idx, domain=arch, prev_blocking=prev_blk
                )
        if not getattr(scene, "review_signoff", None):
            if bible.master_client_review and len(bible.master_client_review.scene_reviews) >= idx:
                scene.review_signoff = bible.master_client_review.scene_reviews[idx - 1]
            else:
                scene.review_signoff = synthesize_scene_review_signoff(
                    scene=scene, scene_index=idx, domain=arch
                )

    return bible


for _bible_inst in [IKEA_ASMR_BIBLE, SEPHORA_PULSE_BIBLE, SEPHORA_EXTENSION_40S_BIBLE, KINETIC_FABRIC_BIBLE]:
    _hydrate_bible_domain_specs(_bible_inst)

def build_ikea_asmr_bible() -> MasterProductionBible:
    """Builds a fresh instance of the IKEA ASMR golden preset bible."""
    return IKEA_ASMR_BIBLE.model_copy(deep=True)


def build_sephora_pulse_bible() -> MasterProductionBible:
    """Builds a fresh instance of the SEPHORA London Pulse preset bible."""
    return SEPHORA_PULSE_BIBLE.model_copy(deep=True)


def build_sephora_extension_40s_bible() -> MasterProductionBible:
    """Builds a fresh instance of the SEPHORA 40s Continuous Extension preset bible."""
    return SEPHORA_EXTENSION_40S_BIBLE.model_copy(deep=True)


def build_kinetic_fabric_bible() -> MasterProductionBible:
    """Builds a fresh instance of the Kinetic Fabric preset bible."""
    return KINETIC_FABRIC_BIBLE.model_copy(deep=True)


def build_sephora_london_pulse_bible() -> MasterProductionBible:
    """Builds a fresh instance of the SEPHORA London Pulse preset bible."""
    return SEPHORA_LONDON_PULSE_BIBLE.model_copy(deep=True)


PRESETS: Dict[str, MasterProductionBible] = {
    "ikea-asmr": IKEA_ASMR_BIBLE,
    "sephora-pulse": SEPHORA_PULSE_BIBLE,
    "sephora-london-pulse": SEPHORA_LONDON_PULSE_BIBLE,
    "sephora-extension-40s": SEPHORA_EXTENSION_40S_BIBLE,
    "kinetic-fabric": KINETIC_FABRIC_BIBLE,
}
CURATED_PRESETS = PRESETS
GOLDEN_PRESET_BIBLES = PRESETS


ARCHETYPE_PRESET_FALLBACKS: Dict[str, str] = {
    "kinetic-action": "kinetic-fabric",
    "culinary-asmr": "ikea-asmr",
    "luxury-fashion": "sephora-pulse",
    "automotive-robotics": "kinetic-fabric",
    "tech-hardware": "sephora-pulse",
    "architectural-sanctuary": "ikea-asmr",
}


def create_bible(
    domain: Union[DomainArchetype, str] = "culinary_asmr",
    title: Optional[str] = None,
    project_title: Optional[str] = None,
    creative_brief: Optional[str] = None,
    scenes: Optional[List[ScenePromptSpec]] = None,
    **kwargs: Any,
) -> MasterProductionBible:
    """Creates a fully populated MasterProductionBible calibrated with domain specifications (PM-FEAT-015, PM-FEAT-016, PM-FEAT-017, PM-FEAT-018)."""
    domain_key = domain.value if hasattr(domain, "value") else str(domain).lower()
    resolved_title = title or project_title or f"Omni Director: {domain_key.replace('_', ' ').title()}"
    brief = creative_brief or f"Cinematic production showcasing {domain_key.replace('_', ' ')}."

    clean_domain = domain_key.replace("_", "-")
    preset_key = ARCHETYPE_PRESET_FALLBACKS.get(clean_domain, "ikea-asmr")
    base_bible = PRESETS.get(preset_key)

    if scenes is None and base_bible:
        bible = base_bible.model_copy(deep=True)
        bible.project_title = resolved_title
        bible.logline = brief
        bible.domain_archetype = domain_key
    else:
        bible = MasterProductionBible(
            project_title=resolved_title,
            logline=brief,
            domain_archetype=domain_key,
            scenes=scenes or [],
            **kwargs,
        )

    return _hydrate_bible_domain_specs(bible)


def get_preset_bible(name: str) -> MasterProductionBible:
    """Retrieves a pre-configured MasterProductionBible preset by name."""
    clean_name = name.lower().replace("_", "-")
    if clean_name not in PRESETS and clean_name in ARCHETYPE_PRESET_FALLBACKS:
        clean_name = ARCHETYPE_PRESET_FALLBACKS[clean_name]
    if clean_name not in PRESETS:
        available = ", ".join(PRESETS.keys())
        raise ValueError(f"Unknown preset: '{name}'. Available presets: {available}")
    bible = PRESETS[clean_name].model_copy(deep=True)
    return _hydrate_bible_domain_specs(bible)


def create_preset_bible(
    preset_or_domain: Union[DomainArchetype, str] = "culinary_asmr",
    **kwargs: Any,
) -> MasterProductionBible:
    """Creates or retrieves a preset MasterProductionBible with full domain calibrations."""
    key = str(preset_or_domain.value if hasattr(preset_or_domain, "value") else preset_or_domain).lower().replace("_", "-")
    if key in PRESETS:
        bible = get_preset_bible(key)
        for k, v in kwargs.items():
            if hasattr(bible, k):
                setattr(bible, k, v)
        return bible
    return create_bible(domain=preset_or_domain, **kwargs)


get_preset = get_preset_bible

# Backfill golden preset constants with domain specs at module import time
for _p in PRESETS.values():
    _hydrate_bible_domain_specs(_p)


