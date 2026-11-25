"""Modular v2.12.0 Dark-Room Cinema HUD Components (PM-FEAT-023, PM-FEAT-024 & Departmental Toolbar).

Provides Python 3.11-compatible builders for:
1. Departmental Toolbar Grouping (.hud-actions organized into 5 accessible collapsible pill groups)
2. PM-FEAT-023: 180-Degree Blocking & Continuity HUD (#animatic-blocking-hud, [W] hotkey)
3. PM-FEAT-024: Client Review & Frame Pin Annotation HUD (#animatic-review-hud, [N] hotkey)
"""

from __future__ import annotations

import json
import math
import re
from html import escape as html_escape
from typing import Any, Dict, List, Tuple

from omni_director.schemas import MasterProductionBible, ProductionBundle
from omni_director.tools.continuity_blocking import (
    generate_blocking_floorplan_svg,
    generate_continuity_log_csv,
    generate_continuity_manifest_json,
    synthesize_default_continuity_blocking,
)
from omni_director.tools.review_notes import (
    generate_client_signoff_md,
    generate_frameio_review_json,
    generate_resolve_marker_edl,
    generate_review_fcpxml_markers,
    synthesize_default_client_review,
)


def _escape_js_template_literal(text: str) -> str:
    """Escapes backslashes, backticks, template interpolations, and closing script tags for safe JS template literals."""
    escaped = text.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
    return re.sub(r"</(script)", r"<\/\1", escaped, flags=re.IGNORECASE)


def _build_departmental_toolbar_html() -> str:
    """Builds the 5 accessible collapsible/pill department groups inside .hud-actions."""
    return """    <div class="hud-actions">
      <div class="dept-toolbar" role="navigation" aria-label="Production Department HUD Launchers">
        <div class="dept-group" id="dept-group-camera" role="group" aria-label="Camera and Blocking Department">
          <button type="button" class="dept-pill-toggle" id="dept-toggle-camera" onclick="toggleDeptGroup('camera')" aria-expanded="false" aria-controls="dept-tray-camera">
            <span class="dept-pill-icon" aria-hidden="true">🎥</span>
            <span>Camera &amp; Blocking</span>
            <span class="dept-count">4</span>
            <span class="dept-caret" aria-hidden="true">▾</span>
          </button>
          <div class="dept-tray" id="dept-tray-camera" role="group" aria-label="Camera and Blocking Tools" hidden>
            <button type="button" class="btn-dof" id="btn-dof-animatic" onclick="toggleDoFHUD()" aria-label="Optical DoF HUD [F]" aria-expanded="false" aria-controls="animatic-dof-hud">
              🎯 Optical DoF HUD [F]
            </button>
            <button type="button" class="btn-dit-lut" id="btn-drone-animatic" onclick="toggleDroneHUD()" aria-label="Drone Aerial Flight HUD [D]" aria-expanded="false" aria-controls="animatic-drone-hud">
              🚁 Drone [D]
            </button>
            <button type="button" class="btn-dof" id="btn-blocking-animatic" onclick="toggleBlockingHUD()" aria-label="180-Degree Blocking and Continuity HUD [W]" aria-expanded="false" aria-controls="animatic-blocking-hud">
              📐 Blocking [W]
            </button>
            <button type="button" class="btn-dof" id="btn-s3d-animatic" onclick="toggleS3dHUD()" aria-label="S3D Stereoscopy []]" aria-expanded="false" aria-controls="modal-s3d-stereography" title="S3D Stereoscopy []]">
              👓 S3D Stereoscopy []]
            </button>
          </div>
        </div>

        <div class="dept-group" id="dept-group-color" role="group" aria-label="Color and VFX Department">
          <button type="button" class="dept-pill-toggle" id="dept-toggle-color" onclick="toggleDeptGroup('color')" aria-expanded="false" aria-controls="dept-tray-color">
            <span class="dept-pill-icon" aria-hidden="true">🎨</span>
            <span>Color &amp; VFX</span>
            <span class="dept-count">5</span>
            <span class="dept-caret" aria-hidden="true">▾</span>
          </button>
          <div class="dept-tray" id="dept-tray-color" role="group" aria-label="Color and VFX Tools" hidden>
            <button type="button" class="btn-dit-lut" id="btn-dit-lut-animatic" onclick="toggleDitLutHUD()" aria-label="DIT 3D LUT Suite [L]" aria-expanded="false" aria-controls="animatic-dit-lut-hud">
              🎨 DIT 3D LUT Suite [L]
            </button>
            <button type="button" class="btn-dof" id="btn-hdr-animatic" onclick="toggleHdrHUD()" aria-label="HDR10/HLG Color Volume HUD [H]" aria-expanded="false" aria-controls="animatic-hdr-hud">
              🌈 HDR Color [H]
            </button>
            <button type="button" class="btn-dof" id="btn-film-animatic" onclick="toggleFilmHUD()" aria-label="Film Stock Emulation HUD [E]" aria-expanded="false" aria-controls="animatic-film-hud">
              🎞️ Film Stock [E]
            </button>
            <button type="button" class="btn-dit-lut" id="btn-vfx-animatic" onclick="toggleVfxHUD()" aria-label="VFX Passes HUD [X]" aria-expanded="false" aria-controls="animatic-vfx-hud">
              ✨ VFX Passes [X]
            </button>
            <button type="button" class="btn-dit-lut" id="btn-motion-gfx-animatic" onclick="toggleMotionGfxHUD()" aria-label="Motion Graphics, Supers and End-Card Studio [=]" aria-expanded="false" aria-controls="modal-motion-graphics-studio" title="Motion Graphics &amp; End-Card [=]">🎞️ Motion GFX [=]</button>
          </div>
        </div>

        <div class="dept-group" id="dept-group-audio" role="group" aria-label="Audio Department">
          <button type="button" class="dept-pill-toggle" id="dept-toggle-audio" onclick="toggleDeptGroup('audio')" aria-expanded="false" aria-controls="dept-tray-audio">
            <span class="dept-pill-icon" aria-hidden="true">🔊</span>
            <span>Audio</span>
            <span class="dept-count">3</span>
            <span class="dept-caret" aria-hidden="true">▾</span>
          </button>
          <div class="dept-tray" id="dept-tray-audio" role="group" aria-label="Audio Tools" hidden>
            <button type="button" class="btn-dof" id="btn-spatial-animatic" onclick="toggleSpatialHUD()" aria-label="Spatial Audio HUD [S]" aria-expanded="false" aria-controls="animatic-spatial-hud">
              🔊 Spatial Audio [S]
            </button>
            <button type="button" class="btn-dof" id="btn-spotting-animatic" onclick="toggleSpottingHUD()" aria-label="Editorial J-Cut / L-Cut Spotting and Beat-Grid HUD [J]" aria-expanded="false" aria-controls="animatic-spotting-hud">
              🎚️ J/L Spotting [J]
            </button>
            <button type="button" class="btn-mixer" id="btn-toggle-mixer" onclick="toggleMixer()" aria-label="Toggle Audio Console [M]" aria-expanded="false" aria-controls="animatic-audio-mixer">
              🎚️ AUDIO [M]
            </button>
          </div>
        </div>

        <div class="dept-group" id="dept-group-prep" role="group" aria-label="Prep and Budget Department">
          <button type="button" class="dept-pill-toggle" id="dept-toggle-prep" onclick="toggleDeptGroup('prep')" aria-expanded="false" aria-controls="dept-tray-prep">
            <span class="dept-pill-icon" aria-hidden="true">📋</span>
            <span>Prep &amp; Budget</span>
            <span class="dept-count">6</span>
            <span class="dept-caret" aria-hidden="true">▾</span>
          </button>
          <div class="dept-tray" id="dept-tray-prep" role="group" aria-label="Prep and Budget Tools" hidden>
            <button type="button" class="btn-dit-lut" id="btn-stripboard-animatic" onclick="toggleStripboardHUD()" aria-label="1st AD Stripboard Schedule HUD [B]" aria-expanded="false" aria-controls="animatic-stripboard-hud">
              📋 Stripboard [B]
            </button>
            <button type="button" class="btn-dit-lut" id="btn-slate-animatic" onclick="toggleSlateHUD()" aria-label="SMPTE Slate &amp; Offload Manifest HUD [T]" aria-expanded="false" aria-controls="animatic-slate-hud">
              🎬 Slate [T]
            </button>
            <button type="button" class="btn-dit-lut" id="btn-aicp-animatic" onclick="toggleAicpHUD()" aria-label="AICP Commercial Production Bid HUD [A]" aria-expanded="false" aria-controls="animatic-aicp-hud">
              💼 AICP [A]
            </button>
            <button type="button" class="btn-dit-lut" id="btn-safety-animatic" onclick="toggleSafetyHUD()" aria-label="On-Set Safety Risk and Exclusion Zone HUD [Z]" aria-expanded="false" aria-controls="animatic-safety-hud">
              🦺 Safety JSA [Z]
            </button>
            <button type="button" class="btn-dit-lut" id="btn-art-dept-animatic" onclick="toggleArtWardrobeHUD()" aria-label="Art &amp; Wardrobe Continuity Locker [\\]" aria-expanded="false" aria-controls="modal-art-wardrobe-continuity" title="Art &amp; Wardrobe [\\]">
              👗 Art &amp; Wardrobe [\\]
            </button>
            <button type="button" class="btn-dit-lut" id="btn-economics-animatic" onclick="toggleRenderEconomicsHUD()" aria-label="Compute &amp; Takes Economics Inspector [;]" aria-expanded="false" aria-controls="modal-render-economics" title="Compute &amp; Takes [;]">
              💎 Compute &amp; Takes [;]
            </button>
          </div>
        </div>

        <div class="dept-group" id="dept-group-delivery" role="group" aria-label="Delivery, QC and Review Department">
          <button type="button" class="dept-pill-toggle" id="dept-toggle-delivery" onclick="toggleDeptGroup('delivery')" aria-expanded="false" aria-controls="dept-tray-delivery">
            <span class="dept-pill-icon" aria-hidden="true">📡</span>
            <span>Delivery, QC &amp; Review</span>
            <span class="dept-count">7</span>
            <span class="dept-caret" aria-hidden="true">▾</span>
          </button>
          <div class="dept-tray dept-tray-right" id="dept-tray-delivery" role="group" aria-label="Delivery, QC and Review Tools" hidden>
            <button type="button" class="btn-dof" id="btn-reframe-animatic" onclick="toggleReframeHUD()" aria-label="Multi-Aspect Social Reframe and Cutdown HUD [R]" aria-expanded="false" aria-controls="animatic-reframe-hud">
              📐 Reframe [R]
            </button>
            <button type="button" class="btn-dit-lut" id="btn-qc-animatic" onclick="toggleQcHUD()" aria-label="Broadcast QC and Clearances HUD [Q]" aria-expanded="false" aria-controls="animatic-qc-hud">
              📡 Broadcast QC [Q]
            </button>
            <button type="button" class="btn-dof" id="btn-review-animatic" onclick="toggleReviewHUD()" aria-label="Client Review and Frame Pin Annotation HUD [N]" aria-expanded="false" aria-controls="animatic-review-hud">
              📝 Review [N]
            </button>
            <button type="button" class="btn-dof" id="btn-c2pa-animatic" onclick="toggleC2paHUD()" aria-label="C2PA Content Credentials and Provenance HUD [Y]" aria-expanded="false" aria-controls="animatic-c2pa-hud">
              🛡️ C2PA [Y]
            </button>
            <button type="button" class="btn-dit-lut" id="btn-localization-animatic" onclick="toggleLocalizationHUD()" aria-label="Localization, ADR Dubbing and Safe-Supers HUD [I]" aria-expanded="false" aria-controls="animatic-localization-hud">
              🌐 i18n / ADR [I]
            </button>
            <button type="button" class="btn-dit-lut" id="btn-ad-animatic" onclick="toggleAccessibilityAdHUD()" aria-label="AD &amp; CVAA [[]]" aria-expanded="false" aria-controls="modal-accessibility-ad" title="AD &amp; CVAA [[]">
              🗣️ AD &amp; CVAA [[]
            </button>
            <button type="button" class="btn-dit-lut" id="btn-otio-coherence-animatic" onclick="toggleOtioCoherenceHUD()" aria-label="OpenTimelineIO and Cross-Dept Coherence Matrix [']" aria-expanded="false" aria-controls="modal-otio-coherence" title="OTIO &amp; Coherence [']">🧭 OTIO Coherence [']</button>
          </div>
        </div>

        <button type="button" class="btn-dof" id="btn-command-palette-animatic" onclick="toggleHudCommandPalette()" aria-label="HUD Palette [/]" aria-expanded="false" aria-controls="modal-hud-command-palette" title="Unified HUD Command Palette [/]">
          ⌘ HUD Palette [/]
        </button>

        <button type="button" class="btn-export" id="btn-export-bible" onclick="exportProductionBible()" aria-label="Export Production Bible JSON">
          ⤓ Export Production Bible (.json)
        </button>
      </div>
      <span class="hud-hotkeys" aria-label="Keyboard shortcuts guide">
        ⌨ [Space] Play · [O] Loop · [/] HUD Palette · [\\] Art &amp; Wardrobe · [;] Compute &amp; Takes · [=] Motion GFX · ['] OTIO Coherence · [K] MoCo · [G] Gaffer · [F] DoF · [W] Blocking · [L] 3D LUT · [S] Spatial · [J] Spotting · [X] VFX · [H] HDR · [B] Stripboard · [E] Film · [T] Slate · [D] Drone · [A] AICP · [Z] Safety · [R] Reframe · [Q] QC · [N] Review · [Y] C2PA · [I] i18n/ADR · [M] Mixer · [C] Captions · [V] Viewfinder · [P] VP Stage · [U] Guides · []] S3D · [[] AD · [←/→] Seek 1s · [,/.] Frame · [Home/0] Rewind · [1-9] Scene
      </span>
    </div>"""


def _build_interactive_blocking_svg(manifest: Any) -> str:
    """Builds the interactive top-down 2D floorplan SVG with clickable per-scene camera wedges."""
    w, h = 840, 520
    cx, cy = 420.0, 260.0
    scale_px = 45.0

    def to_px(xm: float, ym: float) -> Tuple[float, float]:
        return round(cx + xm * scale_px, 1), round(cy - ym * scale_px, 1)

    parts: List[str] = [
        f'<svg id="blocking-floorplan-svg" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img" aria-label="Interactive Overhead 180-Degree Continuity Blocking Floorplan">',
        "  <defs>",
        '    <marker id="blk-arrow-motion" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">',
        '      <path d="M 0 1 L 10 5 L 0 9 z" fill="#38BDF8"/>',
        "    </marker>",
        "  </defs>",
        f'  <rect width="{w}" height="{h}" fill="#090B10" rx="8"/>',
        '  <rect x="24" y="54" width="792" height="420" fill="#101420" stroke="#202434" stroke-width="1.5" rx="6"/>',
    ]

    for gx in range(-7, 8):
        px_x, _ = to_px(float(gx), 0.0)
        if 30 <= px_x <= w - 30:
            parts.append(f'  <line x1="{px_x}" y1="54" x2="{px_x}" y2="474" stroke="#182032" stroke-width="0.8"/>')
    for gy in range(-4, 5):
        _, px_y = to_px(0.0, float(gy))
        if 60 <= px_y <= 470:
            parts.append(f'  <line x1="24" y1="{px_y}" x2="816" y2="{px_y}" stroke="#182032" stroke-width="0.8"/>')

    status_color = "#00FF88" if manifest.continuity_passed else "#FF3B30"
    status_label = "180° AXIS LOCKED" if manifest.continuity_passed else "CONTINUITY VIOLATION"
    title_esc = html_escape(str(manifest.project_title)[:48])
    parts.append(
        '  <text x="28" y="34" fill="#F0F2F8" font-family="JetBrains Mono, monospace" font-size="13" font-weight="700">'
        f"OVERHEAD STAGE BLOCKING — {title_esc}</text>"
    )
    parts.append(
        f'  <rect x="630" y="16" width="186" height="24" rx="4" fill="{status_color}" fill-opacity="0.16" stroke="{status_color}" stroke-width="1"/>'
    )
    parts.append(
        f'  <text x="723" y="32" text-anchor="middle" fill="{status_color}" font-family="JetBrains Mono, monospace" font-size="11" font-weight="700">{status_label}</text>'
    )

    axis_rad = math.radians(manifest.master_axis_deg)
    ax_dx = math.cos(axis_rad) * 7.8
    ax_dy = math.sin(axis_rad) * 7.8
    ax1_x, ax1_y = to_px(-ax_dx, -ax_dy)
    ax2_x, ax2_y = to_px(ax_dx, ax_dy)
    parts.append(
        f'  <line x1="{ax1_x}" y1="{ax1_y}" x2="{ax2_x}" y2="{ax2_y}" stroke="#FFB800" stroke-width="2" stroke-dasharray="8 6" opacity="0.9"/>'
    )
    parts.append(
        f'  <text x="44" y="{ax1_y - 8:.1f}" fill="#FFB800" font-family="JetBrains Mono, monospace" font-size="10" font-weight="700">'
        f"180° LINE OF ACTION ({html_escape(str(manifest.master_axis_side))})</text>"
    )

    cam_palette = ["#00F0FF", "#A78BFA", "#00FF88", "#FB7185", "#FFB800"]
    cone_len_m = 4.2
    for idx, blk in enumerate(manifest.scene_blockings):
        cam = blk.camera
        color = cam_palette[idx % len(cam_palette)] if blk.one_eighty_lock_ok else "#FF3B30"
        cam_px_x, cam_px_y = to_px(cam.x_meters, cam.y_meters)

        half_fov = cam.fov_deg / 2.0
        a1 = math.radians(cam.aim_azimuth_deg - half_fov)
        a2 = math.radians(cam.aim_azimuth_deg + half_fov)
        w1_x, w1_y = to_px(cam.x_meters + cone_len_m * math.cos(a1), cam.y_meters + cone_len_m * math.sin(a1))
        w2_x, w2_y = to_px(cam.x_meters + cone_len_m * math.cos(a2), cam.y_meters + cone_len_m * math.sin(a2))

        scale_s = blk.shot_scale.value if hasattr(blk.shot_scale, "value") else str(blk.shot_scale)
        s_idx = int(blk.scene_index)
        active_cls = " active" if idx == 0 else ""

        parts.append(
            f'  <g class="blocking-cam-node{active_cls}" id="blocking-cam-node-{s_idx}" data-scene-index="{s_idx}" '
            f'role="button" tabindex="0" aria-label="Jump to Scene {s_idx} camera blocking ({scale_s}, {cam.focal_length_mm}mm)" '
            f'onclick="selectBlockingScene({s_idx})" '
            f'onkeydown="if(event.key===\'Enter\'||event.key===\' \'||event.code===\'Space\'){{event.preventDefault();event.stopPropagation();selectBlockingScene({s_idx});}}">'
        )
        parts.append(
            f'    <polygon class="blocking-fov-cone" points="{cam_px_x},{cam_px_y} {w1_x},{w1_y} {w2_x},{w2_y}" '
            f'fill="{color}" fill-opacity="0.16" stroke="{color}" stroke-width="1.2" stroke-opacity="0.65"/>'
        )
        parts.append(
            f'    <circle class="blocking-cam-halo" cx="{cam_px_x}" cy="{cam_px_y}" r="12" fill="none" stroke="{color}" stroke-width="1.5" stroke-opacity="0.0"/>'
        )
        parts.append(
            f'    <circle class="blocking-cam-dot" cx="{cam_px_x}" cy="{cam_px_y}" r="7.5" fill="{color}" stroke="#090B10" stroke-width="1.5"/>'
        )
        parts.append(
            f'    <text x="{cam_px_x + 12:.1f}" y="{cam_px_y + 4:.1f}" fill="{color}" font-family="JetBrains Mono, monospace" font-size="10" font-weight="700">'
            f"S{s_idx} {html_escape(scale_s)} ({cam.focal_length_mm}mm)</text>"
        )
        parts.append("  </g>")

    seen_entities: Dict[str, Any] = {}
    for blk in manifest.scene_blockings:
        for ent in blk.entities:
            if ent.entity_id not in seen_entities:
                seen_entities[ent.entity_id] = ent

    for ent in seen_entities.values():
        ex, ey = to_px(ent.x_meters, ent.y_meters)
        ent_color = html_escape(str(ent.color_hex))
        parts.append(
            f'  <circle cx="{ex}" cy="{ey}" r="9" fill="{ent_color}" fill-opacity="0.88" stroke="#F0F2F8" stroke-width="1.5"/>'
        )
        if abs(ent.motion_dx_meters) > 0.05 or abs(ent.motion_dy_meters) > 0.05:
            mx, my = to_px(ent.x_meters + ent.motion_dx_meters, ent.y_meters + ent.motion_dy_meters)
            parts.append(
                f'  <line x1="{ex}" y1="{ey}" x2="{mx}" y2="{my}" stroke="#38BDF8" stroke-width="2" marker-end="url(#blk-arrow-motion)"/>'
            )
        parts.append(
            f'  <text x="{ex}" y="{ey - 13:.1f}" text-anchor="middle" fill="#F0F2F8" font-family="Space Grotesk, sans-serif" font-size="10" font-weight="600">'
            f"{html_escape(str(ent.label))}</text>"
        )

    parts.append(
        '  <text x="28" y="498" fill="#8E95AA" font-family="JetBrains Mono, monospace" font-size="10">'
        "Click any camera wedge to seek SMPTE timeline · Dashed Amber = 180° Axis · Blue Vector = Screen Travel</text>"
    )
    parts.append("</svg>")
    return "\n".join(parts)


def build_v212_hud_bundle(
    bible: MasterProductionBible,
    bundle: ProductionBundle,
    scene_time_lookup: Dict[int, Tuple[float, float]],
    total_runtime_sec: int,
) -> Dict[str, str]:
    """Builds all v2.12.0 UI fragments (Departmental Toolbar, PM-FEAT-023 Blocking HUD, PM-FEAT-024 Review HUD)."""
    # ------------------------------------------------------------------
    # PM-FEAT-023: 180-Degree Continuity Blocking Data Preparation
    # ------------------------------------------------------------------
    master_blocking = (
        getattr(bible, "master_continuity_blocking", None)
        or getattr(bible, "continuity_blocking", None)
    )
    if master_blocking is None:
        master_blocking = synthesize_default_continuity_blocking(bible)

    blocking_csv_escaped = _escape_js_template_literal(generate_continuity_log_csv(master_blocking))
    blocking_svg_escaped = _escape_js_template_literal(generate_blocking_floorplan_svg(master_blocking))
    blocking_json_escaped = _escape_js_template_literal(generate_continuity_manifest_json(master_blocking))
    interactive_blocking_svg = _build_interactive_blocking_svg(master_blocking)

    blocking_scenes_payload: List[Dict[str, Any]] = []
    blocking_scene_pills: List[str] = []
    for idx, blk in enumerate(master_blocking.scene_blockings):
        s_idx = int(blk.scene_index)
        st_s, en_s = scene_time_lookup.get(s_idx, ((s_idx - 1) * 5.0, s_idx * 5.0))
        scale_s = blk.shot_scale.value if hasattr(blk.shot_scale, "value") else str(blk.shot_scale)
        dir_s = blk.screen_direction.value if hasattr(blk.screen_direction, "value") else str(blk.screen_direction)
        cut_s = blk.cut_type_in.value if hasattr(blk.cut_type_in, "value") else str(blk.cut_type_in)
        blocking_scenes_payload.append({
            "scene_index": s_idx,
            "scene_title": str(blk.scene_title),
            "start_sec": round(st_s, 3),
            "end_sec": round(en_s, 3),
            "screen_direction": dir_s,
            "shot_scale": scale_s,
            "cut_type_in": cut_s,
            "axis_side": str(blk.axis_side),
            "line_of_action_deg": float(blk.line_of_action_deg),
            "eyeline_angle_deg": float(blk.eyeline_angle_deg),
            "one_eighty_lock_ok": bool(blk.one_eighty_lock_ok),
            "color_temp_kelvin": int(blk.color_temp_kelvin),
            "camera_id": str(blk.camera.camera_id),
            "aim_azimuth_deg": float(blk.camera.aim_azimuth_deg),
            "fov_deg": float(blk.camera.fov_deg),
            "focal_length_mm": int(blk.camera.focal_length_mm),
            "blocking_notes": str(blk.blocking_notes),
        })
        active_cls = " active" if idx == 0 else ""
        blocking_scene_pills.append(
            f'<button type="button" class="btn-blk-scene{active_cls}" id="blk-scene-pill-{s_idx}" '
            f'data-scene-index="{s_idx}" onclick="selectBlockingScene({s_idx})">'
            f"S{s_idx:02d} · {html_escape(scale_s)} ({blk.camera.focal_length_mm}mm)</button>"
        )

    cut_matrix_rows: List[str] = []
    for chk in master_blocking.cut_checks:
        cut_label = chk.cut_type.value if hasattr(chk.cut_type, "value") else str(chk.cut_type)
        s_from = chk.shot_scale_from.value if hasattr(chk.shot_scale_from, "value") else str(chk.shot_scale_from)
        s_to = chk.shot_scale_to.value if hasattr(chk.shot_scale_to, "value") else str(chk.shot_scale_to)
        axis_cls = "blk-badge-pass" if chk.axis_preserved else "blk-badge-fail"
        axis_txt = "180° PASS" if chk.axis_preserved else "180° CROSS"
        r30_cls = "blk-badge-pass" if chk.thirty_degree_rule_ok else "blk-badge-fail"
        r30_txt = f"30° PASS ({s_from}→{s_to})" if chk.thirty_degree_rule_ok else f"JUMP CUT ({s_from}→{s_to})"
        cct_cls = "blk-badge-pass" if chk.kelvin_continuity_ok else "blk-badge-fail"
        cct_txt = f"{chk.kelvin_delta_k:.0f}K PASS" if chk.kelvin_continuity_ok else f"{chk.kelvin_delta_k:.0f}K SHIFT"
        dir_cls = "blk-badge-pass" if chk.screen_direction_consistent else "blk-badge-warn"
        dir_txt = "LOCKED" if chk.screen_direction_consistent else "REVERSED"
        cut_matrix_rows.append(
            f'<tr class="blocking-cut-row" data-from-scene="{chk.from_scene_index}" data-to-scene="{chk.to_scene_index}">'
            f"<td><strong>Scene {chk.from_scene_index} → {chk.to_scene_index}</strong><br><span class=\"blk-subcell\">{html_escape(cut_label)}</span></td>"
            f"<td><code>{chk.camera_angle_delta_deg:.1f}°</code> <span class=\"blk-subcell\">({html_escape(chk.axis_side_from)}→{html_escape(chk.axis_side_to)})</span><br><span class=\"blk-badge {axis_cls}\">{axis_txt}</span></td>"
            f"<td><span class=\"blk-badge {r30_cls}\">{html_escape(r30_txt)}</span></td>"
            f"<td><span class=\"blk-badge {cct_cls}\">{cct_txt}</span></td>"
            f"<td><span class=\"blk-badge {dir_cls}\">{dir_txt}</span></td>"
            "</tr>"
        )
    if not cut_matrix_rows:
        cut_matrix_rows.append(
            '<tr><td colspan="5" style="color:var(--text-muted);text-align:center;">Single-scene master setup — no inter-scene editorial cuts.</td></tr>'
        )

    blk_180_cls = "blk-badge-pass" if master_blocking.all_180_axis_locked else "blk-badge-fail"
    blk_30_cls = "blk-badge-pass" if master_blocking.all_30_rule_passed else "blk-badge-fail"
    blk_cct_cls = "blk-badge-pass" if master_blocking.all_kelvin_continuous else "blk-badge-fail"
    blk_overall_cls = "blk-badge-pass" if master_blocking.continuity_passed else "blk-badge-fail"
    blk_overall_lbl = "PASS" if master_blocking.continuity_passed else "VIOLATION"

    first_blk = blocking_scenes_payload[0] if blocking_scenes_payload else {
        "scene_index": 1,
        "scene_title": "Scene 1",
        "shot_scale": "MS",
        "focal_length_mm": 35,
        "aim_azimuth_deg": 72.0,
        "fov_deg": 54.4,
        "eyeline_angle_deg": 15.0,
        "axis_side": "A_SIDE",
        "screen_direction": "left_to_right",
        "color_temp_kelvin": 5600,
        "blocking_notes": "180-degree axis anchored.",
    }

    blocking_scenes_json = re.sub(r"</(script)", r"<\/\1", json.dumps(blocking_scenes_payload), flags=re.IGNORECASE)

    # ------------------------------------------------------------------
    # PM-FEAT-024: Client Review & Pin Annotation Data Preparation
    # ------------------------------------------------------------------
    master_review = (
        getattr(bible, "master_client_review", None)
        or getattr(bible, "client_review", None)
        or getattr(bible, "review_manifest", None)
    )
    if master_review is None:
        master_review = synthesize_default_client_review(bible, fps=24)

    review_edl_escaped = _escape_js_template_literal(generate_resolve_marker_edl(master_review, fps=24))
    review_fcpxml_escaped = _escape_js_template_literal(generate_review_fcpxml_markers(master_review, fps=24))
    review_json_escaped = _escape_js_template_literal(generate_frameio_review_json(master_review))
    review_md_escaped = _escape_js_template_literal(generate_client_signoff_md(master_review))

    review_scenes_payload: List[Dict[str, Any]] = []
    for sr in master_review.scene_reviews:
        s_idx = int(sr.scene_index)
        st_s, en_s = scene_time_lookup.get(s_idx, ((s_idx - 1) * 5.0, s_idx * 5.0))
        status_s = sr.approval_status.value if hasattr(sr.approval_status, "value") else str(sr.approval_status)
        notes_list: List[Dict[str, Any]] = []
        for note in sr.annotations:
            role_s = note.reviewer_role.value if hasattr(note.reviewer_role, "value") else str(note.reviewer_role)
            color_s = note.marker_color.value if hasattr(note.marker_color, "value") else str(note.marker_color)
            notes_list.append({
                "note_id": str(note.note_id),
                "scene_index": int(note.scene_index),
                "timecode_smpte": str(note.timecode_smpte),
                "timecode_sec": float(note.timecode_sec),
                "frame_number": int(note.frame_number),
                "reviewer_role": role_s,
                "reviewer_name": str(note.reviewer_name),
                "marker_color": color_s,
                "comment": str(note.comment),
                "target_parameter": str(note.target_parameter),
                "resolved": bool(note.resolved),
                "blocking_gate": bool(note.blocking_gate),
                "x_norm": float(note.pin.x_norm) if note.pin else 0.5,
                "y_norm": float(note.pin.y_norm) if note.pin else 0.48,
                "compiled_edit_delta": str(note.compiled_edit_delta or ""),
            })
        review_scenes_payload.append({
            "scene_index": s_idx,
            "scene_title": str(sr.scene_title or f"Scene {s_idx}"),
            "start_sec": round(st_s, 3),
            "end_sec": round(en_s, 3),
            "revision": int(sr.revision),
            "approval_status": status_s,
            "signoff_by": str(sr.signoff_by),
            "annotations": notes_list,
        })

    review_state_payload = {
        "project_title": str(master_review.project_title),
        "revision": int(master_review.revision),
        "overall_status": master_review.overall_status.value if hasattr(master_review.overall_status, "value") else str(master_review.overall_status),
        "ready_for_live_render": bool(master_review.ready_for_live_render),
        "scene_reviews": review_scenes_payload,
    }
    review_state_json = re.sub(r"</(script)", r"<\/\1", json.dumps(review_state_payload), flags=re.IGNORECASE)

    review_scene_options = "".join([
        f'<option value="{sr["scene_index"]}">Scene {sr["scene_index"]:02d}: {html_escape(sr["scene_title"][:32])}</option>'
        for sr in review_scenes_payload
    ])

    # ------------------------------------------------------------------
    # CSS for Departmental Toolbar + Blocking HUD + Review HUD
    # ------------------------------------------------------------------
    v212_css = """
    /* v2.12.0 Departmental Toolbar Grouping (Header Crowding Fix) */
    .hud-header {
      flex-wrap: wrap;
      gap: 12px 20px;
      padding: 12px 24px;
    }
    .hud-actions {
      flex: 1 1 auto;
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      gap: 8px;
    }
    .dept-toolbar {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: flex-end;
      gap: 8px;
      position: relative;
    }
    .dept-group {
      position: relative;
      display: inline-flex;
      align-items: center;
    }
    .dept-pill-toggle {
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      color: var(--text-main);
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      font-weight: 700;
      padding: 6px 11px;
      border-radius: 999px;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: border-color 0.15s ease, background 0.15s ease, color 0.15s ease;
      white-space: nowrap;
    }
    .dept-pill-toggle:hover,
    .dept-pill-toggle:focus-visible,
    .dept-pill-toggle[aria-expanded="true"] {
      border-color: var(--cyan-telemetry);
      color: var(--cyan-telemetry);
      background: rgba(0, 240, 255, 0.1);
      outline: 2px solid var(--border-focus);
      outline-offset: 1px;
    }
    .dept-count {
      background: rgba(255, 255, 255, 0.08);
      color: var(--text-muted);
      font-size: 10px;
      padding: 1px 6px;
      border-radius: 999px;
    }
    .dept-pill-toggle[aria-expanded="true"] .dept-count {
      background: rgba(0, 240, 255, 0.2);
      color: var(--cyan-telemetry);
    }
    .dept-tray {
      position: absolute;
      top: calc(100% + 6px);
      left: 0;
      min-width: 220px;
      background: rgba(14, 16, 23, 0.98);
      border: 1px solid var(--border-focus);
      border-radius: 8px;
      padding: 8px;
      display: flex;
      flex-direction: column;
      gap: 6px;
      box-shadow: 0 16px 36px rgba(0, 0, 0, 0.85);
      z-index: 250;
    }
    .dept-tray[hidden] {
      display: none !important;
    }
    .dept-tray.dept-tray-right {
      left: auto;
      right: 0;
    }
    .dept-tray > button {
      width: 100%;
      justify-content: flex-start;
      white-space: nowrap;
    }
    .hud-hotkeys {
      font-size: 10px;
      max-width: 100%;
      flex-wrap: wrap;
      line-height: 1.4;
    }

    /* PM-FEAT-023 Blocking & Continuity HUD + PM-FEAT-024 Client Review HUD */
    .blocking-hud-modal, .review-hud-modal {
      position: fixed;
      inset: 0;
      background: rgba(7, 8, 11, 0.88);
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
      z-index: 10000;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 24px;
    }
    .blocking-modal-content, .review-modal-content {
      background: var(--bg-surface);
      border: 1px solid var(--border-focus);
      border-radius: 8px;
      max-width: 1120px;
      width: 100%;
      max-height: 90vh;
      overflow-y: auto;
      box-shadow: 0 24px 48px rgba(0, 0, 0, 0.8), 0 0 20px rgba(0, 240, 255, 0.15);
      display: flex;
      flex-direction: column;
    }
    .blocking-modal-header, .review-modal-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 16px 20px;
      border-bottom: 1px solid var(--border-subtle);
      background: var(--bg-card);
    }
    .blocking-title-wrap, .review-title-wrap {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .blocking-heading, .review-heading {
      font-family: 'Space Grotesk', sans-serif;
      font-size: 16px;
      font-weight: 700;
      letter-spacing: 0.05em;
      color: var(--text-main);
      margin: 0;
    }
    .blocking-subheading, .review-subheading {
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      color: var(--cyan-telemetry);
      display: block;
      margin-top: 2px;
    }
    .btn-blocking-close, .btn-review-close {
      background: transparent;
      border: 1px solid var(--border-subtle);
      color: var(--text-muted);
      border-radius: 4px;
      width: 32px;
      height: 32px;
      font-size: 16px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.15s ease;
    }
    .btn-blocking-close:hover, .btn-blocking-close:focus-visible,
    .btn-review-close:hover, .btn-review-close:focus-visible {
      border-color: var(--red-rec);
      color: var(--red-rec);
      outline: 2px solid var(--border-focus);
      outline-offset: 2px;
    }
    .blocking-modal-body, .review-modal-body {
      display: flex;
      flex-direction: column;
      gap: 16px;
      padding: 20px;
    }
    .blocking-toolbar, .review-toolbar {
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      border-radius: 6px;
      padding: 12px 14px;
    }
    .blocking-badge-group, .blocking-actions, .review-badge-group, .review-actions {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px;
    }
    .btn-blk-action, .btn-rev-action, .btn-blk-scene {
      background: #101420;
      border: 1px solid var(--border-subtle);
      color: var(--text-main);
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      padding: 6px 10px;
      border-radius: 4px;
      cursor: pointer;
      transition: all 0.15s ease;
    }
    .btn-blk-action:hover, .btn-rev-action:hover, .btn-blk-scene:hover,
    .btn-blk-action:focus-visible, .btn-rev-action:focus-visible, .btn-blk-scene:focus-visible {
      border-color: var(--cyan-telemetry);
      color: var(--cyan-telemetry);
      outline: 2px solid var(--border-focus);
      outline-offset: 1px;
    }
    .btn-blk-scene.active {
      background: rgba(0, 240, 255, 0.15);
      border-color: var(--cyan-telemetry);
      color: var(--cyan-telemetry);
      font-weight: 700;
    }
    .blocking-grid {
      display: grid;
      grid-template-columns: 1.25fr 1fr;
      gap: 16px;
    }
    .review-grid {
      display: grid;
      grid-template-columns: 1.15fr 1fr;
      gap: 16px;
    }
    @media (max-width: 920px) {
      .blocking-grid, .review-grid {
        grid-template-columns: 1fr;
      }
      .hud-actions {
        align-items: flex-start;
      }
      .dept-toolbar {
        justify-content: flex-start;
      }
    }
    .blocking-panel, .review-panel {
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      border-radius: 6px;
      padding: 12px;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .blocking-svg-wrap {
      background: #090B10;
      border: 1px solid var(--border-subtle);
      border-radius: 6px;
      overflow: hidden;
    }
    #blocking-floorplan-svg {
      width: 100%;
      height: auto;
      display: block;
    }
    .blocking-cam-node {
      cursor: pointer;
    }
    .blocking-cam-node:focus-visible {
      outline: 2px solid var(--cyan-telemetry);
    }
    .blocking-cam-node.active .blocking-fov-cone {
      fill-opacity: 0.34;
      stroke-width: 2.2;
      stroke-opacity: 1;
    }
    .blocking-cam-node.active .blocking-cam-halo {
      stroke-opacity: 0.9;
    }
    .blocking-kv-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 8px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
    }
    .blocking-kv-box {
      background: #090B10;
      border: 1px solid var(--border-subtle);
      border-radius: 4px;
      padding: 7px 9px;
    }
    .blocking-kv-lbl {
      display: block;
      font-size: 9px;
      color: var(--text-dim);
      margin-bottom: 2px;
    }
    .blocking-cut-table {
      width: 100%;
      border-collapse: collapse;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
    }
    .blocking-cut-table th {
      text-align: left;
      color: var(--text-muted);
      font-size: 10px;
      padding: 6px 8px;
      border-bottom: 1px solid var(--border-subtle);
    }
    .blocking-cut-table td {
      padding: 8px;
      border-bottom: 1px solid #161B29;
      vertical-align: top;
    }
    .blocking-cut-row.active-cut {
      background: rgba(0, 240, 255, 0.08);
    }
    .blk-subcell {
      font-size: 10px;
      color: var(--text-muted);
    }
    .blk-badge, .rev-status-badge {
      display: inline-block;
      font-family: 'JetBrains Mono', monospace;
      font-size: 10px;
      font-weight: 700;
      padding: 2px 7px;
      border-radius: 3px;
    }
    .blk-badge-pass, .rev-badge-approved {
      color: var(--green-rec);
      background: rgba(0, 255, 136, 0.12);
      border: 1px solid rgba(0, 255, 136, 0.4);
    }
    .blk-badge-warn, .rev-badge-pending {
      color: var(--amber-gold);
      background: rgba(255, 184, 0, 0.14);
      border: 1px solid rgba(255, 184, 0, 0.45);
    }
    .blk-badge-fail, .rev-badge-changes {
      color: var(--red-rec);
      background: rgba(255, 59, 48, 0.14);
      border: 1px solid rgba(255, 59, 48, 0.45);
    }

    /* PM-FEAT-024 Review Pin Canvas & Notes */
    .review-stage-wrap {
      position: relative;
      width: 100%;
      aspect-ratio: 16 / 9;
      background: #050609;
      border: 1px solid var(--border-subtle);
      border-radius: 6px;
      overflow: hidden;
      cursor: crosshair;
    }
    .review-stage-wrap:focus-visible {
      outline: 2px solid var(--cyan-telemetry);
      outline-offset: 2px;
    }
    .review-stage-media {
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      pointer-events: none;
    }
    .review-stage-media svg,
    .review-stage-media img {
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
    }
    .review-pin-layer {
      position: absolute;
      inset: 0;
      pointer-events: none;
      z-index: 4;
    }
    .review-pin-dot {
      position: absolute;
      transform: translate(-50%, -50%);
      width: 24px;
      height: 24px;
      border-radius: 50%;
      border: 2px solid #FFFFFF;
      color: #07080B;
      font-family: 'JetBrains Mono', monospace;
      font-size: 10px;
      font-weight: 700;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      pointer-events: auto;
      box-shadow: 0 2px 10px rgba(0, 0, 0, 0.75);
      transition: transform 0.12s ease;
    }
    .review-pin-dot:hover,
    .review-pin-dot:focus-visible,
    .review-pin-dot.active {
      transform: translate(-50%, -50%) scale(1.22);
      outline: 2px solid var(--cyan-telemetry);
      outline-offset: 2px;
    }
    .review-pin-draft {
      position: absolute;
      transform: translate(-50%, -50%);
      width: 26px;
      height: 26px;
      border-radius: 50%;
      border: 2px dashed var(--cyan-telemetry);
      background: rgba(0, 240, 255, 0.22);
      pointer-events: none;
      z-index: 5;
    }
    .review-pin-form {
      display: flex;
      flex-direction: column;
      gap: 8px;
      background: #090B10;
      border: 1px solid var(--border-subtle);
      border-radius: 6px;
      padding: 10px;
    }
    .review-form-row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }
    .review-input, .review-select {
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      color: var(--text-main);
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      padding: 6px 9px;
      border-radius: 4px;
    }
    .review-input {
      flex: 1 1 200px;
    }
    .review-input:focus-visible, .review-select:focus-visible {
      outline: 2px solid var(--border-focus);
      border-color: var(--cyan-telemetry);
    }
    .review-signoff-list {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .review-signoff-row {
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 8px;
      background: #090B10;
      border: 1px solid var(--border-subtle);
      border-radius: 4px;
      padding: 7px 10px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
    }
    .review-signoff-btns {
      display: inline-flex;
      gap: 4px;
      flex-wrap: wrap;
    }
    .btn-rev-status {
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      color: var(--text-muted);
      font-family: 'JetBrains Mono', monospace;
      font-size: 10px;
      padding: 3px 7px;
      border-radius: 3px;
      cursor: pointer;
    }
    .btn-rev-status:focus-visible {
      outline: 2px solid var(--border-focus);
    }
    .btn-rev-status.active-approved {
      border-color: var(--green-rec);
      color: var(--green-rec);
      background: rgba(0, 255, 136, 0.12);
      font-weight: 700;
    }
    .btn-rev-status.active-changes {
      border-color: var(--red-rec);
      color: var(--red-rec);
      background: rgba(255, 59, 48, 0.14);
      font-weight: 700;
    }
    .btn-rev-status.active-pending {
      border-color: var(--amber-gold);
      color: var(--amber-gold);
      background: rgba(255, 184, 0, 0.14);
      font-weight: 700;
    }
    .review-notes-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
      max-height: 310px;
      overflow-y: auto;
    }
    .review-note-card {
      background: #090B10;
      border: 1px solid var(--border-subtle);
      border-left: 3px solid var(--cyan-telemetry);
      border-radius: 4px;
      padding: 8px 10px;
      display: flex;
      flex-direction: column;
      gap: 5px;
      font-size: 12px;
    }
    .review-note-card.active-note {
      border-color: var(--cyan-telemetry);
      background: rgba(0, 240, 255, 0.08);
    }
    .review-note-top {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
      font-family: 'JetBrains Mono', monospace;
      font-size: 10px;
    }
    .btn-note-seek {
      background: rgba(0, 240, 255, 0.12);
      border: 1px solid rgba(0, 240, 255, 0.4);
      color: var(--cyan-telemetry);
      font-family: 'JetBrains Mono', monospace;
      font-size: 10px;
      font-weight: 700;
      padding: 2px 7px;
      border-radius: 3px;
      cursor: pointer;
    }
    .btn-note-seek:focus-visible {
      outline: 2px solid var(--border-focus);
    }
    .review-note-delta {
      font-family: 'JetBrains Mono', monospace;
      font-size: 10px;
      color: var(--text-muted);
      background: rgba(255, 255, 255, 0.03);
      padding: 4px 6px;
      border-radius: 3px;
    }
"""

    # ------------------------------------------------------------------
    # Modals HTML (PM-FEAT-023 + PM-FEAT-024)
    # ------------------------------------------------------------------
    cut_tbody = "".join(cut_matrix_rows)
    scene_pills_joined = "".join(blocking_scene_pills)
    axis_side_esc = html_escape(str(master_blocking.master_axis_side))
    dominant_dir_esc = html_escape(
        master_blocking.dominant_screen_direction.value
        if hasattr(master_blocking.dominant_screen_direction, "value")
        else str(master_blocking.dominant_screen_direction)
    )
    overall_rev_status = (
        master_review.overall_status.value
        if hasattr(master_review.overall_status, "value")
        else str(master_review.overall_status)
    )
    rev_overall_badge_cls = (
        "rev-badge-approved"
        if overall_rev_status in ("approved", "locked_final")
        else ("rev-badge-changes" if overall_rev_status == "changes_requested" else "rev-badge-pending")
    )
    rev_overall_label = (
        "APPROVED"
        if overall_rev_status in ("approved", "locked_final")
        else ("CHANGES REQUESTED" if overall_rev_status == "changes_requested" else "PENDING")
    )
    rev_gate_cls = "rev-badge-approved" if master_review.ready_for_live_render else "rev-badge-changes"
    rev_gate_label = "READY FOR LIVE RENDER" if master_review.ready_for_live_render else "BLOCKED PENDING SIGN-OFF"

    v212_modals_html = f"""
  <!-- 180-Degree Blocking & Continuity HUD (PM-FEAT-023) -->
  <div id="animatic-blocking-hud" class="blocking-hud-modal" role="dialog" aria-modal="true" aria-labelledby="blocking-hud-title" tabindex="-1" style="display:none;">
    <div class="blocking-modal-content">
      <div class="blocking-modal-header">
        <div class="blocking-title-wrap">
          <span style="font-size:20px;" aria-hidden="true">📐</span>
          <div>
            <h2 id="blocking-hud-title" class="blocking-heading">180° BLOCKING &amp; CONTINUITY FLOORPLAN HUD</h2>
            <span class="blocking-subheading">PM-FEAT-023 · OVERHEAD STAGE FLOORPLAN · 180° AXIS LOCK · 30° RULE · EYELINE &amp; KELVIN MATRIX</span>
          </div>
        </div>
        <button type="button" class="btn-blocking-close" onclick="toggleBlockingHUD()" aria-label="Close Blocking and Continuity HUD">✕</button>
      </div>

      <div class="blocking-modal-body">
        <div class="blocking-toolbar">
          <div class="blocking-badge-group">
            <span class="aicp-badge">AXIS: <strong>{axis_side_esc} ({master_blocking.master_axis_deg:.0f}°)</strong></span>
            <span class="aicp-badge">TRAVEL: <strong>{dominant_dir_esc}</strong></span>
            <span class="aicp-badge">180° LOCK: <span class="blk-badge {blk_180_cls}">{'PASS' if master_blocking.all_180_axis_locked else 'FAIL'}</span></span>
            <span class="aicp-badge">30° RULE: <span class="blk-badge {blk_30_cls}">{'PASS' if master_blocking.all_30_rule_passed else 'FAIL'}</span></span>
            <span class="aicp-badge">CCT: <span class="blk-badge {blk_cct_cls}">{'PASS' if master_blocking.all_kelvin_continuous else 'FAIL'}</span></span>
            <span class="aicp-badge">VERDICT: <span class="blk-badge {blk_overall_cls}">{blk_overall_lbl}</span></span>
          </div>
          <div class="blocking-actions">
            <button type="button" class="btn-blk-action" id="btn-download-continuity-csv" onclick="downloadContinuityCSV()" aria-label="Download Continuity Log CSV">
              ⤓ continuity_log.csv
            </button>
            <button type="button" class="btn-blk-action" id="btn-download-blocking-svg" onclick="downloadBlockingSVG()" aria-label="Download Blocking Floorplan SVG">
              ⤓ blocking_floorplan.svg
            </button>
            <button type="button" class="btn-blk-action" id="btn-download-continuity-json" onclick="downloadContinuityJSON()" aria-label="Download Continuity Manifest JSON">
              ⤓ continuity_manifest.json
            </button>
          </div>
        </div>

        <div class="blocking-grid">
          <div class="blocking-panel">
            <div class="drone-panel-header">
              <span>TOP-DOWN 2D STAGE FLOORPLAN (SYNCED WITH SMPTE SCRUBBER)</span>
              <span class="badge-canvas-telemetry" id="blocking-active-scene-badge">SCENE {int(first_blk['scene_index']):02d}</span>
            </div>
            <div class="blocking-scene-pills" style="display:flex;flex-wrap:wrap;gap:6px;" role="navigation" aria-label="Blocking Scene Selector">
              {scene_pills_joined}
            </div>
            <div class="blocking-svg-wrap">
              {interactive_blocking_svg}
            </div>
            <div class="blocking-kv-grid">
              <div class="blocking-kv-box">
                <span class="blocking-kv-lbl">ACTIVE CAMERA / LENS</span>
                <strong id="blk-kv-cam">{html_escape(str(first_blk['shot_scale']))} · {int(first_blk['focal_length_mm'])}mm ({float(first_blk['fov_deg']):.1f}° FOV)</strong>
              </div>
              <div class="blocking-kv-box">
                <span class="blocking-kv-lbl">AIM AZIMUTH / EYELINE</span>
                <strong id="blk-kv-aim">{float(first_blk['aim_azimuth_deg']):.1f}° / {float(first_blk['eyeline_angle_deg']):+.1f}°</strong>
              </div>
              <div class="blocking-kv-box">
                <span class="blocking-kv-lbl">STAGE KELVIN / AXIS</span>
                <strong id="blk-kv-kelvin">{int(first_blk['color_temp_kelvin'])}K · {html_escape(str(first_blk['axis_side']))}</strong>
              </div>
            </div>
            <div id="blk-active-notes" class="blk-subcell">{html_escape(str(first_blk['blocking_notes']))}</div>
          </div>

          <div class="blocking-panel">
            <div class="drone-panel-header">
              <span>INTER-SCENE CUT TRANSITION MATRIX</span>
              <span class="badge-canvas-telemetry">{len(master_blocking.cut_checks)} CUT CHECK(S)</span>
            </div>
            <div style="overflow-x:auto;">
              <table class="blocking-cut-table" aria-label="Inter-Scene Cut Continuity Matrix">
                <thead>
                  <tr>
                    <th scope="col">Transition</th>
                    <th scope="col">Axis Δ°</th>
                    <th scope="col">30° Rule</th>
                    <th scope="col">CCT ΔK</th>
                    <th scope="col">Screen Dir</th>
                  </tr>
                </thead>
                <tbody>
                  {cut_tbody}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Client Review & Pin Annotation HUD (PM-FEAT-024) -->
  <div id="animatic-review-hud" class="review-hud-modal" role="dialog" aria-modal="true" aria-labelledby="review-hud-title" tabindex="-1" style="display:none;">
    <div class="review-modal-content">
      <div class="review-modal-header">
        <div class="review-title-wrap">
          <span style="font-size:20px;" aria-hidden="true">📝</span>
          <div>
            <h2 id="review-hud-title" class="review-heading">CLIENT REVIEW &amp; FRAME PIN ANNOTATION HUD</h2>
            <span class="review-subheading">PM-FEAT-024 · SMPTE FRAME PINS · RESOLVE EDL &amp; FCPXML MARKERS · FRAME.IO JSON · SIGNOFF GATE</span>
          </div>
        </div>
        <button type="button" class="btn-review-close" onclick="toggleReviewHUD()" aria-label="Close Client Review HUD">✕</button>
      </div>

      <div class="review-modal-body">
        <div class="review-toolbar">
          <div class="review-badge-group">
            <span class="aicp-badge">REV: <strong>v{int(master_review.revision)}</strong></span>
            <span class="aicp-badge">STATUS: <span id="review-overall-badge" class="rev-status-badge {rev_overall_badge_cls}">{rev_overall_label}</span></span>
            <span class="aicp-badge">LIVE GATE: <span id="review-gate-badge" class="rev-status-badge {rev_gate_cls}">{rev_gate_label}</span></span>
            <span class="aicp-badge">NOTES: <strong id="review-counts-label">{int(master_review.total_notes_count)} TOTAL · {int(master_review.open_notes_count)} OPEN</strong></span>
          </div>
          <div class="review-actions">
            <button type="button" class="btn-rev-action" id="btn-download-review-edl" onclick="downloadReviewEDL()" aria-label="Download Resolve Locator EDL">
              ⤓ review_markers.edl
            </button>
            <button type="button" class="btn-rev-action" id="btn-download-review-fcpxml" onclick="downloadReviewFCPXML()" aria-label="Download FCPXML Markers">
              ⤓ review_markers.fcpxml
            </button>
            <button type="button" class="btn-rev-action" id="btn-download-review-json" onclick="downloadReviewJSON()" aria-label="Download Frame.io Review JSON">
              ⤓ review_notes_frameio.json
            </button>
            <button type="button" class="btn-rev-action" id="btn-download-review-md" onclick="downloadReviewMD()" aria-label="Download Client Signoff Markdown Report">
              ⤓ client_signoff_report.md
            </button>
          </div>
        </div>

        <div class="review-grid">
          <div class="review-panel">
            <div class="drone-panel-header">
              <span>INTERACTIVE FRAME PIN CANVAS (CLICK TO DROP PIN @ LIVE TC)</span>
              <span class="badge-canvas-telemetry" id="review-live-tc">00:00:00:00</span>
            </div>
            <div class="review-form-row">
              <label for="review-scene-select" class="qc-label">ACTIVE PLATE:</label>
              <select id="review-scene-select" class="review-select" onchange="selectReviewScene(this.value)" aria-label="Select Scene for Pin Review">
                {review_scene_options}
              </select>
              <span id="review-pin-coords-badge" class="blk-subcell">Click stage to place pin · Target: (50%, 48%)</span>
            </div>

            <div id="review-pin-stage" class="review-stage-wrap" tabindex="0" role="application" aria-label="Interactive Frame Pin Stage. Click or press Enter or Space to drop a frame pin at the current SMPTE timecode. Use Arrow keys to nudge pin coordinates." onclick="onReviewStageClick(event)" onkeydown="onReviewStageKeyDown(event)">
              <div id="review-stage-media" class="review-stage-media" aria-hidden="true"></div>
              <div id="review-pin-layer" class="review-pin-layer"></div>
              <div id="review-pin-draft" class="review-pin-draft" style="left:50%;top:48%;display:none;" aria-hidden="true"></div>
            </div>

            <form class="review-pin-form" onsubmit="submitReviewPinNote(event)">
              <div class="review-form-row">
                <select id="review-role-select" class="review-select" aria-label="Reviewer Role">
                  <option value="client_brand">Client Brand</option>
                  <option value="agency_creative">Agency Creative</option>
                  <option value="director" selected>Director</option>
                  <option value="post_producer">Post Producer</option>
                  <option value="vfx_supervisor">VFX Supervisor</option>
                </select>
                <select id="review-color-select" class="review-select" aria-label="Marker Color Tag">
                  <option value="CYAN">CYAN</option>
                  <option value="AMBER">AMBER</option>
                  <option value="RED">RED</option>
                  <option value="GREEN">GREEN</option>
                  <option value="MAGENTA">MAGENTA</option>
                </select>
                <select id="review-param-select" class="review-select" aria-label="Target Parameter">
                  <option value="lighting">Lighting / Grade</option>
                  <option value="camera">Camera / Framing</option>
                  <option value="pacing">Pacing / Timing</option>
                  <option value="audio">Audio / Foley</option>
                  <option value="visual">Visual Continuity</option>
                </select>
                <label class="reframe-ghost-label" for="review-blocking-chk">
                  <input type="checkbox" id="review-blocking-chk" class="reframe-ghost-chk">
                  <span>Blocking Gate</span>
                </label>
              </div>
              <div class="review-form-row">
                <input type="text" id="review-note-input" class="review-input" placeholder="Enter frame-accurate review note (stamped @ live SMPTE TC)..." aria-label="Review annotation comment">
                <button type="submit" class="btn-rev-action" id="btn-submit-review-pin">📌 Drop Pin Note</button>
              </div>
            </form>
          </div>

          <div class="review-panel">
            <div class="drone-panel-header">
              <span>SCENE APPROVAL GATES &amp; TIMESTAMPED NOTES</span>
              <span class="badge-canvas-telemetry">CLICK TIMECODE TO SEEK</span>
            </div>
            <div id="review-signoff-list" class="review-signoff-list" role="region" aria-label="Scene Approval Status Controls"></div>
            <div id="review-notes-list" class="review-notes-list" role="region" aria-label="Timestamped Review Notes"></div>
          </div>
        </div>
      </div>
    </div>
  </div>"""

    # ------------------------------------------------------------------
    # JavaScript Controllers (Departmental Toolbar + PM-FEAT-023 + PM-FEAT-024)
    # ------------------------------------------------------------------
    v212_js = f"""
    // Departmental Toolbar Grouping Controller (v2.12.0)
    let openDeptGroupId = null;

    function closeAllDeptGroups(restoreFocus) {{
      document.querySelectorAll('.dept-pill-toggle').forEach((btn) => {{
        btn.setAttribute('aria-expanded', 'false');
      }});
      document.querySelectorAll('.dept-tray').forEach((tray) => {{
        tray.setAttribute('hidden', '');
      }});
      if (restoreFocus && openDeptGroupId) {{
        const prevBtn = document.getElementById('dept-toggle-' + openDeptGroupId);
        if (prevBtn) prevBtn.focus();
      }}
      openDeptGroupId = null;
    }}

    function toggleDeptGroup(deptId) {{
      const btn = document.getElementById('dept-toggle-' + deptId);
      const tray = document.getElementById('dept-tray-' + deptId);
      if (!btn || !tray) return;
      const willOpen = tray.hasAttribute('hidden');
      closeAllDeptGroups(false);
      if (willOpen) {{
        tray.removeAttribute('hidden');
        btn.setAttribute('aria-expanded', 'true');
        openDeptGroupId = deptId;
      }}
    }}

    document.addEventListener('click', (e) => {{
      if (openDeptGroupId && !e.target.closest('.dept-group')) {{
        closeAllDeptGroups(false);
      }}
    }});

    function _isEditableElement(el) {{
      if (!el) return false;
      const tag = el.tagName ? el.tagName.toLowerCase() : '';
      return Boolean(el.isContentEditable || tag === 'input' || tag === 'textarea' || tag === 'select');
    }}

    function _getOpenModalDialog() {{
      const dialogs = Array.from(document.querySelectorAll('[role="dialog"][aria-modal="true"]')).filter((dlg) => {{
        if (dlg.hasAttribute('hidden') || dlg.style.display === 'none') return false;
        return window.getComputedStyle(dlg).display !== 'none';
      }});
      return dialogs.length ? dialogs[dialogs.length - 1] : null;
    }}

    function _getFocusableInDialog(dlg) {{
      if (!dlg) return [];
      const selector = 'a[href], button:not([disabled]), input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';
      return Array.from(dlg.querySelectorAll(selector)).filter((el) => {{
        if (el.hasAttribute('hidden') || el.closest('[hidden]')) return false;
        const style = window.getComputedStyle(el);
        return style.display !== 'none' && style.visibility !== 'hidden';
      }});
    }}

    function _handleModalTabFocusTrap(e) {{
      if (!e || e.key !== 'Tab') return false;
      const activeDialog = _getOpenModalDialog();
      if (!activeDialog) return false;
      const focusables = _getFocusableInDialog(activeDialog);
      if (!focusables.length) {{
        e.preventDefault();
        return true;
      }}
      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      const curr = document.activeElement;
      if (!activeDialog.contains(curr)) {{
        e.preventDefault();
        (e.shiftKey ? last : first).focus();
      }} else if (e.shiftKey && curr === first) {{
        e.preventDefault();
        last.focus();
      }} else if (!e.shiftKey && curr === last) {{
        e.preventDefault();
        first.focus();
      }}
      return true;
    }}

    // PM-FEAT-023: 180-Degree Blocking & Continuity HUD Controller
    const BLOCKING_SCENES = {blocking_scenes_json};
    let isBlockingHUDOpen = false;
    let lastBlockingOpener = null;
    let activeBlockingSceneIdx = BLOCKING_SCENES.length ? BLOCKING_SCENES[0].scene_index : 1;
    let _lastBlockingSceneIdx = null;

    function toggleBlockingHUD() {{
      isBlockingHUDOpen = !isBlockingHUDOpen;
      const modal = document.getElementById('animatic-blocking-hud');
      const btn = document.getElementById('btn-blocking-animatic');
      if (modal) modal.style.display = isBlockingHUDOpen ? 'flex' : 'none';
      if (btn) {{
        btn.classList.toggle('active', isBlockingHUDOpen);
        btn.setAttribute('aria-expanded', isBlockingHUDOpen ? 'true' : 'false');
      }}
      if (isBlockingHUDOpen) {{
        lastBlockingOpener = document.activeElement;
        _lastBlockingSceneIdx = null;
        updateBlockingFromTimeline(currentFrame / (FPS || 24));
        const closeBtn = modal ? modal.querySelector('.btn-blocking-close') : null;
        if (closeBtn) closeBtn.focus();
        showToast('📐 180° Blocking & Continuity HUD: ACTIVE [W]');
      }} else {{
        if (lastBlockingOpener && typeof lastBlockingOpener.focus === 'function') {{
          lastBlockingOpener.focus();
        }}
      }}
    }}

    function highlightBlockingScene(sIdx) {{
      activeBlockingSceneIdx = sIdx;
      _lastBlockingSceneIdx = sIdx;
      const spec = BLOCKING_SCENES.find((s) => s.scene_index === sIdx) || BLOCKING_SCENES[0];
      if (!spec) return;
      document.querySelectorAll('.blocking-cam-node').forEach((node) => {{
        const nIdx = parseInt(node.getAttribute('data-scene-index') || '0', 10);
        node.classList.toggle('active', nIdx === spec.scene_index);
      }});
      document.querySelectorAll('.btn-blk-scene').forEach((pill) => {{
        const pIdx = parseInt(pill.getAttribute('data-scene-index') || '0', 10);
        pill.classList.toggle('active', pIdx === spec.scene_index);
      }});
      document.querySelectorAll('.blocking-cut-row').forEach((row) => {{
        const fromIdx = parseInt(row.getAttribute('data-from-scene') || '0', 10);
        const toIdx = parseInt(row.getAttribute('data-to-scene') || '0', 10);
        row.classList.toggle('active-cut', fromIdx === spec.scene_index || toIdx === spec.scene_index);
      }});
      const badge = document.getElementById('blocking-active-scene-badge');
      if (badge) badge.textContent = 'SCENE ' + String(spec.scene_index).padStart(2, '0');
      const kvCam = document.getElementById('blk-kv-cam');
      if (kvCam) kvCam.textContent = spec.shot_scale + ' · ' + spec.focal_length_mm + 'mm (' + spec.fov_deg.toFixed(1) + '° FOV)';
      const kvAim = document.getElementById('blk-kv-aim');
      if (kvAim) kvAim.textContent = spec.aim_azimuth_deg.toFixed(1) + '° / ' + (spec.eyeline_angle_deg >= 0 ? '+' : '') + spec.eyeline_angle_deg.toFixed(1) + '°';
      const kvKel = document.getElementById('blk-kv-kelvin');
      if (kvKel) kvKel.textContent = spec.color_temp_kelvin + 'K · ' + spec.axis_side;
      const notesEl = document.getElementById('blk-active-notes');
      if (notesEl) notesEl.textContent = spec.blocking_notes;
    }}

    function updateBlockingFromTimeline(tSec) {{
      if (!BLOCKING_SCENES.length) return;
      const blockingHud = document.getElementById('animatic-blocking-hud');
      const isHidden = !blockingHud || blockingHud.hidden || blockingHud.style.display === 'none';
      let match = BLOCKING_SCENES.find((s) => tSec >= s.start_sec && tSec < s.end_sec);
      if (!match) match = BLOCKING_SCENES[BLOCKING_SCENES.length - 1];
      if (isHidden || !match || match.scene_index === _lastBlockingSceneIdx) return;
      _lastBlockingSceneIdx = match.scene_index;
      highlightBlockingScene(match.scene_index);
    }}

    function selectBlockingScene(sIdx) {{
      const spec = BLOCKING_SCENES.find((s) => s.scene_index === sIdx);
      if (!spec) return;
      highlightBlockingScene(sIdx);
      jumpToScene(sIdx, spec.start_sec);
      showToast('📐 Blocking Focus: Scene ' + String(sIdx).padStart(2, '0') + ' (' + spec.shot_scale + ')');
    }}

    function initBlockingHUD() {{
      highlightBlockingScene(activeBlockingSceneIdx);
    }}

    function _triggerBlobDownload(content, mimeType, filename, toastMsg) {{
      const blob = new Blob([content], {{ type: mimeType }});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      showToast(toastMsg);
    }}

    function downloadContinuityCSV() {{
      _triggerBlobDownload(`{blocking_csv_escaped}`, 'text/csv;charset=utf-8;', 'continuity_log.csv', 'Downloaded Continuity Log (continuity_log.csv)');
    }}

    function downloadBlockingSVG() {{
      _triggerBlobDownload(`{blocking_svg_escaped}`, 'image/svg+xml;charset=utf-8;', 'blocking_floorplan.svg', 'Downloaded Blocking Floorplan (blocking_floorplan.svg)');
    }}

    function downloadContinuityJSON() {{
      _triggerBlobDownload(`{blocking_json_escaped}`, 'application/json;charset=utf-8;', 'continuity_manifest.json', 'Downloaded Continuity Manifest (continuity_manifest.json)');
    }}

    // PM-FEAT-024: Client Review & Pin Annotation HUD Controller
    const REVIEW_STATE = {review_state_json};
    const REVIEW_INITIAL_EDL = `{review_edl_escaped}`;
    const REVIEW_INITIAL_FCPXML = `{review_fcpxml_escaped}`;
    const REVIEW_INITIAL_JSON = `{review_json_escaped}`;
    const REVIEW_INITIAL_MD = `{review_md_escaped}`;
    let isReviewHUDOpen = false;
    let lastReviewOpener = null;
    let activeReviewSceneIdx = REVIEW_STATE.scene_reviews.length ? REVIEW_STATE.scene_reviews[0].scene_index : 1;
    let activeReviewNoteId = null;
    let draftPinX = 0.50;
    let draftPinY = 0.48;
    let reviewDirty = false;

    const MARKER_HEX_MAP = {{
      CYAN: '#00F0FF',
      AMBER: '#FFB800',
      RED: '#FF3B30',
      GREEN: '#00FF88',
      MAGENTA: '#FF4FD8'
    }};

    function toggleReviewHUD() {{
      isReviewHUDOpen = !isReviewHUDOpen;
      const modal = document.getElementById('animatic-review-hud');
      const btn = document.getElementById('btn-review-animatic');
      if (modal) modal.style.display = isReviewHUDOpen ? 'flex' : 'none';
      if (btn) {{
        btn.classList.toggle('active', isReviewHUDOpen);
        btn.setAttribute('aria-expanded', isReviewHUDOpen ? 'true' : 'false');
      }}
      if (isReviewHUDOpen) {{
        lastReviewOpener = document.activeElement;
        updateReviewFromTimeline(currentFrame / (FPS || 24));
        renderReviewHUD();
        const closeBtn = modal ? modal.querySelector('.btn-review-close') : null;
        if (closeBtn) closeBtn.focus();
        showToast('📝 Client Review & Pin Annotation HUD: ACTIVE [N]');
      }} else {{
        if (lastReviewOpener && typeof lastReviewOpener.focus === 'function') {{
          lastReviewOpener.focus();
        }}
      }}
    }}

    function _recalcReviewSummary() {{
      let total = 0;
      let open = 0;
      let blocking = 0;
      let anyChanges = false;
      let anyPending = false;
      REVIEW_STATE.scene_reviews.forEach((sr) => {{
        if (sr.approval_status === 'changes_requested') anyChanges = true;
        if (sr.approval_status === 'pending_review') anyPending = true;
        sr.annotations.forEach((n) => {{
          total += 1;
          if (!n.resolved) {{
            open += 1;
            if (n.blocking_gate) blocking += 1;
          }}
        }});
      }});
      REVIEW_STATE.overall_status = anyChanges ? 'changes_requested' : (anyPending ? 'pending_review' : 'approved');
      REVIEW_STATE.ready_for_live_render = (!anyChanges) && (blocking === 0);

      const overallEl = document.getElementById('review-overall-badge');
      if (overallEl) {{
        overallEl.className = 'rev-status-badge ' + (
          REVIEW_STATE.overall_status === 'approved' ? 'rev-badge-approved' :
          (REVIEW_STATE.overall_status === 'changes_requested' ? 'rev-badge-changes' : 'rev-badge-pending')
        );
        overallEl.textContent = (
          REVIEW_STATE.overall_status === 'approved' ? 'APPROVED' :
          (REVIEW_STATE.overall_status === 'changes_requested' ? 'CHANGES REQUESTED' : 'PENDING')
        );
      }}
      const gateEl = document.getElementById('review-gate-badge');
      if (gateEl) {{
        gateEl.className = 'rev-status-badge ' + (REVIEW_STATE.ready_for_live_render ? 'rev-badge-approved' : 'rev-badge-changes');
        gateEl.textContent = REVIEW_STATE.ready_for_live_render ? 'READY FOR LIVE RENDER' : 'BLOCKED PENDING SIGN-OFF';
      }}
      const cntEl = document.getElementById('review-counts-label');
      if (cntEl) cntEl.textContent = total + ' TOTAL · ' + open + ' OPEN';
    }}

    function _renderReviewStageMedia(sIdx) {{
      const mediaBox = document.getElementById('review-stage-media');
      if (!mediaBox) return;
      mediaBox.innerHTML = '';
      const frameEl = document.querySelector('#scene-' + sIdx + ' .scene-visual-frame');
      if (frameEl) {{
        const plate = frameEl.querySelector('svg:not(.scene-reframe-overlay), img, .svg-placeholder');
        if (plate) {{
          mediaBox.appendChild(plate.cloneNode(true));
          return;
        }}
      }}
      const fallback = document.createElement('div');
      fallback.className = 'svg-placeholder';
      fallback.textContent = 'Scene ' + String(sIdx).padStart(2, '0') + ' Review Plate';
      mediaBox.appendChild(fallback);
    }}

    function _renderReviewPins() {{
      const layer = document.getElementById('review-pin-layer');
      if (!layer) return;
      layer.innerHTML = '';
      const sr = REVIEW_STATE.scene_reviews.find((s) => s.scene_index === activeReviewSceneIdx);
      if (!sr) return;
      sr.annotations.forEach((note, idx) => {{
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'review-pin-dot' + (note.note_id === activeReviewNoteId ? ' active' : '');
        btn.style.left = ((note.x_norm || 0.5) * 100).toFixed(1) + '%';
        btn.style.top = ((note.y_norm || 0.48) * 100).toFixed(1) + '%';
        btn.style.background = MARKER_HEX_MAP[note.marker_color] || '#00F0FF';
        btn.textContent = String(idx + 1);
        btn.setAttribute('aria-label', 'Pin ' + (idx + 1) + ' at ' + note.timecode_smpte + ': ' + note.comment);
        btn.onclick = (ev) => {{
          ev.stopPropagation();
          jumpToReviewNote(note.note_id);
        }};
        layer.appendChild(btn);
      }});
    }}

    function _renderReviewSignoffs() {{
      const box = document.getElementById('review-signoff-list');
      if (!box) return;
      box.innerHTML = '';
      REVIEW_STATE.scene_reviews.forEach((sr) => {{
        const row = document.createElement('div');
        row.className = 'review-signoff-row';
        const stLabel = sr.approval_status === 'approved' ? 'APPROVED' : (sr.approval_status === 'changes_requested' ? 'CHANGES REQUESTED' : 'PENDING');
        const stCls = sr.approval_status === 'approved' ? 'rev-badge-approved' : (sr.approval_status === 'changes_requested' ? 'rev-badge-changes' : 'rev-badge-pending');

        const left = document.createElement('div');
        const titleStrong = document.createElement('strong');
        titleStrong.textContent = 'S' + String(sr.scene_index).padStart(2, '0') + ' ';
        const badgeSpan = document.createElement('span');
        badgeSpan.className = 'rev-status-badge ' + stCls;
        badgeSpan.textContent = stLabel;
        left.appendChild(titleStrong);
        left.appendChild(badgeSpan);

        const btns = document.createElement('div');
        btns.className = 'review-signoff-btns';
        [
          ['approved', 'APPROVED', 'active-approved'],
          ['changes_requested', 'CHANGES REQUESTED', 'active-changes'],
          ['pending_review', 'PENDING', 'active-pending']
        ].forEach(([val, lbl, activeCls]) => {{
          const b = document.createElement('button');
          b.type = 'button';
          b.className = 'btn-rev-status' + (sr.approval_status === val ? ' ' + activeCls : '');
          b.textContent = lbl;
          b.onclick = () => setSceneApprovalStatus(sr.scene_index, val);
          btns.appendChild(b);
        }});

        row.appendChild(left);
        row.appendChild(btns);
        box.appendChild(row);
      }});
    }}

    function _renderReviewNotesList() {{
      const list = document.getElementById('review-notes-list');
      if (!list) return;
      list.innerHTML = '';
      REVIEW_STATE.scene_reviews.forEach((sr) => {{
        sr.annotations.forEach((note) => {{
          const card = document.createElement('div');
          card.className = 'review-note-card' + (note.note_id === activeReviewNoteId ? ' active-note' : '');
          card.style.borderLeftColor = MARKER_HEX_MAP[note.marker_color] || '#00F0FF';

          const top = document.createElement('div');
          top.className = 'review-note-top';

          const leftMeta = document.createElement('div');
          leftMeta.style.display = 'flex';
          leftMeta.style.alignItems = 'center';
          leftMeta.style.gap = '6px';
          const seekBtn = document.createElement('button');
          seekBtn.type = 'button';
          seekBtn.className = 'btn-note-seek';
          seekBtn.textContent = 'S' + String(note.scene_index).padStart(2, '0') + ' @ ' + note.timecode_smpte;
          seekBtn.onclick = () => jumpToReviewNote(note.note_id);
          const roleSpan = document.createElement('span');
          roleSpan.textContent = note.note_id + ' · ' + note.reviewer_role + ' · (' + Math.round((note.x_norm || 0.5) * 100) + '%, ' + Math.round((note.y_norm || 0.48) * 100) + '%)';
          leftMeta.appendChild(seekBtn);
          leftMeta.appendChild(roleSpan);

          const resBtn = document.createElement('button');
          resBtn.type = 'button';
          resBtn.className = 'btn-rev-status ' + (note.resolved ? 'active-approved' : 'active-changes');
          resBtn.textContent = note.resolved ? 'RESOLVED' : (note.blocking_gate ? 'BLOCKING' : 'OPEN');
          resBtn.onclick = () => toggleReviewNoteResolved(note.note_id);

          top.appendChild(leftMeta);
          top.appendChild(resBtn);

          const body = document.createElement('div');
          body.textContent = note.comment;

          const delta = document.createElement('div');
          delta.className = 'review-note-delta';
          delta.textContent = note.compiled_edit_delta || ('Delta [' + note.target_parameter + ']: ' + note.comment);

          card.appendChild(top);
          card.appendChild(body);
          card.appendChild(delta);
          list.appendChild(card);
        }});
      }});
    }}

    function renderReviewHUD() {{
      const sel = document.getElementById('review-scene-select');
      if (sel && String(sel.value) !== String(activeReviewSceneIdx)) {{
        sel.value = String(activeReviewSceneIdx);
      }}
      const tcEl = document.getElementById('review-live-tc');
      if (tcEl) tcEl.textContent = formatSMPTE(currentFrame);
      _recalcReviewSummary();
      _renderReviewStageMedia(activeReviewSceneIdx);
      _renderReviewPins();
      _renderReviewSignoffs();
      _renderReviewNotesList();
    }}

    function selectReviewScene(sVal) {{
      const sIdx = parseInt(sVal, 10) || 1;
      activeReviewSceneIdx = sIdx;
      const sr = REVIEW_STATE.scene_reviews.find((s) => s.scene_index === sIdx);
      if (sr) jumpToScene(sIdx, sr.start_sec);
      renderReviewHUD();
    }}

    function updateReviewFromTimeline(tSec) {{
      const tcEl = document.getElementById('review-live-tc');
      if (tcEl) tcEl.textContent = formatSMPTE(currentFrame);
      if (!REVIEW_STATE.scene_reviews.length) return;
      let match = REVIEW_STATE.scene_reviews.find((s) => tSec >= s.start_sec && tSec < s.end_sec);
      if (!match) match = REVIEW_STATE.scene_reviews[REVIEW_STATE.scene_reviews.length - 1];
      if (match && match.scene_index !== activeReviewSceneIdx) {{
        activeReviewSceneIdx = match.scene_index;
        if (isReviewHUDOpen) renderReviewHUD();
      }}
    }}

    function _syncReviewDraftPin(focusInput, announceToast) {{
      const draftEl = document.getElementById('review-pin-draft');
      if (draftEl) {{
        draftEl.style.left = (draftPinX * 100).toFixed(1) + '%';
        draftEl.style.top = (draftPinY * 100).toFixed(1) + '%';
        draftEl.style.display = 'block';
      }}
      const coordsEl = document.getElementById('review-pin-coords-badge');
      const liveTc = formatSMPTE(currentFrame);
      if (coordsEl) {{
        coordsEl.textContent = 'Pin Target: (' + Math.round(draftPinX * 100) + '%, ' + Math.round(draftPinY * 100) + '%) @ ' + liveTc;
      }}
      if (focusInput) {{
        const inputEl = document.getElementById('review-note-input');
        if (inputEl) inputEl.focus();
      }}
      if (announceToast) {{
        showToast('📌 Pin positioned at (' + Math.round(draftPinX * 100) + '%, ' + Math.round(draftPinY * 100) + '%) @ ' + liveTc);
      }}
    }}

    function onReviewStageClick(event) {{
      const stage = document.getElementById('review-pin-stage');
      if (!stage) return;
      const rect = stage.getBoundingClientRect();
      if (!rect.width || !rect.height) return;
      const xNorm = Math.max(0.02, Math.min(0.98, (event.clientX - rect.left) / rect.width));
      const yNorm = Math.max(0.02, Math.min(0.98, (event.clientY - rect.top) / rect.height));
      draftPinX = Number(xNorm.toFixed(3));
      draftPinY = Number(yNorm.toFixed(3));
      _syncReviewDraftPin(true, true);
    }}

    function onReviewStageKeyDown(event) {{
      if (event.target && event.target !== event.currentTarget && event.target.closest && event.target.closest('.review-pin-dot')) return;
      const key = event.key;
      const isArrow = key === 'ArrowLeft' || key === 'ArrowRight' || key === 'ArrowUp' || key === 'ArrowDown';
      const isActivate = key === 'Enter' || key === ' ' || event.code === 'Space';
      if (!isArrow && !isActivate) return;
      event.preventDefault();
      event.stopPropagation();

      const draftEl = document.getElementById('review-pin-draft');
      const isDraftVisible = Boolean(draftEl && draftEl.style.display !== 'none');
      if (!isDraftVisible) {{
        draftPinX = 0.50;
        draftPinY = 0.50;
      }}

      if (key === 'ArrowLeft') {{
        draftPinX = Math.max(0.02, Math.min(0.98, Number((draftPinX - 0.02).toFixed(3))));
        _syncReviewDraftPin(false, false);
      }} else if (key === 'ArrowRight') {{
        draftPinX = Math.max(0.02, Math.min(0.98, Number((draftPinX + 0.02).toFixed(3))));
        _syncReviewDraftPin(false, false);
      }} else if (key === 'ArrowUp') {{
        draftPinY = Math.max(0.02, Math.min(0.98, Number((draftPinY - 0.02).toFixed(3))));
        _syncReviewDraftPin(false, false);
      }} else if (key === 'ArrowDown') {{
        draftPinY = Math.max(0.02, Math.min(0.98, Number((draftPinY + 0.02).toFixed(3))));
        _syncReviewDraftPin(false, false);
      }} else if (isActivate) {{
        _syncReviewDraftPin(true, true);
      }}
    }}

    function submitReviewPinNote(event) {{
      event.preventDefault();
      const inputEl = document.getElementById('review-note-input');
      const comment = inputEl ? inputEl.value.trim() : '';
      if (!comment) {{
        showToast('Enter a review note comment before dropping the pin.');
        if (inputEl) inputEl.focus();
        return;
      }}
      const sr = REVIEW_STATE.scene_reviews.find((s) => s.scene_index === activeReviewSceneIdx) || REVIEW_STATE.scene_reviews[0];
      if (!sr) return;
      const roleVal = (document.getElementById('review-role-select') || {{ value: 'director' }}).value;
      const colorVal = (document.getElementById('review-color-select') || {{ value: 'CYAN' }}).value;
      const paramVal = (document.getElementById('review-param-select') || {{ value: 'lighting' }}).value;
      const isBlocking = Boolean((document.getElementById('review-blocking-chk') || {{ checked: false }}).checked);
      const tcStr = formatSMPTE(currentFrame);
      const tSec = Number((currentFrame / (FPS || 24)).toFixed(2));
      const nextNum = sr.annotations.length + 1;
      const noteId = 'REV-S' + String(sr.scene_index).padStart(2, '0') + '-' + String(nextNum).padStart(2, '0');
      const deltaStr = 'Review Edit Delta [Scene ' + sr.scene_index + " '" + sr.scene_title + "' @ " + tcStr + ']: ' +
        'Apply targeted ' + paramVal + ' refinement centered at (' + draftPinX.toFixed(2) + ', ' + draftPinY.toFixed(2) + '): ' + comment + '.';

      sr.annotations.push({{
        note_id: noteId,
        scene_index: sr.scene_index,
        timecode_smpte: tcStr,
        timecode_sec: tSec,
        frame_number: Math.floor(currentFrame),
        reviewer_role: roleVal,
        reviewer_name: roleVal.replace(/_/g, ' ').toUpperCase(),
        marker_color: colorVal,
        comment: comment,
        target_parameter: paramVal,
        resolved: false,
        blocking_gate: isBlocking,
        x_norm: draftPinX,
        y_norm: draftPinY,
        compiled_edit_delta: deltaStr
      }});
      if (isBlocking) sr.approval_status = 'changes_requested';
      reviewDirty = true;
      activeReviewNoteId = noteId;
      if (inputEl) inputEl.value = '';
      const draftEl = document.getElementById('review-pin-draft');
      if (draftEl) draftEl.style.display = 'none';
      renderReviewHUD();
      showToast('📌 Added ' + noteId + ' @ ' + tcStr + ' (' + Math.round(draftPinX * 100) + '%, ' + Math.round(draftPinY * 100) + '%)');
    }}

    function jumpToReviewNote(noteId) {{
      for (const sr of REVIEW_STATE.scene_reviews) {{
        const note = sr.annotations.find((n) => n.note_id === noteId);
        if (note) {{
          activeReviewSceneIdx = note.scene_index;
          activeReviewNoteId = note.note_id;
          renderFrame(note.frame_number);
          renderReviewHUD();
          showToast('⏩ Seeked to ' + note.note_id + ' @ ' + note.timecode_smpte);
          return;
        }}
      }}
    }}

    function toggleReviewNoteResolved(noteId) {{
      for (const sr of REVIEW_STATE.scene_reviews) {{
        const note = sr.annotations.find((n) => n.note_id === noteId);
        if (note) {{
          note.resolved = !note.resolved;
          if (note.resolved) {{
            const hasOpenBlocking = sr.annotations.some((n) => !n.resolved && n.blocking_gate);
            const hasOpenAny = sr.annotations.some((n) => !n.resolved);
            if (sr.approval_status === 'changes_requested' && !hasOpenBlocking) {{
              sr.approval_status = hasOpenAny ? 'pending_review' : 'approved';
            }}
          }} else if (note.blocking_gate) {{
            sr.approval_status = 'changes_requested';
          }}
          reviewDirty = true;
          renderReviewHUD();
          showToast(note.note_id + (note.resolved ? ' marked RESOLVED' : ' reopened'));
          return;
        }}
      }}
    }}

    function setSceneApprovalStatus(sceneIdx, statusVal) {{
      const sr = REVIEW_STATE.scene_reviews.find((s) => s.scene_index === sceneIdx);
      if (!sr) return;
      sr.approval_status = statusVal;
      reviewDirty = true;
      renderReviewHUD();
      const label = statusVal === 'approved' ? 'APPROVED' : (statusVal === 'changes_requested' ? 'CHANGES REQUESTED' : 'PENDING');
      showToast('Scene ' + String(sceneIdx).padStart(2, '0') + ' signoff set to ' + label);
    }}

    function initReviewHUD() {{
      renderReviewHUD();
    }}

    function _buildDynamicReviewEDL() {{
      if (!reviewDirty) return REVIEW_INITIAL_EDL;
      const lines = ['TITLE: ' + REVIEW_STATE.project_title.toUpperCase().slice(0, 48) + ' REVIEW MARKERS', 'FCM: NON-DROP FRAME', ''];
      let ev = 1;
      REVIEW_STATE.scene_reviews.forEach((sr) => {{
        sr.annotations.forEach((n) => {{
          const tcIn = n.timecode_smpte || '00:00:00:00';
          const tcOut = formatSMPTE((n.frame_number || 0) + 1);
          const st = n.resolved ? 'RESOLVED' : 'OPEN';
          lines.push(String(ev).padStart(3, '0') + '  AX       V     C        ' + tcIn + ' ' + tcOut + ' ' + tcIn + ' ' + tcOut);
          lines.push('* FROM CLIP NAME: SCENE_' + String(sr.scene_index).padStart(2, '0') + '_PLATE.MP4');
          lines.push('* LOC: ' + tcIn + ' ' + n.marker_color + ' [' + n.note_id + ' | ' + n.reviewer_role + ' | ' + st + '] ' + n.comment);
          lines.push('');
          ev += 1;
        }});
      }});
      return lines.join('\\n');
    }}

    function _buildDynamicReviewFCPXML() {{
      if (!reviewDirty) return REVIEW_INITIAL_FCPXML;
      const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
      const fps = 24;
      const resources = ['        <format id="r1" name="FFVideoFormat1080p24" frameDuration="1/24s" width="1920" height="1080" colorSpace="1-1-1 (Rec. 709)"/>'];
      const spine = [];
      let offset = 0;
      let totalFrames = 0;
      REVIEW_STATE.scene_reviews.forEach((sr) => {{
        const startSec = Number(sr.start_sec || 0);
        const endSec = Number(sr.end_sec || (startSec + 5));
        const clipDurSec = Math.max(1, Math.round(endSec - startSec));
        const clipFrames = clipDurSec * fps;
        const resId = 'r' + (sr.scene_index + 1);
        resources.push('        <asset id="' + resId + '" name="SCENE_' + String(sr.scene_index).padStart(2, '0') + '" start="0s" duration="' + clipFrames + '/24s" hasVideo="1" hasAudio="1" format="r1"/>');
        const markers = sr.annotations.map((n) => {{
          const tcSec = Number(n.timecode_sec || 0);
          const relSec = Math.max(0, tcSec - startSec);
          const localFrames = Math.max(0, Math.min(clipFrames - 1, Math.round(relSec * fps)));
          return '                            <marker start="' + localFrames + '/24s" duration="1/24s" value="' + esc('[' + n.note_id + ' | ' + n.marker_color + ' | ' + n.reviewer_role + '] ' + n.comment) + '" note="' + esc(n.compiled_edit_delta || n.comment) + '" completed="' + (n.resolved ? '1' : '0') + '"/>';
        }});
        spine.push('                        <asset-clip name="' + esc('Scene_' + String(sr.scene_index).padStart(2, '0')) + '" ref="' + resId + '" offset="' + offset + '/24s" duration="' + clipFrames + '/24s" start="0s" format="r1">\\n' + markers.join('\\n') + '\\n                        </asset-clip>');
        offset += clipFrames;
        totalFrames += clipFrames;
      }});
      return '<?xml version="1.0" encoding="UTF-8"?>\\n<fcpxml version="1.10">\\n    <resources>\\n' + resources.join('\\n') + '\\n    </resources>\\n    <library>\\n        <event name="' + esc(REVIEW_STATE.project_title) + ' Review">\\n            <project name="' + esc(REVIEW_STATE.project_title) + ' Review Markers">\\n                <sequence format="r1" duration="' + Math.max(fps, totalFrames) + '/24s" tcStart="0s" tcFormat="NDF" audioLayout="stereo" audioRate="48k">\\n                    <spine>\\n' + spine.join('\\n') + '\\n                    </spine>\\n                </sequence>\\n            </project>\\n        </event>\\n    </library>\\n</fcpxml>\\n';
    }}

    function _buildDynamicReviewJSON() {{
      if (!reviewDirty) return REVIEW_INITIAL_JSON;
      const comments = [];
      let totalNotes = 0;
      let openNotes = 0;
      let blockingNotes = 0;
      const sceneSignoffs = REVIEW_STATE.scene_reviews.map((sr) => {{
        let srOpen = 0;
        let srResolved = 0;
        sr.annotations.forEach((n) => {{
          totalNotes += 1;
          if (n.resolved) {{
            srResolved += 1;
          }} else {{
            srOpen += 1;
            openNotes += 1;
            if (n.blocking_gate) blockingNotes += 1;
          }}
          comments.push({{
            id: n.note_id,
            scene_index: n.scene_index,
            timestamp: n.timecode_sec,
            timecode_smpte: n.timecode_smpte,
            frame: n.frame_number,
            author_role: n.reviewer_role,
            author_name: n.reviewer_name,
            color: n.marker_color,
            target_parameter: n.target_parameter,
            text: n.comment,
            annotation_pin: {{ x_norm: n.x_norm, y_norm: n.y_norm, radius_norm: 0.06 }},
            resolved: n.resolved,
            blocking_gate: n.blocking_gate,
            compiled_edit_delta: n.compiled_edit_delta
          }});
        }});
        sr.open_notes_count = srOpen;
        sr.resolved_notes_count = srResolved;
        return Object.assign({{}}, sr, {{
          open_notes_count: srOpen,
          resolved_notes_count: srResolved
        }});
      }});
      return JSON.stringify({{
        schema_format: 'frameio_review_v4_compatible',
        project_title: REVIEW_STATE.project_title,
        revision: REVIEW_STATE.revision,
        overall_status: REVIEW_STATE.overall_status,
        overall_approval_status: REVIEW_STATE.overall_status,
        ready_for_live_render: REVIEW_STATE.ready_for_live_render,
        total_notes_count: totalNotes,
        open_notes_count: openNotes,
        blocking_notes_count: blockingNotes,
        unresolved_blockers: blockingNotes,
        comments: comments,
        scene_signoffs: sceneSignoffs
      }}, null, 2);
    }}

    function _buildDynamicReviewMD() {{
      if (!reviewDirty) return REVIEW_INITIAL_MD;
      const escMd = (v) => String(v == null ? '' : v).replace(/\\|/g, '\\\\|').replace(/\\r?\\n/g, ' ');
      const gate = REVIEW_STATE.ready_for_live_render ? 'READY FOR LIVE RENDER' : 'BLOCKED PENDING SIGN-OFF';
      const lines = [
        '# Client Review & Stakeholder Signoff Report: ' + escMd(REVIEW_STATE.project_title),
        '',
        '- **Revision**: `v' + REVIEW_STATE.revision + '`',
        '- **Overall Status**: `' + REVIEW_STATE.overall_status.toUpperCase() + '`',
        '- **Live-Render Gate**: **`' + gate + '`**',
        '',
        '## Per-Scene Signoff Matrix',
        '| Scene | Title | Status | Notes |',
        '|---|---|---|---|'
      ];
      REVIEW_STATE.scene_reviews.forEach((sr) => {{
        lines.push('| ' + sr.scene_index + ' | ' + escMd(sr.scene_title) + ' | `' + sr.approval_status.toUpperCase() + '` | ' + sr.annotations.length + ' |');
      }});
      lines.push('', '## Timestamped Annotation Log', '| Note ID | Scene | Timecode | Pin | Status | Comment |', '|---|---|---|---|---|---|');
      REVIEW_STATE.scene_reviews.forEach((sr) => {{
        sr.annotations.forEach((n) => {{
          const st = n.resolved ? 'RESOLVED' : (n.blocking_gate ? 'BLOCKING' : 'OPEN');
          lines.push('| `' + escMd(n.note_id) + '` | ' + n.scene_index + ' | `' + escMd(n.timecode_smpte) + '` | (' + Math.round((n.x_norm || 0.5) * 100) + '%, ' + Math.round((n.y_norm || 0.48) * 100) + '%) | `' + st + '` | ' + escMd(n.comment) + ' |');
        }});
      }});
      return lines.join('\\n') + '\\n';
    }}

    function downloadReviewEDL() {{
      _triggerBlobDownload(_buildDynamicReviewEDL(), 'text/plain;charset=utf-8;', 'review_markers.edl', 'Downloaded Resolve Locator EDL (review_markers.edl)');
    }}

    function downloadReviewFCPXML() {{
      _triggerBlobDownload(_buildDynamicReviewFCPXML(), 'application/xml;charset=utf-8;', 'review_markers.fcpxml', 'Downloaded FCPXML Markers (review_markers.fcpxml)');
    }}

    function downloadReviewJSON() {{
      _triggerBlobDownload(_buildDynamicReviewJSON(), 'application/json;charset=utf-8;', 'review_notes_frameio.json', 'Downloaded Frame.io Review JSON (review_notes_frameio.json)');
    }}

    function downloadReviewMD() {{
      _triggerBlobDownload(_buildDynamicReviewMD(), 'text/markdown;charset=utf-8;', 'client_signoff_report.md', 'Downloaded Client Signoff Report (client_signoff_report.md)');
    }}
"""

    return {
        "toolbar_actions_html": _build_departmental_toolbar_html(),
        "css": v212_css,
        "modals_html": v212_modals_html,
        "js": v212_js,
    }
