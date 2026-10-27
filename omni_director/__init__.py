"""Omni Director: ADK 2.0 Multi-Agent Movie Director.

Orchestrating Gemini 4 Argon, Gemini 3.8 Flash, Nano Banana (gemini-3-pro-image),
and Gemini Omni (gemini-omni-1.1-flash-preview) for cinematic video production.
"""

from omni_director.agents import (
    CreativeDirectorAgent,
    DirectorPipeline,
    IntakeAndResearchAgent,
    OmniVideoRenderAgent,
    PromptAuditorAgent,
    StoryboardCompilerAgent,
    VisualStoryboardAgent,
)
from omni_director.config import DirectorConfig, cfg
from omni_director.presets import (
    IKEA_ASMR_BIBLE,
    KINETIC_FABRIC_BIBLE,
    PRESETS,
    SEPHORA_EXTENSION_40S_BIBLE,
    SEPHORA_PULSE_BIBLE,
    get_preset_bible,
)
from omni_director.schemas import (
    ActionBeatSpec,
    AspectRatio,
    AuditResult,
    CharacterTurnaroundSpec,
    CraftCameraSpec,
    DiegeticSonicSpec,
    KineticContactChain,
    MasterBgmSpec,
    MasterEnvironmentSpec,
    MasterProductionBible,
    NanoBananaReference,
    ProductionBundle,
    RegimeType,
    SceneKeyframeSpec,
    ScenePromptSpec,
    StorytellingMode,
)
from omni_director.tools import (
    GeminiOmniVideoEngine,
    NanoBananaStoryboardEngine,
    audit_omni_scene_prompt,
    compile_storyboard_html,
)

__version__ = "2.0.0"

__all__ = [
    # Top-Level Runner & Config
    "DirectorPipeline",
    "DirectorConfig",
    "cfg",
    # Presets
    "PRESETS",
    "get_preset_bible",
    "IKEA_ASMR_BIBLE",
    "SEPHORA_PULSE_BIBLE",
    "SEPHORA_EXTENSION_40S_BIBLE",
    "KINETIC_FABRIC_BIBLE",
    # Schemas
    "MasterProductionBible",
    "ScenePromptSpec",
    "ProductionBundle",
    "AuditResult",
    "RegimeType",
    "StorytellingMode",
    "AspectRatio",
    "CraftCameraSpec",
    "KineticContactChain",
    "ActionBeatSpec",
    "DiegeticSonicSpec",
    "MasterBgmSpec",
    "NanoBananaReference",
    "CharacterTurnaroundSpec",
    "MasterEnvironmentSpec",
    "SceneKeyframeSpec",
    # Tools
    "audit_omni_scene_prompt",
    "compile_storyboard_html",
    "NanoBananaStoryboardEngine",
    "GeminiOmniVideoEngine",
    # Agents
    "IntakeAndResearchAgent",
    "CreativeDirectorAgent",
    "VisualStoryboardAgent",
    "PromptAuditorAgent",
    "OmniVideoRenderAgent",
    "StoryboardCompilerAgent",
]
