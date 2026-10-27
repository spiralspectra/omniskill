"""ADK 2.0 Multi-Agent Pipeline for omni-movie-director.

Orchestrates the Lead Director (gemini-4-argon), Fast Workhorse (gemini-3.8-flash),
Concept Artist (gemini-3-pro-image), and Video Engine (gemini-omni-1.1-flash-preview).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from omni_director.config import DirectorConfig, cfg
from omni_director.presets import get_preset_bible
from omni_director.schemas import (
    AuditResult,
    MasterProductionBible,
    ProductionBundle,
    RegimeType,
    ScenePromptSpec,
    StorytellingMode,
)
from omni_director.tools.html_compiler import compile_storyboard_html
from omni_director.tools.nano_banana import NanoBananaStoryboardEngine
from omni_director.tools.omni_video import GeminiOmniVideoEngine
from omni_director.tools.prompt_auditor import audit_omni_scene_prompt

logger = logging.getLogger("omni_director.agents")

# Graceful Google ADK 2.0 Import Handling
try:
    import google.adk
    from google.adk.agents import BaseAgent, LlmAgent, ParallelAgent, SequentialAgent
    HAS_GOOGLE_ADK = True
except ImportError:
    HAS_GOOGLE_ADK = False

    class BaseAgent:  # type: ignore[no-redef]
        def __init__(self, name: str, instruction: str = "", **kwargs: Any) -> None:
            self.name = name
            self.instruction = instruction
            self.kwargs = kwargs

        def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
            return context

    class LlmAgent(BaseAgent):  # type: ignore[no-redef]
        def __init__(self, name: str, model: str = "", instruction: str = "", **kwargs: Any) -> None:
            super().__init__(name, instruction, **kwargs)
            self.model = model

    class SequentialAgent(BaseAgent):  # type: ignore[no-redef]
        def __init__(self, name: str, sub_agents: List[BaseAgent], **kwargs: Any) -> None:
            super().__init__(name, **kwargs)
            self.sub_agents = sub_agents

        def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
            for agent in self.sub_agents:
                context = agent.run(context)
            return context

    class ParallelAgent(BaseAgent):  # type: ignore[no-redef]
        def __init__(self, name: str, sub_agents: List[BaseAgent], **kwargs: Any) -> None:
            super().__init__(name, **kwargs)
            self.sub_agents = sub_agents

        def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
            for agent in self.sub_agents:
                context = agent.run(context)
            return context


class IntakeAndResearchAgent(BaseAgent):
    """Stage 1: Ingests user creative loglines, references, and research parameters."""

    def __init__(self, config: Optional[DirectorConfig] = None) -> None:
        super().__init__(
            name="IntakeAndResearchAgent",
            instruction="Ingests creative brief and grounds aesthetic tone, pacing, and visual style."
        )
        self.config = config or cfg

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        prompt = context.get("raw_prompt") or ""
        preset = context.get("preset_name")
        logger.info(f"[{self.name}] Analyzing intake brief. Preset: {preset}, Prompt: {prompt[:60]}...")
        context["intake_complete"] = True
        return context


class CreativeDirectorAgent(BaseAgent):
    """Stage 2: Single Source of Truth (SSOT). Synthesizes or loads the MasterProductionBible."""

    def __init__(self, config: Optional[DirectorConfig] = None) -> None:
        super().__init__(
            name="CreativeDirectorAgent",
            instruction=f"Authoritative director utilizing {config.director_model if config else 'gemini-4-argon'}."
        )
        self.config = config or cfg

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"[{self.name}] Synthesizing Master Production Bible...")
        if "bible" in context and isinstance(context["bible"], MasterProductionBible):
            bible = context["bible"]
        elif context.get("preset_name"):
            bible = get_preset_bible(context["preset_name"])
        else:
            # Fallback to default golden preset if raw prompt passed without explicit bible
            prompt = context.get("raw_prompt") or ""
            if "sephora" in prompt.lower() or "perfume" in prompt.lower():
                bible = get_preset_bible("sephora-pulse")
            elif "fabric" in prompt.lower() or "aerodynamic" in prompt.lower():
                bible = get_preset_bible("kinetic-fabric")
            else:
                bible = get_preset_bible("ikea-asmr")

        context["bible"] = bible
        logger.info(f"[{self.name}] Sealed Bible: '{bible.project_title}' with {len(bible.scenes)} scenes.")
        return context


class VisualStoryboardAgent(BaseAgent):
    """Stage 3: Generates visual plates and keyframes via NanoBananaStoryboardEngine."""

    def __init__(self, config: Optional[DirectorConfig] = None) -> None:
        super().__init__(
            name="VisualStoryboardAgent",
            instruction="Generates turnaround sheets, environment plates, and keyframes."
        )
        self.config = config or cfg
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

    def __init__(self, scene_index: int, config: Optional[DirectorConfig] = None) -> None:
        super().__init__(
            name=f"ScenePromptAgent_{scene_index}",
            instruction="Enforces CRAFT camera grammar, 1.0x speed lock, and acoustic foley cues."
        )
        self.scene_index = scene_index
        self.config = config or cfg

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        bible: MasterProductionBible = context["bible"]
        matching = [s for s in bible.scenes if s.scene_index == self.scene_index]
        if matching:
            scene = matching[0]
            # Ensure speed lock is in prompt if Regime 2
            if scene.regime == RegimeType.REGIME_2_KINETIC and "1.0x" not in scene.omni_prose_prompt:
                scene.omni_prose_prompt += " Rendered at natural 1.0x real-time speed."
        return context


class BGMComposerAgent(BaseAgent):
    """Stage 4b: Film Composer agent structuring score blueprint."""

    def __init__(self, config: Optional[DirectorConfig] = None) -> None:
        super().__init__(
            name="BGMComposerAgent",
            instruction="Synthesizes musical score and Lyria prompt."
        )
        self.config = config or cfg

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        bible: MasterProductionBible = context["bible"]
        logger.info(f"[{self.name}] BGM Track: '{bible.master_bgm.track_title}' ({bible.master_bgm.tempo_bpm} BPM).")
        return context


class PromptAuditorAgent(BaseAgent):
    """Stage 5: 7-point prompt auditor evaluating scene prompts against Gemini Omni rules."""

    def __init__(self) -> None:
        super().__init__(
            name="PromptAuditorAgent",
            instruction="Audits all scene prompts against the 7-Point Gemini Omni Prompt Standard."
        )

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        bible: MasterProductionBible = context["bible"]
        logger.info(f"[{self.name}] Auditing {len(bible.scenes)} scene prompts...")
        audit_results: List[AuditResult] = []
        all_passed = True

        for scene in bible.scenes:
            result = audit_omni_scene_prompt(scene, regime=bible.creative_regime)
            audit_results.append(result)
            if not result.passed:
                all_passed = False
                logger.warning(f"Scene {scene.scene_index} audit failed: {result.errors}")

        context["audit_results"] = audit_results
        context["audit_passed"] = all_passed
        return context


class OmniVideoRenderAgent(BaseAgent):
    """Stage 6: Renders video via GeminiOmniVideoEngine (or dry-run simulation)."""

    def __init__(self, config: Optional[DirectorConfig] = None) -> None:
        super().__init__(
            name="OmniVideoRenderAgent",
            instruction="Executes video rendering via Gemini Omni or dry-run simulation."
        )
        self.config = config or cfg
        self.engine = GeminiOmniVideoEngine(config=self.config)

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        bible: MasterProductionBible = context["bible"]
        visual_plates = context.get("visual_plates", {})
        logger.info(f"[{self.name}] Executing video pipeline for '{bible.project_title}'...")
        rendered_videos = self.engine.render_production_scenes(bible, reference_plate_paths=visual_plates)
        context["rendered_videos"] = rendered_videos
        return context


class StoryboardCompilerAgent(BaseAgent):
    """Stage 7: Fan-in node generating Dark-Room HTML treatment & production_bundle.json."""

    def __init__(self, config: Optional[DirectorConfig] = None) -> None:
        super().__init__(
            name="StoryboardCompilerAgent",
            instruction="Compiles final dark-room storyboard HTML and production_bundle.json."
        )
        self.config = config or cfg

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        bible: MasterProductionBible = context["bible"]
        output_dir = Path(context.get("output_dir", self.config.output_dir))
        output_dir.mkdir(parents=True, exist_ok=True)

        html_path = output_dir / "storyboard_preview.html"
        json_path = output_dir / "production_bundle.json"

        bundle = ProductionBundle(
            bible=bible,
            storyboard_html_path=str(html_path.resolve()),
            bundle_json_path=str(json_path.resolve()),
            visual_plates=context.get("visual_plates", {}),
            rendered_videos=context.get("rendered_videos", []),
            audit_reports=context.get("audit_results", []),
            mode="dry-run" if context.get("dry_run", True) else "render",
        )

        # Compile HTML and JSON bundle
        logger.info(f"[{self.name}] Compiling Dark-Room Cinema HTML & Bundle -> {output_dir}")
        html_file = compile_storyboard_html(bundle, output_dir=output_dir)

        context["bundle"] = bundle
        context["storyboard_html_path"] = str(html_file.resolve())
        context["bundle_json_path"] = str(json_path.resolve())
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
        self.prompt_auditor = PromptAuditorAgent()
        self.video_agent = OmniVideoRenderAgent(self.config)
        self.compiler_agent = StoryboardCompilerAgent(self.config)

    def run(
        self,
        preset_name: Optional[str] = None,
        raw_prompt: Optional[str] = None,
        bible: Optional[MasterProductionBible] = None,
        output_dir: Optional[str] = None,
        render_video: bool = False,
        dry_run: bool = True,
        continuous_mode: bool = False,
    ) -> ProductionBundle:
        """Executes the end-to-end multi-agent pipeline."""
        target_output_dir = output_dir or self.config.output_dir

        context: Dict[str, Any] = {
            "preset_name": preset_name,
            "raw_prompt": raw_prompt,
            "bible": bible,
            "output_dir": target_output_dir,
            "render_video": render_video,
            "dry_run": dry_run,
            "continuous_mode": continuous_mode,
        }

        # Stage 1: Intake & Research
        context = self.intake_agent.run(context)

        # Stage 2: Creative Director (Bible synthesis/load)
        context = self.director_agent.run(context)

        # Stage 3: Visual Concept / Nano Banana Anchor Plates
        context = self.visual_agent.run(context)

        # Stage 4: Scene Prompt Expansion & BGM (Parallel Fan-Out)
        active_bible: MasterProductionBible = context["bible"]
        scene_agents = [ScenePromptAgent(s.scene_index, self.config) for s in active_bible.scenes]
        fan_out = ParallelAgent(
            name="ScenePromptFanOutAgent",
            sub_agents=[*scene_agents, self.bgm_agent],
        )
        context = fan_out.run(context)

        # Stage 5: Prompt Auditor (7-point rule check)
        context = self.prompt_auditor.run(context)

        # Stage 6: Video Rendering (Simulation / API)
        context = self.video_agent.run(context)

        # Stage 7: Compilation & Output Generation
        context = self.compiler_agent.run(context)

        return context["bundle"]
