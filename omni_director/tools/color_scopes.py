"""Digital Colorimetry Scopes, Waveform/Vectorscope & Shot-Match Continuity (PM-FEAT-039)."""

from __future__ import annotations

import csv
import hashlib
import io
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from omni_director.schemas import (
    AdjacentCutColorMatchSpec,
    AscCdlSpec,
    MasterColorScopesManifest,
    MasterProductionBible,
    ScenePromptSpec,
    SceneScopeTelemetrySpec,
    ScopeSignalStandardEnum,
    ShotMatchStatusEnum,
)


def hex_to_srgb(hex_color: str) -> Tuple[float, float, float]:
    """Converts a #RRGGBB or #RGB hex string into normalized sRGB [0.0, 1.0] floats."""
    raw = str(hex_color or "").strip().lstrip("#")
    if len(raw) == 3:
        raw = "".join(c * 2 for c in raw)
    if len(raw) != 6:
        return (0.5, 0.5, 0.5)
    try:
        r = int(raw[0:2], 16) / 255.0
        g = int(raw[2:4], 16) / 255.0
        b = int(raw[4:6], 16) / 255.0
        return (max(0.0, min(1.0, r)), max(0.0, min(1.0, g)), max(0.0, min(1.0, b)))
    except ValueError:
        return (0.5, 0.5, 0.5)


def _srgb_to_hex(r: float, g: float, b: float) -> str:
    ri = max(0, min(255, int(round(max(0.0, min(1.0, r)) * 255.0))))
    gi = max(0, min(255, int(round(max(0.0, min(1.0, g)) * 255.0))))
    bi = max(0, min(255, int(round(max(0.0, min(1.0, b)) * 255.0))))
    return f"#{ri:02X}{gi:02X}{bi:02X}"


def srgb_to_lab(r: float, g: float, b: float) -> Tuple[float, float, float]:
    """Converts normalized sRGB [0.0, 1.0] to CIE L*a*b* (D65 illuminant, 2 deg observer)."""
    def _lin(c: float) -> float:
        c = max(0.0, min(1.0, float(c)))
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    rl, gl, bl = _lin(r), _lin(g), _lin(b)
    x = (0.4124564 * rl + 0.3575761 * gl + 0.1804375 * bl) / 0.95047
    y = (0.2126729 * rl + 0.7151522 * gl + 0.0721750 * bl) / 1.00000
    z = (0.0193339 * rl + 0.1191920 * gl + 0.9503041 * bl) / 1.08883

    eps = 216.0 / 24389.0
    kappa = 24389.0 / 27.0

    def _f(t: float) -> float:
        return t ** (1.0 / 3.0) if t > eps else (kappa * t + 16.0) / 116.0

    fx, fy, fz = _f(x), _f(y), _f(z)
    l_star = 116.0 * fy - 16.0
    a_star = 500.0 * (fx - fy)
    b_star = 200.0 * (fy - fz)
    return (l_star, a_star, b_star)


def compute_ciede2000(
    lab1: Tuple[float, float, float],
    lab2: Tuple[float, float, float],
    kL: float = 1.0,
    kC: float = 1.0,
    kH: float = 1.0,
) -> float:
    """Computes exact Sharma-Wu-Dalal (2005) CIEDE2000 perceptual color difference."""
    l1, a1, b1 = float(lab1[0]), float(lab1[1]), float(lab1[2])
    l2, a2, b2 = float(lab2[0]), float(lab2[1]), float(lab2[2])

    c1 = math.hypot(a1, b1)
    c2 = math.hypot(a2, b2)
    c_bar = 0.5 * (c1 + c2)
    c_bar7 = c_bar ** 7
    g = 0.5 * (1.0 - math.sqrt(c_bar7 / (c_bar7 + 25.0 ** 7))) if c_bar > 0.0 else 0.5

    a1p = (1.0 + g) * a1
    a2p = (1.0 + g) * a2
    c1p = math.hypot(a1p, b1)
    c2p = math.hypot(a2p, b2)

    def _hue_deg(ap: float, bp: float) -> float:
        if abs(ap) < 1e-12 and abs(bp) < 1e-12:
            return 0.0
        return math.degrees(math.atan2(bp, ap)) % 360.0

    h1p = _hue_deg(a1p, b1)
    h2p = _hue_deg(a2p, b2)

    dl_p = l2 - l1
    dc_p = c2p - c1p
    c_prod = c1p * c2p
    if c_prod < 1e-12:
        dh_p = 0.0
    elif abs(h2p - h1p) <= 180.0:
        dh_p = h2p - h1p
    elif (h2p - h1p) > 180.0:
        dh_p = (h2p - h1p) - 360.0
    else:
        dh_p = (h2p - h1p) + 360.0

    d_big_h_p = 2.0 * math.sqrt(c_prod) * math.sin(math.radians(dh_p * 0.5))

    l_bar_p = 0.5 * (l1 + l2)
    c_bar_p = 0.5 * (c1p + c2p)
    if c_prod < 1e-12:
        h_bar_p = h1p + h2p
    elif abs(h1p - h2p) <= 180.0:
        h_bar_p = 0.5 * (h1p + h2p)
    elif (h1p + h2p) < 360.0:
        h_bar_p = 0.5 * (h1p + h2p + 360.0)
    else:
        h_bar_p = 0.5 * (h1p + h2p - 360.0)

    t = (
        1.0
        - 0.17 * math.cos(math.radians(h_bar_p - 30.0))
        + 0.24 * math.cos(math.radians(2.0 * h_bar_p))
        + 0.32 * math.cos(math.radians(3.0 * h_bar_p + 6.0))
        - 0.20 * math.cos(math.radians(4.0 * h_bar_p - 63.0))
    )
    d_theta = 30.0 * math.exp(-(((h_bar_p - 275.0) / 25.0) ** 2))
    c_bar_p7 = c_bar_p ** 7
    r_c = 2.0 * math.sqrt(c_bar_p7 / (c_bar_p7 + 25.0 ** 7)) if c_bar_p > 0.0 else 0.0
    l_term = (l_bar_p - 50.0) ** 2
    s_l = 1.0 + (0.015 * l_term) / math.sqrt(20.0 + l_term)
    s_c = 1.0 + 0.045 * c_bar_p
    s_h = 1.0 + 0.015 * c_bar_p * t
    r_t = -math.sin(math.radians(2.0 * d_theta)) * r_c

    dl_term = dl_p / (kL * s_l)
    dc_term = dc_p / (kC * s_c)
    dh_term = d_big_h_p / (kH * s_h)
    val = dl_term ** 2 + dc_term ** 2 + dh_term ** 2 + r_t * dc_term * dh_term
    return round(math.sqrt(max(0.0, val)), 4)


def _apply_cdl_unclamped(
    r: float, g: float, b: float, cdl: AscCdlSpec
) -> Tuple[float, float, float, bool]:
    """Applies ASC CDL slope/offset/power/saturation and reports whether signal exceeds [0, 1]."""
    raw = [
        r * cdl.slope[0] + cdl.offset[0],
        g * cdl.slope[1] + cdl.offset[1],
        b * cdl.slope[2] + cdl.offset[2],
    ]
    powered = [
        (max(0.0, v) ** cdl.power[i]) if v > 0.0 else 0.0
        for i, v in enumerate(raw)
    ]
    luma = 0.2126 * powered[0] + 0.7152 * powered[1] + 0.0722 * powered[2]
    sat = cdl.saturation
    sat_rgb = [luma + sat * (p - luma) for p in powered]
    out_of_gamut = any(v < -0.02 or v > 1.02 for v in sat_rgb)
    clamped = (
        max(0.0, min(1.0, sat_rgb[0])),
        max(0.0, min(1.0, sat_rgb[1])),
        max(0.0, min(1.0, sat_rgb[2])),
    )
    return clamped[0], clamped[1], clamped[2], out_of_gamut


def _resolve_scene_kelvin(bible: MasterProductionBible, scene: ScenePromptSpec) -> float:
    blk = getattr(scene, "blocking_spec", None)
    if blk is not None and getattr(blk, "color_temp_kelvin", None) is not None:
        return float(blk.color_temp_kelvin)
    rig = getattr(scene, "lighting_rig", None) or getattr(bible, "master_lighting_rig", None)
    if rig is not None:
        for attr in ("color_temp_kelvin", "cct_kelvin", "color_temperature_k"):
            val = getattr(rig, attr, None)
            if val is not None:
                return float(val)
    return 5600.0


def _resolve_signal_standard(
    bible: MasterProductionBible, domain_profile: Optional[Dict[str, Any]]
) -> ScopeSignalStandardEnum:
    if domain_profile and domain_profile.get("signal_standard"):
        raw = str(domain_profile["signal_standard"]).strip().lower()
        try:
            return ScopeSignalStandardEnum(raw)
        except ValueError:
            pass
    look = getattr(bible, "master_color_look", None)
    disp = str(getattr(look, "target_display", "") or "").lower()
    if "p3" in disp:
        return ScopeSignalStandardEnum.P3_D65
    if "2020" in disp or "pq" in disp or "2100" in disp:
        return ScopeSignalStandardEnum.BT2020_PQ
    return ScopeSignalStandardEnum.REC709_24


def _build_waveform_16_bins(luma_min: float, luma_avg: float, luma_peak: float) -> List[float]:
    """Generates a 16-bin IRE distribution (0-100 IRE) summing to 100.0%."""
    sigma = max(8.0, (luma_peak - luma_min) * 0.28)
    raw_weights: List[float] = []
    for idx in range(16):
        bin_center = (idx + 0.5) * (100.0 / 16.0)
        if bin_center < luma_min - 6.0 or bin_center > luma_peak + 6.0:
            raw_weights.append(0.15)
        else:
            w = math.exp(-0.5 * ((bin_center - luma_avg) / sigma) ** 2)
            raw_weights.append(max(0.25, w))
    total = sum(raw_weights) or 1.0
    bins = [round((w / total) * 100.0, 2) for w in raw_weights]
    diff = round(100.0 - sum(bins), 2)
    max_idx = max(range(16), key=lambda i: bins[i])
    bins[max_idx] = round(max(0.0, bins[max_idx] + diff), 2)
    return bins


def _rgb_to_vectorscope_polar(r: float, g: float, b: float) -> Tuple[float, float]:
    """Maps normalized sRGB to Rec.709 Cb/Cr vectorscope polar coordinates (angle_deg, magnitude)."""
    cb = -0.168736 * r - 0.331264 * g + 0.5 * b
    cr = 0.5 * r - 0.418688 * g - 0.081312 * b
    angle_deg = round(math.degrees(math.atan2(cr, cb)) % 360.0, 2)
    magnitude = round(min(1.0, math.hypot(cb, cr) / 0.5), 3)
    return angle_deg, magnitude


def compile_color_scopes_manifest(
    bible: MasterProductionBible,
    domain_profile: Optional[Dict[str, Any]] = None,
) -> MasterColorScopesManifest:
    """Compiles 16-bin IRE waveform, vectorscope, CIELAB dE2000 & CDL trim manifest (PM-FEAT-039)."""
    cal = dict(domain_profile or {})
    std = _resolve_signal_standard(bible, cal)
    max_de_ceiling = float(cal.get("max_delta_e_ceiling", 3.0) or 3.0)
    max_ev_jump = float(cal.get("max_exposure_jump_stops", 0.75) or 0.75)

    palette = list(getattr(bible, "color_palette", None) or ["#2C3E50", "#475569", "#94A3B8", "#E2E8F0"])
    master_look = getattr(bible, "master_color_look", None)
    master_cdl = getattr(master_look, "cdl", None) or AscCdlSpec()

    scenes = list(getattr(bible, "scenes", None) or [])
    scene_scopes: List[SceneScopeTelemetrySpec] = []
    kelvins: Dict[int, float] = {}

    # Anchor base RGB around primary palette color blended toward neutral mid-tone
    anchor_rgb = hex_to_srgb(palette[0])

    for pos, sc in enumerate(scenes, start=1):
        sc_idx = int(getattr(sc, "scene_index", pos) or pos)
        sc_look = getattr(sc, "scene_color_look", None) or master_look
        cdl = getattr(sc_look, "cdl", None) or master_cdl
        kelvin = _resolve_scene_kelvin(bible, sc)
        kelvins[sc_idx] = kelvin

        # Blend primary anchor with subtle scene-indexed palette tint so coherent cuts remain <= 3.0 dE2000 unless CDL/Kelvin diverges
        accent_rgb = hex_to_srgb(palette[(pos - 1) % len(palette)])
        base_r = 0.985 * anchor_rgb[0] + 0.015 * accent_rgb[0]
        base_g = 0.985 * anchor_rgb[1] + 0.015 * accent_rgb[1]
        base_b = 0.985 * anchor_rgb[2] + 0.015 * accent_rgb[2]

        # Subtle Kelvin warmth/coolness shift relative to 5600K daylight
        k_norm = max(-1.0, min(1.0, (5600.0 - kelvin) / 3000.0))
        base_r = max(0.0, min(1.0, base_r + 0.03 * k_norm))
        base_b = max(0.0, min(1.0, base_b - 0.03 * k_norm))

        gr, gg, gb, oog = _apply_cdl_unclamped(base_r, base_g, base_b, cdl)
        dom_hex = _srgb_to_hex(gr, gg, gb)

        luma = 0.2126 * gr + 0.7152 * gg + 0.0722 * gb
        luma_avg = round(max(8.0, min(90.0, luma * 84.0 + 8.0)), 2)
        spread = 28.0 + min(18.0, abs(cdl.slope[0] - 1.0) * 20.0)
        luma_min = round(max(1.0, luma_avg - spread), 2)
        luma_peak = round(min(100.0, luma_avg + spread), 2)

        rgb_sum = max(1e-6, gr + gg + gb)
        r_pct = round((gr / rgb_sum) * 100.0, 2)
        g_pct = round((gg / rgb_sum) * 100.0, 2)
        b_pct = round(max(0.0, 100.0 - r_pct - g_pct), 2)

        vec_points: List[Tuple[float, float, str]] = []
        max_chroma = 0.0
        for p_hex in palette[:4]:
            pr, pg, pb = hex_to_srgb(p_hex)
            vr, vg, vb, p_oog = _apply_cdl_unclamped(pr, pg, pb, cdl)
            ang, mag = _rgb_to_vectorscope_polar(vr, vg, vb)
            max_chroma = max(max_chroma, mag)
            vec_points.append((ang, mag, _srgb_to_hex(vr, vg, vb)))
            oog = oog or p_oog

        gamut_util = round(
            104.5 if (oog or cdl.saturation > 1.85) else min(98.5, max(28.0, 42.0 + max_chroma * 52.0)),
            2,
        )

        scene_scopes.append(
            SceneScopeTelemetrySpec(
                scene_index=sc_idx,
                signal_standard=std,
                luma_min_ire=luma_min,
                luma_avg_ire=luma_avg,
                luma_peak_ire=luma_peak,
                rgb_balance_pct=(r_pct, g_pct, b_pct),
                gamut_utilization_pct=gamut_util,
                waveform_bins=_build_waveform_16_bins(luma_min, luma_avg, luma_peak),
                vectorscope_points=vec_points,
                dominant_hex=dom_hex,
            )
        )

    cut_matches: List[AdjacentCutColorMatchSpec] = []
    for i in range(len(scene_scopes) - 1):
        s1 = scene_scopes[i]
        s2 = scene_scopes[i + 1]
        lab1 = srgb_to_lab(*hex_to_srgb(s1.dominant_hex))
        lab2 = srgb_to_lab(*hex_to_srgb(s2.dominant_hex))
        de = round(compute_ciede2000(lab1, lab2), 2)
        ev_delta = round(math.log2(max(1.0, s2.luma_avg_ire) / max(1.0, s1.luma_avg_ire)), 2)
        k_delta = round(abs(kelvins.get(s2.scene_index, 5600.0) - kelvins.get(s1.scene_index, 5600.0)), 1)

        r1, g1, b1 = hex_to_srgb(s1.dominant_hex)
        r2, g2, b2 = hex_to_srgb(s2.dominant_hex)
        cdl_offset = (
            round(max(-0.25, min(0.25, r1 - r2)), 4),
            round(max(-0.25, min(0.25, g1 - g2)), 4),
            round(max(-0.25, min(0.25, b1 - b2)), 4),
        )

        if s1.gamut_utilization_pct > 100.0 or s2.gamut_utilization_pct > 100.0:
            status = ShotMatchStatusEnum.OUT_OF_GAMUT
            note = f"Gamut overshoot detected ({max(s1.gamut_utilization_pct, s2.gamut_utilization_pct):.1f}% > 100%)."
        elif de > max_de_ceiling or abs(ev_delta) > max_ev_jump:
            status = ShotMatchStatusEnum.TRIM_RECOMMENDED
            note = f"Apply CDL offset {cdl_offset} to bring dE2000={de:.2f} / EV={ev_delta:+.2f} within tolerance."
        else:
            status = ShotMatchStatusEnum.MATCHED
            note = "Adjacent cut within CIEDE2000 & exposure continuity tolerances."

        cut_matches.append(
            AdjacentCutColorMatchSpec(
                from_scene_index=s1.scene_index,
                to_scene_index=s2.scene_index,
                delta_e_2000=de,
                exposure_delta_stops=ev_delta,
                kelvin_delta_k=k_delta,
                recommended_cdl_offset=cdl_offset,
                match_status=status,
                notes=note,
            )
        )

    mean_de = round(sum(c.delta_e_2000 for c in cut_matches) / len(cut_matches), 2) if cut_matches else 0.0
    all_matched = all(c.match_status == ShotMatchStatusEnum.MATCHED for c in cut_matches) and all(
        s.gamut_utilization_pct <= 100.0 for s in scene_scopes
    )
    title_slug = str(getattr(bible, "project_title", "omni") or "omni")
    mid = f"scopes-{hashlib.sha256(f'{title_slug}:{std.value}:{len(scene_scopes)}'.encode()).hexdigest()[:8]}"

    manifest = MasterColorScopesManifest(
        manifest_id=mid,
        signal_standard=std,
        max_delta_e_ceiling=max_de_ceiling,
        max_exposure_jump_stops=max_ev_jump,
        mean_delta_e_2000=mean_de,
        all_cuts_matched=all_matched,
        scene_scopes=scene_scopes,
        cut_matches=cut_matches,
        scopes_token="",
    )
    manifest.scopes_token = format_color_scopes_token(manifest, scene_scopes[0].scene_index if scene_scopes else 1)
    return manifest


def synthesize_default_color_scopes_manifest(bible: MasterProductionBible) -> MasterColorScopesManifest:
    """Synthesizes default Digital Colorimetry Scopes Manifest for a MasterProductionBible."""
    return compile_color_scopes_manifest(bible)


def format_color_scopes_token(manifest: MasterColorScopesManifest, scene_index: int = 1) -> str:
    """Formats the machine telemetry token for PM-FEAT-039 digital colorimetry scopes."""
    sc_scope = next((s for s in manifest.scene_scopes if s.scene_index == scene_index), None)
    if sc_scope is None and manifest.scene_scopes:
        sc_scope = manifest.scene_scopes[0]

    std_val = manifest.signal_standard.value if hasattr(manifest.signal_standard, "value") else str(manifest.signal_standard)
    avg_ire = sc_scope.luma_avg_ire if sc_scope else 48.0

    cut = next((c for c in manifest.cut_matches if c.to_scene_index == scene_index), None)
    if cut is None and scene_index == 1 and manifest.cut_matches:
        cut = manifest.cut_matches[0]

    de_val = cut.delta_e_2000 if cut else manifest.mean_delta_e_2000
    ev_val = cut.exposure_delta_stops if cut else 0.0
    if sc_scope and sc_scope.gamut_utilization_pct > 100.0:
        status_val = ShotMatchStatusEnum.OUT_OF_GAMUT.value
    elif cut is not None:
        status_val = cut.match_status.value if hasattr(cut.match_status, "value") else str(cut.match_status)
    else:
        status_val = ShotMatchStatusEnum.MATCHED.value

    return (
        f"[COLOR-SCOPES: SC{scene_index:02d} | std={std_val} | avg_ire={avg_ire:.1f} | "
        f"dE2000={de_val:.2f} | ev_delta={ev_val:+.2f}EV | status={status_val}]"
    )


def export_color_scopes_json(manifest: MasterColorScopesManifest) -> str:
    """Serializes MasterColorScopesManifest to formatted JSON."""
    return manifest.model_dump_json(indent=2)


def export_shot_match_cdl_csv(manifest: MasterColorScopesManifest) -> str:
    """Exports adjacent-cut CIEDE2000, exposure stop deltas, and CDL trim offsets as CSV."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "from_scene_index",
        "to_scene_index",
        "delta_e_2000",
        "exposure_delta_stops",
        "kelvin_delta_k",
        "cdl_offset_r",
        "cdl_offset_g",
        "cdl_offset_b",
        "match_status",
        "notes",
    ])
    for cm in manifest.cut_matches:
        st = cm.match_status.value if hasattr(cm.match_status, "value") else str(cm.match_status)
        writer.writerow([
            cm.from_scene_index,
            cm.to_scene_index,
            f"{cm.delta_e_2000:.2f}",
            f"{cm.exposure_delta_stops:+.2f}",
            f"{cm.kelvin_delta_k:.1f}",
            f"{cm.recommended_cdl_offset[0]:+.4f}",
            f"{cm.recommended_cdl_offset[1]:+.4f}",
            f"{cm.recommended_cdl_offset[2]:+.4f}",
            st,
            cm.notes,
        ])
    return buf.getvalue()


def export_finishing_scopes_qc_md(
    manifest: MasterColorScopesManifest,
    bible: Optional[MasterProductionBible] = None,
) -> str:
    """Exports a human-readable Markdown finishing colorimetry QC report."""
    title = str(getattr(bible, "project_title", manifest.manifest_id) or manifest.manifest_id)
    std_val = manifest.signal_standard.value if hasattr(manifest.signal_standard, "value") else str(manifest.signal_standard)
    lines: List[str] = [
        f"# Digital Colorimetry Scopes & Shot-Match QC Report — {title}",
        "",
        f"- **Manifest ID**: `{manifest.manifest_id}`",
        f"- **Signal Standard**: `{std_val}`",
        f"- **Mean CIEDE2000**: `{manifest.mean_delta_e_2000:.2f}` (Ceiling `<= {manifest.max_delta_e_ceiling:.2f}`)",
        f"- **Max Exposure Jump**: `<= {manifest.max_exposure_jump_stops:.2f} EV`",
        f"- **All Cuts Matched**: `{'PASS' if manifest.all_cuts_matched else 'TRIM_REQUIRED'}`",
        "",
        "## Per-Scene Waveform & Gamut Telemetry",
        "",
        "| Scene | Min IRE | Avg IRE | Peak IRE | RGB Balance (%) | Gamut Util (%) | Dominant Hex |",
        "|---:|---:|---:|---:|---|---:|---|",
    ]
    for sc in manifest.scene_scopes:
        rgb_s = f"{sc.rgb_balance_pct[0]:.1f} / {sc.rgb_balance_pct[1]:.1f} / {sc.rgb_balance_pct[2]:.1f}"
        lines.append(
            f"| {sc.scene_index} | {sc.luma_min_ire:.1f} | {sc.luma_avg_ire:.1f} | "
            f"{sc.luma_peak_ire:.1f} | {rgb_s} | {sc.gamut_utilization_pct:.1f}% | `{sc.dominant_hex}` |"
        )
    lines.extend([
        "",
        "## Adjacent-Cut Shot-Match Deltas",
        "",
        "| Cut | dE2000 | EV Delta | Kelvin Delta | CDL Offset (R, G, B) | Status |",
        "|---|---:|---:|---:|---|---|",
    ])
    for cm in manifest.cut_matches:
        st = cm.match_status.value if hasattr(cm.match_status, "value") else str(cm.match_status)
        off_s = f"({cm.recommended_cdl_offset[0]:+.4f}, {cm.recommended_cdl_offset[1]:+.4f}, {cm.recommended_cdl_offset[2]:+.4f})"
        lines.append(
            f"| SC{cm.from_scene_index:02d} -> SC{cm.to_scene_index:02d} | {cm.delta_e_2000:.2f} | "
            f"{cm.exposure_delta_stops:+.2f} EV | {cm.kelvin_delta_k:.0f} K | `{off_s}` | `{st}` |"
        )
    lines.append("")
    return "\n".join(lines)


def export_color_scopes_bundle(
    bible: MasterProductionBible,
    output_dir: Union[str, Path],
    manifest: Optional[MasterColorScopesManifest] = None,
) -> Dict[str, Path]:
    """Writes color_continuity_scopes.json, shot_match_cdl_deltas.csv, and finishing_scopes_qc.md."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    resolved = manifest or getattr(bible, "master_color_scopes", None) or compile_color_scopes_manifest(bible)

    json_path = out_path / "color_continuity_scopes.json"
    csv_path = out_path / "shot_match_cdl_deltas.csv"
    md_path = out_path / "finishing_scopes_qc.md"

    json_path.write_text(export_color_scopes_json(resolved), encoding="utf-8")
    csv_path.write_text(export_shot_match_cdl_csv(resolved), encoding="utf-8")
    md_path.write_text(export_finishing_scopes_qc_md(resolved, bible), encoding="utf-8")

    return {
        "color_continuity_scopes_json": json_path,
        "shot_match_cdl_deltas_csv": csv_path,
        "finishing_scopes_qc_md": md_path,
    }


__all__ = [
    "hex_to_srgb",
    "srgb_to_lab",
    "compute_ciede2000",
    "compile_color_scopes_manifest",
    "synthesize_default_color_scopes_manifest",
    "format_color_scopes_token",
    "export_color_scopes_json",
    "export_shot_match_cdl_csv",
    "export_finishing_scopes_qc_md",
    "export_color_scopes_bundle",
]
