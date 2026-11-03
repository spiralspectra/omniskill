"""Color grading, ASC CDL color science, and cinematic look preset suite."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Optional, Union
from xml.sax.saxutils import escape as xml_escape

from omni_director.schemas import (
    AscCdlSpec,
    ColorLookPreset,
    ColorLookSpec,
    MasterProductionBible,
)


LOOK_PRESET_REGISTRY: Dict[ColorLookPreset, ColorLookSpec] = {
    ColorLookPreset.REC709_NEUTRAL: ColorLookSpec(
        look_preset=ColorLookPreset.REC709_NEUTRAL,
        working_color_space="Rec.709",
        target_display="Rec.709 Gamma 2.4",
        cdl=AscCdlSpec(
            slope=(1.0, 1.0, 1.0),
            offset=(0.0, 0.0, 0.0),
            power=(1.0, 1.0, 1.0),
            saturation=1.0,
        ),
        contrast_pivot=0.435,
        halation_bloom=0.0,
    ),
    ColorLookPreset.KODAK_5219_VISION3: ColorLookSpec(
        look_preset=ColorLookPreset.KODAK_5219_VISION3,
        working_color_space="ACEScg",
        target_display="Rec.709 Gamma 2.4",
        cdl=AscCdlSpec(
            slope=(1.08, 1.02, 0.94),
            offset=(-0.015, -0.005, 0.012),
            power=(0.95, 0.98, 1.04),
            saturation=1.12,
        ),
        contrast_pivot=0.45,
        halation_bloom=0.18,
    ),
    ColorLookPreset.FUJI_ETERNA_500T: ColorLookSpec(
        look_preset=ColorLookPreset.FUJI_ETERNA_500T,
        working_color_space="ACEScg",
        target_display="Rec.709 Gamma 2.4",
        cdl=AscCdlSpec(
            slope=(0.96, 1.03, 1.06),
            offset=(0.018, 0.008, -0.012),
            power=(1.04, 0.98, 0.95),
            saturation=0.92,
        ),
        contrast_pivot=0.42,
        halation_bloom=0.08,
    ),
    ColorLookPreset.BLEACH_BYPASS_SILVER: ColorLookSpec(
        look_preset=ColorLookPreset.BLEACH_BYPASS_SILVER,
        working_color_space="ACEScg",
        target_display="Rec.709 Gamma 2.4",
        cdl=AscCdlSpec(
            slope=(1.25, 1.25, 1.25),
            offset=(-0.08, -0.08, -0.08),
            power=(1.15, 1.15, 1.15),
            saturation=0.35,
        ),
        contrast_pivot=0.50,
        halation_bloom=0.0,
    ),
    ColorLookPreset.TEAL_AND_ORANGE_BLOCKBUSTER: ColorLookSpec(
        look_preset=ColorLookPreset.TEAL_AND_ORANGE_BLOCKBUSTER,
        working_color_space="ACEScg",
        target_display="Rec.709 Gamma 2.4",
        cdl=AscCdlSpec(
            slope=(1.18, 1.02, 0.88),
            offset=(-0.04, 0.01, 0.06),
            power=(0.92, 0.98, 1.12),
            saturation=1.22,
        ),
        contrast_pivot=0.46,
        halation_bloom=0.12,
    ),
    ColorLookPreset.MONOCHROME_PANATOMIC_X: ColorLookSpec(
        look_preset=ColorLookPreset.MONOCHROME_PANATOMIC_X,
        working_color_space="ACEScg",
        target_display="Rec.709 Gamma 2.4",
        cdl=AscCdlSpec(
            slope=(1.05, 1.05, 1.05),
            offset=(-0.02, -0.02, -0.02),
            power=(1.08, 1.08, 1.08),
            saturation=0.0,
        ),
        contrast_pivot=0.44,
        halation_bloom=0.05,
    ),
}


def get_preset_color_look(preset: Union[ColorLookPreset, str]) -> ColorLookSpec:
    """Return calibrated CDL values and color grading spec for a preset name or enum."""
    if isinstance(preset, ColorLookPreset):
        key = preset
    else:
        norm = str(preset).strip().lower().replace("-", "_")
        try:
            key = ColorLookPreset(norm)
        except ValueError:
            key = ColorLookPreset.REC709_NEUTRAL
    return LOOK_PRESET_REGISTRY.get(key, LOOK_PRESET_REGISTRY[ColorLookPreset.REC709_NEUTRAL]).model_copy(deep=True)


def export_asc_cdl_xml(bible: MasterProductionBible) -> str:
    """Produces valid ASC CDL v1.2 XML with ColorDecision, SOPNode, and SATNode elements."""
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<ColorDecisionList xmlns="urn:ASC:CDL:v1.01">',
    ]

    master_look = bible.master_color_look or get_preset_color_look(ColorLookPreset.REC709_NEUTRAL)

    scenes = bible.scenes if bible.scenes else []
    if not scenes:
        cdl = master_look.cdl
        lines.extend([
            '    <ColorDecision>',
            '        <ColorCorrection id="MASTER">',
            '            <SOPNode>',
            f'                <Slope>{cdl.slope[0]:.6f} {cdl.slope[1]:.6f} {cdl.slope[2]:.6f}</Slope>',
            f'                <Offset>{cdl.offset[0]:.6f} {cdl.offset[1]:.6f} {cdl.offset[2]:.6f}</Offset>',
            f'                <Power>{cdl.power[0]:.6f} {cdl.power[1]:.6f} {cdl.power[2]:.6f}</Power>',
            '            </SOPNode>',
            '            <SATNode>',
            f'                <Saturation>{cdl.saturation:.6f}</Saturation>',
            '            </SATNode>',
            '        </ColorCorrection>',
            '    </ColorDecision>',
        ])
    else:
        for scene in scenes:
            scene_look = scene.scene_color_look or master_look
            cdl = scene_look.cdl
            corr_id = xml_escape(f"SCENE_{scene.scene_index:02d}")
            lines.extend([
                '    <ColorDecision>',
                f'        <ColorCorrection id="{corr_id}">',
                '            <SOPNode>',
                f'                <Slope>{cdl.slope[0]:.6f} {cdl.slope[1]:.6f} {cdl.slope[2]:.6f}</Slope>',
                f'                <Offset>{cdl.offset[0]:.6f} {cdl.offset[1]:.6f} {cdl.offset[2]:.6f}</Offset>',
                f'                <Power>{cdl.power[0]:.6f} {cdl.power[1]:.6f} {cdl.power[2]:.6f}</Power>',
                '            </SOPNode>',
                '            <SATNode>',
                f'                <Saturation>{cdl.saturation:.6f}</Saturation>',
                '            </SATNode>',
                '        </ColorCorrection>',
                '    </ColorDecision>',
            ])

    lines.append('</ColorDecisionList>')
    return "\n".join(lines) + "\n"


def export_asc_cdl_file(bible: MasterProductionBible, output_path: Union[str, Path]) -> Path:
    """Writes an ASC CDL XML document to disk and returns the resolved Path."""
    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    xml_content = export_asc_cdl_xml(bible)
    out_p.write_text(xml_content, encoding="utf-8")
    return out_p


def embed_cdl_in_edl(edl_text: str, bible: MasterProductionBible) -> str:
    """Injects standard *ASC_SOP (r g b) (r g b) (r g b) and *ASC_SAT s comment lines per event in CMX 3600 EDL."""
    lines = edl_text.splitlines()
    new_lines = []
    
    # Pre-map scenes by scene_index
    scene_map = {s.scene_index: s for s in bible.scenes}
    master_look = bible.master_color_look or get_preset_color_look(ColorLookPreset.REC709_NEUTRAL)

    current_event_idx: Optional[int] = None
    event_regex = re.compile(r"^(\d{3})\s+")

    for line in lines:
        match = event_regex.match(line)
        if match:
            current_event_idx = int(match.group(1))
            new_lines.append(line)
            continue

        # If line is blank or starting a new event, we might need to inject before next event
        if line.startswith("* FROM CLIP NAME:"):
            new_lines.append(line)
            # Find matching scene
            scene = scene_map.get(current_event_idx if current_event_idx is not None else 1)
            look = (scene.scene_color_look if scene and scene.scene_color_look else master_look)
            cdl = look.cdl
            s = cdl.slope
            o = cdl.offset
            p = cdl.power
            sat = cdl.saturation
            new_lines.append(
                f"*ASC_SOP ({s[0]:.6f} {s[1]:.6f} {s[2]:.6f}) ({o[0]:.6f} {o[1]:.6f} {o[2]:.6f}) ({p[0]:.6f} {p[1]:.6f} {p[2]:.6f})"
            )
            new_lines.append(f"*ASC_SAT {sat:.6f}")
            continue

        new_lines.append(line)

    return "\n".join(new_lines).strip() + "\n"


def cdl_to_svg_matrix_filter(cdl: AscCdlSpec, filter_id: str = "cdl-grade") -> str:
    """Generates an SVG <filter id="..."> element applying ASC CDL transfer functions."""
    s = max(0.0, min(4.0, cdl.saturation))
    sr = (1.0 - s) * 0.2126
    sg = (1.0 - s) * 0.7152
    sb = (1.0 - s) * 0.0722

    # Linear slope and intercept
    r_slope, g_slope, b_slope = cdl.slope
    r_off, g_off, b_off = cdl.offset
    r_pow, g_pow, b_pow = cdl.power

    return (
        f'<filter id="{xml_escape(filter_id)}" color-interpolation-filters="sRGB">\n'
        f'    <feColorMatrix type="matrix" values="\n'
        f'        {sr + s:.4f} {sg:.4f} {sb:.4f} 0 0\n'
        f'        {sr:.4f} {sg + s:.4f} {sb:.4f} 0 0\n'
        f'        {sr:.4f} {sg:.4f} {sb + s:.4f} 0 0\n'
        f'        0 0 0 1 0" result="saturated"/>\n'
        f'    <feComponentTransfer in="saturated" result="graded">\n'
        f'        <feFuncR type="linear" slope="{r_slope:.4f}" intercept="{r_off:.4f}"/>\n'
        f'        <feFuncG type="linear" slope="{g_slope:.4f}" intercept="{g_off:.4f}"/>\n'
        f'        <feFuncB type="linear" slope="{b_slope:.4f}" intercept="{b_off:.4f}"/>\n'
        f'    </feComponentTransfer>\n'
        f'    <feComponentTransfer in="graded">\n'
        f'        <feFuncR type="gamma" exponent="{r_pow:.4f}"/>\n'
        f'        <feFuncG type="gamma" exponent="{g_pow:.4f}"/>\n'
        f'        <feFuncB type="gamma" exponent="{b_pow:.4f}"/>\n'
        f'    </feComponentTransfer>\n'
        f'</filter>'
    )
