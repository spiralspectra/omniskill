"""Multi-Cam Coverage & Conversational Delta Branching Engine."""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from omni_director.schemas import (
    CraftCameraSpec,
    MasterProductionBible,
    ScenePromptSpec,
)


class CoverageType(str, Enum):
    """Standard 3-camera cinematic coverage setup per scene."""

    MASTER_ESTABLISHING = "master"
    DYNAMIC_TRACKING = "dynamic"
    MACRO_INSERT = "macro"


class CoverageVariant(BaseModel):
    """A single camera coverage variant for a scene."""

    coverage_type: CoverageType
    label: str
    craft_camera: CraftCameraSpec
    prompt_text: str = Field(..., min_length=40)
    action_anchor: str


def generate_scene_coverage(
    scene: ScenePromptSpec,
    bible: Optional[MasterProductionBible] = None,
) -> Dict[str, CoverageVariant]:
    """Synthesize 3 complementary camera coverage setups (Master, Dynamic, Macro) for a scene.

    Every coverage variant embeds full CRAFT camera grammar, 1.0x real-time physical invariants,
    <image_1>/<image_2> visual locks, and synchronized diegetic audio cues so it passes the
    7-Point Gemini Omni Prompt Auditor (>= 90.0/100).
    """
    del bible  # Reserved for palette/environment cross-injection
    base_cam = scene.craft_camera
    base_anchor = base_cam.action_anchor if base_cam else scene.scene_title
    base_tone = base_cam.tone_rig if base_cam else "35mm Anamorphic Prime Glass"
    foley_summary = (
        ", ".join(scene.diegetic_sonic.foley_cues[:2])
        if (scene.diegetic_sonic and scene.diegetic_sonic.foley_cues)
        else "crisp tactile surface contact foley and balanced room acoustics"
    )

    master_cam = CraftCameraSpec(
        rig_type="Locked-off Heavy Tripod",
        focal_length_mm=24,
        composition="Wide Architectural Establishing Frame with deep geometric symmetry",
        route="Static locked tripod maintaining rigid horizon equilibrium",
        action_anchor=f"Master wide spatial envelope framing {base_anchor}",
        focus_axis="Deep f/5.6 hyperfocal sharpness preserving foreground and architectural background",
        tone_rig=base_tone,
    )

    dynamic_cam = (
        base_cam.model_copy(deep=True)
        if base_cam is not None
        else CraftCameraSpec(
            rig_type="Precision Steadicam Tracking Rig",
            focal_length_mm=50,
            composition="Medium Hero Tracking Frame along rule-of-thirds intersection",
            route="Smooth lateral tracking glide synchronized with subject velocity",
            action_anchor=base_anchor,
            focus_axis="Continuous autofocus lock on hero subject at f/2.8",
            tone_rig=base_tone,
        )
    )

    macro_cam = CraftCameraSpec(
        rig_type="Motorized Macro Slider",
        focal_length_mm=100,
        composition="Extreme Close-Up Tactile Insert isolating micro-surface contact",
        route="Slow 4-centimeter lateral macro push-in across primary contact interface",
        action_anchor=f"Micro-surface contact point on {base_anchor}",
        focus_axis="Razor-thin f/2.0 macro plane isolating surface texture against optical bokeh",
        tone_rig="100mm Macro Prime Cinema Glass",
    )

    configs = [
        (
            CoverageType.MASTER_ESTABLISHING,
            "Cam A · 24mm Master Wide",
            master_cam,
        ),
        (
            CoverageType.DYNAMIC_TRACKING,
            f"Cam B · {dynamic_cam.focal_length_mm}mm Dynamic Hero",
            dynamic_cam,
        ),
        (
            CoverageType.MACRO_INSERT,
            "Cam C · 100mm Macro Insert",
            macro_cam,
        ),
    ]

    variants: Dict[str, CoverageVariant] = {}
    for cov_type, label, cam_spec in configs:
        prompt_text = (
            f"Captured on a {cam_spec.focal_length_mm}mm {cam_spec.rig_type} ({cam_spec.composition}, "
            f"route: {cam_spec.route}, focus: {cam_spec.focus_axis}) at locked 1.0x real-time natural speed "
            f"with authentic Newtonian gravity, solid surface friction, and rigid physical momentum. "
            f"Preserving <image_1> character identity and <image_2> architectural environment geometry, "
            f"{scene.omni_prose_prompt} Synchronized diegetic audio captures {foley_summary}."
        )
        variants[cov_type.value] = CoverageVariant(
            coverage_type=cov_type,
            label=label,
            craft_camera=cam_spec,
            prompt_text=prompt_text,
            action_anchor=cam_spec.action_anchor,
        )

    return variants


def synthesize_conversational_deltas(
    scene: ScenePromptSpec,
    bible: Optional[MasterProductionBible] = None,
) -> List[str]:
    """Generate 3 single-turn conversational follow-up edit deltas for iterative video refinement.

    Follows the Gemini Omni conversational delta pattern:
    - Turn 2: Lighting & atmospheric grade refinement
    - Turn 3: Camera kinematics & optical depth adjustment
    - Turn 4: Diegetic acoustic & material micro-texture intensification
    """
    cam = scene.craft_camera
    focal = cam.focal_length_mm if cam else 35
    rig = cam.rig_type if cam else "Steadicam"
    primary_foley = (
        scene.diegetic_sonic.foley_cues[0]
        if (scene.diegetic_sonic and scene.diegetic_sonic.foley_cues)
        else "tactile contact foley"
    )
    room_tone = (
        scene.diegetic_sonic.room_acoustics
        if scene.diegetic_sonic
        else "natural room acoustics"
    )
    palette_hint = (
        ", ".join(bible.color_palette[:3])
        if (bible is not None and bible.color_palette)
        else "locked production palette"
    )

    turn_2_lighting = (
        f"Turn 2 Delta (Lighting & Atmosphere): Preserve exact subject identity, wardrobe, and "
        f"spatial blocking from Scene {scene.scene_index:02d}. Deepen the key-to-fill contrast "
        f"ratio along palette anchors ({palette_hint}) while intensifying volumetric rim-light "
        f"separation during the [02s-05s] escalation beat."
    )
    turn_3_camera = (
        f"Turn 3 Delta (Camera & Optics): Keep all physical choreography locked at 1.0x real-time speed. "
        f"Tighten the {focal}mm {rig} framing by 15% and pull focus smoothly "
        f"onto the hero contact surface at [05s-08s] with crisp optical separation."
    )
    turn_4_acoustic = (
        f"Turn 4 Delta (Diegetic Audio & Surface Micro-Detail): Maintain visual timing and "
        f"camera path. Amplify close-mic transient clarity for '{primary_foley}' above "
        f"'{room_tone}' and sharpen specular micro-reflections at peak impact."
    )

    return [turn_2_lighting, turn_3_camera, turn_4_acoustic]
