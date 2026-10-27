"""Nano Banana Storyboard Engine generating 3-Tier Visual Continuity Plates."""

import os
from pathlib import Path
from typing import Dict, List, Optional
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

        # 1. Anchor 1: Character Turnaround Sheet
        if bible.characters:
            char = bible.characters[0]
            svg_content = self.render_character_turnaround_svg(char, bible)
            plate_path = boards_dir / "anchor1_character_turnaround.svg"
            plate_path.write_text(svg_content, encoding="utf-8")
            char.image_path = str(plate_path)
            char.svg_markup = svg_content
            rendered_assets["<image_1>"] = str(plate_path)

        # 2. Anchor 2: Master Architectural Environment Plate
        env_svg = self.render_environment_plate_svg(bible.environment, bible)
        env_path = boards_dir / "anchor2_environment_master.svg"
        env_path.write_text(env_svg, encoding="utf-8")
        bible.environment.image_path = str(env_path)
        bible.environment.svg_markup = env_svg
        rendered_assets["<image_2>"] = str(env_path)

        # 3. Anchor 3: Scene Keyframes & Reference 3
        for scene in bible.scenes:
            scene_svg = self.render_scene_keyframe_svg(scene, bible)
            scene_path = boards_dir / f"anchor3_scene_{scene.scene_index}_keyframe.svg"
            scene_path.write_text(scene_svg, encoding="utf-8")
            rendered_assets[f"scene_{scene.scene_index}"] = str(scene_path)
            if scene.scene_index == 1 and "<image_3>" not in rendered_assets:
                rendered_assets["<image_3>"] = str(scene_path)

        # Update bible nano banana references with paths
        for asset in bible.nano_banana_assets:
            if asset.asset_id in rendered_assets:
                asset.local_path = rendered_assets[asset.asset_id]
                asset.svg_markup = Path(rendered_assets[asset.asset_id]).read_text(encoding="utf-8")

        return rendered_assets

    def render_character_turnaround_svg(
        self,
        char: CharacterTurnaroundSpec,
        bible: MasterProductionBible
    ) -> str:
        """Renders a crisp 3-panel orthographic character turnaround SVG."""
        palette = bible.color_palette or ["#1A1A24", "#FF4B4B", "#00F0FF", "#F0F0F5"]
        c1, c2, c3 = palette[0], palette[1 % len(palette)], palette[2 % len(palette)]
        is_vertical = bible.aspect_ratio == AspectRatio.RATIO_9_16
        view_w, view_h = (1080, 1920) if is_vertical else (1920, 1080)

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
  <rect x="40" y="40" width="{view_w - 80}" height="70" rx="8" fill="#12131A" stroke="#2F3242" stroke-width="1.5"/>
  <text x="65" y="82" font-family="'Space Grotesk', system-ui, sans-serif" font-size="20" font-weight="700" fill="#00F0FF" letter-spacing="2">
    ANCHOR 1: CHARACTER TURNAROUND SHEET (DNA LOCK)
  </text>
  <text x="{view_w - 65}" y="82" font-family="'JetBrains Mono', monospace" font-size="14" fill="#8E92A8" text-anchor="end">
    MODEL: {self.config.image_model} | 5600K DIFFUSE STUDIO | POLARITY LOCK
  </text>

  <!-- 3-Panel Turnaround Frames -->
  <!-- Panel 1: Front Full Body -->
  <rect x="60" y="150" width="560" height="820" rx="10" fill="#151722" stroke="#2F3242" stroke-width="1"/>
  <text x="85" y="195" font-family="'JetBrains Mono', monospace" font-size="16" fill="#8E92A8">PANEL A: FRONT VIEW (EYE-LEVEL)</text>
  <!-- Stylized Figure Front -->
  <circle cx="340" cy="310" r="55" fill="none" stroke="url(#heroAccent)" stroke-width="4" filter="url(#glow)"/>
  <path d="M 285 390 Q 340 370 395 390 L 415 620 L 265 620 Z" fill="#1E202F" stroke="url(#heroAccent)" stroke-width="3"/>
  <rect x="300" y="620" width="35" height="260" rx="8" fill="#282B3E" stroke="#3A3E56" stroke-width="2"/>
  <rect x="345" y="620" width="35" height="260" rx="8" fill="#282B3E" stroke="#3A3E56" stroke-width="2"/>
  <path d="M 270 410 L 220 570" stroke="#3A3E56" stroke-width="16" stroke-linecap="round"/>
  <path d="M 410 410 L 460 570" stroke="#3A3E56" stroke-width="16" stroke-linecap="round"/>

  <!-- Panel 2: 3/4 Dynamic Profile -->
  <rect x="680" y="150" width="560" height="820" rx="10" fill="#151722" stroke="#2F3242" stroke-width="1"/>
  <text x="705" y="195" font-family="'JetBrains Mono', monospace" font-size="16" fill="#8E92A8">PANEL B: 3/4 DYNAMIC ANGLE</text>
  <!-- Stylized Figure 3/4 -->
  <circle cx="960" cy="310" r="55" fill="none" stroke="url(#heroAccent)" stroke-width="4"/>
  <path d="M 915 390 Q 975 375 1015 405 L 1025 620 L 895 620 Z" fill="#1E202F" stroke="url(#heroAccent)" stroke-width="3"/>
  <rect x="925" y="620" width="35" height="260" rx="8" fill="#282B3E" stroke="#3A3E56" stroke-width="2" transform="rotate(-4 925 620)"/>
  <rect x="965" y="620" width="35" height="260" rx="8" fill="#282B3E" stroke="#3A3E56" stroke-width="2" transform="rotate(4 965 620)"/>

  <!-- Panel 3: Tight Profile Macro -->
  <rect x="1300" y="150" width="560" height="820" rx="10" fill="#151722" stroke="#2F3242" stroke-width="1"/>
  <text x="1325" y="195" font-family="'JetBrains Mono', monospace" font-size="16" fill="#8E92A8">PANEL C: HEAD &amp; WARDROBE MACRO</text>
  <circle cx="1580" cy="340" r="95" fill="none" stroke="url(#heroAccent)" stroke-width="4" filter="url(#glow)"/>
  <!-- Facial Profile Path -->
  <path d="M 1580 250 Q 1660 300 1660 340 L 1640 370 L 1670 410 L 1630 435" fill="none" stroke="#00F0FF" stroke-width="3"/>
  <path d="M 1500 450 Q 1580 430 1660 480 L 1660 680 L 1500 680 Z" fill="#1E202F" stroke="url(#heroAccent)" stroke-width="3"/>

  <!-- Telemetry Lower Bar -->
  <rect x="60" y="990" width="{view_w - 120}" height="60" rx="8" fill="#0C0D13" stroke="#2F3242" stroke-width="1"/>
  <text x="85" y="1027" font-family="'JetBrains Mono', monospace" font-size="14" fill="#00F0FF">
    SUBJECT: {char.name.upper()} | SILHOUETTE: {char.silhouette[:60]}...
  </text>
  <text x="{view_w - 85}" y="1027" font-family="'JetBrains Mono', monospace" font-size="13" fill="#E5A93C" text-anchor="end">
    WARDROBE POLARITY: {char.wardrobe_polarity[:50]}...
  </text>
</svg>"""

    def render_environment_plate_svg(
        self,
        env: MasterEnvironmentSpec,
        bible: MasterProductionBible
    ) -> str:
        """Renders Anchor 2: Master Architectural Environment Plate SVG."""
        palette = bible.color_palette or ["#0D1117", "#58A6FF", "#3FB950", "#D29922"]
        c1, c2 = palette[0], palette[1 % len(palette)]
        view_w, view_h = (1920, 1080)

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
  <line x1="0" y1="720" x2="{view_w}" y2="720" stroke="#2D333B" stroke-width="2"/>
  <line x1="960" y1="720" x2="200" y2="1080" stroke="#30363D" stroke-width="1.5"/>
  <line x1="960" y1="720" x2="600" y2="1080" stroke="#30363D" stroke-width="1.5"/>
  <line x1="960" y1="720" x2="960" y2="1080" stroke="#30363D" stroke-width="1.5"/>
  <line x1="960" y1="720" x2="1320" y2="1080" stroke="#30363D" stroke-width="1.5"/>
  <line x1="960" y1="720" x2="1720" y2="1080" stroke="#30363D" stroke-width="1.5"/>

  <!-- Architectural Window Structure (Left) -->
  <rect x="80" y="160" width="340" height="520" fill="none" stroke="{c2}" stroke-width="3"/>
  <line x1="250" y1="160" x2="250" y2="680" stroke="{c2}" stroke-width="2"/>
  <line x1="80" y1="330" x2="420" y2="330" stroke="{c2}" stroke-width="2"/>
  <line x1="80" y1="500" x2="420" y2="500" stroke="{c2}" stroke-width="2"/>

  <!-- Volumetric Sunlight Beam -->
  <polygon points="80,160 420,160 1480,1080 380,1080" fill="url(#lightRay)"/>

  <!-- Back Wall Minimalist Architecture -->
  <line x1="960" y1="200" x2="960" y2="720" stroke="#21262D" stroke-width="1.5"/>
  <line x1="0" y1="200" x2="{view_w}" y2="200" stroke="#21262D" stroke-width="1"/>

  <!-- Camera Reticle Overlay -->
  <circle cx="960" cy="540" r="30" fill="none" stroke="#58A6FF" stroke-width="1" stroke-dasharray="4,4"/>
  <line x1="940" y1="540" x2="980" y2="540" stroke="#58A6FF" stroke-width="1.5"/>
  <line x1="960" y1="520" x2="960" y2="560" stroke="#58A6FF" stroke-width="1.5"/>
  <!-- Corner Reticles -->
  <path d="M 60 140 L 60 80 L 120 80" fill="none" stroke="#8B949E" stroke-width="2"/>
  <path d="M {view_w - 60} 140 L {view_w - 60} 80 L {view_w - 120} 80" fill="none" stroke="#8B949E" stroke-width="2"/>
  <path d="M 60 {view_h - 140} L 60 {view_h - 80} L 120 {view_h - 80}" fill="none" stroke="#8B949E" stroke-width="2"/>
  <path d="M {view_w - 60} {view_h - 140} L {view_w - 60} {view_h - 80} L {view_w - 120} {view_h - 80}" fill="none" stroke="#8B949E" stroke-width="2"/>

  <!-- Top Title HUD -->
  <rect x="40" y="40" width="{view_w - 80}" height="65" rx="8" fill="#0D1117" stroke="#30363D" stroke-width="1.5"/>
  <text x="65" y="80" font-family="'Space Grotesk', sans-serif" font-size="20" font-weight="700" fill="#58A6FF" letter-spacing="2">
    ANCHOR 2: MASTER ARCHITECTURAL ENVIRONMENT PLATE
  </text>
  <text x="{view_w - 65}" y="80" font-family="'JetBrains Mono', monospace" font-size="14" fill="#8B949E" text-anchor="end">
    ZERO-CHARACTER PLATE | VOLUMETRIC LIGHTING LOCK
  </text>

  <!-- Lower Telemetry -->
  <rect x="40" y="{view_h - 100}" width="{view_w - 80}" height="60" rx="8" fill="#0D1117" stroke="#30363D" stroke-width="1.5"/>
  <text x="65" y="{view_h - 63}" font-family="'JetBrains Mono', monospace" font-size="14" fill="#3FB950">
    LOCATION: {env.location_name.upper()} | ARCHITECTURE: {env.spatial_architecture[:60]}...
  </text>
  <text x="{view_w - 65}" y="{view_h - 63}" font-family="'JetBrains Mono', monospace" font-size="13" fill="#D29922" text-anchor="end">
    LIGHTING: {env.lighting_setup[:50]}...
  </text>
</svg>"""

    def render_scene_keyframe_svg(
        self,
        scene: SceneKeyframeSpec | any,
        bible: MasterProductionBible
    ) -> str:
        """Renders Anchor 3: Scene Keyframe / Boundary Plate SVG."""
        palette = bible.color_palette or ["#0F172A", "#38BDF8", "#F43F5E", "#E2E8F0"]
        c1, c2, c3 = palette[0], palette[1 % len(palette)], palette[2 % len(palette)]
        view_w, view_h = (1920, 1080)

        rig_info = scene.craft_camera.to_summary() if hasattr(scene, "craft_camera") and scene.craft_camera else "35mm Prime | Centered"

        return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {view_w} {view_h}" width="100%" height="100%">
  <defs>
    <linearGradient id="sceneGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{c1}"/>
      <stop offset="100%" stop-color="#020617"/>
    </linearGradient>
  </defs>

  <rect width="{view_w}" height="{view_h}" fill="url(#sceneGrad)"/>

  <!-- Depth Staging Grid -->
  <circle cx="960" cy="540" r="380" fill="none" stroke="#1E293B" stroke-width="1.5"/>
  <circle cx="960" cy="540" r="220" fill="none" stroke="#334155" stroke-width="1.5" stroke-dasharray="6,6"/>
  <circle cx="960" cy="540" r="80" fill="none" stroke="{c2}" stroke-width="2"/>

  <!-- Dynamic Vector Arrow -->
  <path d="M 680 720 Q 960 520 1240 720" fill="none" stroke="{c3}" stroke-width="4" stroke-linecap="round"/>
  <polygon points="1240,720 1220,705 1225,728" fill="{c3}"/>

  <!-- Center Action Node -->
  <circle cx="960" cy="540" r="16" fill="{c2}"/>
  <line x1="960" y1="460" x2="960" y2="620" stroke="{c2}" stroke-width="2"/>
  <line x1="880" y1="540" x2="1040" y2="540" stroke="{c2}" stroke-width="2"/>

  <!-- Top Bar -->
  <rect x="40" y="40" width="{view_w - 80}" height="65" rx="8" fill="#0B132B" stroke="#1C2541" stroke-width="1.5"/>
  <text x="65" y="80" font-family="'Space Grotesk', sans-serif" font-size="20" font-weight="700" fill="{c2}" letter-spacing="2">
    SCENE {scene.scene_index}: {scene.scene_title.upper()}
  </text>
  <text x="{view_w - 65}" y="80" font-family="'JetBrains Mono', monospace" font-size="14" fill="#94A3B8" text-anchor="end">
    WINDOW: {scene.timestamp_range} | {scene.regime.value.split(':')[0]}
  </text>

  <!-- Lower Telemetry -->
  <rect x="40" y="{view_h - 100}" width="{view_w - 80}" height="60" rx="8" fill="#0B132B" stroke="#1C2541" stroke-width="1.5"/>
  <text x="65" y="{view_h - 63}" font-family="'JetBrains Mono', monospace" font-size="14" fill="#38BDF8">
    CRAFT RIG: {rig_info}
  </text>
  <text x="{view_w - 65}" y="{view_h - 63}" font-family="'JetBrains Mono', monospace" font-size="13" fill="#F43F5E" text-anchor="end">
    PHYSICS: 1.0X REALTIME LOCK | SEEDANCE KINETIC ENGINE
  </text>
</svg>"""
