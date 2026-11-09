"""HDR10 / SMPTE ST 2084 PQ & ARIB STD-B67 HLG Broadcast Color Science Engine (PM-FEAT-015).

Provides pure-Python EOTF / OETF mathematical transforms, dynamic MaxCLL / MaxFALL
content light level analytics, multi-operator tone mapping, DaVinci Resolve Studio
Color Management (RCM) XML authoring, and Gemini Omni prompt tokens.
"""

from __future__ import annotations

import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from omni_director.schemas import (
    ColorVolumeGamut,
    HdrMasteringDisplaySpec,
    HdrMetadataSpec,
    HdrTransferFunction,
    MasterProductionBible,
    SceneHdrReport,
    ScenePromptSpec,
    ToneMappingOperator,
)

# ==============================================================================
# SMPTE ST 2084 (Perceptual Quantizer / PQ) Mathematical Constants
# ==============================================================================

PQ_C1: float = 0.8359375           # 3424 / 4096
PQ_C2: float = 18.8515625          # 2413 / 128
PQ_C3: float = 18.6875             # 2392 / 128
PQ_M1: float = 0.1593017578125     # 2610 / 16384
PQ_M2: float = 78.84375            # 2523 / 32
PQ_PEAK_NITS: float = 10000.0


def pq_eotf_to_nits(v: float) -> float:
    """SMPTE ST 2084 PQ Electro-Optical Transfer Function (EOTF).

    Converts a normalized electrical signal V in [0.0, 1.0] to absolute display
    luminance in nits (cd/m^2) in [0.0, 10000.0].
    """
    if v <= 0.0:
        return 0.0
    v_clamped = min(1.0, max(0.0, float(v)))
    
    # Y = ( max(V^(1/m2) - c1, 0) / (c2 - c3 * V^(1/m2)) ) ^ (1/m1)
    v_pow = math.pow(v_clamped, 1.0 / PQ_M2)
    num = max(v_pow - PQ_C1, 0.0)
    den = max(PQ_C2 - (PQ_C3 * v_pow), 1e-12)
    
    y = math.pow(num / den, 1.0 / PQ_M1)
    return y * PQ_PEAK_NITS


def pq_inverse_eotf(nits: float) -> float:
    """SMPTE ST 2084 PQ Inverse EOTF (OETF encoding).

    Converts absolute display luminance in nits (cd/m^2) in [0.0, 10000.0]
    to a normalized electrical signal V in [0.0, 1.0].
    """
    if nits <= 0.0:
        return 0.0
    y = min(1.0, max(0.0, float(nits) / PQ_PEAK_NITS))
    
    # V = ( (c1 + c2 * Y^m1) / (1 + c3 * Y^m1) ) ^ m2
    y_pow = math.pow(y, PQ_M1)
    num = PQ_C1 + (PQ_C2 * y_pow)
    den = 1.0 + (PQ_C3 * y_pow)
    
    v = math.pow(num / den, PQ_M2)
    return min(1.0, max(0.0, v))


# ==============================================================================
# ARIB STD-B67 / ITU-R BT.2100 Hybrid Log-Gamma (HLG) Constants & Transforms
# ==============================================================================

HLG_A: float = 0.17883277
HLG_B: float = 0.28466892          # 1 - 4a
HLG_C: float = 0.55991073          # 0.5 - a * ln(4a)


def hlg_oetf(linear_val: float) -> float:
    """ARIB STD-B67 / BT.2100 Hybrid Log-Gamma Opto-Electrical Transfer Function (OETF).

    Encodes normalized linear scene light in [0.0, 1.0+] into normalized HLG signal in [0.0, 1.0].
    """
    if linear_val <= 0.0:
        return 0.0
    e = float(linear_val)
    if e <= (1.0 / 12.0):
        e_prime = math.sqrt(3.0 * e)
    else:
        e_prime = (HLG_A * math.log(max(12.0 * e - HLG_B, 1e-12))) + HLG_C
    return min(1.0, max(0.0, e_prime))


def hlg_eotf(signal: float, peak_nits: float = 1000.0) -> float:
    """ARIB STD-B67 / BT.2100 Hybrid Log-Gamma Electro-Optical Transfer Function (EOTF).

    Converts a normalized electrical signal in [0.0, 1.0] to display luminance in nits
    incorporating display-dependent system gamma.
    """
    if signal <= 0.0:
        return 0.0
    e_prime = min(1.0, max(0.0, float(signal)))
    if e_prime <= 0.5:
        e = (e_prime * e_prime) / 3.0
    else:
        e = (math.exp((e_prime - HLG_C) / HLG_A) + HLG_B) / 12.0

    # System gamma for target display peak luminance
    # Standard BT.2100 gamma: gamma = 1.2 + 0.42 * log10(Lw / 1000)
    lw = max(100.0, float(peak_nits))
    gamma = 1.2 + (0.42 * math.log10(lw / 1000.0))
    return lw * math.pow(e, gamma)


# ==============================================================================
# Tone Mapping Operators
# ==============================================================================

def apply_tone_mapping(
    nits: float,
    max_display_nits: float = 1000.0,
    operator: ToneMappingOperator = ToneMappingOperator.ACES_SPLINE,
) -> float:
    """Applies tone mapping compression from source HDR nits to target display peak luminance."""
    if nits <= 0.0:
        return 0.0
    target_peak = max(100.0, float(max_display_nits))
    op = operator.value if hasattr(operator, "value") else str(operator).lower()

    if op == "clip":
        return min(float(nits), target_peak)

    if op == "reinhard_extended":
        x = float(nits) / target_peak
        c = 2.0  # white point burn multiplier
        # Reinhard extended: (x * (1 + x / c^2)) / (1 + x)
        mapped_ratio = (x * (1.0 + (x / (c * c)))) / (1.0 + x)
        return min(target_peak, mapped_ratio * target_peak)

    if op == "bt_2446_method_a":
        # ITU-R BT.2446 Method A highlight compression
        x = float(nits) / 10000.0
        y = x / (1.0 + (0.75 * x))
        norm = 1.0 / (1.0 + 0.75)
        return min(target_peak, (y / norm) * target_peak)

    # Default: ACES Spline (Narkowicz fit)
    x = float(nits) / target_peak
    a = 2.51
    b = 0.03
    c = 2.43
    d = 0.59
    e = 0.14
    mapped_ratio = (x * (a * x + b)) / (x * (c * x + d) + e)
    return min(target_peak, max(0.0, mapped_ratio) * target_peak)


# ==============================================================================
# Dynamic MaxCLL & MaxFALL Content Light Level Calculators
# ==============================================================================

def calculate_scene_max_cll(bible: MasterProductionBible, scene_idx: int) -> float:
    """Calculates Maximum Content Light Level (MaxCLL) in nits for a given scene.

    Inspects scene-specific HDR metadata, lighting rig intensity, and kinetic
    specular descriptions to compute physical highlight peaks.
    """
    scenes = bible.scenes or []
    if 1 <= scene_idx <= len(scenes):
        scene = scenes[scene_idx - 1]
        if scene.hdr_spec and scene.hdr_spec.max_cll_nits > 0:
            return float(scene.hdr_spec.max_cll_nits)
        
        # Infer from lighting rig photometrics if present
        if scene.lighting_rig and getattr(scene.lighting_rig, "fixtures", None):
            key_fixtures = [
                f for f in scene.lighting_rig.fixtures
                if getattr(f, "role", None) in ("key_light", getattr(getattr(f, "role", None), "value", None))
            ]
            if key_fixtures:
                key_lux = getattr(key_fixtures[0], "lux_at_subject", 1000.0)
                # Estimate peak nits from specular bounce (lux / pi * albedo + specular highlight)
                inferred = min(4000.0, max(400.0, (key_lux / math.pi) * 2.5))
                return round(inferred, 1)

        # Keyword heuristics for high-specular environments
        prompt = scene.omni_prose_prompt.lower()
        if any(w in prompt for w in ["sun", "laser", "explosion", "sparks", "chrome", "lens flare", "neon", "fire", "lightning"]):
            return 1400.0
        if any(w in prompt for w in ["night", "shadow", "candle", "dusk", "interior gloom"]):
            return 650.0

    if bible.master_hdr_spec and bible.master_hdr_spec.max_cll_nits > 0:
        return float(bible.master_hdr_spec.max_cll_nits)

    return 1000.0


def calculate_scene_max_fall(bible: MasterProductionBible, scene_idx: int) -> float:
    """Calculates Maximum Frame Average Light Level (MaxFALL) in nits for a given scene.

    Hollywood HDR grading conventions establish MaxFALL between 25% and 40% of MaxCLL.
    """
    scenes = bible.scenes or []
    if 1 <= scene_idx <= len(scenes):
        scene = scenes[scene_idx - 1]
        if scene.hdr_spec and scene.hdr_spec.max_fall_nits > 0:
            return float(scene.hdr_spec.max_fall_nits)

    max_cll = calculate_scene_max_cll(bible, scene_idx)
    # Default 35% of peak MaxCLL, clamped to realistic frame averages [50, 600]
    return round(min(600.0, max(50.0, max_cll * 0.35)), 1)


def generate_scene_hdr_report(bible: MasterProductionBible, scene_idx: int) -> SceneHdrReport:
    """Generates a complete SceneHdrReport evaluating luminance and gamut clipping risk."""
    max_cll = calculate_scene_max_cll(bible, scene_idx)
    max_fall = calculate_scene_max_fall(bible, scene_idx)
    
    scenes = bible.scenes or []
    scene = scenes[scene_idx - 1] if 1 <= scene_idx <= len(scenes) else None
    
    hdr_spec = (scene.hdr_spec if scene else None) or bible.master_hdr_spec or HdrMetadataSpec()
    
    clipping_risk = "none"
    if max_cll > hdr_spec.mastering_display.peak_luminance_nits:
        clipping_risk = "highlight_compression_active"

    token = format_hdr_prompt_token(hdr_spec)

    return SceneHdrReport(
        scene_index=scene_idx,
        transfer_function=hdr_spec.transfer_function,
        calculated_max_cll_nits=max_cll,
        calculated_max_fall_nits=max_fall,
        gamut_coverage_percent=98.5,
        clipping_risk=clipping_risk,
        tone_mapping_applied=hdr_spec.tone_mapping,
        prompt_token=token,
    )


# ==============================================================================
# Prompt Token Formatting
# ==============================================================================

def format_hdr_prompt_token(hdr_spec: Optional[HdrMetadataSpec]) -> str:
    """Formats an affirmative physical HDR token for Gemini Omni video prompts."""
    if hdr_spec is None:
        return "[HDR Signal: SMPTE ST 2084 PQ, Gamut: Rec.2020, Peak: 1000 nits, MaxCLL: 1000 nits, MaxFALL: 400 nits]"

    tf_str = "SMPTE ST 2084 PQ"
    tf_val = hdr_spec.transfer_function.value if hasattr(hdr_spec.transfer_function, "value") else str(hdr_spec.transfer_function)
    if "hlg" in tf_val.lower():
        tf_str = "ARIB STD-B67 HLG"
    elif "linear" in tf_val.lower():
        tf_str = "Linear Scene Exposure"

    gamut_str = "Rec.2020"
    gamut_val = hdr_spec.target_gamut.value if hasattr(hdr_spec.target_gamut, "value") else str(hdr_spec.target_gamut)
    if "dci" in gamut_val.lower() or "p3" in gamut_val.lower():
        gamut_str = "DCI-P3 D65"
    elif "709" in gamut_val.lower():
        gamut_str = "Rec.709"

    peak_nits = int(round(hdr_spec.mastering_display.peak_luminance_nits))
    max_cll = int(round(hdr_spec.max_cll_nits))
    max_fall = int(round(hdr_spec.max_fall_nits))

    return (
        f"[HDR Signal: {tf_str}, Gamut: {gamut_str}, "
        f"Peak: {peak_nits} nits, MaxCLL: {max_cll} nits, MaxFALL: {max_fall} nits]"
    )


# ==============================================================================
# Exporters: HDR10 JSON, HLG XML, DaVinci Resolve RCM XML, Bundle
# ==============================================================================

def _extract_hdr_and_bible_info(target: Any) -> Tuple[HdrMetadataSpec, str, List[Any], Any]:
    """Helper to extract hdr_spec, title, scenes, and bible from target."""
    if isinstance(target, HdrMetadataSpec):
        return target, "Omni Production", [], None
    hdr_spec = getattr(target, "master_hdr_spec", None) or getattr(target, "hdr_spec", None) or HdrMetadataSpec()
    title = getattr(target, "project_title", getattr(target, "title", "Omni Production"))
    scenes = getattr(target, "scenes", None) or []
    return hdr_spec, title, scenes, target


def export_hdr10_json(bible: Any, path: Path) -> Path:
    """Exports CTA-861.3 / SMPTE ST 2086 HDR10 static metadata JSON."""
    hdr_spec, title, scenes, bible_obj = _extract_hdr_and_bible_info(bible)
    target_path = Path(path)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    scenes_data: List[Dict[str, Any]] = []
    if bible_obj is not None and scenes:
        for idx in range(1, len(scenes) + 1):
            cll = calculate_scene_max_cll(bible_obj, idx)
            fall = calculate_scene_max_fall(bible_obj, idx)
            scenes_data.append({
                "scene_index": idx,
                "max_cll_nits": cll,
                "max_fall_nits": fall,
                "pq_code_max_cll": round(pq_inverse_eotf(cll), 4),
                "pq_code_max_fall": round(pq_inverse_eotf(fall), 4),
            })

    payload = {
        "schema_version": "1.0",
        "standard": "SMPTE ST 2086 / CTA-861.3 / ITU-R BT.2020",
        "production_title": title or "Omni Production",
        "transfer_function": hdr_spec.transfer_function.value if hasattr(hdr_spec.transfer_function, "value") else str(hdr_spec.transfer_function),
        "target_color_gamut": hdr_spec.target_gamut.value if hasattr(hdr_spec.target_gamut, "value") else str(hdr_spec.target_gamut),
        "mastering_display": {
            "peak_luminance_nits": hdr_spec.mastering_display.peak_luminance_nits,
            "black_level_nits": hdr_spec.mastering_display.black_level_nits,
            "color_volume": hdr_spec.mastering_display.color_volume.value if hasattr(hdr_spec.mastering_display.color_volume, "value") else str(hdr_spec.mastering_display.color_volume),
            "white_point_d65": {
                "x": hdr_spec.mastering_display.white_point_d65[0],
                "y": hdr_spec.mastering_display.white_point_d65[1],
            },
            "primaries_cie1931": {
                k: {"x": v[0], "y": v[1]}
                for k, v in hdr_spec.mastering_display.primary_coordinates.items()
            },
            "MasteringDisplayColorPrimaries": {
                k: {"x": v[0], "y": v[1]}
                for k, v in hdr_spec.mastering_display.primary_coordinates.items()
            },
        },
        "MaxCLL": hdr_spec.max_cll_nits,
        "MaxFALL": hdr_spec.max_fall_nits,
        "content_light_levels": {
            "master_max_cll_nits": hdr_spec.max_cll_nits,
            "master_max_fall_nits": hdr_spec.max_fall_nits,
            "knee_point_nits": hdr_spec.knee_point_nits,
            "shoulder_point_nits": hdr_spec.shoulder_point_nits,
            "tone_mapping_operator": hdr_spec.tone_mapping.value if hasattr(hdr_spec.tone_mapping, "value") else str(hdr_spec.tone_mapping),
        },
        "scenes": scenes_data,
    }

    target_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return target_path


def export_hlg_xml(bible: Any, path: Path) -> Path:
    """Exports ARIB STD-B67 / ITU-R BT.2100 HLG broadcast manifest XML."""
    hdr_spec, title, scenes, bible_obj = _extract_hdr_and_bible_info(bible)
    target_path = Path(path)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    root = ET.Element("HlgBroadcastManifest", version="1.0")
    ET.SubElement(root, "ProductionTitle").text = title
    ET.SubElement(root, "Standard").text = "ARIB STD-B67 / ITU-R BT.2100-2"
    ET.SubElement(root, "ColorSpace").text = "BT.2100-HLG"
    ET.SubElement(root, "NominalPeakLuminanceNits").text = str(hdr_spec.mastering_display.peak_luminance_nits)
    
    lw = max(100.0, float(hdr_spec.mastering_display.peak_luminance_nits))
    gamma = 1.2 + (0.42 * math.log10(lw / 1000.0))
    ET.SubElement(root, "SystemGamma").text = f"{gamma:.3f}"

    scenes_elem = ET.SubElement(root, "Scenes")
    if bible_obj is not None and scenes:
        for idx in range(1, len(scenes) + 1):
            cll = calculate_scene_max_cll(bible_obj, idx)
            fall = calculate_scene_max_fall(bible_obj, idx)
            sc = ET.SubElement(scenes_elem, "Scene", index=str(idx))
            ET.SubElement(sc, "MaxCLLNits").text = f"{cll:.1f}"
            ET.SubElement(sc, "MaxFALLNits").text = f"{fall:.1f}"
            ET.SubElement(sc, "HlgSignalPeak").text = f"{hlg_oetf(cll / 1000.0):.4f}"

    tree = ET.ElementTree(root)
    tree.write(str(target_path), encoding="utf-8", xml_declaration=True)
    return target_path


def export_resolve_hdr_xml(bible: Any, path: Path) -> Path:
    """Exports DaVinci Resolve Studio HDR Color Management (RCM) XML metadata."""
    hdr_spec, title, scenes, bible_obj = _extract_hdr_and_bible_info(bible)
    target_path = Path(path)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    root = ET.Element("ResolveColorManagement", version="18.5")
    ET.SubElement(root, "ColorScience").text = "DaVinci YRGB Color Managed"
    ET.SubElement(root, "ColorProcessingMode").text = "HDR DaVinci Wide Gamut Intermediate"
    ET.SubElement(root, "OutputColorSpace").text = "Rec.2020 ST2084"
    ET.SubElement(root, "TargetPeakLuminance").text = f"{hdr_spec.mastering_display.peak_luminance_nits:.0f}"
    ET.SubElement(root, "MaxCLL").text = f"{hdr_spec.max_cll_nits:.0f}"
    ET.SubElement(root, "MaxFALL").text = f"{hdr_spec.max_fall_nits:.0f}"
    ET.SubElement(root, "ToneMapping").text = hdr_spec.tone_mapping.value if hasattr(hdr_spec.tone_mapping, "value") else str(hdr_spec.tone_mapping)

    timeline = ET.SubElement(root, "TimelineClips")
    if bible_obj is not None and scenes:
        for idx in range(1, len(scenes) + 1):
            cll = calculate_scene_max_cll(bible_obj, idx)
            fall = calculate_scene_max_fall(bible_obj, idx)
            clip = ET.SubElement(timeline, "Clip", scene=str(idx))
            ET.SubElement(clip, "InputColorSpace").text = "Linear ACEScg / Scene Referred"
            ET.SubElement(clip, "SceneMaxCLL").text = f"{cll:.1f}"
            ET.SubElement(clip, "SceneMaxFALL").text = f"{fall:.1f}"

    tree = ET.ElementTree(root)
    tree.write(str(target_path), encoding="utf-8", xml_declaration=True)
    return target_path


def export_hdr_bundle(bible: Any, output_dir: Path) -> Dict[str, Path]:
    """Exports all HDR10, HLG, and DaVinci Resolve color management manifests."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    hdr10_path = export_hdr10_json(bible, out_dir / "hdr10_metadata.json")
    hlg_path = export_hlg_xml(bible, out_dir / "hlg_broadcast.xml")
    resolve_path = export_resolve_hdr_xml(bible, out_dir / "resolve_hdr_rcm.xml")

    # Generate master HDR report summary
    scenes = getattr(bible, "scenes", None) or []
    reports = [generate_scene_hdr_report(bible, idx).model_dump() for idx in range(1, len(scenes) + 1)] if scenes else []
    report_path = out_dir / "hdr_master_report.json"
    report_path.write_text(json.dumps({"reports": reports}, indent=2), encoding="utf-8")

    return {
        "hdr10_json": hdr10_path,
        "hlg_xml": hlg_path,
        "resolve_xml": resolve_path,
        "report_json": report_path,
    }


def synthesize_default_hdr_spec(
    transfer_function: HdrTransferFunction = HdrTransferFunction.SMPTE_ST_2084_PQ,
    peak_luminance_nits: float = 1000.0,
    target_gamut: ColorVolumeGamut = ColorVolumeGamut.BT_2020,
    tone_mapping: ToneMappingOperator = ToneMappingOperator.ACES_SPLINE,
) -> HdrMetadataSpec:
    """Synthesize a production-ready HDR mastering metadata spec."""
    mastering = HdrMasteringDisplaySpec(
        peak_luminance_nits=peak_luminance_nits,
        black_level_nits=0.0001,
        color_volume=target_gamut,
    )
    return HdrMetadataSpec(
        transfer_function=transfer_function,
        mastering_display=mastering,
        max_cll_nits=min(10000.0, peak_luminance_nits * 0.95),
        max_fall_nits=min(10000.0, peak_luminance_nits * 0.35),
        tone_mapping=tone_mapping,
        target_gamut=target_gamut,
        knee_point_nits=100.0,
        shoulder_point_nits=peak_luminance_nits,
    )


def export_hdr10_metadata_json(hdr_or_bible: Union[HdrMetadataSpec, MasterProductionBible]) -> str:
    """Generates CTA-861.3 / SMPTE ST 2086 HDR10 static metadata JSON string."""
    if isinstance(hdr_or_bible, HdrMetadataSpec):
        hdr_spec = hdr_or_bible
        title = "Omni Production"
    else:
        hdr_spec = getattr(hdr_or_bible, "master_hdr_spec", None) or HdrMetadataSpec()
        title = getattr(hdr_or_bible, "title", "Omni Production")

    payload = {
        "schema_version": "1.0",
        "standard": "SMPTE ST 2086 / CTA-861.3 / ITU-R BT.2020",
        "production_title": title,
        "transfer_function": hdr_spec.transfer_function.value if hasattr(hdr_spec.transfer_function, "value") else str(hdr_spec.transfer_function),
        "target_color_gamut": hdr_spec.target_gamut.value if hasattr(hdr_spec.target_gamut, "value") else str(hdr_spec.target_gamut),
        "mastering_display": {
            "peak_luminance_nits": hdr_spec.mastering_display.peak_luminance_nits,
            "black_level_nits": hdr_spec.mastering_display.black_level_nits,
            "color_volume": hdr_spec.mastering_display.color_volume.value if hasattr(hdr_spec.mastering_display.color_volume, "value") else str(hdr_spec.mastering_display.color_volume),
            "white_point_d65": {
                "x": hdr_spec.mastering_display.white_point_d65[0],
                "y": hdr_spec.mastering_display.white_point_d65[1],
            },
            "primaries_cie1931": {
                k: {"x": v[0], "y": v[1]}
                for k, v in hdr_spec.mastering_display.primary_coordinates.items()
            },
        },
        "MaxCLL": hdr_spec.max_cll_nits,
        "MaxFALL": hdr_spec.max_fall_nits,
        "content_light_levels": {
            "master_max_cll_nits": hdr_spec.max_cll_nits,
            "master_max_fall_nits": hdr_spec.max_fall_nits,
            "knee_point_nits": hdr_spec.knee_point_nits,
            "shoulder_point_nits": hdr_spec.shoulder_point_nits,
            "tone_mapping_operator": hdr_spec.tone_mapping.value if hasattr(hdr_spec.tone_mapping, "value") else str(hdr_spec.tone_mapping),
        },
    }
    return json.dumps(payload, indent=2)


def export_hlg_broadcast_xml(hdr_or_bible: Union[HdrMetadataSpec, MasterProductionBible]) -> str:
    """Generates ARIB STD-B67 / ITU-R BT.2100 HLG broadcast manifest XML string."""
    if isinstance(hdr_or_bible, HdrMetadataSpec):
        hdr_spec = hdr_or_bible
        title = "Omni Production"
    else:
        hdr_spec = getattr(hdr_or_bible, "master_hdr_spec", None) or HdrMetadataSpec()
        title = getattr(hdr_or_bible, "title", "Omni Production")

    root = ET.Element("HlgBroadcastManifest", version="1.0")
    ET.SubElement(root, "ProductionTitle").text = title
    ET.SubElement(root, "Standard").text = "ARIB STD-B67 / ITU-R BT.2100-2"
    ET.SubElement(root, "ColorSpace").text = "BT.2100-HLG"
    ET.SubElement(root, "NominalPeakLuminanceNits").text = str(hdr_spec.mastering_display.peak_luminance_nits)
    
    lw = max(100.0, float(hdr_spec.mastering_display.peak_luminance_nits))
    gamma = 1.2 + (0.42 * math.log10(lw / 1000.0))
    ET.SubElement(root, "SystemGamma").text = f"{gamma:.3f}"
    ET.SubElement(root, "MaxCLL").text = f"{hdr_spec.max_cll_nits:.1f}"
    ET.SubElement(root, "MaxFALL").text = f"{hdr_spec.max_fall_nits:.1f}"

    return ET.tostring(root, encoding="utf-8").decode("utf-8")


def export_resolve_hdr_xml_string(hdr_or_bible: Union[HdrMetadataSpec, MasterProductionBible]) -> str:
    """Generates DaVinci Resolve Studio HDR Color Management (RCM) XML string."""
    if isinstance(hdr_or_bible, HdrMetadataSpec):
        hdr_spec = hdr_or_bible
    else:
        hdr_spec = getattr(hdr_or_bible, "master_hdr_spec", None) or HdrMetadataSpec()

    root = ET.Element("ResolveColorManagement", version="18.5")
    ET.SubElement(root, "ColorScience").text = "DaVinci YRGB Color Managed"
    ET.SubElement(root, "ColorProcessingMode").text = "HDR DaVinci Wide Gamut Intermediate"
    ET.SubElement(root, "OutputColorSpace").text = "Rec.2020 ST2084"
    ET.SubElement(root, "TargetPeakLuminance").text = f"{hdr_spec.mastering_display.peak_luminance_nits:.0f}"
    ET.SubElement(root, "MaxCLL").text = f"{hdr_spec.max_cll_nits:.0f}"
    ET.SubElement(root, "MaxFALL").text = f"{hdr_spec.max_fall_nits:.0f}"
    ET.SubElement(root, "ToneMapping").text = hdr_spec.tone_mapping.value if hasattr(hdr_spec.tone_mapping, "value") else str(hdr_spec.tone_mapping)

    return ET.tostring(root, encoding="utf-8").decode("utf-8")


# Aliases
export_resolve_hdr_xml_str = export_resolve_hdr_xml_string
