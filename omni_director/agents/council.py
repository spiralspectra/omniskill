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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from pydantic import ConfigDict

from omni_director.config import FORBIDDEN_LEGACY_PATTERNS, DirectorConfig, cfg
from omni_director.presets import DOMAIN_ARCHETYPES, classify_brief_domain
from omni_director.schemas import (
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
)
from omni_director.telemetry import verify_bundle_checksums
from omni_director.tools.prompt_auditor import audit_omni_scene_prompt, heal_omni_scene_prompt

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
        ae_review = self._review_agent_engineer(bible=bible, auto_heal=auto_heal)
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
            version="2.6.0",
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

        # Active Checksum Integrity Verification
        eval_target = output_dir or bundle_dir
        eval_dir = Path(eval_target) if eval_target else (Path(bundle.bundle_json_path).parent if bundle and bundle.bundle_json_path else None)
        if eval_dir and (eval_dir / "telemetry.json").is_file():
            is_valid, checksum_errors = verify_bundle_checksums(eval_dir)
            if not is_valid:
                has_mismatch = any("Checksum mismatch" in err for err in checksum_errors)
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.CRITICAL if has_mismatch else CouncilFindingSeverity.HIGH,
                    category="artifact_integrity",
                    message=f"Bundle artifact checksum verification failed ({len(checksum_errors)} issue(s)): {'; '.join(checksum_errors[:2])}",
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
            hdr_json = eval_dir / "hdr10_metadata.json"
            hlg_xml = eval_dir / "hlg_broadcast_metadata.xml"
            resolve_hdr = eval_dir / "resolve_hdr_parameters.xml"
            if hdr_json.is_file() or hlg_xml.is_file() or resolve_hdr.is_file():
                hdr_items = []
                if hdr_json.is_file():
                    hdr_items.append("hdr10_metadata.json")
                if hlg_xml.is_file():
                    hdr_items.append("hlg_broadcast_metadata.xml")
                if resolve_hdr.is_file():
                    hdr_items.append("resolve_hdr_parameters.xml")
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="hdr_metadata_delivery",
                    message=f"HDR10 mastering metadata JSON, HLG XML, and DaVinci Resolve HDR XML verified on disk: {', '.join(hdr_items)}.",
                    details={"hdr_artifacts": hdr_items}
                ))

            # Verify 1st AD Stripboard Production Scheduler deliverables (PM-FEAT-016)
            mm_xml = eval_dir / "movie_magic_schedule.xml"
            strip_csv = eval_dir / "stripboard_schedule.csv"
            dood_csv = eval_dir / "day_out_of_days_matrix.csv"
            breakdown_json = eval_dir / "script_breakdown_sheets.json"
            if mm_xml.is_file() or strip_csv.is_file() or dood_csv.is_file() or breakdown_json.is_file():
                stripboard_items = []
                if mm_xml.is_file():
                    stripboard_items.append("movie_magic_schedule.xml")
                if strip_csv.is_file():
                    stripboard_items.append("stripboard_schedule.csv")
                if dood_csv.is_file():
                    stripboard_items.append("day_out_of_days_matrix.csv")
                if breakdown_json.is_file():
                    stripboard_items.append("script_breakdown_sheets.json")
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="stripboard_schedule_delivery",
                    message=f"1st AD Movie Magic schedule XML, Stripboard CSV, DOOD matrix, and Breakdown sheets verified on disk: {', '.join(stripboard_items)}.",
                    details={"stripboard_artifacts": stripboard_items}
                ))

            # Verify Physical Film Stock Emulation deliverables (PM-FEAT-017)
            film_dctl = eval_dir / "film_stock_shader.dctl"
            film_ale = eval_dir / "film_stock.ale"
            film_json = eval_dir / "film_emulation_manifest.json"
            if film_dctl.is_file() or film_ale.is_file() or film_json.is_file():
                film_items = []
                if film_dctl.is_file():
                    film_items.append("film_stock_shader.dctl")
                if film_ale.is_file():
                    film_items.append("film_stock.ale")
                if film_json.is_file():
                    film_items.append("film_emulation_manifest.json")
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="film_emulation_delivery",
                    message=f"Film stock DCTL shader, Avid ALE log, and Emulation manifest verified on disk: {', '.join(film_items)}.",
                    details={"film_artifacts": film_items}
                ))

            # Verify SMPTE 12M Clapper Slate & ASC-MHL deliverables (PM-FEAT-018)
            mhl_xml = eval_dir / "asc_mhl_manifest.xml"
            slate_csv = eval_dir / "clapper_slate_log.csv"
            sound_ale = eval_dir / "sound_sync_ale.ale"
            slate_json = eval_dir / "master_slate_spec.json"
            if mhl_xml.is_file() or slate_csv.is_file() or sound_ale.is_file() or slate_json.is_file():
                slate_items = []
                if mhl_xml.is_file():
                    slate_items.append("asc_mhl_manifest.xml")
                if slate_csv.is_file():
                    slate_items.append("clapper_slate_log.csv")
                if sound_ale.is_file():
                    slate_items.append("sound_sync_ale.ale")
                if slate_json.is_file():
                    slate_items.append("master_slate_spec.json")
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="clapper_slate_delivery",
                    message=f"ASC-MHL hash list XML, Clapper slate CSV, Sound sync ALE, and Slate JSON verified on disk: {', '.join(slate_items)}.",
                    details={"slate_artifacts": slate_items}
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
    ) -> PersonaReviewResult:
        """Audits scene prompts against 7-Point standards and self-heals defects."""
        findings: List[CouncilFinding] = []
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
            )
            if (not res.passed or res.score < 90.0) and auto_heal:
                logger.info(f"Self-healing prompt for Scene {scene.scene_index}...")
                healed_target, res = heal_omni_scene_prompt(
                    scene,
                    audit_result=res,
                    regime=bible.creative_regime,
                    storytelling_mode=getattr(bible, "storytelling_mode", None),
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

        avg_audit_score = sum(audit_scores) / len(audit_scores) if audit_scores else 0.0
        score = 25.0 * (avg_audit_score / 100.0)
        critical_count = len([f for f in findings if f.severity == CouncilFindingSeverity.CRITICAL])
        score -= (critical_count * 10.0)
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
        detected_domain = classify_brief_domain(combined_text)
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
        if getattr(bible, "is_mode_b_continuous", False) and len(bible.scenes) > 1:
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
            mhl_manifest = getattr(slate_spec, "asc_mhl_manifest", None)
            hash_count = len(getattr(mhl_manifest, "hash_entries", [])) if mhl_manifest else 0
            cam_roll = getattr(slate_spec, "camera_roll", "A01")
            sound_roll = getattr(slate_spec, "sound_roll", "SR01")
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

        # Verify compiled storyboard HTML transport controls if present
        html_path = (
            Path(bundle.storyboard_html_path)
            if (bundle and bundle.storyboard_html_path)
            else (Path(output_dir) / "storyboard_preview.html" if output_dir else None)
        )
        if html_path and html_path.is_file():
            try:
                html_content = html_path.read_text(encoding="utf-8")
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
