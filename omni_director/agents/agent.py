"""ADK 2.0 Multi-Agent Pipeline for omni-movie-director.

Orchestrates the Lead Director (gemini-4-argon), Fast Workhorse (gemini-3.8-flash),
Concept Artist (gemini-3-pro-image), and Video Engine (gemini-omni-1.1-flash-preview).
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union
from pydantic import ConfigDict

from omni_director.config import DirectorConfig, cfg, validate_model_identifier
import omni_director.presets as _presets_mod
from omni_director.presets import (
    DOMAIN_ARCHETYPES,
    classify_brief_domain,
    get_domain_audio_mixer,
    get_domain_clapper_slate_spec,
    get_domain_color_look,
    get_domain_dof_spec,
    get_domain_drone_spec,
    get_domain_aicp_bid_spec,
    get_domain_c2pa_provenance_spec,
    get_domain_film_emulation_spec,
    get_domain_hdr_spec,
    get_domain_imf_dcp_profile,
    get_domain_lighting_rig,
    get_domain_lut_spec,
    get_domain_moco_rig,
    get_domain_optical_lens,
    get_domain_safety_risk_spec,
    get_domain_spatial_audio_spec,
    get_domain_speed_ramp,
    get_domain_stripboard_spec,
    get_domain_vfx_manifest,
    get_domain_virtual_production,
    get_domain_voice_ducking_profile,
    get_preset_bible,
    hydrate_imf_dcp_and_voice_ducking_specs,
)
from omni_director.tools.stripboard_scheduler import extract_script_breakdown_sheet
from omni_director.tools.delivery_reframe import (
    synthesize_default_reframe_manifest,
    synthesize_default_scene_reframe,
)
from omni_director.tools.broadcast_qc import (
    synthesize_default_broadcast_qc_spec,
    synthesize_default_scene_qc,
)
from omni_director.tools.continuity_blocking import (
    synthesize_default_continuity_blocking,
    synthesize_scene_blocking,
)
from omni_director.tools.review_notes import (
    synthesize_default_client_review,
    synthesize_scene_review_signoff,
)
from omni_director.tools.c2pa_provenance import synthesize_scene_c2pa_provenance
from omni_director.tools.safety_risk import assess_scene_hazards
from omni_director.tools.localization_adr import (
    compile_localization_manifest,
    format_localization_prompt_token,
)
from omni_director.tools.editorial_spotting import (
    build_spotting_manifest,
    format_spotting_prompt_token,
)
from omni_director.tools.wardrobe_props import (
    compile_wardrobe_prop_bible,
    format_art_continuity_token,
)
from omni_director.tools.render_economics import (
    check_render_budget_guardrail,
    compile_render_economics_manifest,
    format_render_profile_token,
)
from omni_director.tools.motion_graphics import (
    compile_motion_graphics_manifest,
    format_motion_graphics_token,
)
from omni_director.tools.otio_coherence import (
    compile_otio_coherence_manifest,
    format_otio_coherence_token,
    reconcile_cross_department_conflicts,
)
from omni_director.tools.render_orchestrator import (
    _recalculate_manifest_summary,
    compile_render_job_manifest,
    evaluate_take_visual_qa,
    format_render_job_token,
    promote_scene_take,
    verify_mode_b_frame_anchor,
)
from omni_director.tools.pitch_treatment import (
    compile_pitch_treatment,
    format_pitch_treatment_token,
)
from omni_director.tools.imf_dcp_packager import format_imf_dcp_token
from omni_director.tools.voice_ducking import format_voice_ducking_token
from omni_director.schemas import (
    ActionBeatSpec,
    AspectRatio,
    AuditResult,
    CharacterTurnaroundSpec,
    CraftCameraSpec,
    DiegeticSonicSpec,
    MasterBgmSpec,
    MasterEnvironmentSpec,
    MasterMotionGraphicsManifest,
    MasterOtioCoherenceManifest,
    MasterPitchTreatmentSpec,
    MasterProductionBible,
    MasterRenderJobManifest,
    NanoBananaReference,
    ProductionBundle,
    RegimeType,
    RenderJobStatusEnum,
    ScenePromptSpec,
    StorytellingMode,
    load_bible_from_json,
)
from omni_director.telemetry import RuntimeTelemetry
from omni_director.agents.council import ProductCouncilOrchestrator
from omni_director.tools.html_compiler import compile_storyboard_html
from omni_director.tools.nano_banana import NanoBananaStoryboardEngine
from omni_director.tools.omni_video import GeminiOmniVideoEngine
from omni_director.tools.prompt_auditor import audit_omni_scene_prompt, heal_omni_scene_prompt

logger = logging.getLogger("omni_director.agents")

# Graceful Google ADK 2.0 Import Handling
try:
    import google.adk
    from google.adk.agents import BaseAgent, LlmAgent, SequentialAgent
    HAS_GOOGLE_ADK = True

    class ParallelAgent(BaseAgent):  # type: ignore[no-redef]
        """Non-deprecated ADK parallel fan-out wrapper built on BaseAgent."""

        model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

        def __init__(
            self,
            name: str = "ParallelAgent",
            sub_agents: Optional[List[BaseAgent]] = None,
            description: str = "",
            instruction: str = "",
            **kwargs: Any,
        ) -> None:
            desc = description or instruction
            super().__init__(name=name, description=desc, **kwargs)
            self.sub_agents = list(sub_agents or [])

        def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
            for agent in self.sub_agents:
                context = agent.run(context)
            return context
except ImportError:
    HAS_GOOGLE_ADK = False

    class BaseAgent:  # type: ignore[no-redef]
        def __init__(self, name: str, description: str = "", instruction: str = "", **kwargs: Any) -> None:
            self.name = name
            self.description = description or instruction
            self.instruction = self.description
            self.kwargs = kwargs

        def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
            return context

    class LlmAgent(BaseAgent):  # type: ignore[no-redef]
        def __init__(self, name: str, model: str = "", description: str = "", instruction: str = "", **kwargs: Any) -> None:
            super().__init__(name=name, description=description, instruction=instruction, **kwargs)
            self.model = model

    class SequentialAgent(BaseAgent):  # type: ignore[no-redef]
        def __init__(self, name: str, sub_agents: List[BaseAgent], description: str = "", instruction: str = "", **kwargs: Any) -> None:
            super().__init__(name=name, description=description, instruction=instruction, **kwargs)
            self.sub_agents = sub_agents

        def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
            for agent in self.sub_agents:
                context = agent.run(context)
            return context

    class ParallelAgent(BaseAgent):  # type: ignore[no-redef]
        def __init__(self, name: str, sub_agents: List[BaseAgent], description: str = "", instruction: str = "", **kwargs: Any) -> None:
            super().__init__(name=name, description=description, instruction=instruction, **kwargs)
            self.sub_agents = sub_agents

        def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
            for agent in self.sub_agents:
                context = agent.run(context)
            return context


def synthesize_custom_bible(
    raw_prompt: str,
    config: Optional[DirectorConfig] = None,
    storytelling_mode: StorytellingMode = StorytellingMode.MODE_A_PARALLEL_CUT,
    project_title: Optional[str] = None,
    creative_brief: Optional[str] = None,
    genre: Optional[str] = None,
    aspect_ratio: Optional[AspectRatio] = None,
    total_runtime_sec: Optional[int] = None,
) -> MasterProductionBible:
    """Dynamically synthesizes a valid 7-Point compliant MasterProductionBible from custom raw_prompt."""
    effective_prompt = creative_brief or raw_prompt
    domain = genre or classify_brief_domain(effective_prompt)
    archetype = DOMAIN_ARCHETYPES.get(domain, DOMAIN_ARCHETYPES["architectural_sanctuary"])

    # Regime handling: support RegimeType enum and string "kinetic"
    raw_regime = archetype.get("regime")
    if raw_regime == RegimeType.REGIME_2_KINETIC or raw_regime == "kinetic" or (isinstance(raw_regime, str) and "kinetic" in raw_regime.lower()):
        regime = RegimeType.REGIME_2_KINETIC
        is_kinetic = True
    else:
        regime = RegimeType.REGIME_1_ATMOSPHERIC
        is_kinetic = False

    domain_color_look = get_domain_color_look(domain)
    domain_audio_mixer = get_domain_audio_mixer(domain)
    domain_speed_ramp = get_domain_speed_ramp(domain)
    domain_lens = get_domain_optical_lens(domain)
    domain_vp = get_domain_virtual_production(domain)
    domain_moco = get_domain_moco_rig(domain)
    domain_lighting = get_domain_lighting_rig(domain)
    domain_dof = get_domain_dof_spec(domain)
    domain_lut = get_domain_lut_spec(domain)
    domain_spatial = get_domain_spatial_audio_spec(domain)
    domain_vfx = get_domain_vfx_manifest(domain)
    domain_hdr = get_domain_hdr_spec(domain)
    domain_film = get_domain_film_emulation_spec(domain)
    domain_drone = get_domain_drone_spec(domain)

    title = project_title or (effective_prompt[:40].strip().title() if effective_prompt else "Omni Vision Sequence")
    if not title:
        title = "Omni Vision Sequence"

    scene_title_1 = f"{title} - Initiation"
    scene_title_2 = f"{title} - Climax"

    palette = archetype.get("color_palette") or archetype.get("palette") or ["#0B132B", "#1C2541", "#3A506B", "#5BC0BE", "#6FFFE9"]
    lighting = archetype.get("default_lighting") or archetype.get("lighting") or "High-contrast chiaroscuro with cold 5600K key and subtle rim lighting"
    foley = archetype.get("default_foley") or archetype.get("foley") or ["Crisp physical movement rustle", "Low resonant ambient hum"]

    default_cam = archetype.get("default_camera")
    cam_rigs = archetype.get("camera_rigs", [])
    if default_cam:
        camera_rig_1 = default_cam
        camera_rig_2 = cam_rigs[0] if cam_rigs else f"{default_cam} (Alternate Angle)"
    elif cam_rigs:
        camera_rig_1 = cam_rigs[0]
        camera_rig_2 = cam_rigs[1] if len(cam_rigs) > 1 else "Steadicam"
    else:
        camera_rig_1 = "Dolly Track"
        camera_rig_2 = "Steadicam"

    focal_length_1 = archetype.get("default_focal_length", 35)
    focal_length_2 = 50 if focal_length_1 != 50 else 85

    prose_1 = (
        f"Wide establishing tracking shot. {raw_prompt.strip()}. "
        f"Adhering to character aesthetic <image_1> and architectural staging <image_2>. "
        f"Shot with {camera_rig_1} with {lighting}. "
        f"{'Rendered at natural 1.0x real-time speed preserving continuous kinetic momentum conservation, physical inertia, and friction invariants. ' if is_kinetic else 'Gentle macro motion with tactile physics, kinetic continuity, and continuous velocity vector. '}"
        f"Diegetic audio captures synchronous {foley[0]} and {foley[-1]}."
    )
    prose_2 = (
        f"Continuation of Scene 1 following the subject. Continuation of {raw_prompt.strip()}. "
        f"Maintaining continuity with keyframe <image_3>. "
        f"{camera_rig_2} maneuver at eye-level with {lighting}. "
        f"{'Rendered at natural 1.0x real-time speed preserving solid kinetic momentum conservation and ground contact reaction. ' if is_kinetic else 'Controlled tactile interaction with micro-acoustic detail and kinetic continuity. '}"
        f"Diegetic sound design features immediate {foley[0]} and atmospheric air wash."
    )

    craft_1 = CraftCameraSpec(
        rig_type=camera_rig_1,
        focal_length_mm=focal_length_1,
        composition="Wide establishing shot with centered horizon and geometric symmetry",
        route="Smooth forward dolly along the central camera axis",
        action_anchor="Hero subject entering the frame",
        focus_axis="Locked focus plane at f/2.8 maintaining 180-degree axis",
        tone_rig="Cinematic anamorphic prime with subtle horizontal flare",
        optical_lens=domain_lens,
    )

    craft_2 = CraftCameraSpec(
        rig_type=camera_rig_2,
        focal_length_mm=focal_length_2,
        composition="Medium close-up at eye level with strong rim separation",
        route="Arced orbit maneuver sweeping 45 degrees around subject",
        action_anchor="Subject's hands and physical contact interface",
        focus_axis="Shallow depth of field with locked subject focal tracking",
        tone_rig="Warm spherical glass with smooth circular bokeh",
        optical_lens=domain_lens,
    )

    scene_1 = ScenePromptSpec(
        scene_index=1,
        scene_title=scene_title_1,
        timestamp_range="00:00 - 00:05",
        regime=regime,
        craft_camera=craft_1,
        speed_ramp=domain_speed_ramp,
        scene_color_look=domain_color_look,
        optical_lens=domain_lens,
        virtual_production=domain_vp,
        moco_rig=domain_moco,
        lighting_rig=domain_lighting,
        dof_spec=domain_dof,
        lut_spec=domain_lut,
        spatial_audio=domain_spatial,
        vfx_compositing=domain_vfx,
        hdr_spec=domain_hdr,
        kinetic_contact_chain="1. Initiation: Subject moves -> 2. Contact: Foot impacts ground -> 3. Transfer: Force accelerates mass -> 4. Evidence: Surface dust shifts -> 5. Recovery: Stable stance." if is_kinetic else None,
        action_beats=[
            "Beat 1: Subject emerges into illuminated frame (00:00 - 00:02)",
            "Beat 2: Subject engages primary movement trajectory (00:02 - 00:05)",
        ],
        diegetic_sonic=DiegeticSonicSpec(
            foley_cues=foley,
            dialogue_lines=[],
            room_acoustics="Controlled cinematic soundstage with damp low-end reverb",
        ),
        omni_prose_prompt=prose_1,
    )
    scene_1.breakdown_sheet = extract_script_breakdown_sheet(scene_1, 1)

    scene_2 = ScenePromptSpec(
        scene_index=2,
        scene_title=scene_title_2,
        timestamp_range="00:05 - 00:10",
        regime=regime,
        craft_camera=craft_2,
        speed_ramp=domain_speed_ramp,
        scene_color_look=domain_color_look,
        optical_lens=domain_lens,
        virtual_production=domain_vp,
        moco_rig=domain_moco,
        lighting_rig=domain_lighting,
        dof_spec=domain_dof,
        lut_spec=domain_lut,
        spatial_audio=domain_spatial,
        vfx_compositing=domain_vfx,
        hdr_spec=domain_hdr,
        kinetic_contact_chain="1. Initiation: Momentum shifts -> 2. Contact: Grip engages frame -> 3. Transfer: Torque arrests rotation -> 4. Evidence: Structural vibration -> 5. Recovery: Heroic pose." if is_kinetic else None,
        action_beats=[
            "Beat 1: Peak acceleration and directional transition (00:05 - 00:08)",
            "Beat 2: Decisive deceleration into static hero posture (00:08 - 00:10)",
        ],
        diegetic_sonic=DiegeticSonicSpec(
            foley_cues=foley,
            dialogue_lines=[],
            room_acoustics="Reflective dynamic spatial acoustics with crisp decay",
        ),
        omni_prose_prompt=prose_2,
    )
    scene_2.breakdown_sheet = extract_script_breakdown_sheet(scene_2, 2)
    domain_slate = get_domain_clapper_slate_spec(domain, [scene_1, scene_2], project_title=title)
    scene_1.film_emulation = domain_film
    scene_2.film_emulation = domain_film
    if domain_slate and len(domain_slate.scenes) >= 1:
        scene_1.clapper_slate = domain_slate.scenes[0]
    if domain_slate and len(domain_slate.scenes) >= 2:
        scene_2.clapper_slate = domain_slate.scenes[1]
    scene_1.drone_flight = domain_drone
    scene_2.drone_flight = domain_drone

    # Sonic Profile and BPM from Archetype
    bgm_bpm = archetype.get("default_bpm", 120 if is_kinetic else 72)
    bgm_key = archetype.get("default_key", "D Minor")
    bgm_genre = archetype.get("default_bgm_genre", "Cinematic Hybrid Score")

    char_data = archetype.get("default_character", {
        "name": "Hero Subject",
        "silhouette": f"Distinctive posture and professional poise appropriate for {domain.replace('_', ' ')}",
        "wardrobe_polarity": "Matte charcoal tailored suit with crisp architectural contrasts",
        "movement_signature": "Precise, deliberate, momentum-conserving movement",
    })
    env_invariants = archetype.get("default_invariants", [
        f"Physical ground surface and spatial boundaries for {domain.replace('_', ' ')} remain rigid",
        "Key hero subjects maintain optical edge consistency"
    ])

    bible = MasterProductionBible(
        project_title=title,
        logline=effective_prompt,
        creative_regime=regime,
        storytelling_mode=storytelling_mode,
        aspect_ratio=aspect_ratio or AspectRatio.RATIO_16_9,
        total_runtime_seconds=total_runtime_sec or 10,
        color_palette=palette,
        environment=MasterEnvironmentSpec(
            location_name=f"{domain.replace('_', ' ').title()} Sanctuary",
            spatial_architecture=f"Architectural space styled for {domain.replace('_', ' ')}",
            lighting_setup=lighting,
            atmospheric_particles="Ultra-fine suspended haze catching oblique light shafts",
            positive_invariants=env_invariants,
            generation_prompt=f"Master architectural environment for {domain.replace('_', ' ')} showing clean lines and deep spatial perspective",
        ),
        characters=[
            CharacterTurnaroundSpec(
                name=char_data.get("name", "Hero Subject"),
                silhouette=char_data.get("silhouette", "Precise kinetic silhouette"),
                wardrobe_polarity=char_data.get("wardrobe_polarity", "Matte charcoal with crisp contrast accents"),
                movement_signature=char_data.get("movement_signature", "Precise, decisive, momentum-conserving kinetic movement"),
                generation_prompt=f"Character turnaround orthographic sheet for {char_data.get('name', 'Hero Subject')} showing front, profile, and three-quarter angles",
            )
        ],
        camera_rig=craft_1,
        sonic_blueprint=DiegeticSonicSpec(
            foley_cues=foley,
            dialogue_lines=[],
            room_acoustics="Controlled cinematic soundstage",
        ),
        master_bgm=MasterBgmSpec(
            track_title=f"{title} Theme",
            genre_style=bgm_genre,
            tempo_bpm=bgm_bpm,
            key_signature=bgm_key,
            instrumentation=["Modular synthesizer pulses", "Sub-bass rumble", "Acoustic strings"],
            dynamic_arc="Gentle rhythmic pulse building into an assertive cinematic climax",
            lyria_prompt=f"Cinematic score for {domain.replace('_', ' ')}, {bgm_genre.lower()} at {bgm_bpm} BPM in {bgm_key}",
        ),
        nano_banana_assets=[
            NanoBananaReference(
                asset_id="<image_1>",
                job_description="Hero Character Turnaround Reference Sheet",
                exclusion_clause="Ignore background clutter and lighting variations",
                generation_prompt="Character turnaround sheet for hero subject on clean studio background",
            ),
            NanoBananaReference(
                asset_id="<image_2>",
                job_description="Master Architectural Environment Anchor",
                exclusion_clause="Ignore transient objects and temporary clutter",
                generation_prompt="Master architectural environment plate with high-contrast cinematic lighting",
            ),
            NanoBananaReference(
                asset_id="<image_3>",
                job_description="Scene 1 Composition Keyframe",
                exclusion_clause="Ignore temporary motion blur and camera artifacts",
                generation_prompt="Scene keyframe showing hero subject entering the architectural space",
            ),
        ],
        scenes=[scene_1, scene_2],
        domain_archetype=domain,
        master_color_look=domain_color_look,
        master_audio_mixer=domain_audio_mixer,
        master_lens_package=domain_lens,
        virtual_production=domain_vp,
        master_moco_rig=domain_moco,
        master_lighting_rig=domain_lighting,
        master_dof_spec=domain_dof,
        master_lut_spec=domain_lut,
        master_spatial_audio=domain_spatial,
        master_vfx_manifest=domain_vfx,
        master_hdr_spec=domain_hdr,
        master_stripboard_schedule=get_domain_stripboard_spec(domain, [scene_1, scene_2]),
        master_film_emulation=domain_film,
        master_slate_spec=domain_slate,
        master_drone_spec=domain_drone,
        master_aicp_bid=get_domain_aicp_bid_spec(domain, total_runtime_seconds=total_runtime_sec or 10),
    )
    bible.master_imf_dcp = None
    bible.master_voice_ducking = None
    for sc in bible.scenes:
        sc.imf_dcp_profile = None
        sc.voice_ducking_spec = None
    _backfill_production_specs(
        bible,
        domain,
        max_render_budget_usd=(config.max_render_budget_usd if config is not None else None),
    )
    return bible


def _backfill_production_specs(
    bible: MasterProductionBible,
    arch: str,
    max_render_budget_usd: Optional[float] = None,
) -> None:
    """Backfills missing master & scene production specifications (PM-FEAT-007..032)."""
    if not getattr(bible, "master_color_look", None):
        bible.master_color_look = get_domain_color_look(arch)
    if not getattr(bible, "master_audio_mixer", None):
        bible.master_audio_mixer = get_domain_audio_mixer(arch)
    if not getattr(bible, "master_lens_package", None):
        bible.master_lens_package = get_domain_optical_lens(arch)
    if not getattr(bible, "virtual_production", None):
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
        bible.master_slate_spec = get_domain_clapper_slate_spec(arch, bible.scenes, project_title=bible.project_title)
    if not getattr(bible, "master_drone_spec", None):
        bible.master_drone_spec = get_domain_drone_spec(arch)
    if not getattr(bible, "master_aicp_bid", None):
        bible.master_aicp_bid = get_domain_aicp_bid_spec(bible, total_runtime_seconds=bible.total_runtime_seconds)

    # PM-FEAT-021: Reframe Manifest (via presets if available in Wave 2, else direct tool synthesizer)
    if not getattr(bible, "master_reframe_manifest", None):
        reframe_fn = getattr(_presets_mod, "get_domain_reframe_manifest", None)
        if callable(reframe_fn):
            bible.master_reframe_manifest = reframe_fn(bible)
        else:
            bible.master_reframe_manifest = synthesize_default_reframe_manifest(bible)

    # PM-FEAT-022: Broadcast QC Manifest (via presets if available in Wave 2, else direct tool synthesizer)
    if not getattr(bible, "master_broadcast_qc", None):
        qc_fn = getattr(_presets_mod, "get_domain_broadcast_qc_spec", None)
        if callable(qc_fn):
            bible.master_broadcast_qc = qc_fn(bible)
        else:
            bible.master_broadcast_qc = synthesize_default_broadcast_qc_spec(bible)

    # PM-FEAT-023: 180-Degree Continuity Axis & Blocking Floorplan (via presets if available in Phase 2a, else tool synthesizer)
    if not getattr(bible, "master_continuity_blocking", None):
        blocking_fn = getattr(_presets_mod, "get_domain_continuity_blocking_spec", None)
        if callable(blocking_fn):
            bible.master_continuity_blocking = blocking_fn(bible)
        else:
            bible.master_continuity_blocking = synthesize_default_continuity_blocking(bible)

    # PM-FEAT-024: Client Review Notes & Signoff Gate (via presets if available in Phase 2a, else tool synthesizer)
    if not getattr(bible, "master_client_review", None):
        review_fn = getattr(_presets_mod, "get_domain_client_review_spec", None)
        if callable(review_fn):
            bible.master_client_review = review_fn(bible)
        else:
            bible.master_client_review = synthesize_default_client_review(bible)

    # PM-FEAT-025: C2PA Content Credentials v2.1 & Talent Likeness Provenance
    if not getattr(bible, "master_c2pa_provenance", None):
        bible.master_c2pa_provenance = get_domain_c2pa_provenance_spec(
            bible, bible.scenes, project_title=bible.project_title
        )

    # PM-FEAT-026: On-Set Stunt, Pyro/SFX, Rigging & Environmental Safety JSA
    if not getattr(bible, "master_safety_risk", None):
        bible.master_safety_risk = get_domain_safety_risk_spec(
            bible, bible.scenes, project_title=bible.project_title
        )

    # PM-FEAT-027: Multi-Territory Localization, ADR Dubbing & Safe-Supers Manifest
    if not getattr(bible, "localization_manifest", None):
        bible.localization_manifest = compile_localization_manifest(bible)

    # PM-FEAT-028: Editorial J-Cut / L-Cut Audio Bridge & BPM Beat-Grid Spotting Manifest
    if not getattr(bible, "spotting_manifest", None):
        bible.spotting_manifest = build_spotting_manifest(bible, fps=24)

    # PM-FEAT-029: S3D Rig Manifest
    if not getattr(bible, "master_s3d_spec", None):
        try:
            from omni_director.tools.stereoscopic_3d import compile_s3d_manifest
            bible.master_s3d_spec = compile_s3d_manifest(bible)
        except Exception:
            pass

    # PM-FEAT-030: Accessibility AD Manifest
    if not getattr(bible, "master_accessibility_spec", None):
        try:
            from omni_director.tools.accessibility_ad import compile_accessibility_manifest
            bible.master_accessibility_spec = compile_accessibility_manifest(bible)
        except Exception:
            pass

    # PM-FEAT-031: Wardrobe, Prop & Art Dressing Continuity Bible
    if not getattr(bible, "master_wardrobe_prop_bible", None):
        wp_fn = getattr(_presets_mod, "get_domain_wardrobe_prop_spec", None)
        if callable(wp_fn):
            bible.master_wardrobe_prop_bible = wp_fn(bible)
        else:
            bible.master_wardrobe_prop_bible = compile_wardrobe_prop_bible(bible)

    # PM-FEAT-032: AI Compute, Take-Budget & Render Economics Manifest
    budget_cap = (
        float(max_render_budget_usd)
        if max_render_budget_usd is not None
        else float(getattr(cfg, "max_render_budget_usd", 50.0))
    )
    if not getattr(bible, "master_render_economics_spec", None):
        econ_fn = getattr(_presets_mod, "get_domain_render_economics_spec", None)
        if callable(econ_fn):
            try:
                bible.master_render_economics_spec = econ_fn(bible, max_budget_usd=budget_cap)
            except TypeError:
                bible.master_render_economics_spec = econ_fn(bible)
        else:
            bible.master_render_economics_spec = compile_render_economics_manifest(
                bible, max_budget_usd=budget_cap
            )

    econ_spec = getattr(bible, "master_render_economics_spec", None)
    if econ_spec is not None and getattr(econ_spec, "guardrail", None) is not None:
        if max_render_budget_usd is not None or abs(float(econ_spec.guardrail.max_render_budget_usd) - budget_cap) > 1e-6:
            est_total = float(getattr(econ_spec.guardrail, "estimated_total_usd", 0.0) or 0.0)
            econ_spec.guardrail.max_render_budget_usd = budget_cap
            econ_spec.guardrail.within_budget = est_total <= budget_cap
            econ_spec.guardrail.utilization_pct = (
                round((est_total / budget_cap) * 100.0, 2) if budget_cap > 0 else 100.0
            )

    slate_scenes = getattr(bible.master_slate_spec, "scenes", []) if bible.master_slate_spec else []
    reframe_scenes = getattr(bible.master_reframe_manifest, "scene_reframes", []) if bible.master_reframe_manifest else []
    qc_scenes = getattr(bible.master_broadcast_qc, "scene_qc_profiles", []) if bible.master_broadcast_qc else []
    blocking_scenes = getattr(bible.master_continuity_blocking, "scene_blockings", []) if bible.master_continuity_blocking else []
    review_scenes = getattr(bible.master_client_review, "scene_reviews", []) if bible.master_client_review else []
    c2pa_scenes = getattr(bible.master_c2pa_provenance, "scene_provenances", []) if bible.master_c2pa_provenance else []
    safety_scenes = getattr(bible.master_safety_risk, "scene_safety_specs", []) if bible.master_safety_risk else []
    art_scenes = getattr(bible.master_wardrobe_prop_bible, "scene_art_specs", []) if getattr(bible, "master_wardrobe_prop_bible", None) else []
    econ_scenes = getattr(bible.master_render_economics_spec, "scene_estimates", []) if getattr(bible, "master_render_economics_spec", None) else []

    # PM-FEAT-033: Motion Graphics, Kinetic Typography & Brand End-Card Manifest
    if not getattr(bible, "master_motion_graphics", None):
        gfx_fn = getattr(_presets_mod, "get_domain_motion_graphics_spec", None)
        if callable(gfx_fn):
            gfx_res = gfx_fn(bible)
            if isinstance(gfx_res, MasterMotionGraphicsManifest):
                bible.master_motion_graphics = gfx_res
            elif isinstance(gfx_res, dict):
                bible.master_motion_graphics = compile_motion_graphics_manifest(
                    bible, domain_calibration=gfx_res
                )
            else:
                bible.master_motion_graphics = compile_motion_graphics_manifest(bible)
        else:
            bible.master_motion_graphics = compile_motion_graphics_manifest(bible)
    gfx_scenes = (
        getattr(bible.master_motion_graphics, "scene_graphics", [])
        if getattr(bible, "master_motion_graphics", None)
        else []
    )

    for idx, scene in enumerate(bible.scenes):
        if not getattr(scene, "speed_ramp", None):
            scene.speed_ramp = get_domain_speed_ramp(arch)
        if not getattr(scene, "scene_color_look", None):
            scene.scene_color_look = bible.master_color_look
        if not getattr(scene, "optical_lens", None):
            scene.optical_lens = bible.master_lens_package
        if not getattr(scene, "virtual_production", None):
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
            scene.breakdown_sheet = extract_script_breakdown_sheet(scene, scene.scene_index)
        if not getattr(scene, "film_emulation", None):
            scene.film_emulation = bible.master_film_emulation
        if not getattr(scene, "clapper_slate", None) and idx < len(slate_scenes):
            scene.clapper_slate = slate_scenes[idx]
        if not getattr(scene, "drone_flight", None):
            scene.drone_flight = bible.master_drone_spec
        if not getattr(scene, "reframe_spec", None):
            if idx < len(reframe_scenes):
                scene.reframe_spec = reframe_scenes[idx]
            else:
                scene.reframe_spec = synthesize_default_scene_reframe(scene=scene, scene_index=scene.scene_index, domain=arch)
        if not getattr(scene, "broadcast_qc", None):
            if idx < len(qc_scenes):
                scene.broadcast_qc = qc_scenes[idx]
            else:
                scene.broadcast_qc = synthesize_default_scene_qc(scene=scene, scene_index=scene.scene_index)
        if not getattr(scene, "blocking_spec", None):
            if idx < len(blocking_scenes):
                scene.blocking_spec = blocking_scenes[idx]
            else:
                prev_blk = bible.scenes[idx - 1].blocking_spec if idx > 0 else None
                scene.blocking_spec = synthesize_scene_blocking(
                    scene=scene,
                    scene_index=scene.scene_index,
                    domain=arch,
                    prev_blocking=prev_blk,
                )
        if not getattr(scene, "review_signoff", None):
            if idx < len(review_scenes):
                scene.review_signoff = review_scenes[idx]
            else:
                scene.review_signoff = synthesize_scene_review_signoff(
                    scene=scene,
                    scene_index=scene.scene_index,
                    domain=arch,
                )
        if not getattr(scene, "c2pa_provenance", None):
            if idx < len(c2pa_scenes):
                scene.c2pa_provenance = c2pa_scenes[idx]
            else:
                scene.c2pa_provenance = synthesize_scene_c2pa_provenance(
                    scene=scene,
                    scene_index=scene.scene_index,
                    bible=bible,
                    domain=arch,
                )
        if not getattr(scene, "safety_risk", None):
            if idx < len(safety_scenes):
                scene.safety_risk = safety_scenes[idx]
            else:
                scene.safety_risk = assess_scene_hazards(
                    scene=scene,
                    scene_index=scene.scene_index,
                    domain=arch,
                    bible=bible,
                )
        if not getattr(scene, "locale_tracks", None) and getattr(bible, "localization_manifest", None):
            loc_manifest = bible.localization_manifest
            tracks = []
            for terr in (getattr(loc_manifest, "territories", None) or []):
                terr_cues = [
                    c for c in (getattr(loc_manifest, "adr_cues", None) or [])
                    if c.locale == terr.bcp47_tag
                ]
                for cue, line_spec in zip(terr_cues, (getattr(terr, "lines", None) or [])):
                    if cue.scene_number == scene.scene_index:
                        tracks.append(line_spec)
            scene.locale_tracks = tracks
        if not getattr(scene, "edit_bridge_in", None) and getattr(bible, "spotting_manifest", None):
            for br in (getattr(bible.spotting_manifest, "bridges", None) or []):
                if br.to_scene == scene.scene_index:
                    scene.edit_bridge_in = br
                    break

        if not getattr(scene, "s3d_spec", None) and getattr(bible, "master_s3d_spec", None):
            for s_spec in (getattr(bible.master_s3d_spec, "scene_specs", None) or []):
                if getattr(s_spec, "scene_number", None) == scene.scene_index:
                    scene.s3d_spec = s_spec
                    break
                    
        if not getattr(scene, "accessibility_spec", None) and getattr(bible, "master_accessibility_spec", None):
            for p_spec in (getattr(bible.master_accessibility_spec, "scene_profiles", None) or []):
                # The profile typically has ad_cues; wait, does it have scene_number? Let's check matching logic or just attach the profile that has ad_cues for this scene
                # Actually, accessibility_spec on the scene might just be a SceneAccessibilityProfileSpec
                if getattr(p_spec, "scene_number", None) == scene.scene_index:
                    scene.accessibility_spec = p_spec
                    break

        if not getattr(scene, "art_continuity_spec", None) and art_scenes:
            matched_art = next(
                (a_spec for a_spec in art_scenes if getattr(a_spec, "scene_index", None) == scene.scene_index),
                None,
            )
            if matched_art is not None:
                scene.art_continuity_spec = matched_art

        if not getattr(scene, "compute_estimate_spec", None) and econ_scenes:
            matched_econ = next(
                (e_spec for e_spec in econ_scenes if getattr(e_spec, "scene_index", None) == scene.scene_index),
                None,
            )
            if matched_econ is not None:
                scene.compute_estimate_spec = matched_econ

        if not getattr(scene, "motion_graphics_spec", None) and gfx_scenes:
            matched_gfx = next(
                (g_spec for g_spec in gfx_scenes if getattr(g_spec, "scene_index", None) == scene.scene_index),
                None,
            )
            if matched_gfx is None and idx < len(gfx_scenes):
                matched_gfx = gfx_scenes[idx]
            if matched_gfx is not None:
                scene.motion_graphics_spec = matched_gfx

    # PM-FEAT-034: OpenTimelineIO (OTIO) Multi-Track & Cross-Department Coherence Manifest (hydrated LAST)
    if not getattr(bible, "master_otio_coherence", None):
        otio_fn = getattr(_presets_mod, "get_domain_otio_coherence_spec", None)
        if callable(otio_fn):
            otio_res = otio_fn(bible)
            if isinstance(otio_res, MasterOtioCoherenceManifest):
                bible.master_otio_coherence = otio_res
            elif isinstance(otio_res, dict):
                reconciled_bible = reconcile_cross_department_conflicts(bible, tolerances=otio_res)
                bible.master_otio_coherence = compile_otio_coherence_manifest(
                    reconciled_bible, tolerances=otio_res, auto_reconcile=True
                )
                for _attr in (
                    "master_dof_spec",
                    "dof_spec",
                    "master_lighting_rig",
                    "master_continuity_blocking",
                    "continuity_blocking",
                    "master_audio_mixer",
                    "spotting_manifest",
                    "editorial_spotting",
                    "master_motion_graphics",
                    "master_reframe_manifest",
                    "reframe_manifest",
                ):
                    _val = getattr(reconciled_bible, _attr, None)
                    if _val is not None and hasattr(bible, _attr):
                        setattr(bible, _attr, _val)
                _reconciled_gfx = getattr(bible, "master_motion_graphics", None)
                _gfx_by_scene = {
                    int(getattr(sg, "scene_index", 0) or 0): sg
                    for sg in list(getattr(_reconciled_gfx, "scene_graphics", None) or [])
                }
                for _src_sc, _dst_sc in zip(
                    list(getattr(reconciled_bible, "scenes", None) or []),
                    list(getattr(bible, "scenes", None) or []),
                ):
                    for _sc_attr in ("dof_spec", "motion_graphics_spec", "otio_sync_token"):
                        _sc_val = getattr(_src_sc, _sc_attr, None)
                        if _sc_val is not None and hasattr(_dst_sc, _sc_attr):
                            setattr(_dst_sc, _sc_attr, _sc_val)
                    _sc_idx = int(getattr(_dst_sc, "scene_index", 0) or 0)
                    if _sc_idx in _gfx_by_scene and getattr(_dst_sc, "motion_graphics_spec", None) is not None:
                        _dst_sc.motion_graphics_spec = _gfx_by_scene[_sc_idx]
            else:
                bible.master_otio_coherence = compile_otio_coherence_manifest(
                    bible, auto_reconcile=True
                )
        else:
            bible.master_otio_coherence = compile_otio_coherence_manifest(
                bible, auto_reconcile=True
            )

    otio_manifest = getattr(bible, "master_otio_coherence", None)
    if otio_manifest is not None:
        if not getattr(otio_manifest, "coherence_token", ""):
            otio_manifest.coherence_token = format_otio_coherence_token(otio_manifest)
        for scene in bible.scenes:
            if not getattr(scene, "otio_sync_token", None):
                scene.otio_sync_token = otio_manifest.coherence_token

    # PM-FEAT-035: Live-Render Job Orchestrator, Multi-Take QA & Mode B Frame-Anchor Continuity
    if not getattr(bible, "master_render_jobs", None):
        rj_fn = getattr(_presets_mod, "get_domain_render_job_spec", None)
        if callable(rj_fn):
            rj_cal = rj_fn(bible)
            if isinstance(rj_cal, MasterRenderJobManifest):
                bible.master_render_jobs = rj_cal
            elif isinstance(rj_cal, dict):
                bible.master_render_jobs = compile_render_job_manifest(
                    bible, domain_calibration=rj_cal, dry_run=True
                )
            else:
                bible.master_render_jobs = compile_render_job_manifest(bible, dry_run=True)
        else:
            bible.master_render_jobs = compile_render_job_manifest(bible, dry_run=True)

    rj_manifest = getattr(bible, "master_render_jobs", None)
    if rj_manifest is not None:
        rj_by_scene = {
            int(getattr(j, "scene_index", 0) or 0): j
            for j in list(getattr(rj_manifest, "jobs", None) or [])
        }
        for idx, scene in enumerate(bible.scenes):
            if not getattr(scene, "render_job_spec", None):
                matched_rj = rj_by_scene.get(int(scene.scene_index))
                if matched_rj is None and idx < len(getattr(rj_manifest, "jobs", None) or []):
                    matched_rj = rj_manifest.jobs[idx]
                if matched_rj is not None:
                    scene.render_job_spec = matched_rj

    # PM-FEAT-036: Executive Director's Treatment & Print-Ready Pitch Lookbook
    if not getattr(bible, "master_pitch_treatment", None):
        pt_fn = getattr(_presets_mod, "get_domain_pitch_treatment_spec", None)
        if callable(pt_fn):
            pt_cal = pt_fn(bible)
            if isinstance(pt_cal, MasterPitchTreatmentSpec):
                bible.master_pitch_treatment = pt_cal
            elif isinstance(pt_cal, dict):
                bible.master_pitch_treatment = compile_pitch_treatment(
                    bible, domain_calibration=pt_cal
                )
            else:
                bible.master_pitch_treatment = compile_pitch_treatment(bible)
        else:
            bible.master_pitch_treatment = compile_pitch_treatment(bible)

    pt_manifest = getattr(bible, "master_pitch_treatment", None)
    if pt_manifest is not None:
        pt_by_scene = {
            int(getattr(sl, "scene_index", 0) or 0): sl
            for sl in list(getattr(pt_manifest, "slides", None) or [])
            if getattr(sl, "scene_index", None) is not None
        }
        for scene in bible.scenes:
            if not getattr(scene, "treatment_spec", None):
                matched_sl = pt_by_scene.get(int(scene.scene_index))
                if matched_sl is not None:
                    scene.treatment_spec = matched_sl

    # PM-FEAT-037 & PM-FEAT-038: SMPTE IMF/DCP Supplemental Packaging & Voice Casting / Sidechain Ducking
    imf_fn = getattr(_presets_mod, "get_domain_imf_dcp_profile", None)
    vd_fn = getattr(_presets_mod, "get_domain_voice_ducking_profile", None)
    imf_profile = imf_fn(arch) if callable(imf_fn) else get_domain_imf_dcp_profile(arch)
    vd_profile = vd_fn(arch) if callable(vd_fn) else get_domain_voice_ducking_profile(arch)
    hydrate_imf_dcp_and_voice_ducking_specs(bible, imf_profile, vd_profile)


class IntakeAndResearchAgent(BaseAgent):
    """Stage 1: Ingests user creative loglines, references, and research parameters."""

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    def __init__(
        self,
        config: Optional[DirectorConfig] = None,
        *,
        name: Optional[str] = None,
        model_name: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        agent_name = name or "IntakeAndResearchAgent"
        cfg_val = config or cfg
        desc = kwargs.pop("description", kwargs.pop("instruction", "Ingests creative brief and grounds aesthetic tone, pacing, and visual style."))
        super().__init__(
            name=agent_name,
            description=desc,
            **kwargs,
        )
        self.config = cfg_val
        self.name = agent_name
        self.instruction = desc
        self.model_name = model_name or self.config.fast_model
        validate_model_identifier(self.model_name, f"{agent_name}.model_name")

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        prompt = context.get("raw_prompt") or ""
        preset = context.get("preset_name")
        logger.info(f"[{self.name}] Analyzing intake brief. Preset: {preset}, Prompt: {prompt[:60]}...")

        # Live research generation if configured
        if not self.config.dry_run and self.config.api_key and prompt:
            try:
                from google import genai
                client = genai.Client(api_key=self.config.api_key)
                response = client.models.generate_content(
                    model=self.config.fast_model,
                    contents=f"Conduct rapid creative research and visual direction grounding for: {prompt}"
                )
                if response and getattr(response, "text", None):
                    context["research_notes"] = response.text
            except Exception as e:
                logger.warning(f"[{self.name}] Live intake query failed: {e}. Falling back to dry-run analysis.")

        if not context.get("domain_archetype") and prompt:
            context["domain_archetype"] = classify_brief_domain(prompt)

        context["intake_complete"] = True
        return context


class CreativeDirectorAgent(BaseAgent):
    """Stage 2: Single Source of Truth (SSOT). Synthesizes or loads the MasterProductionBible."""

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    def __init__(
        self,
        config: Optional[DirectorConfig] = None,
        *,
        name: Optional[str] = None,
        model_name: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        cfg_val = config or cfg
        agent_name = name or "CreativeDirectorAgent"
        desc = kwargs.pop("description", kwargs.pop("instruction", f"Authoritative director utilizing {cfg_val.director_model}."))
        super().__init__(
            name=agent_name,
            description=desc,
            **kwargs,
        )
        self.config = cfg_val
        self.name = agent_name
        self.instruction = desc
        self.model_name = model_name or self.config.director_model
        validate_model_identifier(self.model_name, f"{agent_name}.model_name")

    def synthesize_custom_bible(
        self,
        raw_prompt: str = "",
        project_title: Optional[str] = None,
        creative_brief: Optional[str] = None,
        genre: Optional[str] = None,
        aspect_ratio: Optional[AspectRatio] = None,
        total_runtime_sec: Optional[int] = None,
        storytelling_mode: StorytellingMode = StorytellingMode.MODE_A_PARALLEL_CUT,
    ) -> MasterProductionBible:
        """Synthesizes a domain-aware MasterProductionBible from custom creative brief."""
        return synthesize_custom_bible(
            raw_prompt=raw_prompt,
            config=self.config,
            storytelling_mode=storytelling_mode,
            project_title=project_title,
            creative_brief=creative_brief,
            genre=genre,
            aspect_ratio=aspect_ratio,
            total_runtime_sec=total_runtime_sec,
        )

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:

        logger.info(f"[{self.name}] Synthesizing Master Production Bible...")
        continuous_mode = bool(context.get("continuous_mode", False))
        target_mode = (
            StorytellingMode.MODE_B_CONTINUOUS_CHAIN
            if continuous_mode
            else StorytellingMode.MODE_A_PARALLEL_CUT
        )
        bible = None
        if "bible" in context and isinstance(context["bible"], MasterProductionBible):
            bible = context["bible"].model_copy(deep=True)
        elif context.get("preset_name"):
            bible = get_preset_bible(context["preset_name"])
        else:
            raw_prompt = context.get("raw_prompt") or ""
            # Live structured generation if live mode requested
            if not self.config.dry_run and self.config.api_key and raw_prompt:
                try:
                    from google import genai
                    from google.genai import types
                    client = genai.Client(api_key=self.config.api_key)
                    sys_instruction = (
                        "You are an elite commercial movie director synthesizing a MasterProductionBible. "
                        "Follow the 7-Point Gemini Omni Prompt Standard: max 3 action beats per 10s scene, "
                        "1.0x speed lock for kinetic scenes, CRAFT camera rig, diegetic audio, max 3 image references, "
                        "and clean unbroken prose without markdown headers in omni_prose_prompt."
                    )
                    response = client.models.generate_content(
                        model=self.config.director_model,
                        contents=f"Direct this cinematic commercial / scene sequence: {raw_prompt}",
                        config=types.GenerateContentConfig(
                            system_instruction=sys_instruction,
                            response_mime_type="application/json",
                            response_schema=MasterProductionBible,
                        )
                    )
                    if response and getattr(response, "text", None):
                        bible = MasterProductionBible.model_validate_json(response.text)
                except Exception as e:
                    logger.warning(f"[{self.name}] Live bible synthesis failed: {e}. Falling back to synthesizer.")

            # Fallback or dry-run prompt synthesis:
            # ONLY synthesize a custom bible when raw_prompt is provided, or default to ikea-asmr when both preset and prompt are empty.
            if bible is None:
                if raw_prompt and raw_prompt.strip():
                    bible = synthesize_custom_bible(raw_prompt, self.config, storytelling_mode=target_mode)
                else:
                    bible = get_preset_bible("ikea-asmr")

        if bible is not None:
            if continuous_mode and bible.storytelling_mode != StorytellingMode.MODE_B_CONTINUOUS_CHAIN and bible.total_runtime_seconds <= 40:
                bible.storytelling_mode = StorytellingMode.MODE_B_CONTINUOUS_CHAIN
            if not getattr(bible, "domain_archetype", None):
                bible.domain_archetype = context.get("domain_archetype") or classify_brief_domain(f"{bible.project_title} {bible.logline}")
            _backfill_production_specs(
                bible,
                bible.domain_archetype,
                max_render_budget_usd=context.get("max_render_budget_usd", self.config.max_render_budget_usd),
            )

        context["bible"] = bible
        logger.info(f"[{self.name}] Sealed Bible: '{bible.project_title}' with {len(bible.scenes)} scenes.")
        return context


class VisualStoryboardAgent(BaseAgent):
    """Stage 3: Generates visual plates and keyframes via NanoBananaStoryboardEngine."""

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    def __init__(
        self,
        config: Optional[DirectorConfig] = None,
        *,
        name: Optional[str] = None,
        model_name: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        cfg_val = config or cfg
        agent_name = name or "VisualStoryboardAgent"
        desc = kwargs.pop("description", kwargs.pop("instruction", "Generates turnaround sheets, environment plates, and keyframes."))
        super().__init__(
            name=agent_name,
            description=desc,
            **kwargs,
        )
        self.config = cfg_val
        self.name = agent_name
        self.instruction = desc
        self.model_name = model_name or self.config.image_model
        validate_model_identifier(self.model_name, f"{agent_name}.model_name")
        self.engine = NanoBananaStoryboardEngine(config=self.config)

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        bible: MasterProductionBible = context["bible"]
        output_dir = Path(context.get("output_dir", self.config.output_dir))
        logger.info(f"[{self.name}] Generating Nano Banana visual anchor plates for '{bible.project_title}'...")
        rendered_assets = self.engine.generate_all_storyboard_plates(bible, output_dir=output_dir)
        context["visual_plates"] = rendered_assets
        return context


class ScenePromptAgent(BaseAgent):
    """Stage 4a: Builds and refines scene-level Gemini Omni prompts for a specific scene index."""

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    def __init__(
        self,
        scene_index: int = 1,
        config: Optional[DirectorConfig] = None,
        *,
        name: Optional[str] = None,
        model_name: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        cfg_val = config or cfg
        agent_name = name or f"ScenePromptAgent_{scene_index}"
        desc = kwargs.pop("description", kwargs.pop("instruction", "Enforces CRAFT camera grammar, 1.0x speed lock, and acoustic foley cues."))
        super().__init__(
            name=agent_name,
            description=desc,
            **kwargs,
        )
        self.scene_index = scene_index
        self.config = cfg_val
        self.name = agent_name
        self.instruction = desc
        self.model_name = model_name or self.config.fast_model
        validate_model_identifier(self.model_name, f"{agent_name}.model_name")

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        bible: MasterProductionBible = context["bible"]
        matching = [s for s in bible.scenes if s.scene_index == self.scene_index]
        if matching:
            scene = matching[0]
            # Live API prompt refinement if enabled
            if not self.config.dry_run and self.config.api_key:
                try:
                    from google import genai
                    client = genai.Client(api_key=self.config.api_key)
                    prompt = (
                        f"Refine this scene prompt for Gemini Omni video model. "
                        f"Preserve CRAFT camera, acoustic foley, and max 3 action beats: {scene.omni_prose_prompt}"
                    )
                    res = client.models.generate_content(model=self.config.fast_model, contents=prompt)
                    if res and getattr(res, "text", None):
                        refined_text = res.text.strip().replace("\n#", "\n")
                        if "1.0x" in refined_text or scene.regime != RegimeType.REGIME_2_KINETIC:
                            scene.omni_prose_prompt = refined_text
                except Exception as e:
                    logger.warning(f"[{self.name}] Live prompt refinement failed: {e}")

            # Ensure speed lock is in prompt if Regime 2
            if scene.regime == RegimeType.REGIME_2_KINETIC and not re.search(r"\b1\.0x\b|real-time|natural speed", scene.omni_prose_prompt, re.IGNORECASE):
                scene.omni_prose_prompt += " Rendered at natural 1.0x real-time speed."

            # Ensure PM-FEAT-027 [LOCALIZATION_ADR: ...] and PM-FEAT-028 [SPOTTING_SYNC: ...] tokens are cleanly attached
            if (getattr(bible, "localization_manifest", None) is not None or getattr(scene, "locale_tracks", None)) and not re.search(
                r"\[LOCALIZATION[ _]ADR:?", scene.omni_prose_prompt, re.IGNORECASE
            ):
                loc_token = format_localization_prompt_token(bible, scene)
                scene.omni_prose_prompt = scene.omni_prose_prompt.rstrip() + f" {loc_token}."
            if (getattr(bible, "spotting_manifest", None) is not None or getattr(scene, "edit_bridge_in", None)) and not re.search(
                r"\[SPOTTING[ _]SYNC:?", scene.omni_prose_prompt, re.IGNORECASE
            ):
                spot_token = format_spotting_prompt_token(bible, scene)
                scene.omni_prose_prompt = scene.omni_prose_prompt.rstrip() + f" {spot_token}."
            if (getattr(bible, "master_s3d_spec", None) is not None or getattr(scene, "s3d_spec", None) is not None) and not re.search(
                r"\[S3D[-_ ]RIG:?", scene.omni_prose_prompt, re.IGNORECASE
            ):
                from omni_director.tools.stereoscopic_3d import format_s3d_prompt_token
                s3d_token = format_s3d_prompt_token(bible, scene)
                scene.omni_prose_prompt = scene.omni_prose_prompt.rstrip() + f" {s3d_token}."
            if (getattr(bible, "master_accessibility_spec", None) is not None or getattr(scene, "accessibility_spec", None) is not None) and not re.search(
                r"\[AD[-_ ]CUE:?", scene.omni_prose_prompt, re.IGNORECASE
            ):
                from omni_director.tools.accessibility_ad import format_ad_prompt_token
                ad_token = format_ad_prompt_token(bible, scene)
                scene.omni_prose_prompt = scene.omni_prose_prompt.rstrip() + f" {ad_token}."
            if (getattr(bible, "master_wardrobe_prop_bible", None) is not None or getattr(scene, "art_continuity_spec", None) is not None) and not (
                re.search(r"\[WARDROBE[-_ ]LOCK:?", scene.omni_prose_prompt, re.IGNORECASE)
                and re.search(r"\[PROP[-_ ]STATE:?", scene.omni_prose_prompt, re.IGNORECASE)
            ):
                art_spec = getattr(scene, "art_continuity_spec", None)
                if art_spec is not None:
                    art_token = format_art_continuity_token(art_spec)
                    scene.omni_prose_prompt = scene.omni_prose_prompt.rstrip() + f" {art_token}."
            if (getattr(bible, "master_render_economics_spec", None) is not None or getattr(scene, "compute_estimate_spec", None) is not None) and not re.search(
                r"\[RENDER[-_ ]PROFILE:?", scene.omni_prose_prompt, re.IGNORECASE
            ):
                compute_spec = getattr(scene, "compute_estimate_spec", None)
                if compute_spec is not None:
                    render_token = format_render_profile_token(compute_spec)
                    scene.omni_prose_prompt = scene.omni_prose_prompt.rstrip() + f" {render_token}."
            if (getattr(bible, "master_motion_graphics", None) is not None or getattr(scene, "motion_graphics_spec", None) is not None) and not re.search(
                r"\[GFX[-_ ]CLEANPLATE:?", scene.omni_prose_prompt, re.IGNORECASE
            ):
                gfx_spec = getattr(scene, "motion_graphics_spec", None)
                if gfx_spec is not None:
                    master_gfx = getattr(bible, "master_motion_graphics", None)
                    endcard_spec = getattr(master_gfx, "endcard", None) if master_gfx is not None else None
                    gfx_token = format_motion_graphics_token(gfx_spec, endcard=endcard_spec)
                    if not getattr(gfx_spec, "gfx_prompt_token", ""):
                        gfx_spec.gfx_prompt_token = gfx_token
                    scene.omni_prose_prompt = scene.omni_prose_prompt.rstrip() + f" {gfx_token}."
            if (getattr(bible, "master_otio_coherence", None) is not None or getattr(scene, "otio_sync_token", None)) and not re.search(
                r"\[OTIO[-_ ]SYNC:?", scene.omni_prose_prompt, re.IGNORECASE
            ):
                master_otio = getattr(bible, "master_otio_coherence", None)
                if master_otio is not None:
                    otio_token = format_otio_coherence_token(master_otio)
                    if not getattr(scene, "otio_sync_token", None):
                        scene.otio_sync_token = otio_token
                else:
                    otio_token = str(getattr(scene, "otio_sync_token", "") or "")
                if otio_token:
                    scene.omni_prose_prompt = scene.omni_prose_prompt.rstrip() + f" {otio_token}."

            # Ensure PM-FEAT-035 [RENDER-JOB: ...] (+ [FRAME-ANCHOR: ...] in Mode B) token is attached
            master_rj = getattr(bible, "master_render_jobs", None)
            rj_spec = getattr(scene, "render_job_spec", None)
            if rj_spec is None and master_rj is not None:
                for job in (getattr(master_rj, "jobs", None) or []):
                    if getattr(job, "scene_index", None) == scene.scene_index:
                        rj_spec = job
                        scene.render_job_spec = job
                        break
            if rj_spec is not None:
                is_mode_b_scene = (
                    getattr(bible, "storytelling_mode", None) == StorytellingMode.MODE_B_CONTINUOUS_CHAIN
                    or bool(re.search(r"\+10s|extension", getattr(scene, "timestamp_range", "") or "", re.IGNORECASE))
                )
                needs_anchor = is_mode_b_scene and scene.scene_index > 1
                handoff_spec = None
                if needs_anchor and master_rj is not None:
                    for ho in (getattr(master_rj, "frame_anchor_handoffs", None) or []):
                        if getattr(ho, "to_scene_index", None) == scene.scene_index:
                            handoff_spec = ho
                            break
                has_rj_tok = bool(re.search(r"\[RENDER[-_ ]JOB:?", scene.omni_prose_prompt, re.IGNORECASE))
                has_fa_tok = bool(re.search(r"\[FRAME[-_ ]ANCHOR:?", scene.omni_prose_prompt, re.IGNORECASE))
                if not has_rj_tok or (needs_anchor and not has_fa_tok):
                    scene.omni_prose_prompt = re.sub(
                        r"\s*\[(?:RENDER[-_ ]JOB|FRAME[-_ ]ANCHOR)\s*:[^\]]*\]\.?",
                        "",
                        scene.omni_prose_prompt,
                        flags=re.IGNORECASE,
                    ).rstrip()
                    rj_token = format_render_job_token(rj_spec, handoff=handoff_spec if needs_anchor else None)
                    scene.omni_prose_prompt = scene.omni_prose_prompt + f" {rj_token}."

            # Ensure PM-FEAT-036 [TREATMENT-BEAT: ...] token is attached
            master_pt = getattr(bible, "master_pitch_treatment", None)
            pt_slide = getattr(scene, "treatment_spec", None)
            if pt_slide is None and master_pt is not None:
                for sl in (getattr(master_pt, "slides", None) or []):
                    if getattr(sl, "scene_index", None) == scene.scene_index:
                        pt_slide = sl
                        scene.treatment_spec = sl
                        break
            if pt_slide is not None and not re.search(
                r"\[TREATMENT[-_ ]BEAT:?", scene.omni_prose_prompt, re.IGNORECASE
            ):
                if master_pt is not None:
                    treat_token = format_pitch_treatment_token(pt_slide, master_pt)
                else:
                    s_type = pt_slide.slide_type.value if hasattr(pt_slide.slide_type, "value") else str(pt_slide.slide_type)
                    treat_token = f"[TREATMENT-BEAT: SC{scene.scene_index:02d} | slide={s_type} | headline={pt_slide.headline[:48]}]"
                scene.omni_prose_prompt = scene.omni_prose_prompt.rstrip() + f" {treat_token}."

            # Ensure PM-FEAT-037 [IMF-CPL: ...] token is attached
            master_imf = getattr(bible, "master_imf_dcp", None)
            if (master_imf is not None or getattr(scene, "imf_dcp_profile", None) is not None) and not re.search(
                r"\[IMF[-_ ]CPL:?", scene.omni_prose_prompt, re.IGNORECASE
            ):
                if master_imf is not None:
                    imf_token = format_imf_dcp_token(master_imf, scene.scene_index)
                    scene.omni_prose_prompt = scene.omni_prose_prompt.rstrip() + f" {imf_token}."

            # Ensure PM-FEAT-038 [VOICE-CAST: ...] token is attached
            master_vd = getattr(bible, "master_voice_ducking", None)
            if (master_vd is not None or getattr(scene, "voice_ducking_spec", None) is not None) and not re.search(
                r"\[VOICE[-_ ]CAST:?", scene.omni_prose_prompt, re.IGNORECASE
            ):
                if master_vd is not None:
                    vd_token = format_voice_ducking_token(master_vd, scene.scene_index)
                    scene.omni_prose_prompt = scene.omni_prose_prompt.rstrip() + f" {vd_token}."
        return context


class BGMComposerAgent(BaseAgent):
    """Stage 4b: Film Composer agent structuring score blueprint."""

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    def __init__(
        self,
        config: Optional[DirectorConfig] = None,
        *,
        name: Optional[str] = None,
        model_name: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        cfg_val = config or cfg
        agent_name = name or "BGMComposerAgent"
        desc = kwargs.pop("description", kwargs.pop("instruction", "Synthesizes musical score and Lyria prompt."))
        super().__init__(
            name=agent_name,
            description=desc,
            **kwargs,
        )
        self.config = cfg_val
        self.name = agent_name
        self.instruction = desc
        self.model_name = model_name or self.config.fast_model
        validate_model_identifier(self.model_name, f"{agent_name}.model_name")

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        bible: MasterProductionBible = context["bible"]
        # Live BGM Lyria prompt refinement if enabled
        if not self.config.dry_run and self.config.api_key:
            try:
                from google import genai
                client = genai.Client(api_key=self.config.api_key)
                prompt = f"Compose synchronized Lyria BGM prompt for film '{bible.project_title}': {bible.master_bgm.lyria_prompt}"
                res = client.models.generate_content(model=self.config.fast_model, contents=prompt)
                if res and getattr(res, "text", None):
                    bible.master_bgm.lyria_prompt = res.text.strip()
            except Exception as e:
                logger.warning(f"[{self.name}] Live BGM composition failed: {e}")

        logger.info(f"[{self.name}] BGM Track: '{bible.master_bgm.track_title}' ({bible.master_bgm.tempo_bpm} BPM).")
        return context


class ParallelScenePromptAgent(ParallelAgent):
    """Stage 4: Parallel scene prompt fan-out agent running on fast workhorse (gemini-3.8-flash)."""

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    def __init__(
        self,
        sub_agents: Optional[List[BaseAgent]] = None,
        config: Optional[DirectorConfig] = None,
        *,
        name: Optional[str] = None,
        model_name: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        cfg_val = config or cfg
        agent_name = name or "ParallelScenePromptAgent"
        desc = kwargs.pop("description", kwargs.pop("instruction", "Parallel scene prompt fan-out agent."))
        sub_list = list(sub_agents or [])
        super().__init__(name=agent_name, description=desc, sub_agents=sub_list, **kwargs)
        self.config = cfg_val
        self.name = agent_name
        self.instruction = desc
        self.model_name = model_name or self.config.fast_model
        validate_model_identifier(self.model_name, f"{agent_name}.model_name")
        self.sub_agents = sub_list

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute all sub-agents over the shared context."""
        if not self.sub_agents and isinstance(context.get("bible"), MasterProductionBible):
            for s in context["bible"].scenes:
                context = ScenePromptAgent(s.scene_index, self.config).run(context)
            return context
        for agent in self.sub_agents:
            context = agent.run(context)
        return context


class PromptAuditorAgent(BaseAgent):
    """Stage 5: 7-point prompt auditor evaluating scene prompts against Gemini Omni rules."""

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    def __init__(
        self,
        config: Optional[DirectorConfig] = None,
        *,
        name: Optional[str] = None,
        model_name: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        cfg_val = config or cfg
        agent_name = name or "PromptAuditorAgent"
        desc = kwargs.pop("description", kwargs.pop("instruction", "Audits all scene prompts against the 7-Point Gemini Omni Prompt Standard."))
        super().__init__(
            name=agent_name,
            description=desc,
            **kwargs,
        )
        self.config = cfg_val
        self.name = agent_name
        self.instruction = desc
        self.model_name = model_name or self.config.fast_model
        validate_model_identifier(self.model_name, f"{agent_name}.model_name")

    def run(self, context: Union[Dict[str, Any], MasterProductionBible]) -> Dict[str, Any]:
        if isinstance(context, MasterProductionBible):
            context = {"bible": context}
        bible: MasterProductionBible = context["bible"]
        logger.info(f"[{self.name}] Auditing {len(bible.scenes)} scene prompts...")
        audit_results: List[AuditResult] = []
        all_passed = True

        for scene in bible.scenes:
            result = audit_omni_scene_prompt(
                scene,
                regime=bible.creative_regime,
                storytelling_mode=getattr(bible, "storytelling_mode", None),
                bible=bible,
            )
            needs_loc_token = bool(
                (getattr(bible, "localization_manifest", None) is not None or getattr(scene, "locale_tracks", None))
                and not re.search(r"\[LOCALIZATION[ _]ADR:?", scene.omni_prose_prompt, re.IGNORECASE)
            )
            needs_spot_token = bool(
                (getattr(bible, "spotting_manifest", None) is not None or getattr(scene, "edit_bridge_in", None))
                and not re.search(r"\[SPOTTING[ _]SYNC:?", scene.omni_prose_prompt, re.IGNORECASE)
            )

            needs_s3d_token = bool(
                getattr(scene, "s3d_spec", None) is not None
                and not re.search(r"\[S3D[-_ ]RIG:?", scene.omni_prose_prompt, re.IGNORECASE)
            )
            needs_ad_token = bool(
                getattr(scene, "accessibility_spec", None) is not None
                and not re.search(r"\[AD[-_ ]CUE:?", scene.omni_prose_prompt, re.IGNORECASE)
            )
            art_spec = getattr(scene, "art_continuity_spec", None)
            needs_art_token = bool(
                art_spec is not None
                and not (
                    re.search(r"\[WARDROBE[-_ ]LOCK:?", scene.omni_prose_prompt, re.IGNORECASE)
                    and re.search(r"\[PROP[-_ ]STATE:?", scene.omni_prose_prompt, re.IGNORECASE)
                )
            )
            art_compliance_fail = bool(
                art_spec is not None
                and (
                    len(getattr(art_spec, "assigned_reference_slots", None) or []) > 3
                    or getattr(art_spec, "slot_contention_detected", False)
                )
            )
            compute_spec = getattr(scene, "compute_estimate_spec", None)
            needs_render_profile_token = bool(
                compute_spec is not None
                and not re.search(r"\[RENDER[-_ ]PROFILE:?", scene.omni_prose_prompt, re.IGNORECASE)
            )
            gfx_spec = getattr(scene, "motion_graphics_spec", None)
            needs_gfx_token = bool(
                gfx_spec is not None
                and not re.search(r"\[GFX[-_ ]CLEANPLATE:?", scene.omni_prose_prompt, re.IGNORECASE)
            )
            gfx_compliance_fail = not getattr(result, "motion_graphics_compliant", True)
            master_otio = getattr(bible, "master_otio_coherence", None)
            needs_otio_token = bool(
                (master_otio is not None or getattr(scene, "otio_sync_token", None))
                and not re.search(r"\[OTIO[-_ ]SYNC:?", scene.omni_prose_prompt, re.IGNORECASE)
            )
            otio_compliance_fail = not getattr(result, "otio_coherence_compliant", True)
            rj_spec = getattr(scene, "render_job_spec", None)
            needs_rj_token = bool(
                (rj_spec is not None or getattr(bible, "master_render_jobs", None) is not None)
                and not re.search(r"\[RENDER[-_ ]JOB:?", scene.omni_prose_prompt, re.IGNORECASE)
            )
            rj_compliance_fail = not getattr(result, "render_orchestrator_compliant", True)
            pt_spec = getattr(scene, "treatment_spec", None)
            needs_pt_token = bool(
                (pt_spec is not None or getattr(bible, "master_pitch_treatment", None) is not None)
                and not re.search(r"\[TREATMENT[-_ ]BEAT:?", scene.omni_prose_prompt, re.IGNORECASE)
            )
            pt_compliance_fail = not getattr(result, "pitch_treatment_compliant", True)
            imf_compliance_fail = not getattr(result, "imf_dcp_compliant", True)
            vd_compliance_fail = not getattr(result, "voice_ducking_compliant", True)
            
            s3d_compliance_fail = False
            s3d_spec = getattr(scene, "s3d_spec", None)
            if s3d_spec and getattr(s3d_spec, "max_positive_parallax_pct", 0.0) > 3.0:
                s3d_compliance_fail = True
                
            ad_compliance_fail = False
            ad_spec = getattr(scene, "accessibility_spec", None)
            if ad_spec and not getattr(ad_spec, "cvaa_compliant", True):
                ad_compliance_fail = True

            if (
                not result.passed
                or result.score < 100.0
                or result.warnings
                or needs_loc_token
                or needs_spot_token
                or needs_s3d_token
                or needs_ad_token
                or needs_art_token
                or art_compliance_fail
                or needs_render_profile_token
                or needs_gfx_token
                or gfx_compliance_fail
                or needs_otio_token
                or otio_compliance_fail
                or needs_rj_token
                or rj_compliance_fail
                or needs_pt_token
                or pt_compliance_fail
                or imf_compliance_fail
                or vd_compliance_fail
                or s3d_compliance_fail
                or ad_compliance_fail
            ):
                logger.info(f"[{self.name}] Attempting self-healing for scene {scene.scene_index}...")
                healed_target, result = heal_omni_scene_prompt(
                    scene,
                    audit_result=result,
                    regime=bible.creative_regime,
                    storytelling_mode=getattr(bible, "storytelling_mode", None),
                    bible=bible,
                )
            audit_results.append(result)
            if not result.passed or result.score < 90.0:
                all_passed = False
                logger.warning(f"Scene {scene.scene_index} audit failed: {result.errors}")

        context["audit_results"] = audit_results
        context["audit_passed"] = all_passed
        context["passed"] = all_passed
        return context


class OmniVideoRenderAgent(BaseAgent):
    """Stage 6: Renders video via GeminiOmniVideoEngine (or dry-run simulation)."""

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    def __init__(
        self,
        config: Optional[DirectorConfig] = None,
        *,
        name: Optional[str] = None,
        model_name: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        cfg_val = config or cfg
        agent_name = name or "OmniVideoRenderAgent"
        desc = kwargs.pop("description", kwargs.pop("instruction", "Executes video rendering via Gemini Omni or dry-run simulation."))
        super().__init__(
            name=agent_name,
            description=desc,
            **kwargs,
        )
        self.config = cfg_val
        self.name = agent_name
        self.instruction = desc
        self.model_name = model_name or self.config.video_model
        validate_model_identifier(self.model_name, f"{agent_name}.model_name")
        self.engine = GeminiOmniVideoEngine(config=self.config)

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        bible: MasterProductionBible = context["bible"]
        render_video = context.get("render_video", False)

        # Enforce render_video=False default (NFR-2 hybrid mode)
        if not render_video:
            logger.info(f"[{self.name}] render_video is False (default hybrid mode). Skipping video render calls.")
            context["rendered_videos"] = [
                {
                    "scene_index": s.scene_index,
                    "scene_title": s.scene_title,
                    "status": "skipped_by_default_hybrid_mode",
                    "reason": "render_video is False (default). Use --live or render_video=True to trigger Omni 1.1 video generation."
                }
                for s in bible.scenes
            ]
            return context

        # Quality Gate Check before executing live video render
        audit_passed = context.get("audit_passed")
        if audit_passed is None:
            audit_passed = context.get("passed", True)

        audits = context.get("prompt_audits", context.get("audit_results", []))
        audit_score_failed = False
        for a in audits:
            score = getattr(a, "total_score", getattr(a, "score", None))
            if score is None and isinstance(a, dict):
                score = a.get("total_score", a.get("score"))
            if score is not None and score < 90.0:
                audit_score_failed = True
                break

        if audit_passed is False or audit_score_failed:
            logger.warning(f"[{self.name}] Blocking video render due to failed audit gate (audit_passed={audit_passed}, audit_score_failed={audit_score_failed}).")
            context["video_render_status"] = "blocked_by_failed_audit"
            context["video_manifests"] = []
            context["rendered_videos"] = []
            return context

        dry_run = context.get("dry_run", self.config.dry_run)
        if dry_run:
            econ_manifest = getattr(bible, "master_render_economics_spec", None)
            if econ_manifest is not None:
                econ_manifest.dry_run_billable_usd = 0.0
        else:
            client_review = getattr(bible, "master_client_review", None) or getattr(bible, "client_review", None)
            review_ready = getattr(client_review, "ready_for_live_render", True) if client_review is not None else True
            if not review_ready or context.get("ready_for_live_render") is False:
                logger.warning(
                    f"[{self.name}] Blocking live video render: client review signoff gate not cleared (ready_for_live_render=False)."
                )
                context["video_render_status"] = "blocked_by_client_review"
                context["video_manifests"] = []
                context["rendered_videos"] = []
                return context

            max_budget = float(
                context.get("max_render_budget_usd")
                if context.get("max_render_budget_usd") is not None
                else getattr(self.config, "max_render_budget_usd", 50.0)
            )
            econ_manifest = getattr(bible, "master_render_economics_spec", None)
            if econ_manifest is None:
                econ_manifest = compile_render_economics_manifest(bible, max_budget_usd=max_budget)
                bible.master_render_economics_spec = econ_manifest
            within_budget, guardrail_msg = check_render_budget_guardrail(econ_manifest, max_budget)
            est_total = float(getattr(econ_manifest.guardrail, "estimated_total_usd", 0.0) or 0.0)
            if not within_budget or est_total > max_budget:
                logger.error(f"[{self.name}] Aborting live video render: {guardrail_msg}")
                raise ValueError(
                    f"Live video render aborted by --max-render-usd guardrail: {guardrail_msg}"
                )

        visual_plates = context.get("visual_plates", {})
        logger.info(f"[{self.name}] Executing video pipeline for '{bible.project_title}'...")
        render_kwargs: Dict[str, Any] = {"reference_plate_paths": visual_plates}
        if context.get("scene_filter") is not None:
            render_kwargs["scene_filter"] = context.get("scene_filter")
        if context.get("promote_take") is not None:
            render_kwargs["promote_take"] = context.get("promote_take")
        rendered_videos = self.engine.render_production_scenes(bible, **render_kwargs)
        context["rendered_videos"] = rendered_videos
        return context


class StoryboardCompilerAgent(BaseAgent):
    """Stage 7: Fan-in node generating Dark-Room HTML treatment & production_bundle.json."""

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    def __init__(
        self,
        config: Optional[DirectorConfig] = None,
        *,
        name: Optional[str] = None,
        model_name: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        cfg_val = config or cfg
        agent_name = name or "StoryboardCompilerAgent"
        desc = kwargs.pop("description", kwargs.pop("instruction", "Compiles final dark-room storyboard HTML and production_bundle.json."))
        super().__init__(
            name=agent_name,
            description=desc,
            **kwargs,
        )
        self.config = cfg_val
        self.name = agent_name
        self.instruction = desc
        self.model_name = model_name or self.config.fast_model
        validate_model_identifier(self.model_name, f"{agent_name}.model_name")

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        bible: MasterProductionBible = context["bible"]
        output_dir = Path(context.get("output_dir", self.config.output_dir))
        output_dir.mkdir(parents=True, exist_ok=True)

        html_path = output_dir / "storyboard_preview.html"
        json_path = output_dir / "production_bundle.json"

        bundle = ProductionBundle(
            bible=bible,
            storyboard_html_path=str(html_path),
            bundle_json_path=str(json_path),
            visual_plates=context.get("visual_plates", {}),
            rendered_videos=context.get("rendered_videos", []),
            audit_reports=context.get("audit_results", []),
            mode="dry-run" if context.get("dry_run", True) else "render",
        )

        # Compile HTML and JSON bundle
        logger.info(f"[{self.name}] Compiling Dark-Room Cinema HTML & Bundle -> {output_dir}")
        html_file = compile_storyboard_html(bundle, output_dir=output_dir)

        context["bundle"] = bundle
        context["storyboard_html_path"] = str(html_file)
        context["bundle_json_path"] = str(json_path)
        return context


class DirectorPipeline:
    """The master ADK 2.0 Director Pipeline orchestrating the full production lifecycle."""

    def __init__(self, config: Optional[DirectorConfig] = None) -> None:
        self.config = config or cfg
        self.config.validate_no_legacy_3_1_models()

        # Build sub-agents
        self.intake_agent = IntakeAndResearchAgent(self.config)
        self.director_agent = CreativeDirectorAgent(self.config)
        self.visual_agent = VisualStoryboardAgent(self.config)
        self.bgm_agent = BGMComposerAgent(self.config)
        self.prompt_auditor = PromptAuditorAgent(self.config)
        self.video_agent = OmniVideoRenderAgent(self.config)
        self.compiler_agent = StoryboardCompilerAgent(self.config)
        self.council_orchestrator = ProductCouncilOrchestrator(self.config)
        self.telemetry: Optional[RuntimeTelemetry] = None

    def run_from_bible(
        self,
        bible: Union[MasterProductionBible, Path, str, Dict[str, Any]],
        output_dir: Optional[str] = None,
        run_council: bool = False,
        **kwargs: Any,
    ) -> ProductionBundle:
        """Executes the pipeline directly from an existing MasterProductionBible."""
        resolved_bible = load_bible_from_json(bible)
        return self.run(
            bible=resolved_bible,
            output_dir=output_dir,
            run_council=run_council,
            **kwargs,
        )

    @staticmethod
    def _ensure_domain_specs(
        bible: MasterProductionBible,
        arch: Optional[str] = None,
        max_render_budget_usd: Optional[float] = None,
    ) -> MasterProductionBible:
        """Hydrates missing master and per-scene domain specifications (PM-FEAT-007..034)."""
        resolved_arch = arch or getattr(bible, "domain_archetype", None) or "architectural_sanctuary"
        _backfill_production_specs(
            bible,
            resolved_arch,
            max_render_budget_usd=max_render_budget_usd,
        )
        return bible

    @staticmethod
    def _sync_render_job_specs_to_scenes(
        bible: MasterProductionBible,
        rj_manifest: MasterRenderJobManifest,
    ) -> None:
        """Synchronize SceneRenderJobSpec entries and [RENDER-JOB]/[FRAME-ANCHOR] tokens onto scenes."""
        jobs_by_sc = {int(j.scene_index): j for j in rj_manifest.jobs}
        handoffs_by_to = {int(h.to_scene_index): h for h in rj_manifest.frame_anchor_handoffs}
        is_mode_b = (
            bible.storytelling_mode == StorytellingMode.MODE_B_CONTINUOUS_CHAIN
            or "mode b" in str(bible.storytelling_mode).lower()
        )
        for sc in bible.scenes:
            if int(sc.scene_index) in jobs_by_sc:
                sc.render_job_spec = jobs_by_sc[int(sc.scene_index)]
                if re.search(r"\[RENDER[-_ ]JOB:?", sc.omni_prose_prompt, re.IGNORECASE):
                    sc.omni_prose_prompt = re.sub(
                        r"\s*\[(?:RENDER[-_ ]JOB|FRAME[-_ ]ANCHOR)\s*:[^\]]*\]\.?",
                        "",
                        sc.omni_prose_prompt,
                        flags=re.IGNORECASE,
                    ).rstrip()
                    ho = handoffs_by_to.get(int(sc.scene_index)) if (is_mode_b and sc.scene_index > 1) else None
                    sc.omni_prose_prompt += f" {format_render_job_token(sc.render_job_spec, handoff=ho)}."

    @classmethod
    def _propagate_retry_scene_filter(
        cls,
        bible: MasterProductionBible,
        scene_filter: List[int],
    ) -> None:
        """Increment retry_count, refresh QA scorecards, and re-verify Mode B handoffs for --retry-scene."""
        rj_manifest = getattr(bible, "master_render_jobs", None)
        if rj_manifest is None:
            return
        target_indices = {int(s) for s in scene_filter}
        scenes_by_idx = {int(sc.scene_index): sc for sc in bible.scenes}
        rj_fn = getattr(_presets_mod, "get_domain_render_job_spec", None)
        rj_cal = rj_fn(bible) if callable(rj_fn) else None

        for job in rj_manifest.jobs:
            sc_idx = int(job.scene_index)
            if sc_idx not in target_indices:
                continue
            job.retry_count = int(getattr(job, "retry_count", 0) or 0) + 1
            sc_obj = scenes_by_idx.get(sc_idx)
            if sc_obj is not None:
                existing_cards = list(getattr(job, "take_scorecards", None) or [])
                if existing_cards:
                    refreshed_cards = [
                        evaluate_take_visual_qa(sc_obj, take_record=card, domain_cal=rj_cal)
                        for card in existing_cards
                    ]
                else:
                    refreshed_cards = [
                        evaluate_take_visual_qa(sc_obj, take_record=job.qa_scorecard, domain_cal=rj_cal)
                    ]
                job.take_scorecards = refreshed_cards
                matched_hero = next(
                    (c for c in refreshed_cards if c.take_id == job.selected_take_id),
                    refreshed_cards[0],
                )
                for card in refreshed_cards:
                    card.promoted_hero = card.take_id == matched_hero.take_id
                matched_hero.promoted_hero = True
                job.qa_scorecard = matched_hero.model_copy(deep=True)
                job.status = (
                    RenderJobStatusEnum.QA_PASSED
                    if job.qa_scorecard.composite_qa_score >= 85.0
                    else RenderJobStatusEnum.QA_FLAGGED
                )

        is_mode_b = (
            bible.storytelling_mode == StorytellingMode.MODE_B_CONTINUOUS_CHAIN
            or "mode b" in str(bible.storytelling_mode).lower()
        )
        if is_mode_b and len(rj_manifest.jobs) > 1:
            refreshed_handoffs = []
            for i in range(len(rj_manifest.jobs) - 1):
                prev_job = rj_manifest.jobs[i]
                next_job = rj_manifest.jobs[i + 1]
                next_sc = scenes_by_idx.get(int(next_job.scene_index))
                if next_sc is None and i + 1 < len(bible.scenes):
                    next_sc = bible.scenes[i + 1]
                if next_sc is not None:
                    handoff = verify_mode_b_frame_anchor(prev_job, next_sc)
                    next_job.previous_interaction_id = handoff.previous_interaction_id
                    refreshed_handoffs.append(handoff)
            rj_manifest.frame_anchor_handoffs = refreshed_handoffs

        rj_manifest = _recalculate_manifest_summary(rj_manifest)
        bible.master_render_jobs = rj_manifest
        cls._sync_render_job_specs_to_scenes(bible, rj_manifest)

    @staticmethod
    def _record_economics_and_continuity_telemetry(
        telemetry: RuntimeTelemetry,
        bible: MasterProductionBible,
        max_budget_usd: float,
        dry_run: bool,
    ) -> None:
        """Records numeric PM-FEAT-031..034 telemetry metrics safely."""
        econ_spec = getattr(bible, "master_render_economics_spec", None)
        wp_bible = getattr(bible, "master_wardrobe_prop_bible", None)
        if econ_spec is not None:
            if dry_run:
                econ_spec.dry_run_billable_usd = 0.0
            guardrail = getattr(econ_spec, "guardrail", None)
            est_compute_usd = float(getattr(guardrail, "estimated_total_usd", 0.0) or 0.0)
            budget_ceiling_usd = float(
                getattr(guardrail, "max_render_budget_usd", max_budget_usd) or max_budget_usd
            )
            aicp_savings_pct = float(
                getattr(guardrail, "simulation_savings_vs_aicp_pct", 0.0) or 0.0
            )
            planned_takes = int(getattr(econ_spec, "total_planned_takes", 0) or 0)
        else:
            est_compute_usd = 0.0
            budget_ceiling_usd = float(max_budget_usd)
            aicp_savings_pct = 0.0
            planned_takes = 0

        continuity_breaks = (
            int(getattr(wp_bible, "continuity_breaks_detected", 0) or 0)
            if wp_bible is not None
            else 0
        )

        gfx_manifest = getattr(bible, "master_motion_graphics", None)
        otio_manifest = getattr(bible, "master_otio_coherence", None)
        motion_graphics_cues_count = (
            int(getattr(gfx_manifest, "total_cues_count", 0) or 0)
            if gfx_manifest is not None
            else sum(
                len(getattr(getattr(sc, "motion_graphics_spec", None), "cues", None) or [])
                for sc in (getattr(bible, "scenes", None) or [])
            )
        )
        otio_coherence_score = (
            float(getattr(otio_manifest, "coherence_score", 100.0) or 0.0)
            if otio_manifest is not None
            else 100.0
        )
        otio_conflicts_count = (
            int(getattr(otio_manifest, "conflicts_count", 0) or 0)
            if otio_manifest is not None
            else 0
        )

        rj_manifest = getattr(bible, "master_render_jobs", None)
        render_qa_score = (
            float(getattr(rj_manifest, "overall_qa_score", 95.0) or 0.0)
            if rj_manifest is not None
            else 0.0
        )
        promoted_takes_count = (
            int(getattr(rj_manifest, "promoted_takes_count", 0) or 0)
            if rj_manifest is not None
            else 0
        )

        pt_manifest = getattr(bible, "master_pitch_treatment", None)
        treatment_slides_count = (
            len(getattr(pt_manifest, "slides", None) or [])
            if pt_manifest is not None
            else 0
        )
        pt_diff = getattr(pt_manifest, "revision_diff", None) if pt_manifest is not None else None
        revision_deltas_count = (
            int(getattr(pt_diff, "total_changes", 0) or 0)
            if pt_diff is not None
            else 0
        )

        metrics = {
            "estimated_total_compute_usd": est_compute_usd,
            "render_budget_ceiling_usd": budget_ceiling_usd,
            "aicp_savings_pct": aicp_savings_pct,
            "total_planned_takes": planned_takes,
            "continuity_breaks_detected": continuity_breaks,
            "motion_graphics_cues_count": motion_graphics_cues_count,
            "otio_coherence_score": otio_coherence_score,
            "otio_conflicts_count": otio_conflicts_count,
            "render_qa_score": render_qa_score,
            "promoted_takes_count": promoted_takes_count,
            "treatment_slides_count": treatment_slides_count,
            "revision_deltas_count": revision_deltas_count,
        }
        telemetry.metadata.update(metrics)
        telemetry.audit_summary.update(metrics)

    def run(
        self,
        preset_name: Optional[str] = None,
        raw_prompt: Optional[str] = None,
        prompt: Optional[str] = None,
        bible: Optional[MasterProductionBible] = None,
        output_dir: Optional[str] = None,
        render_video: bool = False,
        dry_run: bool = True,
        continuous_mode: bool = False,
        run_council: bool = False,
        max_render_budget_usd: Optional[float] = None,
        promote_take: Optional[Dict[int, str]] = None,
        scene_filter: Optional[List[int]] = None,
    ) -> ProductionBundle:
        """Executes the end-to-end multi-agent pipeline with telemetry and optional council audit."""
        target_output_dir = output_dir or self.config.output_dir
        out_path = Path(target_output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        effective_prompt = prompt or raw_prompt
        effective_max_budget = (
            float(max_render_budget_usd)
            if max_render_budget_usd is not None
            else float(getattr(self.config, "max_render_budget_usd", 50.0))
        )

        # Propagate dry_run across pipeline and engines
        self.config.dry_run = dry_run
        self.video_agent.config.dry_run = dry_run
        self.video_agent.engine.config.dry_run = dry_run
        self.visual_agent.config.dry_run = dry_run
        self.visual_agent.engine.config.dry_run = dry_run

        # Reset RuntimeTelemetry per run to ensure clean, isolated stage timings and distinct session_id
        existing = getattr(self, "telemetry", None)
        has_run_before = getattr(self, "_has_run", False) or (existing and any(t.stage_name in ("compilation", "product_council") for t in existing.stage_timings))

        if existing is not None and not has_run_before:
            telemetry = existing
            if not telemetry.model_matrix:
                telemetry.model_matrix = {
                    "director_model": self.config.director_model,
                    "fast_model": self.config.fast_model,
                    "image_model": self.config.image_model,
                    "video_model": self.config.video_model,
                }
        else:
            telemetry = RuntimeTelemetry(
                project_title="",
                model_matrix={
                    "director_model": self.config.director_model,
                    "fast_model": self.config.fast_model,
                    "image_model": self.config.image_model,
                    "video_model": self.config.video_model,
                },
            )
        self.telemetry = telemetry
        self._has_run = True

        context: Dict[str, Any] = {
            "preset_name": preset_name,
            "raw_prompt": effective_prompt,
            "bible": bible,
            "output_dir": target_output_dir,
            "render_video": render_video,
            "dry_run": dry_run,
            "continuous_mode": continuous_mode,
            "max_render_budget_usd": effective_max_budget,
            "promote_take": promote_take,
            "scene_filter": scene_filter,
        }

        # Stage 1: Intake & Research
        with telemetry.record_stage("intake_and_research"):
            context = self.intake_agent.run(context)

        # Stage 2: Creative Director (Bible synthesis/load)
        with telemetry.record_stage("creative_director"):
            context = self.director_agent.run(context)

        active_bible: MasterProductionBible = context["bible"]
        telemetry.project_title = active_bible.project_title
        arch = getattr(active_bible, "domain_archetype", None) or "architectural_sanctuary"
        self._ensure_domain_specs(active_bible, arch, max_render_budget_usd=effective_max_budget)
        if promote_take and getattr(active_bible, "master_render_jobs", None) is not None:
            rj_manifest = active_bible.master_render_jobs
            for sc_idx, take_id in promote_take.items():
                rj_manifest = promote_scene_take(rj_manifest, int(sc_idx), str(take_id))
            active_bible.master_render_jobs = rj_manifest
            self._sync_render_job_specs_to_scenes(active_bible, rj_manifest)
        if scene_filter is not None and getattr(active_bible, "master_render_jobs", None) is not None:
            self._propagate_retry_scene_filter(active_bible, scene_filter)
        self._record_economics_and_continuity_telemetry(
            telemetry, active_bible, effective_max_budget, dry_run
        )

        # Stage 3: Visual Concept / Nano Banana Anchor Plates
        with telemetry.record_stage("visual_storyboard"):
            context = self.visual_agent.run(context)

        # Stage 4: Scene Prompt Expansion & BGM (Parallel Fan-Out)
        with telemetry.record_stage("scene_prompts_and_bgm"):
            self.bgm_agent = BGMComposerAgent(self.config)
            scene_agents = [ScenePromptAgent(s.scene_index, self.config) for s in active_bible.scenes]
            fan_out = ParallelScenePromptAgent(
                sub_agents=[*scene_agents, self.bgm_agent],
                config=self.config,
            )
            context = fan_out.run(context)

        # Stage 5: Prompt Auditor (7-point rule check)
        with telemetry.record_stage("prompt_auditor"):
            context = self.prompt_auditor.run(context)

        # Stage 6: Video Rendering (Simulation / API)
        with telemetry.record_stage("video_rendering"):
            context = self.video_agent.run(context)

        # Stage 7: Compilation & Output Generation
        with telemetry.record_stage("compilation"):
            context = self.compiler_agent.run(context)

        bundle: ProductionBundle = context["bundle"]
        self._record_economics_and_continuity_telemetry(
            telemetry, active_bible, effective_max_budget, dry_run
        )

        # Write initial manifest prior to Stage 8 so ProductCouncilOrchestrator evaluates fresh checksums
        telemetry.write_manifest(out_path)

        # Stage 8: Autonomous Product Council
        if run_council:
            with telemetry.record_stage("product_council"):
                report = self.council_orchestrator.audit(bundle, output_dir=out_path)
                bundle.council_report = report

        # Persist bundle.telemetry and bundle.council_report into production_bundle.json before manifest checksumming
        bundle.telemetry = telemetry.to_dict()
        bundle_json_file = out_path / "production_bundle.json"
        bundle_json_file.write_text(bundle.model_dump_json(indent=2), encoding="utf-8")

        # Write runtime telemetry and artifact checksums manifest
        telemetry.write_manifest(out_path)
        bundle.telemetry = telemetry.to_dict()

        return bundle


# ADK 2.0 Architectural Aliases
CreativeStrategistAgent = CreativeDirectorAgent
VisualContinuityAgent = VisualStoryboardAgent
PromptArchitectAgent = PromptAuditorAgent
OptionalOmniVideoRenderAgent = OmniVideoRenderAgent
StoryboardHTMLCompilerAgent = StoryboardCompilerAgent
VisualBibleGeneratorAgent = VisualStoryboardAgent
StoryboardParallelAgent = VisualStoryboardAgent
OmniDirectorPipeline = DirectorPipeline

__all__ = [
    "BaseAgent",
    "LlmAgent",
    "SequentialAgent",
    "ParallelAgent",
    "IntakeAndResearchAgent",
    "CreativeStrategistAgent",
    "CreativeDirectorAgent",
    "VisualContinuityAgent",
    "VisualStoryboardAgent",
    "VisualBibleGeneratorAgent",
    "ScenePromptAgent",
    "ParallelScenePromptAgent",
    "StoryboardParallelAgent",
    "BGMComposerAgent",
    "PromptArchitectAgent",
    "PromptAuditorAgent",
    "OmniVideoRenderAgent",
    "OptionalOmniVideoRenderAgent",
    "StoryboardCompilerAgent",
    "StoryboardHTMLCompilerAgent",
    "DirectorPipeline",
    "OmniDirectorPipeline",
    "synthesize_custom_bible",
]
