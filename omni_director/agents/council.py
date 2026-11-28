"""Autonomous Product Council Orchestrator for Omni Movie Director ADK 2.0.

Evaluates productions across 4 specialized personas:
1. council-fde: Forward Deployed Engineer & Production Rigor (Schema, outputs, bundle structure)
2. council-agent-engineer: Prompt Architect & Heuristics (7-Point audit, self-healing, zero 3.1)
3. council-strategist: Creative Strategist (Domain archetypes, narrative, positive invariants)
4. council-ux-designer: UX & Visual Continuity (ViewBox, SMPTE safe guides, SVG keyframes)
"""

from __future__ import annotations

import json
import logging
import re
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from pydantic import ConfigDict

from omni_director.config import (
    FORBIDDEN_LEGACY_PATTERNS,
    DirectorConfig,
    cfg,
    validate_model_identifier,
)
from omni_director.presets import (
    DOMAIN_ARCHETYPES,
    classify_brief_domain,
    get_domain_localization_spec,
    get_domain_spotting_spec,
    get_domain_s3d_spec,
    get_domain_accessibility_spec,
    get_domain_wardrobe_prop_spec,
    get_domain_render_economics_spec,
    get_domain_motion_graphics_spec,
    get_domain_otio_coherence_spec,
    get_domain_render_job_spec,
    get_domain_pitch_treatment_spec,
    get_domain_imf_dcp_profile,
    get_domain_voice_ducking_profile,
    get_domain_color_scopes_profile,
    get_domain_archive_vault_profile,
)
from omni_director.schemas import (
    StorytellingMode,
    CouncilFinding,
    CouncilFindingSeverity,
    CouncilPersona,
    MasterProductionBible,
    PersonaReviewResult,
    ProductCouncilReport,
    ProductFeatureProposal,
    ProductionBundle,
    SENIOR_PM_PERSONA_PROMPT,
    load_bible_from_json,
    __version__,
)
from omni_director.telemetry import SECRET_PATTERN, verify_bundle_checksums
from omni_director.tools.c2pa_provenance import verify_model_lineage_2026
from omni_director.tools.html_compiler import compile_storyboard_html
from omni_director.tools.prompt_auditor import (
    audit_bible_inter_scene_continuity,
    audit_omni_scene_prompt,
    heal_omni_scene_prompt,
    compile_clean_omni_prompt,
)

logger = logging.getLogger("omni_director.council")

try:
    from google.adk.agents import BaseAgent
except ImportError:
    class BaseAgent:  # type: ignore[no-redef]
        def __init__(self, name: str, description: str = "", **kwargs: Any) -> None:
            self.name = name
            self.description = description
            self.kwargs = kwargs

        def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
            return context


FORBIDDEN_COUNCIL_MODEL_PATTERNS = [
    re.compile(r"gemini[-_]?(?:1\.5|2\.0|2\.5|3\.0|3\.1)", re.IGNORECASE),
    re.compile(r"veo[-_]?(?:3\.0|3\.1)", re.IGNORECASE),
    re.compile(r"imagen[-_]?3", re.IGNORECASE),
    re.compile(r"\b3\.1\b", re.IGNORECASE),
    re.compile(r"[-_]3\.1", re.IGNORECASE),
]


class ProductManagerAgent(BaseAgent):
    """Senior Product Manager agent (`council-product-manager`) inspecting product capabilities and driving daily feature releases."""

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    def __init__(
        self,
        config: Optional[DirectorConfig] = None,
        *,
        name: Optional[str] = None,
        persona_prompt: str = SENIOR_PM_PERSONA_PROMPT,
        **kwargs: Any,
    ) -> None:
        agent_name = name or "ProductManagerAgent"
        desc = kwargs.pop("description", kwargs.pop("instruction", persona_prompt))
        super().__init__(name=agent_name, description=desc, **kwargs)
        self.config = config or cfg
        self.persona = CouncilPersona.PRODUCT_MANAGER
        self.persona_prompt = persona_prompt

    def inspect_product(
        self,
        bible: Optional[MasterProductionBible] = None,
        bundle: Optional[ProductionBundle] = None,
        output_dir: Optional[Path] = None,
    ) -> List[ProductFeatureProposal]:
        """Inspects the product end-to-end and returns high-impact feature recommendations for the Product Council."""
        del bundle, output_dir
        project_ctx = f" for '{bible.project_title}'" if bible else ""
        return [
            ProductFeatureProposal(
                feature_id="PM-FEAT-001",
                title="Industry NLE Timeline & Production Export Suite (EDL, FCPXML, CSV, Call Sheet)",
                problem_statement=(
                    f"Commercial directors and post-production editors reviewing pre-vis storyboards{project_ctx} "
                    "need direct timeline handoff into DaVinci Resolve, Premiere Pro, and Final Cut Pro without manual re-logging."
                ),
                proposed_solution=(
                    "Ship omni_director.tools.nle_export (CMX 3600 24fps EDL, FCPXML v1.10, CSV shot list, "
                    "and Markdown Production Call Sheet) plus the `omni export` CLI subcommand."
                ),
                target_modules=["omni_director/tools/nle_export.py", "omni_director/cli.py"],
                priority="P0",
                status="implemented",
            ),
            ProductFeatureProposal(
                feature_id="PM-FEAT-002",
                title="SMPTE Dialogue Pacing Guardrail & Closed Caption Suite (SRT & WebVTT)",
                problem_statement=(
                    "Over-stuffed spoken dialogue in 8-second clips causes accelerated lip-sync artifacts, and "
                    "enterprise creative reviews require synchronized closed captions (SRT/VTT) and live animatic CC overlays."
                ),
                proposed_solution=(
                    "Ship omni_director.tools.dialogue with a 2.5 WPS speech-rate guardrail, SubRip (.srt) and "
                    "WebVTT (.vtt) compilers, and an interactive #animatic-cc-hud overlay ([C] hotkey) in the Cinema UI."
                ),
                target_modules=["omni_director/tools/dialogue.py", "omni_director/tools/html_compiler.py"],
                priority="P0",
                status="implemented",
            ),
            ProductFeatureProposal(
                feature_id="PM-FEAT-003",
                title="Multi-Cam Coverage & Conversational Delta Branching Engine",
                problem_statement=(
                    "Single-angle scene prompts limit editorial cutting flexibility; directors need A/B/C camera coverage "
                    "(24mm Master Wide, 50mm Dynamic Hero, 100mm Macro Insert) and Turn 2-4 conversational edit deltas."
                ),
                proposed_solution=(
                    "Ship omni_director.tools.coverage (generate_scene_coverage & synthesize_conversational_deltas) "
                    "and interactive .coverage-selector multi-cam tabs inside each scene card in the HTML5 animatic."
                ),
                target_modules=["omni_director/tools/coverage.py", "omni_director/tools/html_compiler.py"],
                priority="P0",
                status="implemented",
            ),
            ProductFeatureProposal(
                feature_id="PM-FEAT-004",
                title="ASC CDL Color Science, Cinematic Look Presets & SVG Filter Grading Engine",
                problem_statement=(
                    f"Commercial directors, DPs, and colorists reviewing storyboards{project_ctx} require industry-standard "
                    "ASC CDL transfer functions (Slope, Offset, Power, Saturation) and established look presets (Kodak 5219, "
                    "Fuji Eterna, Bleach Bypass, Teal & Orange) for DaVinci Resolve handoff rather than raw static hex codes."
                ),
                proposed_solution=(
                    "Implement AscCdlSpec and ColorLookSpec schemas, omni_director.tools.color_grade (Resolve CDL XML export "
                    "and EDL SOP/SAT comments), and real-time SVG filter grading matrices in the HTML5 animatic."
                ),
                target_modules=["omni_director/schemas.py", "omni_director/tools/color_grade.py", "omni_director/tools/html_compiler.py"],
                priority="P0",
                status="implemented",
            ),
            ProductFeatureProposal(
                feature_id="PM-FEAT-005",
                title="Dynamic Speed Ramping, Shutter Angle & Motion Timing Engine",
                problem_statement=(
                    f"High-velocity commercial spots{project_ctx} require dynamic speed ramping (time-warp keyframe curves) "
                    "and explicit 180° / 90° shutter angle calibration to eliminate temporal smearing or stutter in Gemini Omni video generation."
                ),
                proposed_solution=(
                    "Implement SpeedRampCurveSpec, shutter timing camera grammar in CraftCameraSpec, omni_director.tools.speed_ramp "
                    "(FCPXML timeMap export), prompt auditor shutter verification, and animatic velocity curve scrubbing."
                ),
                target_modules=["omni_director/schemas.py", "omni_director/tools/speed_ramp.py", "omni_director/tools/prompt_auditor.py", "omni_director/tools/html_compiler.py"],
                priority="P0",
                status="implemented",
            ),
            ProductFeatureProposal(
                feature_id="PM-FEAT-006",
                title="Interactive Diegetic Stem Audio Mixer & Metering Console",
                problem_statement=(
                    f"Omni Director models high-fidelity 4-stem sound design (Dialogue, Foley, Ambience, BGM){project_ctx}, "
                    "but pitch reviews require interactive channel balance, solo/mute auditioning, and broadcast loudness "
                    "(EBU R128 / ATSC A/85) compliance metering."
                ),
                proposed_solution=(
                    "Implement AudioStemMixerSpec, omni_director.tools.audio_mixer (DAW track manifests and loudness estimation), "
                    "and a slide-out 4-channel audio mixing desk with Web Audio acoustic synthesis and canvas LED VU meters in the animatic."
                ),
                target_modules=["omni_director/schemas.py", "omni_director/tools/audio_mixer.py", "omni_director/tools/html_compiler.py"],
                priority="P0",
                status="implemented",
            ),
            ProductFeatureProposal(
                feature_id="PM-FEAT-007",
                title="Cinematic Optical Lens & Sensor Framing Suite (Anamorphic Squeeze, Focal Length, Hyperfocal Depth & Viewfinder Guides)",
                problem_statement=(
                    f"Directors of Photography and camera operators reviewing storyboards{project_ctx} require precise optical modeling "
                    "(sensor format crop factors, 1.33x/1.5x/2.0x anamorphic squeeze, horizontal field of view, hyperfocal distance) "
                    "to avoid focal distortion in prompt generation, export lens metadata for ACs, and preview safe reticles directly in the animatic."
                ),
                proposed_solution=(
                    "Ship SensorFormat, AnamorphicSqueeze, OpticalLensSpec schemas, omni_director.tools.optical_lens "
                    "(FOV and hyperfocal distance formulas, CSV metadata export, CRAFT optical prompt tokens), "
                    "prompt auditor lens token verification, and Viewfinder Safe Guides HUD (#btn-viewfinder-animatic / #animatic-viewfinder-overlay [V] hotkey) in the HTML5 animatic."
                ),
                target_modules=["omni_director/schemas.py", "omni_director/tools/optical_lens.py", "omni_director/tools/prompt_auditor.py", "omni_director/tools/html_compiler.py"],
                priority="P0",
                status="implemented",
            ),
            ProductFeatureProposal(
                feature_id="PM-FEAT-008",
                title="Virtual Production LED Volume & Unreal Engine Stage Manifest / ICVFX Suite",
                problem_statement=(
                    f"High-end commercial productions{project_ctx} increasingly film on curved LED volume stages with Unreal Engine 5 in-camera visual effects (ICVFX); "
                    "production crews require nDisplay frustum tracking manifests, DMX lighting patch tables, and visual stage geometry blueprints directly from the storyboard bible."
                ),
                proposed_solution=(
                    "Ship LedWallGeometry, DmxLightingFixture, VirtualProductionStageSpec schemas, omni_director.tools.virtual_production "
                    "(Unreal Engine nDisplay manifest JSON export, DMX lighting console patch CSV, frustum prompt tokens), "
                    "and an interactive Virtual Production Stage Modal (#btn-vp-stage-animatic / #animatic-vp-stage-modal [P] hotkey) in the HTML5 animatic."
                ),
                target_modules=["omni_director/schemas.py", "omni_director/tools/virtual_production.py", "omni_director/tools/prompt_auditor.py", "omni_director/tools/html_compiler.py"],
                priority="P0",
                status="implemented",
            ),
            ProductFeatureProposal(
                feature_id="PM-FEAT-009",
                title="Kinetic Motion Control (MoCo) Rig & 6-DOF Camera Kinematics Engine",
                problem_statement=(
                    f"Complex kinetic camera maneuvers{project_ctx} require precision mechanical motion control "
                    "(Bolt Cinebot, Technocrane, Cablecam, Steadicam, FPV Drone) and 6-DOF trajectory waypoint tracking "
                    "(X/Y/Z position, Roll/Pitch/Yaw orientation, velocity, acceleration) to guarantee repeatable camera paths "
                    "and exportable camera tracking data for VFX pipelines (Nuke, Maya, Blender, Unreal Engine)."
                ),
                proposed_solution=(
                    "Ship MotionControlRigType, TrajectoryWaypoint6DOF, MocoRigSpec schemas, omni_director.tools.moco_kinematics "
                    "(path distance and velocity calculation, JSON, CSV, FBX ASCII camera transform exports), CRAFT camera MoCo prompt tokens, "
                    "prompt auditor MoCo token verification, and an interactive MoCo Trajectory HUD (#btn-moco-animatic / #animatic-moco-hud [K] hotkey) in the animatic."
                ),
                target_modules=["omni_director/schemas.py", "omni_director/tools/moco_kinematics.py", "omni_director/tools/prompt_auditor.py", "omni_director/tools/html_compiler.py"],
                priority="P0",
                status="implemented",
            ),
            ProductFeatureProposal(
                feature_id="PM-FEAT-010",
                title="Volumetric Atmospheric & Studio Lighting Rig Simulator",
                problem_statement=(
                    f"High-end cinematic visuals{project_ctx} require calibrated multi-point studio lighting "
                    "(Key, Fill, Rim, Kicker, Practicals, Ambient) with color temperature (Kelvin), photometric illuminance (Lux), "
                    "diffusion grades, particulate atmospheric haze/fog modeling, and lighting contrast ratios (Key:Fill, Key:Rim) "
                    "to eliminate flat lighting and export gaffer setup call sheets."
                ),
                proposed_solution=(
                    "Ship LightingFixtureRole, DiffusionGrade, ParticulateHazeType, StudioLightFixtureSpec, AtmosphericHazeSpec, "
                    "LightingRigSpec schemas, omni_director.tools.lighting_rig (Key:Fill & Key:Rim photometric contrast formulas, "
                    "lighting plot JSON and gaffer equipment CSV exports), prompt auditor lighting tokens, and an interactive "
                    "Studio Gaffer HUD (#btn-gaffer-animatic / #animatic-gaffer-hud [G] hotkey) in the animatic."
                ),
                target_modules=["omni_director/schemas.py", "omni_director/tools/lighting_rig.py", "omni_director/tools/prompt_auditor.py", "omni_director/tools/html_compiler.py"],
                priority="P0",
                status="implemented",
            ),
            ProductFeatureProposal(
                feature_id="PM-FEAT-011",
                title="Domain-Calibrated Depth of Field (DoF), Iris Aperture & Optical Focus Engine",
                problem_statement=(
                    f"Commercial film genres{project_ctx} require domain-specific optical focus depth behavior—"
                    "from macro razor-thin depth of field in culinary ASMR (T1.4 on 100mm) and creamy 2x oval bokeh in luxury fashion portraiture (T1.8 on 85mm), "
                    "to hyperfocal deep tracking in automotive action (T5.6 on 24mm) and panoramic infinite focus in architecture (T8.0 on 18mm)—"
                    "to prevent optical inconsistency across scenes."
                ),
                proposed_solution=(
                    "Ship DomainDofSpec schema in omni_director.schemas, calibrate get_domain_dof_spec() across all 6 commercial domain archetypes "
                    "in omni_director.presets, bind dof_spec to ScenePromptSpec and master_dof_spec to MasterProductionBible, "
                    "and integrate domain DoF verification into ProductCouncilOrchestrator."
                ),
                target_modules=["omni_director/schemas.py", "omni_director/presets.py", "omni_director/agents/council.py"],
                priority="P0",
                status="implemented",
            ),
            ProductFeatureProposal(
                feature_id="PM-FEAT-012",
                title="Domain 3D LUT Color Science & Film Emulation (.cube) Suite",
                problem_statement=(
                    f"Cinematic production pipelines{project_ctx} require authentic color science and film stock emulation 3D LUTs (.cube)—"
                    "such as warm Kodak 5219 Vision3 for culinary, bleach bypass silver for high-contrast fashion, metallic teal & orange for automotive, "
                    "and cold surgical Rec.709 for cleanroom tech—to guide professional colorists and post-production grading."
                ),
                proposed_solution=(
                    "Ship DomainLutSpec schema in omni_director.schemas, calibrate get_domain_lut_spec() across all 6 commercial domain archetypes "
                    "in omni_director.presets, bind lut_spec to ScenePromptSpec and master_lut_spec to MasterProductionBible, "
                    "export 33x33x33 .cube metadata, and integrate 3D LUT verification into ProductCouncilOrchestrator."
                ),
                target_modules=["omni_director/schemas.py", "omni_director/presets.py", "omni_director/agents/council.py"],
                priority="P0",
                status="implemented",
            ),
            ProductFeatureProposal(
                feature_id="PM-FEAT-013",
                title="Spatial Audio & Binaural Soundfield Acoustic Simulation (Dolby Atmos 7.1.4 & HOA Ambisonics)",
                problem_statement=(
                    f"Enterprise cinematic productions and game engines{project_ctx} require physics-based spatial audio modeling—"
                    "including 7.1.4 Dolby Atmos speaker beds, Higher-Order Ambisonics (HOA 3rd-order), Sabine and Eyring reverberation decay (RT60), "
                    "wall material acoustic absorption coefficients, 3D Vector Base Amplitude Panning (VBAP), and Audio Definition Model (ADM) metadata—"
                    "to eliminate flat stereo audio and deliver immersive binaural soundfields."
                ),
                proposed_solution=(
                    "Ship SpatialCoordinate3D, AcousticRoomImpulseResponse, SpatialAudioObjectSpec, and SpatialAudioSoundfieldSpec schemas, "
                    "omni_director.tools.spatial_audio (Sabine/Eyring RT60 formulas, 7.1.4 VBAP matrix, ITU-R BS.2076 ADM JSON and Ambisonics CSV exports), "
                    "CRAFT diegetic spatial audio prompt tokens, prompt auditor spatial compliance rules, and an interactive Spatial Audio Console "
                    "(#btn-spatial-animatic / #animatic-spatial-hud [S] hotkey) in the dark-room animatic."
                ),
                target_modules=["omni_director/schemas.py", "omni_director/tools/spatial_audio.py", "omni_director/tools/prompt_auditor.py", "omni_director/tools/html_compiler.py", "omni_director/tools/nle_export.py"],
                priority="P0",
                status="implemented",
            ),
            ProductFeatureProposal(
                feature_id="PM-FEAT-014",
                title="Advanced Multi-Pass VFX Compositing & Render Layer Manifest Engine (OpenEXR & Cryptomatte)",
                problem_statement=(
                    f"Professional studio VFX pipelines (Foundry Nuke, Maya, Blender, Unreal Engine){project_ctx} require multi-pass "
                    "render layer decomposition—such as Beauty RGBA, Direct/Indirect Diffuse, Specular Reflection, Transmission/Refraction, "
                    "Subsurface Scattering, Emission, Z-Depth, World Normals, Motion Vectors, and 32-bit Murmur3 hex-hashed Cryptomatte object/material IDs—"
                    "to allow seamless live-action visual effects integration rather than un-decomposed flat video renders."
                ),
                proposed_solution=(
                    "Ship VfxRenderPassType, VfxLayerChannelSpec, CryptomatteManifestSpec, and VfxCompositingManifestSpec schemas, "
                    "omni_director.tools.vfx_compositor (16/32-bit OpenEXR channel manifests, Murmur3 Cryptomatte hash generator, and Foundry Nuke .nk template generator), "
                    "prompt auditor VFX compositing tokens, NLE bundle export, and an interactive Multi-Pass VFX Compositing HUD "
                    "(#btn-vfx-animatic / #animatic-vfx-hud [X] hotkey) in the dark-room animatic."
                ),
                target_modules=["omni_director/schemas.py", "omni_director/tools/vfx_compositor.py", "omni_director/tools/prompt_auditor.py", "omni_director/tools/html_compiler.py", "omni_director/tools/nle_export.py"],
                priority="P0",
                status="implemented",
            ),
            ProductFeatureProposal(
                feature_id="PM-FEAT-015",
                title="HDR10 / HLG Broadcast Color Volume & Mastering Display Metadata Engine (SMPTE ST 2084 PQ & ST 2086)",
                problem_statement=(
                    f"High-end cinematic theatrical distribution and commercial streaming broadcasters (Apple TV+, Netflix, BBC, YouTube HDR){project_ctx} "
                    "require rigorous SMPTE ST 2084 PQ (Perceptual Quantizer) and ARIB STD-B67 HLG color volume mastering metadata—including SMPTE ST 2086 "
                    "mastering display color primaries, white point chromaticity, peak/minimum luminance nits, MaxCLL (Maximum Content Light Level), "
                    "MaxFALL (Maximum Frame Average Light Level), and ACES/Reinhard/BT.2446 tone mapping—to prevent highlight clipping and gamut distortion."
                ),
                proposed_solution=(
                    "Implement HdrMetadataSpec, HdrMasteringDisplaySpec, and SceneHdrReport schemas, omni_director.tools.hdr_signal "
                    "(pure-Python PQ/HLG transforms, EOTF/OETF curves, MaxCLL/MaxFALL calculations, tone mapping operators, HDR10 JSON, HLG XML, "
                    "DaVinci Resolve HDR XML export), CRAFT HDR prompt tokens, prompt auditor calibration rules, and an interactive HDR Color Volume HUD "
                    "(#btn-hdr-animatic / #animatic-hdr-hud [H] hotkey) with HTML5 Canvas waveform monitor in the dark-room animatic."
                ),
                target_modules=["omni_director/schemas.py", "omni_director/tools/hdr_signal.py", "omni_director/presets.py", "omni_director/tools/prompt_auditor.py", "omni_director/tools/html_compiler.py", "omni_director/tools/nle_export.py"],
                priority="P0",
                status="implemented",
            ),
            ProductFeatureProposal(
                feature_id="PM-FEAT-016",
                title="1st AD Script Breakdown & Interactive Stripboard Production Scheduler Engine (Movie Magic & DOOD)",
                problem_statement=(
                    f"Professional cinematic and commercial production workflows{project_ctx} require standardized 1st Assistant Director (1st AD) "
                    "production scheduling: automated 1/8th-page scene breakdown across 12 industry categories (Cast, Extras, Stunts, Vehicles, Props, "
                    "SFX, VFX, Wardrobe, Makeup, Sound, Special Equipment, Animals), Hollywood color-coded stripboard strips (Yellow/Blue/White/Green), "
                    "shooting day breaks, and Day-Out-of-Days (DOOD) talent matrices enforcing SAG-AFTRA 12-hour turnaround rest compliance."
                ),
                proposed_solution=(
                    "Implement ScriptBreakdownSheet, StripboardStripSpec, MasterStripboardScheduleSpec, and DayOutOfDaysRecord schemas, "
                    "omni_director.tools.stripboard_scheduler (1/8th-page breakdown generator, stripboard strip color-coding, DOOD matrix with SAG-AFTRA "
                    "12-hour turnaround validation, Movie Magic XML, Stripboard CSV, DOOD CSV export), CRAFT 1st AD prompt tokens, and an interactive "
                    "Stripboard & DOOD Production Console (#btn-stripboard-animatic / #animatic-stripboard-hud [B] hotkey) in the dark-room animatic."
                ),
                target_modules=["omni_director/schemas.py", "omni_director/tools/stripboard_scheduler.py", "omni_director/presets.py", "omni_director/tools/prompt_auditor.py", "omni_director/tools/html_compiler.py", "omni_director/tools/nle_export.py"],
                priority="P0",
                status="implemented",
            ),
            ProductFeatureProposal(
                feature_id="PM-FEAT-017",
                title="Physical Film Stock Emulation & Chemical Chemistry Engine (Microscopic Grain, Halation & Gate Weave)",
                problem_statement=(
                    f"Directors of Photography and colorists reviewing storyboards{project_ctx} require authentic photochemical film stock "
                    "emulation—including silver halide crystal RMS granularity, dye cloud diffusion, rem-jet anti-halation layer absorption, "
                    "gate weave mechanical jitter (±3.5μm to ±12.0μm), push/pull development chemistry (±2.0 EV), and DaVinci Resolve DCTL shader exports—"
                    "to eliminate clinical digital video artifacts and ensure cinematic analog texture."
                ),
                proposed_solution=(
                    "Implement FilmStockManufacturer, FilmGaugeFormat, GrainPhysicsSpec, HalationPhysicsSpec, GateWeavePhysicsSpec, and FilmStockSpec schemas, "
                    "omni_director.tools.film_emulation (RMS grain density formulas, halation PSF simulation, gate weave sinusoidal jitter, Kodak/Fuji presets, "
                    "DaVinci Resolve DCTL shader generator, Avid ALE log, Film Stock JSON export), CRAFT film emulation prompt tokens ([FILM_STOCK: ...]), "
                    "prompt auditor photochemical verification rules, and an interactive Film Stock Emulation HUD in the dark-room animatic."
                ),
                target_modules=["omni_director/schemas.py", "omni_director/tools/film_emulation.py", "omni_director/presets.py", "omni_director/tools/prompt_auditor.py", "omni_director/tools/html_compiler.py", "omni_director/tools/nle_export.py"],
                priority="P0",
                status="implemented",
            ),
            ProductFeatureProposal(
                feature_id="PM-FEAT-018",
                title="SMPTE 12M Timecode Sync, Digital Clapper Slate & ASC-MHL Offload Manifest Engine",
                problem_statement=(
                    f"Production sound mixers, script supervisors, and DIT offload technicians{project_ctx} require standardized SMPTE 12M "
                    "linear/drop-frame timecode synchronization (HH:MM:SS:FF / HH:MM:SS;FF), production clapper slates (Scene/Take/Roll/Filter/FPS), "
                    "and American Society of Cinematographers Media Hash List (ASC-MHL v2.0 XML) cryptographically sealed offload manifests (MD5, SHA-1, C4) "
                    "to guarantee picture-to-sound synchronization and dual-destination archival data integrity."
                ),
                proposed_solution=(
                    "Implement Smpte12MTimecodeSpec, ClapperSlateSpec, AscMhlHashEntry, AscMhlManifestSpec, and MasterProductionSlateSpec schemas, "
                    "omni_director.tools.clapper_slate (SMPTE 12M frame conversion, drop-frame alignment, audio sync offset calculation, ASC-MHL v2.0 XML generator, "
                    "clapper slate CSV log, Avid ALE sound sync log export), CRAFT clapper slate prompt tokens ([CLAPPER_SLATE: ...]), prompt auditor slate verification rules, "
                    "and an interactive Digital Clapper Slate Console with clapper arm animation in the dark-room animatic."
                ),
                target_modules=["omni_director/schemas.py", "omni_director/tools/clapper_slate.py", "omni_director/presets.py", "omni_director/tools/prompt_auditor.py", "omni_director/tools/html_compiler.py", "omni_director/tools/nle_export.py"],
                priority="P0",
                status="implemented",
            ),
            ProductFeatureProposal(
                feature_id="PM-FEAT-019",
                title="Aerial Drone Flight Path Simulator & FAA Part 107 Airspace Compliance Engine",
                problem_statement=(
                    f"Aerial directors of photography and remote pilot in command (RPIC) operators{project_ctx} require standardized 3D waypoint "
                    "navigation (latitude/longitude/altitude AGL), 3-axis gimbal pitch/yaw trajectories, solar ephemeris calculation (golden hour/blue hour/solar noon), "
                    "dynamic wind drift vectors, and strict FAA Part 107 regulatory compliance (120m / 400ft AGL ceiling, 45 m/s speed limits) with professional "
                    "KML, GPX, and CSV flight manifests to ensure aerial shot safety and cinematographic continuity."
                ),
                proposed_solution=(
                    "Implement DroneRigType, FlightProfile, FlightWaypointSpec, GimbalTrajectorySpec, WindVectorSpec, SolarEphemerisSpec, DroneFlightPathSpec, and "
                    "MasterDroneSpec schemas, omni_director.tools.drone_flight / drone_aerial (3D waypoint interpolation, haversine distance, solar position math, "
                    "wind drift deflection, KML flight path export, GPX GPS track export, drone flight sheet CSV/MD, flight manifest JSON), CRAFT drone flight prompt "
                    "tokens ([DRONE_FLIGHT: ...]), prompt auditor aerial compliance rules, and an interactive 3D Drone Flight Path HUD in the dark-room animatic."
                ),
                target_modules=["omni_director/schemas.py", "omni_director/tools/drone_flight.py", "omni_director/presets.py", "omni_director/tools/prompt_auditor.py", "omni_director/tools/html_compiler.py", "omni_director/tools/nle_export.py"],
                priority="P0",
                status="implemented",
            ),
            ProductFeatureProposal(
                feature_id="PM-FEAT-020",
                title="AICP Commercial Production Budget & Bid Form Estimator",
                problem_statement=(
                    f"Commercial line producers, executive producers, and agency procurement directors{project_ctx} require standardized Association of Independent "
                    "Commercial Producers (AICP) commercial production budgeting across all canonical sections A through K (Pre-Production/Wrap, Production Crew, "
                    "Location & Travel, Props & Wardrobe, Studio & Equipment, Film Raw Stock/DIT, Director/Creative, Talent & Session, Editorial/Post, "
                    "Contingency & Insurance, Production Markups/Fees) with automated tier-calibrated top sheets and CSV/JSON/Markdown exports to validate "
                    "commercial feasibility and agency procurement compliance."
                ),
                proposed_solution=(
                    "Implement AicpSectionCode, AicpLineItemSpec, AicpSectionBudgetSpec, AicpTopSheetSummarySpec, and MasterAicpBidSpec schemas, "
                    "omni_director.tools.aicp_budget (line item rate calculation, overtime/fringes compounding, production markup application, top sheet synthesis, "
                    "AICP bid sheet CSV generator, production budget top sheet Markdown generator, bid manifest JSON export), domain budget tier calibration "
                    "($95k-$480k across 6 archetypes), and an interactive AICP Commercial Production Bid HUD in the dark-room animatic."
                ),
                target_modules=["omni_director/schemas.py", "omni_director/tools/aicp_budget.py", "omni_director/presets.py", "omni_director/tools/html_compiler.py", "omni_director/tools/nle_export.py"],
                priority="P0",
                status="implemented",
            ),
            ProductFeatureProposal(
                feature_id="PM-FEAT-021",
                title="Multi-Aspect Social Reframe, Safe-Zone Cropping & Cutdown Delivery Engine",
                problem_statement=(
                    f"Agency social producers and finishing editors{project_ctx} must deliver 16:9 broadcast masters alongside "
                    "9:16 TikTok/Instagram Reels/YouTube Shorts, 4:5 Meta/LinkedIn, and 1:1 feeds without subject cropping or "
                    "platform UI overlay collisions, plus frame-accurate :30s, :15s, and :06s editorial cutdowns."
                ),
                proposed_solution=(
                    "Implement DeliverableAspectRatio, CutdownFormatType, SocialDeliveryPlatform, ReframePanMode, "
                    "AspectCropWindowSpec, CutdownSegmentSpec, CutdownVersionSpec, SceneReframeSpec, and "
                    "DeliveryReframeManifestSpec schemas; omni_director.tools.delivery_reframe (COI crop window math, "
                    "platform safe-zone validation, cutdown EDL/FCPXML/CSV/JSON exporters, [REFRAME: ...] prompt tokens); "
                    "6-domain calibration via get_domain_reframe_manifest(); and an interactive Multi-Aspect Reframe HUD [R] "
                    "in the dark-room animatic. Acceptance criteria: safe_zone_audit_passed across all 6 archetypes, "
                    "deliverable EDL/FCPXML/CSV/JSON exports, and HUD #btn-reframe-animatic / #animatic-reframe-hud."
                ),
                target_modules=[
                    "omni_director/schemas.py",
                    "omni_director/tools/delivery_reframe.py",
                    "omni_director/presets.py",
                    "omni_director/tools/prompt_auditor.py",
                    "omni_director/tools/html_compiler.py",
                    "omni_director/tools/nle_export.py",
                ],
                priority="P0",
                status="implemented",
            ),
            ProductFeatureProposal(
                feature_id="PM-FEAT-022",
                title="Broadcast Technical QC, ITU-R BT.1702 PSE Flash-Safety, Loudness & Rights Clearance Suite",
                problem_statement=(
                    f"Commercial trafficking teams and network standards-and-practices engineers{project_ctx} require pre-delivery "
                    "ITU-R BT.1702 photosensitive epilepsy (PSE) <=3Hz flash-safety verification, ATSC A/85 (-24 LKFS) & EBU R128 "
                    "(-23 LUFS) loudness compliance, Ad-ID/ISCI head-slate specs, and SAG-AFTRA/music/location/FAA legal "
                    "clearance tracking before broadcast trafficking."
                ),
                proposed_solution=(
                    "Implement BroadcastLoudnessStandard, ClearanceCategory, ClearanceStatus, QcVerdictStatus, "
                    "BroadcastTraffickingSlateSpec, LoudnessComplianceSpec, PseFlashCheckSpec, ClearanceRecordSpec, "
                    "SceneQcProfileSpec, and MasterBroadcastQcSpec schemas; omni_director.tools.broadcast_qc (PSE flash evaluator, "
                    "loudness validator, rights clearance matrix, QC certificate Markdown/CSV/JSON exporters, [BROADCAST_QC: ...] "
                    "prompt tokens); 6-domain calibration via get_domain_broadcast_qc_spec(); and an interactive Broadcast QC & "
                    "Trafficking HUD [Q] in the dark-room animatic. Acceptance criteria: 0 PSE (>3Hz) failures, ATSC A/85 or EBU R128 "
                    "PASS across all 6 archetypes, and HUD #btn-qc-animatic / #animatic-qc-hud."
                ),
                target_modules=[
                    "omni_director/schemas.py",
                    "omni_director/tools/broadcast_qc.py",
                    "omni_director/presets.py",
                    "omni_director/tools/prompt_auditor.py",
                    "omni_director/tools/html_compiler.py",
                    "omni_director/tools/nle_export.py",
                ],
                priority="P0",
                status="implemented",
            ),
            ProductFeatureProposal(
                feature_id="PM-FEAT-023",
                title="Inter-Scene Editorial Continuity, 180-Degree Axis & Overhead Blocking Floorplan Engine",
                problem_statement=(
                    f"Script supervisors, directors of photography, and finishing editors{project_ctx} need automated "
                    "180-degree line-of-action enforcement, 30-degree camera angle delta validation, eyeline match checks, "
                    "Kelvin continuity bounds (<=1500K across cuts), and overhead 2D stage blocking floorplans to eliminate "
                    "screen-direction reversals and axial jump cuts prior to rendering."
                ),
                proposed_solution=(
                    "Implement ScreenDirection, ShotScaleSize, EditorialCutType, StageBlockingEntity, CameraAxisPlacement, "
                    "InterSceneCutCheckSpec, SceneBlockingSpec, and MasterContinuityBlockingSpec schemas; "
                    "omni_director.tools.continuity_blocking (evaluate_180_axis_and_30_rule, synthesize_scene_blocking, "
                    "continuity_log.csv, blocking_floorplan.svg, continuity_manifest.json exporters, [CONTINUITY_AXIS: ...] "
                    "prompt tokens); audit_bible_inter_scene_continuity in prompt_auditor.py; 6-domain calibration via "
                    "get_domain_continuity_blocking_spec(); and an interactive 180-Degree Blocking & Continuity HUD [W] "
                    "(#btn-blocking-animatic, #animatic-blocking-hud, #blocking-floorplan-svg) in the dark-room animatic."
                ),
                target_modules=[
                    "omni_director/schemas.py",
                    "omni_director/tools/continuity_blocking.py",
                    "omni_director/presets.py",
                    "omni_director/tools/prompt_auditor.py",
                    "omni_director/tools/html_compiler.py",
                    "omni_director/tools/html_hud_v212.py",
                    "omni_director/tools/nle_export.py",
                ],
                priority="P0",
                status="implemented",
            ),
            ProductFeatureProposal(
                feature_id="PM-FEAT-024",
                title="Client Review, Frame-Accurate Pin Annotation, NLE Markers & Revision Sign-Off Engine",
                problem_statement=(
                    f"Agency creatives, brand clients, directors, and post producers{project_ctx} require frame-accurate "
                    "spatial pin annotations on storyboard frames, DaVinci Resolve/FCPXML/Frame.io v4 marker round-tripping, "
                    "deterministic edit-delta compilation, and a strict live-render sign-off gate before committing "
                    "billable Gemini Omni video generation credits."
                ),
                proposed_solution=(
                    "Implement ReviewApprovalStatus, ReviewerRole, MarkerColorTag, ReviewPinCoordinate, "
                    "ReviewAnnotationSpec, SceneReviewSignoffSpec, and MasterClientReviewSpec schemas; "
                    "omni_director.tools.review_notes (compile_review_note_to_delta, review_markers.edl, "
                    "review_markers.fcpxml, review_notes_frameio.json, review_notes.csv, client_signoff_report.md exporters, "
                    "[REVIEW_GATE: ...] prompt tokens); 6-domain calibration via get_domain_client_review_spec(); and an "
                    "interactive Client Review & Frame Pin Annotation HUD [N] (#btn-review-animatic, #animatic-review-hud, "
                    "#review-pin-stage) in the dark-room animatic."
                ),
                target_modules=[
                    "omni_director/schemas.py",
                    "omni_director/tools/review_notes.py",
                    "omni_director/presets.py",
                    "omni_director/tools/prompt_auditor.py",
                    "omni_director/tools/html_compiler.py",
                    "omni_director/tools/html_hud_v212.py",
                    "omni_director/tools/nle_export.py",
                ],
                priority="P0",
                status="implemented",
            ),
            ProductFeatureProposal(
                feature_id="PM-FEAT-025",
                title="C2PA Content Credentials v2.1, EU AI Act Art. 50 & Talent Likeness Provenance Engine",
                problem_statement=(
                    f"Enterprise broadcasters, legal compliance teams, and agency distributors{project_ctx} require "
                    "cryptographically verifiable C2PA v2.1 Content Credentials, EU AI Act Article 50 synthetic disclosure "
                    "tiers, strict 2026 Gemini Model Matrix lineage verification (zero legacy models), and SAG-AFTRA "
                    "digital replica / talent likeness consent gating before rendering or publishing."
                ),
                proposed_solution=(
                    "Implement SyntheticDisclosureTier, C2paActionType, LikenessConsentStatus, C2paIngredientSpec, "
                    "C2paAssertionActionSpec, TalentLikenessRecordSpec, SceneC2paProvenanceSpec, and "
                    "MasterC2paProvenanceSpec schemas; omni_director.tools.c2pa_provenance (verify_model_lineage_2026, "
                    "compute_prompt_lineage_digest, c2pa_manifest.json, ai_disclosure_certificate.md, "
                    "likeness_consent_ledger.csv exporters, [C2PA_PROVENANCE: ...] prompt tokens); 6-domain calibration "
                    "via get_domain_c2pa_provenance_spec(); and an interactive C2PA Provenance & Content Credentials HUD "
                    "[Y] (#btn-c2pa-animatic, #animatic-c2pa-hud, #c2pa-lineage-svg) in the dark-room animatic."
                ),
                target_modules=[
                    "omni_director/schemas.py",
                    "omni_director/tools/c2pa_provenance.py",
                    "omni_director/presets.py",
                    "omni_director/tools/prompt_auditor.py",
                    "omni_director/tools/html_compiler.py",
                    "omni_director/tools/html_hud_v212.py",
                    "omni_director/tools/html_hud_v213.py",
                    "omni_director/cli.py",
                ],
                priority="P0",
                status="implemented",
            ),
            ProductFeatureProposal(
                feature_id="PM-FEAT-026",
                title="On-Set Stunt, Pyro/SFX, Rigging & Environmental Safety Risk Assessment Matrix / JSA Engine",
                problem_statement=(
                    f"Physical production units, 1st Assistant Directors, Stunt Coordinators, and Unit Safety Officers{project_ctx} "
                    "require physics-calibrated kinetic exclusion zones (MoCo arm reach + E-stop braking distance, FAA Part 107 "
                    "UAV standoff perimeters, stunt vehicle braking buffers), 5x5 Job Safety Analysis (JSA) hazard matrices "
                    "aligned with CSATF Safety Bulletins, and standby medical/fire/E-stop emergency protocols prior to stage call."
                ),
                proposed_solution=(
                    "Implement SafetyHazardCategory, RiskSeverityLevel, SafetySignoffStatus, SafetyHazardControlSpec, "
                    "StandbyMedicalAndEmergencySpec, SceneSafetyRiskSpec, and MasterSafetyRiskSpec schemas; "
                    "omni_director.tools.safety_risk (calculate_kinetic_exclusion_zone_m, assess_scene_hazards, "
                    "safety_bulletin.md, safety_jsa_matrix.csv, safety_risk_manifest.json exporters, [SAFETY_JSA: ...] "
                    "prompt tokens); 6-domain calibration via get_domain_safety_risk_spec(); and an interactive On-Set Safety "
                    "Risk & Exclusion Perimeter HUD [Z] (#btn-safety-animatic, #animatic-safety-hud, #safety-perimeter-svg) "
                    "in the dark-room animatic."
                ),
                target_modules=[
                    "omni_director/schemas.py",
                    "omni_director/tools/safety_risk.py",
                    "omni_director/presets.py",
                    "omni_director/tools/prompt_auditor.py",
                    "omni_director/tools/html_compiler.py",
                    "omni_director/tools/html_hud_v212.py",
                    "omni_director/tools/html_hud_v213.py",
                    "omni_director/cli.py",
                ],
                priority="P0",
                status="implemented",
            ),
            ProductFeatureProposal(
                feature_id="PM-FEAT-027",
                title="Multi-Territory Localization, ADR Dubbing Studio, Lip-Sync Timing & Safe-Supers Engine",
                problem_statement=(
                    f"Global brand campaigns and multi-territory broadcast distributors{project_ctx} require "
                    "deterministic ADR dubbing cue sheets with pre-roll beeps, syllable/WPS lip-sync drift gating, "
                    "RTL/CJK text-expansion modeling, on-screen graphic supers safe-zone enforcement, and W3C "
                    "IMSC1 TTML / SRT / VTT timed-text packages prior to international trafficking."
                ),
                proposed_solution=(
                    "Implement LocaleSyncStatus, SupersSafeStatus, LocalizedLineSpec, LocaleAdaptationSpec, "
                    "AdrSpottingCueSpec, and LocalizationManifestSpec schemas; omni_director.tools.localization_adr "
                    "(LOCALE_PROFILES, compile_localization_manifest, synthesize_default_localization_manifest, "
                    "audit_locale_lip_sync_and_supers, format_localization_prompt_token, export_imsc1_ttml, "
                    "export_adr_cue_sheet_csv, export_localization_manifest_json, export_localized_subtitles, "
                    "export_localization_bundle, [LOCALIZATION_ADR: ...] prompt tokens); 6-domain calibration via "
                    "get_domain_localization_spec(); and an interactive Multi-Language Localization & ADR Dubbing "
                    "Studio HUD [I] (#btn-localization-animatic, #animatic-localization-hud, #localization-lipsync-svg) "
                    "in the dark-room animatic."
                ),
                target_modules=[
                    "omni_director/schemas.py",
                    "omni_director/tools/localization_adr.py",
                    "omni_director/presets.py",
                    "omni_director/tools/prompt_auditor.py",
                    "omni_director/tools/html_compiler.py",
                    "omni_director/tools/html_hud_v212.py",
                    "omni_director/tools/html_hud_v214.py",
                    "omni_director/agents/agent.py",
                    "omni_director/agents/council.py",
                    "omni_director/cli.py",
                ],
                priority="P0",
                status="implemented",
            ),
            ProductFeatureProposal(
                feature_id="PM-FEAT-028",
                title="Editorial J-Cut / L-Cut Audio Bridge, BPM Beat-Grid Sync & Music/Foley Spotting Engine",
                problem_statement=(
                    f"Commercial editors, music supervisors, and re-recording mixers{project_ctx} require "
                    "frame-accurate split-edit audio bridges (J-Cut pre-lap, L-Cut overhang, and JL overlap), "
                    "24fps BPM beat-grid locking across picture cuts, downbeat-aligned music/foley spotting sheets, "
                    "and CMX 3600 split-edit EDL deliverables."
                ),
                proposed_solution=(
                    "Implement AudioBridgeType, EditBridgeSpec, SpottingCueEntry, and SpottingManifestSpec schemas; "
                    "omni_director.tools.editorial_spotting (compute_bpm_beat_grid, build_spotting_manifest, "
                    "synthesize_default_spotting_manifest, format_spotting_prompt_token, export_split_edit_edl, "
                    "export_spotting_cue_sheet_csv, export_spotting_sheet_md, export_spotting_manifest_json, "
                    "export_spotting_bundle, [SPOTTING_SYNC: ...] prompt tokens); 6-domain calibration via "
                    "get_domain_spotting_spec(); and an interactive Editorial Spotting & Beat-Grid HUD [J] "
                    "(#btn-spotting-animatic, #animatic-spotting-hud, #spotting-timeline-svg) in the dark-room animatic."
                ),
                target_modules=[
                    "omni_director/schemas.py",
                    "omni_director/tools/editorial_spotting.py",
                    "omni_director/presets.py",
                    "omni_director/tools/prompt_auditor.py",
                    "omni_director/tools/html_compiler.py",
                    "omni_director/tools/html_hud_v212.py",
                    "omni_director/tools/html_hud_v214.py",
                    "omni_director/agents/agent.py",
                    "omni_director/agents/council.py",
                    "omni_director/cli.py",
                ],
                priority="P0",
                status="implemented",
            ),
            ProductFeatureProposal(
                feature_id="PM-FEAT-029",
                title="Stereoscopic 3D (S3D) & Apple Vision Pro Immersive Video",
                problem_statement=(
                    f"Spatial computing platforms and immersive theater campaigns{project_ctx} require "
                    "physically calibrated stereoscopic interaxial baselines, convergence plane tracking, "
                    "<=3.0% positive retinal parallax comfort gating, and Apple Vision Pro MV-HEVC (hvc1) "
                    "metadata packages across every scene."
                ),
                proposed_solution=(
                    "Implement StereoscopicRigType, SpatialVideoFormat, S3DCameraSpec, SceneStereoscopicSpec, "
                    "and MasterSpatialVideoSpec schemas; omni_director.tools.stereoscopic_3d "
                    "(calculate_parallax_budget, compute_mv_hevc_metadata, compile_s3d_manifest, "
                    "format_s3d_prompt_token, export_s3d_csv, export_spatial_manifest_json, export_s3d_bundle, "
                    "[S3D-RIG: ...] prompt tokens); 6-domain calibration via get_domain_s3d_spec(); and an "
                    "interactive S3D Stereoscopy & MV-HEVC Spatial HUD []] (#btn-s3d-animatic, "
                    "#modal-s3d-stereography, #s3d-anaglyph-canvas, #s3d-depth-svg) in the dark-room animatic."
                ),
                target_modules=[
                    "omni_director/schemas.py",
                    "omni_director/tools/stereoscopic_3d.py",
                    "omni_director/presets.py",
                    "omni_director/tools/prompt_auditor.py",
                    "omni_director/tools/html_compiler.py",
                    "omni_director/tools/html_hud_v212.py",
                    "omni_director/tools/html_hud_v215.py",
                    "omni_director/agents/agent.py",
                    "omni_director/agents/council.py",
                    "omni_director/cli.py",
                    "omni_director/tools/nle_export.py",
                ],
                priority="P0",
                status="implemented",
            ),
            ProductFeatureProposal(
                feature_id="PM-FEAT-030",
                title="Audio Description (AD) & Streaming Accessibility Compliance (WCAG/CVAA)",
                problem_statement=(
                    f"Broadcast networks, streaming distributors, and public-sector brand spots{project_ctx} "
                    "require 21st Century CVAA Audio Description cue sheets fitted strictly into open "
                    "dialogue gaps (zero collision), speech-rate pacing checks, WCAG 2.2 AA/AAA contrast "
                    "verification, and WebVTT AD subtitle deliverables."
                ),
                proposed_solution=(
                    "Implement AdTargetAudience, AudioDescriptionCueSpec, SceneAccessibilityProfileSpec, and "
                    "MasterAccessibilitySpec schemas; omni_director.tools.accessibility_ad "
                    "(detect_dialogue_gaps, verify_wcag_color_contrast, compile_accessibility_manifest, "
                    "format_ad_prompt_token, export_ad_vtt, export_ad_script_csv, "
                    "export_accessibility_manifest_json, export_accessibility_bundle, [AD-CUE: ...] prompt tokens); "
                    "6-domain calibration via get_domain_accessibility_spec(); and an interactive Accessibility & "
                    "AD Compliance HUD [[] (#btn-ad-animatic, #modal-accessibility-ad, #ad-scrubber-ribbon) "
                    "in the dark-room animatic."
                ),
                target_modules=[
                    "omni_director/schemas.py",
                    "omni_director/tools/accessibility_ad.py",
                    "omni_director/presets.py",
                    "omni_director/tools/prompt_auditor.py",
                    "omni_director/tools/html_compiler.py",
                    "omni_director/tools/html_hud_v212.py",
                    "omni_director/tools/html_hud_v215.py",
                    "omni_director/agents/agent.py",
                    "omni_director/agents/council.py",
                    "omni_director/cli.py",
                    "omni_director/tools/nle_export.py",
                ],
                priority="P0",
                status="implemented",
            ),
            ProductFeatureProposal(
                feature_id="PM-FEAT-031",
                title="Wardrobe, Prop Action-State Continuity & Art Department Dressing Bible",
                problem_statement=(
                    f"Multi-scene commercial productions{project_ctx} suffer from unmotivated prop state "
                    "reversals (e.g. damaged->intact or left/right hand swaps), costume weathering drift, "
                    "and <image_1..3> Nano Banana reference slot contention when wardrobe, environment, and "
                    "hero prop plates exceed the 3-slot architectural ceiling."
                ),
                proposed_solution=(
                    "Implement ScenePropContinuityState, SceneWardrobeStateSpec, ArtDressingAnchorSpec, "
                    "SceneArtContinuitySpec, and MasterWardrobePropBible schemas; omni_director.tools.wardrobe_props "
                    "(detect_prop_state_transitions, validate_reference_slot_budget, format_art_continuity_token, "
                    "compile_wardrobe_prop_bible, export_wardrobe_prop_bundle, [WARDROBE-LOCK:]/[PROP-STATE:] tokens); "
                    "6-domain calibration via get_domain_wardrobe_prop_spec(); and the Art & Wardrobe Continuity "
                    "Locker HUD [\\] (#btn-art-dept-animatic, #modal-art-wardrobe-continuity) plus Unified HUD "
                    "Command Palette [/] (#btn-command-palette-animatic, #modal-hud-command-palette)."
                ),
                target_modules=[
                    "omni_director/schemas.py",
                    "omni_director/tools/wardrobe_props.py",
                    "omni_director/presets.py",
                    "omni_director/tools/prompt_auditor.py",
                    "omni_director/tools/html_compiler.py",
                    "omni_director/tools/html_hud_v212.py",
                    "omni_director/tools/html_hud_v216.py",
                    "omni_director/agents/agent.py",
                    "omni_director/agents/council.py",
                    "omni_director/telemetry.py",
                ],
                priority="P0",
                status="implemented",
            ),
            ProductFeatureProposal(
                feature_id="PM-FEAT-032",
                title="Gemini Model Matrix Compute Economics, Live-Render Cost Guardrail & Multi-Take Variant Ledger",
                problem_statement=(
                    f"Executive producers and virtual production supervisors{project_ctx} need deterministic "
                    "per-scene token, Nano Banana plate, and Omni video compute cost estimates strictly "
                    "priced on the 2026 Gemini Model Matrix, with hard live-render budget caps, AI-vs-AICP "
                    "savings telemetry, and reproducible seed/take variant ledgers."
                ),
                proposed_solution=(
                    "Implement ModelTierRateSpec, TakeVariantRecord, SceneComputeEstimateSpec, "
                    "RenderBudgetGuardrailSpec, and MasterRenderEconomicsManifest schemas; "
                    "omni_director.tools.render_economics (get_2026_model_matrix_rates, estimate_scene_compute_cost, "
                    "check_render_budget_guardrail, compile_render_economics_manifest, format_render_profile_token, "
                    "export_render_economics_bundle, [RENDER-PROFILE: ...] tokens); 6-domain calibration via "
                    "get_domain_render_economics_spec(); and the Compute Economics & Take-Variant Inspector HUD [;] "
                    "(#btn-economics-animatic, #modal-render-economics) in the dark-room animatic."
                ),
                target_modules=[
                    "omni_director/schemas.py",
                    "omni_director/tools/render_economics.py",
                    "omni_director/presets.py",
                    "omni_director/tools/prompt_auditor.py",
                    "omni_director/tools/html_compiler.py",
                    "omni_director/tools/html_hud_v212.py",
                    "omni_director/tools/html_hud_v216.py",
                    "omni_director/agents/agent.py",
                    "omni_director/agents/council.py",
                    "omni_director/telemetry.py",
                ],
                priority="P0",
                status="implemented",
            ),
            ProductFeatureProposal(
                feature_id="PM-FEAT-033",
                title="Broadcast Kinetic Typography, MOGRT Supers & Brand End-Card Compositing Engine",
                problem_statement=(
                    f"Broadcast and vertical social deliverables{project_ctx} risk failing readability and safe-zone "
                    "clearance when on-screen kinetic supers exceed the 180 WPM reading ceiling, collide with 9:16 "
                    "TikTok/Reels engagement chrome, lack WCAG 2.2 AA/AAA scrim contrast, omit mandatory legal "
                    "disclaimers (such as closed-course automotive supers), or desynchronize tail Brand End-Cards."
                ),
                proposed_solution=(
                    "Implement GraphicLayerRoleEnum, CompositeStrategyEnum, TypographyPlacementSpec, "
                    "GraphicSuperCueSpec, BrandEndcardSpec, SceneMotionGraphicsSpec, and "
                    "MasterMotionGraphicsManifest schemas; omni_director.tools.motion_graphics "
                    "(compile_motion_graphics_manifest, compute_effective_wpm, compute_wcag_contrast_ratio, "
                    "format_motion_graphics_token, export_motion_graphics_bundle exporting motion_graphics_mogrt.json, "
                    "broadcast_supers.ass, and brand_endcard_spec.md, plus [GFX-SUPER:]/[GFX-CLEANPLATE:]/[ENDCARD:] "
                    "telemetry tokens); 6-domain calibration via get_domain_motion_graphics_spec(); and the Motion "
                    "Graphics, Supers & End-Card Studio HUD [=] (#btn-motion-gfx-animatic, #modal-motion-graphics-studio)."
                ),
                target_modules=[
                    "omni_director/schemas.py",
                    "omni_director/tools/motion_graphics.py",
                    "omni_director/presets.py",
                    "omni_director/tools/prompt_auditor.py",
                    "omni_director/tools/html_compiler.py",
                    "omni_director/tools/html_hud_v212.py",
                    "omni_director/tools/html_hud_v216.py",
                    "omni_director/tools/html_hud_v217.py",
                    "omni_director/agents/agent.py",
                    "omni_director/agents/council.py",
                    "omni_director/tools/nle_export.py",
                    "omni_director/telemetry.py",
                ],
                priority="P0",
                status="implemented",
            ),
            ProductFeatureProposal(
                feature_id="PM-FEAT-034",
                title="Universal OpenTimelineIO (.otio) Multi-Track Interchange & Cross-Departmental Coherence Gate",
                problem_statement=(
                    f"Complex multi-department productions{project_ctx} lack a unified ASWF OpenTimelineIO 0.16 "
                    "(Timeline.1) 7-track interchange container and an automated shoot-day coherence gate reconciling "
                    "optics vs. DoF, lighting Kelvin vs. blocking, audio stems vs. spotting, 9:16 reframe vs. "
                    "motion graphics, Mode B runtime vs. render economics, AICP post vs. compute, and C2PA vs. safety JSA."
                ),
                proposed_solution=(
                    "Implement CoherenceDomainPairEnum, CoherenceCheckStatusEnum, CrossDeptCoherenceCheck, "
                    "OtioTrackSummarySpec, and MasterOtioCoherenceManifest schemas; omni_director.tools.otio_coherence "
                    "(compile_otio_timeline_dict, evaluate_cross_department_coherence, "
                    "reconcile_cross_department_conflicts, compile_otio_coherence_manifest, format_otio_coherence_token, "
                    "export_otio_coherence_bundle exporting production_timeline.otio, coherence_matrix.json, and "
                    "coherence_readiness_report.md, plus [OTIO-SYNC:]/[COHERENCE-LOCK:] tokens); 6-domain tolerance "
                    "calibration via get_domain_otio_coherence_spec(); and the OpenTimelineIO (.otio) & Cross-Dept "
                    "Coherence Matrix HUD ['] (#btn-otio-coherence-animatic, #modal-otio-coherence)."
                ),
                target_modules=[
                    "omni_director/schemas.py",
                    "omni_director/tools/otio_coherence.py",
                    "omni_director/presets.py",
                    "omni_director/tools/prompt_auditor.py",
                    "omni_director/tools/html_compiler.py",
                    "omni_director/tools/html_hud_v212.py",
                    "omni_director/tools/html_hud_v216.py",
                    "omni_director/tools/html_hud_v217.py",
                    "omni_director/agents/agent.py",
                    "omni_director/agents/council.py",
                    "omni_director/tools/nle_export.py",
                    "omni_director/telemetry.py",
                ],
                priority="P0",
                status="implemented",
            ),
            ProductFeatureProposal(
                feature_id="PM-FEAT-035",
                title="Live-Render Job Orchestrator, Multi-Take Visual QA & Mode B Frame-Anchor Continuity Engine",
                problem_statement=(
                    f"Production pipelines{project_ctx} transitioning from dry-run storyboards to live video "
                    "rendering lack deterministic multi-take visual/audio QA scoring, Mode B frame-anchor "
                    "handoff validation (End_Frame_0N.png & previous_interaction_id), and one-click ffmpeg "
                    "rough-cut assembly scripts."
                ),
                proposed_solution=(
                    "Implement RenderJobStatusEnum, TakeQaScorecardSpec, FrameAnchorHandoffSpec, "
                    "SceneRenderJobSpec, and MasterRenderJobManifest schemas; omni_director.tools.render_orchestrator "
                    "(evaluate_take_visual_qa, verify_mode_b_frame_anchor, compile_render_job_manifest, "
                    "promote_scene_take, generate_rough_cut_assembly_script, format_render_job_token, "
                    "export_render_jobs_bundle exporting render_job_manifest.json, take_qa_scorecard.csv, and "
                    "rough_cut_assembly.sh, plus [RENDER-JOB:]/[FRAME-ANCHOR:] telemetry tokens); 6-domain QA "
                    "calibration via get_domain_render_job_spec(); and the Live-Render Jobs, Take A/B/C QA & "
                    "Frame-Anchor HUD [`] (#btn-render-jobs-animatic, #modal-render-jobs, #render-anchor-svg)."
                ),
                target_modules=[
                    "omni_director/schemas.py",
                    "omni_director/tools/render_orchestrator.py",
                    "omni_director/presets.py",
                    "omni_director/tools/prompt_auditor.py",
                    "omni_director/tools/html_compiler.py",
                    "omni_director/tools/html_hud_v212.py",
                    "omni_director/tools/html_hud_v216.py",
                    "omni_director/tools/html_hud_v218.py",
                    "omni_director/agents/agent.py",
                    "omni_director/agents/council.py",
                    "omni_director/tools/nle_export.py",
                    "omni_director/telemetry.py",
                ],
                priority="P0",
                status="implemented",
            ),
            ProductFeatureProposal(
                feature_id="PM-FEAT-036",
                title="Executive Director's Treatment, Print-Ready Pitch Lookbook & Bible Revision Diff Engine",
                problem_statement=(
                    f"Executive stakeholders and agency creative directors{project_ctx} lack a print-ready "
                    "director's pitch treatment lookbook combining Nano Banana visual plates, color scripts, "
                    "sonic arcs, and AI-vs-AICP ROI summaries, as well as a deterministic SHA-256 revision "
                    "diff engine comparing Bible iterations and council scores."
                ),
                proposed_solution=(
                    "Implement TreatmentSlideTypeEnum, TreatmentBoardSlideSpec, BibleRevisionDeltaItem, "
                    "BibleRevisionDiffReport, and MasterPitchTreatmentSpec schemas; omni_director.tools.pitch_treatment "
                    "(compile_pitch_treatment, diff_production_bibles, format_pitch_treatment_token, "
                    "export_treatment_lookbook_html with @media print page breaks and html.escape(), "
                    "export_pitch_treatment_bundle exporting director_treatment_lookbook.html, "
                    "director_treatment_brief.md, and pitch_treatment_manifest.json, plus [TREATMENT-BEAT:] "
                    "tokens); 6-domain calibration via get_domain_pitch_treatment_spec(); and the Director's "
                    "Pitch Treatment & Lookbook Studio HUD [-] (#btn-treatment-animatic, #modal-pitch-treatment)."
                ),
                target_modules=[
                    "omni_director/schemas.py",
                    "omni_director/tools/pitch_treatment.py",
                    "omni_director/presets.py",
                    "omni_director/tools/prompt_auditor.py",
                    "omni_director/tools/html_compiler.py",
                    "omni_director/tools/html_hud_v212.py",
                    "omni_director/tools/html_hud_v216.py",
                    "omni_director/tools/html_hud_v218.py",
                    "omni_director/agents/agent.py",
                    "omni_director/agents/council.py",
                    "omni_director/tools/nle_export.py",
                    "omni_director/telemetry.py",
                ],
                priority="P0",
                status="implemented",
            ),
            ProductFeatureProposal(
                feature_id="PM-FEAT-037",
                title="SMPTE ST 2067 IMF Multi-Version Mastering & DCI Theatrical DCP Packaging Engine",
                problem_statement=(
                    f"Multi-territory and multi-cutdown commercial deliveries{project_ctx} duplicate 12-bit master "
                    "picture essence across localized/cutdown renders and lack SMPTE ST 2067 ASSETMAP/PKL/CPL "
                    "XML packaging plus SMPTE ST 429 DCI Theatrical DCP bitrate/color/KDM verification."
                ),
                proposed_solution=(
                    "Implement ImfApplicationProfileEnum, ImfAssetTrackSpec, ImfCompositionPlaylistSpec, "
                    "DciTheatricalDcpSpec, and MasterImfDcpManifest schemas; omni_director.tools.imf_dcp_packager "
                    "(compile_imf_dcp_manifest, format_imf_dcp_token, export_imf_assetmap_xml, export_imf_pkl_xml, "
                    "export_imf_cpl_xml, export_imf_dcp_manifest_json, export_dcp_cpl_spec_md, export_imf_dcp_bundle "
                    "with deduplicated OV picture essence reuse and <=250.0 Mbps JPEG2000 DCI cap); 6-domain "
                    "calibration via get_domain_imf_dcp_profile(); [IMF-CPL:] telemetry token stripping; and the "
                    "IMF Package & Theatrical DCP Mastering HUD [}] (#btn-imf-dcp, #imfDcpModal)."
                ),
                target_modules=[
                    "omni_director/schemas.py",
                    "omni_director/tools/imf_dcp_packager.py",
                    "omni_director/presets.py",
                    "omni_director/tools/prompt_auditor.py",
                    "omni_director/tools/html_compiler.py",
                    "omni_director/tools/html_hud_v212.py",
                    "omni_director/tools/html_hud_v219.py",
                    "omni_director/agents/agent.py",
                    "omni_director/agents/council.py",
                    "omni_director/tools/nle_export.py",
                    "omni_director/telemetry.py",
                    "omni_director/cli.py",
                ],
                priority="P0",
                status="implemented",
            ),
            ProductFeatureProposal(
                feature_id="PM-FEAT-038",
                title="Voice Casting, Phoneme/Viseme Lip-Sync Scripting & Automated Stem Sidechain Ducking Engine",
                problem_statement=(
                    f"Dialogue, voice-over, and Audio Description (AD) tracks{project_ctx} lack explicit "
                    "vocal register casting, Preston Blair 13-class viseme lip-sync timing <=2.5 WPS, and "
                    "sample-accurate sidechain stem ducking automation preserving >=6.0 dB dialogue-to-BGM SNR."
                ),
                proposed_solution=(
                    "Implement VocalRegisterEnum, VisemeClassEnum, VoiceCastingProfile, VisemeLipSyncCue, "
                    "SidechainDuckingKeyframe, SceneVoiceDuckingSpec, and MasterVoiceDuckingManifest schemas; "
                    "omni_director.tools.voice_ducking (compile_voice_ducking_manifest, format_voice_ducking_token, "
                    "export_voice_casting_json, export_stem_ducking_csv, export_adr_viseme_md, "
                    "export_voice_ducking_bundle); 6-domain calibration via get_domain_voice_ducking_profile(); "
                    "[VOICE-CAST:] telemetry token stripping; and the Voice Casting, Viseme Lip-Sync & Sidechain "
                    "Ducking Studio HUD [{] (#btn-voice-ducking, #voiceDuckingModal, #v219-ducking-svg)."
                ),
                target_modules=[
                    "omni_director/schemas.py",
                    "omni_director/tools/voice_ducking.py",
                    "omni_director/presets.py",
                    "omni_director/tools/prompt_auditor.py",
                    "omni_director/tools/html_compiler.py",
                    "omni_director/tools/html_hud_v212.py",
                    "omni_director/tools/html_hud_v219.py",
                    "omni_director/agents/agent.py",
                    "omni_director/agents/council.py",
                    "omni_director/tools/nle_export.py",
                    "omni_director/telemetry.py",
                    "omni_director/cli.py",
                ],
                priority="P0",
                status="implemented",
            ),
            ProductFeatureProposal(
                feature_id="PM-FEAT-039",
                title="Colorist Finishing Scopes, CIELAB Delta-E2000 Shot-to-Shot Continuity Match & Interactive A/B Wipe Monitor",
                problem_statement=(
                    f"Finishing colorists and directors inspecting multi-scene commercials{project_ctx} lack "
                    "real-time Luma Waveform, RGB Parade, and Rec.709 Vectorscope telemetry, perceptual "
                    "CIEDE2000 inter-cut chromatic drift diagnostics with ASC CDL trim offsets, and an "
                    "interactive A/B split-screen comparison monitor."
                ),
                proposed_solution=(
                    "Implement ScopeSignalStandardEnum, ShotMatchStatusEnum, SceneScopeTelemetrySpec, "
                    "AdjacentCutColorMatchSpec, and MasterColorScopesManifest schemas; "
                    "omni_director.tools.color_scopes (compile_color_scopes_manifest, compute_ciede2000, "
                    "format_color_scopes_token, export_color_scopes_json, export_shot_match_cdl_csv, "
                    "export_finishing_scopes_qc_md, export_color_scopes_bundle); 6-domain calibration via "
                    "get_domain_color_scopes_profile(); [COLOR-SCOPES:] telemetry token stripping; and the "
                    "Colorist Scopes & A/B Wipe HUD [+] (#btn-color-scopes, #colorScopesModal, "
                    "#v220-scopes-svg, #v220-ab-wipe-stage)."
                ),
                target_modules=[
                    "omni_director/schemas.py",
                    "omni_director/tools/color_scopes.py",
                    "omni_director/presets.py",
                    "omni_director/tools/prompt_auditor.py",
                    "omni_director/tools/html_compiler.py",
                    "omni_director/tools/html_hud_v212.py",
                    "omni_director/tools/html_hud_v220.py",
                    "omni_director/agents/agent.py",
                    "omni_director/agents/council.py",
                    "omni_director/tools/nle_export.py",
                    "omni_director/telemetry.py",
                    "omni_director/cli.py",
                ],
                priority="P0",
                status="implemented",
            ),
            ProductFeatureProposal(
                feature_id="PM-FEAT-040",
                title="RFC 8493 BagIt Production Archive Vault, Checksum Verification & Agency/DAM Handoff Engine",
                problem_statement=(
                    f"Agency producers and post-finishing supervisors handing off final commercial bundles{project_ctx} "
                    "lack an RFC 8493 BagIt-compliant archival package with deterministic 6-department payload "
                    "routing, SHA-256 manifest verification, Payload-Oxum integrity, and retention SLA governance."
                ),
                proposed_solution=(
                    "Implement ArchiveRetentionTierEnum, VaultDepartmentEnum, ArchiveVaultEntrySpec, "
                    "DepartmentVaultSummarySpec, and MasterArchiveVaultManifest schemas; "
                    "omni_director.tools.archive_vault (compile_archive_vault_manifest, classify_artifact_department, "
                    "format_archive_vault_token, export_archive_vault_json, export_bag_info_txt, "
                    "export_manifest_sha256_txt, export_agency_delivery_readme_md, export_archive_vault_bundle); "
                    "6-domain calibration via get_domain_archive_vault_profile(); [ARCHIVE-VAULT:] telemetry "
                    "token stripping; and the RFC 8493 Archive Vault HUD [:] (#btn-archive-vault, "
                    "#archiveVaultModal, #v220-vault-svg)."
                ),
                target_modules=[
                    "omni_director/schemas.py",
                    "omni_director/tools/archive_vault.py",
                    "omni_director/presets.py",
                    "omni_director/tools/prompt_auditor.py",
                    "omni_director/tools/html_compiler.py",
                    "omni_director/tools/html_hud_v212.py",
                    "omni_director/tools/html_hud_v220.py",
                    "omni_director/agents/agent.py",
                    "omni_director/agents/council.py",
                    "omni_director/tools/nle_export.py",
                    "omni_director/telemetry.py",
                    "omni_director/cli.py",
                ],
                priority="P0",
                status="implemented",
            ),
        ]

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """ADK 2.0 Agent invocation hook."""
        bible = context.get("bible")
        bundle = context.get("bundle")
        out_dir = Path(context["output_dir"]) if context.get("output_dir") else None
        context["pm_recommendations"] = self.inspect_product(bible=bible, bundle=bundle, output_dir=out_dir)
        return context


class ProductCouncilOrchestrator(BaseAgent):
    """Orchestrates 4-persona autonomous product council audit of production bibles and bundles."""

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    def __init__(
        self,
        config: Optional[DirectorConfig] = None,
        *,
        name: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        agent_name = name or "ProductCouncilOrchestrator"
        desc = kwargs.pop("description", kwargs.pop("instruction", "Autonomous Product Council Orchestrator"))
        super().__init__(name=agent_name, description=desc, **kwargs)
        self.config = config or cfg
        self.product_manager = ProductManagerAgent(config=self.config)

    def consult_product_manager(
        self,
        bible: Optional[MasterProductionBible] = None,
        bundle: Optional[ProductionBundle] = None,
        output_dir: Optional[Path] = None,
    ) -> List[ProductFeatureProposal]:
        """Consults the Senior Product Manager persona to inspect the product and recommend features."""
        return self.product_manager.inspect_product(bible=bible, bundle=bundle, output_dir=output_dir)

    def convene_council(
        self,
        bundle_or_bible: Optional[Union[ProductionBundle, MasterProductionBible, Dict[str, Any], str, Path]] = None,
        output_dir: Optional[Union[str, Path]] = None,
        auto_heal: bool = True,
        *,
        bundle: Optional[ProductionBundle] = None,
        bible: Optional[MasterProductionBible] = None,
    ) -> ProductCouncilReport:
        """Convenes the autonomous 4-persona product council and senior product manager."""
        return self.audit(
            bundle_or_bible=bundle_or_bible,
            output_dir=output_dir,
            auto_heal=auto_heal,
            bundle=bundle,
            bible=bible,
        )

    def review_production_bundle(
        self,
        bundle: ProductionBundle,
        output_dir: Optional[Union[str, Path]] = None,
        auto_heal: bool = True,
    ) -> ProductCouncilReport:
        """Audits and reviews a production bundle."""
        return self.audit(bundle=bundle, output_dir=output_dir, auto_heal=auto_heal)

    def audit(
        self,
        bundle_or_bible: Optional[Union[ProductionBundle, MasterProductionBible, Dict[str, Any], str, Path]] = None,
        output_dir: Optional[Union[str, Path]] = None,
        auto_heal: bool = True,
        *,
        bundle: Optional[ProductionBundle] = None,
        bible: Optional[MasterProductionBible] = None,
    ) -> ProductCouncilReport:
        """Executes a 100-point council audit across all 4 personas."""
        resolved_bundle: Optional[ProductionBundle] = bundle
        resolved_bible: Optional[MasterProductionBible] = bible
        resolved_out_dir: Optional[Path] = None

        target = bundle_or_bible if bundle_or_bible is not None else (bundle or bible)
        if target is None:
            raise ValueError("No target bundle or bible provided for council audit.")

        if isinstance(target, ProductionBundle):
            resolved_bundle = target
            resolved_bible = target.bible
            if target.bundle_json_path:
                resolved_out_dir = Path(target.bundle_json_path).parent
        elif isinstance(target, MasterProductionBible):
            resolved_bible = target
        elif isinstance(target, dict):
            if "bible" in target and isinstance(target["bible"], dict):
                try:
                    resolved_bundle = ProductionBundle.model_validate(target)
                    resolved_bible = resolved_bundle.bible
                except Exception:
                    resolved_bible = load_bible_from_json(target)
            else:
                resolved_bible = load_bible_from_json(target)
        elif isinstance(target, (str, Path)):
            path = Path(target)
            if path.is_file():
                resolved_out_dir = path.parent
            resolved_bible = load_bible_from_json(path)
        else:
            raise ValueError(f"Unsupported payload for council audit: {type(target)}")

        bundle = resolved_bundle
        bible = resolved_bible

        if output_dir:
            resolved_out_dir = Path(output_dir)
        elif not resolved_out_dir:
            resolved_out_dir = Path(self.config.output_dir)

        reviews: List[PersonaReviewResult] = []
        recommendations: List[str] = []

        # 1. Council FDE Review (25 pts max)
        fde_review = self._review_fde(bible=bible, bundle=bundle, output_dir=resolved_out_dir)
        reviews.append(fde_review)

        # 2. Council Agent Engineer Review (25 pts max)
        ae_review = self._review_agent_engineer(bible=bible, auto_heal=auto_heal, bundle=bundle)
        reviews.append(ae_review)

        # 3. Council Strategist Review (25 pts max)
        strat_review = self._review_strategist(bible=bible)
        reviews.append(strat_review)

        # 4. Council UX Designer Review (25 pts max)
        ux_review = self._review_ux_designer(bible=bible, bundle=bundle, output_dir=resolved_out_dir)
        reviews.append(ux_review)

        total_score = round(sum(r.score for r in reviews), 2)
        critical_count = sum(
            len([f for f in r.findings if f.severity == CouncilFindingSeverity.CRITICAL])
            for r in reviews
        )
        passed = (total_score >= 88.0 and critical_count == 0)

        for r in reviews:
            for f in r.findings:
                if f.suggested_fix and f.suggested_fix not in recommendations:
                    recommendations.append(f.suggested_fix)

        pm_proposals = self.consult_product_manager(bible=bible, bundle=bundle, output_dir=resolved_out_dir)

        report = ProductCouncilReport(
            version=__version__,
            project_title=bible.project_title if bible else "Omni Production",
            timestamp=datetime.now(timezone.utc).isoformat(),
            overall_score=total_score,
            passed=passed,
            critical_findings_count=critical_count,
            reviews=reviews,
            recommendations=recommendations,
            pm_persona_prompt=self.product_manager.persona_prompt,
            pm_recommendations=pm_proposals,
        )

        if bundle is not None:
            bundle.council_report = report

        # Write reports to output directory
        if resolved_out_dir:
            try:
                resolved_out_dir.mkdir(parents=True, exist_ok=True)
                json_path = resolved_out_dir / "council_report.json"
                json_path.write_text(json.dumps(report.model_dump(), indent=2), encoding="utf-8")
                # Also create council_audit_report.json alias
                (resolved_out_dir / "council_audit_report.json").write_text(
                    json.dumps(report.model_dump(), indent=2), encoding="utf-8"
                )
                md_path = resolved_out_dir / "council_report.md"
                md_path.write_text(self.generate_markdown_report(report), encoding="utf-8")
            except Exception as e:
                logger.warning(f"Could not persist council reports to {resolved_out_dir}: {e}")

        return report

    def evaluate_bundle(
        self,
        bundle_or_bible: Optional[Union[ProductionBundle, MasterProductionBible, Dict[str, Any], str, Path]] = None,
        output_dir: Optional[Union[str, Path]] = None,
        auto_heal: bool = True,
        *,
        bundle: Optional[ProductionBundle] = None,
        bible: Optional[MasterProductionBible] = None,
    ) -> ProductCouncilReport:
        """Alias for audit()."""
        return self.audit(
            bundle_or_bible=bundle_or_bible,
            output_dir=output_dir,
            auto_heal=auto_heal,
            bundle=bundle,
            bible=bible,
        )

    def _review_fde(
        self,
        bible: Optional[MasterProductionBible],
        bundle: Optional[ProductionBundle] = None,
        output_dir: Optional[Union[Path, str]] = None,
        bundle_dir: Optional[Union[Path, str]] = None,
        **kwargs: Any,
    ) -> PersonaReviewResult:
        """Evaluates schema integrity, output structure, and bundle artifacts."""
        findings: List[CouncilFinding] = []
        score = 25.0

        if bible is None:
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.CRITICAL,
                category="schema_integrity",
                message="MasterProductionBible is missing or could not be loaded.",
                suggested_fix="Ensure valid MasterProductionBible is provided."
            ))
            return PersonaReviewResult(
                persona=CouncilPersona.COUNCIL_FDE,
                score=0.0,
                findings=findings,
                summary="Fatal: MasterProductionBible missing."
            )

        if not bible.scenes:
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.CRITICAL,
                category="scene_completeness",
                message="Bible has zero scenes defined.",
                suggested_fix="Define at least one scene in bible.scenes."
            ))
            score -= 25.0
        else:
            scene_indices = [s.scene_index for s in bible.scenes]
            expected = list(range(1, len(bible.scenes) + 1))
            if scene_indices != expected:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.MEDIUM,
                    category="scene_indexing",
                    message=f"Scene indices {scene_indices} are not 1-indexed sequential {expected}.",
                    suggested_fix="Renumber scenes sequentially starting at 1."
                ))
                score -= 3.0

        if bundle is not None:
            if not bundle.storyboard_html_path or not Path(bundle.storyboard_html_path).exists():
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.MEDIUM,
                    category="artifact_delivery",
                    message="storyboard_preview.html is missing or does not exist on disk.",
                    suggested_fix="Compile storyboard HTML before compiling bundle."
                ))
                score -= 4.0
            if not bundle.bundle_json_path or not Path(bundle.bundle_json_path).exists():
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.LOW,
                    category="artifact_delivery",
                    message="production_bundle.json file path does not exist on disk.",
                    suggested_fix="Persist production_bundle.json to output directory."
                ))
                score -= 2.0

        # Active Checksum Integrity Verification & Zero-Leak Secret Scan
        eval_target = output_dir or bundle_dir
        eval_dir = Path(eval_target) if eval_target else (Path(bundle.bundle_json_path).parent if bundle and bundle.bundle_json_path else None)
        if eval_dir:
            scanned_files: List[str] = []
            secret_leak_files: List[str] = []
            for sec_fname in ("telemetry.json", "production_bundle.json"):
                sec_path = eval_dir / sec_fname
                if sec_path.is_file():
                    scanned_files.append(sec_fname)
                    try:
                        raw_txt = sec_path.read_text(encoding="utf-8")
                        if SECRET_PATTERN.search(raw_txt):
                            secret_leak_files.append(sec_fname)
                    except Exception:
                        pass
            if secret_leak_files:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.CRITICAL,
                    category="telemetry_secret_leak",
                    message=f"Secret or API credential pattern detected in exported artifact(s): {', '.join(secret_leak_files)}.",
                    suggested_fix="Sanitize all credentials via RuntimeTelemetry before writing telemetry.json or production_bundle.json.",
                ))
                score -= 10.0
            elif scanned_files:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="telemetry_secret_scan",
                    message=f"Zero-leak SECRET_PATTERN scan passed cleanly on: {', '.join(scanned_files)}.",
                    details={"scanned_files": scanned_files},
                ))

        if eval_dir and (eval_dir / "telemetry.json").is_file():
            is_valid, checksum_errors = verify_bundle_checksums(eval_dir)
            if not is_valid:
                is_standalone_export_dir = (
                    bundle is None
                    and not (eval_dir / "production_bundle.json").is_file()
                    and not (eval_dir / "storyboard_preview.html").is_file()
                )
                effective_errors = (
                    [err for err in checksum_errors if "Mandatory bundle file" not in err]
                    if is_standalone_export_dir
                    else checksum_errors
                )
                if effective_errors:
                    has_mismatch = any("Checksum mismatch" in err for err in effective_errors)
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.CRITICAL if has_mismatch else CouncilFindingSeverity.HIGH,
                        category="artifact_integrity",
                        message=f"Bundle artifact checksum verification failed ({len(effective_errors)} issue(s)): {'; '.join(effective_errors[:2])}",
                        suggested_fix="Re-run compilation to regenerate artifacts with matching SHA-256 digests."
                    ))
                    score -= 6.0 if has_mismatch else 4.0

        # Verify Optical Depth-of-Field (DoF) and Focus Puller deliverables (PM-FEAT-011)
        if eval_dir:
            dof_chart = eval_dir / "dof_chart.json"
            cue_sheet = eval_dir / "focus_puller_cue_sheet.csv"
            if dof_chart.is_file() or cue_sheet.is_file():
                dof_items = []
                if dof_chart.is_file():
                    dof_items.append("dof_chart.json")
                if cue_sheet.is_file():
                    dof_items.append("focus_puller_cue_sheet.csv")
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="optical_dof_delivery",
                    message=f"Optical Depth-of-Field (DoF) hyperfocal chart and 1st AC cue sheet verified on disk: {', '.join(dof_items)}.",
                    details={"dof_artifacts": dof_items}
                ))

            # Verify DIT 3D Cube Color Grading LUT suite deliverables (PM-FEAT-012)
            cube_lut = eval_dir / "production_look.cube"
            dit_manifest = eval_dir / "dit_cart_manifest.json"
            if cube_lut.is_file() or dit_manifest.is_file():
                lut_items = []
                if cube_lut.is_file():
                    lut_items.append("production_look.cube")
                if dit_manifest.is_file():
                    lut_items.append("dit_cart_manifest.json")
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="color_lut_delivery",
                    message=f"DIT 3D Cube Color Grading LUT suite and offload cart manifest verified on disk: {', '.join(lut_items)}.",
                    details={"lut_artifacts": lut_items}
                ))

            # Verify Spatial Audio & Binaural Soundfield deliverables (PM-FEAT-013)
            spatial_adm = eval_dir / "spatial_audio_adm.json"
            spatial_adm_alt = eval_dir / "spatial_audio_adm_manifest.json"
            ambisonic_csv = eval_dir / "ambisonic_b_format.csv"
            ambisonic_alt = eval_dir / "spatial_audio_ambisonic_channels.csv"
            if spatial_adm.is_file() or spatial_adm_alt.is_file() or ambisonic_csv.is_file() or ambisonic_alt.is_file():
                spatial_items = []
                if spatial_adm.is_file() or spatial_adm_alt.is_file():
                    spatial_items.append("spatial_audio_adm.json")
                if ambisonic_csv.is_file() or ambisonic_alt.is_file():
                    spatial_items.append("ambisonic_b_format.csv")
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="spatial_audio_delivery",
                    message=f"Spatial audio Dolby Atmos ADM manifest and HOA Ambisonics matrix verified on disk: {', '.join(spatial_items)}.",
                    details={"spatial_artifacts": spatial_items}
                ))

            # Verify Advanced Multi-Pass VFX Compositing deliverables (PM-FEAT-014)
            exr_manifest = eval_dir / "openexr_channels.json"
            exr_alt = eval_dir / "vfx_compositing_manifest.json"
            cryptomatte_json = eval_dir / "cryptomatte_manifest.json"
            nuke_script = eval_dir / "nuke_composite.nk"
            nuke_alt = eval_dir / "nuke_composite_template.nk"
            if exr_manifest.is_file() or exr_alt.is_file() or cryptomatte_json.is_file() or nuke_script.is_file() or nuke_alt.is_file():
                vfx_items = []
                if exr_manifest.is_file() or exr_alt.is_file():
                    vfx_items.append("openexr_channels.json")
                if cryptomatte_json.is_file():
                    vfx_items.append("cryptomatte_manifest.json")
                if nuke_script.is_file() or nuke_alt.is_file():
                    vfx_items.append("nuke_composite.nk")
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="vfx_compositing_delivery",
                    message=f"Multi-pass VFX OpenEXR channels, Cryptomatte manifest, and Nuke composite script verified on disk: {', '.join(vfx_items)}.",
                    details={"vfx_artifacts": vfx_items}
                ))

            # Verify HDR10 / HLG Broadcast Color Volume Metadata deliverables (PM-FEAT-015)
            hdr_candidates = [
                "hdr10_metadata.json",
                "hlg_broadcast.xml",
                "hlg_broadcast_metadata.xml",
                "resolve_hdr_rcm.xml",
                "resolve_hdr_parameters.xml",
                "hdr_master_report.json",
            ]
            hdr_items = [name for name in hdr_candidates if (eval_dir / name).is_file()]
            if hdr_items:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="hdr_metadata_delivery",
                    message=f"HDR10 mastering metadata JSON, HLG XML, and DaVinci Resolve HDR XML verified on disk: {', '.join(hdr_items)}.",
                    details={"hdr_artifacts": hdr_items}
                ))

            # Verify 1st AD Stripboard Production Scheduler deliverables (PM-FEAT-016)
            strip_candidates = [
                "movie_magic_schedule.xml",
                "stripboard_schedule.csv",
                "dood_matrix.csv",
                "day_out_of_days_matrix.csv",
                "stripboard_summary.json",
                "script_breakdown_sheets.json",
            ]
            stripboard_items = [name for name in strip_candidates if (eval_dir / name).is_file()]
            if stripboard_items:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="stripboard_schedule_delivery",
                    message=f"1st AD Movie Magic schedule XML, Stripboard CSV, DOOD matrix, and Breakdown sheets verified on disk: {', '.join(stripboard_items)}.",
                    details={"stripboard_artifacts": stripboard_items}
                ))

            # Verify Physical Film Stock Emulation deliverables (PM-FEAT-017)
            film_candidates = [
                "film_stock_shader.dctl",
                "film_stock.ale",
                "film_emulation_spec.json",
                "film_emulation_manifest.json",
            ]
            film_items = [name for name in film_candidates if (eval_dir / name).is_file()]
            if film_items:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="film_emulation_delivery",
                    message=f"Film stock DCTL shader, Avid ALE log, and Emulation manifest verified on disk: {', '.join(film_items)}.",
                    details={"film_artifacts": film_items}
                ))

            # Verify SMPTE 12M Clapper Slate & ASC-MHL deliverables (PM-FEAT-018)
            slate_candidates = [
                "asc_mhl_manifest.xml",
                "clapper_slate_log.csv",
                "sound_sync.ale",
                "sound_sync_ale.ale",
                "slate_manifest.json",
                "master_slate_spec.json",
            ]
            slate_items = [name for name in slate_candidates if (eval_dir / name).is_file()]
            if slate_items:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="clapper_slate_delivery",
                    message=f"ASC-MHL hash list XML, Clapper slate CSV, Sound sync ALE, and Slate JSON verified on disk: {', '.join(slate_items)}.",
                    details={"slate_artifacts": slate_items}
                ))

            # Verify Aerial Drone Flight Path deliverables (PM-FEAT-019)
            kml_file = eval_dir / "flight_path.kml" if (eval_dir / "flight_path.kml").is_file() else (eval_dir / "drone_flight_plan.kml")
            gpx_file = eval_dir / "flight_waypoints.gpx" if (eval_dir / "flight_waypoints.gpx").is_file() else (eval_dir / "drone_flight_track.gpx")
            drone_csv = eval_dir / "drone_flight_sheet.csv"
            drone_json = eval_dir / "drone_flight_manifest.json"
            drone_md = eval_dir / "drone_flight_sheet.md"
            if kml_file.is_file() or gpx_file.is_file() or drone_csv.is_file() or drone_json.is_file() or drone_md.is_file():
                drone_items = []
                if kml_file.is_file():
                    drone_items.append(kml_file.name)
                if gpx_file.is_file():
                    drone_items.append(gpx_file.name)
                if drone_csv.is_file():
                    drone_items.append("drone_flight_sheet.csv")
                if drone_md.is_file():
                    drone_items.append("drone_flight_sheet.md")
                if drone_json.is_file():
                    drone_items.append("drone_flight_manifest.json")
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="drone_flight_delivery",
                    message=f"Drone flight path KML, GPX track, Flight sheet CSV/MD, and Flight manifest JSON verified on disk: {', '.join(drone_items)}.",
                    details={"drone_artifacts": drone_items}
                ))

            # Verify AICP Commercial Production Bid deliverables (PM-FEAT-020)
            aicp_csv = eval_dir / "aicp_bid_sheet.csv" if (eval_dir / "aicp_bid_sheet.csv").is_file() else (eval_dir / "aicp_budget_bid.csv")
            aicp_json = eval_dir / "aicp_bid_manifest.json" if (eval_dir / "aicp_bid_manifest.json").is_file() else (eval_dir / "aicp_budget_manifest.json")
            aicp_md = eval_dir / "production_budget_topsheet.md" if (eval_dir / "production_budget_topsheet.md").is_file() else (eval_dir / "aicp_budget_summary.md")
            if aicp_csv.is_file() or aicp_json.is_file() or aicp_md.is_file():
                aicp_items = []
                if aicp_csv.is_file():
                    aicp_items.append(aicp_csv.name)
                if aicp_json.is_file():
                    aicp_items.append(aicp_json.name)
                if aicp_md.is_file():
                    aicp_items.append(aicp_md.name)
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="aicp_budget_delivery",
                    message=f"AICP commercial bid sheet CSV, Bid manifest JSON, and Production budget topsheet Markdown verified on disk: {', '.join(aicp_items)}.",
                    details={"aicp_artifacts": aicp_items}
                ))

            # Verify Multi-Aspect Reframe & Cutdown Delivery deliverables (PM-FEAT-021)
            reframe_candidates = [
                "reframe_crop_matrix.csv",
                "cutdown_15s.edl",
                "cutdown_06s.edl",
                "reframe_9x16.fcpxml",
                "delivery_reframe_manifest.json",
            ]
            reframe_items = [name for name in reframe_candidates if (eval_dir / name).is_file()]
            if reframe_items:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="reframe_delivery",
                    message=f"Multi-aspect reframe crop matrix, cutdown EDLs, 9:16 FCPXML, and Reframe manifest verified on disk: {', '.join(reframe_items)}.",
                    details={"reframe_artifacts": reframe_items},
                ))

            # Verify Broadcast Technical QC & Rights Clearance deliverables (PM-FEAT-022)
            qc_candidates = [
                "broadcast_qc_certificate.md",
                "rights_clearance_matrix.csv",
                "broadcast_qc_manifest.json",
            ]
            qc_items = [name for name in qc_candidates if (eval_dir / name).is_file()]
            if qc_items:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="broadcast_qc_delivery",
                    message=f"Broadcast QC certificate, Rights clearance matrix CSV, and Broadcast QC manifest JSON verified on disk: {', '.join(qc_items)}.",
                    details={"qc_artifacts": qc_items},
                ))

            # Verify Inter-Scene Editorial Continuity & Overhead Blocking Floorplan deliverables (PM-FEAT-023)
            continuity_candidates = [
                "continuity_log.csv",
                "blocking_floorplan.svg",
                "continuity_manifest.json",
            ]
            continuity_items = [name for name in continuity_candidates if (eval_dir / name).is_file()]
            if continuity_items:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="continuity_blocking_delivery",
                    message=f"Inter-scene continuity log CSV, 180-degree blocking floorplan SVG, and Continuity manifest JSON verified on disk: {', '.join(continuity_items)}.",
                    details={"continuity_artifacts": continuity_items},
                ))

            # Verify Client Review, Frame-Accurate Markers & Sign-Off deliverables (PM-FEAT-024)
            review_candidates = [
                "review_markers.edl",
                "review_markers.fcpxml",
                "review_notes_frameio.json",
                "review_notes.csv",
                "client_signoff_report.md",
            ]
            review_items = [name for name in review_candidates if (eval_dir / name).is_file()]
            if review_items:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="client_review_delivery",
                    message=f"Client review Resolve EDL, FCPXML markers, Frame.io JSON, Review notes CSV, and Sign-off report verified on disk: {', '.join(review_items)}.",
                    details={"review_artifacts": review_items},
                ))

            # Verify C2PA Content Credentials & Likeness Provenance deliverables (PM-FEAT-025)
            c2pa_candidates = [
                "c2pa_manifest.json",
                "ai_disclosure_certificate.md",
                "likeness_consent_ledger.csv",
            ]
            c2pa_items = [name for name in c2pa_candidates if (eval_dir / name).is_file()]
            if c2pa_items:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="c2pa_provenance_delivery",
                    message=f"C2PA Content Credentials manifest JSON, AI disclosure certificate MD, and Likeness consent ledger CSV verified on disk: {', '.join(c2pa_items)}.",
                    details={"c2pa_artifacts": c2pa_items},
                ))

            # Verify On-Set Safety Risk & JSA deliverables (PM-FEAT-026)
            safety_candidates = [
                "safety_bulletin.md",
                "safety_jsa_matrix.csv",
                "safety_risk_manifest.json",
            ]
            safety_items = [name for name in safety_candidates if (eval_dir / name).is_file()]
            if safety_items:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="safety_risk_delivery",
                    message=f"On-set safety bulletin MD, Safety JSA matrix CSV, and Safety risk manifest JSON verified on disk: {', '.join(safety_items)}.",
                    details={"safety_artifacts": safety_items},
                ))

            has_full_nle_exports = (
                (eval_dir / "timeline.edl").is_file()
                and (eval_dir / "sequence.fcpxml").is_file()
            )

            # Verify Multi-Territory Localization, ADR Dubbing & IMSC1 TTML deliverables (PM-FEAT-027)
            loc_candidates = [
                "localization_manifest.json",
                "adr_cue_sheet.csv",
                "subtitles_localized.ttml",
            ]
            loc_items = [name for name in loc_candidates if (eval_dir / name).is_file()]
            if loc_items:
                missing_loc = [name for name in loc_candidates if name not in loc_items]
                if missing_loc and has_full_nle_exports:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.MEDIUM,
                        category="localization_adr_delivery",
                        message=(
                            f"Partial localization ADR deliverables on disk ({', '.join(loc_items)}); "
                            f"missing: {', '.join(missing_loc)}."
                        ),
                        suggested_fix="Run export_localization_bundle() or export_all_nle_artifacts() to export all PM-FEAT-027 artifacts.",
                        details={"localization_artifacts": loc_items, "missing_artifacts": missing_loc},
                    ))
                    score -= 1.0
                else:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.INFO,
                        category="localization_adr_delivery",
                        message=f"Localization manifest JSON, ADR cue sheet CSV, and IMSC1 TTML verified on disk: {', '.join(loc_items)}.",
                        details={"localization_artifacts": loc_items},
                    ))
            elif has_full_nle_exports:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.MEDIUM,
                    category="localization_adr_delivery",
                    message="NLE exports present on disk without PM-FEAT-027 localization deliverables (localization_manifest.json, adr_cue_sheet.csv, subtitles_localized.ttml).",
                    suggested_fix="Run export_localization_bundle() or export_all_nle_artifacts().",
                    details={"missing_artifacts": loc_candidates},
                ))
                score -= 1.0

            # Verify Editorial Spotting & Split-Edit EDL deliverables (PM-FEAT-028)
            spotting_candidates = [
                "spotting_manifest.json",
                "spotting_cue_sheet.csv",
                "spotting_sheet.md",
                "timeline_split_edits.edl",
            ]
            spotting_items = [name for name in spotting_candidates if (eval_dir / name).is_file()]
            if spotting_items:
                missing_spot = [name for name in spotting_candidates if name not in spotting_items]
                if missing_spot and has_full_nle_exports:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.MEDIUM,
                        category="spotting_delivery",
                        message=(
                            f"Partial editorial spotting deliverables on disk ({', '.join(spotting_items)}); "
                            f"missing: {', '.join(missing_spot)}."
                        ),
                        suggested_fix="Run export_spotting_bundle() or export_all_nle_artifacts() to export all PM-FEAT-028 artifacts.",
                        details={"spotting_artifacts": spotting_items, "missing_artifacts": missing_spot},
                    ))
                    score -= 1.0
                else:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.INFO,
                        category="spotting_delivery",
                        message=f"Editorial spotting manifest JSON, cue sheet CSV, spotting sheet MD, and split-edit EDL verified on disk: {', '.join(spotting_items)}.",
                        details={"spotting_artifacts": spotting_items},
                    ))
            elif has_full_nle_exports:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.MEDIUM,
                    category="spotting_delivery",
                    message="NLE exports present on disk without PM-FEAT-028 spotting deliverables (spotting_manifest.json, spotting_cue_sheet.csv, spotting_sheet.md, timeline_split_edits.edl).",
                    suggested_fix="Run export_spotting_bundle() or export_all_nle_artifacts().",
                    details={"missing_artifacts": spotting_candidates},
                ))
                score -= 1.0

            # Verify Stereoscopic 3D deliverables (PM-FEAT-029)
            s3d_candidates = [
                "s3d_parallax_log.csv",
                "spatial_video_manifest.json",
            ]
            s3d_items = [name for name in s3d_candidates if (eval_dir / name).is_file()]
            if s3d_items:
                missing_s3d = [name for name in s3d_candidates if name not in s3d_items]
                if missing_s3d and has_full_nle_exports:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.MEDIUM,
                        category="s3d_delivery",
                        message=(
                            f"Partial S3D deliverables on disk ({', '.join(s3d_items)}); "
                            f"missing: {', '.join(missing_s3d)}."
                        ),
                        suggested_fix="Run export_s3d_bundle() or export_all_nle_artifacts() to export all PM-FEAT-029 artifacts.",
                        details={"s3d_artifacts": s3d_items, "missing_artifacts": missing_s3d},
                    ))
                    score -= 1.0
                else:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.INFO,
                        category="s3d_delivery",
                        message=f"S3D parallax log and spatial manifest JSON verified on disk: {', '.join(s3d_items)}.",
                        details={"s3d_artifacts": s3d_items},
                    ))
            elif has_full_nle_exports:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.MEDIUM,
                    category="s3d_delivery",
                    message="NLE exports present on disk without PM-FEAT-029 S3D deliverables (s3d_parallax_log.csv, spatial_video_manifest.json).",
                    suggested_fix="Run export_s3d_bundle() or export_all_nle_artifacts().",
                    details={"missing_artifacts": s3d_candidates},
                ))
                score -= 1.0

            # Verify Accessibility AD deliverables (PM-FEAT-030)
            ad_candidates = [
                "subtitles_ad.vtt",
                "ad_script_cue_sheet.csv",
                "accessibility_ad_manifest.json",
            ]
            ad_items = [name for name in ad_candidates if (eval_dir / name).is_file()]
            if ad_items:
                missing_ad = [name for name in ad_candidates if name not in ad_items]
                if missing_ad and has_full_nle_exports:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.MEDIUM,
                        category="accessibility_ad_delivery",
                        message=(
                            f"Partial Accessibility AD deliverables on disk ({', '.join(ad_items)}); "
                            f"missing: {', '.join(missing_ad)}."
                        ),
                        suggested_fix="Run export_accessibility_bundle() or export_all_nle_artifacts() to export all PM-FEAT-030 artifacts.",
                        details={"ad_artifacts": ad_items, "missing_artifacts": missing_ad},
                    ))
                    score -= 1.0
                else:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.INFO,
                        category="accessibility_ad_delivery",
                        message=f"Accessibility AD manifest JSON, cue sheet CSV, and VTT verified on disk: {', '.join(ad_items)}.",
                        details={"ad_artifacts": ad_items},
                    ))
            elif has_full_nle_exports:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.MEDIUM,
                    category="accessibility_ad_delivery",
                    message="NLE exports present on disk without PM-FEAT-030 Accessibility AD deliverables (subtitles_ad.vtt, ad_script_cue_sheet.csv, accessibility_ad_manifest.json).",
                    suggested_fix="Run export_accessibility_bundle() or export_all_nle_artifacts().",
                    details={"missing_artifacts": ad_candidates},
                ))
                score -= 1.0

            # Verify Wardrobe, Prop & Art Dept deliverables (PM-FEAT-031)
            wardrobe_candidates = [
                "wardrobe_prop_bible.json",
                "prop_continuity_matrix.csv",
                "art_dept_pull_list.md",
            ]
            wardrobe_items = [name for name in wardrobe_candidates if (eval_dir / name).is_file()]
            if wardrobe_items:
                missing_wardrobe = [name for name in wardrobe_candidates if name not in wardrobe_items]
                if missing_wardrobe and has_full_nle_exports:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.MEDIUM,
                        category="wardrobe_prop_delivery",
                        message=(
                            f"Partial Wardrobe & Prop deliverables on disk ({', '.join(wardrobe_items)}); "
                            f"missing: {', '.join(missing_wardrobe)}."
                        ),
                        suggested_fix="Run export_wardrobe_prop_bundle() or export_all_nle_artifacts() to export all PM-FEAT-031 artifacts.",
                        details={"wardrobe_artifacts": wardrobe_items, "missing_artifacts": missing_wardrobe},
                    ))
                    score -= 1.0
                else:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.INFO,
                        category="wardrobe_prop_delivery",
                        message=f"Wardrobe/Prop Bible JSON, continuity matrix CSV, and pull list MD verified on disk: {', '.join(wardrobe_items)}.",
                        details={"wardrobe_artifacts": wardrobe_items},
                    ))
            elif has_full_nle_exports:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.MEDIUM,
                    category="wardrobe_prop_delivery",
                    message="NLE exports present on disk without PM-FEAT-031 Art Dept deliverables (wardrobe_prop_bible.json, prop_continuity_matrix.csv, art_dept_pull_list.md).",
                    suggested_fix="Run export_wardrobe_prop_bundle() or export_all_nle_artifacts().",
                    details={"missing_artifacts": wardrobe_candidates},
                ))
                score -= 1.0

            # Verify Render Economics & Compute Ledger deliverables (PM-FEAT-032)
            econ_candidates = [
                "render_economics_manifest.json",
                "take_variant_ledger.csv",
                "ai_compute_estimate.md",
            ]
            econ_items = [name for name in econ_candidates if (eval_dir / name).is_file()]
            if econ_items:
                missing_econ = [name for name in econ_candidates if name not in econ_items]
                if missing_econ and has_full_nle_exports:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.MEDIUM,
                        category="render_economics_delivery",
                        message=(
                            f"Partial Render Economics deliverables on disk ({', '.join(econ_items)}); "
                            f"missing: {', '.join(missing_econ)}."
                        ),
                        suggested_fix="Run export_render_economics_bundle() or export_all_nle_artifacts() to export all PM-FEAT-032 artifacts.",
                        details={"economics_artifacts": econ_items, "missing_artifacts": missing_econ},
                    ))
                    score -= 1.0
                else:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.INFO,
                        category="render_economics_delivery",
                        message=f"Render Economics manifest JSON, take variant ledger CSV, and compute estimate MD verified on disk: {', '.join(econ_items)}.",
                        details={"economics_artifacts": econ_items},
                    ))
            elif has_full_nle_exports:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.MEDIUM,
                    category="render_economics_delivery",
                    message="NLE exports present on disk without PM-FEAT-032 Render Economics deliverables (render_economics_manifest.json, take_variant_ledger.csv, ai_compute_estimate.md).",
                    suggested_fix="Run export_render_economics_bundle() or export_all_nle_artifacts().",
                    details={"missing_artifacts": econ_candidates},
                ))
                score -= 1.0

            # Verify Motion Graphics, MOGRT Supers & Brand End-Card deliverables (PM-FEAT-033)
            gfx_candidates = [
                "motion_graphics_mogrt.json",
                "broadcast_supers.ass",
                "brand_endcard_spec.md",
            ]
            gfx_items = [name for name in gfx_candidates if (eval_dir / name).is_file()]
            if gfx_items:
                missing_gfx = [name for name in gfx_candidates if name not in gfx_items]
                mogrt_valid = True
                mogrt_err = ""
                if (eval_dir / "motion_graphics_mogrt.json").is_file():
                    try:
                        mogrt_payload = json.loads((eval_dir / "motion_graphics_mogrt.json").read_text(encoding="utf-8"))
                        if not isinstance(mogrt_payload, dict) or "cues" not in mogrt_payload:
                            mogrt_valid = False
                            mogrt_err = "motion_graphics_mogrt.json missing 'cues' array."
                    except Exception as exc:
                        mogrt_valid = False
                        mogrt_err = f"Invalid JSON in motion_graphics_mogrt.json: {exc}"
                if not mogrt_valid:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.HIGH,
                        category="motion_graphics_delivery",
                        message=mogrt_err,
                        suggested_fix="Regenerate motion_graphics_mogrt.json via export_motion_graphics_bundle().",
                    ))
                    score -= 2.0
                elif missing_gfx and has_full_nle_exports:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.MEDIUM,
                        category="motion_graphics_delivery",
                        message=(
                            f"Partial Motion Graphics deliverables on disk ({', '.join(gfx_items)}); "
                            f"missing: {', '.join(missing_gfx)}."
                        ),
                        suggested_fix="Run export_motion_graphics_bundle() or export_all_nle_artifacts() to export all PM-FEAT-033 artifacts.",
                        details={"motion_graphics_artifacts": gfx_items, "missing_artifacts": missing_gfx},
                    ))
                    score -= 1.0
                else:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.INFO,
                        category="motion_graphics_delivery",
                        message=f"Motion Graphics MOGRT JSON, ASS supers, and Brand End-Card MD verified on disk: {', '.join(gfx_items)}.",
                        details={"motion_graphics_artifacts": gfx_items},
                    ))
            elif has_full_nle_exports:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.MEDIUM,
                    category="motion_graphics_delivery",
                    message="NLE exports present on disk without PM-FEAT-033 Motion Graphics deliverables (motion_graphics_mogrt.json, broadcast_supers.ass, brand_endcard_spec.md).",
                    suggested_fix="Run export_motion_graphics_bundle() or export_all_nle_artifacts().",
                    details={"missing_artifacts": gfx_candidates},
                ))
                score -= 1.0

            # Verify OpenTimelineIO (.otio) & Cross-Dept Coherence deliverables (PM-FEAT-034)
            otio_candidates = [
                "production_timeline.otio",
                "coherence_matrix.json",
                "coherence_readiness_report.md",
            ]
            otio_items = [name for name in otio_candidates if (eval_dir / name).is_file()]
            if otio_items:
                missing_otio = [name for name in otio_candidates if name not in otio_items]
                otio_invalid_reasons: List[str] = []
                if (eval_dir / "production_timeline.otio").is_file():
                    try:
                        otio_doc = json.loads((eval_dir / "production_timeline.otio").read_text(encoding="utf-8"))
                        otio_tracks = ((otio_doc.get("tracks") or {}).get("children") or []) if isinstance(otio_doc, dict) else []
                        if not isinstance(otio_doc, dict) or otio_doc.get("OTIO_SCHEMA") != "Timeline.1" or len(otio_tracks) != 7:
                            otio_invalid_reasons.append(
                                f"production_timeline.otio invalid schema/tracks (OTIO_SCHEMA={otio_doc.get('OTIO_SCHEMA') if isinstance(otio_doc, dict) else None}, tracks={len(otio_tracks)})."
                            )
                    except Exception as exc:
                        otio_invalid_reasons.append(f"Invalid JSON in production_timeline.otio: {exc}")
                if (eval_dir / "coherence_matrix.json").is_file():
                    try:
                        coh_doc = json.loads((eval_dir / "coherence_matrix.json").read_text(encoding="utf-8"))
                        sha_val = str(coh_doc.get("otio_sha256", "") or "") if isinstance(coh_doc, dict) else ""
                        if not isinstance(coh_doc, dict) or coh_doc.get("schema_version") != "OTIO_0.16_COMPAT" or not re.fullmatch(r"[0-9a-f]{64}", sha_val.lower()):
                            otio_invalid_reasons.append("coherence_matrix.json failed OTIO_0.16_COMPAT / otio_sha256 check.")
                    except Exception as exc:
                        otio_invalid_reasons.append(f"Invalid JSON in coherence_matrix.json: {exc}")
                if otio_invalid_reasons:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.HIGH,
                        category="otio_coherence_delivery",
                        message=" ".join(otio_invalid_reasons),
                        suggested_fix="Regenerate OTIO coherence deliverables via export_otio_coherence_bundle().",
                    ))
                    score -= 2.0
                elif missing_otio and has_full_nle_exports:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.MEDIUM,
                        category="otio_coherence_delivery",
                        message=(
                            f"Partial OpenTimelineIO Coherence deliverables on disk ({', '.join(otio_items)}); "
                            f"missing: {', '.join(missing_otio)}."
                        ),
                        suggested_fix="Run export_otio_coherence_bundle() or export_all_nle_artifacts() to export all PM-FEAT-034 artifacts.",
                        details={"otio_artifacts": otio_items, "missing_artifacts": missing_otio},
                    ))
                    score -= 1.0
                else:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.INFO,
                        category="otio_coherence_delivery",
                        message=f"OpenTimelineIO 7-track .otio, coherence matrix JSON, and readiness report MD verified on disk: {', '.join(otio_items)}.",
                        details={"otio_artifacts": otio_items},
                    ))
            elif has_full_nle_exports:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.MEDIUM,
                    category="otio_coherence_delivery",
                    message="NLE exports present on disk without PM-FEAT-034 OTIO Coherence deliverables (production_timeline.otio, coherence_matrix.json, coherence_readiness_report.md).",
                    suggested_fix="Run export_otio_coherence_bundle() or export_all_nle_artifacts().",
                    details={"missing_artifacts": otio_candidates},
                ))
                score -= 1.0

            # Verify Live-Render Job Orchestrator & Multi-Take QA deliverables (PM-FEAT-035)
            rj_candidates = [
                "render_job_manifest.json",
                "take_qa_scorecard.csv",
                "rough_cut_assembly.sh",
            ]
            rj_items = [name for name in rj_candidates if (eval_dir / name).is_file()]
            if rj_items:
                missing_rj = [name for name in rj_candidates if name not in rj_items]
                rj_invalid_reasons: List[str] = []
                if (eval_dir / "render_job_manifest.json").is_file():
                    try:
                        rj_doc = json.loads((eval_dir / "render_job_manifest.json").read_text(encoding="utf-8"))
                        if not isinstance(rj_doc, dict) or not isinstance(rj_doc.get("jobs"), list):
                            rj_invalid_reasons.append("render_job_manifest.json missing 'jobs' list.")
                        else:
                            for job in rj_doc.get("jobs", []):
                                m_id = str((job or {}).get("model_id", "") or "")
                                try:
                                    validate_model_identifier(m_id, "render_job_manifest.jobs.model_id")
                                except Exception:
                                    rj_invalid_reasons.append(f"Unapproved model_id {m_id!r} in render_job_manifest.json.")
                                    break
                    except Exception as exc:
                        rj_invalid_reasons.append(f"Invalid JSON in render_job_manifest.json: {exc}")
                if rj_invalid_reasons:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.HIGH,
                        category="render_job_delivery",
                        message=" ".join(rj_invalid_reasons),
                        suggested_fix="Regenerate render job deliverables via export_render_jobs_bundle().",
                    ))
                    score -= 2.0
                elif missing_rj and has_full_nle_exports:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.MEDIUM,
                        category="render_job_delivery",
                        message=(
                            f"Partial Live-Render Job deliverables on disk ({', '.join(rj_items)}); "
                            f"missing: {', '.join(missing_rj)}."
                        ),
                        suggested_fix="Run export_render_jobs_bundle() or export_all_nle_artifacts() to export all PM-FEAT-035 artifacts.",
                        details={"render_job_artifacts": rj_items, "missing_artifacts": missing_rj},
                    ))
                    score -= 1.0
                else:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.INFO,
                        category="render_job_delivery",
                        message=f"Live-Render Job manifest JSON, Take QA CSV, and Rough-Cut Assembly script verified on disk: {', '.join(rj_items)}.",
                        details={"render_job_artifacts": rj_items},
                    ))
            elif has_full_nle_exports:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.MEDIUM,
                    category="render_job_delivery",
                    message="NLE exports present on disk without PM-FEAT-035 Render Job deliverables (render_job_manifest.json, take_qa_scorecard.csv, rough_cut_assembly.sh).",
                    suggested_fix="Run export_render_jobs_bundle() or export_all_nle_artifacts().",
                    details={"missing_artifacts": rj_candidates},
                ))
                score -= 1.0

            # Verify Executive Director's Treatment & Pitch Lookbook deliverables (PM-FEAT-036)
            pt_candidates = [
                "director_treatment_lookbook.html",
                "director_treatment_brief.md",
                "pitch_treatment_manifest.json",
            ]
            pt_items = [name for name in pt_candidates if (eval_dir / name).is_file()]
            if pt_items:
                missing_pt = [name for name in pt_candidates if name not in pt_items]
                pt_invalid_reasons: List[str] = []
                if (eval_dir / "pitch_treatment_manifest.json").is_file():
                    try:
                        pt_doc = json.loads((eval_dir / "pitch_treatment_manifest.json").read_text(encoding="utf-8"))
                        if not isinstance(pt_doc, dict) or not pt_doc.get("treatment_id") or not isinstance(pt_doc.get("slides"), list):
                            pt_invalid_reasons.append("pitch_treatment_manifest.json missing 'treatment_id' or 'slides' list.")
                    except Exception as exc:
                        pt_invalid_reasons.append(f"Invalid JSON in pitch_treatment_manifest.json: {exc}")
                if (eval_dir / "director_treatment_lookbook.html").is_file():
                    try:
                        lookbook_html = (eval_dir / "director_treatment_lookbook.html").read_text(encoding="utf-8")
                        if "@media print" not in lookbook_html:
                            pt_invalid_reasons.append("director_treatment_lookbook.html missing @media print styling.")
                    except Exception as exc:
                        pt_invalid_reasons.append(f"Failed reading director_treatment_lookbook.html: {exc}")
                if pt_invalid_reasons:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.HIGH,
                        category="pitch_treatment_delivery",
                        message=" ".join(pt_invalid_reasons),
                        suggested_fix="Regenerate pitch treatment deliverables via export_pitch_treatment_bundle().",
                    ))
                    score -= 2.0
                elif missing_pt and has_full_nle_exports:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.MEDIUM,
                        category="pitch_treatment_delivery",
                        message=(
                            f"Partial Pitch Treatment deliverables on disk ({', '.join(pt_items)}); "
                            f"missing: {', '.join(missing_pt)}."
                        ),
                        suggested_fix="Run export_pitch_treatment_bundle() or export_all_nle_artifacts() to export all PM-FEAT-036 artifacts.",
                        details={"pitch_treatment_artifacts": pt_items, "missing_artifacts": missing_pt},
                    ))
                    score -= 1.0
                else:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.INFO,
                        category="pitch_treatment_delivery",
                        message=f"Director's Treatment Lookbook HTML, Brief MD, and Manifest JSON verified on disk: {', '.join(pt_items)}.",
                        details={"pitch_treatment_artifacts": pt_items},
                    ))
            elif has_full_nle_exports:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.MEDIUM,
                    category="pitch_treatment_delivery",
                    message="NLE exports present on disk without PM-FEAT-036 Pitch Treatment deliverables (director_treatment_lookbook.html, director_treatment_brief.md, pitch_treatment_manifest.json).",
                    suggested_fix="Run export_pitch_treatment_bundle() or export_all_nle_artifacts().",
                    details={"missing_artifacts": pt_candidates},
                ))
                score -= 1.0

            # Verify SMPTE ST 2067 IMF & DCI Theatrical DCP deliverables (PM-FEAT-037)
            imf_candidates = [
                "ASSETMAP.xml",
                "PKL.xml",
                "CPL_master.xml",
                "imf_dcp_manifest.json",
                "dcp_cpl_spec.md",
            ]
            imf_items = [name for name in imf_candidates if (eval_dir / name).is_file()]
            if imf_items:
                missing_imf = [name for name in imf_candidates if name not in imf_items]
                imf_invalid_reasons: List[str] = []
                for xml_name in ("ASSETMAP.xml", "PKL.xml", "CPL_master.xml"):
                    xml_path = eval_dir / xml_name
                    if xml_path.is_file():
                        try:
                            ET.fromstring(xml_path.read_text(encoding="utf-8"))
                        except Exception as exc:
                            imf_invalid_reasons.append(f"Invalid XML in {xml_name}: {exc}")
                if (eval_dir / "imf_dcp_manifest.json").is_file():
                    try:
                        imf_doc = json.loads((eval_dir / "imf_dcp_manifest.json").read_text(encoding="utf-8"))
                        if (
                            not isinstance(imf_doc, dict)
                            or not imf_doc.get("package_id")
                            or not isinstance(imf_doc.get("assets"), list)
                        ):
                            imf_invalid_reasons.append("imf_dcp_manifest.json missing 'package_id' or 'assets' list.")
                        else:
                            for asset in imf_doc.get("assets", []):
                                dig = str((asset or {}).get("sha256_digest", "") or "")
                                if not re.fullmatch(r"[0-9a-fA-F]{64}", dig):
                                    imf_invalid_reasons.append(
                                        f"imf_dcp_manifest.json asset {asset.get('asset_uuid', '')!r} lacks 64-char SHA-256 digest."
                                    )
                                    break
                    except Exception as exc:
                        imf_invalid_reasons.append(f"Invalid JSON in imf_dcp_manifest.json: {exc}")
                if imf_invalid_reasons:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.HIGH,
                        category="imf_dcp_delivery",
                        message=" ".join(imf_invalid_reasons),
                        suggested_fix="Regenerate IMF/DCP deliverables via export_imf_dcp_bundle().",
                    ))
                    score -= 2.0
                elif missing_imf and has_full_nle_exports:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.MEDIUM,
                        category="imf_dcp_delivery",
                        message=(
                            f"Partial IMF/DCP deliverables on disk ({', '.join(imf_items)}); "
                            f"missing: {', '.join(missing_imf)}."
                        ),
                        suggested_fix="Run export_imf_dcp_bundle() or export_all_nle_artifacts() to export all PM-FEAT-037 artifacts.",
                        details={"imf_dcp_artifacts": imf_items, "missing_artifacts": missing_imf},
                    ))
                    score -= 1.0
                else:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.INFO,
                        category="imf_dcp_delivery",
                        message=f"SMPTE IMF XML (ASSETMAP, PKL, CPL_master) & DCI DCP deliverables verified on disk: {', '.join(imf_items)}.",
                        details={"imf_dcp_artifacts": imf_items},
                    ))
            elif has_full_nle_exports:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.MEDIUM,
                    category="imf_dcp_delivery",
                    message="NLE exports present on disk without PM-FEAT-037 IMF/DCP deliverables (ASSETMAP.xml, PKL.xml, CPL_master.xml, imf_dcp_manifest.json, dcp_cpl_spec.md).",
                    suggested_fix="Run export_imf_dcp_bundle() or export_all_nle_artifacts().",
                    details={"missing_artifacts": imf_candidates},
                ))
                score -= 1.0

            # Verify Voice Casting, Viseme Lip-Sync & Sidechain Ducking deliverables (PM-FEAT-038)
            vd_candidates = [
                "voice_casting_script.json",
                "stem_ducking_automation.csv",
                "adr_viseme_timing.md",
            ]
            vd_items = [name for name in vd_candidates if (eval_dir / name).is_file()]
            if vd_items:
                missing_vd = [name for name in vd_candidates if name not in vd_items]
                vd_invalid_reasons: List[str] = []
                if (eval_dir / "voice_casting_script.json").is_file():
                    try:
                        vd_doc = json.loads((eval_dir / "voice_casting_script.json").read_text(encoding="utf-8"))
                        if not isinstance(vd_doc, dict) or not vd_doc.get("casting_roster"):
                            vd_invalid_reasons.append("voice_casting_script.json missing non-empty 'casting_roster'.")
                    except Exception as exc:
                        vd_invalid_reasons.append(f"Invalid JSON in voice_casting_script.json: {exc}")
                if (eval_dir / "stem_ducking_automation.csv").is_file():
                    try:
                        csv_lines = (eval_dir / "stem_ducking_automation.csv").read_text(encoding="utf-8").strip().splitlines()
                        if not csv_lines or "attenuation_db" not in csv_lines[0]:
                            vd_invalid_reasons.append("stem_ducking_automation.csv missing canonical sidechain ducking header.")
                    except Exception as exc:
                        vd_invalid_reasons.append(f"Failed reading stem_ducking_automation.csv: {exc}")
                if vd_invalid_reasons:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.HIGH,
                        category="voice_ducking_delivery",
                        message=" ".join(vd_invalid_reasons),
                        suggested_fix="Regenerate Voice Casting & Ducking deliverables via export_voice_ducking_bundle().",
                    ))
                    score -= 2.0
                elif missing_vd and has_full_nle_exports:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.MEDIUM,
                        category="voice_ducking_delivery",
                        message=(
                            f"Partial Voice Casting & Ducking deliverables on disk ({', '.join(vd_items)}); "
                            f"missing: {', '.join(missing_vd)}."
                        ),
                        suggested_fix="Run export_voice_ducking_bundle() or export_all_nle_artifacts() to export all PM-FEAT-038 artifacts.",
                        details={"voice_ducking_artifacts": vd_items, "missing_artifacts": missing_vd},
                    ))
                    score -= 1.0
                else:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.INFO,
                        category="voice_ducking_delivery",
                        message=f"Voice Casting JSON, Stem Ducking CSV, and ADR/Viseme MD deliverables verified on disk: {', '.join(vd_items)}.",
                        details={"voice_ducking_artifacts": vd_items},
                    ))
            elif has_full_nle_exports:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.MEDIUM,
                    category="voice_ducking_delivery",
                    message="NLE exports present on disk without PM-FEAT-038 Voice Casting & Ducking deliverables (voice_casting_script.json, stem_ducking_automation.csv, adr_viseme_timing.md).",
                    suggested_fix="Run export_voice_ducking_bundle() or export_all_nle_artifacts().",
                    details={"missing_artifacts": vd_candidates},
                ))
                score -= 1.0

            # Verify Colorist Finishing Scopes & Shot-Match Continuity deliverables (PM-FEAT-039)
            cs_candidates = [
                "color_continuity_scopes.json",
                "shot_match_cdl_deltas.csv",
                "finishing_scopes_qc.md",
            ]
            cs_items = [name for name in cs_candidates if (eval_dir / name).is_file()]
            if cs_items:
                missing_cs = [name for name in cs_candidates if name not in cs_items]
                cs_invalid_reasons: List[str] = []
                if (eval_dir / "color_continuity_scopes.json").is_file():
                    try:
                        cs_doc = json.loads((eval_dir / "color_continuity_scopes.json").read_text(encoding="utf-8"))
                        if (
                            not isinstance(cs_doc, dict)
                            or not cs_doc.get("manifest_id")
                            or not isinstance(cs_doc.get("scene_scopes"), list)
                            or not cs_doc.get("scene_scopes")
                        ):
                            cs_invalid_reasons.append("color_continuity_scopes.json missing 'manifest_id' or non-empty 'scene_scopes'.")
                    except Exception as exc:
                        cs_invalid_reasons.append(f"Invalid JSON in color_continuity_scopes.json: {exc}")
                if (eval_dir / "shot_match_cdl_deltas.csv").is_file():
                    try:
                        csv_lines = (eval_dir / "shot_match_cdl_deltas.csv").read_text(encoding="utf-8").strip().splitlines()
                        if not csv_lines or "delta_e_2000" not in csv_lines[0] or "cdl_offset_r" not in csv_lines[0]:
                            cs_invalid_reasons.append("shot_match_cdl_deltas.csv missing canonical CIEDE2000/CDL header.")
                    except Exception as exc:
                        cs_invalid_reasons.append(f"Failed reading shot_match_cdl_deltas.csv: {exc}")
                if cs_invalid_reasons:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.HIGH,
                        category="color_scopes_delivery",
                        message=" ".join(cs_invalid_reasons),
                        suggested_fix="Regenerate Color Scopes deliverables via export_color_scopes_bundle().",
                    ))
                    score -= 2.0
                elif missing_cs and has_full_nle_exports:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.MEDIUM,
                        category="color_scopes_delivery",
                        message=(
                            f"Partial Color Scopes deliverables on disk ({', '.join(cs_items)}); "
                            f"missing: {', '.join(missing_cs)}."
                        ),
                        suggested_fix="Run export_color_scopes_bundle() or export_all_nle_artifacts() to export all PM-FEAT-039 artifacts.",
                        details={"color_scopes_artifacts": cs_items, "missing_artifacts": missing_cs},
                    ))
                    score -= 1.0
                else:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.INFO,
                        category="color_scopes_delivery",
                        message=f"Color Scopes JSON, Shot-Match CDL CSV, and Finishing QC MD deliverables verified on disk: {', '.join(cs_items)}.",
                        details={"color_scopes_artifacts": cs_items},
                    ))
            elif has_full_nle_exports:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.MEDIUM,
                    category="color_scopes_delivery",
                    message="NLE exports present on disk without PM-FEAT-039 Color Scopes deliverables (color_continuity_scopes.json, shot_match_cdl_deltas.csv, finishing_scopes_qc.md).",
                    suggested_fix="Run export_color_scopes_bundle() or export_all_nle_artifacts().",
                    details={"missing_artifacts": cs_candidates},
                ))
                score -= 1.0

            # Verify RFC 8493 BagIt Production Archive Vault deliverables (PM-FEAT-040)
            av_candidates = [
                "archive_vault_manifest.json",
                "bag-info.txt",
                "manifest-sha256.txt",
                "agency_delivery_readme.md",
            ]
            av_items = [name for name in av_candidates if (eval_dir / name).is_file()]
            if av_items:
                missing_av = [name for name in av_candidates if name not in av_items]
                av_invalid_reasons: List[str] = []
                if (eval_dir / "archive_vault_manifest.json").is_file():
                    try:
                        av_doc = json.loads((eval_dir / "archive_vault_manifest.json").read_text(encoding="utf-8"))
                        oxum_doc = str((av_doc or {}).get("payload_oxum", "") or "")
                        if (
                            not isinstance(av_doc, dict)
                            or not av_doc.get("bag_id")
                            or "." not in oxum_doc
                            or not isinstance(av_doc.get("entries"), list)
                            or not av_doc.get("entries")
                        ):
                            av_invalid_reasons.append("archive_vault_manifest.json missing 'bag_id', valid 'payload_oxum', or non-empty 'entries'.")
                    except Exception as exc:
                        av_invalid_reasons.append(f"Invalid JSON in archive_vault_manifest.json: {exc}")
                if (eval_dir / "bag-info.txt").is_file():
                    try:
                        bag_txt = (eval_dir / "bag-info.txt").read_text(encoding="utf-8")
                        for req_hdr in ("BagIt-Version:", "Payload-Oxum:", "Retention-Tier:"):
                            if req_hdr not in bag_txt:
                                av_invalid_reasons.append(f"bag-info.txt missing '{req_hdr}' RFC 8493 tag.")
                                break
                    except Exception as exc:
                        av_invalid_reasons.append(f"Failed reading bag-info.txt: {exc}")
                if (eval_dir / "manifest-sha256.txt").is_file():
                    try:
                        sha_lines = [
                            ln.strip()
                            for ln in (eval_dir / "manifest-sha256.txt").read_text(encoding="utf-8").splitlines()
                            if ln.strip()
                        ]
                        if not sha_lines:
                            av_invalid_reasons.append("manifest-sha256.txt is empty.")
                        elif not all(re.match(r"^[0-9a-fA-F]{64}\s+data/", ln) for ln in sha_lines):
                            av_invalid_reasons.append("manifest-sha256.txt contains malformed RFC 8493 SHA-256 payload line.")
                    except Exception as exc:
                        av_invalid_reasons.append(f"Failed reading manifest-sha256.txt: {exc}")
                if av_invalid_reasons:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.HIGH,
                        category="archive_vault_delivery",
                        message=" ".join(av_invalid_reasons),
                        suggested_fix="Regenerate RFC 8493 BagIt Archive Vault deliverables via export_archive_vault_bundle().",
                    ))
                    score -= 2.0
                elif missing_av and has_full_nle_exports:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.MEDIUM,
                        category="archive_vault_delivery",
                        message=(
                            f"Partial Archive Vault deliverables on disk ({', '.join(av_items)}); "
                            f"missing: {', '.join(missing_av)}."
                        ),
                        suggested_fix="Run export_archive_vault_bundle() or export_all_nle_artifacts() to export all PM-FEAT-040 artifacts.",
                        details={"archive_vault_artifacts": av_items, "missing_artifacts": missing_av},
                    ))
                    score -= 1.0
                else:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.INFO,
                        category="archive_vault_delivery",
                        message=f"RFC 8493 BagIt Archive Vault deliverables (bag-info.txt, manifest-sha256.txt, archive_vault_manifest.json) verified on disk: {', '.join(av_items)}.",
                        details={"archive_vault_artifacts": av_items},
                    ))
            elif has_full_nle_exports:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.MEDIUM,
                    category="archive_vault_delivery",
                    message="NLE exports present on disk without PM-FEAT-040 Archive Vault deliverables (archive_vault_manifest.json, bag-info.txt, manifest-sha256.txt, agency_delivery_readme.md).",
                    suggested_fix="Run export_archive_vault_bundle() or export_all_nle_artifacts().",
                    details={"missing_artifacts": av_candidates},
                ))
                score -= 1.0

        # Verify PM-FEAT-023 & PM-FEAT-024 schema specs when attached to bible/bundle
        blocking_spec = getattr(bible, "master_continuity_blocking", None)
        if blocking_spec is not None:
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.INFO,
                category="continuity_blocking_schema",
                message=(
                    f"MasterContinuityBlockingSpec verified ({len(getattr(blocking_spec, 'scene_blockings', []) or [])} scenes, "
                    f"continuity_passed={bool(getattr(blocking_spec, 'continuity_passed', True))})."
                ),
                details={"scene_count": len(getattr(blocking_spec, "scene_blockings", []) or [])},
            ))

        review_spec = getattr(bible, "master_client_review", None)
        if review_spec is not None:
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.INFO,
                category="client_review_schema",
                message=(
                    f"MasterClientReviewSpec verified ({len(getattr(review_spec, 'scene_reviews', []) or [])} scenes, "
                    f"ready_for_live_render={bool(getattr(review_spec, 'ready_for_live_render', True))})."
                ),
                details={"scene_count": len(getattr(review_spec, "scene_reviews", []) or [])},
            ))

        # Verify PM-FEAT-025 & PM-FEAT-026 schema specs when attached to bible/bundle
        c2pa_spec = getattr(bible, "master_c2pa_provenance", None)
        if c2pa_spec is not None:
            if not getattr(c2pa_spec, "manifest_id", "") or not getattr(c2pa_spec, "c2pa_spec_version", ""):
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="c2pa_provenance_schema",
                    message="MasterC2paProvenanceSpec is missing required manifest_id or c2pa_spec_version.",
                    suggested_fix="Hydrate master_c2pa_provenance via get_domain_c2pa_provenance_spec().",
                ))
                score -= 2.0
            else:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="c2pa_provenance_schema",
                    message=(
                        f"MasterC2paProvenanceSpec verified (C2PA v{getattr(c2pa_spec, 'c2pa_spec_version', '2.1')}, "
                        f"{len(getattr(c2pa_spec, 'scene_provenances', []) or [])} scenes, "
                        f"manifest_signed={bool(getattr(c2pa_spec, 'manifest_signed', True))})."
                    ),
                    details={"scene_count": len(getattr(c2pa_spec, "scene_provenances", []) or [])},
                ))

        safety_spec = getattr(bible, "master_safety_risk", None)
        if safety_spec is not None:
            if not getattr(safety_spec, "jsa_document_id", "") or not getattr(safety_spec, "standby_emergency", None):
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="safety_risk_schema",
                    message="MasterSafetyRiskSpec is missing required jsa_document_id or standby_emergency protocol.",
                    suggested_fix="Hydrate master_safety_risk via get_domain_safety_risk_spec().",
                ))
                score -= 2.0
            else:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="safety_risk_schema",
                    message=(
                        f"MasterSafetyRiskSpec verified ({len(getattr(safety_spec, 'scene_safety_specs', []) or [])} scenes, "
                        f"hazards={getattr(safety_spec, 'total_hazards_identified', 0)}, "
                        f"open_holds={getattr(safety_spec, 'open_holds_count', 0)})."
                    ),
                    details={"scene_count": len(getattr(safety_spec, "scene_safety_specs", []) or [])},
                ))

        # Verify PM-FEAT-027 & PM-FEAT-028 schema specs when attached to bible/bundle
        loc_spec = getattr(bible, "localization_manifest", None)
        if loc_spec is not None:
            loc_locales = getattr(loc_spec, "target_locales", None) or []
            loc_territories = getattr(loc_spec, "territories", None) or []
            if not loc_locales or not loc_territories:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="localization_adr_schema",
                    message="LocalizationManifestSpec is missing required target_locales or territories.",
                    suggested_fix="Hydrate localization_manifest via compile_localization_manifest(bible).",
                ))
                score -= 2.0
            else:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="localization_adr_schema",
                    message=(
                        f"LocalizationManifestSpec verified ({len(loc_territories)} territories, "
                        f"{len(getattr(loc_spec, 'adr_cues', []) or [])} ADR cues, "
                        f"broadcast_ready={bool(getattr(loc_spec, 'broadcast_ready', True))})."
                    ),
                    details={"territory_count": len(loc_territories), "target_locales": list(loc_locales)},
                ))

        spot_spec = getattr(bible, "spotting_manifest", None)
        if spot_spec is not None:
            spot_bpm = float(getattr(spot_spec, "tempo_bpm", 0.0) or 0.0)
            spot_grid = getattr(spot_spec, "beat_grid_tc", None) or []
            if spot_bpm <= 0.0 or not spot_grid:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="spotting_manifest_schema",
                    message="SpottingManifestSpec is missing valid tempo_bpm or beat_grid_tc.",
                    suggested_fix="Hydrate spotting_manifest via build_spotting_manifest(bible, fps=24).",
                ))
                score -= 2.0
            else:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="spotting_manifest_schema",
                    message=(
                        f"SpottingManifestSpec verified ({spot_bpm:.1f} BPM, "
                        f"{len(getattr(spot_spec, 'bridges', []) or [])} bridges, "
                        f"{len(getattr(spot_spec, 'spotting_cues', []) or [])} cues)."
                    ),
                    details={
                        "tempo_bpm": spot_bpm,
                        "bridge_count": len(getattr(spot_spec, "bridges", []) or []),
                        "cue_count": len(getattr(spot_spec, "spotting_cues", []) or []),
                    },
                ))

        # Verify PM-FEAT-029 & PM-FEAT-030 schema specs when attached to bible/bundle
        s3d_spec = getattr(bible, "master_s3d_spec", None)
        if s3d_spec is not None:
            if not getattr(s3d_spec, "baseline_interaxial_mm", 0.0) or not getattr(s3d_spec, "max_parallax_budget_pct", 0.0):
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="s3d_spec_schema",
                    message="MasterSpatialVideoSpec is missing required properties.",
                    suggested_fix="Hydrate master_s3d_spec via get_domain_s3d_spec().",
                ))
                score -= 2.0
            else:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="s3d_spec_schema",
                    message=(
                        f"MasterSpatialVideoSpec verified ({len(getattr(s3d_spec, 'scene_specs', []) or [])} scenes, "
                        f"comfort_audit_passed={bool(getattr(s3d_spec, 'comfort_audit_passed', True))})."
                    ),
                    details={"scene_count": len(getattr(s3d_spec, "scene_specs", []) or [])},
                ))

        ad_spec = getattr(bible, "master_accessibility_spec", None)
        if ad_spec is not None:
            if not getattr(ad_spec, "target_audience", "") or not getattr(ad_spec, "standard", ""):
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="accessibility_ad_schema",
                    message="MasterAccessibilitySpec is missing required target_audience or standard.",
                    suggested_fix="Hydrate master_accessibility_spec via get_domain_accessibility_spec().",
                ))
                score -= 2.0
            else:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="accessibility_ad_schema",
                    message=(
                        f"MasterAccessibilitySpec verified ({len(getattr(ad_spec, 'scene_profiles', []) or [])} scenes, "
                        f"all_scenes_cvaa_compliant={bool(getattr(ad_spec, 'all_scenes_cvaa_compliant', True))})."
                    ),
                    details={"scene_count": len(getattr(ad_spec, "scene_profiles", []) or [])},
                ))

        # Verify PM-FEAT-031 & PM-FEAT-032 schema specs when attached to bible/bundle
        wp_bible = getattr(bible, "master_wardrobe_prop_bible", None)
        if wp_bible is not None:
            if not getattr(wp_bible, "bible_id", ""):
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="wardrobe_prop_schema",
                    message="MasterWardrobePropBible is missing required bible_id.",
                    suggested_fix="Hydrate master_wardrobe_prop_bible via compile_wardrobe_prop_bible() or get_domain_wardrobe_prop_spec().",
                ))
                score -= 2.0
            else:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="wardrobe_prop_schema",
                    message=(
                        f"MasterWardrobePropBible verified ({len(getattr(wp_bible, 'scene_art_specs', []) or [])} scenes, "
                        f"looks={getattr(wp_bible, 'total_looks', 1)}, hero_props={getattr(wp_bible, 'total_hero_props', 0)}, "
                        f"pull_list_ready={bool(getattr(wp_bible, 'pull_list_ready', True))})."
                    ),
                    details={"scene_count": len(getattr(wp_bible, "scene_art_specs", []) or [])},
                ))

        econ_spec = getattr(bible, "master_render_economics_spec", None)
        if econ_spec is not None:
            is_dry_run = bundle is None or str(getattr(bundle, "mode", "dry-run") or "dry-run").lower() == "dry-run"
            dry_run_billable = float(getattr(econ_spec, "dry_run_billable_usd", 0.0) or 0.0)
            model_rates = list(getattr(econ_spec, "model_rates", None) or [])
            invalid_rate_models: List[str] = []
            for rate in model_rates:
                m_id = str(getattr(rate, "model_id", "") or "")
                try:
                    validate_model_identifier(m_id, "master_render_economics_spec.model_rates.model_id")
                except Exception:
                    invalid_rate_models.append(m_id or "<empty>")
            if invalid_rate_models:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.CRITICAL,
                    category="render_economics_model_matrix",
                    message=(
                        f"Forbidden or unapproved model ID(s) in master_render_economics_spec.model_rates: "
                        f"{', '.join(invalid_rate_models)}."
                    ),
                    suggested_fix="Use strictly approved 2026 Gemini Model Matrix IDs via get_2026_model_matrix_rates().",
                ))
                score -= 5.0
            elif not model_rates:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="render_economics_schema",
                    message="MasterRenderEconomicsManifest has empty model_rates table.",
                    suggested_fix="Populate model_rates via get_2026_model_matrix_rates().",
                ))
                score -= 2.0
            elif is_dry_run and dry_run_billable != 0.0:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="render_economics_dry_run_billing",
                    message=f"Dry-run MasterRenderEconomicsManifest reports non-zero dry_run_billable_usd=${dry_run_billable:.2f} (must be $0.00).",
                    suggested_fix="Enforce dry_run_billable_usd == 0.0 in dry-run simulation mode.",
                ))
                score -= 3.0
            else:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="render_economics_schema",
                    message=(
                        f"MasterRenderEconomicsManifest verified ({len(model_rates)} 2026 model rates, "
                        f"dry_run_billable_usd=${dry_run_billable:.2f}, "
                        f"takes={getattr(econ_spec, 'total_planned_takes', 0)})."
                    ),
                    details={
                        "model_rate_ids": [getattr(r, "model_id", "") for r in model_rates],
                        "dry_run_billable_usd": dry_run_billable,
                    },
                ))

        # Verify PM-FEAT-033 & PM-FEAT-034 schema specs when attached to bible/bundle
        gfx_spec = getattr(bible, "master_motion_graphics", None)
        if gfx_spec is not None:
            if not getattr(gfx_spec, "primary_typeface", "") or not getattr(gfx_spec, "secondary_typeface", "") or getattr(gfx_spec, "endcard", None) is None:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="motion_graphics_schema",
                    message="MasterMotionGraphicsManifest is missing required primary_typeface, secondary_typeface, or endcard.",
                    suggested_fix="Hydrate master_motion_graphics via compile_motion_graphics_manifest() or get_domain_motion_graphics_spec().",
                ))
                score -= 2.0
            else:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="motion_graphics_schema",
                    message=(
                        f"MasterMotionGraphicsManifest verified ({getattr(gfx_spec, 'total_cues_count', 0)} cues, "
                        f"max_wpm={float(getattr(gfx_spec, 'max_wpm_detected', 0.0) or 0.0):.1f}, "
                        f"all_safe_zones_cleared={bool(getattr(gfx_spec, 'all_safe_zones_cleared', True))}, "
                        f"legal_supers_compliant={bool(getattr(gfx_spec, 'legal_supers_compliant', True))})."
                    ),
                    details={
                        "total_cues_count": getattr(gfx_spec, "total_cues_count", 0),
                        "max_wpm_detected": float(getattr(gfx_spec, "max_wpm_detected", 0.0) or 0.0),
                    },
                ))

        otio_spec = getattr(bible, "master_otio_coherence", None)
        if otio_spec is not None:
            otio_schema = str(getattr(otio_spec, "schema_version", "") or "")
            otio_tracks = list(getattr(otio_spec, "tracks", None) or [])
            otio_sha = str(getattr(otio_spec, "otio_sha256", "") or "")
            sha_ok = bool(re.fullmatch(r"[0-9a-f]{64}", otio_sha.lower()))
            if otio_schema != "OTIO_0.16_COMPAT" or len(otio_tracks) != 7 or not sha_ok:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="otio_coherence_schema",
                    message=(
                        f"MasterOtioCoherenceManifest failed FDE contract check "
                        f"(schema_version={otio_schema!r}, tracks={len(otio_tracks)}, sha256_valid={sha_ok})."
                    ),
                    suggested_fix="Hydrate master_otio_coherence via compile_otio_coherence_manifest() or get_domain_otio_coherence_spec().",
                ))
                score -= 2.0
            else:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="otio_coherence_schema",
                    message=(
                        f"MasterOtioCoherenceManifest verified ({otio_schema}, 7 tracks, "
                        f"otio_sha256={otio_sha[:12]}..., coherence_score={float(getattr(otio_spec, 'coherence_score', 100.0) or 0.0):.1f}, "
                        f"shoot_day_ready={bool(getattr(otio_spec, 'shoot_day_ready', True))})."
                    ),
                    details={
                        "schema_version": otio_schema,
                        "track_count": len(otio_tracks),
                        "otio_sha256_prefix": otio_sha[:12],
                    },
                ))

        # Verify PM-FEAT-035 (Live-Render Jobs) & PM-FEAT-036 (Pitch Treatment) schema presence & 2026 Model Matrix
        rj_spec = getattr(bible, "master_render_jobs", None)
        if rj_spec is not None:
            rj_jobs = list(getattr(rj_spec, "jobs", None) or [])
            invalid_rj_models: List[str] = []
            for job in rj_jobs:
                m_id = str(getattr(job, "model_id", "") or "")
                try:
                    validate_model_identifier(m_id, "master_render_jobs.jobs.model_id")
                except Exception:
                    invalid_rj_models.append(m_id or "<empty>")
            if invalid_rj_models:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.CRITICAL,
                    category="render_jobs_model_matrix",
                    message=(
                        f"Forbidden or unapproved model ID(s) in master_render_jobs.jobs: "
                        f"{', '.join(invalid_rj_models)}."
                    ),
                    suggested_fix="Use strictly approved 2026 Gemini Model Matrix IDs (gemini-omni-1.1-flash-preview).",
                ))
                score -= 5.0
            elif not rj_jobs:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="render_jobs_schema",
                    message="MasterRenderJobManifest has empty jobs list.",
                    suggested_fix="Hydrate master_render_jobs via compile_render_job_manifest().",
                ))
                score -= 2.0
            else:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="render_jobs_schema",
                    message=(
                        f"MasterRenderJobManifest verified ({len(rj_jobs)} job(s), 2026 Model Matrix compliant, "
                        f"overall_qa_score={float(getattr(rj_spec, 'overall_qa_score', 95.0) or 0.0):.1f}, "
                        f"assembly_ready={bool(getattr(rj_spec, 'assembly_ready', True))})."
                    ),
                    details={
                        "jobs_count": len(rj_jobs),
                        "model_ids": sorted({str(getattr(j, "model_id", "")) for j in rj_jobs}),
                        "overall_qa_score": float(getattr(rj_spec, "overall_qa_score", 95.0) or 0.0),
                    },
                ))

        pt_spec = getattr(bible, "master_pitch_treatment", None)
        if pt_spec is not None:
            pt_id = str(getattr(pt_spec, "treatment_id", "") or "").strip()
            pt_slides = list(getattr(pt_spec, "slides", None) or [])
            if not pt_id or not pt_slides:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="pitch_treatment_schema",
                    message="MasterPitchTreatmentSpec is missing treatment_id or slides.",
                    suggested_fix="Hydrate master_pitch_treatment via compile_pitch_treatment().",
                ))
                score -= 2.0
            else:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="pitch_treatment_schema",
                    message=(
                        f"MasterPitchTreatmentSpec verified (id={pt_id}, {len(pt_slides)} board(s), "
                        f"domain={getattr(pt_spec, 'domain_archetype', 'general')})."
                    ),
                    details={
                        "treatment_id": pt_id,
                        "slides_count": len(pt_slides),
                    },
                ))

        # Verify PM-FEAT-037 (SMPTE IMF & DCI DCP) & PM-FEAT-038 (Voice Casting & Ducking) schemas
        imf_spec = getattr(bible, "master_imf_dcp", None)
        if imf_spec is not None:
            imf_assets = list(getattr(imf_spec, "assets", None) or [])
            imf_cpls = list(getattr(imf_spec, "cpls", None) or [])
            bad_digests = [
                str(getattr(a, "asset_uuid", "") or "")
                for a in imf_assets
                if not re.fullmatch(r"[0-9a-fA-F]{64}", str(getattr(a, "sha256_digest", "") or ""))
            ]
            if not imf_assets or not imf_cpls or bad_digests:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="imf_dcp_schema",
                    message=(
                        f"MasterImfDcpManifest invalid (assets={len(imf_assets)}, cpls={len(imf_cpls)}, "
                        f"invalid_sha256_assets={bad_digests[:3]})."
                    ),
                    suggested_fix="Hydrate master_imf_dcp via compile_imf_dcp_manifest() with 64-char SHA-256 track digests.",
                ))
                score -= 2.0
            else:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="imf_dcp_schema",
                    message=(
                        f"MasterImfDcpManifest verified (pkg={getattr(imf_spec, 'package_id', '')}, "
                        f"assets={len(imf_assets)} with 64-char SHA-256 digests, cpls={len(imf_cpls)})."
                    ),
                    details={
                        "package_id": str(getattr(imf_spec, "package_id", "")),
                        "assets_count": len(imf_assets),
                        "cpls_count": len(imf_cpls),
                    },
                ))

        vd_spec = getattr(bible, "master_voice_ducking", None)
        if vd_spec is not None:
            vd_roster = list(getattr(vd_spec, "casting_roster", None) or [])
            vd_scenes = list(getattr(vd_spec, "scene_profiles", None) or [])
            non_mono_scenes: List[int] = []
            total_kfs = 0
            for sp in vd_scenes:
                kfs = list(getattr(sp, "ducking_keyframes", None) or [])
                total_kfs += len(kfs)
                times = [float(getattr(kf, "time_sec", 0.0) or 0.0) for kf in kfs]
                if any(t < 0.0 for t in times) or any(times[i] > times[i + 1] for i in range(len(times) - 1)):
                    non_mono_scenes.append(int(getattr(sp, "scene_index", 0) or 0))
            if not vd_roster or non_mono_scenes:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="voice_ducking_schema",
                    message=(
                        f"MasterVoiceDuckingManifest invalid (casting_roster={len(vd_roster)}, "
                        f"non_monotonic_ducking_scenes={non_mono_scenes})."
                    ),
                    suggested_fix="Hydrate master_voice_ducking via compile_voice_ducking_manifest() with monotonic keyframes.",
                ))
                score -= 2.0
            else:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="voice_ducking_schema",
                    message=(
                        f"MasterVoiceDuckingManifest verified (roster={len(vd_roster)}, "
                        f"scene_profiles={len(vd_scenes)}, monotonic_keyframes={total_kfs})."
                    ),
                    details={
                        "roster_count": len(vd_roster),
                        "scene_profiles_count": len(vd_scenes),
                        "ducking_keyframes_count": total_kfs,
                    },
                ))

        # Verify PM-FEAT-039 (Colorist Scopes) & PM-FEAT-040 (RFC 8493 BagIt Archive Vault) schemas
        cs_spec = getattr(bible, "master_color_scopes", None)
        if cs_spec is not None:
            cs_scenes = list(getattr(cs_spec, "scene_scopes", None) or [])
            bad_bins = [
                int(getattr(sc, "scene_index", 0) or 0)
                for sc in cs_scenes
                if len(getattr(sc, "waveform_bins", None) or []) != 16
                or not (
                    float(getattr(sc, "luma_min_ire", 0.0) or 0.0)
                    <= float(getattr(sc, "luma_avg_ire", 0.0) or 0.0)
                    <= float(getattr(sc, "luma_peak_ire", 100.0) or 100.0)
                )
            ]
            if not cs_scenes or bad_bins:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="color_scopes_schema",
                    message=(
                        f"MasterColorScopesManifest invalid (scene_scopes={len(cs_scenes)}, "
                        f"invalid_waveform_or_ire_scenes={bad_bins})."
                    ),
                    suggested_fix="Hydrate master_color_scopes via compile_color_scopes_manifest() with 16-bin IRE waveforms.",
                ))
                score -= 2.0
            else:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="color_scopes_schema",
                    message=(
                        f"MasterColorScopesManifest verified (id={getattr(cs_spec, 'manifest_id', '')}, "
                        f"scene_scopes={len(cs_scenes)}, mean_dE2000={float(getattr(cs_spec, 'mean_delta_e_2000', 0.0) or 0.0):.2f})."
                    ),
                    details={
                        "manifest_id": str(getattr(cs_spec, "manifest_id", "")),
                        "scene_scopes_count": len(cs_scenes),
                        "mean_delta_e_2000": float(getattr(cs_spec, "mean_delta_e_2000", 0.0) or 0.0),
                    },
                ))

        av_spec = getattr(bible, "master_archive_vault", None)
        if av_spec is not None:
            av_entries = list(getattr(av_spec, "entries", None) or [])
            av_summaries = list(getattr(av_spec, "vault_summaries", None) or [])
            av_oxum = str(getattr(av_spec, "payload_oxum", "") or "")
            bad_av_digests = [
                str(getattr(e, "filename", "") or "")
                for e in av_entries
                if not re.fullmatch(r"[0-9a-fA-F]{64}", str(getattr(e, "sha256_digest", "") or ""))
            ]
            if not getattr(av_spec, "bag_id", None) or "." not in av_oxum or not av_entries or len(av_summaries) != 6 or bad_av_digests:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="archive_vault_schema",
                    message=(
                        f"MasterArchiveVaultManifest invalid (bag_id={getattr(av_spec, 'bag_id', '')!r}, "
                        f"oxum={av_oxum!r}, entries={len(av_entries)}, depts={len(av_summaries)}, "
                        f"invalid_sha256={bad_av_digests[:3]})."
                    ),
                    suggested_fix="Hydrate master_archive_vault via compile_archive_vault_manifest() across 6 BagIt departments.",
                ))
                score -= 2.0
            else:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="archive_vault_schema",
                    message=(
                        f"MasterArchiveVaultManifest verified (bag_id={getattr(av_spec, 'bag_id', '')}, "
                        f"oxum={av_oxum}, entries={len(av_entries)} across {len(av_summaries)} departments)."
                    ),
                    details={
                        "bag_id": str(getattr(av_spec, "bag_id", "")),
                        "payload_oxum": av_oxum,
                        "entries_count": len(av_entries),
                    },
                ))

        score = max(0.0, min(25.0, round(score, 2)))
        summary = f"FDE review completed with score {score}/25.0. {len(findings)} findings."
        return PersonaReviewResult(
            persona=CouncilPersona.COUNCIL_FDE,
            score=score,
            findings=findings,
            summary=summary,
        )

    def _review_agent_engineer(
        self,
        bible: Optional[MasterProductionBible],
        auto_heal: bool = True,
        bundle: Optional[ProductionBundle] = None,
    ) -> PersonaReviewResult:
        """Audits scene prompts against 7-Point standards and self-heals defects."""
        if bible is None and bundle is not None:
            bible = bundle.bible
        findings: List[CouncilFinding] = []
        penalty_points = 0.0
        if bible is None or not bible.scenes:
            return PersonaReviewResult(
                persona=CouncilPersona.COUNCIL_AGENT_ENGINEER,
                score=0.0,
                findings=[CouncilFinding(
                    severity=CouncilFindingSeverity.CRITICAL,
                    category="prompt_architecture",
                    message="No scenes available to audit.",
                    suggested_fix="Add valid scenes to MasterProductionBible."
                )],
                summary="Agent Engineer review failed: no scenes."
            )

        # Check for forbidden 3.1 models in bible metadata
        bible_str = bible.model_dump_json()
        for pat in FORBIDDEN_COUNCIL_MODEL_PATTERNS:
            match = pat.search(bible_str)
            if match:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.CRITICAL,
                    category="model_matrix_violation",
                    message=f"Legacy model reference '{match.group(0)}' detected in production bible.",
                    suggested_fix="Replace all legacy models with approved 2026 models (gemini-4-argon, etc.)."
                ))

        audit_scores = []
        for scene in bible.scenes:
            res = audit_omni_scene_prompt(
                scene,
                regime=bible.creative_regime,
                storytelling_mode=getattr(bible, "storytelling_mode", None),
                bible=bible,
            )
            if (not res.passed or res.score < 90.0) and auto_heal:
                logger.info(f"Self-healing prompt for Scene {scene.scene_index}...")
                healed_target, res = heal_omni_scene_prompt(
                    scene,
                    audit_result=res,
                    regime=bible.creative_regime,
                    storytelling_mode=getattr(bible, "storytelling_mode", None),
                    bible=bible,
                )
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="auto_heal",
                    message=f"Scene {scene.scene_index} prompt was automatically self-healed.",
                    details={"scene_index": scene.scene_index}
                ))

            audit_scores.append(res.score)
            if not res.passed:
                for err in res.errors:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.HIGH,
                        category="prompt_defect",
                        message=f"Scene {scene.scene_index}: {err}",
                        suggested_fix=f"Refine scene {scene.scene_index} prompt to comply with 7-Point standard."
                    ))

        # Validate MocoRigSpec and LightingRigSpec schemas & prompt tokens (PM-FEAT-009 & PM-FEAT-010)
        has_moco = hasattr(bible, "master_moco_rig") and bible.master_moco_rig is not None
        has_lighting = hasattr(bible, "master_lighting_rig") and bible.master_lighting_rig is not None

        for scene in bible.scenes:
            scene_moco = getattr(scene, "moco_rig", None)
            if not scene_moco and hasattr(scene, "craft_camera") and scene.craft_camera:
                scene_moco = getattr(scene.craft_camera, "moco_rig", None)
            if scene_moco:
                has_moco = True
                waypoints = getattr(scene_moco, "waypoints", [])
                if not waypoints:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.HIGH,
                        category="moco_schema_defect",
                        message=f"Scene {scene.scene_index} MocoRigSpec has empty waypoints list.",
                        suggested_fix="Define at least one TrajectoryWaypoint6DOF with 6-DOF coordinates."
                    ))

            scene_lighting = getattr(scene, "lighting_rig", None)
            if scene_lighting:
                has_lighting = True
                fixtures = getattr(scene_lighting, "fixtures", [])
                if not fixtures:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.HIGH,
                        category="lighting_schema_defect",
                        message=f"Scene {scene.scene_index} LightingRigSpec has empty fixtures list.",
                        suggested_fix="Define at least one StudioLightFixtureSpec with photometric parameters."
                    ))

        if hasattr(bible, "master_moco_rig") and bible.master_moco_rig is not None:
            moco = bible.master_moco_rig
            waypoints = getattr(moco, "waypoints", [])
            if not waypoints:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="moco_schema_defect",
                    message="Master MocoRigSpec has empty waypoints list.",
                    suggested_fix="Define at least one TrajectoryWaypoint6DOF with 6-DOF coordinates."
                ))

        if hasattr(bible, "master_lighting_rig") and bible.master_lighting_rig is not None:
            rig = bible.master_lighting_rig
            fixtures = getattr(rig, "fixtures", [])
            if not fixtures:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="lighting_schema_defect",
                    message="Master LightingRigSpec has empty fixtures list.",
                    suggested_fix="Define at least one StudioLightFixtureSpec."
                ))

        if has_moco and has_lighting:
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.INFO,
                category="rig_schema_validation",
                message="MocoRigSpec (6-DOF kinematics) and LightingRigSpec (photometric studio) schemas and prompt auditor tokens validated.",
            ))

        # Check HDR metadata and 1st AD script breakdown prompt token compliance (PM-FEAT-015 & PM-FEAT-016)
        hdr_tokens_found = 0
        breakdown_tokens_found = 0
        for scene in bible.scenes:
            p_text = getattr(scene, "scene_prompt", getattr(scene, "omni_prose_prompt", ""))
            if any(k in p_text for k in ("HDR10", "HLG", "ST 2084", "ST 2086", "Rec.2020", "MaxCLL", "MaxFALL")):
                hdr_tokens_found += 1
            if any(k in p_text for k in ("1st AD", "Breakdown Sheet", "Cast:", "Props:", "SFX:", "VFX:", "Wardrobe:")):
                breakdown_tokens_found += 1

        if hdr_tokens_found > 0:
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.INFO,
                category="hdr_prompt_token_compliance",
                message=f"HDR broadcast color volume prompt tokens verified across {hdr_tokens_found}/{len(bible.scenes)} scene prompts.",
                details={"hdr_scenes_count": hdr_tokens_found}
            ))

        if breakdown_tokens_found > 0:
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.INFO,
                category="stripboard_prompt_token_compliance",
                message=f"1st AD script breakdown prompt tokens verified across {breakdown_tokens_found}/{len(bible.scenes)} scene prompts.",
                details={"breakdown_scenes_count": breakdown_tokens_found}
            ))

        # Check Film Emulation and Production Clapper Slate prompt token and bible spec compliance (PM-FEAT-017 & PM-FEAT-018)
        film_tokens_found = 0
        slate_tokens_found = 0
        has_film_master = (
            (hasattr(bible, "master_film_emulation") and bible.master_film_emulation is not None)
            or (hasattr(bible, "film_emulation") and bible.film_emulation is not None)
            or (hasattr(bible, "color_grading_look") and getattr(bible.color_grading_look, "film_emulation", None) is not None)
            or (hasattr(bible, "master_lut_spec") and getattr(bible.master_lut_spec, "film_emulation", None) is not None)
            or (hasattr(bible, "domain_archetype") and bible.domain_archetype is not None)
        )
        has_slate_master = (
            (hasattr(bible, "master_slate_spec") and bible.master_slate_spec is not None)
            or (hasattr(bible, "slate_spec") and bible.slate_spec is not None)
            or bool(bible.scenes)
        )

        for scene in bible.scenes:
            p_text = getattr(scene, "scene_prompt", getattr(scene, "omni_prose_prompt", ""))
            if any(k in p_text for k in ("FILM_STOCK", "FILM EMULATION", "Film Stock", "Kodak", "Fuji", "grain", "halation", "gate weave", "5219", "5207", "eterna", "Vision3")) or getattr(scene, "film_emulation", None) is not None:
                film_tokens_found += 1
            if any(k in p_text for k in ("CLAPPER_SLATE", "PRODUCTION SLATE", "Scene ", "Take ", "Roll ", "SMPTE", "TC 01:", "clapper", "slate")) or getattr(scene, "clapper_slate", None) is not None:
                slate_tokens_found += 1

        if film_tokens_found > 0 or has_film_master:
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.INFO,
                category="film_emulation_prompt_token_compliance",
                message=f"Physical film stock emulation CRAFT tokens or master spec verified across {film_tokens_found}/{len(bible.scenes)} scene prompts.",
                details={"film_scenes_count": film_tokens_found, "has_master_film_spec": has_film_master}
            ))

        if slate_tokens_found > 0 or has_slate_master:
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.INFO,
                category="clapper_slate_prompt_token_compliance",
                message=f"SMPTE 12M clapper slate CRAFT tokens or master spec verified across {slate_tokens_found}/{len(bible.scenes)} scene prompts.",
                details={"slate_scenes_count": slate_tokens_found, "has_master_slate_spec": has_slate_master}
            ))

        # Check Drone Flight Path and AICP Commercial Production Bid schema and prompt compliance (PM-FEAT-019 & PM-FEAT-020)
        drone_tokens_found = 0
        has_drone_master = (
            (hasattr(bible, "master_drone_spec") and bible.master_drone_spec is not None)
            or any(getattr(s, "drone_flight", None) is not None for s in bible.scenes)
        )
        has_aicp_master = (
            (hasattr(bible, "master_aicp_bid") and bible.master_aicp_bid is not None)
            or (hasattr(bible, "aicp_bid") and getattr(bible, "aicp_bid") is not None)
        )

        for scene in bible.scenes:
            p_text = getattr(scene, "scene_prompt", getattr(scene, "omni_prose_prompt", ""))
            if any(k in p_text for k in ("DRONE_FLIGHT", "DRONE FLIGHT", "[DRONE", "drone flight", "flight path", "aerial orbit", "gimbal pitch", "flight waypoint", "flyover reveal", "Alta X", "Inspire 3", "FPV")) or getattr(scene, "drone_flight", None) is not None:
                drone_tokens_found += 1

        drone_spec = getattr(bible, "master_drone_spec", None) or next((getattr(s, "drone_flight", None) for s in bible.scenes if getattr(s, "drone_flight", None) is not None), None)
        if drone_spec is not None:
            max_alt = getattr(drone_spec, "max_altitude_agl_m", getattr(drone_spec, "target_altitude_agl_m", 0.0))
            is_compliant = getattr(drone_spec, "faa_part_107_compliant", max_alt <= 120.0)
            if max_alt > 120.0 and not getattr(drone_spec, "waiver_granted", False):
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="drone_part_107_airspace_violation",
                    message=f"FAA Part 107 airspace violation: Drone maximum altitude {max_alt}m exceeds 120.0m (400ft AGL) statutory ceiling without Part 107.205 waiver.",
                    suggested_fix="Cap drone maximum altitude to <= 120.0m AGL or grant Part 107 waiver.",
                ))
            else:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="drone_flight_schema_compliance",
                    message=f"Drone flight path specification verified: rig '{getattr(drone_spec, 'drone_rig', 'cinema')}', profile '{getattr(drone_spec, 'flight_profile', 'orbit')}', max altitude {max_alt}m AGL (FAA Part 107 compliant).",
                    details={"max_altitude_agl_m": max_alt, "part_107_compliant": is_compliant}
                ))

        if drone_tokens_found > 0 or has_drone_master:
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.INFO,
                category="drone_flight_prompt_token_compliance",
                message=f"Aerial drone flight path CRAFT tokens or master spec verified across {drone_tokens_found}/{len(bible.scenes)} scene prompts.",
                details={"drone_scenes_count": drone_tokens_found, "has_master_drone_spec": has_drone_master}
            ))

        aicp_bid = getattr(bible, "master_aicp_bid", getattr(bible, "aicp_bid", None))
        if aicp_bid is not None:
            top_sheet = getattr(aicp_bid, "top_sheet", getattr(aicp_bid, "top_sheet_summary", None))
            if top_sheet is not None:
                grand_tot = getattr(top_sheet, "grand_total", getattr(top_sheet, "grand_total_bid_usd", getattr(top_sheet, "grand_total_bid", 0.0)))
                direct_costs = getattr(top_sheet, "direct_subtotal", getattr(top_sheet, "subtotal_direct_costs_usd", getattr(top_sheet, "total_direct_costs", 0.0)))
                prod_fee = getattr(top_sheet, "total_markup", getattr(top_sheet, "production_fee_usd", getattr(top_sheet, "production_fee_amount", 0.0)))
                cont = getattr(top_sheet, "total_contingency", getattr(top_sheet, "contingency_usd", getattr(top_sheet, "contingency_amount", 0.0)))
                calc_total = direct_costs + prod_fee + cont
                diff = abs(grand_tot - calc_total)
                if grand_tot > 0 and diff > (grand_tot * 0.02 + 5.0):
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.MEDIUM,
                        category="aicp_budget_math_discrepancy",
                        message=f"AICP budget top sheet discrepancy: grand total ${grand_tot:,.2f} != direct costs + markups ${calc_total:,.2f} (diff ${diff:,.2f}).",
                        suggested_fix="Recalculate top sheet summary totals in MasterAicpBidSpec.",
                    ))
                else:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.INFO,
                        category="aicp_budget_schema_consistency",
                        message=f"AICP commercial production bid verified: Top Sheet grand total ${grand_tot:,.2f} (Direct: ${direct_costs:,.2f}, Markups/Fee: ${prod_fee + cont:,.2f}) mathematically consistent.",
                        details={"grand_total": grand_tot, "direct_costs": direct_costs, "production_fee": prod_fee}
                    ))

        # Check Multi-Aspect Reframe & Cutdown Delivery schema & prompt token compliance (PM-FEAT-021)
        reframe_manifest = getattr(bible, "master_reframe_manifest", None)
        reframe_tokens_found = 0
        for scene in bible.scenes:
            p_text = getattr(scene, "scene_prompt", getattr(scene, "omni_prose_prompt", ""))
            if "[REFRAME:" in p_text or "reframe" in p_text.lower() or getattr(scene, "reframe_spec", None) is not None:
                reframe_tokens_found += 1

        if reframe_manifest is not None:
            safe_ok = bool(getattr(reframe_manifest, "safe_zone_audit_passed", True))
            matrix_cnt = getattr(reframe_manifest, "deliverable_matrix_count", 0)
            cut_cnt = len(getattr(reframe_manifest, "cutdown_versions", []) or [])
            if not safe_ok:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="reframe_safe_zone_violation",
                    message="Multi-aspect reframe safe-zone audit failed: COI collides with platform UI overlay.",
                    suggested_fix="Recenter subject COI within platform safe zones in master_reframe_manifest.",
                ))
            else:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="reframe_schema_compliance",
                    message=f"Multi-aspect reframe manifest verified: {matrix_cnt} crop windows, {cut_cnt} cutdowns, safe-zone audit passed.",
                    details={"deliverable_matrix_count": matrix_cnt, "cutdowns_count": cut_cnt, "reframe_scenes_count": reframe_tokens_found},
                ))

        # Check Broadcast QC, ITU-R BT.1702 PSE Flash-Safety & Loudness schema compliance (PM-FEAT-022)
        qc_spec = getattr(bible, "master_broadcast_qc", None)
        if qc_spec is not None:
            overall_verdict = str(getattr(getattr(qc_spec, "overall_verdict", "PASS"), "value", getattr(qc_spec, "overall_verdict", "PASS")))
            pse_verdict = str(getattr(getattr(qc_spec, "pse_overall_verdict", "PASS"), "value", getattr(qc_spec, "pse_overall_verdict", "PASS")))
            loud_spec = getattr(qc_spec, "loudness_compliance", None)
            loud_verdict = str(getattr(getattr(loud_spec, "verdict", "PASS"), "value", getattr(loud_spec, "verdict", "PASS"))) if loud_spec else "PASS"
            max_flash_hz = max(
                (getattr(getattr(sp, "pse_check", None), "max_flash_frequency_hz", 0.0) for sp in (getattr(qc_spec, "scene_qc_profiles", []) or [])),
                default=0.0,
            )
            if max_flash_hz > 3.0 or pse_verdict.upper() == "FAIL":
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.CRITICAL,
                    category="broadcast_qc_pse_violation",
                    message=f"ITU-R BT.1702 PSE flash-safety failure: peak flash frequency {max_flash_hz:.2f} Hz exceeds 3.0 Hz safety ceiling.",
                    suggested_fix="Reduce strobe/luminance flicker below 3.0 Hz and rerun broadcast QC.",
                ))
            elif overall_verdict.upper() == "FAIL" or loud_verdict.upper() == "FAIL":
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="broadcast_qc_loudness_violation",
                    message=f"Broadcast QC non-compliant (overall={overall_verdict}, loudness={loud_verdict}).",
                    suggested_fix="Adjust integrated LUFS / true-peak ceiling to match ATSC A/85 or EBU R128.",
                ))
            else:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="broadcast_qc_schema_compliance",
                    message=f"Broadcast Technical QC verified: verdict={overall_verdict}, PSE={pse_verdict} ({max_flash_hz:.2f} Hz <= 3.0 Hz), loudness={loud_verdict}.",
                    details={"overall_verdict": overall_verdict, "pse_verdict": pse_verdict, "loudness_verdict": loud_verdict, "max_flash_hz": max_flash_hz},
                ))

        # Check Inter-Scene Editorial Continuity & 180-Degree Axis Blocking (PM-FEAT-023)
        inter_scene_checks = audit_bible_inter_scene_continuity(bible)
        inter_scene_violations = [
            v
            for chk in inter_scene_checks
            for v in (getattr(chk, "violations", None) or [])
        ]
        failed_cuts = [
            chk
            for chk in inter_scene_checks
            if not getattr(chk, "passed", True) or not getattr(chk, "axis_preserved", True)
        ]
        blocking_spec = getattr(bible, "master_continuity_blocking", None)
        if blocking_spec is not None:
            cont_passed = bool(getattr(blocking_spec, "continuity_passed", True))
            all_180 = bool(getattr(blocking_spec, "all_180_axis_locked", True))
            spec_cuts = getattr(blocking_spec, "cut_checks", []) or []
            spec_viol_count = int(
                getattr(
                    blocking_spec,
                    "axis_violations_count",
                    sum(len(getattr(c, "violations", []) or []) for c in spec_cuts),
                )
                or 0
            )
            spec_failed_cuts = [
                c
                for c in spec_cuts
                if not getattr(c, "passed", True) or not getattr(c, "axis_preserved", True) or bool(getattr(c, "violations", None))
            ]
        else:
            cont_passed = True
            all_180 = True
            spec_viol_count = 0
            spec_failed_cuts = []

        if inter_scene_violations or failed_cuts or not cont_passed or not all_180 or spec_viol_count > 0 or spec_failed_cuts:
            total_axis_issues = max(len(inter_scene_violations), len(failed_cuts), spec_viol_count, len(spec_failed_cuts), 1)
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.HIGH,
                category="continuity_axis_violation",
                message=(
                    f"Inter-scene continuity / 180-degree axis violation detected "
                    f"(continuity_passed={cont_passed}, axis_violations_count={max(spec_viol_count, len(inter_scene_violations))}, "
                    f"failed_cuts={max(len(failed_cuts), len(spec_failed_cuts))})."
                ),
                suggested_fix="Preserve 180-degree line-of-action side, >=30-degree camera angle delta, and <=1500K Kelvin continuity across cuts.",
                details={"axis_violations_count": total_axis_issues, "violations": inter_scene_violations[:5]},
            ))
            penalty_points += 3.0
        elif blocking_spec is not None or inter_scene_checks:
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.INFO,
                category="continuity_blocking_schema_compliance",
                message=(
                    f"Inter-scene editorial continuity verified across {len(inter_scene_checks)} cut(s): "
                    f"continuity_passed={cont_passed}, axis_violations_count=0."
                ),
                details={"cut_checks_count": len(inter_scene_checks), "continuity_passed": cont_passed, "axis_violations_count": 0},
            ))

        # Check Client Review & Live-Render Sign-Off Gate (PM-FEAT-024)
        review_spec = getattr(bible, "master_client_review", None)
        if review_spec is not None:
            raw_unresolved = int(getattr(review_spec, "unresolved_blockers", getattr(review_spec, "blocking_notes_count", 0)) or 0)
            raw_blocking_cnt = int(getattr(review_spec, "blocking_notes_count", 0) or 0)
            computed_blockers = sum(
                1
                for sr in (getattr(review_spec, "scene_reviews", []) or [])
                for ann in (getattr(sr, "annotations", []) or [])
                if not getattr(ann, "resolved", True) and getattr(ann, "blocking_gate", False)
            )
            unresolved_blockers = max(raw_unresolved, raw_blocking_cnt, computed_blockers)
            ready_for_render = bool(getattr(review_spec, "ready_for_live_render", True))
            overall_rev_st = str(
                getattr(getattr(review_spec, "overall_status", "approved"), "value", getattr(review_spec, "overall_status", "approved"))
            ).lower()
            if unresolved_blockers > 0 or not ready_for_render or overall_rev_st == "changes_requested":
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="client_review_gate_blocked",
                    message=(
                        f"Client review live-render gate blocked: unresolved_blockers={unresolved_blockers}, "
                        f"ready_for_live_render={ready_for_render}, overall_status={overall_rev_st}."
                    ),
                    suggested_fix="Resolve all blocking client review annotations and approve scenes before live render.",
                    details={"unresolved_blockers": unresolved_blockers, "ready_for_live_render": ready_for_render},
                ))
                penalty_points += 3.0
            else:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="client_review_schema_compliance",
                    message=(
                        f"Client review sign-off gate verified: unresolved_blockers=0, "
                        f"ready_for_live_render=True, status={overall_rev_st}."
                    ),
                    details={"unresolved_blockers": 0, "ready_for_live_render": True, "overall_status": overall_rev_st},
                ))

        # Check C2PA Content Credentials v2.1 & Talent Likeness Provenance (PM-FEAT-025)
        c2pa_master = getattr(bible, "master_c2pa_provenance", None)
        if c2pa_master is not None:
            c2pa_models: List[str] = [
                getattr(act, "model_used", "")
                for act in (getattr(c2pa_master, "actions", None) or [])
                if getattr(act, "model_used", None)
            ] + [
                getattr(ing, "generative_model", "")
                for ing in (getattr(c2pa_master, "ingredients", None) or [])
                if getattr(ing, "generative_model", None)
            ]
            for sp in (getattr(c2pa_master, "scene_provenances", None) or []):
                c2pa_models.extend(
                    getattr(act, "model_used", "")
                    for act in (getattr(sp, "actions", None) or [])
                    if getattr(act, "model_used", None)
                )
                c2pa_models.extend(
                    getattr(ing, "generative_model", "")
                    for ing in (getattr(sp, "ingredients", None) or [])
                    if getattr(ing, "generative_model", None)
                )
            lineage_ok, offending_c2pa = verify_model_lineage_2026(c2pa_models) if c2pa_models else (True, [])
            consents_ok = bool(getattr(c2pa_master, "all_likeness_consents_verified", True))
            eu_art50_ok = bool(getattr(c2pa_master, "eu_ai_act_art50_compliant", True))
            if not lineage_ok:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.CRITICAL,
                    category="c2pa_model_lineage_violation",
                    message=f"Unapproved or legacy model reference(s) {offending_c2pa} detected in master_c2pa_provenance actions/ingredients.",
                    suggested_fix="Replace legacy models with approved 2026 Gemini Model Matrix identifiers in C2PA provenance.",
                ))
            elif not consents_ok or not eu_art50_ok:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="c2pa_provenance_compliance_violation",
                    message=(
                        f"C2PA provenance compliance gate failed: eu_ai_act_art50_compliant={eu_art50_ok}, "
                        f"all_likeness_consents_verified={consents_ok}."
                    ),
                    suggested_fix="Verify EU AI Act Art. 50 disclosure and all talent likeness consents in master_c2pa_provenance.",
                ))
                penalty_points += 3.0
            else:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="c2pa_provenance_schema_compliance",
                    message=(
                        f"C2PA v2.1 provenance verified: EU AI Act Art. 50 compliant, "
                        f"all_likeness_consents_verified=True, zero legacy models across "
                        f"{len(getattr(c2pa_master, 'scene_provenances', []) or [])} scene(s)."
                    ),
                    details={"scene_provenances_count": len(getattr(c2pa_master, "scene_provenances", []) or [])},
                ))

        # Check On-Set Safety Risk & JSA Gate (PM-FEAT-026)
        safety_master = getattr(bible, "master_safety_risk", None)
        if safety_master is not None:
            open_holds = int(getattr(safety_master, "open_holds_count", 0) or 0)
            safety_status = str(
                getattr(getattr(safety_master, "signoff_status", "cleared"), "value", getattr(safety_master, "signoff_status", "cleared"))
            ).lower()
            crit_residual = any(
                (
                    getattr(getattr(h, "residual_risk_level", None), "value", getattr(h, "residual_risk_level", ""))
                    or ""
                ).lower() == "critical"
                for ss in (getattr(safety_master, "scene_safety_specs", None) or [])
                for h in (getattr(ss, "hazards", None) or [])
            )
            if open_holds > 0 or safety_status == "hold_required" or crit_residual:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="safety_risk_hold_violation",
                    message=(
                        f"On-set Safety JSA gate blocked: open_holds_count={open_holds}, "
                        f"signoff_status={safety_status}, critical_residual={crit_residual}."
                    ),
                    suggested_fix="Mitigate all stage/rig hazards and clear open safety holds in master_safety_risk.",
                ))
                penalty_points += 3.0
            else:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="safety_risk_schema_compliance",
                    message=(
                        f"On-set Safety JSA verified: open_holds_count=0, signoff_status={safety_status}, "
                        f"{getattr(safety_master, 'total_hazards_identified', 0)} hazard(s) mitigated."
                    ),
                    details={"total_hazards": getattr(safety_master, "total_hazards_identified", 0)},
                ))

        # Check Multi-Territory Localization, ADR Dubbing & Safe-Supers (PM-FEAT-027)
        loc_manifest = getattr(bible, "localization_manifest", None)
        if loc_manifest is not None:
            target_locales = getattr(loc_manifest, "target_locales", None) or []
            territories = getattr(loc_manifest, "territories", None) or []
            max_drift = float(getattr(loc_manifest, "max_allowed_drift_ratio", 1.15) or 1.15)
            broadcast_ready = bool(getattr(loc_manifest, "broadcast_ready", True))
            rescript_locales = []
            overflow_locales = []
            for terr in territories:
                tag = getattr(terr, "bcp47_tag", getattr(terr, "locale", ""))
                s_st = str(getattr(getattr(terr, "supers_status", "clear"), "value", getattr(terr, "supers_status", "clear"))).lower()
                if s_st == "safe_zone_overflow":
                    overflow_locales.append(tag)
                for ln in (getattr(terr, "lines", None) or []):
                    ln_st = str(getattr(getattr(ln, "sync_status", "locked"), "value", getattr(ln, "sync_status", "locked"))).lower()
                    ratio = float(getattr(ln, "lip_sync_ratio", 1.0) or 1.0)
                    if ln_st == "rescript_required" or ratio > max_drift:
                        if tag not in rescript_locales:
                            rescript_locales.append(tag)
            if not target_locales or not territories:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="localization_schema_defect",
                    message="LocalizationManifestSpec has empty target_locales or territories.",
                    suggested_fix="Hydrate localization_manifest via compile_localization_manifest(bible).",
                ))
                penalty_points += 3.0
            elif not broadcast_ready or rescript_locales or overflow_locales:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="localization_adr_compliance_violation",
                    message=(
                        f"Localization ADR gate failed: broadcast_ready={broadcast_ready}, "
                        f"rescript_locales={rescript_locales}, supers_overflow={overflow_locales}."
                    ),
                    suggested_fix="Retime/rescript flagged ADR dialogue lines within drift ceiling and tighten supers within safe-zone.",
                ))
                penalty_points += 3.0
            else:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="localization_adr_schema_compliance",
                    message=(
                        f"Localization & ADR Dubbing verified: {len(territories)} territory track(s) "
                        f"({', '.join(target_locales[:4])}), profile={getattr(loc_manifest, 'imsc1_profile', 'imsc1-text-1.1')}, broadcast_ready=True."
                    ),
                    details={"target_locales": list(target_locales), "territories_count": len(territories)},
                ))

        # Per-scene locale_tracks compliance check (PM-FEAT-027)
        max_loc_drift = float(getattr(loc_manifest, "max_allowed_drift_ratio", 1.15) or 1.15) if loc_manifest is not None else 1.15
        bad_locale_scenes: List[int] = []
        for sc in bible.scenes:
            for tr in (getattr(sc, "locale_tracks", None) or []):
                st = str(getattr(getattr(tr, "sync_status", "locked"), "value", getattr(tr, "sync_status", "locked"))).lower()
                ratio = float(getattr(tr, "lip_sync_ratio", 1.0) or 1.0)
                if st == "rescript_required" or ratio > max_loc_drift:
                    if sc.scene_index not in bad_locale_scenes:
                        bad_locale_scenes.append(sc.scene_index)
        if bad_locale_scenes:
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.HIGH,
                category="scene_locale_tracks_violation",
                message=f"Scene locale_tracks exceed lip-sync drift ceiling or require rescript on scene(s): {bad_locale_scenes}.",
                suggested_fix="Shorten adapted ADR lines or retime visemes within max_allowed_drift_ratio.",
            ))
            penalty_points += 2.0

        # Check Editorial J-Cut / L-Cut Audio Bridge & BPM Beat-Grid Spotting (PM-FEAT-028)
        spot_manifest = getattr(bible, "spotting_manifest", None)
        fpb_val = float(getattr(spot_manifest, "frames_per_beat", 12.0) or 12.0) if spot_manifest is not None else 12.0
        bridge_unlock_ceiling = max(4, int(round(fpb_val * 0.5)))
        unlocked_bridges: List[str] = []
        if spot_manifest is not None:
            tempo_bpm = float(getattr(spot_manifest, "tempo_bpm", 0.0) or 0.0)
            beat_grid_tc = getattr(spot_manifest, "beat_grid_tc", None) or []
            beat_score = float(getattr(spot_manifest, "beat_alignment_score", 0.0) or 0.0)
            bridges = getattr(spot_manifest, "bridges", None) or []
            unlocked_bridges = [
                f"{getattr(br, 'from_scene', '?')}->{getattr(br, 'to_scene', '?')}"
                for br in bridges
                if not getattr(br, "beat_locked", True) and abs(int(getattr(br, "beat_offset_frames", 0) or 0)) > bridge_unlock_ceiling
            ]
            if tempo_bpm <= 0.0 or not beat_grid_tc:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="spotting_schema_defect",
                    message=f"SpottingManifestSpec has invalid tempo_bpm={tempo_bpm} or empty beat_grid_tc.",
                    suggested_fix="Hydrate spotting_manifest via build_spotting_manifest(bible, fps=24).",
                ))
                penalty_points += 3.0
            elif beat_score < 60.0 or unlocked_bridges:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="spotting_beat_sync_violation",
                    message=(
                        f"Editorial spotting beat-sync defect: beat_alignment_score={beat_score:.1f}%, "
                        f"unlocked_bridges={unlocked_bridges}."
                    ),
                    suggested_fix="Snap J-Cut/L-Cut split-edit bridges to nearest BPM downbeat within frame tolerance.",
                ))
                penalty_points += 3.0
            else:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="spotting_sync_schema_compliance",
                    message=(
                        f"Editorial Spotting & Beat-Grid verified: {tempo_bpm:.1f} BPM, "
                        f"{len(bridges)} split-edit bridge(s), beat_alignment_score={beat_score:.1f}%."
                    ),
                    details={"tempo_bpm": tempo_bpm, "bridges_count": len(bridges), "beat_alignment_score": beat_score},
                ))

        # Per-scene edit_bridge_in compliance check (PM-FEAT-028)
        bad_bridge_scenes: List[int] = []
        for sc in bible.scenes:
            br = getattr(sc, "edit_bridge_in", None)
            if br is not None:
                if not getattr(br, "beat_locked", True) and abs(int(getattr(br, "beat_offset_frames", 0) or 0)) > bridge_unlock_ceiling:
                    bad_bridge_scenes.append(sc.scene_index)
        if bad_bridge_scenes:
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.HIGH,
                category="scene_edit_bridge_violation",
                message=f"Scene edit_bridge_in unlocked from BPM beat grid (>{bridge_unlock_ceiling}f offset) on scene(s): {bad_bridge_scenes}.",
                suggested_fix="Re-lock J-Cut/L-Cut audio bridge to nearest beat in build_spotting_manifest().",
            ))
            penalty_points += 2.0

        # Verify PM-FEAT-029 (Stereoscopic 3D) constraints on all scenes
        s3d_spec = getattr(bible, "master_s3d_spec", None)
        if s3d_spec is not None:
            if not getattr(s3d_spec, "comfort_audit_passed", True):
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="s3d_comfort_audit_failed",
                    message="MasterS3DSpec failed comfort audit.",
                    suggested_fix="Re-evaluate convergence distance and interaxial baselines.",
                ))
                penalty_points += 2.0
            
            s3d_violation_scenes = []
            s3d_strip_failed_scenes = []
            for sc in bible.scenes:
                sc_s3d = getattr(sc, "s3d_spec", None)
                if sc_s3d and float(getattr(sc_s3d, "max_positive_parallax_pct", 0.0) or 0.0) >= 3.0:
                    s3d_violation_scenes.append(sc.scene_index)
                prompt = getattr(sc, "omni_prose_prompt", "")
                if prompt and "[S3D-RIG:" in prompt:
                    clean_prompt = compile_clean_omni_prompt(prompt)
                    if "[S3D-RIG:" in clean_prompt:
                        s3d_strip_failed_scenes.append(sc.scene_index)
                        
            if s3d_violation_scenes:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="s3d_parallax_violation",
                    message=f"Scene(s) {s3d_violation_scenes} exceeded 3.0% max_positive_parallax_pct budget.",
                    suggested_fix="Reduce subject distance or adjust convergence pull target.",
                ))
                penalty_points += 2.0
            if s3d_strip_failed_scenes:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="s3d_prompt_strip_failed",
                    message=f"Scene(s) {s3d_strip_failed_scenes} failed to cleanly strip [S3D-RIG: ...] tokens in compile_clean_omni_prompt.",
                    suggested_fix="Ensure S3D-RIG tokens follow the standard format.",
                ))
                penalty_points += 2.0

        # Verify PM-FEAT-030 (Accessibility AD) constraints on all scenes
        ad_spec = getattr(bible, "master_accessibility_spec", None)
        if ad_spec is not None:
            if not getattr(ad_spec, "all_scenes_cvaa_compliant", True):
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="accessibility_ad_cvaa_failed",
                    message="MasterAccessibilitySpec failed CVAA compliance.",
                    suggested_fix="Ensure AD track fits within available dialogue gaps.",
                ))
                penalty_points += 2.0
            
            ad_collision_scenes = []
            ad_strip_failed_scenes = []
            for sc in bible.scenes:
                sc_ad = getattr(sc, "accessibility_spec", None)
                if sc_ad and bool(getattr(sc_ad, "dialogue_collision_detected", False)):
                    ad_collision_scenes.append(sc.scene_index)
                prompt = getattr(sc, "omni_prose_prompt", "")
                if prompt and "[AD-CUE:" in prompt:
                    clean_prompt = compile_clean_omni_prompt(prompt)
                    if "[AD-CUE:" in clean_prompt:
                        ad_strip_failed_scenes.append(sc.scene_index)

            if ad_collision_scenes:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="accessibility_scene_ad_collision",
                    message=f"Scene(s) {ad_collision_scenes} detected AD dialogue collision (dialogue_collision_detected=True).",
                    suggested_fix="Shift Audio Description cue into an open dialogue gap so dialogue_collision_detected=False.",
                ))
                penalty_points += 2.0

            if int(getattr(ad_spec, "collision_count", 0) or 0) > 0:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="accessibility_ad_collision",
                    message=f"MasterAccessibilitySpec has {getattr(ad_spec, 'collision_count', 0)} AD dialogue collisions.",
                    suggested_fix="Ensure zero dialogue overlap.",
                ))
                penalty_points += 2.0
                
            if ad_strip_failed_scenes:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="accessibility_ad_prompt_strip_failed",
                    message=f"Scene(s) {ad_strip_failed_scenes} failed to cleanly strip [AD-CUE: ...] tokens in compile_clean_omni_prompt.",
                    suggested_fix="Ensure AD-CUE tokens follow the standard format.",
                ))
                penalty_points += 2.0

        # Verify PM-FEAT-031 (Wardrobe, Prop & Art Continuity) and <image_1..3> slot budget
        wp_bible = getattr(bible, "master_wardrobe_prop_bible", None)
        slot_budget_violations: List[int] = []
        slot_contention_scenes: List[int] = []
        art_strip_failed_scenes: List[int] = []
        for sc in bible.scenes:
            sc_art = getattr(sc, "art_continuity_spec", None)
            if sc_art is not None:
                assigned_slots = list(getattr(sc_art, "assigned_reference_slots", None) or [])
                if len(assigned_slots) > 3:
                    slot_budget_violations.append(sc.scene_index)
                if bool(getattr(sc_art, "slot_contention_detected", False)):
                    slot_contention_scenes.append(sc.scene_index)
            prompt = getattr(sc, "omni_prose_prompt", "")
            if prompt and ("[WARDROBE-LOCK:" in prompt or "[PROP-STATE:" in prompt):
                clean_prompt = compile_clean_omni_prompt(prompt)
                if "[WARDROBE-LOCK:" in clean_prompt or "[PROP-STATE:" in clean_prompt:
                    art_strip_failed_scenes.append(sc.scene_index)
        if slot_budget_violations:
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.HIGH,
                category="art_reference_slot_budget_exceeded",
                message=f"Scene(s) {slot_budget_violations} exceeded the 3-slot <image_1..3> ceiling in assigned_reference_slots.",
                suggested_fix="Prioritize wardrobe, env, and prop plates to at most 3 <image_1..3> slots via validate_reference_slot_budget().",
            ))
            penalty_points += 3.0
        if slot_contention_scenes:
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.HIGH,
                category="art_reference_slot_contention",
                message=f"Scene(s) {slot_contention_scenes} flagged slot_contention_detected=True (>3 plates).",
                suggested_fix="Consolidate reference plates to <= 3 total <image_1..3> slots.",
            ))
            penalty_points += 2.0
        if art_strip_failed_scenes:
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.HIGH,
                category="art_continuity_prompt_strip_failed",
                message=f"Scene(s) {art_strip_failed_scenes} failed to cleanly strip [WARDROBE-LOCK:]/[PROP-STATE:] tokens in compile_clean_omni_prompt.",
                suggested_fix="Ensure art continuity tokens match standard bracket syntax.",
            ))
            penalty_points += 2.0
        if wp_bible is not None and not slot_budget_violations and not slot_contention_scenes and not art_strip_failed_scenes:
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.INFO,
                category="art_continuity_schema_compliance",
                message=(
                    f"Wardrobe/Prop Continuity & <image_1..3> slot budget verified across {len(bible.scenes)} scene(s) "
                    f"(continuity_breaks={getattr(wp_bible, 'continuity_breaks_detected', 0)})."
                ),
            ))

        # Verify PM-FEAT-032 (Render Economics & Compute Take Budget) constraints on all scenes
        econ_spec = getattr(bible, "master_render_economics_spec", None)
        econ_strip_failed_scenes: List[int] = []
        invalid_take_scenes: List[int] = []
        for sc in bible.scenes:
            sc_econ = getattr(sc, "compute_estimate_spec", None)
            if sc_econ is not None and int(getattr(sc_econ, "planned_takes", 1) or 0) < 1:
                invalid_take_scenes.append(sc.scene_index)
            prompt = getattr(sc, "omni_prose_prompt", "")
            if prompt and "[RENDER-PROFILE:" in prompt:
                clean_prompt = compile_clean_omni_prompt(prompt)
                if "[RENDER-PROFILE:" in clean_prompt:
                    econ_strip_failed_scenes.append(sc.scene_index)
        if invalid_take_scenes:
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.HIGH,
                category="render_economics_invalid_takes",
                message=f"Scene(s) {invalid_take_scenes} specify planned_takes < 1 in compute_estimate_spec.",
                suggested_fix="Set planned_takes >= 1 via estimate_scene_compute_cost().",
            ))
            penalty_points += 2.0
        if econ_strip_failed_scenes:
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.HIGH,
                category="render_economics_prompt_strip_failed",
                message=f"Scene(s) {econ_strip_failed_scenes} failed to cleanly strip [RENDER-PROFILE: ...] tokens in compile_clean_omni_prompt.",
                suggested_fix="Ensure RENDER-PROFILE tokens follow the standard bracket format.",
            ))
            penalty_points += 2.0
        if econ_spec is not None:
            guardrail = getattr(econ_spec, "guardrail", None)
            if guardrail is not None and not bool(getattr(guardrail, "within_budget", True)):
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="render_economics_budget_exceeded",
                    message=(
                        f"MasterRenderEconomicsManifest guardrail exceeded: "
                        f"${getattr(guardrail, 'estimated_total_usd', 0.0):.2f} > "
                        f"${getattr(guardrail, 'max_render_budget_usd', 0.0):.2f}."
                    ),
                    suggested_fix="Reduce planned_takes or raise max_render_budget_usd within domain policy.",
                ))
                penalty_points += 2.0
            elif not invalid_take_scenes and not econ_strip_failed_scenes:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="render_economics_schema_compliance",
                    message=(
                        f"Render Economics Guardrail verified across {len(bible.scenes)} scene(s) "
                        f"(within_budget=True, total_takes={getattr(econ_spec, 'total_planned_takes', 0)})."
                    ),
                ))

        # Verify PM-FEAT-033 (Motion Graphics) & PM-FEAT-034 (OTIO Coherence) + token stripping
        gfx_spec = getattr(bible, "master_motion_graphics", None)
        gfx_otio_strip_failed: List[int] = []
        for sc in bible.scenes:
            prompt = getattr(sc, "omni_prose_prompt", "")
            if prompt and any(tok in prompt for tok in ("[GFX-CLEANPLATE:", "[GFX-SUPER:", "[OTIO-SYNC:")):
                clean_prompt = compile_clean_omni_prompt(prompt)
                if any(tok in clean_prompt for tok in ("[GFX-CLEANPLATE:", "[GFX-SUPER:", "[OTIO-SYNC:")):
                    gfx_otio_strip_failed.append(sc.scene_index)
        if gfx_otio_strip_failed:
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.HIGH,
                category="gfx_otio_prompt_strip_failed",
                message=(
                    f"Scene(s) {gfx_otio_strip_failed} failed to cleanly strip "
                    "[GFX-CLEANPLATE:]/[GFX-SUPER:]/[OTIO-SYNC:] tokens in compile_clean_omni_prompt."
                ),
                suggested_fix="Ensure GFX and OTIO telemetry tokens match standard bracket syntax in _MACHINE_TELEMETRY_TOKEN_RE.",
            ))
            penalty_points += 2.0

        if gfx_spec is not None:
            max_wpm = float(getattr(gfx_spec, "max_wpm_detected", 0.0) or 0.0)
            safe_cleared = bool(getattr(gfx_spec, "all_safe_zones_cleared", True))
            legal_ok = bool(getattr(gfx_spec, "legal_supers_compliant", True))
            if max_wpm > 180.0:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="motion_graphics_wpm_exceeded",
                    message=f"MasterMotionGraphicsManifest max_wpm_detected={max_wpm:.2f} exceeds 180.0 WPM broadcast ceiling.",
                    suggested_fix="Shorten super copy or extend cue display_duration_sec so max_wpm_detected <= 180.0.",
                ))
                penalty_points += 2.0
            if not safe_cleared:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="motion_graphics_safe_zone_violation",
                    message="MasterMotionGraphicsManifest failed 9:16/16:9 safe-zone or >=25% cleanplate negative-space audit.",
                    suggested_fix="Clamp graphic placement into 9:16 safe envelope and preserve >=25% negative space.",
                ))
                penalty_points += 2.0
            if not legal_ok:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="motion_graphics_legal_non_compliant",
                    message="MasterMotionGraphicsManifest flagged legal_supers_compliant=False.",
                    suggested_fix="Attach compliant legal disclaimer cue via compile_motion_graphics_manifest().",
                ))
                penalty_points += 2.0
            if max_wpm <= 180.0 and safe_cleared and legal_ok and not gfx_otio_strip_failed:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="motion_graphics_schema_compliance",
                    message=(
                        f"Motion Graphics & Safe-Zone Gate verified across {len(bible.scenes)} scene(s) "
                        f"(max_wpm={max_wpm:.1f} <= 180.0, all_safe_zones_cleared=True, legal_supers_compliant=True)."
                    ),
                ))

        otio_spec = getattr(bible, "master_otio_coherence", None)
        if otio_spec is not None:
            coh_score = float(getattr(otio_spec, "coherence_score", 100.0) or 0.0)
            coh_conflicts = int(getattr(otio_spec, "conflicts_count", 0) or 0)
            if coh_score < 85.0 or coh_conflicts > 0:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="otio_coherence_gate_failed",
                    message=(
                        f"MasterOtioCoherenceManifest failed cross-department coherence gate "
                        f"(coherence_score={coh_score:.1f} < 85.0 or conflicts_count={coh_conflicts} > 0)."
                    ),
                    suggested_fix="Run reconcile_cross_department_conflicts() and compile_otio_coherence_manifest(auto_reconcile=True).",
                ))
                penalty_points += 2.0
            elif not gfx_otio_strip_failed:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="otio_coherence_schema_compliance",
                    message=(
                        f"OTIO Cross-Department Coherence Gate verified "
                        f"(coherence_score={coh_score:.1f} >= 85.0, conflicts_count=0)."
                    ),
                ))

        # Verify PM-FEAT-035 (Render Orchestrator) & PM-FEAT-036 (Pitch Treatment) token stripping & Mode B continuity
        rj_pt_strip_failed: List[int] = []
        for sc in bible.scenes:
            prompt = getattr(sc, "omni_prose_prompt", "")
            if prompt and any(tok in prompt for tok in ("[RENDER-JOB:", "[FRAME-ANCHOR:", "[TREATMENT-BEAT:")):
                clean_prompt = compile_clean_omni_prompt(prompt)
                if any(tok in clean_prompt for tok in ("[RENDER-JOB:", "[FRAME-ANCHOR:", "[TREATMENT-BEAT:")):
                    rj_pt_strip_failed.append(sc.scene_index)
        if rj_pt_strip_failed:
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.HIGH,
                category="render_treatment_prompt_strip_failed",
                message=(
                    f"Scene(s) {rj_pt_strip_failed} failed to cleanly strip "
                    "[RENDER-JOB:]/[FRAME-ANCHOR:]/[TREATMENT-BEAT:] tokens in compile_clean_omni_prompt."
                ),
                suggested_fix="Ensure PM-FEAT-035/036 telemetry tokens match _MACHINE_TELEMETRY_TOKEN_RE.",
            ))
            penalty_points += 2.0

        rj_spec = getattr(bible, "master_render_jobs", None)
        if rj_spec is not None:
            overall_qa = float(getattr(rj_spec, "overall_qa_score", 95.0) or 0.0)
            assembly_ready = bool(getattr(rj_spec, "assembly_ready", True))
            story_mode = getattr(bible, "storytelling_mode", StorytellingMode.MODE_A_PARALLEL_CUT)
            is_mode_b = story_mode == StorytellingMode.MODE_B_CONTINUOUS_CHAIN
            handoffs = list(getattr(rj_spec, "frame_anchor_handoffs", None) or [])

            if overall_qa < 85.0 or not assembly_ready:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="render_orchestrator_gate_failed",
                    message=(
                        f"MasterRenderJobManifest failed QA/assembly gate "
                        f"(overall_qa_score={overall_qa:.1f}, assembly_ready={assembly_ready})."
                    ),
                    suggested_fix="Promote passing takes or re-evaluate via compile_render_job_manifest().",
                ))
                penalty_points += 2.0
            elif is_mode_b and len(bible.scenes) > 1 and (
                len(handoffs) < len(bible.scenes) - 1
                or any(not bool(getattr(h, "continuity_locked", False)) or not getattr(h, "end_frame_asset_id", "") for h in handoffs)
            ):
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="mode_b_frame_anchor_continuity_failed",
                    message=(
                        f"Mode B production lacks locked FrameAnchorHandoffSpec continuity across "
                        f"{len(bible.scenes)} scenes (handoffs={len(handoffs)})."
                    ),
                    suggested_fix="Verify Mode B frame-anchor handoffs via verify_mode_b_frame_anchor().",
                ))
                penalty_points += 2.0
            elif not rj_pt_strip_failed:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="render_orchestrator_schema_compliance",
                    message=(
                        f"Render Orchestrator & Mode B Frame-Anchor Continuity verified "
                        f"(overall_qa_score={overall_qa:.1f}, assembly_ready={assembly_ready}, handoffs={len(handoffs)})."
                    ),
                ))

        pt_spec = getattr(bible, "master_pitch_treatment", None)
        if pt_spec is not None:
            pt_slides = list(getattr(pt_spec, "slides", None) or [])
            if not pt_slides:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="pitch_treatment_schema_failed",
                    message="MasterPitchTreatmentSpec contains zero treatment slides.",
                    suggested_fix="Compile pitch treatment via compile_pitch_treatment().",
                ))
                penalty_points += 2.0
            elif not rj_pt_strip_failed:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="pitch_treatment_schema_compliance",
                    message=f"MasterPitchTreatmentSpec contract verified ({len(pt_slides)} board slides, token present={bool(getattr(pt_spec, 'treatment_token', ''))}).",
                ))

        # Verify PM-FEAT-037 (SMPTE IMF & DCI DCP) & PM-FEAT-038 (Voice Casting & Ducking) token stripping & contracts
        v219_strip_failed: List[int] = []
        v219_tokens = ("[MODE B CONTINUITY:", "[RENDER-ORCHESTRATOR:", "[IMF-CPL:", "[VOICE-CAST:")
        for sc in bible.scenes:
            prompt = getattr(sc, "omni_prose_prompt", "")
            if prompt and any(tok in prompt for tok in v219_tokens):
                clean_prompt = compile_clean_omni_prompt(prompt)
                if any(tok in clean_prompt for tok in v219_tokens):
                    v219_strip_failed.append(sc.scene_index)
        if v219_strip_failed:
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.HIGH,
                category="imf_voice_prompt_strip_failed",
                message=(
                    f"Scene(s) {v219_strip_failed} failed to cleanly strip "
                    "[MODE B CONTINUITY:]/[RENDER-ORCHESTRATOR:]/[IMF-CPL:]/[VOICE-CAST:] tokens in compile_clean_omni_prompt."
                ),
                suggested_fix="Ensure v2.19 telemetry tokens match _MACHINE_TELEMETRY_TOKEN_RE.",
            ))
            penalty_points += 2.0

        imf_spec = getattr(bible, "master_imf_dcp", None)
        if imf_spec is not None:
            dcp_spec = getattr(imf_spec, "dcp_spec", None)
            max_bitrate = float(getattr(dcp_spec, "jpeg2000_max_bitrate_mbps", 250.0) or 0.0) if dcp_spec else 0.0
            asset_uuids = {
                str(getattr(a, "asset_uuid", "") or "").strip()
                for a in (getattr(imf_spec, "assets", None) or [])
                if str(getattr(a, "asset_uuid", "") or "").strip()
            }
            cpls = list(getattr(imf_spec, "cpls", None) or [])
            broken_cpl_refs: List[str] = []
            for cpl in cpls:
                links = list(getattr(cpl, "linked_asset_uuids", None) or [])
                if not links or any(u not in asset_uuids for u in links):
                    broken_cpl_refs.append(str(getattr(cpl, "version_tag", "CPL") or "CPL"))
            if max_bitrate <= 0.0 or max_bitrate > 250.0 or not asset_uuids or broken_cpl_refs:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="imf_dcp_compliance_failed",
                    message=(
                        f"MasterImfDcpManifest failed SMPTE/DCI gate "
                        f"(jpeg2000_max_bitrate_mbps={max_bitrate:.1f}, broken_cpls={broken_cpl_refs})."
                    ),
                    suggested_fix="Cap DCI JPEG2000 bitrate <= 250.0 Mbps and link valid OV/supplemental asset UUIDs.",
                ))
                penalty_points += 2.0
            elif not v219_strip_failed:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="imf_dcp_schema_compliance",
                    message=(
                        f"SMPTE IMF & DCI DCP contract verified (bitrate={max_bitrate:.1f} Mbps <= 250.0 Mbps, "
                        f"assets={len(asset_uuids)}, cpls={len(cpls)})."
                    ),
                ))

        vd_spec = getattr(bible, "master_voice_ducking", None)
        if vd_spec is not None:
            pass_rate = float(getattr(vd_spec, "lip_sync_pass_rate_pct", 0.0) or 0.0)
            snr_min = float(getattr(vd_spec, "dialogue_clarity_snr_min_db", 0.0) or 0.0)
            over_wps = [
                (int(getattr(sp, "scene_index", 0) or 0), float(getattr(cue, "wps", 0.0) or 0.0))
                for sp in (getattr(vd_spec, "scene_profiles", None) or [])
                for cue in (getattr(sp, "viseme_cues", None) or [])
                if float(getattr(cue, "wps", 0.0) or 0.0) > 2.5
            ]
            low_snr_scenes = [
                int(getattr(sp, "scene_index", 0) or 0)
                for sp in (getattr(vd_spec, "scene_profiles", None) or [])
                if float(getattr(sp, "dialogue_to_bgm_snr_db", 0.0) or 0.0) < 6.0
            ]
            if pass_rate < 90.0 or snr_min < 6.0 or over_wps or low_snr_scenes:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="voice_ducking_compliance_failed",
                    message=(
                        f"MasterVoiceDuckingManifest failed lip-sync/ducking gate "
                        f"(lip_sync_pass_rate_pct={pass_rate:.1f}%, snr_min={snr_min:.1f}dB, "
                        f"over_wps={over_wps[:3]}, low_snr_scenes={low_snr_scenes})."
                    ),
                    suggested_fix="Keep spoken dialogue <= 2.5 WPS, lip_sync_pass_rate_pct >= 90%, and SNR >= 6.0 dB.",
                ))
                penalty_points += 2.0
            elif not v219_strip_failed:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="voice_ducking_schema_compliance",
                    message=(
                        f"Voice Casting & Sidechain Ducking contract verified "
                        f"(lip_sync_pass_rate={pass_rate:.1f}% >= 90%, snr_min={snr_min:.1f} dB >= 6.0 dB, WPS <= 2.5)."
                    ),
                ))

        # Verify PM-FEAT-039 (Colorist Scopes) & PM-FEAT-040 (Archive Vault) token stripping & contracts
        v220_strip_failed: List[int] = []
        v220_tokens = ("[COLOR-SCOPES:", "[ARCHIVE-VAULT:")
        for sc in bible.scenes:
            prompt = getattr(sc, "omni_prose_prompt", "")
            if prompt and any(tok in prompt for tok in v220_tokens):
                clean_prompt = compile_clean_omni_prompt(prompt)
                if any(tok in clean_prompt for tok in v220_tokens):
                    v220_strip_failed.append(sc.scene_index)
        if v220_strip_failed:
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.HIGH,
                category="color_scopes_vault_prompt_strip_failed",
                message=(
                    f"Scene(s) {v220_strip_failed} failed to cleanly strip "
                    "[COLOR-SCOPES:]/[ARCHIVE-VAULT:] tokens in compile_clean_omni_prompt."
                ),
                suggested_fix="Ensure v2.20 telemetry tokens match _MACHINE_TELEMETRY_TOKEN_RE.",
            ))
            penalty_points += 2.0

        cs_spec = getattr(bible, "master_color_scopes", None)
        if cs_spec is not None:
            de_ceil = float(getattr(cs_spec, "max_delta_e_ceiling", 3.0) or 3.0)
            ev_ceil = float(getattr(cs_spec, "max_exposure_jump_stops", 0.75) or 0.75)
            oog_scenes = [
                int(getattr(sc, "scene_index", 0) or 0)
                for sc in (getattr(cs_spec, "scene_scopes", None) or [])
                if float(getattr(sc, "gamut_utilization_pct", 0.0) or 0.0) > 100.0
            ]
            bad_cuts = [
                f"SC{getattr(cm, 'from_scene_index', 0)}->SC{getattr(cm, 'to_scene_index', 0)}"
                for cm in (getattr(cs_spec, "cut_matches", None) or [])
                if str(getattr(getattr(cm, "match_status", None), "value", getattr(cm, "match_status", ""))) == "out_of_gamut"
            ]
            if de_ceil <= 0.0 or ev_ceil <= 0.0 or oog_scenes or bad_cuts:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="color_scopes_compliance_failed",
                    message=(
                        f"MasterColorScopesManifest failed gamut/continuity gate "
                        f"(oog_scenes={oog_scenes}, out_of_gamut_cuts={bad_cuts})."
                    ),
                    suggested_fix="Keep scene gamut utilization <= 100% and match adjacent cuts within CIEDE2000 & EV tolerances.",
                ))
                penalty_points += 2.0
            elif not v220_strip_failed:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="color_scopes_schema_compliance",
                    message=(
                        f"Colorist Scopes contract verified (dE2000 ceiling={de_ceil:.2f}, "
                        f"EV jump ceiling={ev_ceil:.2f} stops, mean_dE2000={float(getattr(cs_spec, 'mean_delta_e_2000', 0.0) or 0.0):.2f})."
                    ),
                ))

        av_spec = getattr(bible, "master_archive_vault", None)
        if av_spec is not None:
            av_ready = bool(getattr(av_spec, "archive_ready", False))
            av_missing = int(getattr(av_spec, "missing_artifacts", 0) or 0)
            av_total = int(getattr(av_spec, "total_artifacts", 0) or 0)
            av_entries = list(getattr(av_spec, "entries", None) or [])
            if not av_ready or av_missing > 0 or av_total < len(av_entries) or not av_entries:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="archive_vault_compliance_failed",
                    message=(
                        f"MasterArchiveVaultManifest failed integrity gate "
                        f"(archive_ready={av_ready}, missing={av_missing}, total={av_total}, entries={len(av_entries)})."
                    ),
                    suggested_fix="Ensure RFC 8493 BagIt manifest has zero missing mandatory artifacts and valid SHA-256 checksums.",
                ))
                penalty_points += 2.0
            elif not v220_strip_failed:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="archive_vault_schema_compliance",
                    message=(
                        f"RFC 8493 Archive Vault contract verified (bag={getattr(av_spec, 'bag_id', '')}, "
                        f"oxum={getattr(av_spec, 'payload_oxum', '')}, artifacts={av_total})."
                    ),
                ))

        # Check continuity_blocking_compliant, review_gate_compliant, c2pa_provenance_compliant, safety_risk_compliant, localization_adr_compliant, and spotting_sync_compliant on bundle.audit_reports
        if bundle is not None and getattr(bundle, "audit_reports", None):
            non_cont_scenes = [
                getattr(rep, "scene_index", idx)
                for idx, rep in enumerate(bundle.audit_reports, 1)
                if not getattr(rep, "continuity_blocking_compliant", True)
            ]
            non_rev_scenes = [
                getattr(rep, "scene_index", idx)
                for idx, rep in enumerate(bundle.audit_reports, 1)
                if not getattr(rep, "review_gate_compliant", True)
            ]
            non_c2pa_scenes = [
                getattr(rep, "scene_index", idx)
                for idx, rep in enumerate(bundle.audit_reports, 1)
                if not getattr(rep, "c2pa_provenance_compliant", True)
            ]
            non_safety_scenes = [
                getattr(rep, "scene_index", idx)
                for idx, rep in enumerate(bundle.audit_reports, 1)
                if not getattr(rep, "safety_risk_compliant", True)
            ]
            non_loc_scenes = [
                getattr(rep, "scene_index", idx)
                for idx, rep in enumerate(bundle.audit_reports, 1)
                if not getattr(rep, "localization_adr_compliant", True)
            ]
            non_spot_scenes = [
                getattr(rep, "scene_index", idx)
                for idx, rep in enumerate(bundle.audit_reports, 1)
                if not getattr(rep, "spotting_sync_compliant", True)
            ]
            non_art_scenes = [
                getattr(rep, "scene_index", idx)
                for idx, rep in enumerate(bundle.audit_reports, 1)
                if not getattr(rep, "art_continuity_compliant", True)
            ]
            non_econ_scenes = [
                getattr(rep, "scene_index", idx)
                for idx, rep in enumerate(bundle.audit_reports, 1)
                if not getattr(rep, "render_economics_compliant", True)
            ]
            non_gfx_scenes = [
                getattr(rep, "scene_index", idx)
                for idx, rep in enumerate(bundle.audit_reports, 1)
                if not getattr(rep, "motion_graphics_compliant", True)
            ]
            non_otio_scenes = [
                getattr(rep, "scene_index", idx)
                for idx, rep in enumerate(bundle.audit_reports, 1)
                if not getattr(rep, "otio_coherence_compliant", True)
            ]
            non_rj_scenes = [
                getattr(rep, "scene_index", idx)
                for idx, rep in enumerate(bundle.audit_reports, 1)
                if not getattr(rep, "render_orchestrator_compliant", True)
            ]
            non_pt_scenes = [
                getattr(rep, "scene_index", idx)
                for idx, rep in enumerate(bundle.audit_reports, 1)
                if not getattr(rep, "pitch_treatment_compliant", True)
            ]
            non_imf_scenes = [
                getattr(rep, "scene_index", idx)
                for idx, rep in enumerate(bundle.audit_reports, 1)
                if not getattr(rep, "imf_dcp_compliant", True)
            ]
            non_vd_scenes = [
                getattr(rep, "scene_index", idx)
                for idx, rep in enumerate(bundle.audit_reports, 1)
                if not getattr(rep, "voice_ducking_compliant", True)
            ]
            non_cs_scenes = [
                getattr(rep, "scene_index", idx)
                for idx, rep in enumerate(bundle.audit_reports, 1)
                if not getattr(rep, "color_scopes_compliant", True)
            ]
            non_av_scenes = [
                getattr(rep, "scene_index", idx)
                for idx, rep in enumerate(bundle.audit_reports, 1)
                if not getattr(rep, "archive_vault_compliant", True)
            ]
            if non_cont_scenes:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="audit_report_continuity_non_compliant",
                    message=f"Bundle audit_reports flagged continuity_blocking_compliant=False on scene(s): {non_cont_scenes}.",
                    suggested_fix="Heal 180-degree continuity axis locks and rerun scene prompt audits.",
                ))
                penalty_points += 2.0
            if non_rev_scenes:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="audit_report_review_gate_non_compliant",
                    message=f"Bundle audit_reports flagged review_gate_compliant=False on scene(s): {non_rev_scenes}.",
                    suggested_fix="Resolve pending client review change requests on flagged scenes.",
                ))
                penalty_points += 2.0
            if non_c2pa_scenes:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="audit_report_c2pa_non_compliant",
                    message=f"Bundle audit_reports flagged c2pa_provenance_compliant=False on scene(s): {non_c2pa_scenes}.",
                    suggested_fix="Verify 2026 model lineage, EU AI Act Art. 50 disclosure, and talent likeness consent on flagged scenes.",
                ))
                penalty_points += 2.0
            if non_safety_scenes:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="audit_report_safety_non_compliant",
                    message=f"Bundle audit_reports flagged safety_risk_compliant=False on scene(s): {non_safety_scenes}.",
                    suggested_fix="Clear JSA safety holds and mitigate residual hazards on flagged scenes.",
                ))
                penalty_points += 2.0
            if non_loc_scenes:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="audit_report_localization_non_compliant",
                    message=f"Bundle audit_reports flagged localization_adr_compliant=False on scene(s): {non_loc_scenes}.",
                    suggested_fix="Retime/rescript flagged localized dialogue tracks within drift ceiling.",
                ))
                penalty_points += 2.0
            if non_spot_scenes:
                bridge_map = {
                    int(getattr(br, "to_scene", 0)): br
                    for br in (getattr(spot_manifest, "bridges", None) or [])
                } if spot_manifest is not None else {}
                scene_map = {int(sc.scene_index): sc for sc in bible.scenes}
                all_non_spot_within_half_beat = all(
                    (
                        (br := getattr(scene_map.get(sc_idx), "edit_bridge_in", None) or bridge_map.get(sc_idx)) is not None
                        and abs(int(getattr(br, "beat_offset_frames", 0) or 0)) <= bridge_unlock_ceiling
                    )
                    for sc_idx in non_spot_scenes
                )
                spot_beat_ok = (
                    spot_manifest is not None
                    and float(getattr(spot_manifest, "beat_alignment_score", 0.0) or 0.0) >= 70.0
                    and not unlocked_bridges
                    and not bad_bridge_scenes
                    and all_non_spot_within_half_beat
                )
                if spot_beat_ok:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.INFO,
                        category="audit_report_spotting_advisory",
                        message=f"Scene(s) {non_spot_scenes} within half-beat BPM tolerance (beat_alignment_score >= 70%).",
                    ))
                else:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.HIGH,
                        category="audit_report_spotting_non_compliant",
                        message=f"Bundle audit_reports flagged spotting_sync_compliant=False on scene(s): {non_spot_scenes}.",
                        suggested_fix="Lock incoming J-Cut/L-Cut audio bridge to BPM beat grid on flagged scenes.",
                    ))
                    penalty_points += 2.0
            if not non_cont_scenes and not non_rev_scenes:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="audit_report_continuity_and_review_compliance",
                    message=f"Bundle audit_reports verified continuity_blocking_compliant=True and review_gate_compliant=True across {len(bundle.audit_reports)} scene(s).",
                ))
            if not non_c2pa_scenes and not non_safety_scenes:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="audit_report_c2pa_and_safety_compliance",
                    message=f"Bundle audit_reports verified c2pa_provenance_compliant=True and safety_risk_compliant=True across {len(bundle.audit_reports)} scene(s).",
                ))
            if not non_loc_scenes and not non_spot_scenes:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="audit_report_localization_and_spotting_compliance",
                    message=f"Bundle audit_reports verified localization_adr_compliant=True and spotting_sync_compliant=True across {len(bundle.audit_reports)} scene(s).",
                ))
            if non_art_scenes:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="audit_report_art_continuity_non_compliant",
                    message=f"Bundle audit_reports flagged art_continuity_compliant=False on scene(s): {non_art_scenes}.",
                    suggested_fix="Resolve <image_1..3> slot contention and hydrate art_continuity_spec on flagged scenes.",
                ))
                penalty_points += 2.0
            if non_econ_scenes:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="audit_report_render_economics_non_compliant",
                    message=f"Bundle audit_reports flagged render_economics_compliant=False on scene(s): {non_econ_scenes}.",
                    suggested_fix="Ensure compute_estimate_spec planned_takes >= 1 and within_budget=True on flagged scenes.",
                ))
                penalty_points += 2.0
            if not non_art_scenes and not non_econ_scenes:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="audit_report_art_and_economics_compliance",
                    message=f"Bundle audit_reports verified art_continuity_compliant=True and render_economics_compliant=True across {len(bundle.audit_reports)} scene(s).",
                ))
            if non_gfx_scenes:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="audit_report_motion_graphics_non_compliant",
                    message=f"Bundle audit_reports flagged motion_graphics_compliant=False on scene(s): {non_gfx_scenes}.",
                    suggested_fix="Ensure motion graphics WPM <= 180, 9:16 safe zones, and [GFX-CLEANPLATE] compliance on flagged scenes.",
                ))
                penalty_points += 2.0
            if non_otio_scenes:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="audit_report_otio_coherence_non_compliant",
                    message=f"Bundle audit_reports flagged otio_coherence_compliant=False on scene(s): {non_otio_scenes}.",
                    suggested_fix="Ensure OTIO cross-department coherence reconciliation succeeds on flagged scenes.",
                ))
                penalty_points += 2.0
            if not non_gfx_scenes and not non_otio_scenes:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="audit_report_gfx_and_otio_compliance",
                    message=f"Bundle audit_reports verified motion_graphics_compliant=True and otio_coherence_compliant=True across {len(bundle.audit_reports)} scene(s).",
                ))
            if non_rj_scenes:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="audit_report_render_orchestrator_non_compliant",
                    message=f"Bundle audit_reports flagged render_orchestrator_compliant=False on scene(s): {non_rj_scenes}.",
                    suggested_fix="Resolve flagged render job QA or Mode B frame-anchor continuity on affected scenes.",
                ))
                penalty_points += 2.0
            if non_pt_scenes:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="audit_report_pitch_treatment_non_compliant",
                    message=f"Bundle audit_reports flagged pitch_treatment_compliant=False on scene(s): {non_pt_scenes}.",
                    suggested_fix="Hydrate scene treatment_spec and master_pitch_treatment on affected scenes.",
                ))
                penalty_points += 2.0
            if not non_rj_scenes and not non_pt_scenes:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="audit_report_render_and_treatment_compliance",
                    message=f"Bundle audit_reports verified render_orchestrator_compliant=True and pitch_treatment_compliant=True across {len(bundle.audit_reports)} scene(s).",
                ))
            if non_imf_scenes:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="audit_report_imf_dcp_non_compliant",
                    message=f"Bundle audit_reports flagged imf_dcp_compliant=False on scene(s): {non_imf_scenes}.",
                    suggested_fix="Ensure DCI JPEG2000 bitrate <= 250.0 Mbps and valid OV asset UUID links on flagged scenes.",
                ))
                penalty_points += 2.0
            if non_vd_scenes:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="audit_report_voice_ducking_non_compliant",
                    message=f"Bundle audit_reports flagged voice_ducking_compliant=False on scene(s): {non_vd_scenes}.",
                    suggested_fix="Ensure dialogue WPS <= 2.5 and sidechain ducking SNR >= 6.0 dB on flagged scenes.",
                ))
                penalty_points += 2.0
            if not non_imf_scenes and not non_vd_scenes:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="audit_report_imf_and_voice_compliance",
                    message=f"Bundle audit_reports verified imf_dcp_compliant=True and voice_ducking_compliant=True across {len(bundle.audit_reports)} scene(s).",
                ))
            if non_cs_scenes:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="audit_report_color_scopes_non_compliant",
                    message=f"Bundle audit_reports flagged color_scopes_compliant=False on scene(s): {non_cs_scenes}.",
                    suggested_fix="Keep 16-bin IRE waveforms, <=100% gamut utilization, and CIEDE2000/EV cut deltas within ceiling.",
                ))
                penalty_points += 2.0
            if non_av_scenes:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="audit_report_archive_vault_non_compliant",
                    message=f"Bundle audit_reports flagged archive_vault_compliant=False on scene(s): {non_av_scenes}.",
                    suggested_fix="Verify RFC 8493 BagIt bag_id, payload_oxum, and archive_ready=True on flagged scenes.",
                ))
                penalty_points += 2.0
            if not non_cs_scenes and not non_av_scenes:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="audit_report_scopes_and_vault_compliance",
                    message=f"Bundle audit_reports verified color_scopes_compliant=True and archive_vault_compliant=True across {len(bundle.audit_reports)} scene(s).",
                ))

        avg_audit_score = sum(audit_scores) / len(audit_scores) if audit_scores else 0.0
        score = 25.0 * (avg_audit_score / 100.0)
        critical_count = len([f for f in findings if f.severity == CouncilFindingSeverity.CRITICAL])
        score -= (critical_count * 10.0)
        score -= penalty_points
        score = max(0.0, min(25.0, round(score, 2)))

        summary = f"Agent Engineer review completed with score {score}/25.0 (Prompt Audit avg: {avg_audit_score:.1f}%)."
        return PersonaReviewResult(
            persona=CouncilPersona.COUNCIL_AGENT_ENGINEER,
            score=score,
            findings=findings,
            summary=summary,
        )

    def _review_strategist(self, bible: Optional[MasterProductionBible]) -> PersonaReviewResult:
        """Evaluates creative domain alignment, 6-archetype styling, and positive invariants."""
        findings: List[CouncilFinding] = []
        score = 25.0

        if bible is None:
            return PersonaReviewResult(
                persona=CouncilPersona.COUNCIL_STRATEGIST,
                score=0.0,
                findings=[],
                summary="Strategist review failed: bible missing."
            )

        combined_text = f"{bible.project_title} {bible.logline}"
        detected_domain = getattr(bible, "domain_archetype", None) or classify_brief_domain(combined_text)
        archetype = DOMAIN_ARCHETYPES.get(detected_domain, {})

        # Check positive invariants across scene prompts (no negative prompt constraints)
        negative_phrases = [
            "don't ", "do not ", "avoid ", "no blur", "never ", "without any ",
            "no shaking", "no camera shake", "no cuts", "without cuts", "not blurry",
            "no jitter", "without jitter", "no artifact", "without artifact",
        ]
        for scene in bible.scenes:
            prompt_str = getattr(scene, "scene_prompt", getattr(scene, "omni_prose_prompt", ""))
            prompt_lower = prompt_str.lower()
            for phrase in negative_phrases:
                if phrase in prompt_lower:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.LOW,
                        category="positive_invariants",
                        message=f"Scene {scene.scene_index} uses negative constraint '{phrase}'. Use positive direction instead.",
                        suggested_fix=f"Rephrase Scene {scene.scene_index} prompt with affirmative physical descriptions."
                    ))
                    score -= 1.0

        # Mode B Continuous Narrative Verification
        if getattr(bible, "storytelling_mode", None) == StorytellingMode.MODE_B_CONTINUOUS_CHAIN and len(bible.scenes) > 1:
            for scene in bible.scenes[1:]:
                prompt_str = getattr(scene, "scene_prompt", getattr(scene, "omni_prose_prompt", "")).lower()
                has_continuity_anchor = any(
                    kw in prompt_str
                    for kw in ("continue", "continuous", "unbroken", "maintains", "extending", "momentum", "anchor")
                )
                if not has_continuity_anchor:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.MEDIUM,
                        category="narrative_continuity",
                        message=f"Mode B scene {scene.scene_index} lacks clear temporal/camera continuity anchor.",
                        suggested_fix=f"Add continuous camera momentum or anchor marker to scene {scene.scene_index}."
                    ))
                    score -= 1.0

        # Check sonic identity presence
        bgm_desc = ""
        if hasattr(bible, "master_bgm") and bible.master_bgm:
            bgm_desc = (
                getattr(bible.master_bgm, "sonic_description", "")
                or getattr(bible.master_bgm, "lyria_prompt", "")
                or getattr(bible.master_bgm, "genre_style", "")
            )
        elif hasattr(bible, "sonic_identity") and bible.sonic_identity:
            bgm_obj = getattr(bible.sonic_identity, "master_bgm", bible.sonic_identity)
            bgm_desc = (
                getattr(bgm_obj, "sonic_description", "")
                or getattr(bgm_obj, "lyria_prompt", "")
                or getattr(bgm_obj, "genre_style", "")
            )

        if not bgm_desc:
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.MEDIUM,
                category="sonic_strategy",
                message="Master BGM sonic description is empty.",
                suggested_fix="Define clear tempo, instrumentation, and sonic atmosphere in master_bgm."
            ))
            score -= 3.0

        # Check domain color grading spec
        if hasattr(bible, "master_color_look") and bible.master_color_look:
            preset = getattr(bible.master_color_look, "look_preset", getattr(bible.master_color_look, "preset", None))
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.INFO,
                category="domain_color_grading",
                message=f"Deterministic ASC CDL look preset aligned: '{preset}' for domain '{detected_domain}'.",
                details={"domain": detected_domain, "preset": str(preset)},
            ))
        else:
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.LOW,
                category="domain_color_grading",
                message="Master color look spec missing from production bible.",
                suggested_fix="Assign master_color_look via get_domain_color_look().",
            ))
            score -= 0.25

        # Check calibrated 4-stem audio mixer
        if hasattr(bible, "master_audio_mixer") and bible.master_audio_mixer:
            channels = getattr(bible.master_audio_mixer, "channels", {})
            lufs = getattr(bible.master_audio_mixer, "master_lufs_target", -23.0)
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.INFO,
                category="sonic_mixer_calibration",
                message=f"Calibrated 4-stem audio mixer verified for domain '{detected_domain}' with target {lufs} LUFS across {len(channels)} channels.",
                details={"domain": detected_domain, "channels": list(channels.keys()) if isinstance(channels, dict) else []},
            ))
        else:
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.LOW,
                category="sonic_mixer_calibration",
                message="Master 4-stem audio mixer missing from production bible.",
                suggested_fix="Assign master_audio_mixer via get_domain_audio_mixer().",
            ))
            score -= 0.25

        # Check scene speed ramp curves
        scenes_with_ramp = [s for s in bible.scenes if getattr(s, "speed_ramp", None) is not None]
        if len(scenes_with_ramp) == len(bible.scenes) and len(bible.scenes) > 0:
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.INFO,
                category="speed_ramp_alignment",
                message=f"Kinetic speed ramp curves verified across all {len(bible.scenes)} scenes for domain '{detected_domain}'.",
                details={"domain": detected_domain, "scene_count": len(bible.scenes)},
            ))
        else:
            missing_count = len(bible.scenes) - len(scenes_with_ramp)
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.LOW,
                category="speed_ramp_alignment",
                message=f"{missing_count} scene(s) lack kinetic speed ramp curves.",
                suggested_fix="Assign scene.speed_ramp via get_domain_speed_ramp().",
            ))
            score -= 0.25

        # Check domain optical lens package (PM-FEAT-007)
        if hasattr(bible, "master_lens_package") and bible.master_lens_package:
            lens_pkg = bible.master_lens_package
            sensor_str = lens_pkg.sensor_format.value if hasattr(lens_pkg.sensor_format, "value") else str(lens_pkg.sensor_format)
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.INFO,
                category="optical_lens_alignment",
                message=f"Cinematic optical lens package verified: {lens_pkg.focal_length_mm}mm T{lens_pkg.aperture_t_stop} ({sensor_str}) for domain '{detected_domain}'.",
                details={"domain": detected_domain, "focal_length_mm": lens_pkg.focal_length_mm},
            ))
        else:
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.LOW,
                category="optical_lens_alignment",
                message="Master optical lens package missing from production bible.",
                suggested_fix="Assign master_lens_package via get_domain_optical_lens().",
            ))
            score -= 0.25

        # Check domain virtual production stage spec (PM-FEAT-008)
        if hasattr(bible, "virtual_production") and bible.virtual_production:
            vp_stage = bible.virtual_production
            fixtures = getattr(vp_stage, "dmx_fixtures", [])
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.INFO,
                category="virtual_production_alignment",
                message=f"Virtual Production stage manifest verified: '{vp_stage.stage_name}' with {len(fixtures)} DMX fixtures for domain '{detected_domain}'.",
                details={"domain": detected_domain, "stage_name": vp_stage.stage_name},
            ))
        else:
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.LOW,
                category="virtual_production_alignment",
                message="Virtual production stage spec missing from production bible.",
                suggested_fix="Assign virtual_production via get_domain_virtual_production().",
            ))
            score -= 0.25

        # Check domain motion control rig spec (PM-FEAT-009)
        if hasattr(bible, "master_moco_rig") and bible.master_moco_rig:
            moco = bible.master_moco_rig
            rig_type_str = moco.rig_type.value if hasattr(moco.rig_type, "value") else str(moco.rig_type)
            waypoints_count = len(getattr(moco, "waypoints", []))
            max_vel = getattr(moco, "max_velocity_mps", 0.0)
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.INFO,
                category="moco_rig_alignment",
                message=f"Kinetic MoCo rig verified: '{rig_type_str}' ({waypoints_count} 6-DOF waypoints, max {max_vel} m/s) aligned with domain '{detected_domain}'.",
                details={"domain": detected_domain, "rig_type": rig_type_str, "waypoints": waypoints_count},
            ))
        else:
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.LOW,
                category="moco_rig_alignment",
                message="Master motion control rig (master_moco_rig) missing from production bible.",
                suggested_fix="Assign master_moco_rig via get_domain_moco_rig().",
            ))
            score -= 0.25

        # Check domain volumetric studio lighting rig spec (PM-FEAT-010)
        if hasattr(bible, "master_lighting_rig") and bible.master_lighting_rig:
            rig = bible.master_lighting_rig
            fixtures = getattr(rig, "fixtures", [])
            haze = getattr(rig, "atmospheric_haze", None)
            haze_str = (haze.haze_type.value if hasattr(haze.haze_type, "value") else str(haze.haze_type)) if haze else "clean_air"
            k2f = getattr(rig, "key_to_fill_ratio", 2.0)
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.INFO,
                category="lighting_rig_alignment",
                message=f"Volumetric studio lighting rig verified: {len(fixtures)} fixtures, Key:Fill {k2f}:1, haze '{haze_str}' aligned with domain '{detected_domain}'.",
                details={"domain": detected_domain, "fixtures_count": len(fixtures), "key_to_fill": k2f},
            ))
        else:
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.LOW,
                category="lighting_rig_alignment",
                message="Master studio lighting rig (master_lighting_rig) missing from production bible.",
                suggested_fix="Assign master_lighting_rig via get_domain_lighting_rig().",
            ))
            score -= 0.25

        # Check domain depth of field (DoF) and optical focus calibration (PM-FEAT-011)
        if hasattr(bible, "master_dof_spec") and bible.master_dof_spec:
            dof = bible.master_dof_spec
            focus_style = getattr(dof, "focus_style", "Unknown")
            aperture = getattr(dof, "aperture_t_stop", 0.0)
            focal_mm = getattr(dof, "focal_length_mm", 0)
            iris = getattr(dof, "iris_geometry", "Unknown")
            depth_char = getattr(dof, "depth_character", "Unknown")
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.INFO,
                category="domain_dof_calibration",
                message=f"Domain DoF calibration verified: '{focus_style}' (T{aperture}, {focal_mm}mm, {iris}, {depth_char}) aligned with domain '{detected_domain}'.",
                details={"domain": detected_domain, "focus_style": focus_style, "aperture": aperture, "iris": iris, "depth_character": depth_char},
            ))
        else:
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.LOW,
                category="domain_dof_calibration",
                message="Master depth of field spec (master_dof_spec) missing from production bible.",
                suggested_fix="Assign master_dof_spec via get_domain_dof_spec().",
            ))
            score -= 0.25

        # Check domain 3D LUT color science & film emulation suite (PM-FEAT-012)
        if hasattr(bible, "master_lut_spec") and bible.master_lut_spec:
            lut = bible.master_lut_spec
            lut_name = getattr(lut, "lut_name", "Unknown")
            emulation = getattr(lut, "film_emulation", "Unknown")
            cube_fn = getattr(lut, "cube_filename", "Unknown")
            grid = getattr(lut, "grid_size", 33)
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.INFO,
                category="domain_lut_calibration",
                message=f"Domain 3D LUT color science verified: '{lut_name}' ({emulation}, {grid}x{grid}x{grid} {cube_fn}) aligned with domain '{detected_domain}'.",
                details={"domain": detected_domain, "lut_name": lut_name, "emulation": emulation, "cube": cube_fn},
            ))
        else:
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.LOW,
                category="domain_lut_calibration",
                message="Master 3D LUT spec (master_lut_spec) missing from production bible.",
                suggested_fix="Assign master_lut_spec via get_domain_lut_spec().",
            ))
            score -= 0.25

        # Check domain spatial audio & acoustic simulation (PM-FEAT-013)
        if hasattr(bible, "master_spatial_audio") and bible.master_spatial_audio:
            spatial = bible.master_spatial_audio
            bed = getattr(spatial.bed_format, "value", str(spatial.bed_format))
            room = spatial.acoustic_room.room_name if spatial.acoustic_room else "Standard Stage"
            rt60 = spatial.acoustic_room.rt60_seconds if spatial.acoustic_room else 0.45
            obj_count = len(spatial.audio_objects)
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.INFO,
                category="domain_spatial_audio_calibration",
                message=f"Domain spatial audio verified: {bed} Atmos bed, '{room}' (RT60={rt60:.2f}s, {obj_count} 3D objects) aligned with domain '{detected_domain}'.",
                details={"domain": detected_domain, "bed_format": bed, "room": room, "objects": obj_count},
            ))
        else:
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.LOW,
                category="domain_spatial_audio_calibration",
                message="Master spatial audio spec (master_spatial_audio) missing from production bible.",
                suggested_fix="Assign master_spatial_audio via get_domain_spatial_audio_spec().",
            ))
            score -= 0.25

        # Check domain VFX multi-pass compositing manifest (PM-FEAT-014)
        if hasattr(bible, "master_vfx_manifest") and bible.master_vfx_manifest:
            vfx = bible.master_vfx_manifest
            fmt = getattr(vfx, "channel_format", "half_float_16")
            pass_count = len(vfx.render_passes)
            crypto_entries = len(vfx.cryptomatte.matte_entries) if vfx.cryptomatte else 0
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.INFO,
                category="domain_vfx_compositing_calibration",
                message=f"Domain VFX compositing manifest verified: OpenEXR {fmt} ({pass_count} passes, {crypto_entries} Cryptomatte IDs, ACEScg) aligned with domain '{detected_domain}'.",
                details={"domain": detected_domain, "format": fmt, "passes": pass_count, "crypto_entries": crypto_entries},
            ))
        else:
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.LOW,
                category="domain_vfx_compositing_calibration",
                message="Master VFX compositing manifest (master_vfx_manifest) missing from production bible.",
                suggested_fix="Assign master_vfx_manifest via get_domain_vfx_manifest().",
            ))
            score -= 0.25

        # Check domain HDR mastering metadata calibration (PM-FEAT-015)
        if hasattr(bible, "master_hdr_spec") and bible.master_hdr_spec:
            hdr = bible.master_hdr_spec
            peak = getattr(hdr, "target_peak_nits", 1000.0)
            tf = getattr(hdr.transfer_function, "value", str(hdr.transfer_function))
            gamut = getattr(hdr.color_gamut, "value", str(hdr.color_gamut))
            tm = getattr(hdr.tone_mapping, "value", str(hdr.tone_mapping))
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.INFO,
                category="domain_hdr_calibration",
                message=f"Domain HDR metadata verified: {tf} ({gamut}, {peak:.0f} nits peak, MaxCLL {hdr.max_cll_nits:.0f}, MaxFALL {hdr.max_fall_nits:.0f}, tone mapper {tm}) aligned with domain '{detected_domain}'.",
                details={"domain": detected_domain, "transfer_function": tf, "color_gamut": gamut, "peak_nits": peak, "tone_mapping": tm},
            ))
        else:
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.LOW,
                category="domain_hdr_calibration",
                message="Master HDR metadata spec (master_hdr_spec) missing from production bible.",
                suggested_fix="Assign master_hdr_spec via get_domain_hdr_spec().",
            ))
            score -= 0.25

        # Check domain 1st AD Stripboard Schedule & DOOD SAG-AFTRA 12h turnaround (PM-FEAT-016)
        if hasattr(bible, "master_stripboard_schedule") and bible.master_stripboard_schedule:
            sched = bible.master_stripboard_schedule
            total_days = getattr(sched, "total_shooting_days", getattr(sched, "total_shoot_days", 1))
            total_strips = len(sched.strips)
            dood_records = getattr(sched, "dood_records", getattr(sched, "day_out_of_days", []))
            dood_count = len(dood_records)
            turnaround_ok = all(getattr(r, "sag_turnaround_compliant", getattr(r, "sag_aftra_compliant", True)) for r in dood_records)
            if not turnaround_ok:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.MEDIUM,
                    category="stripboard_turnaround_violation",
                    message="Stripboard schedule contains SAG-AFTRA 12-hour turnaround rest interval violations.",
                    suggested_fix="Re-order strips or add day breaks to guarantee 12 hours minimum rest between shooting calls."
                ))
                score -= 1.0
            else:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="domain_stripboard_calibration",
                    message=f"1st AD Stripboard schedule verified: {total_strips} strips across {total_days} shoot day(s), {dood_count} DOOD cast records (SAG-AFTRA 12-hour turnaround rest compliant) aligned with domain '{detected_domain}'.",
                    details={"domain": detected_domain, "shoot_days": total_days, "strips_count": total_strips, "dood_count": dood_count, "sag_turnaround": turnaround_ok},
                ))
        else:
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.LOW,
                category="domain_stripboard_calibration",
                message="Master stripboard schedule (master_stripboard_schedule) missing from production bible.",
                suggested_fix="Assign master_stripboard_schedule via get_domain_stripboard_spec().",
            ))
            score -= 0.25

        # Check domain physical film stock chemistry, grain, halation, and gate weave (PM-FEAT-017)
        film_spec = getattr(bible, "master_film_emulation", getattr(bible, "film_emulation", None))
        if film_spec:
            stock = getattr(film_spec, "stock_name", "Unknown Stock")
            mfr = getattr(film_spec, "manufacturer", None)
            mfr_str = mfr.value if hasattr(mfr, "value") else str(mfr)
            gauge = getattr(film_spec, "gauge", None)
            gauge_str = gauge.value if hasattr(gauge, "value") else str(gauge)
            rms = getattr(getattr(film_spec, "grain", None), "rms_granularity", 0.0)
            halation_px = getattr(getattr(film_spec, "halation", None), "halation_radius_pixels", 0.0)
            weave_um = getattr(getattr(film_spec, "gate_weave", None), "lateral_drift_microns", 0.0)
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.INFO,
                category="domain_film_emulation_calibration",
                message=f"Physical film stock emulation verified: {stock} ({mfr_str}, {gauge_str}, RMS {rms}, halation {halation_px}px, gate weave {weave_um}μm) aligned with domain '{detected_domain}'.",
                details={"domain": detected_domain, "stock": stock, "manufacturer": mfr_str, "gauge": gauge_str, "rms_granularity": rms},
            ))
        else:
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.LOW,
                category="domain_film_emulation_calibration",
                message="Master physical film stock emulation spec (master_film_emulation) missing from production bible.",
                suggested_fix="Assign master_film_emulation via get_domain_film_emulation_spec().",
            ))
            score -= 0.25

        # Check domain production clapper slate & ASC-MHL v2.0 offload manifest (PM-FEAT-018)
        slate_spec = getattr(bible, "master_slate_spec", getattr(bible, "slate_spec", None))
        if slate_spec:
            slates_count = len(getattr(slate_spec, "scenes", []))
            mhl_manifest = getattr(slate_spec, "asc_mhl", None) or getattr(slate_spec, "asc_mhl_manifest", None)
            hash_count = len(getattr(mhl_manifest, "hash_entries", [])) if mhl_manifest else 0
            first_slate = slate_spec.scenes[0] if getattr(slate_spec, "scenes", None) else None
            cam_roll = getattr(first_slate, "camera_roll", None) or getattr(slate_spec, "camera_roll", "A01")
            sound_roll = getattr(first_slate, "sound_roll", None) or getattr(slate_spec, "sound_roll", "SR01")
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.INFO,
                category="domain_clapper_slate_calibration",
                message=f"SMPTE 12M clapper slate & ASC-MHL v2.0 manifest verified: {slates_count} scene slates (Cam {cam_roll}, Sound {sound_roll}, {hash_count} MHL hash entries) aligned with domain '{detected_domain}'.",
                details={"domain": detected_domain, "slates_count": slates_count, "camera_roll": cam_roll, "sound_roll": sound_roll, "mhl_hash_entries": hash_count},
            ))
        else:
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.LOW,
                category="domain_clapper_slate_calibration",
                message="Master production clapper slate spec (master_slate_spec) missing from production bible.",
                suggested_fix="Assign master_slate_spec via get_domain_clapper_slate_spec().",
            ))
            score -= 0.25

        # Check domain aerial drone flight path calibration (PM-FEAT-019)
        drone_spec = getattr(bible, "master_drone_spec", None) or next((getattr(s, "drone_flight", None) for s in bible.scenes if getattr(s, "drone_flight", None) is not None), None)
        if drone_spec is not None:
            rig = str(getattr(drone_spec, "drone_rig", ""))
            profile = str(getattr(drone_spec, "flight_profile", ""))
            wps = getattr(drone_spec, "waypoints", []) or []
            max_speed = max((getattr(w, "speed_mps", 0.0) for w in wps), default=getattr(drone_spec, "max_speed_mps", 0.0))
            alt = getattr(drone_spec, "max_altitude_agl_m", getattr(drone_spec, "target_altitude_agl_m", 0.0))
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.INFO,
                category="domain_drone_flight_calibration",
                message=f"Aerial drone flight spec verified: {rig} ({profile}, speed {max_speed} m/s, altitude {alt}m AGL) calibrated for domain '{detected_domain}'.",
                details={"domain": detected_domain, "drone_rig": rig, "flight_profile": profile, "speed_mps": max_speed, "altitude_agl_m": alt},
            ))
        else:
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.LOW,
                category="domain_drone_flight_calibration",
                message="Master aerial drone flight path spec (master_drone_spec) missing from production bible.",
                suggested_fix="Assign master_drone_spec via get_domain_drone_spec().",
            ))
            score -= 0.25

        # Check domain commercial production budget tiering (PM-FEAT-020)
        aicp_bid = getattr(bible, "master_aicp_bid", getattr(bible, "aicp_bid", None))
        if aicp_bid is not None:
            top_sheet = getattr(aicp_bid, "top_sheet", getattr(aicp_bid, "top_sheet_summary", None))
            grand_tot = getattr(top_sheet, "grand_total", getattr(top_sheet, "grand_total_bid_usd", getattr(top_sheet, "grand_total_bid", 0.0))) if top_sheet else 0.0

            budget_targets = {
                "automotive_robotics": (320000.0, 480000.0),
                "culinary_asmr": (95000.0, 165000.0),
                "luxury_fashion": (220000.0, 380000.0),
                "kinetic_action": (280000.0, 450000.0),
                "tech_hardware": (140000.0, 240000.0),
                "architectural_sanctuary": (120000.0, 210000.0),
            }
            target_min, target_max = budget_targets.get(detected_domain, (50000.0, 500000.0))
            if target_min <= grand_tot <= target_max:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="domain_aicp_budget_tiering",
                    message=f"AICP commercial production budget verified: Grand total ${grand_tot:,.2f} falls within target window [${target_min:,.0f} - ${target_max:,.0f}] for domain '{detected_domain}'.",
                    details={"domain": detected_domain, "grand_total": grand_tot, "target_min": target_min, "target_max": target_max},
                ))
            else:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.LOW,
                    category="domain_aicp_budget_tiering",
                    message=f"AICP budget ${grand_tot:,.2f} outside expected commercial tier [${target_min:,.0f} - ${target_max:,.0f}] for domain '{detected_domain}'.",
                    details={"domain": detected_domain, "grand_total": grand_tot, "target_min": target_min, "target_max": target_max},
                    suggested_fix=f"Adjust line item rates to target commercial budget of ${target_min:,.0f} - ${target_max:,.0f}.",
                ))
                score -= 0.25
        else:
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.LOW,
                category="domain_aicp_budget_tiering",
                message="Master AICP commercial production bid spec (master_aicp_bid) missing from production bible.",
                suggested_fix="Assign master_aicp_bid via get_domain_aicp_bid_spec().",
            ))
            score -= 0.25

        # Check multi-aspect social reframe & cutdown delivery alignment (PM-FEAT-021)
        reframe_manifest = getattr(bible, "master_reframe_manifest", None)
        if reframe_manifest is not None:
            cut_count = len(getattr(reframe_manifest, "cutdown_versions", []) or [])
            safe_ok = bool(getattr(reframe_manifest, "safe_zone_audit_passed", True))
            matrix_count = getattr(reframe_manifest, "deliverable_matrix_count", 0)
            if safe_ok and cut_count >= 2:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="domain_reframe_strategy",
                    message=f"Multi-aspect social reframe manifest verified: {matrix_count} crop windows and {cut_count} cutdown timelines pass platform UI safe zones for domain '{detected_domain}'.",
                    details={"domain": detected_domain, "deliverable_matrix_count": matrix_count, "cutdowns": cut_count},
                ))
            else:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.MEDIUM,
                    category="domain_reframe_strategy",
                    message=f"Reframe manifest incomplete or safe-zone collision detected (safe_ok={safe_ok}, cutdowns={cut_count}).",
                    suggested_fix="Regenerate master_reframe_manifest via get_domain_reframe_manifest().",
                ))
                score -= 0.5
        else:
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.LOW,
                category="domain_reframe_strategy",
                message="Master multi-aspect reframe manifest (master_reframe_manifest) missing from production bible.",
                suggested_fix="Assign master_reframe_manifest via get_domain_reframe_manifest().",
            ))
            score -= 0.25

        # Check Broadcast QC, loudness standard alignment & rights clearance completeness (PM-FEAT-022)
        qc_spec = getattr(bible, "master_broadcast_qc", None)
        if qc_spec is not None:
            expected_std = "atsc_a85" if detected_domain in {"automotive_robotics", "kinetic_action"} else "ebu_r128"
            loud_spec = getattr(qc_spec, "loudness_compliance", None)
            actual_std = str(getattr(getattr(loud_spec, "standard", expected_std), "value", getattr(loud_spec, "standard", expected_std))).lower() if loud_spec else expected_std
            overall_v = str(getattr(getattr(qc_spec, "overall_verdict", "PASS"), "value", getattr(qc_spec, "overall_verdict", "PASS"))).upper()
            cleared = bool(getattr(qc_spec, "legal_clearance_complete", True))
            if overall_v == "FAIL":
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="domain_broadcast_qc",
                    message=f"Broadcast Technical QC verdict FAIL for domain '{detected_domain}'.",
                    suggested_fix="Resolve PSE flash-safety or loudness target discrepancies before trafficking.",
                ))
                score -= 1.0
            else:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="domain_broadcast_qc",
                    message=f"Broadcast QC & trafficking spec verified ({overall_v}, standard={actual_std}, legal_cleared={cleared}) for domain '{detected_domain}'.",
                    details={"domain": detected_domain, "loudness_standard": actual_std, "overall_verdict": overall_v, "legal_clearance_complete": cleared},
                ))
        else:
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.LOW,
                category="domain_broadcast_qc",
                message="Master Broadcast QC spec (master_broadcast_qc) missing from production bible.",
                suggested_fix="Assign master_broadcast_qc via get_domain_broadcast_qc_spec().",
            ))
            score -= 0.25

        # Check Inter-Scene Continuity & 180-Degree Blocking domain alignment (PM-FEAT-023)
        expected_screen_dirs = {
            "culinary_asmr": "static_centered",
            "automotive_robotics": "left_to_right",
            "luxury_fashion": "toward_camera",
            "kinetic_action": "left_to_right",
            "tech_hardware": "static_centered",
            "architectural_sanctuary": "toward_camera",
        }
        blocking_manifest = getattr(bible, "master_continuity_blocking", None)
        if blocking_manifest is not None:
            cont_passed = bool(getattr(blocking_manifest, "continuity_passed", True))
            all_180 = bool(getattr(blocking_manifest, "all_180_axis_locked", True))
            axis_viol = int(
                getattr(
                    blocking_manifest,
                    "axis_violations_count",
                    sum(len(getattr(c, "violations", []) or []) for c in (getattr(blocking_manifest, "cut_checks", []) or [])),
                )
                or 0
            )
            dom_dir = str(
                getattr(getattr(blocking_manifest, "dominant_screen_direction", ""), "value", getattr(blocking_manifest, "dominant_screen_direction", ""))
            ).lower()
            if not cont_passed or not all_180 or axis_viol > 0:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="domain_continuity_blocking",
                    message=f"Inter-scene continuity blocking failed for domain '{detected_domain}' (continuity_passed={cont_passed}, axis_violations={axis_viol}).",
                    suggested_fix="Resolve 180-degree axis or 30-degree cut violations in master_continuity_blocking.",
                ))
                score -= 1.0
            elif detected_domain in expected_screen_dirs and dom_dir and dom_dir != expected_screen_dirs[detected_domain]:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.LOW,
                    category="domain_continuity_blocking",
                    message=(
                        f"Dominant screen direction '{dom_dir}' differs from domain archetype '{detected_domain}' "
                        f"calibration '{expected_screen_dirs[detected_domain]}'."
                    ),
                    suggested_fix="Calibrate master_continuity_blocking via get_domain_continuity_blocking_spec().",
                ))
                score -= 0.25
            else:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="domain_continuity_blocking",
                    message=(
                        f"Inter-scene continuity & 180-degree blocking aligned for domain '{detected_domain}' "
                        f"(screen_direction={dom_dir}, scenes={len(getattr(blocking_manifest, 'scene_blockings', []) or [])}, continuity_passed=True)."
                    ),
                    details={"domain": detected_domain, "dominant_screen_direction": dom_dir, "continuity_passed": True},
                ))
        else:
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.LOW,
                category="domain_continuity_blocking",
                message="Master continuity blocking spec (master_continuity_blocking) missing from production bible.",
                suggested_fix="Assign master_continuity_blocking via get_domain_continuity_blocking_spec().",
            ))
            score -= 0.25

        # Check Client Review & Sign-Off Gate readiness across the 6 archetypes (PM-FEAT-024)
        review_manifest = getattr(bible, "master_client_review", None)
        if review_manifest is not None:
            ready_render = bool(getattr(review_manifest, "ready_for_live_render", True))
            overall_rev = str(
                getattr(getattr(review_manifest, "overall_status", "approved"), "value", getattr(review_manifest, "overall_status", "approved"))
            ).lower()
            raw_blockers = int(getattr(review_manifest, "unresolved_blockers", getattr(review_manifest, "blocking_notes_count", 0)) or 0)
            computed_blockers = sum(
                1
                for sr in (getattr(review_manifest, "scene_reviews", []) or [])
                for ann in (getattr(sr, "annotations", []) or [])
                if not getattr(ann, "resolved", True) and getattr(ann, "blocking_gate", False)
            )
            eff_blockers = max(raw_blockers, int(getattr(review_manifest, "blocking_notes_count", 0) or 0), computed_blockers)
            if not ready_render or eff_blockers > 0 or overall_rev == "changes_requested":
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="domain_client_review",
                    message=(
                        f"Client review sign-off gate incomplete for domain '{detected_domain}' "
                        f"(status={overall_rev}, unresolved_blockers={eff_blockers}, ready_for_live_render={ready_render})."
                    ),
                    suggested_fix="Resolve blocking stakeholder annotations and obtain sign-off before live render.",
                ))
                score -= 1.0
            else:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="domain_client_review",
                    message=(
                        f"Client review & sign-off readiness verified for domain '{detected_domain}' "
                        f"(status={overall_rev}, unresolved_blockers=0, ready_for_live_render=True)."
                    ),
                    details={"domain": detected_domain, "overall_status": overall_rev, "ready_for_live_render": True},
                ))
        else:
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.LOW,
                category="domain_client_review",
                message="Master client review spec (master_client_review) missing from production bible.",
                suggested_fix="Assign master_client_review via get_domain_client_review_spec().",
            ))
            score -= 0.25

        # Check domain-calibrated C2PA Content Credentials & Talent Likeness Provenance (PM-FEAT-025)
        expected_c2pa_tiers = {
            "automotive_robotics": "hybrid_icvfx_assisted",
            "culinary_asmr": "full_ai_synthetic",
            "luxury_fashion": "virtual_digital_replica",
            "kinetic_action": "hybrid_icvfx_assisted",
            "tech_hardware": "full_ai_synthetic",
            "architectural_sanctuary": "full_ai_synthetic",
        }
        c2pa_manifest = getattr(bible, "master_c2pa_provenance", None)
        if c2pa_manifest is not None:
            tier_val = str(
                getattr(getattr(c2pa_manifest, "synthetic_tier", ""), "value", getattr(c2pa_manifest, "synthetic_tier", ""))
            ).lower()
            likeness_recs = getattr(c2pa_manifest, "talent_likeness_records", None) or []
            consents_verified = bool(getattr(c2pa_manifest, "all_likeness_consents_verified", True))
            exp_tier = expected_c2pa_tiers.get(detected_domain)
            if not consents_verified:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="domain_c2pa_provenance",
                    message=f"Talent likeness consent unverified for domain '{detected_domain}' in master_c2pa_provenance.",
                    suggested_fix="Verify SAG-AFTRA & EU AI Act Art. 50 likeness consent records in master_c2pa_provenance.",
                ))
                score -= 1.0
            elif exp_tier and tier_val != exp_tier:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.LOW,
                    category="domain_c2pa_provenance",
                    message=f"C2PA synthetic_tier '{tier_val}' differs from domain '{detected_domain}' calibration '{exp_tier}'.",
                    suggested_fix="Calibrate master_c2pa_provenance via get_domain_c2pa_provenance_spec().",
                ))
                score -= 0.25
            elif not likeness_recs:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.LOW,
                    category="domain_c2pa_provenance",
                    message=f"master_c2pa_provenance has empty talent_likeness_records for domain '{detected_domain}'.",
                    suggested_fix="Populate talent_likeness_records via get_domain_c2pa_provenance_spec().",
                ))
                score -= 0.25
            else:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="domain_c2pa_provenance",
                    message=(
                        f"C2PA v2.1 provenance calibrated for domain '{detected_domain}' "
                        f"(tier={tier_val}, likeness_records={len(likeness_recs)}, consents_verified=True)."
                    ),
                    details={"domain": detected_domain, "synthetic_tier": tier_val, "likeness_records_count": len(likeness_recs)},
                ))
        else:
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.LOW,
                category="domain_c2pa_provenance",
                message="Master C2PA provenance spec (master_c2pa_provenance) missing from production bible.",
                suggested_fix="Assign master_c2pa_provenance via get_domain_c2pa_provenance_spec().",
            ))
            score -= 0.25

        # Check domain-calibrated On-Set Safety Risk & JSA Matrix (PM-FEAT-026)
        expected_safety_calibration = {
            "automotive_robotics": (18.0, "stunt_vehicle"),
            "kinetic_action": (10.0, "wire_rigging_height"),
            "tech_hardware": (6.0, "laser_optical"),
            "luxury_fashion": (4.5, "electrical_dmx_wet"),
            "architectural_sanctuary": (4.0, "wire_rigging_height"),
            "culinary_asmr": (3.0, "food_allergen_thermal"),
        }
        safety_manifest = getattr(bible, "master_safety_risk", None)
        if safety_manifest is not None:
            scene_safeties = getattr(safety_manifest, "scene_safety_specs", None) or []
            max_excl_m = max((float(getattr(ss, "max_exclusion_zone_m", 0.0) or 0.0) for ss in scene_safeties), default=0.0)
            standby = getattr(safety_manifest, "standby_emergency", None)
            present_cats = {
                str(getattr(getattr(h, "category", ""), "value", getattr(h, "category", ""))).lower()
                for ss in scene_safeties
                for h in (getattr(ss, "hazards", None) or [])
            }
            exp_min_m, exp_cat = expected_safety_calibration.get(detected_domain, (3.0, "wire_rigging_height"))
            open_holds = int(getattr(safety_manifest, "open_holds_count", 0) or 0)
            if open_holds > 0:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="domain_safety_risk",
                    message=f"On-set Safety JSA has {open_holds} open hold(s) for domain '{detected_domain}'.",
                    suggested_fix="Clear all safety holds and verify hazard mitigations in master_safety_risk.",
                ))
                score -= 1.0
            elif standby is None or not getattr(standby, "emergency_radio_channel", ""):
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.LOW,
                    category="domain_safety_risk",
                    message=f"Standby emergency protocol incomplete for domain '{detected_domain}'.",
                    suggested_fix="Populate standby_emergency via get_domain_safety_risk_spec().",
                ))
                score -= 0.25
            elif max_excl_m + 1e-6 < exp_min_m or (exp_cat and present_cats and exp_cat not in present_cats):
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.LOW,
                    category="domain_safety_risk",
                    message=(
                        f"Safety JSA calibration mismatch for domain '{detected_domain}': "
                        f"max_exclusion_zone_m={max_excl_m:.1f}m (expected >= {exp_min_m:.1f}m), categories={sorted(present_cats)}."
                    ),
                    suggested_fix="Calibrate master_safety_risk via get_domain_safety_risk_spec().",
                ))
                score -= 0.25
            else:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="domain_safety_risk",
                    message=(
                        f"On-set Safety JSA calibrated for domain '{detected_domain}' "
                        f"(max_exclusion={max_excl_m:.1f}m, radio='{standby.emergency_radio_channel}', hazards={sorted(present_cats)})."
                    ),
                    details={"domain": detected_domain, "max_exclusion_zone_m": max_excl_m, "hazard_categories": sorted(present_cats)},
                ))
        else:
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.LOW,
                category="domain_safety_risk",
                message="Master On-Set Safety Risk spec (master_safety_risk) missing from production bible.",
                suggested_fix="Assign master_safety_risk via get_domain_safety_risk_spec().",
            ))
            score -= 0.25

        # Check domain-calibrated Multi-Territory Localization & ADR Dubbing (PM-FEAT-027) when manifest is present
        loc_manifest = getattr(bible, "localization_manifest", None)
        if loc_manifest is not None:
            expected_loc = get_domain_localization_spec(detected_domain)
            target_locales = list(getattr(loc_manifest, "target_locales", None) or [])
            territories = list(getattr(loc_manifest, "territories", None) or [])
            max_wps = float(getattr(loc_manifest, "max_allowed_wps", 2.5) or 2.5)
            exp_wps = float(expected_loc.get("max_allowed_wps", 2.5))
            broadcast_ready = bool(getattr(loc_manifest, "broadcast_ready", True))
            if not broadcast_ready:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="domain_localization_adr",
                    message=f"Localization manifest not broadcast_ready for domain '{detected_domain}'.",
                    suggested_fix="Resolve lip-sync drift and safe-supers overflow in localization_manifest.",
                ))
                score -= 1.0
            elif not target_locales or not territories:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.LOW,
                    category="domain_localization_adr",
                    message=f"Localization manifest has empty target_locales/territories for domain '{detected_domain}'.",
                    suggested_fix="Populate localization_manifest via compile_localization_manifest(bible).",
                ))
                score -= 0.25
            elif max_wps > exp_wps + 0.6:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.LOW,
                    category="domain_localization_adr",
                    message=(
                        f"Localization max_allowed_wps={max_wps:.2f} exceeds domain '{detected_domain}' "
                        f"calibration ceiling ({exp_wps:.2f} WPS)."
                    ),
                    suggested_fix="Calibrate localization_manifest via get_domain_localization_spec().",
                ))
                score -= 0.25
            else:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="domain_localization_adr",
                    message=(
                        f"Multi-Territory Localization & ADR calibrated for domain '{detected_domain}' "
                        f"(locales={', '.join(target_locales[:4])}, max_wps={max_wps:.2f}, broadcast_ready=True)."
                    ),
                    details={"domain": detected_domain, "target_locales": target_locales, "max_allowed_wps": max_wps},
                ))

        # Check domain-calibrated Editorial J-Cut/L-Cut & BPM Spotting (PM-FEAT-028) when manifest is present
        spot_manifest = getattr(bible, "spotting_manifest", None)
        if spot_manifest is not None:
            expected_spot = get_domain_spotting_spec(detected_domain)
            tempo_bpm = float(getattr(spot_manifest, "tempo_bpm", 0.0) or 0.0)
            bridges = list(getattr(spot_manifest, "bridges", None) or [])
            beat_score = float(getattr(spot_manifest, "beat_alignment_score", 0.0) or 0.0)
            exp_bridge_obj = expected_spot.get("default_bridge_type")
            exp_bridge_str = str(getattr(exp_bridge_obj, "value", exp_bridge_obj or "j_cut")).lower()
            bridge_types = {
                str(getattr(getattr(br, "bridge_type", ""), "value", getattr(br, "bridge_type", ""))).lower()
                for br in bridges
            }
            if tempo_bpm <= 0.0 or (len(bible.scenes) > 1 and not bridges):
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.LOW,
                    category="domain_spotting_sync",
                    message=f"Spotting manifest incomplete for domain '{detected_domain}' (tempo_bpm={tempo_bpm}, bridges={len(bridges)}).",
                    suggested_fix="Build spotting_manifest via build_spotting_manifest(bible, fps=24).",
                ))
                score -= 0.25
            elif beat_score < 60.0:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="domain_spotting_sync",
                    message=f"Editorial spotting beat_alignment_score={beat_score:.1f}% below threshold for domain '{detected_domain}'.",
                    suggested_fix="Align scene cut boundaries and J-Cut/L-Cut bridges with BPM beat grid.",
                ))
                score -= 1.0
            elif bridges and exp_bridge_str not in bridge_types and "jl_overlap" not in bridge_types:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.LOW,
                    category="domain_spotting_sync",
                    message=(
                        f"Editorial bridge types {sorted(bridge_types)} differ from domain '{detected_domain}' "
                        f"calibrated default '{exp_bridge_str}'."
                    ),
                    suggested_fix="Calibrate spotting_manifest via get_domain_spotting_spec().",
                ))
                score -= 0.25
            else:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="domain_spotting_sync",
                    message=(
                        f"Editorial Spotting & Beat-Grid calibrated for domain '{detected_domain}' "
                        f"({tempo_bpm:.1f} BPM, bridges={sorted(bridge_types) or [exp_bridge_str]}, beat_score={beat_score:.1f}%)."
                    ),
                    details={"domain": detected_domain, "tempo_bpm": tempo_bpm, "beat_alignment_score": beat_score},
                ))

        # Verify Stereoscopic 3D & Spatial Video constraints (PM-FEAT-029)
        s3d_spec = getattr(bible, "master_s3d_spec", None)
        if s3d_spec is not None:
            expected_s3d = get_domain_s3d_spec(detected_domain)
            exp_fov = expected_s3d.get("field_of_view_deg", 100.0)
            actual_fov = float(getattr(s3d_spec, "field_of_view_deg", 0.0) or 0.0)
            if abs(actual_fov - exp_fov) > 0.1:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.LOW,
                    category="domain_s3d_calibration",
                    message=f"S3D field_of_view_deg={actual_fov} differs from domain '{detected_domain}' baseline {exp_fov}.",
                    suggested_fix="Calibrate master_s3d_spec via get_domain_s3d_spec()."
                ))
                score -= 0.25

        # Verify Accessibility AD CVAA compliance (PM-FEAT-030)
        ad_spec = getattr(bible, "master_accessibility_spec", None)
        if ad_spec is not None:
            expected_ad = get_domain_accessibility_spec(detected_domain)
            exp_audience = str(getattr(expected_ad.get("target_audience", ""), "value", expected_ad.get("target_audience", "")))
            actual_audience = str(getattr(getattr(ad_spec, "target_audience", ""), "value", getattr(ad_spec, "target_audience", "")))
            if actual_audience and exp_audience and actual_audience != exp_audience:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.LOW,
                    category="domain_accessibility_ad_calibration",
                    message=f"AD target_audience '{actual_audience}' differs from domain '{detected_domain}' baseline '{exp_audience}'.",
                    suggested_fix="Calibrate master_accessibility_spec via get_domain_accessibility_spec()."
                ))
                score -= 0.25

        # Verify Wardrobe, Prop Continuity & Art Dressing Bible (PM-FEAT-031)
        wp_bible = getattr(bible, "master_wardrobe_prop_bible", None)
        if wp_bible is not None:
            expected_wp = get_domain_wardrobe_prop_spec(detected_domain)
            breaks = int(getattr(wp_bible, "continuity_breaks_detected", 0) or 0)
            pull_ready = bool(getattr(wp_bible, "pull_list_ready", True))
            if breaks > 0 or not pull_ready:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="domain_wardrobe_prop_continuity",
                    message=(
                        f"MasterWardrobePropBible detected {breaks} prop continuity break(s) "
                        f"(pull_list_ready={pull_ready}) for domain '{detected_domain}'."
                    ),
                    suggested_fix="Resolve prop state reversals/hand swaps via continuity_delta_note and recompile wardrobe_prop_bible.",
                ))
                score -= 2.0
            else:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="domain_wardrobe_prop_continuity",
                    message=(
                        f"Wardrobe & Prop Continuity verified for domain '{detected_domain}' "
                        f"(looks={getattr(wp_bible, 'total_looks', 1)}, hero_props={getattr(wp_bible, 'total_hero_props', 0)}, "
                        f"continuity_breaks=0, pull_list_ready=True)."
                    ),
                    details={
                        "domain": detected_domain,
                        "continuity_breaks_detected": 0,
                        "expected_prop_id": expected_wp.get("prop_id"),
                    },
                ))

        # Verify AI Compute Economics & AICP Savings Guardrail (PM-FEAT-032)
        econ_spec = getattr(bible, "master_render_economics_spec", None)
        if econ_spec is not None:
            expected_econ = get_domain_render_economics_spec(detected_domain)
            guardrail = getattr(econ_spec, "guardrail", None)
            if guardrail is None:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.LOW,
                    category="domain_render_economics",
                    message=f"MasterRenderEconomicsManifest missing guardrail summary for domain '{detected_domain}'.",
                    suggested_fix="Compile master_render_economics_spec via compile_render_economics_manifest().",
                ))
                score -= 0.25
            else:
                within_budget = bool(getattr(guardrail, "within_budget", True))
                savings_pct = float(getattr(guardrail, "simulation_savings_vs_aicp_pct", 0.0) or 0.0)
                est_usd = float(getattr(guardrail, "estimated_total_usd", 0.0) or 0.0)
                cap_usd = float(getattr(guardrail, "max_render_budget_usd", 0.0) or 0.0)
                if not within_budget:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.HIGH,
                        category="domain_render_economics",
                        message=(
                            f"Render economics estimated spend (${est_usd:.2f}) exceeds budget ceiling "
                            f"(${cap_usd:.2f}) for domain '{detected_domain}'."
                        ),
                        suggested_fix="Calibrate take budget or cap via get_domain_render_economics_spec().",
                    ))
                    score -= 2.0
                elif savings_pct < 90.0:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.MEDIUM,
                        category="domain_render_economics",
                        message=(
                            f"AI-vs-AICP simulation savings ({savings_pct:.2f}%) below 90% commercial benchmark "
                            f"for domain '{detected_domain}'."
                        ),
                        suggested_fix="Re-evaluate planned takes and AICP bid baseline in compile_render_economics_manifest().",
                    ))
                    score -= 1.0
                else:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.INFO,
                        category="domain_render_economics",
                        message=(
                            f"Render economics calibrated for domain '{detected_domain}' "
                            f"(est=${est_usd:.2f}/${cap_usd:.2f} cap, domain_cap=${expected_econ.get('max_render_budget_usd', cap_usd):.2f}, "
                            f"AI-vs-AICP savings={savings_pct:.2f}%)."
                        ),
                        details={
                            "domain": detected_domain,
                            "estimated_total_usd": est_usd,
                            "max_render_budget_usd": cap_usd,
                            "simulation_savings_vs_aicp_pct": savings_pct,
                        },
                    ))

        # Verify Motion Graphics, Kinetic Typography & Brand End-Card Calibration (PM-FEAT-033)
        gfx_spec = getattr(bible, "master_motion_graphics", None)
        if gfx_spec is not None:
            expected_gfx = get_domain_motion_graphics_spec(detected_domain)
            exp_primary_font = str(expected_gfx.get("primary_typeface", "") or "")
            actual_primary_font = str(getattr(gfx_spec, "primary_typeface", "") or "")
            endcard_obj = getattr(gfx_spec, "endcard", None)
            ec_dur = float(getattr(endcard_obj, "duration_sec", 0.0) or 0.0) if endcard_obj is not None else 0.0
            max_wpm = float(getattr(gfx_spec, "max_wpm_detected", 0.0) or 0.0)
            safe_ok = bool(getattr(gfx_spec, "all_safe_zones_cleared", True))
            legal_ok = bool(getattr(gfx_spec, "legal_supers_compliant", True))

            auto_legal_ok = True
            if detected_domain == "automotive_robotics":
                legal_texts = [
                    str(getattr(cue, "copy_text", "") or "")
                    for sg in (getattr(gfx_spec, "scene_graphics", None) or [])
                    for cue in (getattr(sg, "cues", None) or [])
                    if str(getattr(getattr(cue, "role", ""), "value", getattr(cue, "role", ""))).lower() == "legal_disclaimer"
                ]
                auto_legal_ok = any("Closed course. Professional driver." in txt for txt in legal_texts)

            if endcard_obj is None or ec_dur < 2.5 or ec_dur > 3.0:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.MEDIUM,
                    category="domain_motion_graphics_calibration",
                    message=f"BrandEndcardSpec duration ({ec_dur:.2f}s) outside calibrated 2.5s-3.0s window for domain '{detected_domain}'.",
                    suggested_fix="Calibrate master_motion_graphics via get_domain_motion_graphics_spec(bible).",
                ))
                score -= 0.5
            elif not auto_legal_ok:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="domain_motion_graphics_calibration",
                    message="Automotive robotics production lacks mandatory 'Closed course. Professional driver.' legal super.",
                    suggested_fix="Hydrate master_motion_graphics via get_domain_motion_graphics_spec(bible) for automotive_robotics.",
                ))
                score -= 1.0
            elif max_wpm > 180.0 or not safe_ok or not legal_ok:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="domain_motion_graphics_calibration",
                    message=(
                        f"Motion graphics calibration failed for domain '{detected_domain}' "
                        f"(max_wpm={max_wpm:.1f}, all_safe_zones_cleared={safe_ok}, legal_supers_compliant={legal_ok})."
                    ),
                    suggested_fix="Recompile master_motion_graphics via get_domain_motion_graphics_spec(bible).",
                ))
                score -= 1.0
            elif exp_primary_font and actual_primary_font and actual_primary_font != exp_primary_font:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.LOW,
                    category="domain_motion_graphics_calibration",
                    message=(
                        f"Motion graphics primary_typeface '{actual_primary_font}' differs from domain "
                        f"'{detected_domain}' baseline '{exp_primary_font}'."
                    ),
                    suggested_fix="Calibrate master_motion_graphics via get_domain_motion_graphics_spec().",
                ))
                score -= 0.25
            else:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="domain_motion_graphics_calibration",
                    message=(
                        f"Motion graphics & Brand End-Card calibrated for domain '{detected_domain}' "
                        f"(typeface='{actual_primary_font}', endcard={ec_dur:.2f}s, max_wpm={max_wpm:.1f}, 9:16_clear={safe_ok})."
                    ),
                    details={
                        "domain": detected_domain,
                        "primary_typeface": actual_primary_font,
                        "endcard_duration_sec": ec_dur,
                        "max_wpm_detected": max_wpm,
                    },
                ))

        # Verify OpenTimelineIO & Cross-Department Shoot-Day Coherence (PM-FEAT-034)
        otio_spec = getattr(bible, "master_otio_coherence", None)
        if otio_spec is not None:
            expected_otio = get_domain_otio_coherence_spec(detected_domain)
            shoot_ready = bool(getattr(otio_spec, "shoot_day_ready", False))
            coh_score = float(getattr(otio_spec, "coherence_score", 0.0) or 0.0)
            conflicts_cnt = int(getattr(otio_spec, "conflicts_count", 0) or 0)
            if not shoot_ready or conflicts_cnt > 0 or coh_score < 85.0:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="domain_otio_coherence_readiness",
                    message=(
                        f"OTIO cross-department coherence gate blocked shoot-day readiness for domain '{detected_domain}' "
                        f"(shoot_day_ready={shoot_ready}, score={coh_score:.1f}, conflicts={conflicts_cnt})."
                    ),
                    suggested_fix="Reconcile cross-department conflicts via get_domain_otio_coherence_spec(bible).",
                ))
                score -= 2.0
            else:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="domain_otio_coherence_readiness",
                    message=(
                        f"OTIO 7-track cross-department coherence verified for domain '{detected_domain}' "
                        f"(shoot_day_ready=True, coherence_score={coh_score:.1f}, "
                        f"focal_tol<={expected_otio.get('focal_delta_mm_max', 15.0)}mm, "
                        f"kelvin_tol<={expected_otio.get('kelvin_delta_max', 1500.0)}K)."
                    ),
                    details={
                        "domain": detected_domain,
                        "shoot_day_ready": True,
                        "coherence_score": coh_score,
                        "conflicts_count": conflicts_cnt,
                    },
                ))

        # Verify Live-Render Job QA & Domain Alignment (PM-FEAT-035)
        rj_spec = getattr(bible, "master_render_jobs", None)
        if rj_spec is not None:
            expected_rj = get_domain_render_job_spec(detected_domain)
            overall_qa = float(getattr(rj_spec, "overall_qa_score", 0.0) or 0.0)
            assembly_ready = bool(getattr(rj_spec, "assembly_ready", False))
            if overall_qa < 90.0 or not assembly_ready:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="domain_render_qa_calibration",
                    message=(
                        f"MasterRenderJobManifest failed domain '{detected_domain}' QA threshold "
                        f"(overall_qa_score={overall_qa:.1f} < 90.0 or assembly_ready={assembly_ready})."
                    ),
                    suggested_fix="Promote higher-scoring takes or recalibrate via get_domain_render_job_spec(bible).",
                ))
                score -= 1.5
            else:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="domain_render_qa_calibration",
                    message=(
                        f"Domain-calibrated Live-Render QA verified for '{detected_domain}' "
                        f"(overall_qa_score={overall_qa:.1f} >= 90.0, min_temporal={expected_rj.get('min_temporal_stability', 90.0)}, "
                        f"min_ref_fidelity={expected_rj.get('min_reference_fidelity', 91.0)})."
                    ),
                    details={
                        "domain": detected_domain,
                        "overall_qa_score": overall_qa,
                        "assembly_ready": assembly_ready,
                    },
                ))

        # Verify Executive Director's Treatment & Pitch Lookbook Alignment (PM-FEAT-036)
        pt_spec = getattr(bible, "master_pitch_treatment", None)
        if pt_spec is not None:
            expected_pt = get_domain_pitch_treatment_spec(detected_domain)
            dir_stmt = str(getattr(pt_spec, "executive_director_statement", "") or "").strip()
            aud_hook = str(getattr(pt_spec, "target_audience_hook", "") or "").strip()
            slides = list(getattr(pt_spec, "slides", None) or [])
            slide_types = {
                str(getattr(getattr(sl, "slide_type", None), "value", getattr(sl, "slide_type", ""))).lower()
                for sl in slides
            }
            has_roi = "budget_roi_summary" in slide_types
            if not dir_stmt or not aud_hook or len(slides) < 5 or not has_roi:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="domain_pitch_treatment_calibration",
                    message=(
                        f"MasterPitchTreatmentSpec incomplete for domain '{detected_domain}' "
                        f"(statement={bool(dir_stmt)}, hook={bool(aud_hook)}, slides={len(slides)}, has_budget_roi={has_roi})."
                    ),
                    suggested_fix="Compile Executive Treatment via compile_pitch_treatment(bible, domain_calibration=get_domain_pitch_treatment_spec(bible)).",
                ))
                score -= 1.5
            else:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="domain_pitch_treatment_calibration",
                    message=(
                        f"Executive Director's Treatment calibrated for '{detected_domain}' "
                        f"(tone='{expected_pt.get('executive_tone', '')}', slides={len(slides)}, budget_roi_summary=True)."
                    ),
                    details={
                        "domain": detected_domain,
                        "slides_count": len(slides),
                        "hero_kpi_focus": expected_pt.get("hero_kpi_focus", ""),
                    },
                ))

        # Verify SMPTE IMF OV Picture Deduplication & Domain Alignment (PM-FEAT-037)
        imf_spec = getattr(bible, "master_imf_dcp", None)
        if imf_spec is not None:
            expected_imf = get_domain_imf_dcp_profile(detected_domain)
            imf_cpls = list(getattr(imf_spec, "cpls", None) or [])
            loc_manifest = getattr(bible, "localization_manifest", None)
            reframe_manifest = getattr(bible, "master_reframe_manifest", None) or getattr(bible, "reframe_manifest", None)
            has_locales = bool(loc_manifest and getattr(loc_manifest, "locales", None))
            has_cutdowns = bool(reframe_manifest and (getattr(reframe_manifest, "cutdowns", None) or getattr(reframe_manifest, "cutdown_versions", None)))
            has_supplemental_scope = len(imf_cpls) > 1 or has_locales or has_cutdowns
            reuse_pct = float(getattr(imf_spec, "deduplicated_picture_reuse_pct", 0.0) or 0.0)
            if has_supplemental_scope and reuse_pct <= 0.0:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="domain_imf_dcp_calibration",
                    message=(
                        f"MasterImfDcpManifest for domain '{detected_domain}' has supplemental scope "
                        f"(cpls={len(imf_cpls)}, locales={has_locales}, cutdowns={has_cutdowns}) but "
                        f"deduplicated_picture_reuse_pct={reuse_pct:.1f}% <= 0.0%."
                    ),
                    suggested_fix="Reuse OV picture essence UUIDs across supplemental CPLs via compile_imf_dcp_manifest().",
                ))
                score -= 1.5
            else:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="domain_imf_dcp_calibration",
                    message=(
                        f"SMPTE IMF & DCI DCP calibrated for '{detected_domain}' "
                        f"(profile={expected_imf.get('application_profile', '')}, cpls={len(imf_cpls)}, "
                        f"deduplicated_picture_reuse_pct={reuse_pct:.1f}%)."
                    ),
                    details={
                        "domain": detected_domain,
                        "cpls_count": len(imf_cpls),
                        "deduplicated_picture_reuse_pct": reuse_pct,
                    },
                ))

        # Verify Voice Casting Register/Pace & AD Ducking Protection (PM-FEAT-038)
        vd_spec = getattr(bible, "master_voice_ducking", None)
        if vd_spec is not None:
            expected_vd = get_domain_voice_ducking_profile(detected_domain)
            expected_reg = str(expected_vd.get("vocal_register", "") or "").upper()
            roster = list(getattr(vd_spec, "casting_roster", None) or [])
            roster_regs = {
                str(getattr(getattr(p, "vocal_register", None), "value", getattr(p, "vocal_register", ""))).upper()
                for p in roster
            }
            music_duck_db = float(getattr(vd_spec, "default_music_duck_db", 0.0) or 0.0)
            acc_spec = getattr(bible, "master_accessibility_spec", None)
            has_ad_cues = bool(acc_spec and int(getattr(acc_spec, "total_ad_cues", 0) or 0) > 0)
            ad_kfs = [
                kf
                for sp in (getattr(vd_spec, "scene_profiles", None) or [])
                for kf in (getattr(sp, "ducking_keyframes", None) or [])
                if "AD" in str(getattr(kf, "trigger_stem", "")).upper()
                or "AUDIO_DESC" in str(getattr(kf, "trigger_stem", "")).upper()
            ]
            ad_protected = (not has_ad_cues) or any(float(getattr(kf, "attenuation_db", 0.0) or 0.0) < 0.0 for kf in ad_kfs)
            reg_ok = bool(roster_regs) and (not expected_reg or expected_reg in roster_regs)
            pace_ok = all(float(getattr(p, "target_wpm", 0.0) or 0.0) <= 150.0 for p in roster)
            if not reg_ok or not pace_ok or music_duck_db >= 0.0 or not ad_protected:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="domain_voice_ducking_calibration",
                    message=(
                        f"MasterVoiceDuckingManifest misaligned for domain '{detected_domain}' "
                        f"(expected_register={expected_reg}, roster_registers={sorted(roster_regs)}, "
                        f"music_duck_db={music_duck_db:.1f}, ad_protected={ad_protected})."
                    ),
                    suggested_fix="Calibrate vocal register, WPM pace (<=150), and AD ducking protection via get_domain_voice_ducking_profile().",
                ))
                score -= 1.5
            else:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="domain_voice_ducking_calibration",
                    message=(
                        f"Voice Casting & Sidechain Ducking calibrated for '{detected_domain}' "
                        f"(register={expected_reg}, music_duck={music_duck_db:.1f} dB, ad_ducking_kfs={len(ad_kfs)})."
                    ),
                    details={
                        "domain": detected_domain,
                        "expected_register": expected_reg,
                        "music_duck_db": music_duck_db,
                        "ad_ducking_keyframes": len(ad_kfs),
                    },
                ))

        # Verify Colorist Scopes Signal Standard & CIEDE2000 Domain Calibration (PM-FEAT-039)
        cs_spec = getattr(bible, "master_color_scopes", None)
        if cs_spec is not None:
            expected_cs = get_domain_color_scopes_profile(detected_domain)
            expected_std = str(expected_cs.get("signal_standard", "") or "").lower()
            expected_de = float(expected_cs.get("max_delta_e_ceiling", 3.0) or 3.0)
            expected_ev = float(expected_cs.get("max_exposure_jump_stops", 0.75) or 0.75)
            actual_std = str(
                getattr(getattr(cs_spec, "signal_standard", None), "value", getattr(cs_spec, "signal_standard", ""))
            ).lower()
            actual_de = float(getattr(cs_spec, "max_delta_e_ceiling", 3.0) or 3.0)
            actual_ev = float(getattr(cs_spec, "max_exposure_jump_stops", 0.75) or 0.75)
            if actual_de > expected_de + 0.01 or actual_ev > expected_ev + 0.01 or (expected_std and actual_std != expected_std):
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="domain_color_scopes_calibration",
                    message=(
                        f"MasterColorScopesManifest misaligned for domain '{detected_domain}' "
                        f"(std={actual_std} vs {expected_std}, dE_ceil={actual_de:.2f} vs {expected_de:.2f}, "
                        f"ev_ceil={actual_ev:.2f} vs {expected_ev:.2f})."
                    ),
                    suggested_fix="Calibrate master_color_scopes via get_domain_color_scopes_profile().",
                ))
                score -= 1.5
            else:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="domain_color_scopes_calibration",
                    message=(
                        f"Colorist Finishing Scopes calibrated for '{detected_domain}' "
                        f"(std={actual_std}, dE2000<={actual_de:.2f}, EV<={actual_ev:.2f})."
                    ),
                    details={
                        "domain": detected_domain,
                        "signal_standard": actual_std,
                        "max_delta_e_ceiling": actual_de,
                        "max_exposure_jump_stops": actual_ev,
                    },
                ))

        # Verify RFC 8493 BagIt Retention Tier & Rights Window Domain Calibration (PM-FEAT-040)
        av_spec = getattr(bible, "master_archive_vault", None)
        if av_spec is not None:
            expected_av = get_domain_archive_vault_profile(detected_domain)
            expected_tier = str(expected_av.get("retention_tier", "") or "").lower()
            actual_tier = str(
                getattr(getattr(av_spec, "retention_tier", None), "value", getattr(av_spec, "retention_tier", ""))
            ).lower()
            rights_iso = str(getattr(av_spec, "rights_expiry_iso", "") or "").strip()
            if (expected_tier and actual_tier != expected_tier) or not rights_iso:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.HIGH,
                    category="domain_archive_vault_calibration",
                    message=(
                        f"MasterArchiveVaultManifest misaligned for domain '{detected_domain}' "
                        f"(retention_tier={actual_tier} vs {expected_tier}, rights_expiry_iso={rights_iso!r})."
                    ),
                    suggested_fix="Calibrate master_archive_vault retention tier & rights window via get_domain_archive_vault_profile().",
                ))
                score -= 1.5
            else:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="domain_archive_vault_calibration",
                    message=(
                        f"RFC 8493 Archive Vault calibrated for '{detected_domain}' "
                        f"(retention_tier={actual_tier}, rights_expiry={rights_iso})."
                    ),
                    details={
                        "domain": detected_domain,
                        "retention_tier": actual_tier,
                        "rights_expiry_iso": rights_iso,
                    },
                ))

        # Verify domain cross-alignment across color/optical/reframe/QC specs
        explicit_arch = getattr(bible, "domain_archetype", None)
        if explicit_arch is not None:
            explicit_str = str(getattr(explicit_arch, "value", explicit_arch)).lower()
            if explicit_str == detected_domain:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="domain_cross_alignment",
                    message=f"Domain cross-alignment verified: explicit domain_archetype '{explicit_str}' matches strategic brief classification.",
                    details={"domain_archetype": explicit_str},
                ))

        score = max(0.0, min(25.0, round(score, 2)))
        summary = f"Strategist review completed with score {score}/25.0 (Domain: {detected_domain})."
        return PersonaReviewResult(
            persona=CouncilPersona.COUNCIL_STRATEGIST,
            score=score,
            findings=findings,
            summary=summary,
        )

    def _review_ux_designer(
        self,
        bible: Optional[MasterProductionBible],
        bundle: Optional[ProductionBundle],
        output_dir: Optional[Path] = None,
    ) -> PersonaReviewResult:
        """Evaluates viewBox geometry, SMPTE safe guides, and visual storyboard plate completeness."""
        findings: List[CouncilFinding] = []
        score = 25.0

        if bible is None or not bible.scenes:
            return PersonaReviewResult(
                persona=CouncilPersona.COUNCIL_UX_DESIGNER,
                score=0.0,
                findings=[],
                summary="UX Designer review failed: no scenes."
            )

        for scene in bible.scenes:
            svg = ""
            kf = getattr(scene, "keyframe_spec", None)
            if kf and hasattr(kf, "svg_markup") and kf.svg_markup:
                svg = kf.svg_markup or ""
            elif bundle and bundle.visual_plates:
                svg = bundle.visual_plates.get(f"scene_{scene.scene_index}", "")

            if svg:
                # If svg is a path to an SVG file, load the content
                if svg.endswith(".svg") or (len(svg) < 500 and Path(svg).is_file()):
                    try:
                        p = Path(svg)
                        if p.is_file():
                            svg = p.read_text(encoding="utf-8")
                    except Exception:
                        pass

                # Check viewBox attribute
                if not re.search(r'viewBox=["\']\s*0\s+0\s+\d+(\.\d+)?\s+\d+(\.\d+)?\s*["\']', svg):
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.MEDIUM,
                        category="viewbox_geometry",
                        message=f"Scene {scene.scene_index} SVG keyframe lacks standard valid viewBox attribute.",
                        suggested_fix="Render SVG keyframe with standard viewBox='0 0 1920 1080'."
                    ))
                    score -= 2.0

                # Check safe guides
                has_action_safe = "safe-guide-action" in svg or 'stroke-dasharray="8 6"' in svg or 'stroke-dasharray="6,6"' in svg
                has_title_safe = "safe-guide-title" in svg or 'stroke-dasharray="4 4"' in svg or 'stroke-dasharray="3,3"' in svg
                if not (has_action_safe and has_title_safe):
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.LOW,
                        category="safe_guides",
                        message=f"Scene {scene.scene_index} SVG keyframe missing SMPTE action-safe or title-safe guide rects.",
                        suggested_fix="Enable show_safe_guides=True when rendering keyframe SVGs."
                    ))
                    score -= 1.5

        # Verify compiled storyboard HTML transport controls if present (or compile in temp dir for raw bible audits)
        html_path = (
            Path(bundle.storyboard_html_path)
            if (bundle and bundle.storyboard_html_path)
            else (Path(output_dir) / "storyboard_preview.html" if output_dir else None)
        )
        html_content: Optional[str] = None
        if html_path and html_path.is_file():
            try:
                html_content = html_path.read_text(encoding="utf-8")
            except Exception:
                html_content = None
        else:
            try:
                with tempfile.TemporaryDirectory() as tmp_compile_dir:
                    compile_target = bundle.model_copy(deep=True) if bundle is not None else bible
                    compiled_path = compile_storyboard_html(compile_target, output_dir=tmp_compile_dir)
                    if compiled_path and Path(compiled_path).is_file():
                        html_content = Path(compiled_path).read_text(encoding="utf-8")
            except Exception:
                html_content = None

        if html_content:
            try:
                if 'id="btn-play-animatic"' not in html_content or 'id="smpte-timecode"' not in html_content:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.MEDIUM,
                        category="animatic_transport",
                        message="Compiled storyboard preview HTML lacks interactive play transport or SMPTE timecode display.",
                        suggested_fix="Ensure compile_storyboard_html generates #btn-play-animatic and #smpte-timecode controls."
                    ))
                    score -= 2.0
                if 'id="btn-loop-animatic"' not in html_content or "jumpToBeat(" not in html_content:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.LOW,
                        category="animatic_transport",
                        message="Compiled storyboard preview HTML lacks continuous loop playback toggle button (#btn-loop-animatic) or jumpToBeat controls.",
                        suggested_fix="Ensure compile_storyboard_html generates #btn-loop-animatic and jumpToBeat handlers."
                    ))
                    score -= 1.0
                if 'role="tablist"' not in html_content or "cinema-toast" not in html_content:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.LOW,
                        category="animatic_accessibility",
                        message="Compiled storyboard preview HTML lacks accessible tablist semantics or non-blocking cinema-toast container.",
                        suggested_fix="Ensure compile_storyboard_html generates role='tablist' and #cinema-toast elements."
                    ))
                    score -= 1.0
                if 'id="btn-viewfinder-animatic"' not in html_content and 'id="animatic-viewfinder-overlay"' not in html_content:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.LOW,
                        category="animatic_viewfinder",
                        message="Compiled storyboard preview HTML lacks optical viewfinder overlay or safe guide toggle (#btn-viewfinder-animatic).",
                        suggested_fix="Ensure compile_storyboard_html generates #btn-viewfinder-animatic and #animatic-viewfinder-overlay controls."
                    ))
                    score -= 1.0
                if 'id="btn-vp-stage-animatic"' not in html_content and 'id="animatic-vp-stage-modal"' not in html_content:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.LOW,
                        category="animatic_virtual_production",
                        message="Compiled storyboard preview HTML lacks virtual production stage modal (#animatic-vp-stage-modal).",
                        suggested_fix="Ensure compile_storyboard_html generates #btn-vp-stage-animatic and #animatic-vp-stage-modal controls."
                    ))
                    score -= 1.0
                if 'id="btn-moco-animatic"' not in html_content and 'id="animatic-moco-hud"' not in html_content:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.LOW,
                        category="animatic_moco_hud",
                        message="Compiled storyboard preview HTML lacks interactive MoCo kinematics HUD (#animatic-moco-hud / #btn-moco-animatic).",
                        suggested_fix="Ensure compile_storyboard_html generates #btn-moco-animatic and #animatic-moco-hud controls."
                    ))
                    score -= 1.0
                if 'id="btn-gaffer-animatic"' not in html_content and 'id="animatic-gaffer-hud"' not in html_content:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.LOW,
                        category="animatic_gaffer_hud",
                        message="Compiled storyboard preview HTML lacks interactive studio gaffer HUD (#animatic-gaffer-hud / #btn-gaffer-animatic).",
                        suggested_fix="Ensure compile_storyboard_html generates #btn-gaffer-animatic and #animatic-gaffer-hud controls."
                    ))
                    score -= 1.0

                if 'id="btn-dof-animatic"' not in html_content and 'id="animatic-dof-hud"' not in html_content:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.LOW,
                        category="animatic_dof_hud",
                        message="Compiled storyboard preview HTML lacks interactive optical DoF HUD (#animatic-dof-hud / #btn-dof-animatic).",
                        suggested_fix="Ensure compile_storyboard_html generates #btn-dof-animatic and #animatic-dof-hud controls."
                    ))
                    score -= 1.0
                else:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.INFO,
                        category="animatic_dof_hud",
                        message="Optical Depth-of-Field (DoF) interactive HUD verified in dark-room animatic (#btn-dof-animatic / #animatic-dof-hud [F]).",
                    ))

                if 'id="btn-dit-lut-animatic"' not in html_content and 'id="animatic-dit-lut-hud"' not in html_content:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.LOW,
                        category="animatic_dit_lut_hud",
                        message="Compiled storyboard preview HTML lacks interactive DIT 3D LUT HUD (#animatic-dit-lut-hud / #btn-dit-lut-animatic).",
                        suggested_fix="Ensure compile_storyboard_html generates #btn-dit-lut-animatic and #animatic-dit-lut-hud controls."
                    ))
                    score -= 1.0
                else:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.INFO,
                        category="animatic_dit_lut_hud",
                        message="DIT 3D LUT Color Science & Film Emulation Suite HUD verified in dark-room animatic (#btn-dit-lut-animatic / #animatic-dit-lut-hud [L]).",
                    ))

                if 'id="btn-spatial-animatic"' not in html_content and 'id="animatic-spatial-hud"' not in html_content:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.LOW,
                        category="animatic_spatial_audio_hud",
                        message="Compiled storyboard preview HTML lacks interactive spatial audio HUD (#animatic-spatial-hud / #btn-spatial-animatic).",
                        suggested_fix="Ensure compile_storyboard_html generates #btn-spatial-animatic and #animatic-spatial-hud controls."
                    ))
                    score -= 1.0
                else:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.INFO,
                        category="animatic_spatial_audio_hud",
                        message="Spatial Audio & 7.1.4 Binaural Soundfield HUD verified in dark-room animatic (#btn-spatial-animatic / #animatic-spatial-hud [S]).",
                    ))

                if 'id="btn-vfx-animatic"' not in html_content and 'id="animatic-vfx-hud"' not in html_content:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.LOW,
                        category="animatic_vfx_hud",
                        message="Compiled storyboard preview HTML lacks interactive multi-pass VFX compositing HUD (#animatic-vfx-hud / #btn-vfx-animatic).",
                        suggested_fix="Ensure compile_storyboard_html generates #btn-vfx-animatic and #animatic-vfx-hud controls."
                    ))
                    score -= 1.0
                else:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.INFO,
                        category="animatic_vfx_hud",
                        message="Advanced Multi-Pass VFX Compositing Manifest HUD verified in dark-room animatic (#btn-vfx-animatic / #animatic-vfx-hud [X]).",
                    ))

                if 'id="btn-hdr-animatic"' not in html_content and 'id="animatic-hdr-hud"' not in html_content:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.LOW,
                        category="animatic_hdr_hud",
                        message="Compiled storyboard preview HTML lacks interactive HDR Broadcast Color Volume HUD (#animatic-hdr-hud / #btn-hdr-animatic).",
                        suggested_fix="Ensure compile_storyboard_html generates #btn-hdr-animatic, #animatic-hdr-hud, and #hdr-waveform-canvas."
                    ))
                    score -= 1.0
                else:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.INFO,
                        category="animatic_hdr_hud",
                        message="HDR Broadcast Color Volume & Waveform Monitor HUD verified in dark-room animatic (#btn-hdr-animatic / #animatic-hdr-hud [H]).",
                    ))

                if 'id="btn-stripboard-animatic"' not in html_content and 'id="animatic-stripboard-hud"' not in html_content:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.LOW,
                        category="animatic_stripboard_hud",
                        message="Compiled storyboard preview HTML lacks interactive 1st AD Stripboard Production Scheduler HUD (#animatic-stripboard-hud / #btn-stripboard-animatic).",
                        suggested_fix="Ensure compile_storyboard_html generates #btn-stripboard-animatic, #animatic-stripboard-hud, and #dood-talent-table."
                    ))
                    score -= 1.0
                else:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.INFO,
                        category="animatic_stripboard_hud",
                        message="1st AD Script Breakdown & Stripboard Production Console HUD verified in dark-room animatic (#btn-stripboard-animatic / #animatic-stripboard-hud [B]).",
                    ))

                if ('id="btn-film-animatic"' not in html_content and 'id="animatic-film-hud"' not in html_content) or (
                    'id="btn-download-film-dctl"' not in html_content or 'id="btn-download-film-ale"' not in html_content
                ):
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.LOW,
                        category="animatic_film_hud",
                        message="Compiled storyboard preview HTML lacks interactive Film Stock Emulation HUD (#animatic-film-hud, #btn-film-animatic, #btn-download-film-dctl, #btn-download-film-ale).",
                        suggested_fix="Ensure compile_storyboard_html generates #btn-film-animatic, #animatic-film-hud, #btn-download-film-dctl, and #btn-download-film-ale."
                    ))
                    score -= 1.0
                else:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.INFO,
                        category="animatic_film_hud",
                        message="Physical Film Stock Emulation HUD verified in dark-room animatic (#btn-film-animatic / #animatic-film-hud [E], DCTL & ALE downloads).",
                    ))

                if ('id="btn-slate-animatic"' not in html_content and 'id="animatic-slate-hud"' not in html_content) or (
                    'id="btn-download-mhl-xml"' not in html_content or 'id="btn-download-sound-ale"' not in html_content or 'id="btn-download-slate-csv"' not in html_content
                ):
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.LOW,
                        category="animatic_slate_hud",
                        message="Compiled storyboard preview HTML lacks interactive Digital Clapper Slate HUD (#animatic-slate-hud, #btn-slate-animatic, #btn-download-mhl-xml, #btn-download-sound-ale, #btn-download-slate-csv).",
                        suggested_fix="Ensure compile_storyboard_html generates #btn-slate-animatic, #animatic-slate-hud, #btn-download-mhl-xml, #btn-download-sound-ale, and #btn-download-slate-csv."
                    ))
                    score -= 1.0
                else:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.INFO,
                        category="animatic_slate_hud",
                        message="SMPTE 12M Digital Clapper Slate HUD verified in dark-room animatic (#btn-slate-animatic / #animatic-slate-hud [T], ASC-MHL, Sound ALE & Slate CSV downloads).",
                    ))

                if ('id="btn-drone-animatic"' not in html_content and 'id="animatic-drone-hud"' not in html_content) or (
                    'id="btn-download-drone-kml"' not in html_content or 'id="btn-download-drone-gpx"' not in html_content or 'id="btn-download-drone-csv"' not in html_content
                ):
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.LOW,
                        category="animatic_drone_hud",
                        message="Compiled storyboard preview HTML lacks interactive Drone Flight Path HUD (#animatic-drone-hud, #btn-drone-animatic, #btn-download-drone-kml, #btn-download-drone-gpx, #btn-download-drone-csv).",
                        suggested_fix="Ensure compile_storyboard_html generates #btn-drone-animatic, #animatic-drone-hud, #btn-download-drone-kml, #btn-download-drone-gpx, and #btn-download-drone-csv."
                    ))
                    score -= 1.0
                else:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.INFO,
                        category="animatic_drone_hud",
                        message="Aerial Drone Flight Path HUD verified in dark-room animatic (#btn-drone-animatic / #animatic-drone-hud [D], KML, GPX & CSV downloads).",
                    ))

                if ('id="btn-aicp-animatic"' not in html_content and 'id="animatic-aicp-hud"' not in html_content) or (
                    'id="btn-download-aicp-csv"' not in html_content or 'id="btn-download-aicp-json"' not in html_content or 'id="btn-download-aicp-md"' not in html_content
                ):
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.LOW,
                        category="animatic_aicp_hud",
                        message="Compiled storyboard preview HTML lacks interactive AICP Commercial Production Bid HUD (#animatic-aicp-hud, #btn-aicp-animatic, #btn-download-aicp-csv, #btn-download-aicp-json, #btn-download-aicp-md).",
                        suggested_fix="Ensure compile_storyboard_html generates #btn-aicp-animatic, #animatic-aicp-hud, #btn-download-aicp-csv, #btn-download-aicp-json, and #btn-download-aicp-md."
                    ))
                    score -= 1.0
                else:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.INFO,
                        category="animatic_aicp_hud",
                        message="AICP Commercial Production Bid HUD verified in dark-room animatic (#btn-aicp-animatic / #animatic-aicp-hud [A], CSV, JSON & Markdown downloads).",
                    ))

                # Full compiled animatic controls & keybinding governance checks
                is_full_animatic_html = (
                    "addEventListener('keydown'" in html_content
                    or 'addEventListener("keydown"' in html_content
                    or "OMNI MOVIE DIRECTOR" in html_content
                )

                if is_full_animatic_html:
                    if 'id="btn-toggle-mixer"' not in html_content or 'id="animatic-audio-mixer"' not in html_content:
                        findings.append(CouncilFinding(
                            severity=CouncilFindingSeverity.LOW,
                            category="animatic_audio_mixer",
                            message="Compiled storyboard preview HTML lacks interactive Audio Mixing Console (#btn-toggle-mixer / #animatic-audio-mixer).",
                            suggested_fix="Ensure compile_storyboard_html renders #btn-toggle-mixer and #animatic-audio-mixer.",
                        ))
                        score -= 0.5
                    else:
                        findings.append(CouncilFinding(
                            severity=CouncilFindingSeverity.INFO,
                            category="animatic_audio_mixer",
                            message="Interactive Audio Mixing Console verified (#btn-toggle-mixer / #animatic-audio-mixer [M]).",
                        ))

                    if 'id="btn-cc-animatic"' not in html_content or 'id="animatic-cc-hud"' not in html_content:
                        findings.append(CouncilFinding(
                            severity=CouncilFindingSeverity.LOW,
                            category="animatic_cc_hud",
                            message="Compiled storyboard preview HTML lacks Closed Captions HUD (#btn-cc-animatic / #animatic-cc-hud).",
                            suggested_fix="Ensure compile_storyboard_html renders #btn-cc-animatic and #animatic-cc-hud.",
                        ))
                        score -= 0.5
                    else:
                        findings.append(CouncilFinding(
                            severity=CouncilFindingSeverity.INFO,
                            category="animatic_cc_hud",
                            message="Closed Captions HUD verified (#btn-cc-animatic / #animatic-cc-hud [C]).",
                        ))

                    if 'id="btn-export-bible"' not in html_content:
                        findings.append(CouncilFinding(
                            severity=CouncilFindingSeverity.LOW,
                            category="animatic_export_bible",
                            message="Compiled storyboard preview HTML lacks Export Production Bible button (#btn-export-bible).",
                            suggested_fix="Ensure compile_storyboard_html renders #btn-export-bible.",
                        ))
                        score -= 0.5
                    else:
                        findings.append(CouncilFinding(
                            severity=CouncilFindingSeverity.INFO,
                            category="animatic_export_bible",
                            message="Export Production Bible JSON control verified (#btn-export-bible).",
                        ))

                    # PM-FEAT-021 Reframe HUD check
                    if 'id="btn-reframe-animatic"' not in html_content and 'id="animatic-reframe-hud"' not in html_content:
                        findings.append(CouncilFinding(
                            severity=CouncilFindingSeverity.LOW,
                            category="animatic_reframe_hud",
                            message="Compiled storyboard preview HTML lacks Multi-Aspect Social Reframe HUD (#btn-reframe-animatic / #animatic-reframe-hud).",
                            suggested_fix="Ensure compile_storyboard_html renders #btn-reframe-animatic and #animatic-reframe-hud [R].",
                        ))
                        score -= 0.5
                    else:
                        findings.append(CouncilFinding(
                            severity=CouncilFindingSeverity.INFO,
                            category="animatic_reframe_hud",
                            message="Multi-Aspect Social Reframe HUD verified (#btn-reframe-animatic / #animatic-reframe-hud [R]).",
                        ))

                    # PM-FEAT-022 Broadcast QC HUD check
                    if 'id="btn-qc-animatic"' not in html_content and 'id="animatic-qc-hud"' not in html_content:
                        findings.append(CouncilFinding(
                            severity=CouncilFindingSeverity.LOW,
                            category="animatic_qc_hud",
                            message="Compiled storyboard preview HTML lacks Broadcast Technical QC HUD (#btn-qc-animatic / #animatic-qc-hud).",
                            suggested_fix="Ensure compile_storyboard_html renders #btn-qc-animatic and #animatic-qc-hud [Q].",
                        ))
                        score -= 0.5
                    else:
                        findings.append(CouncilFinding(
                            severity=CouncilFindingSeverity.INFO,
                            category="animatic_qc_hud",
                            message="Broadcast Technical QC & Clearance HUD verified (#btn-qc-animatic / #animatic-qc-hud [Q]).",
                        ))

                    # PM-FEAT-023 180-Degree Blocking & Continuity HUD check
                    missing_blocking_ids = [
                        el_id
                        for el_id in ("animatic-blocking-hud", "btn-blocking-animatic", "blocking-floorplan-svg")
                        if f'id="{el_id}"' not in html_content
                    ]
                    if missing_blocking_ids:
                        findings.append(CouncilFinding(
                            severity=CouncilFindingSeverity.LOW,
                            category="animatic_blocking_hud",
                            message=f"Compiled storyboard preview HTML lacks 180-Degree Blocking HUD element(s): {', '.join('#' + i for i in missing_blocking_ids)}.",
                            suggested_fix="Ensure compile_storyboard_html renders #btn-blocking-animatic, #animatic-blocking-hud, and #blocking-floorplan-svg [W].",
                        ))
                        score -= 1.0
                    else:
                        findings.append(CouncilFinding(
                            severity=CouncilFindingSeverity.INFO,
                            category="animatic_blocking_hud",
                            message="180-Degree Blocking & Continuity Floorplan HUD verified (#btn-blocking-animatic / #animatic-blocking-hud / #blocking-floorplan-svg [W]).",
                        ))

                    # PM-FEAT-024 Client Review & Frame Pin Annotation HUD check
                    missing_review_ids = [
                        el_id
                        for el_id in ("animatic-review-hud", "btn-review-animatic", "review-pin-stage")
                        if f'id="{el_id}"' not in html_content
                    ]
                    if missing_review_ids:
                        findings.append(CouncilFinding(
                            severity=CouncilFindingSeverity.LOW,
                            category="animatic_review_hud",
                            message=f"Compiled storyboard preview HTML lacks Client Review & Frame Pin HUD element(s): {', '.join('#' + i for i in missing_review_ids)}.",
                            suggested_fix="Ensure compile_storyboard_html renders #btn-review-animatic, #animatic-review-hud, and #review-pin-stage [N].",
                        ))
                        score -= 1.0
                    else:
                        findings.append(CouncilFinding(
                            severity=CouncilFindingSeverity.INFO,
                            category="animatic_review_hud",
                            message="Client Review & Frame Pin Annotation HUD verified (#btn-review-animatic / #animatic-review-hud / #review-pin-stage [N]).",
                        ))

                    # PM-FEAT-025 C2PA Content Credentials & Provenance HUD check
                    missing_c2pa_ids = [
                        el_id
                        for el_id in ("animatic-c2pa-hud", "btn-c2pa-animatic", "c2pa-lineage-svg")
                        if f'id="{el_id}"' not in html_content
                    ]
                    if missing_c2pa_ids:
                        findings.append(CouncilFinding(
                            severity=CouncilFindingSeverity.LOW,
                            category="animatic_c2pa_hud",
                            message=f"Compiled storyboard preview HTML lacks C2PA Content Credentials HUD element(s): {', '.join('#' + i for i in missing_c2pa_ids)}.",
                            suggested_fix="Ensure compile_storyboard_html renders #btn-c2pa-animatic, #animatic-c2pa-hud, and #c2pa-lineage-svg [Y].",
                        ))
                        score -= 1.0
                    else:
                        findings.append(CouncilFinding(
                            severity=CouncilFindingSeverity.INFO,
                            category="animatic_c2pa_hud",
                            message="C2PA Content Credentials & Provenance Lineage HUD verified (#btn-c2pa-animatic / #animatic-c2pa-hud / #c2pa-lineage-svg [Y]).",
                        ))

                    # PM-FEAT-026 On-Set Safety Risk & Exclusion Perimeter HUD check
                    missing_safety_ids = [
                        el_id
                        for el_id in ("animatic-safety-hud", "btn-safety-animatic", "safety-perimeter-svg")
                        if f'id="{el_id}"' not in html_content
                    ]
                    if missing_safety_ids:
                        findings.append(CouncilFinding(
                            severity=CouncilFindingSeverity.LOW,
                            category="animatic_safety_hud",
                            message=f"Compiled storyboard preview HTML lacks On-Set Safety JSA HUD element(s): {', '.join('#' + i for i in missing_safety_ids)}.",
                            suggested_fix="Ensure compile_storyboard_html renders #btn-safety-animatic, #animatic-safety-hud, and #safety-perimeter-svg [Z].",
                        ))
                        score -= 1.0
                    else:
                        findings.append(CouncilFinding(
                            severity=CouncilFindingSeverity.INFO,
                            category="animatic_safety_hud",
                            message="On-Set Safety Risk & Exclusion Perimeter HUD verified (#btn-safety-animatic / #animatic-safety-hud / #safety-perimeter-svg [Z]).",
                        ))

                    # PM-FEAT-027 Multi-Territory Localization & ADR Dubbing HUD check
                    missing_loc_ids = [
                        el_id
                        for el_id in ("animatic-localization-hud", "btn-localization-animatic", "localization-lipsync-svg")
                        if f'id="{el_id}"' not in html_content
                    ]
                    if missing_loc_ids:
                        findings.append(CouncilFinding(
                            severity=CouncilFindingSeverity.LOW,
                            category="animatic_localization_hud",
                            message=f"Compiled storyboard preview HTML lacks Localization & ADR HUD element(s): {', '.join('#' + i for i in missing_loc_ids)}.",
                            suggested_fix="Ensure compile_storyboard_html renders #btn-localization-animatic, #animatic-localization-hud, and #localization-lipsync-svg [I].",
                        ))
                        score -= 1.0
                    else:
                        findings.append(CouncilFinding(
                            severity=CouncilFindingSeverity.INFO,
                            category="animatic_localization_hud",
                            message="Localization & ADR Dubbing HUD verified (#btn-localization-animatic / #animatic-localization-hud / #localization-lipsync-svg [I]).",
                        ))

                    # PM-FEAT-028 Editorial J-Cut/L-Cut Spotting & Beat-Grid HUD check
                    missing_spot_ids = [
                        el_id
                        for el_id in ("animatic-spotting-hud", "btn-spotting-animatic", "spotting-timeline-svg")
                        if f'id="{el_id}"' not in html_content
                    ]
                    if missing_spot_ids:
                        findings.append(CouncilFinding(
                            severity=CouncilFindingSeverity.LOW,
                            category="animatic_spotting_hud",
                            message=f"Compiled storyboard preview HTML lacks Editorial Spotting & Beat-Grid HUD element(s): {', '.join('#' + i for i in missing_spot_ids)}.",
                            suggested_fix="Ensure compile_storyboard_html renders #btn-spotting-animatic, #animatic-spotting-hud, and #spotting-timeline-svg [J].",
                        ))
                        score -= 1.0
                    else:
                        findings.append(CouncilFinding(
                            severity=CouncilFindingSeverity.INFO,
                            category="animatic_spotting_hud",
                            message="Editorial Spotting & Beat-Grid HUD verified (#btn-spotting-animatic / #animatic-spotting-hud / #spotting-timeline-svg [J]).",
                        ))

                    # PM-FEAT-029 S3D & Spatial Video HUD check
                    missing_s3d_ids = [
                        el_id
                        for el_id in ("modal-s3d-stereography", "btn-s3d-animatic")
                        if f'id="{el_id}"' not in html_content
                    ]
                    if missing_s3d_ids or "]" not in html_content:
                        findings.append(CouncilFinding(
                            severity=CouncilFindingSeverity.LOW,
                            category="animatic_s3d_hud",
                            message=f"Compiled storyboard HTML lacks S3D/Spatial Video HUD element(s): {', '.join('#' + i for i in missing_s3d_ids)} or hotkey ']'.",
                            suggested_fix="Ensure compile_storyboard_html renders #modal-s3d-stereography, #btn-s3d-animatic, and hotkey ']'.",
                        ))
                        score -= 1.0
                    else:
                        findings.append(CouncilFinding(
                            severity=CouncilFindingSeverity.INFO,
                            category="animatic_s3d_hud",
                            message="S3D & Spatial Video HUD verified (#btn-s3d-animatic / #modal-s3d-stereography / hotkey ']').",
                        ))

                    # PM-FEAT-030 Accessibility AD HUD check
                    missing_ad_ids = [
                        el_id
                        for el_id in ("modal-accessibility-ad", "btn-ad-animatic", "ad-scrubber-ribbon")
                        if f'id="{el_id}"' not in html_content
                    ]
                    if missing_ad_ids or "[" not in html_content:
                        findings.append(CouncilFinding(
                            severity=CouncilFindingSeverity.LOW,
                            category="animatic_accessibility_ad_hud",
                            message=f"Compiled storyboard HTML lacks Accessibility AD HUD element(s): {', '.join('#' + i for i in missing_ad_ids)} or hotkey '['.",
                            suggested_fix="Ensure compile_storyboard_html renders #modal-accessibility-ad, #btn-ad-animatic, #ad-scrubber-ribbon, and hotkey '['.",
                        ))
                        score -= 1.0
                    else:
                        findings.append(CouncilFinding(
                            severity=CouncilFindingSeverity.INFO,
                            category="animatic_accessibility_ad_hud",
                            message="Accessibility AD HUD verified (#btn-ad-animatic / #modal-accessibility-ad / #ad-scrubber-ribbon / hotkey '[').",
                        ))

                    # v2.16.0 Unified HUD Command Palette [/] check
                    missing_palette_ids = [
                        el_id
                        for el_id in ("modal-hud-command-palette", "btn-command-palette-animatic")
                        if f'id="{el_id}"' not in html_content
                    ]
                    if missing_palette_ids or "/" not in html_content:
                        findings.append(CouncilFinding(
                            severity=CouncilFindingSeverity.LOW,
                            category="animatic_command_palette_hud",
                            message=f"Compiled storyboard HTML lacks Unified HUD Command Palette element(s): {', '.join('#' + i for i in missing_palette_ids)} or hotkey '/'.",
                            suggested_fix="Ensure compile_storyboard_html renders #modal-hud-command-palette, #btn-command-palette-animatic, and hotkey '/'.",
                        ))
                        score -= 1.0
                    else:
                        findings.append(CouncilFinding(
                            severity=CouncilFindingSeverity.INFO,
                            category="animatic_command_palette_hud",
                            message="Unified HUD Command Palette verified (#btn-command-palette-animatic / #modal-hud-command-palette / hotkey '/').",
                        ))

                    # PM-FEAT-031 Art & Wardrobe Continuity Locker [\] HUD check
                    missing_art_ids = [
                        el_id
                        for el_id in ("modal-art-wardrobe-continuity", "btn-art-dept-animatic")
                        if f'id="{el_id}"' not in html_content
                    ]
                    if missing_art_ids:
                        findings.append(CouncilFinding(
                            severity=CouncilFindingSeverity.LOW,
                            category="animatic_art_wardrobe_hud",
                            message=f"Compiled storyboard HTML lacks Art & Wardrobe Continuity Locker HUD element(s): {', '.join('#' + i for i in missing_art_ids)}.",
                            suggested_fix="Ensure compile_storyboard_html renders #modal-art-wardrobe-continuity and #btn-art-dept-animatic [\\].",
                        ))
                        score -= 1.0
                    else:
                        findings.append(CouncilFinding(
                            severity=CouncilFindingSeverity.INFO,
                            category="animatic_art_wardrobe_hud",
                            message="Art & Wardrobe Continuity Locker HUD verified (#btn-art-dept-animatic / #modal-art-wardrobe-continuity / hotkey '\\').",
                        ))

                    # PM-FEAT-032 Render Economics & Take-Variant Inspector [;] HUD check
                    missing_econ_ids = [
                        el_id
                        for el_id in ("modal-render-economics", "btn-economics-animatic")
                        if f'id="{el_id}"' not in html_content
                    ]
                    if missing_econ_ids:
                        findings.append(CouncilFinding(
                            severity=CouncilFindingSeverity.LOW,
                            category="animatic_render_economics_hud",
                            message=f"Compiled storyboard HTML lacks Compute Economics & Take-Variant HUD element(s): {', '.join('#' + i for i in missing_econ_ids)}.",
                            suggested_fix="Ensure compile_storyboard_html renders #modal-render-economics and #btn-economics-animatic [;].",
                        ))
                        score -= 1.0
                    else:
                        findings.append(CouncilFinding(
                            severity=CouncilFindingSeverity.INFO,
                            category="animatic_render_economics_hud",
                            message="Compute Economics & Take-Variant Inspector HUD verified (#btn-economics-animatic / #modal-render-economics / hotkey ';').",
                        ))

                    # PM-FEAT-033 Motion Graphics, Supers & End-Card Studio [=] HUD & Command Palette [/] check
                    missing_mgs_ids = [
                        el_id
                        for el_id in ("modal-motion-graphics-studio", "btn-motion-gfx-animatic")
                        if f'id="{el_id}"' not in html_content
                    ]
                    has_mgs_palette = ("motiongfx" in html_content and "toggleMotionGfxHUD" in html_content)
                    if missing_mgs_ids or not has_mgs_palette:
                        findings.append(CouncilFinding(
                            severity=CouncilFindingSeverity.LOW,
                            category="animatic_motion_graphics_hud",
                            message=(
                                f"Compiled storyboard HTML lacks Motion Graphics Studio HUD element(s): "
                                f"{', '.join('#' + i for i in missing_mgs_ids) or 'Command Palette / entry'}."
                            ),
                            suggested_fix="Ensure compile_storyboard_html renders #modal-motion-graphics-studio, #btn-motion-gfx-animatic [=], and Command Palette [/] entry.",
                        ))
                        score -= 1.0
                    else:
                        findings.append(CouncilFinding(
                            severity=CouncilFindingSeverity.INFO,
                            category="animatic_motion_graphics_hud",
                            message="Motion Graphics, Supers & End-Card Studio HUD verified (#btn-motion-gfx-animatic / #modal-motion-graphics-studio / Command Palette '/' / hotkey '=').",
                        ))

                    # PM-FEAT-034 OpenTimelineIO (.otio) & Cross-Dept Coherence Matrix ['] HUD & Command Palette [/] check
                    missing_otio_ids = [
                        el_id
                        for el_id in ("modal-otio-coherence", "btn-otio-coherence-animatic")
                        if f'id="{el_id}"' not in html_content
                    ]
                    has_otio_palette = ("otiocoherence" in html_content and "toggleOtioCoherenceHUD" in html_content)
                    if missing_otio_ids or not has_otio_palette:
                        findings.append(CouncilFinding(
                            severity=CouncilFindingSeverity.LOW,
                            category="animatic_otio_coherence_hud",
                            message=(
                                f"Compiled storyboard HTML lacks OpenTimelineIO Coherence HUD element(s): "
                                f"{', '.join('#' + i for i in missing_otio_ids) or 'Command Palette / entry'}."
                            ),
                            suggested_fix="Ensure compile_storyboard_html renders #modal-otio-coherence, #btn-otio-coherence-animatic ['], and Command Palette [/] entry.",
                        ))
                        score -= 1.0
                    else:
                        findings.append(CouncilFinding(
                            severity=CouncilFindingSeverity.INFO,
                            category="animatic_otio_coherence_hud",
                            message="OpenTimelineIO (.otio) & Cross-Dept Coherence Matrix HUD verified (#btn-otio-coherence-animatic / #modal-otio-coherence / Command Palette '/' / hotkey ''').",
                        ))

                    # PM-FEAT-035 Live-Render Jobs, Take A/B/C QA & Mode B Frame-Anchor [`] HUD & Command Palette [/] check
                    missing_rj_ids = [
                        el_id
                        for el_id in ("modal-render-jobs", "btn-render-jobs-animatic", "render-anchor-svg")
                        if f'id="{el_id}"' not in html_content
                    ]
                    has_rj_palette = ("renderjobs" in html_content and "toggleRenderJobsHUD" in html_content)
                    if missing_rj_ids or not has_rj_palette:
                        findings.append(CouncilFinding(
                            severity=CouncilFindingSeverity.LOW,
                            category="animatic_render_jobs_hud",
                            message=(
                                f"Compiled storyboard HTML lacks Live-Render Jobs HUD element(s): "
                                f"{', '.join('#' + i for i in missing_rj_ids) or 'Command Palette / entry'}."
                            ),
                            suggested_fix="Ensure compile_storyboard_html renders #modal-render-jobs, #btn-render-jobs-animatic [`], #render-anchor-svg, and Command Palette 'renderjobs' entry.",
                        ))
                        score -= 1.0
                    else:
                        findings.append(CouncilFinding(
                            severity=CouncilFindingSeverity.INFO,
                            category="animatic_render_jobs_hud",
                            message="Live-Render Jobs & Frame-Anchor HUD verified (#btn-render-jobs-animatic / #modal-render-jobs / #render-anchor-svg / Command Palette 'renderjobs').",
                        ))

                    # PM-FEAT-036 Director's Pitch Treatment & Lookbook [-] HUD & Command Palette [/] check
                    missing_pt_ids = [
                        el_id
                        for el_id in ("modal-pitch-treatment", "btn-treatment-animatic")
                        if f'id="{el_id}"' not in html_content
                    ]
                    has_pt_palette = (
                        "treatment" in html_content
                        and "togglePitchTreatmentHUD" in html_content
                        and "safeguides" in html_content
                    )
                    if missing_pt_ids or not has_pt_palette:
                        findings.append(CouncilFinding(
                            severity=CouncilFindingSeverity.LOW,
                            category="animatic_pitch_treatment_hud",
                            message=(
                                f"Compiled storyboard HTML lacks Director's Pitch Treatment HUD element(s): "
                                f"{', '.join('#' + i for i in missing_pt_ids) or 'Command Palette (treatment/safeguides) entry'}."
                            ),
                            suggested_fix="Ensure compile_storyboard_html renders #modal-pitch-treatment, #btn-treatment-animatic [-], and Command Palette 'treatment' & 'safeguides' entries.",
                        ))
                        score -= 1.0
                    else:
                        findings.append(CouncilFinding(
                            severity=CouncilFindingSeverity.INFO,
                            category="animatic_pitch_treatment_hud",
                            message="Director's Pitch Treatment & Lookbook HUD verified (#btn-treatment-animatic / #modal-pitch-treatment / Command Palette 'treatment' & 'safeguides').",
                        ))

                    # PM-FEAT-037 SMPTE IMF & DCI Theatrical DCP HUD [}] & Command Palette [/] check
                    missing_imf_ids = [
                        el_id
                        for el_id in ("imfDcpModal", "btn-imf-dcp")
                        if f'id="{el_id}"' not in html_content
                    ]
                    has_imf_palette = ("'imfdcp'" in html_content or '"imfdcp"' in html_content) and "toggleImfDcpHUD" in html_content
                    if missing_imf_ids or not has_imf_palette:
                        findings.append(CouncilFinding(
                            severity=CouncilFindingSeverity.LOW,
                            category="animatic_imf_dcp_hud",
                            message=(
                                f"Compiled storyboard HTML lacks IMF/DCP HUD element(s): "
                                f"{', '.join('#' + i for i in missing_imf_ids) or 'Command Palette imfdcp entry'}."
                            ),
                            suggested_fix="Ensure compile_storyboard_html renders #imfDcpModal, #btn-imf-dcp [}], and Command Palette 'imfdcp' entry.",
                        ))
                        score -= 1.0
                    else:
                        findings.append(CouncilFinding(
                            severity=CouncilFindingSeverity.INFO,
                            category="animatic_imf_dcp_hud",
                            message="IMF Package & Theatrical DCP HUD verified (#btn-imf-dcp / #imfDcpModal / Command Palette 'imfdcp').",
                        ))

                    # PM-FEAT-038 Voice Casting, Viseme Lip-Sync & Sidechain Ducking HUD [{] & Command Palette [/] check
                    missing_vd_ids = [
                        el_id
                        for el_id in ("voiceDuckingModal", "btn-voice-ducking", "v219-ducking-svg")
                        if f'id="{el_id}"' not in html_content
                    ]
                    has_vd_palette = ("'voiceducking'" in html_content or '"voiceducking"' in html_content) and "toggleVoiceDuckingHUD" in html_content
                    if missing_vd_ids or not has_vd_palette:
                        findings.append(CouncilFinding(
                            severity=CouncilFindingSeverity.LOW,
                            category="animatic_voice_ducking_hud",
                            message=(
                                f"Compiled storyboard HTML lacks Voice Casting & Ducking HUD element(s): "
                                f"{', '.join('#' + i for i in missing_vd_ids) or 'Command Palette voiceducking entry'}."
                            ),
                            suggested_fix="Ensure compile_storyboard_html renders #voiceDuckingModal, #btn-voice-ducking [{], #v219-ducking-svg, and Command Palette 'voiceducking' entry.",
                        ))
                        score -= 1.0
                    else:
                        findings.append(CouncilFinding(
                            severity=CouncilFindingSeverity.INFO,
                            category="animatic_voice_ducking_hud",
                            message="Voice Casting & Sidechain Ducking HUD verified (#btn-voice-ducking / #voiceDuckingModal / #v219-ducking-svg / Command Palette 'voiceducking').",
                        ))

                    # PM-FEAT-039 Colorist Scopes, CIEDE2000 & A/B Wipe HUD [+] & Command Palette [/] check
                    missing_cs_ids = [
                        el_id
                        for el_id in ("colorScopesModal", "btn-color-scopes", "v220-scopes-svg", "v220-ab-wipe-stage")
                        if f'id="{el_id}"' not in html_content
                    ]
                    has_cs_palette = ("'colorscopes'" in html_content or '"colorscopes"' in html_content) and "toggleColorScopesHUD" in html_content
                    if missing_cs_ids or not has_cs_palette:
                        findings.append(CouncilFinding(
                            severity=CouncilFindingSeverity.LOW,
                            category="animatic_color_scopes_hud",
                            message=(
                                f"Compiled storyboard HTML lacks Colorist Scopes HUD element(s): "
                                f"{', '.join('#' + i for i in missing_cs_ids) or 'Command Palette colorscopes entry'}."
                            ),
                            suggested_fix="Ensure compile_storyboard_html renders #colorScopesModal, #btn-color-scopes [+], #v220-scopes-svg, #v220-ab-wipe-stage, and Command Palette 'colorscopes' entry.",
                        ))
                        score -= 1.0
                    else:
                        findings.append(CouncilFinding(
                            severity=CouncilFindingSeverity.INFO,
                            category="animatic_color_scopes_hud",
                            message="Colorist Scopes & A/B Wipe HUD verified (#btn-color-scopes / #colorScopesModal / #v220-scopes-svg / #v220-ab-wipe-stage / Command Palette 'colorscopes').",
                        ))

                    # PM-FEAT-040 RFC 8493 Archive Vault & Agency Handoff HUD [:] & Command Palette [/] check
                    missing_av_ids = [
                        el_id
                        for el_id in ("archiveVaultModal", "btn-archive-vault", "v220-vault-svg")
                        if f'id="{el_id}"' not in html_content
                    ]
                    has_av_palette = ("'archivevault'" in html_content or '"archivevault"' in html_content) and "toggleArchiveVaultHUD" in html_content
                    if missing_av_ids or not has_av_palette:
                        findings.append(CouncilFinding(
                            severity=CouncilFindingSeverity.LOW,
                            category="animatic_archive_vault_hud",
                            message=(
                                f"Compiled storyboard HTML lacks Archive Vault HUD element(s): "
                                f"{', '.join('#' + i for i in missing_av_ids) or 'Command Palette archivevault entry'}."
                            ),
                            suggested_fix="Ensure compile_storyboard_html renders #archiveVaultModal, #btn-archive-vault [:], #v220-vault-svg, and Command Palette 'archivevault' entry.",
                        ))
                        score -= 1.0
                    else:
                        findings.append(CouncilFinding(
                            severity=CouncilFindingSeverity.INFO,
                            category="animatic_archive_vault_hud",
                            message="RFC 8493 Archive Vault HUD verified (#btn-archive-vault / #archiveVaultModal / #v220-vault-svg / Command Palette 'archivevault').",
                        ))

                    # Departmental toolbar grouping check (#dept-group-camera, #dept-group-delivery)
                    missing_dept_groups = [
                        grp_id
                        for grp_id in ("dept-group-camera", "dept-group-delivery")
                        if f'id="{grp_id}"' not in html_content
                    ]
                    if missing_dept_groups:
                        findings.append(CouncilFinding(
                            severity=CouncilFindingSeverity.LOW,
                            category="animatic_departmental_toolbar",
                            message=f"Compiled storyboard preview HTML lacks departmental toolbar group(s): {', '.join('#' + g for g in missing_dept_groups)}.",
                            suggested_fix="Group departmental HUD toggles into #dept-group-camera and #dept-group-delivery.",
                        ))
                        score -= 0.5
                    else:
                        findings.append(CouncilFinding(
                            severity=CouncilFindingSeverity.INFO,
                            category="animatic_departmental_toolbar",
                            message="Departmental toolbar grouping verified (#dept-group-camera, #dept-group-delivery).",
                        ))

                    # Zero blocking dialog calls check (alert/confirm/prompt)
                    script_blocks = re.findall(r"<script\b[^>]*>(.*?)</script>", html_content, re.DOTALL | re.IGNORECASE)
                    blocking_dialog_hits: list[str] = []
                    for sb in script_blocks:
                        blocking_dialog_hits.extend(
                            re.findall(r"(?<![.\w\$])(?:window\.)?(?:alert|confirm|prompt)\s*\(", sb)
                        )
                    if blocking_dialog_hits:
                        findings.append(CouncilFinding(
                            severity=CouncilFindingSeverity.MEDIUM,
                            category="animatic_blocking_dialogs",
                            message=f"Blocking JS dialog call(s) detected in compiled animatic: {', '.join(blocking_dialog_hits[:3])}.",
                            suggested_fix="Replace alert/confirm/prompt with non-blocking showToast() and inline dark-room HUD controls.",
                        ))
                        score -= 1.0
                    else:
                        findings.append(CouncilFinding(
                            severity=CouncilFindingSeverity.INFO,
                            category="animatic_blocking_dialogs",
                            message="Zero blocking JS dialog calls (alert/confirm/prompt) verified.",
                        ))

                    # Verify zero duplicate JS keydown hotkey bindings, W & N hotkeys, & Escape handler cleanup
                    kd_match = re.search(r"window\.addEventListener\(['\"]keydown['\"].*?^\s*\}\);", html_content, re.DOTALL | re.MULTILINE)
                    if kd_match:
                        kd_block = kd_match.group(0)
                        bound_literals = re.findall(r"e\.key\s*===\s*['\"]([^'\"]+)['\"]", kd_block)
                        seen_keys: set[str] = set()
                        dup_keys: list[str] = []
                        for k_lit in bound_literals:
                            if k_lit in seen_keys and k_lit not in dup_keys:
                                dup_keys.append(k_lit)
                            seen_keys.add(k_lit)
                        if dup_keys:
                            findings.append(CouncilFinding(
                                severity=CouncilFindingSeverity.MEDIUM,
                                category="animatic_hotkey_collision",
                                message=f"Duplicate JS keydown hotkey bindings detected: {', '.join(dup_keys)}.",
                                suggested_fix="Assign unique keyboard shortcuts per HUD toggle in html_compiler.py.",
                            ))
                            score -= 1.0
                        else:
                            findings.append(CouncilFinding(
                                severity=CouncilFindingSeverity.INFO,
                                category="animatic_hotkey_collision",
                                message=f"Zero duplicate JS keydown hotkey bindings verified across {len(seen_keys)} key checks.",
                            ))

                        has_w_key = bool(re.search(r"e\.key\s*===\s*['\"][wW]['\"]", kd_block))
                        has_n_key = bool(re.search(r"e\.key\s*===\s*['\"][nN]['\"]", kd_block))
                        if not (has_w_key and has_n_key):
                            missing_hk = []
                            if not has_w_key:
                                missing_hk.append("W")
                            if not has_n_key:
                                missing_hk.append("N")
                            findings.append(CouncilFinding(
                                severity=CouncilFindingSeverity.LOW,
                                category="animatic_hotkeys_wn",
                                message=f"Global keydown handler missing required hotkey binding(s): {', '.join(missing_hk)}.",
                                suggested_fix="Bind W (Blocking HUD) and N (Client Review HUD) in global keydown listener.",
                            ))
                            score -= 0.5
                        else:
                            findings.append(CouncilFinding(
                                severity=CouncilFindingSeverity.INFO,
                                category="animatic_hotkeys_wn",
                                message="Blocking [W] and Client Review [N] keyboard hotkeys verified.",
                            ))

                        has_y_key = bool(re.search(r"e\.key\s*===\s*['\"][yY]['\"]", kd_block))
                        has_z_key = bool(re.search(r"e\.key\s*===\s*['\"][zZ]['\"]", kd_block))
                        if not (has_y_key and has_z_key):
                            missing_yz = []
                            if not has_y_key:
                                missing_yz.append("Y")
                            if not has_z_key:
                                missing_yz.append("Z")
                            findings.append(CouncilFinding(
                                severity=CouncilFindingSeverity.LOW,
                                category="animatic_hotkeys_yz",
                                message=f"Global keydown handler missing required hotkey binding(s): {', '.join(missing_yz)}.",
                                suggested_fix="Bind Y (C2PA Provenance HUD) and Z (On-Set Safety HUD) in global keydown listener.",
                            ))
                            score -= 0.5
                        else:
                            findings.append(CouncilFinding(
                                severity=CouncilFindingSeverity.INFO,
                                category="animatic_hotkeys_yz",
                                message="C2PA Provenance [Y] and On-Set Safety JSA [Z] keyboard hotkeys verified.",
                            ))

                        has_i_key = bool(re.search(r"e\.key\s*===\s*['\"][iI]['\"]", kd_block))
                        has_j_key = bool(re.search(r"e\.key\s*===\s*['\"][jJ]['\"]", kd_block))
                        if not (has_i_key and has_j_key):
                            missing_ij = []
                            if not has_i_key:
                                missing_ij.append("I")
                            if not has_j_key:
                                missing_ij.append("J")
                            findings.append(CouncilFinding(
                                severity=CouncilFindingSeverity.LOW,
                                category="animatic_hotkeys_ij",
                                message=f"Global keydown handler missing required hotkey binding(s): {', '.join(missing_ij)}.",
                                suggested_fix="Bind I (Localization HUD) and J (Editorial Spotting HUD) in global keydown listener.",
                            ))
                            score -= 0.5
                        else:
                            findings.append(CouncilFinding(
                                severity=CouncilFindingSeverity.INFO,
                                category="animatic_hotkeys_ij",
                                message="Localization & ADR [I] and Editorial Spotting [J] keyboard hotkeys verified.",
                            ))

                        has_eq_key = bool(re.search(r"""e\.key\s*===\s*(?:'='|"=")""", kd_block))
                        has_quote_key = bool(re.search(r"""e\.key\s*===\s*(?:"'"|'\\'')""", kd_block))
                        if not (has_eq_key and has_quote_key):
                            missing_eq_quote = []
                            if not has_eq_key:
                                missing_eq_quote.append("=")
                            if not has_quote_key:
                                missing_eq_quote.append("'")
                            findings.append(CouncilFinding(
                                severity=CouncilFindingSeverity.LOW,
                                category="animatic_hotkeys_eq_quote",
                                message=f"Global keydown handler missing required hotkey binding(s): {', '.join(missing_eq_quote)}.",
                                suggested_fix="Bind = (Motion Graphics Studio HUD) and ' (OTIO Coherence Matrix HUD) in global keydown listener.",
                            ))
                            score -= 0.5
                        else:
                            findings.append(CouncilFinding(
                                severity=CouncilFindingSeverity.INFO,
                                category="animatic_hotkeys_eq_quote",
                                message="Motion Graphics Studio [=] and OTIO Coherence Matrix ['] global keyboard hotkeys verified.",
                            ))

                        has_backtick_key = bool(re.search(r"""e\.key\s*===\s*(?:'`'|"`")""", kd_block))
                        has_minus_key = bool(re.search(r"""e\.key\s*===\s*(?:'-'|"-")""", kd_block))
                        if not (has_backtick_key and has_minus_key):
                            missing_bm = []
                            if not has_backtick_key:
                                missing_bm.append("`")
                            if not has_minus_key:
                                missing_bm.append("-")
                            findings.append(CouncilFinding(
                                severity=CouncilFindingSeverity.LOW,
                                category="animatic_hotkeys_backtick_minus",
                                message=f"Global keydown handler missing required hotkey binding(s): {', '.join(missing_bm)}.",
                                suggested_fix="Bind ` (Live-Render Jobs HUD) and - (Director Pitch Treatment HUD) in global keydown listener.",
                            ))
                            score -= 0.5
                        else:
                            findings.append(CouncilFinding(
                                severity=CouncilFindingSeverity.INFO,
                                category="animatic_hotkeys_backtick_minus",
                                message="Live-Render Jobs [`] and Director Pitch Treatment [-] global keyboard hotkeys verified.",
                            ))

                        has_rbrace_key = bool(re.search(r"""e\.key\s*===\s*(?:'\}'|"\}")""", kd_block))
                        has_lbrace_key = bool(re.search(r"""e\.key\s*===\s*(?:'\{'|"\{")""", kd_block))
                        if not (has_rbrace_key and has_lbrace_key):
                            missing_braces = []
                            if not has_rbrace_key:
                                missing_braces.append("}")
                            if not has_lbrace_key:
                                missing_braces.append("{")
                            findings.append(CouncilFinding(
                                severity=CouncilFindingSeverity.LOW,
                                category="animatic_hotkeys_braces",
                                message=f"Global keydown handler missing required hotkey binding(s): {', '.join(missing_braces)}.",
                                suggested_fix="Bind } (IMF/DCP Mastering HUD) and { (Voice Casting & Ducking HUD) in global keydown listener.",
                            ))
                            score -= 0.5
                        else:
                            findings.append(CouncilFinding(
                                severity=CouncilFindingSeverity.INFO,
                                category="animatic_hotkeys_braces",
                                message="IMF/DCP Mastering [}] and Voice Casting & Ducking [{] global keyboard hotkeys verified.",
                            ))

                        has_plus_key = bool(re.search(r"""e\.key\s*===\s*(?:'\+'|"\+")""", kd_block))
                        has_colon_key = bool(re.search(r"""e\.key\s*===\s*(?:'\:'|"\:"|':'|":")""", kd_block))
                        if not (has_plus_key and has_colon_key):
                            missing_pc = []
                            if not has_plus_key:
                                missing_pc.append("+")
                            if not has_colon_key:
                                missing_pc.append(":")
                            findings.append(CouncilFinding(
                                severity=CouncilFindingSeverity.LOW,
                                category="animatic_hotkeys_plus_colon",
                                message=f"Global keydown handler missing required hotkey binding(s): {', '.join(missing_pc)}.",
                                suggested_fix="Bind + (Colorist Scopes HUD) and : (RFC 8493 Archive Vault HUD) in global keydown listener.",
                            ))
                            score -= 0.5
                        else:
                            findings.append(CouncilFinding(
                                severity=CouncilFindingSeverity.INFO,
                                category="animatic_hotkeys_plus_colon",
                                message="Colorist Scopes [+] and RFC 8493 Archive Vault [:] global keyboard hotkeys verified.",
                            ))

                        esc_idx = kd_block.find("e.key === 'Escape'")
                        if esc_idx == -1:
                            esc_idx = kd_block.find('e.key === "Escape"')
                        esc_end = kd_block.find("return;", esc_idx) if esc_idx != -1 else -1
                        esc_slice = (
                            kd_block[esc_idx:esc_end]
                            if (esc_idx != -1 and esc_end != -1)
                            else (kd_block[esc_idx:] if esc_idx != -1 else "")
                        )
                        sec_match = re.search(r"function\s+closeSecondaryOpenHUDs\s*\(\)\s*\{(.*?)\}", html_content, re.DOTALL)
                        esc_combined = esc_slice + ("\n" + sec_match.group(1) if (sec_match and "closeSecondaryOpenHUDs" in esc_slice) else "")
                        esc_panel_checks = (
                            ("animatic-audio-mixer", ("animatic-audio-mixer", "toggleMixer")),
                            ("animatic-reframe-hud", ("ReframeHUD", "animatic-reframe-hud")),
                            ("animatic-qc-hud", ("QcHUD", "QCHUD", "animatic-qc-hud")),
                            ("animatic-blocking-hud", ("BlockingHUD", "animatic-blocking-hud")),
                            ("animatic-review-hud", ("ReviewHUD", "animatic-review-hud")),
                            ("animatic-c2pa-hud", ("C2paHUD", "animatic-c2pa-hud")),
                            ("animatic-safety-hud", ("SafetyHUD", "animatic-safety-hud")),
                            ("animatic-localization-hud", ("LocalizationHUD", "animatic-localization-hud")),
                            ("animatic-spotting-hud", ("SpottingHUD", "animatic-spotting-hud")),
                            ("modal-s3d-stereography", ("S3dHUD", "isS3dHUDOpen", "modal-s3d-stereography")),
                            ("modal-accessibility-ad", ("AccessibilityAdHUD", "isAccessibilityAdHUDOpen", "modal-accessibility-ad")),
                            ("modal-hud-command-palette", ("HudCommandPalette", "isHudCommandPaletteOpen", "modal-hud-command-palette")),
                            ("modal-art-wardrobe-continuity", ("ArtWardrobeHUD", "isArtWardrobeHUDOpen", "modal-art-wardrobe-continuity")),
                            ("modal-render-economics", ("RenderEconomicsHUD", "isRenderEconomicsHUDOpen", "modal-render-economics")),
                            ("modal-motion-graphics-studio", ("MotionGfxHUD", "isMotionGfxHUDOpen", "modal-motion-graphics-studio")),
                            ("modal-otio-coherence", ("OtioCoherenceHUD", "isOtioCoherenceHUDOpen", "modal-otio-coherence")),
                            ("modal-render-jobs", ("RenderJobsHUD", "isRenderJobsHUDOpen", "modal-render-jobs")),
                            ("modal-pitch-treatment", ("PitchTreatmentHUD", "isPitchTreatmentHUDOpen", "modal-pitch-treatment")),
                            ("imfDcpModal", ("ImfDcpHUD", "isImfDcpHUDOpen", "imfDcpModal")),
                            ("voiceDuckingModal", ("VoiceDuckingHUD", "isVoiceDuckingHUDOpen", "voiceDuckingModal")),
                            ("colorScopesModal", ("ColorScopesHUD", "isColorScopesHUDOpen", "colorScopesModal")),
                            ("archiveVaultModal", ("ArchiveVaultHUD", "isArchiveVaultHUDOpen", "archiveVaultModal")),
                        )
                        missing_esc: list[str] = [
                            panel_id
                            for panel_id, markers in esc_panel_checks
                            if panel_id in html_content and not any(m in esc_combined for m in markers)
                        ]
                        if missing_esc:
                            findings.append(CouncilFinding(
                                severity=CouncilFindingSeverity.LOW,
                                category="animatic_escape_dismissal",
                                message=f"Escape key handler does not dismiss open panels: {', '.join(missing_esc)}.",
                                suggested_fix="Add Escape dismissal logic for all v2.12-v2.17 HUDs and modals in global keydown handler.",
                            ))
                            score -= 0.5

                    # Verify real AICP bid values in HUD match bible.master_aicp_bid
                    aicp_bid = getattr(bible, "master_aicp_bid", None)
                    if aicp_bid is not None and 'id="aicp-grand-total-val"' in html_content:
                        expected_total = float(getattr(getattr(aicp_bid, "top_sheet", None), "grand_total", 0.0) or 0.0)
                        rendered_match = re.search(r'id="aicp-grand-total-val"[^>]*>\$?([0-9,]+\.\d{2})<', html_content)
                        if rendered_match and expected_total > 0:
                            rendered_total = float(rendered_match.group(1).replace(",", ""))
                            if abs(rendered_total - expected_total) > 1.0:
                                findings.append(CouncilFinding(
                                    severity=CouncilFindingSeverity.MEDIUM,
                                    category="animatic_aicp_real_data",
                                    message=f"AICP HUD displays ${rendered_total:,.2f} instead of bible master_aicp_bid total ${expected_total:,.2f}.",
                                    suggested_fix="Bind AICP HUD metrics directly to bible.master_aicp_bid.top_sheet.",
                                ))
                                score -= 1.0
                            else:
                                findings.append(CouncilFinding(
                                    severity=CouncilFindingSeverity.INFO,
                                    category="animatic_aicp_real_data",
                                    message=f"AICP HUD real-data binding verified (${rendered_total:,.2f} matches master_aicp_bid).",
                                ))

            except Exception:
                pass

        score = max(0.0, min(25.0, round(score, 2)))
        summary = f"UX Designer review completed with score {score}/25.0."
        return PersonaReviewResult(
            persona=CouncilPersona.COUNCIL_UX_DESIGNER,
            score=score,
            findings=findings,
            summary=summary,
        )

    def generate_markdown_report(self, report: ProductCouncilReport) -> str:
        """Formats the ProductCouncilReport as a publication-ready Markdown document."""
        status_badge = "PASSED" if report.passed else "FAILED"
        lines = [
            f"# Product Council Audit Report: {report.project_title}",
            "",
            f"**Version**: {report.version} | **Timestamp**: `{report.timestamp}`",
            f"**Overall Score**: **`{report.overall_score} / 100.0`** | **Status**: **{status_badge}**",
            f"**Critical Findings**: {report.critical_findings_count}",
            "",
            "## Persona Scorecard",
            "",
            "| Persona | Role | Score (/25) | Findings Count | Summary |",
            "| :--- | :--- | :---: | :---: | :--- |",
        ]

        role_map = {
            CouncilPersona.COUNCIL_FDE: "Forward Deployed Engineer (Schema & Delivery)",
            CouncilPersona.COUNCIL_AGENT_ENGINEER: "Agent Engineer (7-Point Prompts & Models)",
            CouncilPersona.COUNCIL_STRATEGIST: "Creative Strategist (Domain & Invariants)",
            CouncilPersona.COUNCIL_UX_DESIGNER: "UX & Visual Continuity (ViewBox & Safe Guides)",
        }

        for rev in report.reviews:
            role = role_map.get(rev.persona, rev.persona.value)
            lines.append(
                f"| `{rev.persona.value}` | {role} | **{rev.score:.1f}** | {len(rev.findings)} | {rev.summary} |"
            )

        lines.extend([
            "",
            "## Findings & Action Items",
            "",
        ])

        if not any(r.findings for r in report.reviews):
            lines.append("No findings or defects identified. All criteria met with highest honors.")
        else:
            for rev in report.reviews:
                if not rev.findings:
                    continue
                lines.append(f"### {rev.persona.value.upper()}")
                for f in rev.findings:
                    badge = f"[{f.severity.value.upper()}]"
                    lines.append(f"- {badge} **{f.category}**: {f.message}")
                    if f.suggested_fix:
                        lines.append(f"  - *Suggested Fix*: {f.suggested_fix}")
                lines.append("")

        if report.pm_recommendations:
            lines.extend([
                "## Senior Product Manager Roadmap & Feature Inspection",
                "",
                f"> **Persona (`{CouncilPersona.PRODUCT_MANAGER.value}`)**: *{report.pm_persona_prompt}*",
                "",
                "| ID | Priority | Status | Feature Title | Target Modules |",
                "| :--- | :---: | :---: | :--- | :--- |",
            ])
            for feat in report.pm_recommendations:
                mods = ", ".join(f"`{m}`" for m in feat.target_modules)
                lines.append(
                    f"| `{feat.feature_id}` | **{feat.priority}** | `{feat.status}` | **{feat.title}**: {feat.proposed_solution} | {mods} |"
                )
            lines.append("")

        if report.recommendations:
            lines.extend([
                "## Recommendations",
                "",
            ])
            for rec in report.recommendations:
                lines.append(f"1. {rec}")
            lines.append("")

        return "\n".join(lines)

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """ADK 2.0 Agent invocation hook."""
        bundle_or_bible = context.get("bundle") or context.get("bible")
        out_dir = context.get("output_dir")
        auto_heal = context.get("auto_heal", True)
        report = self.audit(bundle_or_bible, output_dir=out_dir, auto_heal=auto_heal)
        context["council_report"] = report
        return context
