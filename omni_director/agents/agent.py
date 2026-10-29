"""ADK 2.0 Multi-Agent Pipeline for omni-movie-director.

Orchestrates the Lead Director (gemini-4-argon), Fast Workhorse (gemini-3.8-flash),
Concept Artist (gemini-3-pro-image), and Video Engine (gemini-omni-1.1-flash-preview).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union
from pydantic import ConfigDict

from omni_director.config import DirectorConfig, cfg
from omni_director.presets import DOMAIN_ARCHETYPES, classify_brief_domain, get_preset_bible
from omni_director.schemas import (
    ActionBeatSpec,
    AspectRatio,
    AuditResult,
    CharacterTurnaroundSpec,
    CraftCameraSpec,
    DiegeticSonicSpec,
    MasterBgmSpec,
    MasterEnvironmentSpec,
    MasterProductionBible,
    NanoBananaReference,
    ProductionBundle,
    RegimeType,
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
    from google.adk.agents import BaseAgent, LlmAgent, ParallelAgent, SequentialAgent
    HAS_GOOGLE_ADK = True
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


def synthesize_custom_bible(raw_prompt: str, config: Optional[DirectorConfig] = None) -> MasterProductionBible:
    """Dynamically synthesizes a valid 7-Point compliant MasterProductionBible from custom raw_prompt."""
    domain = classify_brief_domain(raw_prompt)
    archetype = DOMAIN_ARCHETYPES.get(domain, DOMAIN_ARCHETYPES["architectural_sanctuary"])

    # Regime handling: support RegimeType enum and string "kinetic"
    raw_regime = archetype.get("regime")
    if raw_regime == RegimeType.REGIME_2_KINETIC or raw_regime == "kinetic" or (isinstance(raw_regime, str) and "kinetic" in raw_regime.lower()):
        regime = RegimeType.REGIME_2_KINETIC
        is_kinetic = True
    else:
        regime = RegimeType.REGIME_1_ATMOSPHERIC
        is_kinetic = False

    title = raw_prompt[:40].strip().title()
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
        f"{'Rendered at natural 1.0x real-time speed with solid gravity and friction invariants. ' if is_kinetic else 'Gentle macro motion with tactile physics. '}"
        f"Diegetic audio captures synchronous {foley[0]} and {foley[-1]}."
    )
    prose_2 = (
        f"Continuation of Scene 1 following the subject. Continuation of {raw_prompt.strip()}. "
        f"Maintaining continuity with keyframe <image_3>. "
        f"{camera_rig_2} maneuver at eye-level with {lighting}. "
        f"{'Rendered at natural 1.0x real-time speed with solid momentum and ground contact reaction. ' if is_kinetic else 'Controlled tactile interaction with micro-acoustic detail. '}"
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
    )

    craft_2 = CraftCameraSpec(
        rig_type=camera_rig_2,
        focal_length_mm=focal_length_2,
        composition="Medium close-up at eye level with strong rim separation",
        route="Arced orbit maneuver sweeping 45 degrees around subject",
        action_anchor="Subject's hands and physical contact interface",
        focus_axis="Shallow depth of field with locked subject focal tracking",
        tone_rig="Warm spherical glass with smooth circular bokeh",
    )

    scene_1 = ScenePromptSpec(
        scene_index=1,
        scene_title=scene_title_1,
        timestamp_range="00:00 - 00:05",
        regime=regime,
        craft_camera=craft_1,
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

    scene_2 = ScenePromptSpec(
        scene_index=2,
        scene_title=scene_title_2,
        timestamp_range="00:05 - 00:10",
        regime=regime,
        craft_camera=craft_2,
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

    return MasterProductionBible(
        project_title=title,
        logline=raw_prompt,
        creative_regime=regime,
        storytelling_mode=StorytellingMode.MODE_A_PARALLEL_CUT,
        aspect_ratio=AspectRatio.RATIO_16_9,
        total_runtime_seconds=10,
        color_palette=palette,
        environment=MasterEnvironmentSpec(
            location_name="Hero Environment",
            spatial_architecture=f"Architectural space styled for {domain.replace('_', ' ')}",
            lighting_setup=lighting,
            atmospheric_particles="Ultra-fine suspended haze catching oblique light shafts",
            positive_invariants=["Polished floor surface", "Structural steel pillar grid"],
            generation_prompt="Master architectural environment showing clean lines and deep spatial perspective",
        ),
        characters=[
            CharacterTurnaroundSpec(
                name="Hero Subject",
                silhouette="Athletic minimalist silhouette with sharp aerodynamic contours",
                wardrobe_polarity="Matte black performance composite with iridescent teal accents",
                movement_signature="Precise, decisive, momentum-conserving kinetic movement",
                generation_prompt="Character turnaround orthographic sheet showing front, profile, and three-quarter angles",
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
            genre_style="Cinematic Hybrid Score",
            tempo_bpm=120 if is_kinetic else 72,
            key_signature="D Minor",
            instrumentation=["Modular synthesizer pulses", "Sub-bass rumble", "Acoustic strings"],
            dynamic_arc="Gentle rhythmic pulse building into an assertive cinematic climax",
            lyria_prompt=f"Cinematic score for {domain.replace('_', ' ')}, modular synthesizer pulses with deep sub-bass and crisp acoustic transients",
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
    )


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

    def synthesize_custom_bible(self, raw_prompt: str) -> MasterProductionBible:
        """Synthesizes a domain-aware MasterProductionBible from custom creative brief."""
        return synthesize_custom_bible(raw_prompt, self.config)

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:

        logger.info(f"[{self.name}] Synthesizing Master Production Bible...")
        bible = None
        if "bible" in context and isinstance(context["bible"], MasterProductionBible):
            bible = context["bible"]
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
                    bible = synthesize_custom_bible(raw_prompt, self.config)
                else:
                    bible = get_preset_bible("ikea-asmr")

        if bible is not None:
            if not getattr(bible, "domain_archetype", None) and context.get("domain_archetype"):
                bible.domain_archetype = context["domain_archetype"]

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
            if scene.regime == RegimeType.REGIME_2_KINETIC and "1.0x" not in scene.omni_prose_prompt:
                scene.omni_prose_prompt += " Rendered at natural 1.0x real-time speed."
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
        sub_list = sub_agents or []
        super().__init__(name=agent_name, description=desc, sub_agents=sub_list, **kwargs)
        self.config = cfg_val
        self.name = agent_name
        self.instruction = desc
        self.model_name = model_name or self.config.fast_model
        self.sub_agents = sub_list

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute all sub-agents over the shared context."""
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
            )
            if not result.passed or result.score < 100.0 or result.warnings:
                logger.info(f"[{self.name}] Attempting self-healing for scene {scene.scene_index}...")
                healed_target, result = heal_omni_scene_prompt(
                    scene,
                    audit_result=result,
                    regime=bible.creative_regime,
                    storytelling_mode=getattr(bible, "storytelling_mode", None),
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

        visual_plates = context.get("visual_plates", {})
        logger.info(f"[{self.name}] Executing video pipeline for '{bible.project_title}'...")
        rendered_videos = self.engine.render_production_scenes(bible, reference_plate_paths=visual_plates)
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
    ) -> ProductionBundle:
        """Executes the end-to-end multi-agent pipeline with telemetry and optional council audit."""
        target_output_dir = output_dir or self.config.output_dir
        out_path = Path(target_output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        effective_prompt = prompt or raw_prompt

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
        }

        # Stage 1: Intake & Research
        with telemetry.record_stage("intake_and_research"):
            context = self.intake_agent.run(context)

        # Stage 2: Creative Director (Bible synthesis/load)
        with telemetry.record_stage("creative_director"):
            context = self.director_agent.run(context)

        active_bible: MasterProductionBible = context["bible"]
        telemetry.project_title = active_bible.project_title

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
