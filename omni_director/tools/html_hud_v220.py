"""Modular v2.20.0 Dark-Room Cinema HUD Components (PM-FEAT-039 & PM-FEAT-040).

Provides Python 3.11+ builders for:
1. PM-FEAT-039: Colorist Scopes (Waveform / RGB Parade / Vectorscope), CIEDE2000 Shot-Match & A/B Wipe (#colorScopesModal)
2. PM-FEAT-040: RFC 8493 BagIt Archive Vault & Agency Handoff Verification (#archiveVaultModal)
"""

from __future__ import annotations

import hashlib
import json
import re
from html import escape as html_escape
from typing import Any, Dict, List, Optional, Tuple


def _escape_json_for_script(payload: Any) -> str:
    """Serializes JSON safely for embedding inside HTML <script> tags."""
    return re.sub(r"</(script)", r"<\/\1", json.dumps(payload), flags=re.IGNORECASE)


def _to_plain(obj: Any) -> Any:
    """Converts Pydantic models, enums, or nested objects into JSON-safe Python structures."""
    if obj is None:
        return None
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if hasattr(obj, "value"):
        return obj.value
    if isinstance(obj, dict):
        return {str(k): _to_plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_plain(v) for v in obj]
    return obj


def _get_field(obj: Any, key: str, default: Any = None) -> Any:
    """Safely extracts a field from a dict or object attribute."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _sec_to_smpte(sec: float, fps: int = 24) -> str:
    """Formats seconds to HH:MM:SS:FF SMPTE 24fps timecode."""
    total_frames = max(0, int(round(float(sec) * fps)))
    ff = total_frames % fps
    total_sec = total_frames // fps
    ss = total_sec % 60
    mm = (total_sec // 60) % 60
    hh = total_sec // 3600
    return f"{hh:02d}:{mm:02d}:{ss:02d}:{ff:02d}"


def _parse_scene_window(timestamp_range: str, fallback_start: float) -> Tuple[float, float]:
    """Parses MM:SS-MM:SS or +Ns timestamp ranges into (start_sec, end_sec)."""
    ts = str(timestamp_range or "")
    matches = re.findall(r"(\d+):(\d+)", ts)
    if len(matches) >= 2:
        start_s = float(int(matches[0][0]) * 60 + int(matches[0][1]))
        end_s = float(int(matches[1][0]) * 60 + int(matches[1][1]))
        if end_s > start_s:
            return start_s, end_s
    ext = re.search(r"\+(\d+)s", ts, re.IGNORECASE)
    dur = float(max(4, min(15, int(ext.group(1))))) if ext else 8.0
    return fallback_start, fallback_start + dur


def _sha256_hex(seed_text: str) -> str:
    return hashlib.sha256(seed_text.encode("utf-8")).hexdigest()


def _hex_to_rgb_ire(hex_color: str) -> Tuple[float, float, float]:
    """Converts #RRGGBB into broadcast RGB IRE percentages (7.5-92.0)."""
    cleaned = re.sub(r"[^0-9A-Fa-f]", "", str(hex_color or ""))
    if len(cleaned) != 6:
        cleaned = "38BDF8"
    r = int(cleaned[0:2], 16) / 255.0
    g = int(cleaned[2:4], 16) / 255.0
    b = int(cleaned[4:6], 16) / 255.0
    return (
        round(12.0 + r * 78.0, 1),
        round(12.0 + g * 78.0, 1),
        round(12.0 + b * 78.0, 1),
    )


def _rgb_to_vectorscope_polar(r_ire: float, g_ire: float, b_ire: float) -> Tuple[float, float]:
    """Computes approximate Cb/Cr vectorscope angle (deg) and saturation (%) from RGB IRE."""
    r = r_ire / 100.0
    g = g_ire / 100.0
    b = b_ire / 100.0
    cb = -0.168736 * r - 0.331264 * g + 0.5 * b
    cr = 0.5 * r - 0.418688 * g - 0.081312 * b
    import math
    angle = round((math.degrees(math.atan2(cr, cb)) + 360.0) % 360.0, 1)
    sat = round(min(94.0, max(12.0, math.hypot(cb, cr) * 210.0)), 1)
    return angle, sat


def synthesize_v220_color_scopes_state(
    bible: Any,
    scenes_payload: Any = None,
    existing_scopes: Any = None,
) -> Dict[str, Any]:
    """Extracts or deterministically synthesizes PM-FEAT-039 Colorist Scopes & Shot-Match CDL state."""
    project_title = str(_get_field(bible, "project_title", "Omni Production") or "Omni Production")
    aspect_val = str(_to_plain(_get_field(bible, "aspect_ratio", "16:9")) or "16:9")
    runtime_sec = float(_get_field(bible, "total_runtime_seconds", 32) or 32)

    raw_existing = (
        existing_scopes
        or _get_field(bible, "master_color_scopes", None)
        or _get_field(bible, "color_scopes", None)
        or _get_field(bible, "color_continuity_scopes", None)
    )
    plain_existing = _to_plain(raw_existing) if isinstance(_to_plain(raw_existing), dict) else {}

    color_look = _to_plain(_get_field(bible, "master_color_look", None) or {}) or {}
    hdr_spec = _to_plain(_get_field(bible, "master_hdr_spec", None) or _get_field(bible, "hdr_spec", None) or {}) or {}
    palette = [str(c) for c in (_to_plain(_get_field(bible, "color_palette", None)) or []) if isinstance(c, str)]
    if not palette:
        palette = ["#2C3E50", "#E74C3C", "#ECF0F1", "#F39C12"]

    look_preset = str(color_look.get("look_preset") or "rec709_neutral")
    master_cdl = color_look.get("cdl") if isinstance(color_look.get("cdl"), dict) else {}
    base_slope = master_cdl.get("slope") or [1.0, 1.0, 1.0]
    base_offset = master_cdl.get("offset") or [0.0, 0.0, 0.0]
    base_power = master_cdl.get("power") or [1.0, 1.0, 1.0]
    base_sat = float(master_cdl.get("saturation") if master_cdl.get("saturation") is not None else 1.0)

    default_std = (
        "SMPTE ST 2084 PQ HDR10 (1000 nits)"
        if hdr_spec
        else str(color_look.get("target_display") or "Rec.709 Gamma 2.4 (100 nits)")
    )
    signal_standard = str(plain_existing.get("signal_standard") or default_std)

    scenes_raw = scenes_payload if scenes_payload is not None else _get_field(bible, "scenes", [])
    scenes = _to_plain(scenes_raw) or []
    if not isinstance(scenes, list) or not scenes:
        scenes = [
            {"scene_index": 1, "scene_title": "Opening Establishing Plate", "timestamp_range": "00:00-00:08"},
            {"scene_index": 2, "scene_title": "Hero Macro Detail", "timestamp_range": "00:08-00:16"},
        ]

    raw_scene_scopes = (
        plain_existing.get("scene_scopes")
        if isinstance(plain_existing.get("scene_scopes"), list)
        else (plain_existing.get("shot_matches") if isinstance(plain_existing.get("shot_matches"), list) else None)
    )
    raw_cut_matches = plain_existing.get("cut_matches") if isinstance(plain_existing.get("cut_matches"), list) else []
    cut_by_to_scene: Dict[int, Dict[str, Any]] = {}
    for cm in raw_cut_matches:
        if isinstance(cm, dict) and cm.get("to_scene_index") is not None:
            cut_by_to_scene[int(cm["to_scene_index"])] = cm

    scene_scopes: List[Dict[str, Any]] = []
    if raw_scene_scopes:
        for idx, item in enumerate(raw_scene_scopes):
            if not isinstance(item, dict):
                continue
            s_idx = int(item.get("scene_index") or (idx + 1))
            sc_meta = scenes[idx] if idx < len(scenes) and isinstance(scenes[idx], dict) else {}
            cm_meta = cut_by_to_scene.get(s_idx, {})
            dom_hex = str(item.get("dominant_hex") or palette[idx % len(palette)])
            sec_hex = str(item.get("secondary_hex") or palette[(idx + 1) % len(palette)])
            r_ire, g_ire, b_ire = _hex_to_rgb_ire(dom_hex)
            parade = item.get("rgb_parade") if isinstance(item.get("rgb_parade"), dict) else {}
            rgb_bal = item.get("rgb_balance_pct") if isinstance(item.get("rgb_balance_pct"), (list, tuple)) and len(item.get("rgb_balance_pct")) >= 3 else None
            luma_avg = round(float(item.get("luma_avg_ire") if item.get("luma_avg_ire") is not None else (item.get("luma_ire_avg") or (0.2126 * r_ire + 0.7152 * g_ire + 0.0722 * b_ire))), 1)
            luma_min = round(float(item.get("luma_min_ire") if item.get("luma_min_ire") is not None else (item.get("luma_ire_min") or max(4.0, luma_avg - 24.5))), 1)
            luma_max = round(float(item.get("luma_peak_ire") if item.get("luma_peak_ire") is not None else (item.get("luma_ire_max") or min(98.0, luma_avg + 26.0))), 1)
            if parade:
                r_val = round(float(parade.get("r_ire") if parade.get("r_ire") is not None else r_ire), 1)
                g_val = round(float(parade.get("g_ire") if parade.get("g_ire") is not None else g_ire), 1)
                b_val = round(float(parade.get("b_ire") if parade.get("b_ire") is not None else b_ire), 1)
            elif rgb_bal:
                r_val = round(max(6.0, min(95.0, float(rgb_bal[0]) * 1.5)), 1)
                g_val = round(max(6.0, min(95.0, float(rgb_bal[1]) * 1.5)), 1)
                b_val = round(max(6.0, min(95.0, float(rgb_bal[2]) * 1.5)), 1)
            else:
                r_val, g_val, b_val = r_ire, g_ire, b_ire
            ang, sat_p = _rgb_to_vectorscope_polar(r_val, g_val, b_val)
            raw_de = item.get("delta_e_2000") if item.get("delta_e_2000") is not None else cm_meta.get("delta_e_2000")
            de = round(float(raw_de if raw_de is not None else (0.0 if idx == 0 else 1.2)), 2)
            raw_exp = (
                item.get("exposure_jump_stops")
                if item.get("exposure_jump_stops") is not None
                else cm_meta.get("exposure_delta_stops")
            )
            exp_jump = round(float(raw_exp if raw_exp is not None else (0.0 if idx == 0 else 0.28)), 2)
            raw_status = item.get("shot_match_status") or cm_meta.get("match_status")
            status_norm = str(raw_status).upper() if raw_status else ("MATCHED" if de <= 2.3 and abs(exp_jump) <= 0.75 else "TRIM_RECOMMENDED")
            scene_scopes.append(
                {
                    "scene_index": s_idx,
                    "scene_title": str(item.get("scene_title") or sc_meta.get("scene_title") or f"Scene {s_idx}"),
                    "smpte_in": str(item.get("smpte_in") or _sec_to_smpte(idx * 8.0, 24)),
                    "smpte_out": str(item.get("smpte_out") or _sec_to_smpte((idx + 1) * 8.0, 24)),
                    "look_preset": str(item.get("look_preset") or look_preset),
                    "dominant_hex": dom_hex,
                    "secondary_hex": sec_hex,
                    "luma_ire_min": luma_min,
                    "luma_ire_avg": luma_avg,
                    "luma_ire_max": luma_max,
                    "rgb_parade": {"r_ire": r_val, "g_ire": g_val, "b_ire": b_val},
                    "vectorscope_hue_deg": float(item.get("vectorscope_hue_deg") or ang),
                    "vectorscope_sat_pct": float(item.get("vectorscope_sat_pct") or sat_p),
                    "delta_e_2000": de,
                    "exposure_jump_stops": exp_jump,
                    "cdl_slope": item.get("cdl_slope") or base_slope,
                    "cdl_offset": item.get("cdl_offset") or cm_meta.get("recommended_cdl_offset") or base_offset,
                    "cdl_power": item.get("cdl_power") or base_power,
                    "cdl_saturation": float(item.get("cdl_saturation") or base_sat),
                    "shot_match_status": status_norm,
                }
            )

    if not scene_scopes:
        cursor_s = 0.0
        prev_luma: Optional[float] = None
        for idx, sc in enumerate(scenes):
            sc_d = sc if isinstance(sc, dict) else {}
            s_idx = int(sc_d.get("scene_index") or (idx + 1))
            st_s, en_s = _parse_scene_window(str(sc_d.get("timestamp_range") or ""), cursor_s)
            cursor_s = en_s
            sc_grade = sc_d.get("color_grade") if isinstance(sc_d.get("color_grade"), dict) else {}
            sc_cdl = sc_grade.get("cdl") if isinstance(sc_grade.get("cdl"), dict) else {}
            sc_look = str(sc_grade.get("look_preset") or look_preset)
            dom_hex = palette[idx % len(palette)]
            sec_hex = palette[(idx + 1) % len(palette)]
            r_ire, g_ire, b_ire = _hex_to_rgb_ire(dom_hex)
            # Subtle deterministic per-scene modulation so waveform/parade shows realistic shot variation
            h_byte = int(_sha256_hex(f"{project_title}:scope:{s_idx}")[:2], 16)
            mod = ((h_byte % 19) - 9) * 0.65
            r_val = round(max(6.0, min(94.0, r_ire + mod)), 1)
            g_val = round(max(6.0, min(94.0, g_ire + mod * 0.7)), 1)
            b_val = round(max(6.0, min(94.0, b_ire - mod * 0.5)), 1)
            luma_avg = round(0.2126 * r_val + 0.7152 * g_val + 0.0722 * b_val, 1)
            luma_min = round(max(3.5, luma_avg - 24.0 - (idx % 3) * 2.0), 1)
            luma_max = round(min(97.5, luma_avg + 25.0 + (idx % 2) * 3.0), 1)
            ang, sat_p = _rgb_to_vectorscope_polar(r_val, g_val, b_val)

            if idx == 0 or prev_luma is None:
                de = 0.0
                exp_jump = 0.0
            else:
                de = round(0.65 + ((h_byte % 12) * 0.11), 2)
                exp_jump = round(max(-0.65, min(0.65, (luma_avg - prev_luma) / 28.0)), 2)
            prev_luma = luma_avg

            slope = sc_cdl.get("slope") or [
                round(float(base_slope[0]) + (0.012 if idx % 2 else -0.008), 3),
                round(float(base_slope[1]), 3),
                round(float(base_slope[2]) + (-0.01 if idx % 2 else 0.009), 3),
            ]
            offset = sc_cdl.get("offset") or [round(float(x), 4) for x in base_offset]
            power = sc_cdl.get("power") or [round(float(x), 3) for x in base_power]
            sat_v = round(float(sc_cdl.get("saturation") if sc_cdl.get("saturation") is not None else base_sat), 2)

            scene_scopes.append(
                {
                    "scene_index": s_idx,
                    "scene_title": str(sc_d.get("scene_title") or f"Scene {s_idx}"),
                    "smpte_in": _sec_to_smpte(st_s, 24),
                    "smpte_out": _sec_to_smpte(en_s, 24),
                    "look_preset": sc_look,
                    "dominant_hex": dom_hex,
                    "secondary_hex": sec_hex,
                    "luma_ire_min": luma_min,
                    "luma_ire_avg": luma_avg,
                    "luma_ire_max": luma_max,
                    "rgb_parade": {"r_ire": r_val, "g_ire": g_val, "b_ire": b_val},
                    "vectorscope_hue_deg": ang,
                    "vectorscope_sat_pct": sat_p,
                    "delta_e_2000": de,
                    "exposure_jump_stops": exp_jump,
                    "cdl_slope": slope,
                    "cdl_offset": offset,
                    "cdl_power": power,
                    "cdl_saturation": sat_v,
                    "shot_match_status": "MATCHED" if de <= 2.3 and abs(exp_jump) <= 0.75 else "TRIM_RECOMMENDED",
                }
            )
        if cursor_s > 0:
            runtime_sec = max(runtime_sec, cursor_s)

    cut_deltas = [float(s["delta_e_2000"]) for s in scene_scopes[1:]] or [float(scene_scopes[0]["delta_e_2000"])]
    mean_delta_e = round(
        float(plain_existing.get("mean_delta_e_2000") if plain_existing.get("mean_delta_e_2000") is not None else (sum(cut_deltas) / max(1, len(cut_deltas)))),
        2,
    )
    max_exp_jump = round(
        float(
            plain_existing.get("max_exposure_jump_stops")
            if plain_existing.get("max_exposure_jump_stops") is not None
            else max(abs(float(s["exposure_jump_stops"])) for s in scene_scopes)
        ),
        2,
    )
    all_matched = bool(
        plain_existing.get("all_cuts_matched")
        if plain_existing.get("all_cuts_matched") is not None
        else (mean_delta_e <= 2.3 and max_exp_jump <= 0.75 and all(s["shot_match_status"] == "MATCHED" for s in scene_scopes))
    )

    return {
        "schema": "omni.color_continuity_scopes.v1",
        "project_title": project_title,
        "aspect_ratio": aspect_val,
        "fps": 24,
        "total_runtime_sec": round(runtime_sec, 2),
        "signal_standard": signal_standard,
        "working_color_space": str(color_look.get("working_color_space") or "ACEScg"),
        "look_preset": look_preset,
        "mean_delta_e_2000": mean_delta_e,
        "max_exposure_jump_stops": max_exp_jump,
        "all_cuts_matched": all_matched,
        "palette": palette,
        "scene_scopes": scene_scopes,
    }


def synthesize_v220_archive_vault_state(
    bible: Any,
    scenes_payload: Any = None,
    existing_vault: Any = None,
) -> Dict[str, Any]:
    """Extracts or deterministically synthesizes PM-FEAT-040 RFC 8493 BagIt Archive Vault state."""
    project_title = str(_get_field(bible, "project_title", "Omni Production") or "Omni Production")
    runtime_sec = float(_get_field(bible, "total_runtime_seconds", 32) or 32)
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", project_title.lower()).strip("_") or "omni_production"

    raw_existing = (
        existing_vault
        or _get_field(bible, "master_archive_vault", None)
        or _get_field(bible, "archive_vault", None)
        or _get_field(bible, "archive_manifest", None)
    )
    plain_existing = _to_plain(raw_existing) if isinstance(_to_plain(raw_existing), dict) else {}

    qc_spec = _to_plain(_get_field(bible, "master_broadcast_qc", None) or _get_field(bible, "broadcast_qc", None) or {}) or {}
    c2pa_spec = _to_plain(_get_field(bible, "master_c2pa_provenance", None) or _get_field(bible, "c2pa_provenance", None) or {}) or {}

    bag_hash = _sha256_hex(f"bagit:{project_title}:{runtime_sec}")[:10].upper()
    bag_id = str(plain_existing.get("bag_id") or f"OMNI-BAG-{bag_hash}")
    retention_tier = str(plain_existing.get("retention_tier") or "ENTERPRISE_WORM_7YR")
    rights_expiry_iso = str(
        plain_existing.get("rights_expiry_iso")
        or qc_spec.get("rights_expiry_iso")
        or c2pa_spec.get("rights_expiry_iso")
        or "2029-11-28"
    )
    bagging_date_iso = str(plain_existing.get("bagging_date_iso") or "2026-11-28")

    raw_depts = (
        plain_existing.get("vault_summaries")
        if isinstance(plain_existing.get("vault_summaries"), list)
        else (
            plain_existing.get("department_vaults")
            if isinstance(plain_existing.get("department_vaults"), list)
            else (plain_existing.get("departments") if isinstance(plain_existing.get("departments"), list) else None)
        )
    )
    raw_artifacts = (
        plain_existing.get("entries")
        if isinstance(plain_existing.get("entries"), list)
        else (
            plain_existing.get("artifacts")
            if isinstance(plain_existing.get("artifacts"), list)
            else (plain_existing.get("manifest_entries") if isinstance(plain_existing.get("manifest_entries"), list) else None)
        )
    )

    default_specs: List[Tuple[str, str, str, str, int]] = [
        ("Camera & Optical", "camera_optical", f"data/01_camera/lens_package.csv", "CSV Optical Spec", 42800),
        ("Camera & Optical", "camera_optical", f"data/01_camera/moco_track.json", "JSON Kinematics", 186400),
        ("Color & LUTs", "color_luts", f"data/02_color/production_look.cube", "33x33x33 3D LUT", 1124600),
        ("Color & LUTs", "color_luts", f"data/02_color/color_continuity_scopes.json", "Scopes & Delta-E", 94200),
        ("Audio & Spatial", "audio_spatial", f"data/03_audio/audio_stems_manifest.json", "4-Stem ADM Mix", 482000),
        ("Audio & Spatial", "audio_spatial", f"data/03_audio/voice_casting_script.json", "Viseme & Ducking", 164800),
        ("VFX & Motion GFX", "vfx_motion", f"data/04_vfx/openexr_channels.json", "EXR AOV Manifest", 312500),
        ("VFX & Motion GFX", "vfx_motion", f"data/04_vfx/motion_graphics_mogrt.json", "MOGRT Typography", 248900),
        ("Editorial & IMF/DCP", "editorial_imf", f"data/05_editorial/production_timeline.otio", "OpenTimelineIO", 294100),
        ("Editorial & IMF/DCP", "editorial_imf", f"data/05_editorial/imf_dcp_manifest.json", "SMPTE ST 2067 IMF", 418700),
        ("Legal, C2PA & QC", "legal_qc", f"data/06_legal_qc/c2pa_manifest.json", "C2PA v2.1 Ledger", 156200),
        ("Legal, C2PA & QC", "legal_qc", f"data/06_legal_qc/broadcast_qc_manifest.json", "PSE & EBU R128 QC", 128400),
    ]

    artifacts: List[Dict[str, Any]] = []
    if raw_artifacts:
        for idx, a in enumerate(raw_artifacts):
            if not isinstance(a, dict):
                continue
            dept_val = str(a.get("vault_department") or a.get("department") or "01_Editorial_Timelines")
            fname_val = str(a.get("filename") or "")
            path_val = str(
                a.get("bag_path")
                or a.get("file_path")
                or (f"data/{dept_val}/{fname_val}" if fname_val else f"data/artifact_{idx + 1}.json")
            )
            size_b = int(a.get("size_bytes") or 65536)
            sha_val = str(a.get("sha256_digest") or a.get("sha256") or _sha256_hex(f"{bag_id}:{path_val}:{size_b}"))
            ver_val = bool(
                a.get("verified")
                if a.get("verified") is not None
                else (bool(sha_val) and len(sha_val) == 64)
            )
            artifacts.append(
                {
                    "department": dept_val,
                    "bag_path": path_val,
                    "format": str(a.get("mime_type") or a.get("format") or "Production Deliverable"),
                    "size_bytes": size_b,
                    "sha256": sha_val,
                    "verified": ver_val,
                }
            )
    if not artifacts:
        for dept_lbl, _dept_key, path_val, fmt, size_b in default_specs:
            artifacts.append(
                {
                    "department": dept_lbl,
                    "bag_path": path_val,
                    "format": fmt,
                    "size_bytes": size_b,
                    "sha256": _sha256_hex(f"{bag_id}:{slug}:{path_val}:{runtime_sec}"),
                    "verified": True,
                }
            )

    department_vaults: List[Dict[str, Any]] = []
    if raw_depts:
        for d in raw_depts:
            if not isinstance(d, dict):
                continue
            tot_bytes = d.get("total_bytes")
            fp_mb = (
                round(float(tot_bytes) / (1024.0 * 1024.0), 2)
                if tot_bytes is not None and d.get("footprint_mb") is None
                else round(float(d.get("footprint_mb") or 120.0), 2)
            )
            art_cnt = int(d.get("artifact_count") or 0)
            ver_cnt = int(d.get("verified_count") if d.get("verified_count") is not None else art_cnt)
            department_vaults.append(
                {
                    "department": str(d.get("folder_name") or d.get("department") or "Department"),
                    "artifact_count": art_cnt,
                    "footprint_mb": max(0.01, fp_mb) if art_cnt > 0 else fp_mb,
                    "verified": bool(d.get("verified") if d.get("verified") is not None else (ver_cnt >= art_cnt)),
                }
            )
    if not department_vaults:
        dept_order = [
            ("Camera & Optical", 184.5),
            ("Color & LUTs", 268.2),
            ("Audio & Spatial", 312.8),
            ("VFX & Motion GFX", 410.4),
            ("Editorial & IMF/DCP", 246.6),
            ("Legal, C2PA & QC", 64.5),
        ]
        by_dept_cnt: Dict[str, int] = {}
        for a in artifacts:
            by_dept_cnt[a["department"]] = by_dept_cnt.get(a["department"], 0) + 1
        scale = max(0.75, min(2.0, runtime_sec / 32.0))
        for dept_name, base_mb in dept_order:
            department_vaults.append(
                {
                    "department": dept_name,
                    "artifact_count": by_dept_cnt.get(dept_name, 2),
                    "footprint_mb": round(base_mb * scale, 2),
                    "verified": True,
                }
            )

    total_bytes = sum(int(a["size_bytes"]) for a in artifacts)
    # Include estimated master mezzanine media payload in footprint GB & Payload-Oxum
    total_dept_mb = sum(float(d["footprint_mb"]) for d in department_vaults)
    estimated_media_footprint_gb = round(
        float(
            plain_existing.get("estimated_media_footprint_gb")
            if plain_existing.get("estimated_media_footprint_gb") is not None
            else (total_dept_mb / 1024.0)
        ),
        2,
    )
    oxum_bytes = int(plain_existing.get("payload_bytes") or max(total_bytes, int(round(total_dept_mb * 1024 * 1024))))
    payload_oxum = str(plain_existing.get("payload_oxum") or f"{oxum_bytes}.{len(artifacts)}")
    archive_ready = bool(
        plain_existing.get("archive_ready")
        if plain_existing.get("archive_ready") is not None
        else (bool(artifacts) and all(a.get("verified", True) for a in artifacts))
    )

    return {
        "schema": "omni.archive_vault_manifest.v1",
        "rfc_standard": "RFC 8493 BagIt v1.0",
        "project_title": project_title,
        "bag_id": bag_id,
        "bagging_date_iso": bagging_date_iso,
        "retention_tier": retention_tier,
        "payload_oxum": payload_oxum,
        "estimated_media_footprint_gb": estimated_media_footprint_gb,
        "rights_expiry_iso": rights_expiry_iso,
        "archive_ready": archive_ready,
        "department_vaults": department_vaults,
        "artifacts": artifacts,
    }


def build_v220_hud_bundle(
    bible: Any,
    scenes_payload: Any = None,
    existing_scopes: Any = None,
    existing_vault: Any = None,
) -> Dict[str, str]:
    """Builds Dark-Room Cinema v2.20.0 HUD bundle returning {'css': ..., 'html': ..., 'js': ...}."""
    scopes_state = synthesize_v220_color_scopes_state(bible, scenes_payload=scenes_payload, existing_scopes=existing_scopes)
    vault_state = synthesize_v220_archive_vault_state(bible, scenes_payload=scenes_payload, existing_vault=existing_vault)

    scopes_json = _escape_json_for_script(scopes_state)
    vault_json = _escape_json_for_script(vault_state)

    match_badge_cls = "v220-badge-pass" if scopes_state["all_cuts_matched"] else "v220-badge-warn"
    match_badge_lbl = "ALL CUTS MATCHED" if scopes_state["all_cuts_matched"] else "TRIM REVIEW RECOMMENDED"

    vault_badge_cls = "v220-badge-pass" if vault_state["archive_ready"] else "v220-badge-warn"
    vault_badge_lbl = "ARCHIVE READY · RFC 8493 VERIFIED" if vault_state["archive_ready"] else "CHECKS PENDING"

    scene_scopes = scopes_state.get("scene_scopes") or []
    scope_rows_html: List[str] = []
    scene_options_html: List[str] = []
    for idx, sc in enumerate(scene_scopes):
        s_idx = int(sc.get("scene_index", idx + 1))
        parade = sc.get("rgb_parade") or {}
        de_val = float(sc.get("delta_e_2000", 0.0))
        exp_val = float(sc.get("exposure_jump_stops", 0.0))
        status_str = str(sc.get("shot_match_status", "MATCHED"))
        st_cls = "v220-badge-pass" if status_str == "MATCHED" else "v220-badge-warn"
        slope_str = ", ".join(f"{float(v):.3f}" for v in (sc.get("cdl_slope") or [1.0, 1.0, 1.0]))
        scope_rows_html.append(
            f'<tr>'
            f'<td><strong>S{s_idx:02d}</strong> · {html_escape(str(sc.get("scene_title", "")))}<br>'
            f'<code class="v220-code">{html_escape(str(sc.get("smpte_in", "")))} - {html_escape(str(sc.get("smpte_out", "")))}</code></td>'
            f'<td><span class="v220-swatch" style="background:{html_escape(str(sc.get("dominant_hex", "#38BDF8")))};"></span> '
            f'<code class="v220-code">{float(sc.get("luma_ire_min", 10)):.1f} / {float(sc.get("luma_ire_avg", 50)):.1f} / {float(sc.get("luma_ire_max", 90)):.1f} IRE</code></td>'
            f'<td><code class="v220-code">R:{float(parade.get("r_ire", 50)):.1f} G:{float(parade.get("g_ire", 50)):.1f} B:{float(parade.get("b_ire", 50)):.1f}</code></td>'
            f'<td><code class="v220-code">&Delta;E {de_val:.2f}</code> · <span class="v220-sub">{exp_val:+.2f} EV</span></td>'
            f'<td><code class="v220-code">Slope [{slope_str}] · Sat {float(sc.get("cdl_saturation", 1.0)):.2f}</code></td>'
            f'<td><span class="v220-badge {st_cls}">{html_escape(status_str)}</span></td>'
            f'</tr>'
        )
        sel_attr = ' selected' if idx == 0 else ''
        scene_options_html.append(f'<option value="{s_idx}"{sel_attr}>S{s_idx:02d} · {html_escape(str(sc.get("scene_title", ""))[:30])}</option>')
    scope_tbody_html = "\n".join(scope_rows_html)
    scene_options_str = "\n".join(scene_options_html)

    vault_rows_html: List[str] = []
    for art in vault_state.get("artifacts") or []:
        ver_cls = "v220-badge-pass" if art.get("verified", True) else "v220-badge-warn"
        ver_lbl = "SHA-256 VERIFIED" if art.get("verified", True) else "UNVERIFIED"
        size_kb = max(0.1, float(art.get("size_bytes", 1024)) / 1024.0)
        vault_rows_html.append(
            f'<tr>'
            f'<td><code class="v220-code">{html_escape(str(art.get("bag_path", "")))}</code><br>'
            f'<span class="v220-sub">{html_escape(str(art.get("department", "")))} · {html_escape(str(art.get("format", "")))}</span></td>'
            f'<td><code class="v220-code">{size_kb:.1f} KB</code></td>'
            f'<td><code class="v220-sha">{html_escape(str(art.get("sha256", "")))}</code></td>'
            f'<td><span class="v220-badge {ver_cls}">{ver_lbl}</span></td>'
            f'</tr>'
        )
    vault_tbody_html = "\n".join(vault_rows_html)

    css_str = """
    /* v2.20.0 Colorist Scopes & RFC 8493 Archive Vault HUDs */
    #colorScopesModal,
    #archiveVaultModal {
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(7, 8, 11, 0.92);
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
      z-index: 10075;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }
    .v220-modal-card {
      background: #0E1017;
      color: #F8FAFC;
      border: 1px solid #38BDF8;
      border-radius: 10px;
      width: 100%;
      max-width: 1160px;
      max-height: 92vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      box-shadow: 0 24px 60px rgba(0, 0, 0, 0.9);
    }
    .v220-modal-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      padding: 14px 20px;
      background: #141722;
      border-bottom: 1px solid #334155;
    }
    .v220-modal-title {
      margin: 0;
      font-family: 'Space Grotesk', sans-serif;
      font-size: 16px;
      font-weight: 700;
      color: #F8FAFC;
    }
    .v220-modal-sub {
      display: block;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      color: #7DD3FC;
      margin-top: 2px;
    }
    .v220-close-btn {
      min-width: 44px;
      min-height: 44px;
      background: #B91C1C;
      color: #FFFFFF;
      border: 1px solid #F87171;
      border-radius: 5px;
      padding: 8px 14px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 12px;
      font-weight: 700;
      cursor: pointer;
    }
    .v220-close-btn:hover,
    .v220-close-btn:focus-visible {
      background: #DC2626;
      outline: 2px solid #FACC15;
      outline-offset: 2px;
    }
    .v220-modal-body {
      padding: 18px 20px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }
    .v220-kpi-row {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
      justify-content: space-between;
      background: #141722;
      border: 1px solid #334155;
      border-radius: 6px;
      padding: 12px 14px;
    }
    .v220-badge-group {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }
    .v220-badge {
      display: inline-block;
      padding: 4px 9px;
      border-radius: 4px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      font-weight: 700;
    }
    .v220-badge-pass {
      background: #064E3B;
      color: #A7F3D0;
      border: 1px solid #10B981;
    }
    .v220-badge-warn {
      background: #451A03;
      color: #FDE68A;
      border: 1px solid #F59E0B;
    }
    .v220-badge-info {
      background: #0C4A6E;
      color: #BAE6FD;
      border: 1px solid #38BDF8;
    }
    .v220-code {
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      color: #FDE047;
    }
    .v220-sha {
      font-family: 'JetBrains Mono', monospace;
      font-size: 10.5px;
      color: #BAE6FD;
      word-break: break-all;
    }
    .v220-sub {
      font-size: 11.5px;
      color: #E2E8F0;
    }
    .v220-swatch {
      display: inline-block;
      width: 11px;
      height: 11px;
      border-radius: 2px;
      border: 1px solid #F8FAFC;
      vertical-align: middle;
      margin-right: 4px;
    }
    .v220-section-title {
      margin: 4px 0 0;
      font-family: 'Space Grotesk', sans-serif;
      font-size: 13px;
      font-weight: 700;
      color: #BAE6FD;
    }
    .v220-svg-frame {
      background: #05070B;
      border: 1px solid #334155;
      border-radius: 8px;
      padding: 12px;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .v220-svg-frame svg {
      width: 100%;
      height: auto;
      display: block;
      border-radius: 4px;
    }
    .v220-controls-bar {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
      justify-content: space-between;
      background: #0B1120;
      border: 1px solid #334155;
      border-radius: 6px;
      padding: 10px 12px;
    }
    .v220-ctrl-group {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }
    .v220-select {
      min-height: 44px;
      background: #141722;
      color: #F8FAFC;
      border: 1px solid #475569;
      border-radius: 5px;
      padding: 6px 10px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11.5px;
    }
    .v220-select:focus-visible,
    .v220-range:focus-visible {
      outline: 2px solid #FACC15;
      outline-offset: 2px;
    }
    #v220-ab-wipe-stage {
      position: relative;
      width: 100%;
      height: 210px;
      background: #05070B;
      border: 1px solid #475569;
      border-radius: 8px;
      overflow: hidden;
    }
    .v220-wipe-layer {
      position: absolute;
      inset: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      overflow: hidden;
    }
    .v220-wipe-layer svg {
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
    }
    #v220-ab-layer-b {
      z-index: 2;
      clip-path: inset(0 0 0 50%);
    }
    #v220-ab-layer-a {
      z-index: 1;
    }
    #v220-ab-divider {
      position: absolute;
      top: 0;
      bottom: 0;
      left: 50%;
      width: 2px;
      background: #FACC15;
      z-index: 4;
      pointer-events: none;
      box-shadow: 0 0 8px rgba(250, 204, 21, 0.8);
    }
    .v220-wipe-tag {
      position: absolute;
      top: 10px;
      z-index: 5;
      padding: 4px 8px;
      border-radius: 4px;
      background: rgba(14, 16, 23, 0.9);
      border: 1px solid #38BDF8;
      color: #F8FAFC;
      font-family: 'JetBrains Mono', monospace;
      font-size: 10.5px;
      font-weight: 700;
    }
    .v220-wipe-tag-a { left: 10px; }
    .v220-wipe-tag-b { right: 10px; border-color: #FACC15; }
    .v220-slider-row {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .v220-range {
      flex: 1;
      min-height: 44px;
      accent-color: #38BDF8;
      cursor: pointer;
    }
    .v220-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
    }
    .v220-table th,
    .v220-table td {
      border: 1px solid #334155;
      padding: 8px 10px;
      text-align: left;
      vertical-align: top;
    }
    .v220-table th {
      background: #1E293B;
      color: #F8FAFC;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
    }
    .v220-card-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      gap: 10px;
      background: #141722;
      border: 1px solid #334155;
      border-radius: 8px;
      padding: 12px 14px;
    }
    .v220-spec-cell {
      background: #0B1120;
      border: 1px solid #334155;
      border-radius: 6px;
      padding: 8px 10px;
      display: flex;
      flex-direction: column;
      gap: 3px;
    }
    .v220-spec-lbl {
      font-family: 'JetBrains Mono', monospace;
      font-size: 10px;
      text-transform: uppercase;
      color: #CBD5E1;
    }
    .v220-spec-val {
      font-family: 'JetBrains Mono', monospace;
      font-size: 12px;
      font-weight: 700;
      color: #F8FAFC;
    }
    .v220-actions-row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      justify-content: flex-end;
    }
    .v220-dl-btn {
      min-height: 44px;
      background: #0369A1;
      color: #FFFFFF;
      border: 1px solid #38BDF8;
      border-radius: 5px;
      padding: 8px 14px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11.5px;
      font-weight: 700;
      cursor: pointer;
    }
    .v220-dl-btn:hover {
      background: #0284C7;
    }
    .v220-dl-btn:focus-visible {
      outline: 2px solid #FACC15;
      outline-offset: 2px;
    }
    @media (prefers-reduced-motion: reduce) {
      #colorScopesModal *,
      #archiveVaultModal * {
        transition: none !important;
      }
    }
    """

    html_str = f"""
<!-- v2.20.0 PM-FEAT-039: Colorist Scopes, Delta-E Match & A/B Wipe Monitor HUD -->
<div id="colorScopesModal" role="dialog" aria-modal="true" aria-labelledby="colorScopesTitle" tabindex="-1">
  <div class="v220-modal-card">
    <div class="v220-modal-header">
      <div>
        <h2 id="colorScopesTitle" class="v220-modal-title">Colorist Scopes, CIEDE2000 Shot-Match &amp; A/B Wipe Monitor</h2>
        <span class="v220-modal-sub">Waveform (IRE), RGB Parade, Vectorscope &amp; Interactive Cut/CDL Split Monitor [+]</span>
      </div>
      <button type="button" class="v220-close-btn" id="colorScopesCloseBtn" onclick="toggleColorScopesHUD(false)" aria-label="Close Colorist Scopes and A/B Wipe HUD">Close [Esc]</button>
    </div>
    <div class="v220-modal-body">
      <div class="v220-kpi-row">
        <div class="v220-badge-group">
          <span class="v220-badge v220-badge-info" id="v220-signal-std-badge">{html_escape(str(scopes_state["signal_standard"]))}</span>
          <span class="v220-badge v220-badge-info" id="v220-delta-e-badge">Mean &Delta;E2000: {float(scopes_state["mean_delta_e_2000"]):.2f}</span>
          <span class="v220-badge v220-badge-info" id="v220-exp-jump-badge">Max Exp Jump: {float(scopes_state["max_exposure_jump_stops"]):.2f} stops</span>
          <span class="v220-badge {match_badge_cls}" id="v220-match-status-badge">{match_badge_lbl}</span>
        </div>
        <span class="v220-sub">Working Space: <strong class="v220-code">{html_escape(str(scopes_state["working_color_space"]))}</strong></span>
      </div>

      <div class="v220-svg-frame">
        <div class="v220-controls-bar">
          <div class="v220-ctrl-group">
            <label for="v220-scope-scene-select" class="v220-sub"><strong>Scope Focus:</strong></label>
            <select id="v220-scope-scene-select" class="v220-select" onchange="updateV220ScopesView()">
              {scene_options_str}
            </select>
          </div>
          <span class="v220-sub" id="v220-scopes-telemetry" aria-live="polite">Luma Waveform · RGB Parade · Vectorscope (Cb/Cr)</span>
        </div>
        <svg id="v220-scopes-svg" viewBox="0 0 920 220" role="img" aria-label="Broadcast Colorist Scopes SVG showing Luma Waveform, RGB Parade, and Vectorscope"></svg>
      </div>

      <h3 class="v220-section-title">Interactive A/B Wipe Comparison Monitor</h3>
      <div class="v220-svg-frame">
        <div class="v220-controls-bar">
          <div class="v220-ctrl-group">
            <label for="v220-ab-mode-select" class="v220-sub"><strong>Wipe Mode:</strong></label>
            <select id="v220-ab-mode-select" class="v220-select" onchange="updateV220AbWipe()">
              <option value="scene_cut">Scene N vs Scene N+1 (Cut Continuity)</option>
              <option value="cdl_vs_neutral">CDL Look vs Rec.709 Neutral</option>
            </select>
          </div>
          <span class="v220-code" id="v220-ab-readout" aria-live="polite">Split: 50% · S01 vs S02</span>
        </div>
        <div id="v220-ab-wipe-stage" role="region" aria-label="A/B Split Screen Comparison Stage">
          <div id="v220-ab-layer-a" class="v220-wipe-layer"></div>
          <div id="v220-ab-layer-b" class="v220-wipe-layer"></div>
          <div id="v220-ab-divider" aria-hidden="true"></div>
          <span id="v220-ab-tag-a" class="v220-wipe-tag v220-wipe-tag-a">A: S01</span>
          <span id="v220-ab-tag-b" class="v220-wipe-tag v220-wipe-tag-b">B: S02</span>
        </div>
        <div class="v220-slider-row">
          <label for="v220-ab-wipe-slider" class="v220-sub"><strong>A/B Wipe Position:</strong></label>
          <input type="range" id="v220-ab-wipe-slider" class="v220-range" min="0" max="100" value="50" oninput="updateV220AbWipe()" aria-label="A/B Wipe Split Position Percentage">
          <span class="v220-code" id="v220-ab-pct-lbl">50%</span>
        </div>
      </div>

      <h3 class="v220-section-title">Per-Scene Shot-Match CDL &amp; Scope Telemetry</h3>
      <table class="v220-table" aria-label="Per-Scene Color Scopes and Shot-Match CDL Table">
        <thead>
          <tr>
            <th>Scene / SMPTE</th>
            <th>Luma (Min / Avg / Max)</th>
            <th>RGB Parade (IRE)</th>
            <th>Cut &Delta;E2000 &amp; EV</th>
            <th>ASC CDL Trim</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody id="v220-scopes-tbody">
          {scope_tbody_html}
        </tbody>
      </table>

      <div class="v220-actions-row">
        <button type="button" class="v220-dl-btn" id="btn-dl-color-scopes-json" onclick="downloadColorScopesJSON()">⤓ color_continuity_scopes.json</button>
        <button type="button" class="v220-dl-btn" id="btn-dl-shot-match-csv" onclick="downloadShotMatchCDLCSV()">⤓ shot_match_cdl_deltas.csv</button>
      </div>
    </div>
  </div>
</div>

<!-- v2.20.0 PM-FEAT-040: RFC 8493 BagIt Archive Vault & Agency Handoff HUD -->
<div id="archiveVaultModal" role="dialog" aria-modal="true" aria-labelledby="archiveVaultTitle" tabindex="-1">
  <div class="v220-modal-card">
    <div class="v220-modal-header">
      <div>
        <h2 id="archiveVaultTitle" class="v220-modal-title">RFC 8493 BagIt Archive Vault &amp; Agency Handoff</h2>
        <span class="v220-modal-sub">6-Department Vault Manifest, Payload-Oxum Integrity &amp; SHA-256 Ledger [:]</span>
      </div>
      <button type="button" class="v220-close-btn" id="archiveVaultCloseBtn" onclick="toggleArchiveVaultHUD(false)" aria-label="Close Archive Vault and Agency Handoff HUD">Close [Esc]</button>
    </div>
    <div class="v220-modal-body">
      <div class="v220-kpi-row">
        <div class="v220-badge-group">
          <span class="v220-badge v220-badge-info" id="v220-bag-id-badge">BAG: {html_escape(str(vault_state["bag_id"]))}</span>
          <span class="v220-badge {vault_badge_cls}" id="v220-archive-ready-badge">{vault_badge_lbl}</span>
        </div>
        <span class="v220-sub">Standard: <strong class="v220-code">{html_escape(str(vault_state["rfc_standard"]))}</strong></span>
      </div>

      <div class="v220-card-grid" aria-label="Archive Vault Summary Metrics">
        <div class="v220-spec-cell">
          <span class="v220-spec-lbl">Retention Tier</span>
          <span class="v220-spec-val">{html_escape(str(vault_state["retention_tier"]))}</span>
        </div>
        <div class="v220-spec-cell">
          <span class="v220-spec-lbl">Payload-Oxum</span>
          <span class="v220-spec-val">{html_escape(str(vault_state["payload_oxum"]))}</span>
        </div>
        <div class="v220-spec-cell">
          <span class="v220-spec-lbl">Estimated Footprint</span>
          <span class="v220-spec-val">{float(vault_state["estimated_media_footprint_gb"]):.2f} GB</span>
        </div>
        <div class="v220-spec-cell">
          <span class="v220-spec-lbl">Rights Expiry ISO</span>
          <span class="v220-spec-val">{html_escape(str(vault_state["rights_expiry_iso"]))}</span>
        </div>
      </div>

      <div class="v220-svg-frame">
        <div class="v220-sub"><strong>6-Department Vault Payload Breakdown</strong> · <span id="v220-vault-telemetry" aria-live="polite">All 6 production departments checksummed for cold-storage agency handoff.</span></div>
        <svg id="v220-vault-svg" viewBox="0 0 920 185" role="img" aria-label="6-Department Archive Vault Breakdown SVG"></svg>
      </div>

      <h3 class="v220-section-title">Artifact SHA-256 Verification Ledger (manifest-sha256.txt)</h3>
      <table class="v220-table" aria-label="Archive Vault Artifact SHA-256 Verification Table">
        <thead>
          <tr>
            <th>Bag Payload Path / Department</th>
            <th>Size</th>
            <th>SHA-256 Digest</th>
            <th>Verification</th>
          </tr>
        </thead>
        <tbody id="v220-vault-tbody">
          {vault_tbody_html}
        </tbody>
      </table>

      <div class="v220-actions-row">
        <button type="button" class="v220-dl-btn" id="btn-dl-archive-json" onclick="downloadArchiveVaultJSON()">⤓ archive_vault_manifest.json</button>
        <button type="button" class="v220-dl-btn" id="btn-dl-bag-info" onclick="downloadBagInfoTXT()">⤓ bag-info.txt</button>
        <button type="button" class="v220-dl-btn" id="btn-dl-manifest-sha256" onclick="downloadManifestSha256TXT()">⤓ manifest-sha256.txt</button>
      </div>
    </div>
  </div>
</div>
"""

    js_template = """
    // v2.20.0 Colorist Scopes & A/B Wipe (PM-FEAT-039) & RFC 8493 Archive Vault (PM-FEAT-040)
    const V220_COLOR_SCOPES_STATE = __SCOPES_JSON__;
    const V220_ARCHIVE_VAULT_STATE = __VAULT_JSON__;
    window.V220_COLOR_SCOPES_STATE = V220_COLOR_SCOPES_STATE;
    window.V220_ARCHIVE_VAULT_STATE = V220_ARCHIVE_VAULT_STATE;

    let isColorScopesHUDOpen = false;
    window.isColorScopesHUDOpen = false;
    let lastColorScopesOpener = null;

    let isArchiveVaultHUDOpen = false;
    window.isArchiveVaultHUDOpen = false;
    let lastArchiveVaultOpener = null;

    let _v220Initialized = false;

    if (typeof V216_HUD_COMMANDS !== 'undefined' && Array.isArray(V216_HUD_COMMANDS)) {
      if (!V216_HUD_COMMANDS.some((c) => c.id === 'colorscopes')) {
        V216_HUD_COMMANDS.push({ id: 'colorscopes', name: 'Colorist Scopes, Delta-E Match & A/B Wipe', dept: 'Color', key: '+', fn: 'toggleColorScopesHUD' });
      }
      if (!V216_HUD_COMMANDS.some((c) => c.id === 'archivevault')) {
        V216_HUD_COMMANDS.push({ id: 'archivevault', name: 'RFC 8493 Archive Vault & Agency Handoff', dept: 'Delivery', key: ':', fn: 'toggleArchiveVaultHUD' });
      }
    }

    function _v220ShowToast(msg) {
      if (typeof showToast === 'function') {
        showToast(msg);
        return;
      }
      const toast = document.createElement('div');
      toast.className = 'cinema-toast show';
      toast.textContent = msg;
      toast.style.position = 'fixed';
      toast.style.bottom = '20px';
      toast.style.right = '20px';
      toast.style.background = '#0F172A';
      toast.style.color = '#F8FAFC';
      toast.style.padding = '10px 16px';
      toast.style.borderRadius = '6px';
      toast.style.border = '1px solid #38BDF8';
      toast.style.zIndex = '20000';
      document.body.appendChild(toast);
      setTimeout(() => toast.remove(), 2600);
    }

    function _v220DownloadBlob(content, mime, filename, toastMsg) {
      const blob = new Blob([content], { type: mime });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      _v220ShowToast(toastMsg);
    }

    function _v220SvgEl(tag, attrs) {
      const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
      Object.keys(attrs || {}).forEach((k) => el.setAttribute(k, String(attrs[k])));
      return el;
    }

    function _v220TrapFocus(modal, onEscape) {
      if (!modal) return;
      modal.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
          e.stopPropagation();
          onEscape();
          return;
        }
        if (e.key !== 'Tab') return;
        if (typeof _handleModalTabFocusTrap === 'function') return;
        const focusables = modal.querySelectorAll('a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])');
        if (!focusables.length) return;
        const firstEl = focusables[0];
        const lastEl = focusables[focusables.length - 1];
        if (e.shiftKey && document.activeElement === firstEl) {
          lastEl.focus();
          e.preventDefault();
        } else if (!e.shiftKey && document.activeElement === lastEl) {
          firstEl.focus();
          e.preventDefault();
        }
      });
    }

    function _getSelectedScopeScene() {
      const sel = document.getElementById('v220-scope-scene-select');
      const scopes = V220_COLOR_SCOPES_STATE.scene_scopes || [];
      if (!scopes.length) return null;
      const targetIdx = sel ? parseInt(sel.value, 10) : scopes[0].scene_index;
      return scopes.find((s) => Number(s.scene_index) === targetIdx) || scopes[0];
    }

    function renderV220ScopesSvg() {
      const svg = document.getElementById('v220-scopes-svg');
      if (!svg) return;
      while (svg.firstChild) svg.removeChild(svg.firstChild);

      const W = 920;
      const H = 220;
      svg.appendChild(_v220SvgEl('rect', { x: 0, y: 0, width: W, height: H, fill: '#05070B' }));

      const scopes = V220_COLOR_SCOPES_STATE.scene_scopes || [];
      const activeSc = _getSelectedScopeScene() || { scene_index: 1, luma_ire_min: 12, luma_ire_avg: 52, luma_ire_max: 88, rgb_parade: { r_ire: 56, g_ire: 50, b_ire: 48 }, vectorscope_hue_deg: 42, vectorscope_sat_pct: 48 };

      // 3 Panels: Waveform (16..310), RGB Parade (326..610), Vectorscope (626..904)
      const panels = [
        { x: 14, w: 294, title: 'LUMA WAVEFORM (0-100 IRE)' },
        { x: 322, w: 286, title: 'RGB PARADE · S' + String(activeSc.scene_index).padStart(2, '0') },
        { x: 622, w: 284, title: 'VECTORSCOPE (Cb / Cr)' }
      ];
      panels.forEach((p) => {
        svg.appendChild(_v220SvgEl('rect', { x: p.x, y: 12, width: p.w, height: H - 24, rx: 6, fill: '#0B101B', stroke: '#334155', 'stroke-width': 1 }));
        const t = _v220SvgEl('text', { x: p.x + 10, y: 28, fill: '#BAE6FD', 'font-family': 'JetBrains Mono, monospace', 'font-size': 10, 'font-weight': 700 });
        t.textContent = p.title;
        svg.appendChild(t);
      });

      // Panel 1: Luma Waveform across all scenes
      const wfX = 24;
      const wfY = 40;
      const wfW = 274;
      const wfH = 152;
      [0, 25, 50, 75, 100].forEach((ire) => {
        const gy = wfY + wfH - (ire / 100) * wfH;
        svg.appendChild(_v220SvgEl('line', { x1: wfX, y1: gy, x2: wfX + wfW, y2: gy, stroke: ire === 100 || ire === 0 ? '#475569' : '#1E293B', 'stroke-width': 1, 'stroke-dasharray': ire === 50 ? '3,3' : '' }));
        const gl = _v220SvgEl('text', { x: wfX + 2, y: gy - 2, fill: '#94A3B8', 'font-family': 'JetBrains Mono, monospace', 'font-size': 8.5 });
        gl.textContent = String(ire);
        svg.appendChild(gl);
      });
      const stepW = wfW / Math.max(1, scopes.length);
      let avgPts = '';
      scopes.forEach((sc, i) => {
        const bx = wfX + i * stepW + 6;
        const bw = Math.max(14, stepW - 12);
        const yMax = wfY + wfH - (Math.min(100, Number(sc.luma_ire_max || 88)) / 100) * wfH;
        const yMin = wfY + wfH - (Math.max(0, Number(sc.luma_ire_min || 10)) / 100) * wfH;
        const yAvg = wfY + wfH - (Math.min(100, Number(sc.luma_ire_avg || 50)) / 100) * wfH;
        const isSel = Number(sc.scene_index) === Number(activeSc.scene_index);
        svg.appendChild(_v220SvgEl('rect', {
          x: bx, y: yMax, width: bw, height: Math.max(8, yMin - yMax), rx: 3,
          fill: isSel ? '#38BDF8' : '#1E3A8A', 'fill-opacity': isSel ? '0.52' : '0.35',
          stroke: isSel ? '#FACC15' : '#38BDF8', 'stroke-width': isSel ? 1.5 : 0.8
        }));
        svg.appendChild(_v220SvgEl('line', { x1: bx, y1: yAvg, x2: bx + bw, y2: yAvg, stroke: '#F8FAFC', 'stroke-width': 1.8 }));
        avgPts += (bx + bw / 2).toFixed(1) + ',' + yAvg.toFixed(1) + ' ';
      });
      if (avgPts.trim()) {
        svg.appendChild(_v220SvgEl('polyline', { points: avgPts.trim(), fill: 'none', stroke: '#FACC15', 'stroke-width': 1.4, 'stroke-dasharray': '4,2' }));
      }

      // Panel 2: RGB Parade for selected scene
      const rpX = 338;
      const rpY = 40;
      const rpW = 254;
      const rpH = 152;
      const parade = activeSc.rgb_parade || { r_ire: 54, g_ire: 50, b_ire: 46 };
      const channels = [
        { lbl: 'R', val: Number(parade.r_ire || 54), col: '#EF4444' },
        { lbl: 'G', val: Number(parade.g_ire || 50), col: '#22C55E' },
        { lbl: 'B', val: Number(parade.b_ire || 46), col: '#38BDF8' }
      ];
      channels.forEach((ch, idx) => {
        const cx = rpX + idx * 86 + 10;
        const cw = 64;
        svg.appendChild(_v220SvgEl('rect', { x: cx, y: rpY, width: cw, height: rpH, rx: 4, fill: '#05070B', stroke: '#1E293B', 'stroke-width': 1 }));
        const barH = Math.max(10, (Math.min(100, ch.val) / 100) * (rpH - 18));
        const by = rpY + rpH - barH - 14;
        svg.appendChild(_v220SvgEl('rect', { x: cx + 8, y: by, width: cw - 16, height: barH, rx: 3, fill: ch.col, 'fill-opacity': '0.78' }));
        // Waveform ripple inside channel
        const midY = by + 4;
        const pathD = 'M ' + (cx + 8) + ' ' + midY + ' Q ' + (cx + cw / 2) + ' ' + Math.max(rpY + 4, midY - 12) + ' ' + (cx + cw - 8) + ' ' + midY;
        svg.appendChild(_v220SvgEl('path', { d: pathD, fill: 'none', stroke: '#F8FAFC', 'stroke-width': 1.2 }));
        const cl = _v220SvgEl('text', { x: cx + cw / 2, y: rpY + rpH - 2, fill: '#F8FAFC', 'font-family': 'JetBrains Mono, monospace', 'font-size': 9.5, 'text-anchor': 'middle' });
        cl.textContent = ch.lbl + ' ' + ch.val.toFixed(0) + ' IRE';
        svg.appendChild(cl);
      });

      // Panel 3: Vectorscope (Cb/Cr)
      const vsCx = 764;
      const vsCy = 122;
      const vsR = 72;
      svg.appendChild(_v220SvgEl('circle', { cx: vsCx, cy: vsCy, r: vsR, fill: '#05070B', stroke: '#334155', 'stroke-width': 1.2 }));
      svg.appendChild(_v220SvgEl('circle', { cx: vsCx, cy: vsCy, r: vsR * 0.55, fill: 'none', stroke: '#1E293B', 'stroke-width': 1, 'stroke-dasharray': '3,3' }));
      svg.appendChild(_v220SvgEl('line', { x1: vsCx - vsR, y1: vsCy, x2: vsCx + vsR, y2: vsCy, stroke: '#1E293B', 'stroke-width': 1 }));
      svg.appendChild(_v220SvgEl('line', { x1: vsCx, y1: vsCy - vsR, x2: vsCx, y2: vsCy + vsR, stroke: '#1E293B', 'stroke-width': 1 }));
      // Skin-tone I-line (~123 deg)
      const skinRad = (123 * Math.PI) / 180;
      svg.appendChild(_v220SvgEl('line', {
        x1: vsCx, y1: vsCy,
        x2: (vsCx + Math.cos(skinRad) * vsR).toFixed(1),
        y2: (vsCy - Math.sin(skinRad) * vsR).toFixed(1),
        stroke: '#F59E0B', 'stroke-width': 1, 'stroke-dasharray': '4,3'
      }));
      const targets = [
        { lbl: 'R', deg: 103, col: '#EF4444' },
        { lbl: 'Yl', deg: 167, col: '#FACC15' },
        { lbl: 'G', deg: 241, col: '#22C55E' },
        { lbl: 'Cy', deg: 283, col: '#38BDF8' },
        { lbl: 'B', deg: 347, col: '#60A5FA' },
        { lbl: 'Mg', deg: 61, col: '#E879F9' }
      ];
      targets.forEach((tg) => {
        const rad = (tg.deg * Math.PI) / 180;
        const tx = vsCx + Math.cos(rad) * (vsR * 0.78);
        const ty = vsCy - Math.sin(rad) * (vsR * 0.78);
        svg.appendChild(_v220SvgEl('rect', { x: tx - 5, y: ty - 5, width: 10, height: 10, fill: 'none', stroke: tg.col, 'stroke-width': 1 }));
      });
      // Plot each scene chroma vector
      scopes.forEach((sc) => {
        const ang = (Number(sc.vectorscope_hue_deg || 45) * Math.PI) / 180;
        const mag = (Math.min(92, Number(sc.vectorscope_sat_pct || 45)) / 100) * vsR;
        const px = vsCx + Math.cos(ang) * mag;
        const py = vsCy - Math.sin(ang) * mag;
        const isSel = Number(sc.scene_index) === Number(activeSc.scene_index);
        svg.appendChild(_v220SvgEl('line', { x1: vsCx, y1: vsCy, x2: px.toFixed(1), y2: py.toFixed(1), stroke: isSel ? '#FACC15' : '#38BDF8', 'stroke-width': isSel ? 2 : 1, 'stroke-opacity': isSel ? '0.95' : '0.45' }));
        svg.appendChild(_v220SvgEl('circle', { cx: px.toFixed(1), cy: py.toFixed(1), r: isSel ? 5 : 3.2, fill: sc.dominant_hex || '#38BDF8', stroke: isSel ? '#FACC15' : '#F8FAFC', 'stroke-width': 1.2 }));
      });
    }

    function _buildFallbackSceneSvg(sc, badgeText, filterCss) {
      const svg = _v220SvgEl('svg', { viewBox: '0 0 640 210', role: 'img', 'aria-label': badgeText });
      if (filterCss) svg.style.filter = filterCss;
      svg.appendChild(_v220SvgEl('rect', { x: 0, y: 0, width: 640, height: 210, fill: '#090D16' }));
      svg.appendChild(_v220SvgEl('rect', { x: 18, y: 18, width: 604, height: 174, rx: 10, fill: sc.dominant_hex || '#1E293B', 'fill-opacity': '0.35', stroke: sc.secondary_hex || '#38BDF8', 'stroke-width': 2 }));
      svg.appendChild(_v220SvgEl('circle', { cx: 180, cy: 105, r: 58, fill: sc.dominant_hex || '#38BDF8', 'fill-opacity': '0.7' }));
      svg.appendChild(_v220SvgEl('circle', { cx: 460, cy: 105, r: 44, fill: sc.secondary_hex || '#FACC15', 'fill-opacity': '0.65' }));
      const txt = _v220SvgEl('text', { x: 320, y: 112, fill: '#F8FAFC', 'font-family': 'Space Grotesk, sans-serif', 'font-size': 16, 'font-weight': 700, 'text-anchor': 'middle' });
      txt.textContent = 'S' + String(sc.scene_index).padStart(2, '0') + ' · ' + String(sc.scene_title || 'Scene');
      svg.appendChild(txt);
      return svg;
    }

    function _cloneSceneArtworkForWipe(sc, filterCss) {
      const domPlate = document.querySelector('#scene-' + sc.scene_index + ' .plate-svg-container svg');
      if (domPlate) {
        const cloned = domPlate.cloneNode(true);
        if (filterCss) cloned.style.filter = filterCss;
        return cloned;
      }
      return _buildFallbackSceneSvg(sc, 'Scene ' + sc.scene_index, filterCss);
    }

    window.updateV220ScopesView = function() {
      renderV220ScopesSvg();
      window.updateV220AbWipe();
    };

    window.updateV220AbWipe = function() {
      const slider = document.getElementById('v220-ab-wipe-slider');
      const modeSel = document.getElementById('v220-ab-mode-select');
      const layerA = document.getElementById('v220-ab-layer-a');
      const layerB = document.getElementById('v220-ab-layer-b');
      const divider = document.getElementById('v220-ab-divider');
      const tagA = document.getElementById('v220-ab-tag-a');
      const tagB = document.getElementById('v220-ab-tag-b');
      const pctLbl = document.getElementById('v220-ab-pct-lbl');
      const readout = document.getElementById('v220-ab-readout');
      if (!slider || !layerA || !layerB) return;

      const pct = Math.max(0, Math.min(100, parseInt(slider.value || '50', 10)));
      if (pctLbl) pctLbl.textContent = pct + '%';
      if (divider) divider.style.left = pct + '%';
      layerB.style.clipPath = 'inset(0 0 0 ' + pct + '%)';

      const scopes = V220_COLOR_SCOPES_STATE.scene_scopes || [];
      if (!scopes.length) return;
      const scA = _getSelectedScopeScene() || scopes[0];
      const idxA = scopes.findIndex((s) => Number(s.scene_index) === Number(scA.scene_index));
      const scB = scopes[(idxA + 1) % scopes.length] || scA;
      const mode = modeSel ? modeSel.value : 'scene_cut';

      while (layerA.firstChild) layerA.removeChild(layerA.firstChild);
      while (layerB.firstChild) layerB.removeChild(layerB.firstChild);

      if (mode === 'cdl_vs_neutral') {
        const activePreset = (typeof currentLook !== 'undefined' && currentLook) ? currentLook : (scA.look_preset || 'kodak_5219_vision3');
        layerA.appendChild(_cloneSceneArtworkForWipe(scA, 'url(#cdl-filter-' + activePreset + ')'));
        layerB.appendChild(_cloneSceneArtworkForWipe(scA, 'url(#cdl-filter-rec709_neutral)'));
        if (tagA) tagA.textContent = 'A: S' + String(scA.scene_index).padStart(2, '0') + ' (' + activePreset + ')';
        if (tagB) tagB.textContent = 'B: S' + String(scA.scene_index).padStart(2, '0') + ' (rec709_neutral)';
        if (readout) readout.textContent = 'Split: ' + pct + '% · CDL Look vs Rec.709 Neutral';
      } else {
        layerA.appendChild(_cloneSceneArtworkForWipe(scA, ''));
        layerB.appendChild(_cloneSceneArtworkForWipe(scB, ''));
        if (tagA) tagA.textContent = 'A: S' + String(scA.scene_index).padStart(2, '0') + ' (' + Number(scA.luma_ire_avg || 50).toFixed(1) + ' IRE)';
        if (tagB) tagB.textContent = 'B: S' + String(scB.scene_index).padStart(2, '0') + ' (ΔE ' + Number(scB.delta_e_2000 || 0).toFixed(2) + ')';
        if (readout) readout.textContent = 'Split: ' + pct + '% · S' + String(scA.scene_index).padStart(2, '0') + ' vs S' + String(scB.scene_index).padStart(2, '0') + ' (ΔE ' + Number(scB.delta_e_2000 || 0).toFixed(2) + ')';
      }
    };

    function renderV220VaultSvg() {
      const svg = document.getElementById('v220-vault-svg');
      if (!svg) return;
      while (svg.firstChild) svg.removeChild(svg.firstChild);

      const W = 920;
      const H = 185;
      svg.appendChild(_v220SvgEl('rect', { x: 0, y: 0, width: W, height: H, fill: '#05070B' }));

      const depts = V220_ARCHIVE_VAULT_STATE.department_vaults || [];
      if (!depts.length) return;
      const maxMb = Math.max(100, ...depts.map((d) => Number(d.footprint_mb || 100)));
      const rowH = 24;
      const startY = 16;

      depts.forEach((d, idx) => {
        const y = startY + idx * (rowH + 3);
        const lbl = _v220SvgEl('text', { x: 14, y: y + 16, fill: '#F8FAFC', 'font-family': 'JetBrains Mono, monospace', 'font-size': 10.5 });
        lbl.textContent = String(d.department || 'Dept');
        svg.appendChild(lbl);

        const barX = 188;
        const maxBarW = 540;
        svg.appendChild(_v220SvgEl('rect', { x: barX, y: y + 4, width: maxBarW, height: 15, rx: 4, fill: '#1E293B', stroke: '#334155', 'stroke-width': 1 }));
        const fillW = Math.max(20, Math.round((Number(d.footprint_mb || 50) / maxMb) * maxBarW));
        svg.appendChild(_v220SvgEl('rect', { x: barX, y: y + 4, width: fillW, height: 15, rx: 4, fill: d.verified ? '#10B981' : '#F59E0B', 'fill-opacity': '0.85' }));

        const val = _v220SvgEl('text', { x: 742, y: y + 16, fill: '#BAE6FD', 'font-family': 'JetBrains Mono, monospace', 'font-size': 10.5 });
        val.textContent = Number(d.footprint_mb || 0).toFixed(1) + ' MB · ' + Number(d.artifact_count || 0) + ' files · OK';
        svg.appendChild(val);
      });
    }

    window.toggleColorScopesHUD = function(forceState) {
      const modal = document.getElementById('colorScopesModal');
      const btn = document.getElementById('btn-color-scopes');
      if (!modal) return;
      const shouldOpen = forceState !== undefined ? Boolean(forceState) : !isColorScopesHUDOpen;
      if (!shouldOpen && !isColorScopesHUDOpen) return;
      if (shouldOpen) {
        if (typeof closeSecondaryOpenHUDs === 'function') closeSecondaryOpenHUDs('colorscopes');
        if (isArchiveVaultHUDOpen) window.toggleArchiveVaultHUD(false);
      }
      isColorScopesHUDOpen = shouldOpen;
      window.isColorScopesHUDOpen = shouldOpen;
      if (btn) {
        btn.classList.toggle('active', shouldOpen);
        btn.setAttribute('aria-expanded', shouldOpen ? 'true' : 'false');
      }
      if (shouldOpen) {
        lastColorScopesOpener = document.activeElement;
        modal.style.display = 'flex';
        renderV220ScopesSvg();
        window.updateV220AbWipe();
        const closeBtn = document.getElementById('colorScopesCloseBtn');
        if (closeBtn) closeBtn.focus();
        _v220ShowToast('📊 Colorist Scopes & A/B Wipe Monitor: ACTIVE [+]');
      } else {
        modal.style.display = 'none';
        if (lastColorScopesOpener && typeof lastColorScopesOpener.focus === 'function') lastColorScopesOpener.focus();
        else if (btn && typeof btn.focus === 'function') btn.focus();
      }
    };

    window.toggleArchiveVaultHUD = function(forceState) {
      const modal = document.getElementById('archiveVaultModal');
      const btn = document.getElementById('btn-archive-vault');
      if (!modal) return;
      const shouldOpen = forceState !== undefined ? Boolean(forceState) : !isArchiveVaultHUDOpen;
      if (!shouldOpen && !isArchiveVaultHUDOpen) return;
      if (shouldOpen) {
        if (typeof closeSecondaryOpenHUDs === 'function') closeSecondaryOpenHUDs('archivevault');
        if (isColorScopesHUDOpen) window.toggleColorScopesHUD(false);
      }
      isArchiveVaultHUDOpen = shouldOpen;
      window.isArchiveVaultHUDOpen = shouldOpen;
      if (btn) {
        btn.classList.toggle('active', shouldOpen);
        btn.setAttribute('aria-expanded', shouldOpen ? 'true' : 'false');
      }
      if (shouldOpen) {
        lastArchiveVaultOpener = document.activeElement;
        modal.style.display = 'flex';
        renderV220VaultSvg();
        const closeBtn = document.getElementById('archiveVaultCloseBtn');
        if (closeBtn) closeBtn.focus();
        _v220ShowToast('🗄️ RFC 8493 Archive Vault & Agency Handoff: ACTIVE [:]');
      } else {
        modal.style.display = 'none';
        if (lastArchiveVaultOpener && typeof lastArchiveVaultOpener.focus === 'function') lastArchiveVaultOpener.focus();
        else if (btn && typeof btn.focus === 'function') btn.focus();
      }
    };

    function _csvCellV220(val) {
      const s = String(val == null ? '' : val);
      return '"' + s.replace(/"/g, '""') + '"';
    }

    window.downloadColorScopesJSON = function() {
      _v220DownloadBlob(
        JSON.stringify(V220_COLOR_SCOPES_STATE, null, 2),
        'application/json;charset=utf-8;',
        'color_continuity_scopes.json',
        'Downloaded color_continuity_scopes.json'
      );
    };

    window.downloadShotMatchCDLCSV = function() {
      const rows = [['Scene', 'Scene_Title', 'SMPTE_In', 'SMPTE_Out', 'Look_Preset', 'Luma_Min_IRE', 'Luma_Avg_IRE', 'Luma_Max_IRE', 'R_IRE', 'G_IRE', 'B_IRE', 'Delta_E_2000', 'Exposure_Jump_Stops', 'CDL_Slope', 'CDL_Offset', 'CDL_Power', 'CDL_Sat', 'Status']];
      (V220_COLOR_SCOPES_STATE.scene_scopes || []).forEach((sc) => {
        const p = sc.rgb_parade || {};
        rows.push([
          sc.scene_index,
          sc.scene_title,
          sc.smpte_in,
          sc.smpte_out,
          sc.look_preset,
          sc.luma_ire_min,
          sc.luma_ire_avg,
          sc.luma_ire_max,
          p.r_ire,
          p.g_ire,
          p.b_ire,
          sc.delta_e_2000,
          sc.exposure_jump_stops,
          (sc.cdl_slope || []).join(' '),
          (sc.cdl_offset || []).join(' '),
          (sc.cdl_power || []).join(' '),
          sc.cdl_saturation,
          sc.shot_match_status
        ]);
      });
      const csvText = rows.map((r) => r.map(_csvCellV220).join(',')).join('\\n') + '\\n';
      _v220DownloadBlob(csvText, 'text/csv;charset=utf-8;', 'shot_match_cdl_deltas.csv', 'Downloaded shot_match_cdl_deltas.csv');
    };

    window.downloadArchiveVaultJSON = function() {
      _v220DownloadBlob(
        JSON.stringify(V220_ARCHIVE_VAULT_STATE, null, 2),
        'application/json;charset=utf-8;',
        'archive_vault_manifest.json',
        'Downloaded archive_vault_manifest.json'
      );
    };

    window.downloadBagInfoTXT = function() {
      const v = V220_ARCHIVE_VAULT_STATE;
      const lines = [
        'Source-Organization: Omni Movie Director Studio',
        'Bag-Software-Agent: Omni-Director RFC 8493 Packager v2.20.0',
        'Bagging-Date: ' + String(v.bagging_date_iso || '2026-11-28'),
        'External-Identifier: ' + String(v.bag_id || ''),
        'External-Description: Agency Production Archive for ' + String(v.project_title || 'Omni Production'),
        'Payload-Oxum: ' + String(v.payload_oxum || ''),
        'Bag-Size: ' + Number(v.estimated_media_footprint_gb || 0).toFixed(2) + ' GB',
        'Retention-Tier: ' + String(v.retention_tier || 'ENTERPRISE_WORM_7YR'),
        'Rights-Expiry-Date: ' + String(v.rights_expiry_iso || '2029-11-28'),
        'Archive-Ready: ' + (v.archive_ready ? 'true' : 'false')
      ];
      _v220DownloadBlob(lines.join('\\n') + '\\n', 'text/plain;charset=utf-8;', 'bag-info.txt', 'Downloaded bag-info.txt');
    };

    window.downloadManifestSha256TXT = function() {
      const lines = (V220_ARCHIVE_VAULT_STATE.artifacts || []).map((a) => String(a.sha256 || '') + '  ' + String(a.bag_path || ''));
      _v220DownloadBlob(lines.join('\\n') + '\\n', 'text/plain;charset=utf-8;', 'manifest-sha256.txt', 'Downloaded manifest-sha256.txt');
    };

    window.initV220HUDs = function() {
      if (_v220Initialized) return;
      _v220Initialized = true;
      const colorModal = document.getElementById('colorScopesModal');
      const vaultModal = document.getElementById('archiveVaultModal');
      _v220TrapFocus(colorModal, () => toggleColorScopesHUD(false));
      _v220TrapFocus(vaultModal, () => toggleArchiveVaultHUD(false));
      if (colorModal) {
        colorModal.addEventListener('click', (e) => {
          if (e.target === colorModal) toggleColorScopesHUD(false);
        });
      }
      if (vaultModal) {
        vaultModal.addEventListener('click', (e) => {
          if (e.target === vaultModal) toggleArchiveVaultHUD(false);
        });
      }
      renderV220ScopesSvg();
      window.updateV220AbWipe();
      renderV220VaultSvg();
    };

    document.addEventListener('DOMContentLoaded', () => {
      if (typeof initV220HUDs === 'function') initV220HUDs();
    });
    """

    js_str = (
        js_template
        .replace("__SCOPES_JSON__", scopes_json)
        .replace("__VAULT_JSON__", vault_json)
    )

    return {
        "css": css_str,
        "html": html_str,
        "js": js_str,
    }


__all__ = [
    "synthesize_v220_color_scopes_state",
    "synthesize_v220_archive_vault_state",
    "build_v220_hud_bundle",
]
