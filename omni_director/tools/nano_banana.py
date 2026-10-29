"""Nano Banana Storyboard Engine generating 3-Tier Visual Continuity Plates."""

import html
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from omni_director.config import DirectorConfig
from omni_director.schemas import (
    AspectRatio,
    CharacterTurnaroundSpec,
    MasterEnvironmentSpec,
    MasterProductionBible,
    NanoBananaReference,
    SceneKeyframeSpec,
)


class NanoBananaStoryboardEngine:
    """Storyboard pre-visualization engine powered by Nano Banana (gemini-3-pro-image).

    Generates Anchor 1 (Character Turnaround), Anchor 2 (Master Environment Plate),
    and Anchor 3 (Scene Keyframes). Generates cinema-grade SVG visual plates in
    offline/dry-run mode, and invokes the Google GenAI SDK when live credentials exist.
    """

    def __init__(self, config: Optional[DirectorConfig] = None):
        self.config = config or DirectorConfig()

    def _generate_live_or_svg(self, prompt: str, svg_fallback: str, out_prefix: Path) -> Path:
        """Attempts live image generation via client.models.generate_content or falls back to SVG."""
        if not self.config.dry_run and self.config.api_key:
            try:
                from google import genai
                client = genai.Client(api_key=self.config.api_key)
                response = client.models.generate_content(
                    model=self.config.image_model,
                    contents=prompt,
                )
                if response and response.candidates and response.candidates[0].content:
                    for part in response.candidates[0].content.parts:
                        inline = getattr(part, "inline_data", None)
                        if inline and getattr(inline, "data", None):
                            png_path = out_prefix.with_suffix(".png")
                            png_path.write_bytes(inline.data)
                            return png_path
            except Exception:
                pass

        svg_path = out_prefix.with_suffix(".svg")
        svg_path.write_text(svg_fallback, encoding="utf-8")
        return svg_path

    def generate_all_storyboard_plates(
        self,
        bible: MasterProductionBible,
        output_dir: Path
    ) -> Dict[str, str]:
        """Generates all 3 continuity anchor plates for a MasterProductionBible.

        Returns:
            Dict mapping asset tags (e.g. '<image_1>', '<image_2>', '<image_3>', 'scene_1')
            to relative or absolute file paths.
        """
        boards_dir = output_dir / "storyboards"
        boards_dir.mkdir(parents=True, exist_ok=True)
        rendered_assets: Dict[str, str] = {}

        # 1. Anchor 1: Character Turnaround Sheet or Primary Hero Subject Plate
        if bible.characters:
            char = bible.characters[0]
            svg_content = self.render_character_turnaround_svg(char, bible)
            plate_prefix = boards_dir / "anchor1_character_turnaround"
            char_prompt = char.generation_prompt or f"Character turnaround sheet: {char.name}. Silhouette: {char.silhouette}. Wardrobe: {char.wardrobe_polarity}"
            actual_path = self._generate_live_or_svg(
                prompt=char_prompt,
                svg_fallback=svg_content,
                out_prefix=plate_prefix
            )
            char.image_path = str(actual_path)
            char.svg_markup = svg_content if actual_path.suffix == ".svg" else None
            rendered_assets["<image_1>"] = str(actual_path)
        else:
            # Fallback for non-character projects (e.g. hero object/product/fabric)
            asset1 = next((a for a in bible.nano_banana_assets if a.asset_id == "<image_1>"), None)
            char_fallback = CharacterTurnaroundSpec(
                name=asset1.job_description[:30] if asset1 else bible.project_title,
                silhouette=asset1.job_description if asset1 else "Hero subject geometry",
                wardrobe_polarity=asset1.exclusion_clause if asset1 else "Default polarity",
                movement_signature="Rigid physical geometry and material properties."
            )
            svg_content = self.render_character_turnaround_svg(char_fallback, bible)
            plate_prefix = boards_dir / "anchor1_character_turnaround"
            prompt_val = asset1.generation_prompt if asset1 else f"Hero subject anchor plate: {bible.project_title}"
            actual_path = self._generate_live_or_svg(
                prompt=prompt_val,
                svg_fallback=svg_content,
                out_prefix=plate_prefix
            )
            rendered_assets["<image_1>"] = str(actual_path)

        # 2. Anchor 2: Master Architectural Environment Plate
        env_svg = self.render_environment_plate_svg(bible.environment, bible)
        env_prefix = boards_dir / "anchor2_environment_master"
        env_prompt = bible.environment.generation_prompt or f"Architectural environment master plate: {bible.environment.location_name}. Architecture: {bible.environment.spatial_architecture}. Lighting: {bible.environment.lighting_setup}"
        actual_env_path = self._generate_live_or_svg(
            prompt=env_prompt,
            svg_fallback=env_svg,
            out_prefix=env_prefix
        )
        bible.environment.image_path = str(actual_env_path)
        bible.environment.svg_markup = env_svg if actual_env_path.suffix == ".svg" else None
        rendered_assets["<image_2>"] = str(actual_env_path)

        # 3. Anchor 3: Scene Keyframes & Reference 3
        for scene in bible.scenes:
            scene_svg = self.render_scene_keyframe_svg(scene, bible)
            scene_prefix = boards_dir / f"anchor3_scene_{scene.scene_index}_keyframe"
            actual_scene_path = self._generate_live_or_svg(
                prompt=f"Cinematic storyboard keyframe for Scene {scene.scene_index}: {scene.scene_title}. {scene.omni_prose_prompt}",
                svg_fallback=scene_svg,
                out_prefix=scene_prefix
            )
            rendered_assets[f"scene_{scene.scene_index}"] = str(actual_scene_path)
            if scene.scene_index == 1 and "<image_3>" not in rendered_assets:
                rendered_assets["<image_3>"] = str(actual_scene_path)

        # Update bible nano banana references with paths
        for asset in bible.nano_banana_assets:
            if asset.asset_id in rendered_assets:
                p = Path(rendered_assets[asset.asset_id])
                asset.local_path = str(p)
                if p.suffix == ".svg":
                    asset.svg_markup = p.read_text(encoding="utf-8")

        return rendered_assets

    def _aspect_dimensions(self, aspect_ratio: Optional[AspectRatio | str]) -> tuple[int, int]:
        """Resolves pixel canvas dimensions for a given aspect ratio."""
        if not aspect_ratio:
            return (1920, 1080)
        val = aspect_ratio.value if isinstance(aspect_ratio, AspectRatio) else str(aspect_ratio)
        if "9:16" in val:
            return (1080, 1920)
        elif "1:1" in val:
            return (1080, 1080)
        elif "2.39" in val:
            return (2560, 1071)
        return (1920, 1080)

    def render_character_turnaround_svg(
        self,
        char: CharacterTurnaroundSpec,
        bible: MasterProductionBible
    ) -> str:
        """Renders a crisp 3-panel orthographic character turnaround SVG scaled to viewBox."""
        palette = bible.color_palette or ["#1A1A24", "#FF4B4B", "#00F0FF", "#F0F0F5"]
        c1, c2, c3 = palette[0], palette[1 % len(palette)], palette[2 % len(palette)]
        view_w, view_h = self._aspect_dimensions(bible.aspect_ratio)

        # Dynamic layout geometry
        pad = 40
        panel_gap = 20
        panel_w = int((view_w - (2 * pad) - (2 * panel_gap)) / 3)
        panel_y = 140
        panel_h = max(200, view_h - panel_y - 120)

        x_a = pad
        x_b = pad + panel_w + panel_gap
        x_c = pad + 2 * (panel_w + panel_gap)

        head_r = max(20, min(55, int(panel_w * 0.16)))
        leg_w = max(15, min(35, int(panel_w * 0.1)))
        leg_h = max(80, min(260, int(panel_h * 0.3)))

        return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {view_w} {view_h}" width="100%" height="100%">
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{c1}" stop-opacity="0.95"/>
      <stop offset="100%" stop-color="#0A0B10" stop-opacity="1.0"/>
    </linearGradient>
    <linearGradient id="heroAccent" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="{c2}"/>
      <stop offset="100%" stop-color="{c3}"/>
    </linearGradient>
    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="8" result="blur"/>
      <feComposite in="SourceGraphic" in2="blur" operator="over"/>
    </filter>
  </defs>

  <!-- Background Canvas -->
  <rect width="{view_w}" height="{view_h}" fill="url(#bgGrad)"/>
  
  <!-- Subtle Studio Grid -->
  <pattern id="grid" width="60" height="60" patternUnits="userSpaceOnUse">
    <path d="M 60 0 L 0 0 0 60" fill="none" stroke="#252736" stroke-width="1" stroke-opacity="0.4"/>
  </pattern>
  <rect width="{view_w}" height="{view_h}" fill="url(#grid)"/>

  <!-- Top Cinema HUD -->
  <rect x="{pad}" y="40" width="{view_w - 2 * pad}" height="70" rx="8" fill="#12131A" stroke="#2F3242" stroke-width="1.5"/>
  <text x="{pad + 25}" y="82" font-family="'Space Grotesk', system-ui, sans-serif" font-size="20" font-weight="700" fill="#00F0FF" letter-spacing="2">
    ANCHOR 1: CHARACTER TURNAROUND SHEET (DNA LOCK)
  </text>
  <text x="{view_w - pad - 25}" y="82" font-family="'JetBrains Mono', monospace" font-size="14" fill="#8E92A8" text-anchor="end">
    MODEL: {self.config.image_model} | 5600K DIFFUSE STUDIO | POLARITY LOCK
  </text>

  <!-- 3-Panel Turnaround Frames -->
  <!-- Panel 1: Front Full Body -->
  <rect x="{x_a}" y="{panel_y}" width="{panel_w}" height="{panel_h}" rx="10" fill="#151722" stroke="#2F3242" stroke-width="1"/>
  <text x="{x_a + 20}" y="{panel_y + 40}" font-family="'JetBrains Mono', monospace" font-size="14" fill="#8E92A8">PANEL A: FRONT</text>
  <!-- Stylized Figure Front -->
  <circle cx="{x_a + panel_w // 2}" cy="{panel_y + 160}" r="{head_r}" fill="none" stroke="url(#heroAccent)" stroke-width="4" filter="url(#glow)"/>
  <path d="M {x_a + panel_w // 2 - 55} {panel_y + 230} Q {x_a + panel_w // 2} {panel_y + 210} {x_a + panel_w // 2 + 55} {panel_y + 230} L {x_a + panel_w // 2 + 70} {panel_y + 450} L {x_a + panel_w // 2 - 70} {panel_y + 450} Z" fill="#1E202F" stroke="url(#heroAccent)" stroke-width="3"/>
  <rect x="{x_a + panel_w // 2 - leg_w - 5}" y="{panel_y + 450}" width="{leg_w}" height="{leg_h}" rx="8" fill="#282B3E" stroke="#3A3E56" stroke-width="2"/>
  <rect x="{x_a + panel_w // 2 + 5}" y="{panel_y + 450}" width="{leg_w}" height="{leg_h}" rx="8" fill="#282B3E" stroke="#3A3E56" stroke-width="2"/>

  <!-- Panel 2: 3/4 Dynamic Profile -->
  <rect x="{x_b}" y="{panel_y}" width="{panel_w}" height="{panel_h}" rx="10" fill="#151722" stroke="#2F3242" stroke-width="1"/>
  <text x="{x_b + 20}" y="{panel_y + 40}" font-family="'JetBrains Mono', monospace" font-size="14" fill="#8E92A8">PANEL B: 3/4 ANGLE</text>
  <!-- Stylized Figure 3/4 -->
  <circle cx="{x_b + panel_w // 2}" cy="{panel_y + 160}" r="{head_r}" fill="none" stroke="url(#heroAccent)" stroke-width="4"/>
  <path d="M {x_b + panel_w // 2 - 45} {panel_y + 230} Q {x_b + panel_w // 2 + 15} {panel_y + 215} {x_b + panel_w // 2 + 55} {panel_y + 245} L {x_b + panel_w // 2 + 65} {panel_y + 450} L {x_b + panel_w // 2 - 65} {panel_y + 450} Z" fill="#1E202F" stroke="url(#heroAccent)" stroke-width="3"/>
  <rect x="{x_b + panel_w // 2 - leg_w - 5}" y="{panel_y + 450}" width="{leg_w}" height="{leg_h}" rx="8" fill="#282B3E" stroke="#3A3E56" stroke-width="2"/>
  <rect x="{x_b + panel_w // 2 + 5}" y="{panel_y + 450}" width="{leg_w}" height="{leg_h}" rx="8" fill="#282B3E" stroke="#3A3E56" stroke-width="2"/>

  <!-- Panel 3: Tight Profile Macro -->
  <rect x="{x_c}" y="{panel_y}" width="{panel_w}" height="{panel_h}" rx="10" fill="#151722" stroke="#2F3242" stroke-width="1"/>
  <text x="{x_c + 20}" y="{panel_y + 40}" font-family="'JetBrains Mono', monospace" font-size="14" fill="#8E92A8">PANEL C: PROFILE</text>
  <circle cx="{x_c + panel_w // 2}" cy="{panel_y + 190}" r="{int(head_r * 1.3)}" fill="none" stroke="url(#heroAccent)" stroke-width="4" filter="url(#glow)"/>
  <!-- Facial Profile Path -->
  <path d="M {x_c + panel_w // 2} {panel_y + 130} Q {x_c + panel_w // 2 + 50} {panel_y + 160} {x_c + panel_w // 2 + 50} {panel_y + 190} L {x_c + panel_w // 2 + 30} {panel_y + 220} L {x_c + panel_w // 2 + 60} {panel_y + 260} L {x_c + panel_w // 2 + 20} {panel_y + 285}" fill="none" stroke="#00F0FF" stroke-width="3"/>
  <path d="M {x_c + panel_w // 2 - 60} {panel_y + 300} Q {x_c + panel_w // 2 + 20} {panel_y + 280} {x_c + panel_w // 2 + 70} {panel_y + 330} L {x_c + panel_w // 2 + 70} {panel_y + 510} L {x_c + panel_w // 2 - 60} {panel_y + 510} Z" fill="#1E202F" stroke="url(#heroAccent)" stroke-width="3"/>

    <!-- Telemetry Lower Bar -->
  <rect x="{pad}" y="{view_h - 100}" width="{view_w - 2 * pad}" height="60" rx="8" fill="#0C0D13" stroke="#2F3242" stroke-width="1"/>
  <text x="{pad + 25}" y="{view_h - 63}" font-family="'JetBrains Mono', monospace" font-size="14" fill="#00F0FF">
    SUBJECT: {html.escape(char.name.upper())} | SILHOUETTE: {html.escape(char.silhouette[:50])}...
  </text>
  <text x="{view_w - pad - 25}" y="{view_h - 63}" font-family="'JetBrains Mono', monospace" font-size="13" fill="#E5A93C" text-anchor="end">
    WARDROBE POLARITY: {html.escape(char.wardrobe_polarity[:45])}...
  </text>
</svg>"""

    def render_environment_plate_svg(
        self,
        env: MasterEnvironmentSpec,
        bible: MasterProductionBible
    ) -> str:
        """Renders Anchor 2: Master Architectural Environment Plate SVG scaled to viewBox."""
        palette = bible.color_palette or ["#0D1117", "#58A6FF", "#3FB950", "#D29922"]
        c1, c2 = palette[0], palette[1 % len(palette)]
        view_w, view_h = self._aspect_dimensions(bible.aspect_ratio)

        pad = 40
        horizon_y = int(view_h * 0.65)
        center_x = view_w // 2
        center_y = view_h // 2
        win_x = int(view_w * 0.05)
        win_w = int(view_w * 0.22)
        win_y = int(view_h * 0.15)
        win_h = int(view_h * 0.45)

        return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {view_w} {view_h}" width="100%" height="100%">
  <defs>
    <linearGradient id="envGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{c1}"/>
      <stop offset="100%" stop-color="#080A0F"/>
    </linearGradient>
    <linearGradient id="lightRay" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{c2}" stop-opacity="0.35"/>
      <stop offset="100%" stop-color="{c2}" stop-opacity="0.0"/>
    </linearGradient>
  </defs>

  <rect width="{view_w}" height="{view_h}" fill="url(#envGrad)"/>

  <!-- Architectural Perspective Lines -->
  <!-- Floorboard Lines -->
  <line x1="0" y1="{horizon_y}" x2="{view_w}" y2="{horizon_y}" stroke="#2D333B" stroke-width="2"/>
  <line x1="{center_x}" y1="{horizon_y}" x2="{int(view_w * 0.1)}" y2="{view_h}" stroke="#30363D" stroke-width="1.5"/>
  <line x1="{center_x}" y1="{horizon_y}" x2="{int(view_w * 0.3)}" y2="{view_h}" stroke="#30363D" stroke-width="1.5"/>
  <line x1="{center_x}" y1="{horizon_y}" x2="{center_x}" y2="{view_h}" stroke="#30363D" stroke-width="1.5"/>
  <line x1="{center_x}" y1="{horizon_y}" x2="{int(view_w * 0.7)}" y2="{view_h}" stroke="#30363D" stroke-width="1.5"/>
  <line x1="{center_x}" y1="{horizon_y}" x2="{int(view_w * 0.9)}" y2="{view_h}" stroke="#30363D" stroke-width="1.5"/>

  <!-- Architectural Window Structure (Left) -->
  <rect x="{win_x}" y="{win_y}" width="{win_w}" height="{win_h}" fill="none" stroke="{c2}" stroke-width="3"/>
  <line x1="{win_x + win_w // 2}" y1="{win_y}" x2="{win_x + win_w // 2}" y2="{win_y + win_h}" stroke="{c2}" stroke-width="2"/>
  <line x1="{win_x}" y1="{win_y + win_h // 3}" x2="{win_x + win_w}" y2="{win_y + win_h // 3}" stroke="{c2}" stroke-width="2"/>
  <line x1="{win_x}" y1="{win_y + 2 * win_h // 3}" x2="{win_x + win_w}" y2="{win_y + 2 * win_h // 3}" stroke="{c2}" stroke-width="2"/>

  <!-- Volumetric Sunlight Beam -->
  <polygon points="{win_x},{win_y} {win_x + win_w},{win_y} {int(view_w * 0.85)},{view_h} {int(view_w * 0.25)},{view_h}" fill="url(#lightRay)"/>

  <!-- Back Wall Minimalist Architecture -->
  <line x1="{center_x}" y1="{int(view_h * 0.18)}" x2="{center_x}" y2="{horizon_y}" stroke="#21262D" stroke-width="1.5"/>
  <line x1="0" y1="{int(view_h * 0.18)}" x2="{view_w}" y2="{int(view_h * 0.18)}" stroke="#21262D" stroke-width="1"/>

  <!-- Camera Reticle Overlay -->
  <circle cx="{center_x}" cy="{center_y}" r="30" fill="none" stroke="#58A6FF" stroke-width="1" stroke-dasharray="4,4"/>
  <line x1="{center_x - 20}" y1="{center_y}" x2="{center_x + 20}" y2="{center_y}" stroke="#58A6FF" stroke-width="1.5"/>
  <line x1="{center_x}" y1="{center_y - 20}" x2="{center_x}" y2="{center_y + 20}" stroke="#58A6FF" stroke-width="1.5"/>
  <!-- Corner Reticles -->
  <path d="M 60 140 L 60 80 L 120 80" fill="none" stroke="#8B949E" stroke-width="2"/>
  <path d="M {view_w - 60} 140 L {view_w - 60} 80 L {view_w - 120} 80" fill="none" stroke="#8B949E" stroke-width="2"/>
  <path d="M 60 {view_h - 140} L 60 {view_h - 80} L 120 {view_h - 80}" fill="none" stroke="#8B949E" stroke-width="2"/>
  <path d="M {view_w - 60} {view_h - 140} L {view_w - 60} {view_h - 80} L {view_w - 120} {view_h - 80}" fill="none" stroke="#8B949E" stroke-width="2"/>

  <!-- Top Title HUD -->
  <rect x="{pad}" y="40" width="{view_w - 2 * pad}" height="65" rx="8" fill="#0D1117" stroke="#30363D" stroke-width="1.5"/>
  <text x="{pad + 25}" y="80" font-family="'Space Grotesk', sans-serif" font-size="20" font-weight="700" fill="#58A6FF" letter-spacing="2">
    ANCHOR 2: MASTER ARCHITECTURAL ENVIRONMENT PLATE
  </text>
  <text x="{view_w - pad - 25}" y="80" font-family="'JetBrains Mono', monospace" font-size="14" fill="#8B949E" text-anchor="end">
    ZERO-CHARACTER PLATE | VOLUMETRIC LIGHTING LOCK
  </text>

  <!-- Lower Telemetry -->
  <rect x="{pad}" y="{view_h - 100}" width="{view_w - 2 * pad}" height="60" rx="8" fill="#0D1117" stroke="#30363D" stroke-width="1.5"/>
  <text x="{pad + 25}" y="{view_h - 63}" font-family="'JetBrains Mono', monospace" font-size="14" fill="#3FB950">
    LOCATION: {html.escape(env.location_name.upper())} | ARCHITECTURE: {html.escape(env.spatial_architecture[:50])}...
  </text>
  <text x="{view_w - pad - 25}" y="{view_h - 63}" font-family="'JetBrains Mono', monospace" font-size="13" fill="#D29922" text-anchor="end">
    LIGHTING: {html.escape(env.lighting_setup[:45])}...
  </text>
</svg>"""

    def render_scene_keyframe_svg(
        self,
        scene: Union[SceneKeyframeSpec, Any],
        bible: MasterProductionBible,
        show_safe_guides: bool = True,
    ) -> str:
        """Renders Anchor 3: Scene Keyframe / Boundary Plate SVG scaled to viewBox."""
        palette = bible.color_palette or ["#0F172A", "#38BDF8", "#F43F5E", "#E2E8F0"]
        c1, c2, c3 = palette[0], palette[1 % len(palette)], palette[2 % len(palette)]
        view_w, view_h = self._aspect_dimensions(bible.aspect_ratio)

        pad = 40
        center_x = view_w // 2
        center_y = view_h // 2
        max_dim = min(view_w, view_h)
        r_outer = int(max_dim * 0.35)
        r_mid = int(max_dim * 0.20)
        r_inner = int(max_dim * 0.08)

        rig_info = scene.craft_camera.to_summary() if hasattr(scene, "craft_camera") and scene.craft_camera else "35mm Prime | Centered"
        regime_str = scene.regime.value.split(':')[0] if hasattr(scene.regime, "value") else str(scene.regime).split(':')[0]

        safe_guides_markup = ""
        if show_safe_guides:
            action_w = int(view_w * 0.90)
            action_h = int(view_h * 0.90)
            action_x = (view_w - action_w) // 2
            action_y = (view_h - action_h) // 2

            title_w = int(view_w * 0.80)
            title_h = int(view_h * 0.80)
            title_x = (view_w - title_w) // 2
            title_y = (view_h - title_h) // 2

            safe_guides_markup = f"""
  <!-- SMPTE Safe Guides -->
  <rect class="safe-guide-action" x="{action_x}" y="{action_y}" width="{action_w}" height="{action_h}" fill="none" stroke="#64748B" stroke-width="1.5" stroke-dasharray="6,6" opacity="0.6"/>
  <rect class="safe-guide-title" x="{title_x}" y="{title_y}" width="{title_w}" height="{title_h}" fill="none" stroke="#475569" stroke-width="1" stroke-dasharray="3,3" opacity="0.4"/>"""

        return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {view_w} {view_h}" width="100%" height="100%">
  <defs>
    <linearGradient id="sceneGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{c1}"/>
      <stop offset="100%" stop-color="#020617"/>
    </linearGradient>
  </defs>

  <rect width="{view_w}" height="{view_h}" fill="url(#sceneGrad)"/>
{safe_guides_markup}

  <!-- Depth Staging Grid -->
  <circle cx="{center_x}" cy="{center_y}" r="{r_outer}" fill="none" stroke="#1E293B" stroke-width="1.5"/>
  <circle cx="{center_x}" cy="{center_y}" r="{r_mid}" fill="none" stroke="#334155" stroke-width="1.5" stroke-dasharray="6,6"/>
  <circle cx="{center_x}" cy="{center_y}" r="{r_inner}" fill="none" stroke="{c2}" stroke-width="2"/>

  <!-- Dynamic Vector Arrow -->
  <path d="M {center_x - int(r_outer * 0.7)} {center_y + int(r_outer * 0.5)} Q {center_x} {center_y} {center_x + int(r_outer * 0.7)} {center_y + int(r_outer * 0.5)}" fill="none" stroke="{c3}" stroke-width="4" stroke-linecap="round"/>
  <polygon points="{center_x + int(r_outer * 0.7)},{center_y + int(r_outer * 0.5)} {center_x + int(r_outer * 0.7) - 20},{center_y + int(r_outer * 0.5) - 15} {center_x + int(r_outer * 0.7) - 15},{center_y + int(r_outer * 0.5) + 10}" fill="{c3}"/>

  <!-- Center Action Node -->
  <circle cx="{center_x}" cy="{center_y}" r="16" fill="{c2}"/>
  <line x1="{center_x}" y1="{center_y - 80}" x2="{center_x}" y2="{center_y + 80}" stroke="{c2}" stroke-width="2"/>
  <line x1="{center_x - 80}" y1="{center_y}" x2="{center_x + 80}" y2="{center_y}" stroke="{c2}" stroke-width="2"/>

  <!-- Top Bar -->
  <rect x="{pad}" y="40" width="{view_w - 2 * pad}" height="65" rx="8" fill="#0B132B" stroke="#1C2541" stroke-width="1.5"/>
  <text x="{pad + 25}" y="80" font-family="'Space Grotesk', sans-serif" font-size="20" font-weight="700" fill="{c2}" letter-spacing="2">
    SCENE {scene.scene_index}: {html.escape(scene.scene_title.upper())}
  </text>
  <text x="{view_w - pad - 25}" y="80" font-family="'JetBrains Mono', monospace" font-size="14" fill="#94A3B8" text-anchor="end">
    WINDOW: {html.escape(scene.timestamp_range)} | {html.escape(regime_str)}
  </text>

  <!-- Lower Telemetry -->
  <rect x="{pad}" y="{view_h - 100}" width="{view_w - 2 * pad}" height="60" rx="8" fill="#0B132B" stroke="#1C2541" stroke-width="1.5"/>
  <text x="{pad + 25}" y="{view_h - 63}" font-family="'JetBrains Mono', monospace" font-size="14" fill="#38BDF8">
    CRAFT RIG: {html.escape(rig_info)}
  </text>
  <text x="{view_w - pad - 25}" y="{view_h - 63}" font-family="'JetBrains Mono', monospace" font-size="13" fill="#F43F5E" text-anchor="end">
    PHYSICS: 1.0X REALTIME LOCK | SEEDANCE KINETIC ENGINE
  </text>
</svg>"""

    def generate_svg_storyboard_frame(
        self,
        scene: Union[SceneKeyframeSpec, Any],
        bible: MasterProductionBible,
        show_safe_guides: bool = True,
    ) -> str:
        """Alias for render_scene_keyframe_svg with SMPTE safe guides."""
        return self.render_scene_keyframe_svg(scene, bible, show_safe_guides=show_safe_guides)


def generate_svg_storyboard_frame(
    scene: Union[SceneKeyframeSpec, Any],
    bible: MasterProductionBible,
    show_safe_guides: bool = True,
) -> str:
    """Module-level generator for storyboard frame SVG with SMPTE safe guides."""
    engine = NanoBananaStoryboardEngine()
    return engine.render_scene_keyframe_svg(scene, bible, show_safe_guides=show_safe_guides)
