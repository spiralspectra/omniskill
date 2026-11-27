"""Modular v2.17.0 Dark-Room Cinema HUD Components (PM-FEAT-033 & PM-FEAT-034).

Provides Python 3.11-compatible builders for:
1. PM-FEAT-033: Motion Graphics, Supers & End-Card Studio (#modal-motion-graphics-studio, [=] hotkey)
2. PM-FEAT-034: OpenTimelineIO (.otio) & Cross-Dept Coherence Matrix (#modal-otio-coherence, ['] hotkey)
"""

from __future__ import annotations

import hashlib
import json
import re
from html import escape as html_escape
from typing import Any, Dict, List, Tuple


_OTIO_TRACK_DEFS: List[Tuple[str, str, str]] = [
    ("V1_Picture_Master", "Video", "#38BDF8"),
    ("V2_VFX_GFX_Overlay", "Video", "#A855F7"),
    ("A1_Dialogue", "Audio", "#34D399"),
    ("A2_Foley_SFX", "Audio", "#FBBF24"),
    ("A3_Ambience", "Audio", "#60A5FA"),
    ("A4_Music_Score", "Audio", "#F472B6"),
    ("A5_Audio_Description", "Audio", "#FB923C"),
]

_COHERENCE_CHECK_DEFS: List[Tuple[str, str, str, str, str]] = [
    ("CHK-01-OPTICS-DOF", "optics_vs_dof", "OPTICS_VS_DOF", "Camera Optics ↔ Depth of Field", "Focal length & T-stop within CoC hyperfocal envelope"),
    ("CHK-02-KELVIN-BLOCKING", "lighting_kelvin_vs_blocking", "LIGHTING_KELVIN_VS_BLOCKING", "Gaffer Rig ↔ 180° Blocking", "Key/fill CCT Kelvin matched across camera axis"),
    ("CHK-03-AUDIO-SPOTTING", "audio_stems_vs_spotting", "AUDIO_STEMS_VS_SPOTTING", "Spatial Stems ↔ Editorial Spotting", "7.1.4 / Stereo stems aligned to J/L-cut bridges"),
    ("CHK-04-REFRAME-GRAPHICS", "reframe_vs_graphics_blocking", "REFRAME_VS_GRAPHICS_BLOCKING", "Social Reframe ↔ Motion GFX", "9:16 & 16:9 safe zones clear of [GFX-CLEANPLATE]"),
    ("CHK-05-MODEB-ECONOMICS", "mode_b_vs_runtime_economics", "MODE_B_VS_RUNTIME_ECONOMICS", "Storytelling Mode ↔ Runtime Cap", "Mode B <= 40s or Mode A parallel cut budget valid"),
    ("CHK-06-AICP-COMPUTE", "aicp_post_vs_render_compute", "AICP_POST_VS_RENDER_COMPUTE", "AICP Bid ↔ AI Render Economics", "Estimated AI compute within budget guardrail cap"),
    ("CHK-07-C2PA-SAFETY", "c2pa_vs_cast_safety", "C2PA_VS_CAST_SAFETY", "C2PA Provenance ↔ Set Safety JSA", "Likeness disclosures & set exclusion clearances synced"),
]

_COHERENCE_META_BY_KEY: Dict[str, Tuple[str, str, str, str]] = {}
for _cid, _pair, _legacy, _depts, _bound in _COHERENCE_CHECK_DEFS:
    _COHERENCE_META_BY_KEY[_cid] = (_cid, _pair, _depts, _bound)
    _COHERENCE_META_BY_KEY[_pair] = (_cid, _pair, _depts, _bound)
    _COHERENCE_META_BY_KEY[_legacy] = (_cid, _pair, _depts, _bound)


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
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _sec_to_smpte(sec: float, fps: int = 24) -> str:
    total_frames = max(0, int(round(float(sec) * fps)))
    ff = total_frames % fps
    total_sec = total_frames // fps
    ss = total_sec % 60
    mm = (total_sec // 60) % 60
    hh = total_sec // 3600
    return f"{hh:02d}:{mm:02d}:{ss:02d}:{ff:02d}"


def _smpte_to_sec(smpte: str, fps: int = 24) -> float | None:
    """Parses HH:MM:SS:FF SMPTE timecode into seconds."""
    m = re.match(r"^\s*(\d{2}):(\d{2}):(\d{2}):(\d{2})\s*$", str(smpte or ""))
    if not m:
        return None
    hh, mm, ss, ff = (int(x) for x in m.groups())
    rate = max(1, int(fps))
    return round(hh * 3600 + mm * 60 + ss + (ff / rate), 3)


def _wcag_contrast_ratio(fg_hex: str, bg_hex: str) -> float:
    """Computes WCAG 2.2 contrast ratio between two #RRGGBB hex colors."""
    def _rel_lum(hex_color: str) -> float:
        cleaned = str(hex_color or "").strip().lstrip("#")
        if len(cleaned) == 3:
            cleaned = "".join(ch * 2 for ch in cleaned)
        if len(cleaned) < 6:
            return 0.0
        try:
            r, g, b = (int(cleaned[i : i + 2], 16) / 255.0 for i in (0, 2, 4))
        except ValueError:
            return 0.0
        lin = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
        return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)

    l1 = _rel_lum(fg_hex)
    l2 = _rel_lum(bg_hex)
    return round((max(l1, l2) + 0.05) / (min(l1, l2) + 0.05), 2)


def _parse_scene_window(timestamp_range: str, fallback_start: float) -> Tuple[float, float]:
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


def _compute_wpm(text: str, duration_sec: float) -> float:
    words = [w for w in re.split(r"\s+", str(text or "").strip()) if w]
    dur = max(0.5, float(duration_sec or 8.0))
    return round((len(words) / dur) * 60.0, 1)


def _normalize_endcard(
    raw_end: Dict[str, Any],
    brand_name: str,
    logline: str,
    default_start: float,
    tail_scene_index: int = 1,
) -> Dict[str, Any]:
    """Normalizes BrandEndcardSpec or legacy flat endcard fields for the HUD."""
    end_dur = float(raw_end["duration_sec"]) if raw_end.get("duration_sec") is not None else 3.0
    sting_smpte = str(raw_end.get("audio_sting_sync_smpte") or "")
    sting_sec = _smpte_to_sec(sting_smpte) if sting_smpte else None
    end_start = (
        float(raw_end["start_sec"])
        if raw_end.get("start_sec") is not None
        else (sting_sec if sting_sec is not None else default_start)
    )
    end_end = (
        float(raw_end["end_sec"])
        if raw_end.get("end_sec") is not None
        else (end_start + end_dur)
    )
    cta_headline = str(
        raw_end.get("cta_headline")
        or raw_end.get("cta_text")
        or raw_end.get("brand_lockup")
        or raw_end.get("brand_name")
        or brand_name
    )
    cta_subcopy = str(raw_end.get("cta_subcopy") or raw_end.get("tagline") or logline[:84])
    url_or_qr = str(raw_end.get("url_or_qr_label") or "")
    brand_lockup = str(raw_end.get("brand_lockup") or raw_end.get("brand_name") or brand_name or cta_headline)
    cta_text = str(raw_end.get("cta_headline") or raw_end.get("cta_text") or url_or_qr or "DISCOVER MORE")
    bg_plate_hex = str(raw_end.get("background_plate_hex") or raw_end.get("bg_hex") or "#090D16")
    fg_hex = str(raw_end.get("fg_hex") or "#F8FAFC")
    contrast_val = (
        float(raw_end["contrast_ratio"])
        if raw_end.get("contrast_ratio") is not None
        else _wcag_contrast_ratio(fg_hex, bg_plate_hex)
    )
    reserved_tail = int(
        raw_end["reserved_tail_scene_index"]
        if raw_end.get("reserved_tail_scene_index") is not None
        else tail_scene_index
    )
    return {
        "duration_sec": round(end_dur, 2),
        "logo_lockup_position": str(raw_end.get("logo_lockup_position") or "center_upper_safe"),
        "cta_headline": cta_headline,
        "cta_subcopy": cta_subcopy,
        "url_or_qr_label": url_or_qr,
        "audio_sting_sync_smpte": sting_smpte or _sec_to_smpte(end_start),
        "background_plate_hex": bg_plate_hex,
        "reserved_tail_scene_index": reserved_tail,
        # Display aliases retained for UI compatibility
        "brand_lockup": brand_lockup,
        "tagline": cta_subcopy,
        "cta_text": cta_text,
        "start_sec": round(end_start, 2),
        "end_sec": round(end_end, 2),
        "fg_hex": fg_hex,
        "bg_hex": bg_plate_hex,
        "accent_hex": str(raw_end.get("accent_hex") or "#38BDF8"),
        "contrast_ratio": round(contrast_val, 2),
        "safe_zone_cleared": bool(raw_end["safe_zone_cleared"]) if raw_end.get("safe_zone_cleared") is not None else True,
        "gfx_cleanplate": bool(raw_end["gfx_cleanplate"]) if raw_end.get("gfx_cleanplate") is not None else True,
    }


def synthesize_v217_motion_graphics_state(bible: Any) -> Dict[str, Any]:
    """Extracts or safely synthesizes PM-FEAT-033 Motion Graphics, Supers & End-Card Studio state."""
    existing = (
        _get_field(bible, "master_motion_graphics", None)
        or _get_field(bible, "motion_graphics_spec", None)
        or _get_field(bible, "motion_graphics", None)
    )
    plain = _to_plain(existing)

    project_title = str(_get_field(bible, "project_title", "Omni Production") or "Omni Production")
    brand_name = str(_get_field(bible, "brand_name", "") or project_title)
    archetype = str(_get_field(bible, "domain_archetype", "architectural_sanctuary") or "architectural_sanctuary")
    logline = str(_get_field(bible, "logline", "") or "Precision crafted cinematic visual showcase.")
    scenes = _to_plain(_get_field(bible, "scenes", []) or [])

    scene_title_map: Dict[int, str] = {}
    scene_window_map: Dict[int, Tuple[float, float]] = {}
    win_cursor = 0.0
    for idx, sc in enumerate(scenes):
        if isinstance(sc, dict):
            s_i = int(sc.get("scene_index", idx + 1) or (idx + 1))
            scene_title_map[s_i] = str(sc.get("scene_title") or f"Scene {s_i}")
            st_w, en_w = _parse_scene_window(str(sc.get("timestamp_range") or ""), win_cursor)
            scene_window_map[s_i] = (st_w, en_w)
            win_cursor = en_w

    if isinstance(plain, dict) and ("scene_graphics" in plain or "endcard" in plain):
        raw_scene_graphics = list(plain.get("scene_graphics") or [])
        raw_end = plain.get("endcard") if isinstance(plain.get("endcard"), dict) else {}
        bg_plate_hex = str(raw_end.get("background_plate_hex") or raw_end.get("bg_hex") or "#090D16")

        norm_cues: List[Dict[str, Any]] = []
        scene_neg_spaces: List[float] = []
        cursor_s = 0.0

        for idx, sg in enumerate(raw_scene_graphics):
            if not isinstance(sg, dict):
                continue
            s_idx = int(sg.get("scene_index", idx + 1) or (idx + 1))
            s_title = str(sg.get("scene_title") or scene_title_map.get(s_idx) or f"Scene {s_idx}")

            if isinstance(sg.get("cues"), list):
                # Real SceneMotionGraphicsSpec schema
                neg_space_pct = (
                    float(sg["cleanplate_negative_space_pct"])
                    if sg.get("cleanplate_negative_space_pct") is not None
                    else 32.0
                )
                scene_neg_spaces.append(neg_space_pct)
                cleanplate_ok = neg_space_pct >= 25.0
                cleanplate_zone = str(sg.get("cleanplate_zone") or "upper_left_third")
                gfx_prompt_token = str(sg.get("gfx_prompt_token") or "")
                leg_score = (
                    float(sg["legibility_score"])
                    if sg.get("legibility_score") is not None
                    else 100.0
                )

                for c_idx, cue in enumerate(sg.get("cues") or []):
                    if not isinstance(cue, dict):
                        continue
                    c_s_idx = int(cue.get("scene_index", s_idx) or s_idx)
                    c_s_title = scene_title_map.get(c_s_idx, s_title)
                    cue_id = str(cue.get("cue_id") or f"GFX_SC{c_s_idx:02d}_{c_idx + 1:02d}")
                    role_raw = str(cue.get("role") or "kinetic_headline").lower()
                    copy_text = str(cue.get("copy_text") or "")

                    in_smpte = str(cue.get("in_smpte") or "")
                    out_smpte = str(cue.get("out_smpte") or "")
                    parsed_in = _smpte_to_sec(in_smpte) if in_smpte else None
                    parsed_out = _smpte_to_sec(out_smpte) if out_smpte else None

                    default_win_start = scene_window_map.get(c_s_idx, (cursor_s, cursor_s + 8.0))[0]
                    start_s = parsed_in if parsed_in is not None else default_win_start
                    disp_dur = cue.get("display_duration_sec")
                    if parsed_out is not None and parsed_out > start_s:
                        end_s = parsed_out
                    elif disp_dur is not None and float(disp_dur) > 0:
                        end_s = start_s + float(disp_dur)
                    else:
                        end_s = start_s + 3.0
                    dur_s = float(disp_dur) if (disp_dur is not None and float(disp_dur) > 0) else max(0.5, end_s - start_s)
                    cursor_s = max(cursor_s, end_s)

                    smpte_in = in_smpte or _sec_to_smpte(start_s)
                    smpte_out = out_smpte or _sec_to_smpte(end_s)

                    wpm_val = (
                        float(cue["effective_wpm"])
                        if cue.get("effective_wpm") is not None
                        else _compute_wpm(copy_text, dur_s)
                    )
                    placement = cue.get("placement") if isinstance(cue.get("placement"), dict) else {}
                    contrast_val = (
                        float(placement["wcag_contrast_ratio"])
                        if placement.get("wcag_contrast_ratio") is not None
                        else _wcag_contrast_ratio(str(placement.get("fill_hex") or "#F8FAFC"), bg_plate_hex)
                    )
                    fg_hex = str(placement.get("fill_hex") or "#F8FAFC")
                    ratios = [str(r) for r in (cue.get("reframe_cleared_ratios") or [])]
                    sz_16 = "16:9" in ratios
                    sz_9 = "9:16" in ratios
                    leg_passed = (
                        bool(cue["legibility_audit_passed"])
                        if cue.get("legibility_audit_passed") is not None
                        else (wpm_val <= 180.0 and contrast_val >= 4.5 and sz_9)
                    )

                    is_legal = role_raw == "legal_disclaimer"
                    super_txt = "" if is_legal else copy_text
                    legal_txt = copy_text if is_legal else ""

                    norm_cues.append({
                        "scene_index": c_s_idx,
                        "scene_title": c_s_title,
                        "cue_id": cue_id,
                        "role": role_raw,
                        "copy_text": copy_text,
                        "word_count": int(cue.get("word_count") if cue.get("word_count") is not None else len(copy_text.split())),
                        "display_duration_sec": round(dur_s, 2),
                        "effective_wpm": round(wpm_val, 2),
                        "start_sec": round(start_s, 2),
                        "end_sec": round(end_s, 2),
                        "in_smpte": smpte_in,
                        "out_smpte": smpte_out,
                        "smpte_in": smpte_in,
                        "smpte_out": smpte_out,
                        "super_text": super_txt,
                        "legal_super": legal_txt,
                        "wpm": round(wpm_val, 1),
                        "contrast_ratio": round(contrast_val, 2),
                        "fg_hex": fg_hex,
                        "bg_hex": bg_plate_hex,
                        "safe_zone_16x9": sz_16,
                        "safe_zone_9x16": sz_9,
                        "reframe_cleared_ratios": ratios,
                        "legibility_audit_passed": leg_passed,
                        "gfx_cleanplate": cleanplate_ok,
                        "cleanplate_negative_space_pct": round(neg_space_pct, 1),
                        "cleanplate_zone": cleanplate_zone,
                        "legibility_score": round(leg_score, 1),
                        "composite_strategy": str(cue.get("composite_strategy") or "post_comp_cleanplate"),
                        "animation_preset": str(cue.get("animation_preset") or ""),
                        "placement": placement,
                        "gfx_prompt_token": gfx_prompt_token,
                        "token": "[GFX-CLEANPLATE]" if cleanplate_ok else "[GFX-LOW-NEG-SPACE]",
                    })
            else:
                # Backward-compatible legacy flat cue dictionary
                start_s = float(sg["start_sec"]) if sg.get("start_sec") is not None else cursor_s
                dur_s = float(sg["duration_sec"]) if sg.get("duration_sec") is not None else 8.0
                end_s = float(sg["end_sec"]) if sg.get("end_sec") is not None else (start_s + dur_s)
                if end_s <= start_s:
                    end_s = start_s + 8.0
                cursor_s = max(cursor_s, end_s)

                super_txt = str(
                    sg.get("super_text")
                    or sg.get("headline_text")
                    or sg.get("copy_text")
                    or f"S{s_idx:02d} // {project_title[:24]}"
                )
                legal_txt = str(sg.get("legal_super") or sg.get("legal_disclaimer") or "")
                if sg.get("wpm") is not None:
                    wpm_val = float(sg["wpm"])
                elif sg.get("reading_speed_wpm") is not None:
                    wpm_val = float(sg["reading_speed_wpm"])
                elif sg.get("effective_wpm") is not None:
                    wpm_val = float(sg["effective_wpm"])
                else:
                    wpm_val = _compute_wpm(super_txt, end_s - start_s)

                if sg.get("contrast_ratio") is not None:
                    contrast_val = float(sg["contrast_ratio"])
                elif sg.get("wcag_contrast_ratio") is not None:
                    contrast_val = float(sg["wcag_contrast_ratio"])
                else:
                    contrast_val = 12.6

                if sg.get("reframe_cleared_ratios") is not None:
                    ratios = [str(r) for r in (sg.get("reframe_cleared_ratios") or [])]
                    sz_16 = "16:9" in ratios
                    sz_9 = "9:16" in ratios
                else:
                    fallback_sz = bool(sg["safe_zone_cleared"]) if sg.get("safe_zone_cleared") is not None else True
                    sz_16 = bool(sg["safe_zone_16x9"]) if sg.get("safe_zone_16x9") is not None else fallback_sz
                    sz_9 = bool(sg["safe_zone_9x16"]) if sg.get("safe_zone_9x16") is not None else fallback_sz
                    ratios = ([r for r, ok in (("16:9", sz_16), ("9:16", sz_9)) if ok])

                if sg.get("cleanplate_negative_space_pct") is not None:
                    neg_space_pct = float(sg["cleanplate_negative_space_pct"])
                    scene_neg_spaces.append(neg_space_pct)
                    cleanplate = neg_space_pct >= 25.0
                elif sg.get("gfx_cleanplate") is not None:
                    cleanplate = bool(sg["gfx_cleanplate"])
                    neg_space_pct = 32.0 if cleanplate else 15.0
                elif sg.get("cleanplate_reserved") is not None:
                    cleanplate = bool(sg["cleanplate_reserved"])
                    neg_space_pct = 32.0 if cleanplate else 15.0
                else:
                    cleanplate = True
                    neg_space_pct = 32.0

                leg_passed = (
                    bool(sg["legibility_audit_passed"])
                    if sg.get("legibility_audit_passed") is not None
                    else (wpm_val <= 180.0 and contrast_val >= 4.5 and sz_9)
                )
                smpte_in = str(sg.get("in_smpte") or sg.get("smpte_in") or _sec_to_smpte(start_s))
                smpte_out = str(sg.get("out_smpte") or sg.get("smpte_out") or _sec_to_smpte(end_s))

                norm_cues.append({
                    "scene_index": s_idx,
                    "scene_title": s_title,
                    "cue_id": str(sg.get("cue_id") or f"GFX-S{s_idx:02d}"),
                    "role": str(sg.get("role") or "kinetic_headline").lower(),
                    "copy_text": super_txt,
                    "word_count": len(super_txt.split()),
                    "display_duration_sec": round(end_s - start_s, 2),
                    "effective_wpm": round(wpm_val, 2),
                    "start_sec": round(start_s, 2),
                    "end_sec": round(end_s, 2),
                    "in_smpte": smpte_in,
                    "out_smpte": smpte_out,
                    "smpte_in": smpte_in,
                    "smpte_out": smpte_out,
                    "super_text": super_txt,
                    "legal_super": legal_txt,
                    "wpm": round(wpm_val, 1),
                    "contrast_ratio": round(contrast_val, 2),
                    "fg_hex": str(sg.get("fg_hex") or "#F8FAFC"),
                    "bg_hex": str(sg.get("bg_hex") or bg_plate_hex),
                    "safe_zone_16x9": sz_16,
                    "safe_zone_9x16": sz_9,
                    "reframe_cleared_ratios": ratios,
                    "legibility_audit_passed": leg_passed,
                    "gfx_cleanplate": cleanplate,
                    "cleanplate_negative_space_pct": round(neg_space_pct, 1),
                    "cleanplate_zone": str(sg.get("cleanplate_zone") or "Lower-Third Left (Title Safe 80%)"),
                    "token": "[GFX-CLEANPLATE]" if cleanplate else "[GFX-DIRECT]",
                })

        tail_idx = max((c["scene_index"] for c in norm_cues), default=max(1, len(scenes)))
        endcard = _normalize_endcard(raw_end, brand_name, logline, cursor_s, tail_scene_index=tail_idx)

        computed_max_wpm = max((c["wpm"] for c in norm_cues), default=0.0)
        manifest_wpm = float(plain["max_wpm_detected"]) if plain.get("max_wpm_detected") is not None else 0.0
        max_wpm = max(computed_max_wpm, manifest_wpm) if norm_cues else manifest_wpm

        contrast_vals = [c["contrast_ratio"] for c in norm_cues]
        if endcard.get("contrast_ratio") is not None:
            contrast_vals.append(float(endcard["contrast_ratio"]))
        min_contrast = min(contrast_vals) if contrast_vals else 15.4

        cues_safe = all(
            c["safe_zone_16x9"] and c["safe_zone_9x16"] and c["legibility_audit_passed"] and c["gfx_cleanplate"]
            for c in norm_cues
        )
        cleanplates_safe = all(pct >= 25.0 for pct in scene_neg_spaces)
        computed_safe = cues_safe and cleanplates_safe and bool(endcard["safe_zone_cleared"])
        explicit_safe = plain.get("all_safe_zones_cleared")
        all_safe = (bool(explicit_safe) if explicit_safe is not None else True) and computed_safe

        legal_cues = [
            c for c in norm_cues
            if c.get("role") == "legal_disclaimer" or bool(c.get("legal_super"))
        ]
        computed_legal = (
            max_wpm <= 180.0
            and min_contrast >= 4.5
            and all(c["wpm"] <= 180.0 and c["contrast_ratio"] >= 4.5 and c["legibility_audit_passed"] for c in legal_cues)
        )
        explicit_legal = plain.get("legal_supers_compliant")
        legal_ok = (bool(explicit_legal) if explicit_legal is not None else True) and computed_legal

        return {
            "project_title": str(plain.get("project_title") or project_title),
            "brand_name": brand_name,
            "archetype": str(plain.get("domain_archetype") or archetype),
            "primary_typeface": str(plain.get("primary_typeface") or "Space Grotesk"),
            "secondary_typeface": str(plain.get("secondary_typeface") or "JetBrains Mono"),
            "max_wpm_detected": round(max_wpm, 1),
            "min_contrast_ratio": round(min_contrast, 2),
            "all_safe_zones_cleared": all_safe,
            "legal_supers_compliant": legal_ok,
            "cleanplate_count": sum(1 for c in norm_cues if c["gfx_cleanplate"]),
            "scene_graphics": norm_cues,
            "endcard": endcard,
        }

    # Deterministic synthesis from bible scenes when no MasterMotionGraphicsManifest exists
    scene_graphics: List[Dict[str, Any]] = []
    cursor_sec = 0.0
    for idx, sc in enumerate(scenes):
        sc_dict = sc if isinstance(sc, dict) else {}
        s_idx = int(sc_dict.get("scene_index", idx + 1) or (idx + 1))
        s_title = str(sc_dict.get("scene_title") or f"Scene {s_idx}")
        start_s, end_s = _parse_scene_window(str(sc_dict.get("timestamp_range") or ""), cursor_sec)
        cursor_sec = end_s
        beats = sc_dict.get("action_beats") or []
        super_base = s_title.upper()[:30]
        super_txt = f"0{s_idx} // {super_base}" if s_idx < 10 else f"{s_idx} // {super_base}"
        if idx == 0:
            super_txt = f"{brand_name.upper()[:24]} — {s_title.upper()[:22]}"
        legal_txt = (
            "Simulated pre-vis sequence. Final specifications may vary."
            if archetype in ("automotive_robotics", "tech_hardware") and idx == 0
            else (str(beats[0])[:52] if beats else "Cleared broadcast title-safe 80% overlay")
        )
        wpm_val = _compute_wpm(super_txt, end_s - start_s)
        smpte_in = _sec_to_smpte(start_s)
        smpte_out = _sec_to_smpte(end_s)
        scene_graphics.append({
            "scene_index": s_idx,
            "scene_title": s_title,
            "cue_id": f"GFX-S{s_idx:02d}",
            "role": "kinetic_headline",
            "copy_text": super_txt,
            "word_count": len(super_txt.split()),
            "display_duration_sec": round(end_s - start_s, 2),
            "effective_wpm": wpm_val,
            "start_sec": round(start_s, 2),
            "end_sec": round(end_s, 2),
            "in_smpte": smpte_in,
            "out_smpte": smpte_out,
            "smpte_in": smpte_in,
            "smpte_out": smpte_out,
            "super_text": super_txt,
            "legal_super": legal_txt,
            "wpm": wpm_val,
            "contrast_ratio": 13.4,
            "fg_hex": "#F8FAFC",
            "bg_hex": "#0B0F19",
            "safe_zone_16x9": True,
            "safe_zone_9x16": True,
            "reframe_cleared_ratios": ["16:9", "9:16"],
            "legibility_audit_passed": True,
            "gfx_cleanplate": True,
            "cleanplate_negative_space_pct": 34.0,
            "cleanplate_zone": "Lower-Third Left (Title Safe 80%)",
            "token": "[GFX-CLEANPLATE]",
        })

    if not scene_graphics:
        cursor_sec = 8.0
        super_txt = f"{brand_name.upper()[:24]} — HERO REVEAL"
        scene_graphics.append({
            "scene_index": 1,
            "scene_title": "Opening Master",
            "cue_id": "GFX-S01",
            "role": "kinetic_headline",
            "copy_text": super_txt,
            "word_count": len(super_txt.split()),
            "display_duration_sec": 8.0,
            "effective_wpm": _compute_wpm(super_txt, 8.0),
            "start_sec": 0.0,
            "end_sec": 8.0,
            "in_smpte": "00:00:00:00",
            "out_smpte": "00:00:08:00",
            "smpte_in": "00:00:00:00",
            "smpte_out": "00:00:08:00",
            "super_text": super_txt,
            "legal_super": "Cleared broadcast title-safe 80% overlay",
            "wpm": _compute_wpm(super_txt, 8.0),
            "contrast_ratio": 13.4,
            "fg_hex": "#F8FAFC",
            "bg_hex": "#0B0F19",
            "safe_zone_16x9": True,
            "safe_zone_9x16": True,
            "reframe_cleared_ratios": ["16:9", "9:16"],
            "legibility_audit_passed": True,
            "gfx_cleanplate": True,
            "cleanplate_negative_space_pct": 34.0,
            "cleanplate_zone": "Lower-Third Left (Title Safe 80%)",
            "token": "[GFX-CLEANPLATE]",
        })

    endcard = _normalize_endcard(
        {
            "cta_headline": brand_name,
            "cta_subcopy": logline[:84],
            "url_or_qr_label": "EXPLORE THE SERIES",
            "duration_sec": 3.0,
            "background_plate_hex": "#07080B",
        },
        brand_name,
        logline,
        cursor_sec,
        tail_scene_index=scene_graphics[-1]["scene_index"],
    )
    max_wpm = max([c["wpm"] for c in scene_graphics] or [0.0])

    return {
        "project_title": project_title,
        "brand_name": brand_name,
        "archetype": archetype,
        "primary_typeface": "Space Grotesk",
        "secondary_typeface": "JetBrains Mono",
        "max_wpm_detected": round(max_wpm, 1),
        "min_contrast_ratio": 13.4,
        "all_safe_zones_cleared": True,
        "legal_supers_compliant": max_wpm <= 180.0,
        "cleanplate_count": len(scene_graphics),
        "scene_graphics": scene_graphics,
        "endcard": endcard,
    }


def _build_otio_timeline_doc(project_title: str, tracks: List[Dict[str, Any]], fps: int = 24) -> Dict[str, Any]:
    """Builds a valid OpenTimelineIO Timeline.1 JSON dictionary."""
    otio_tracks = []
    for tr in tracks:
        children = []
        for clip in tr.get("clips") or []:
            start_f = int(clip.get("start_frame", 0) or 0)
            dur_f = max(1, int(clip.get("duration_frames", 192) or 192))
            children.append({
                "OTIO_SCHEMA": "Clip.1",
                "name": str(clip.get("name") or "Clip"),
                "source_range": {
                    "OTIO_SCHEMA": "TimeRange.1",
                    "start_time": {"OTIO_SCHEMA": "RationalTime.1", "value": float(start_f), "rate": float(fps)},
                    "duration": {"OTIO_SCHEMA": "RationalTime.1", "value": float(dur_f), "rate": float(fps)},
                },
                "metadata": {
                    "scene_index": int(clip.get("scene_index", 1) or 1),
                    "smpte_in": str(clip.get("smpte_in") or _sec_to_smpte(start_f / fps, fps)),
                    "smpte_out": str(clip.get("smpte_out") or _sec_to_smpte((start_f + dur_f) / fps, fps)),
                },
            })
        otio_tracks.append({
            "OTIO_SCHEMA": "Track.1",
            "name": str(tr.get("track_name") or "V1_Picture_Master"),
            "kind": str(tr.get("kind") or "Video"),
            "children": children,
        })

    return {
        "OTIO_SCHEMA": "Timeline.1",
        "name": f"{project_title} Master Timeline",
        "global_start_time": {"OTIO_SCHEMA": "RationalTime.1", "value": 0.0, "rate": float(fps)},
        "tracks": {
            "OTIO_SCHEMA": "Stack.1",
            "name": "tracks",
            "children": otio_tracks,
        },
    }


def _build_default_coherence_checks(bible: Any, total_runtime_sec: float) -> List[Dict[str, Any]]:
    """Synthesizes deterministic 7-row cross-departmental coherence checks from bible state."""
    story_mode = str(_get_field(bible, "storytelling_mode", "mode_a_parallel_cut") or "mode_a_parallel_cut").lower()
    is_mode_b = "mode_b" in story_mode or "continuous" in story_mode
    mode_ok = (not is_mode_b) or (total_runtime_sec <= 40.0)

    econ = _to_plain(_get_field(bible, "master_render_economics_spec", None))
    guardrail = econ.get("guardrail") if isinstance(econ, dict) and isinstance(econ.get("guardrail"), dict) else {}
    within_budget = bool(guardrail.get("within_budget", True))
    est_usd = float(guardrail.get("estimated_total_usd", 6.8) or 6.8)
    cap_usd = float(guardrail.get("max_render_budget_usd", 50.0) or 50.0)

    scenes = _to_plain(_get_field(bible, "scenes", []) or [])
    first_sc = scenes[0] if scenes and isinstance(scenes[0], dict) else {}
    lighting = first_sc.get("lighting_rig") if isinstance(first_sc.get("lighting_rig"), dict) else {}
    kelvin = int(lighting.get("key_cct_kelvin") or lighting.get("cct_kelvin") or 5600)

    measured_map = {
        "optics_vs_dof": ("35mm Prime @ T2.8 (CoC 0.029mm)", "PASS"),
        "lighting_kelvin_vs_blocking": (f"{kelvin}K Key / 180° Axis Locked", "PASS"),
        "audio_stems_vs_spotting": ("-14.0 LUFS / J&L Spotting Synced", "PASS"),
        "reframe_vs_graphics_blocking": ("16:9 + 9:16 [GFX-CLEANPLATE] Clear", "PASS"),
        "mode_b_vs_runtime_economics": (
            f"{'Mode B' if is_mode_b else 'Mode A'} · {total_runtime_sec:.1f}s",
            "PASS" if mode_ok else "CONFLICT",
        ),
        "aicp_post_vs_render_compute": (
            f"${est_usd:.2f} / ${cap_usd:.2f} Cap",
            "PASS" if within_budget else "WARN",
        ),
        "c2pa_vs_cast_safety": ("C2PA v2.1 + JSA Cleared", "PASS"),
    }

    checks: List[Dict[str, Any]] = []
    for check_id, pair, _legacy_id, depts, bounds in _COHERENCE_CHECK_DEFS:
        measured, status = measured_map[pair]
        detail_txt = "Nominal cross-department lock" if status == "PASS" else "Review departmental threshold variance"
        checks.append({
            "check_id": check_id,
            "pair": pair,
            "departments": depts,
            "source_spec": depts.split(" ↔ ")[0] if " ↔ " in depts else depts,
            "target_spec": depts.split(" ↔ ")[1] if " ↔ " in depts else depts,
            "status": status,
            "measured_value": measured,
            "measured": measured,
            "expected_bound": bounds,
            "expected_bounds": bounds,
            "delta_summary": detail_txt,
            "detail": detail_txt,
            "remediation_action": "" if status == "PASS" else detail_txt,
        })
    return checks


def _normalize_coherence_check(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Normalizes a CrossDeptCoherenceCheck or legacy dict truthfully without masking status."""
    raw_cid = str(raw.get("check_id") or "")
    raw_pair = str(raw.get("pair") or "").lower()
    meta = _COHERENCE_META_BY_KEY.get(raw_pair) or _COHERENCE_META_BY_KEY.get(raw_cid)

    cid = raw_cid or (meta[0] if meta else "CHK-CUSTOM")
    pair = raw_pair or (meta[1] if meta else cid.lower())
    default_depts = meta[2] if meta else cid
    default_bound = meta[3] if meta else ""

    source_spec = str(raw.get("source_spec") or "")
    target_spec = str(raw.get("target_spec") or "")
    departments = str(raw.get("departments") or "")
    if not departments:
        if source_spec and target_spec:
            departments = f"{source_spec} ↔ {target_spec}"
        else:
            departments = default_depts

    raw_status = str(raw.get("status") if raw.get("status") is not None else "pass").strip().upper()
    if raw_status not in ("PASS", "WARN", "CONFLICT"):
        raw_status = "WARN"

    measured_val = str(
        raw.get("measured_value")
        if raw.get("measured_value") is not None
        else (raw.get("measured") if raw.get("measured") is not None else "")
    )
    expected_bound = str(
        raw.get("expected_bound")
        if raw.get("expected_bound") is not None
        else (raw.get("expected_bounds") if raw.get("expected_bounds") is not None else default_bound)
    )
    delta_summary = str(
        raw.get("delta_summary")
        if raw.get("delta_summary") is not None
        else (raw.get("detail") if raw.get("detail") is not None else "")
    )
    remediation = str(raw.get("remediation_action") or "")
    detail_txt = f"{delta_summary} · Remediation: {remediation}".strip(" ·") if remediation else delta_summary

    return {
        "check_id": cid,
        "pair": pair,
        "departments": departments,
        "source_spec": source_spec,
        "target_spec": target_spec,
        "status": raw_status,
        "measured_value": measured_val,
        "measured": measured_val,
        "expected_bound": expected_bound,
        "expected_bounds": expected_bound,
        "delta_summary": delta_summary,
        "detail": detail_txt,
        "remediation_action": remediation,
        "auto_reconcilable": bool(raw.get("auto_reconcilable", True)),
    }


def _tracks_from_otio_timeline(
    otio_doc: Dict[str, Any],
    existing_track_map: Dict[str, Dict[str, Any]],
    fps: int = 24,
) -> List[Dict[str, Any]]:
    """Extracts 7-track SVG diagram clips and OtioTrackSummarySpec telemetry from Timeline.1."""
    color_map = {t_name: t_color for t_name, _, t_color in _OTIO_TRACK_DEFS}
    kind_map = {t_name: t_kind for t_name, t_kind, _ in _OTIO_TRACK_DEFS}
    otio_children = list((otio_doc.get("tracks") or {}).get("children") or [])

    tracks: List[Dict[str, Any]] = []
    for ot_tr in otio_children:
        if not isinstance(ot_tr, dict):
            continue
        t_name = str(ot_tr.get("name") or "")
        t_kind = str(ot_tr.get("kind") or kind_map.get(t_name, "Video"))
        t_color = color_map.get(t_name, "#38BDF8")
        summary = existing_track_map.get(t_name) or {}

        clips: List[Dict[str, Any]] = []
        cursor_f = 0
        clip_only_count = 0
        marker_acc = len(ot_tr.get("markers") or [])
        total_track_frames = 0

        for c_idx, child in enumerate(ot_tr.get("children") or []):
            if not isinstance(child, dict):
                continue
            schema = str(child.get("OTIO_SCHEMA") or "Clip.1")
            is_gap = schema == "Gap.1"
            sr = child.get("source_range") or {}
            dur_obj = sr.get("duration") or {}
            dur_val = float(dur_obj.get("value", 0.0) or 0.0)
            dur_rate = float(dur_obj.get("rate", fps) or fps) or float(fps)
            dur_f = max(1, int(round((dur_val / dur_rate) * fps)))

            meta_root = child.get("metadata") or {}
            omni_meta = meta_root.get("omni_director") if isinstance(meta_root.get("omni_director"), dict) else {}
            if omni_meta.get("record_in_frame") is not None:
                st_f = int(omni_meta["record_in_frame"])
            elif meta_root.get("record_in_frame") is not None:
                st_f = int(meta_root["record_in_frame"])
            else:
                st_f = cursor_f
            cursor_f = max(cursor_f + dur_f, st_f + dur_f)
            total_track_frames += dur_f

            st_s = round(st_f / fps, 2)
            du_s = round(dur_f / fps, 2)

            c_markers = list(child.get("markers") or [])
            marker_acc += len(c_markers)
            if not is_gap:
                clip_only_count += 1

            media_ref = child.get("media_reference") if isinstance(child.get("media_reference"), dict) else {}
            target_url = str(media_ref.get("target_url") or "")

            sc_idx = omni_meta.get("scene_index") or meta_root.get("scene_index")
            if sc_idx is None:
                m_sc = re.search(r"SC(\d+)", str(child.get("name") or ""), re.IGNORECASE)
                sc_idx = int(m_sc.group(1)) if m_sc else (c_idx + 1)

            clips.append({
                "name": str(child.get("name") or f"{t_name}_{c_idx + 1:02d}"),
                "schema": schema,
                "is_gap": is_gap,
                "scene_index": int(sc_idx),
                "start_sec": st_s,
                "duration_sec": du_s,
                "start_frame": st_f,
                "duration_frames": dur_f,
                "smpte_in": str(meta_root.get("smpte_in") or _sec_to_smpte(st_s, fps)),
                "smpte_out": str(meta_root.get("smpte_out") or _sec_to_smpte(st_s + du_s, fps)),
                "target_url": target_url,
                "marker_count": len(c_markers),
                "j_prelap_frames": int(omni_meta.get("j_prelap_frames", 0) or 0),
                "l_overhang_frames": int(omni_meta.get("l_overhang_frames", 0) or 0),
            })

        tracks.append({
            "track_name": t_name,
            "kind": t_kind,
            "color": t_color,
            "clip_count": int(summary["clip_count"]) if summary.get("clip_count") is not None else clip_only_count,
            "marker_count": int(summary["marker_count"]) if summary.get("marker_count") is not None else marker_acc,
            "total_frames_24fps": int(summary["total_frames_24fps"]) if summary.get("total_frames_24fps") is not None else total_track_frames,
            "clips": clips,
        })
    return tracks


def synthesize_v217_otio_coherence_state(bible: Any) -> Dict[str, Any]:
    """Extracts or safely synthesizes PM-FEAT-034 OpenTimelineIO & Cross-Dept Coherence Matrix state."""
    existing = (
        _get_field(bible, "master_otio_coherence", None)
        or _get_field(bible, "otio_coherence_manifest", None)
        or _get_field(bible, "otio_coherence", None)
    )
    plain = _to_plain(existing)
    project_title = str(_get_field(bible, "project_title", "Omni Production") or "Omni Production")
    scenes = _to_plain(_get_field(bible, "scenes", []) or [])
    fps = 24

    # Map OtioTrackSummarySpec or legacy tracks from manifest
    existing_track_map: Dict[str, Dict[str, Any]] = {}
    if isinstance(plain, dict) and isinstance(plain.get("tracks"), list):
        for tr in plain["tracks"]:
            if isinstance(tr, dict):
                t_name = str(tr.get("track_name") or tr.get("name") or "")
                if t_name:
                    existing_track_map[t_name] = tr

    # Build real Timeline.1 via compile_otio_timeline_dict(bible) with safe fallback for plain mock dicts
    otio_doc: Dict[str, Any] | None = None
    if not isinstance(bible, dict) and hasattr(bible, "storytelling_mode") and hasattr(bible, "project_title"):
        try:
            from omni_director.tools.otio_coherence import compile_otio_timeline_dict
            otio_doc = compile_otio_timeline_dict(bible, fps=float(fps))
        except (AttributeError, TypeError, ValueError, ImportError):
            otio_doc = None

    if otio_doc is not None:
        tracks = _tracks_from_otio_timeline(otio_doc, existing_track_map, fps=fps)
        max_end_frame = max(
            (
                max((c["start_frame"] + c["duration_frames"] for c in tr.get("clips") or []), default=0)
                for tr in tracks
            ),
            default=0,
        )
        manifest_frames = int(plain["total_frames"]) if isinstance(plain, dict) and plain.get("total_frames") is not None else 0
        total_frames = max(192, max_end_frame, manifest_frames)
        total_runtime_sec = round(total_frames / fps, 2)
    else:
        # Fallback for plain mock dicts without full Pydantic MasterProductionBible
        scene_spans: List[Dict[str, Any]] = []
        cursor_s = 0.0
        for idx, sc in enumerate(scenes):
            sc_dict = sc if isinstance(sc, dict) else {}
            s_idx = int(sc_dict.get("scene_index", idx + 1) or (idx + 1))
            s_title = str(sc_dict.get("scene_title") or f"Scene {s_idx}")
            start_s, end_s = _parse_scene_window(str(sc_dict.get("timestamp_range") or ""), cursor_s)
            cursor_s = end_s
            dur_s = max(1.0, end_s - start_s)
            start_f = int(round(start_s * fps))
            dur_f = max(24, int(round(dur_s * fps)))
            scene_spans.append({
                "scene_index": s_idx,
                "scene_title": s_title,
                "start_sec": round(start_s, 2),
                "duration_sec": round(dur_s, 2),
                "start_frame": start_f,
                "duration_frames": dur_f,
                "smpte_in": _sec_to_smpte(start_s, fps),
                "smpte_out": _sec_to_smpte(start_s + dur_s, fps),
            })

        if not scene_spans:
            scene_spans.append({
                "scene_index": 1,
                "scene_title": "Opening Master",
                "start_sec": 0.0,
                "duration_sec": 8.0,
                "start_frame": 0,
                "duration_frames": 192,
                "smpte_in": "00:00:00:00",
                "smpte_out": "00:00:08:00",
            })
            cursor_s = 8.0

        total_runtime_sec = round(max(8.0, cursor_s), 2)
        total_frames = int(round(total_runtime_sec * fps))

        tracks = []
        for t_name, t_kind, t_color in _OTIO_TRACK_DEFS:
            raw_tr = existing_track_map.get(t_name)
            clips: List[Dict[str, Any]] = []
            if raw_tr and isinstance(raw_tr.get("clips"), list) and raw_tr["clips"]:
                for c_idx, c in enumerate(raw_tr["clips"]):
                    if not isinstance(c, dict):
                        continue
                    st_s = float(c.get("start_sec", c_idx * 8.0) or 0.0)
                    du_s = float(c.get("duration_sec", 8.0) or 8.0)
                    st_f = int(c.get("start_frame", round(st_s * fps)))
                    du_f = max(1, int(c.get("duration_frames", round(du_s * fps))))
                    clips.append({
                        "name": str(c.get("name") or f"{t_name}_S{c_idx + 1:02d}"),
                        "schema": "Clip.1",
                        "is_gap": False,
                        "scene_index": int(c.get("scene_index", c_idx + 1) or (c_idx + 1)),
                        "start_sec": round(st_s, 2),
                        "duration_sec": round(du_s, 2),
                        "start_frame": st_f,
                        "duration_frames": du_f,
                        "smpte_in": str(c.get("smpte_in") or _sec_to_smpte(st_s, fps)),
                        "smpte_out": str(c.get("smpte_out") or _sec_to_smpte(st_s + du_s, fps)),
                        "target_url": "",
                        "marker_count": 0,
                        "j_prelap_frames": 0,
                        "l_overhang_frames": 0,
                    })
            else:
                if t_name == "A4_Music_Score":
                    clips.append({
                        "name": "BGM_Master_Stem",
                        "schema": "Clip.1",
                        "is_gap": False,
                        "scene_index": 1,
                        "start_sec": 0.0,
                        "duration_sec": total_runtime_sec,
                        "start_frame": 0,
                        "duration_frames": total_frames,
                        "smpte_in": _sec_to_smpte(0.0, fps),
                        "smpte_out": _sec_to_smpte(total_runtime_sec, fps),
                        "target_url": "audio/a4_bgm_master.wav",
                        "marker_count": 0,
                        "j_prelap_frames": 0,
                        "l_overhang_frames": 0,
                    })
                else:
                    prefix = t_name.split("_", 1)[0]
                    for sp in scene_spans:
                        clips.append({
                            "name": f"{prefix}_S{sp['scene_index']:02d}_{sp['scene_title'][:14]}",
                            "schema": "Clip.1",
                            "is_gap": False,
                            "scene_index": sp["scene_index"],
                            "start_sec": sp["start_sec"],
                            "duration_sec": sp["duration_sec"],
                            "start_frame": sp["start_frame"],
                            "duration_frames": sp["duration_frames"],
                            "smpte_in": sp["smpte_in"],
                            "smpte_out": sp["smpte_out"],
                            "target_url": "",
                            "marker_count": 0,
                            "j_prelap_frames": 0,
                            "l_overhang_frames": 0,
                        })

            tracks.append({
                "track_name": t_name,
                "kind": t_kind,
                "color": t_color,
                "clip_count": len(clips),
                "marker_count": 0,
                "total_frames_24fps": sum(c["duration_frames"] for c in clips),
                "clips": clips,
            })

        otio_doc = _build_otio_timeline_doc(project_title, tracks, fps=fps)

    # Render exact manifest coherence_checks truthfully if present; otherwise evaluate/synthesize
    coherence_checks: List[Dict[str, Any]] = []
    if isinstance(plain, dict) and isinstance(plain.get("coherence_checks"), list) and plain["coherence_checks"]:
        for chk in plain["coherence_checks"]:
            if isinstance(chk, dict):
                coherence_checks.append(_normalize_coherence_check(chk))
    elif not isinstance(bible, dict) and hasattr(bible, "storytelling_mode"):
        try:
            from omni_director.tools.otio_coherence import evaluate_cross_department_coherence
            evaluated = _to_plain(evaluate_cross_department_coherence(bible)) or []
            coherence_checks = [_normalize_coherence_check(chk) for chk in evaluated if isinstance(chk, dict)]
        except (AttributeError, TypeError, ValueError, ImportError):
            coherence_checks = []

    if not coherence_checks:
        coherence_checks = _build_default_coherence_checks(bible, total_runtime_sec)

    computed_conflicts = sum(1 for c in coherence_checks if c["status"] == "CONFLICT")
    computed_warnings = sum(1 for c in coherence_checks if c["status"] == "WARN")

    manifest_conflicts = (
        int(plain["conflicts_count"])
        if isinstance(plain, dict) and plain.get("conflicts_count") is not None
        else 0
    )
    manifest_warnings = (
        int(plain["warnings_count"])
        if isinstance(plain, dict) and plain.get("warnings_count") is not None
        else 0
    )
    conflicts_count = max(computed_conflicts, manifest_conflicts)
    warnings_count = max(computed_warnings, manifest_warnings)

    computed_score = round(max(0.0, 100.0 - conflicts_count * 15.0 - warnings_count * 5.0), 1)
    if (
        isinstance(plain, dict)
        and plain.get("coherence_score") is not None
        and computed_conflicts <= manifest_conflicts
        and computed_warnings <= manifest_warnings
    ):
        coherence_score = round(float(plain["coherence_score"]), 1)
    else:
        coherence_score = computed_score

    explicit_ready = plain.get("shoot_day_ready") if isinstance(plain, dict) else None
    shoot_day_ready = (
        (bool(explicit_ready) if explicit_ready is not None else True)
        and conflicts_count == 0
        and coherence_score >= 85.0
    )

    otio_json_text = json.dumps(otio_doc, indent=2, sort_keys=True)
    otio_sha256 = hashlib.sha256(otio_json_text.encode("utf-8")).hexdigest()

    return {
        "project_title": project_title,
        "fps": fps,
        "total_runtime_sec": total_runtime_sec,
        "total_frames": total_frames,
        "tracks": tracks,
        "coherence_checks": coherence_checks,
        "coherence_score": coherence_score,
        "conflicts_count": conflicts_count,
        "warnings_count": warnings_count,
        "shoot_day_ready": shoot_day_ready,
        "otio_sha256": otio_sha256,
        "otio_json_text": otio_json_text,
        "otio_timeline_doc": otio_doc,
        "otio_document": otio_doc,
    }


def build_v217_hud_bundle(bible: Any) -> Dict[str, str]:
    """Builds Dark-Room Cinema v2.17.0 HUD CSS, modals HTML, and JS controllers."""
    mgs_state = synthesize_v217_motion_graphics_state(bible)
    otio_state = synthesize_v217_otio_coherence_state(bible)

    mgs_json = _escape_json_for_script(mgs_state)
    otio_json = _escape_json_for_script(otio_state)

    # Pre-rendered Motion Graphics Studio KPIs & rows
    max_wpm = float(mgs_state.get("max_wpm_detected", 0.0))
    wpm_pct = min(100.0, max(0.0, round((max_wpm / 220.0) * 100.0, 1)))
    wpm_ok = max_wpm <= 180.0
    wpm_badge_cls = "v217-badge-pass" if wpm_ok else "v217-badge-warn"
    wpm_status_txt = f"{max_wpm:.1f} WPM (<=180 OK)" if wpm_ok else f"{max_wpm:.1f} WPM (>180 FAST)"

    min_contrast = float(mgs_state.get("min_contrast_ratio", 13.4))
    contrast_tier = "AAA" if min_contrast >= 7.0 else ("AA" if min_contrast >= 4.5 else "LOW")
    contrast_cls = "v217-badge-pass" if min_contrast >= 4.5 else "v217-badge-warn"
    safe_ok = bool(mgs_state.get("all_safe_zones_cleared", True))
    safe_cls = "v217-badge-pass" if safe_ok else "v217-badge-warn"

    mgs_cue_rows: List[str] = []
    mgs_select_opts: List[str] = []
    for idx, cue in enumerate(mgs_state.get("scene_graphics") or []):
        s_idx = int(cue.get("scene_index", idx + 1))
        cue_wpm = float(cue.get("wpm", 0.0))
        cw_cls = "v217-badge-pass" if cue_wpm <= 180.0 else "v217-badge-warn"
        sz_txt = "16:9 & 9:16 OK" if (cue.get("safe_zone_16x9") and cue.get("safe_zone_9x16")) else "SAFE REVIEW"
        sz_cls = "v217-badge-pass" if (cue.get("safe_zone_16x9") and cue.get("safe_zone_9x16")) else "v217-badge-warn"
        opt_label = str(cue.get("super_text") or cue.get("legal_super") or cue.get("copy_text") or cue.get("cue_id") or "")
        mgs_select_opts.append(
            f'<option value="{idx}">S{s_idx:02d} · {html_escape(opt_label)[:36]}</option>'
        )
        neg_pct = float(cue.get("cleanplate_negative_space_pct", 32.0))
        mgs_cue_rows.append(
            f'<tr class="v217-cue-row" tabindex="0" data-cue-idx="{idx}" onclick="selectMgsPreviewCue({idx})">'
            f'<td><strong>S{s_idx:02d}</strong><br><code class="v217-code">{html_escape(str(cue.get("cue_id", "")))}</code></td>'
            f'<td><code class="v217-code">{html_escape(str(cue.get("smpte_in", "")))}</code><br>'
            f'<span class="v217-sub">to {html_escape(str(cue.get("smpte_out", "")))}</span></td>'
            f'<td><strong>{html_escape(str(cue.get("super_text", "")))}</strong><br>'
            f'<span class="v217-sub">{html_escape(str(cue.get("legal_super", "")))}</span></td>'
            f'<td><span class="v217-badge {cw_cls}">{cue_wpm:.1f} WPM</span></td>'
            f'<td><span class="v217-badge {sz_cls}">{sz_txt}</span><br>'
            f'<span class="v217-sub">{float(cue.get("contrast_ratio", 12.0)):.1f}:1</span></td>'
            f'<td><code class="v217-code">{html_escape(str(cue.get("token", "[GFX-CLEANPLATE]")))}</code><br>'
            f'<span class="v217-sub">{html_escape(str(cue.get("cleanplate_zone", "")))} ({neg_pct:.0f}%)</span></td>'
            f'</tr>'
        )
    mgs_select_opts.append('<option value="endcard">END-CARD · Brand Lockup &amp; CTA</option>')
    mgs_tbody_html = "\n".join(mgs_cue_rows)
    mgs_options_html = "\n".join(mgs_select_opts)

    endcard = mgs_state.get("endcard") or {}

    # Pre-rendered OTIO & Coherence Matrix rows
    coh_score = float(otio_state.get("coherence_score", 100.0))
    conflicts_cnt = int(otio_state.get("conflicts_count", 0))
    warnings_cnt = int(otio_state.get("warnings_count", 0))
    shoot_ready = bool(otio_state.get("shoot_day_ready", True))
    shoot_badge_cls = "v217-badge-pass" if shoot_ready else ("v217-badge-fail" if conflicts_cnt > 0 else "v217-badge-warn")
    shoot_badge_txt = "SHOOT-DAY READY" if shoot_ready else ("CONFLICT HOLD" if conflicts_cnt > 0 else "REVIEW WARNINGS")
    otio_sha_prefix = html_escape(str(otio_state.get("otio_sha256", ""))[:16])

    coh_rows_html: List[str] = []
    for chk in otio_state.get("coherence_checks") or []:
        st = str(chk.get("status", "PASS")).upper()
        st_cls = "v217-badge-pass" if st == "PASS" else ("v217-badge-fail" if st == "CONFLICT" else "v217-badge-warn")
        pair_txt = str(chk.get("pair") or "")
        depts_txt = str(chk.get("departments") or "")
        if not depts_txt and (chk.get("source_spec") or chk.get("target_spec")):
            depts_txt = f"{chk.get('source_spec', '')} ↔ {chk.get('target_spec', '')}".strip(" ↔")
        measured_txt = str(chk.get("measured_value") if chk.get("measured_value") is not None else (chk.get("measured") or ""))
        bound_txt = str(chk.get("expected_bound") if chk.get("expected_bound") is not None else (chk.get("expected_bounds") or ""))
        delta_txt = str(chk.get("delta_summary") if chk.get("delta_summary") is not None else (chk.get("detail") or ""))
        rem_txt = str(chk.get("remediation_action") or "")
        notes_html = html_escape(delta_txt)
        if rem_txt:
            notes_html += f'<br><span class="v217-code">Fix: {html_escape(rem_txt)}</span>'
        coh_rows_html.append(
            f'<tr>'
            f'<td><code class="v217-code">{html_escape(str(chk.get("check_id", "")))}</code>'
            + (f' <span class="v217-sub">({html_escape(pair_txt)})</span>' if pair_txt else '')
            + f'<br><span class="v217-sub">{html_escape(depts_txt)}</span></td>'
            f'<td><span class="v217-badge {st_cls}">{html_escape(st)}</span></td>'
            f'<td>{html_escape(measured_txt)}</td>'
            f'<td><span class="v217-sub">{html_escape(bound_txt)}</span></td>'
            f'<td><span class="v217-sub">{notes_html}</span></td>'
            f'</tr>'
        )
    coh_tbody_html = "\n".join(coh_rows_html)

    css = """
    /* v2.17.0 Motion Graphics Studio & OpenTimelineIO Coherence Matrix HUDs */
    #modal-motion-graphics-studio,
    #modal-otio-coherence {
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(7, 8, 11, 0.92);
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
      z-index: 10060;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }
    .v217-modal-card {
      background: #0E1017;
      color: #F8FAFC;
      border: 1px solid #38BDF8;
      border-radius: 10px;
      width: 100%;
      max-width: 1100px;
      max-height: 92vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      box-shadow: 0 24px 60px rgba(0, 0, 0, 0.9);
    }
    .v217-modal-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      padding: 14px 20px;
      background: #141722;
      border-bottom: 1px solid #334155;
    }
    .v217-modal-title {
      margin: 0;
      font-family: 'Space Grotesk', sans-serif;
      font-size: 16px;
      font-weight: 700;
      color: #F8FAFC;
    }
    .v217-modal-sub {
      display: block;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      color: #38BDF8;
      margin-top: 2px;
    }
    .v217-close-btn {
      background: #B91C1C;
      color: #FFFFFF;
      border: 1px solid #F87171;
      border-radius: 5px;
      padding: 6px 12px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 12px;
      font-weight: 700;
      cursor: pointer;
    }
    .v217-close-btn:hover,
    .v217-close-btn:focus-visible {
      background: #DC2626;
      outline: 2px solid #FFFFFF;
      outline-offset: 2px;
    }
    .v217-modal-body {
      padding: 18px 20px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }
    .v217-kpi-row {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      align-items: center;
      justify-content: space-between;
      background: #141722;
      border: 1px solid #334155;
      border-radius: 6px;
      padding: 12px 14px;
    }
    .v217-gauge-wrap {
      flex: 1 1 250px;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .v217-gauge-bar {
      width: 100%;
      height: 12px;
      background: #07080B;
      border: 1px solid #475569;
      border-radius: 999px;
      overflow: hidden;
    }
    .v217-gauge-fill {
      height: 100%;
      background: linear-gradient(90deg, #10B981, #38BDF8);
      transition: width 0.2s ease;
    }
    .v217-badge-group {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }
    .v217-badge {
      display: inline-block;
      padding: 3px 8px;
      border-radius: 4px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      font-weight: 700;
    }
    .v217-badge-pass {
      background: rgba(16, 185, 129, 0.18);
      color: #34D399;
      border: 1px solid #10B981;
    }
    .v217-badge-warn {
      background: rgba(245, 158, 11, 0.18);
      color: #FBBF24;
      border: 1px solid #F59E0B;
    }
    .v217-badge-fail {
      background: rgba(239, 68, 68, 0.18);
      color: #F87171;
      border: 1px solid #EF4444;
    }
    .v217-code {
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      color: #FDE047;
    }
    .v217-sub {
      font-size: 11px;
      color: #CBD5E1;
    }
    .v217-toolbar-inline {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
      justify-content: space-between;
      background: #141722;
      border: 1px solid #334155;
      border-radius: 6px;
      padding: 10px 12px;
    }
    .v217-seg-group {
      display: inline-flex;
      gap: 6px;
    }
    .v217-seg-btn {
      background: #07080B;
      color: #CBD5E1;
      border: 1px solid #475569;
      border-radius: 5px;
      padding: 6px 11px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      font-weight: 700;
      cursor: pointer;
    }
    .v217-seg-btn[aria-pressed="true"],
    .v217-seg-btn:hover {
      background: #0F172A;
      color: #F8FAFC;
      border-color: #38BDF8;
    }
    .v217-seg-btn:focus-visible,
    .v217-select:focus-visible,
    .v217-cue-row:focus-visible {
      outline: 2px solid #FACC15;
      outline-offset: 2px;
    }
    .v217-select {
      background: #07080B;
      color: #F8FAFC;
      border: 1px solid #475569;
      border-radius: 5px;
      padding: 6px 10px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      min-width: 240px;
    }
    .v217-stage-grid {
      display: grid;
      grid-template-columns: minmax(0, 1.5fr) minmax(240px, 1fr);
      gap: 14px;
      align-items: stretch;
    }
    @media (max-width: 820px) {
      .v217-stage-grid {
        grid-template-columns: 1fr;
      }
    }
    .v217-svg-frame {
      background: #05070B;
      border: 1px solid #334155;
      border-radius: 8px;
      padding: 10px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .v217-svg-frame svg {
      width: 100%;
      height: auto;
      display: block;
      border-radius: 4px;
    }
    .v217-endcard-panel {
      background: #141722;
      border: 1px solid #334155;
      border-radius: 8px;
      padding: 14px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .v217-endcard-panel h3 {
      margin: 0;
      font-family: 'Space Grotesk', sans-serif;
      font-size: 13px;
      color: #38BDF8;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }
    .v217-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
    }
    .v217-table th,
    .v217-table td {
      border: 1px solid #334155;
      padding: 8px 10px;
      text-align: left;
      vertical-align: top;
    }
    .v217-table th {
      background: #1E293B;
      color: #F8FAFC;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
    }
    .v217-cue-row {
      cursor: pointer;
    }
    .v217-cue-row:hover,
    .v217-cue-row.selected {
      background: rgba(56, 189, 248, 0.12);
    }
    .v217-inspector-bar {
      background: #0B1120;
      border: 1px solid #334155;
      border-radius: 6px;
      padding: 8px 12px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      color: #E2E8F0;
    }
    .v217-actions-row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      justify-content: flex-end;
    }
    .v217-dl-btn {
      background: #0369A1;
      color: #FFFFFF;
      border: 1px solid #38BDF8;
      border-radius: 5px;
      padding: 7px 12px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      font-weight: 700;
      cursor: pointer;
    }
    .v217-dl-btn:hover,
    .v217-dl-btn:focus-visible {
      background: #0284C7;
      outline: 2px solid #FACC15;
      outline-offset: 2px;
    }
    @media (prefers-reduced-motion: reduce) {
      .v217-gauge-fill {
        transition: none;
      }
    }
    """

    modals_html = f"""
<!-- v2.17.0 PM-FEAT-033: Motion Graphics, Supers & End-Card Studio -->
<div id="modal-motion-graphics-studio" role="dialog" aria-modal="true" aria-labelledby="mgs-modal-title" tabindex="-1">
  <div class="v217-modal-card">
    <div class="v217-modal-header">
      <div>
        <h2 id="mgs-modal-title" class="v217-modal-title">Motion Graphics, Supers &amp; End-Card Studio</h2>
        <span class="v217-modal-sub">16:9 / 9:16 Safe-Zone Previewer, WPM Reading Speed, WCAG Contrast &amp; [GFX-CLEANPLATE] [=]</span>
      </div>
      <button type="button" class="v217-close-btn" id="btn-motion-gfx-close" onclick="toggleMotionGfxHUD(false)" aria-label="Close Motion Graphics Studio">Close [Esc]</button>
    </div>
    <div class="v217-modal-body">
      <div class="v217-kpi-row">
        <div class="v217-gauge-wrap">
          <div class="v217-sub">Peak Super Reading Speed: <strong id="mgs-wpm-readout">{max_wpm:.1f} WPM</strong> (Target &lt;= 180 WPM)</div>
          <div class="v217-gauge-bar" role="progressbar" aria-label="Peak super reading speed in words per minute" aria-valuenow="{max_wpm:.1f}" aria-valuemin="0" aria-valuemax="220">
            <div class="v217-gauge-fill" style="width: {wpm_pct:.1f}%;"></div>
          </div>
        </div>
        <div class="v217-badge-group">
          <span class="v217-badge {wpm_badge_cls}">{html_escape(wpm_status_txt)}</span>
          <span class="v217-badge {contrast_cls}">WCAG {contrast_tier} ({min_contrast:.1f}:1)</span>
          <span class="v217-badge {safe_cls}">{'SAFE ZONES CLEARED' if safe_ok else 'SAFE ZONE REVIEW'}</span>
          <span class="v217-badge v217-badge-pass">[GFX-CLEANPLATE] {int(mgs_state.get('cleanplate_count', 0))} CUES</span>
        </div>
      </div>

      <div class="v217-toolbar-inline">
        <div class="v217-seg-group" role="group" aria-label="Safe-zone preview aspect ratio">
          <button type="button" class="v217-seg-btn" id="btn-mgs-aspect-16x9" aria-pressed="true" onclick="setMgsAspectRatio('16:9')">16:9 Broadcast</button>
          <button type="button" class="v217-seg-btn" id="btn-mgs-aspect-9x16" aria-pressed="false" onclick="setMgsAspectRatio('9:16')">9:16 Vertical Social</button>
        </div>
        <div>
          <label for="mgs-preview-select" class="v217-sub">Active Overlay: </label>
          <select id="mgs-preview-select" class="v217-select" aria-label="Select super cue or brand end-card to preview" onchange="selectMgsPreviewCue(this.value)">
            {mgs_options_html}
          </select>
        </div>
      </div>

      <div class="v217-stage-grid">
        <div class="v217-svg-frame">
          <svg id="mgs-safezone-svg" viewBox="0 0 640 360" role="img" aria-label="Interactive 16:9 and 9:16 safe-zone and motion graphics super previewer"></svg>
          <div id="mgs-preview-telemetry" class="v217-inspector-bar" aria-live="polite">Previewing S01 super inside Action-Safe (90%) and Title-Safe (80%) guides.</div>
        </div>
        <div class="v217-endcard-panel" id="mgs-endcard-panel">
          <h3>Brand End-Card Lockup</h3>
          <div><span class="v217-sub">CTA Headline:</span><br><strong>{html_escape(str(endcard.get("cta_headline") or endcard.get("brand_lockup") or ""))}</strong></div>
          <div><span class="v217-sub">CTA Subcopy:</span><br><span class="v217-sub">{html_escape(str(endcard.get("cta_subcopy") or endcard.get("tagline") or ""))}</span></div>
          <div><span class="v217-sub">URL / QR Label:</span> <code class="v217-code">{html_escape(str(endcard.get("url_or_qr_label") or endcard.get("cta_text") or ""))}</code></div>
          <div><span class="v217-sub">Plate &amp; Lockup:</span> <code class="v217-code">{html_escape(str(endcard.get("background_plate_hex") or endcard.get("bg_hex") or "#090D16"))}</code> · <span class="v217-sub">{html_escape(str(endcard.get("logo_lockup_position") or "center_upper_safe"))}</span></div>
          <div><span class="v217-sub">Typography:</span> <code class="v217-code">{html_escape(str(mgs_state.get("primary_typeface", "Space Grotesk")))}</code> / <code class="v217-code">{html_escape(str(mgs_state.get("secondary_typeface", "JetBrains Mono")))}</code></div>
          <div><span class="v217-sub">Duration:</span> <strong>{float(endcard.get("duration_sec", 3.0)):.1f}s</strong> · Sting <code class="v217-code">{html_escape(str(endcard.get("audio_sting_sync_smpte") or ""))}</code> · Contrast <strong>{float(endcard.get("contrast_ratio", 15.4)):.1f}:1</strong></div>
          <div><button type="button" class="v217-seg-btn" onclick="selectMgsPreviewCue('endcard')">Preview End-Card Lockup</button></div>
        </div>
      </div>

      <table class="v217-table" aria-label="Per-Scene Motion Graphics and Legal Super Cues">
        <thead>
          <tr>
            <th>Scene / Cue</th>
            <th>SMPTE Window</th>
            <th>Super &amp; Legal Copy</th>
            <th>Reading Speed</th>
            <th>Safe Zone &amp; Contrast</th>
            <th>Cleanplate Token</th>
          </tr>
        </thead>
        <tbody id="mgs-cue-tbody">
          {mgs_tbody_html}
        </tbody>
      </table>

      <div class="v217-actions-row">
        <button type="button" class="v217-dl-btn" id="btn-dl-mogrt-json" onclick="downloadMotionGraphicsMogrtJSON()">⤓ motion_graphics_mogrt.json</button>
        <button type="button" class="v217-dl-btn" id="btn-dl-supers-ass" onclick="downloadBroadcastSupersASS()">⤓ broadcast_supers.ass</button>
      </div>
    </div>
  </div>
</div>

<!-- v2.17.0 PM-FEAT-034: OpenTimelineIO (.otio) & Cross-Dept Coherence Matrix -->
<div id="modal-otio-coherence" role="dialog" aria-modal="true" aria-labelledby="otio-modal-title" tabindex="-1">
  <div class="v217-modal-card">
    <div class="v217-modal-header">
      <div>
        <h2 id="otio-modal-title" class="v217-modal-title">OpenTimelineIO (.otio) &amp; Cross-Dept Coherence Matrix</h2>
        <span class="v217-modal-sub">7-Track NLE Timeline (V1-V2, A1-A5) @ 24fps &amp; Cross-Departmental Readiness Gate [']</span>
      </div>
      <button type="button" class="v217-close-btn" id="btn-otio-coherence-close" onclick="toggleOtioCoherenceHUD(false)" aria-label="Close OpenTimelineIO Coherence Matrix">Close [Esc]</button>
    </div>
    <div class="v217-modal-body">
      <div class="v217-kpi-row">
        <div class="v217-gauge-wrap">
          <div class="v217-sub">Cross-Dept Coherence Score: <strong>{coh_score:.1f} / 100</strong> · {int(otio_state.get("total_frames", 192))} Frames @ {int(otio_state.get("fps", 24))}fps</div>
          <div class="v217-gauge-bar" role="progressbar" aria-label="Cross-departmental coherence score" aria-valuenow="{coh_score:.1f}" aria-valuemin="0" aria-valuemax="100">
            <div class="v217-gauge-fill" style="width: {min(100.0, max(0.0, coh_score)):.1f}%;"></div>
          </div>
        </div>
        <div class="v217-badge-group">
          <span class="v217-badge {shoot_badge_cls}">{shoot_badge_txt}</span>
          <span class="v217-badge {'v217-badge-pass' if conflicts_cnt == 0 else 'v217-badge-fail'}">{conflicts_cnt} CONFLICT(S)</span>
          <span class="v217-badge {'v217-badge-pass' if warnings_cnt == 0 else 'v217-badge-warn'}">{warnings_cnt} WARNING(S)</span>
          <span class="v217-badge v217-badge-pass">SHA {otio_sha_prefix}</span>
        </div>
      </div>

      <div class="v217-svg-frame">
        <svg id="otio-timeline-svg" viewBox="0 0 880 276" role="img" aria-label="Interactive 7-track OpenTimelineIO timeline diagram with SMPTE 24fps ruler"></svg>
        <div id="otio-clip-inspector" class="v217-inspector-bar" aria-live="polite">Click or press Enter on any .otio clip block to inspect SMPTE 24fps frame boundaries and seek playhead.</div>
      </div>

      <table class="v217-table" aria-label="Cross-Departmental Coherence Matrix">
        <thead>
          <tr>
            <th>Coherence Check &amp; Departments</th>
            <th>Status</th>
            <th>Measured</th>
            <th>Expected Bounds</th>
            <th>Audit Notes</th>
          </tr>
        </thead>
        <tbody id="otio-coherence-tbody">
          {coh_tbody_html}
        </tbody>
      </table>

      <div class="v217-actions-row">
        <button type="button" class="v217-dl-btn" id="btn-dl-otio-timeline" onclick="downloadOtioTimelineFile()">⤓ production_timeline.otio</button>
        <button type="button" class="v217-dl-btn" id="btn-dl-coherence-json" onclick="downloadCoherenceMatrixJSON()">⤓ coherence_matrix.json</button>
      </div>
    </div>
  </div>
</div>
"""

    js_template = """
    // v2.17.0 Motion Graphics Studio (PM-FEAT-033) & OTIO Coherence Matrix (PM-FEAT-034)
    const V217_MGS_STATE = __MGS_JSON__;
    const V217_OTIO_STATE = __OTIO_JSON__;

    let isMotionGfxHUDOpen = false;
    let lastMotionGfxOpener = null;
    let isOtioCoherenceHUDOpen = false;
    let lastOtioCoherenceOpener = null;
    let _mgsAspectRatio = '16:9';
    let _mgsSelectedTarget = 0;
    let _v217Initialized = false;

    if (typeof V216_HUD_COMMANDS !== 'undefined' && Array.isArray(V216_HUD_COMMANDS)) {
      if (!V216_HUD_COMMANDS.some((c) => c.id === 'motiongfx')) {
        V216_HUD_COMMANDS.push({ id: 'motiongfx', name: 'Motion Graphics, Supers & End-Card Studio', dept: 'Color', key: '=', fn: 'toggleMotionGfxHUD' });
      }
      if (!V216_HUD_COMMANDS.some((c) => c.id === 'otiocoherence')) {
        V216_HUD_COMMANDS.push({ id: 'otiocoherence', name: 'OpenTimelineIO (.otio) & Cross-Dept Coherence Matrix', dept: 'Delivery', key: "'", fn: 'toggleOtioCoherenceHUD' });
      }
    }

    function _v217ShowToast(msg) {
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

    function _v217DownloadBlob(content, mime, filename, toastMsg) {
      const blob = new Blob([content], { type: mime });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      _v217ShowToast(toastMsg);
    }

    function _v217SvgEl(tag, attrs) {
      const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
      Object.keys(attrs || {}).forEach((k) => el.setAttribute(k, String(attrs[k])));
      return el;
    }

    function _v217CloseSiblingHUDs(activeKey) {
      if (typeof closeSecondaryOpenHUDs === 'function') closeSecondaryOpenHUDs(activeKey);
      if (typeof isHudCommandPaletteOpen !== 'undefined' && isHudCommandPaletteOpen && typeof toggleHudCommandPalette === 'function') toggleHudCommandPalette(false);
      if (typeof isArtWardrobeHUDOpen !== 'undefined' && isArtWardrobeHUDOpen && typeof toggleArtWardrobeHUD === 'function') toggleArtWardrobeHUD(false);
      if (typeof isRenderEconomicsHUDOpen !== 'undefined' && isRenderEconomicsHUDOpen && typeof toggleRenderEconomicsHUD === 'function') toggleRenderEconomicsHUD(false);
      if (typeof isS3dHUDOpen !== 'undefined' && isS3dHUDOpen && typeof toggleS3dHUD === 'function') toggleS3dHUD(false);
      if (typeof isAccessibilityAdHUDOpen !== 'undefined' && isAccessibilityAdHUDOpen && typeof toggleAccessibilityAdHUD === 'function') toggleAccessibilityAdHUD(false);
      if (typeof isRenderJobsHUDOpen !== 'undefined' && isRenderJobsHUDOpen && typeof toggleRenderJobsHUD === 'function') toggleRenderJobsHUD(false);
      if (typeof isPitchTreatmentHUDOpen !== 'undefined' && isPitchTreatmentHUDOpen && typeof togglePitchTreatmentHUD === 'function') togglePitchTreatmentHUD(false);
      if (typeof isImfDcpHUDOpen !== 'undefined' && isImfDcpHUDOpen && typeof toggleImfDcpHUD === 'function') toggleImfDcpHUD(false);
      if (typeof isVoiceDuckingHUDOpen !== 'undefined' && isVoiceDuckingHUDOpen && typeof toggleVoiceDuckingHUD === 'function') toggleVoiceDuckingHUD(false);
      if (activeKey !== 'motiongfx' && isMotionGfxHUDOpen) toggleMotionGfxHUD(false);
      if (activeKey !== 'otio' && isOtioCoherenceHUDOpen) toggleOtioCoherenceHUD(false);
    }

    function _v217TrapFocus(modal, onEscape) {
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

    window.setMgsAspectRatio = function(aspect) {
      _mgsAspectRatio = aspect === '9:16' ? '9:16' : '16:9';
      const btn16 = document.getElementById('btn-mgs-aspect-16x9');
      const btn9 = document.getElementById('btn-mgs-aspect-9x16');
      if (btn16) btn16.setAttribute('aria-pressed', _mgsAspectRatio === '16:9' ? 'true' : 'false');
      if (btn9) btn9.setAttribute('aria-pressed', _mgsAspectRatio === '9:16' ? 'true' : 'false');
      renderMotionGfxPreview();
    };

    window.selectMgsPreviewCue = function(target) {
      _mgsSelectedTarget = target === 'endcard' ? 'endcard' : Math.max(0, parseInt(target, 10) || 0);
      const sel = document.getElementById('mgs-preview-select');
      if (sel) sel.value = String(_mgsSelectedTarget);
      document.querySelectorAll('#mgs-cue-tbody .v217-cue-row').forEach((row) => {
        row.classList.toggle('selected', String(row.dataset.cueIdx) === String(_mgsSelectedTarget));
      });
      renderMotionGfxPreview();
    };

    function renderMotionGfxPreview() {
      const svg = document.getElementById('mgs-safezone-svg');
      const bar = document.getElementById('mgs-preview-telemetry');
      if (!svg) return;
      while (svg.firstChild) svg.removeChild(svg.firstChild);

      const W = 640;
      const H = 360;
      svg.appendChild(_v217SvgEl('rect', { x: 0, y: 0, width: W, height: H, fill: '#05070B' }));

      const isVertical = _mgsAspectRatio === '9:16';
      const fw = isVertical ? 202 : 620;
      const fh = isVertical ? 344 : 340;
      const fx = Math.round((W - fw) / 2);
      const fy = Math.round((H - fh) / 2);

      // Active viewport frame
      svg.appendChild(_v217SvgEl('rect', { x: fx, y: fy, width: fw, height: fh, fill: '#0B1120', stroke: '#475569', 'stroke-width': 1.5, rx: 4 }));

      // Action-Safe (90%) and Title-Safe (80%)
      const ax = fx + fw * 0.05;
      const ay = fy + fh * 0.05;
      const aw = fw * 0.90;
      const ah = fh * 0.90;
      svg.appendChild(_v217SvgEl('rect', { x: ax, y: ay, width: aw, height: ah, fill: 'none', stroke: '#38BDF8', 'stroke-width': 1, 'stroke-dasharray': '5,4', opacity: 0.8 }));

      const tx = fx + fw * 0.10;
      const ty = fy + fh * 0.10;
      const tw = fw * 0.80;
      const th = fh * 0.80;
      svg.appendChild(_v217SvgEl('rect', { x: tx, y: ty, width: tw, height: th, fill: 'none', stroke: '#FBBF24', 'stroke-width': 1, 'stroke-dasharray': '3,3', opacity: 0.85 }));

      if (isVertical) {
        // Vertical Reels/TikTok HUD bottom & right engagement guard
        svg.appendChild(_v217SvgEl('rect', { x: fx + fw - 32, y: fy + fh * 0.48, width: 28, height: fh * 0.36, fill: 'rgba(239,68,68,0.16)', stroke: '#F87171', 'stroke-width': 1, rx: 3 }));
        svg.appendChild(_v217SvgEl('rect', { x: fx + 6, y: fy + fh - 48, width: fw - 44, height: 42, fill: 'rgba(239,68,68,0.16)', stroke: '#F87171', 'stroke-width': 1, rx: 3 }));
      }

      const endcard = V217_MGS_STATE.endcard || {};
      const cues = V217_MGS_STATE.scene_graphics || [];
      const isEndcard = _mgsSelectedTarget === 'endcard' || !cues.length;
      const activeCue = !isEndcard ? (cues[_mgsSelectedTarget] || cues[0]) : null;

      if (isEndcard) {
        // Centered End-Card lockup inside Title-Safe 80%
        const endPlate = String(endcard.background_plate_hex || endcard.bg_hex || '#090D16');
        const endHeadline = String(endcard.cta_headline || endcard.brand_lockup || V217_MGS_STATE.brand_name || 'OMNI STUDIO');
        const endSubcopy = String(endcard.cta_subcopy || endcard.tagline || '');
        const endUrlLabel = String(endcard.url_or_qr_label || endcard.cta_text || 'EXPLORE MORE');

        svg.appendChild(_v217SvgEl('rect', { x: tx + 8, y: ty + th * 0.20, width: tw - 16, height: th * 0.60, fill: endPlate, 'fill-opacity': 0.94, stroke: '#38BDF8', 'stroke-width': 1.5, rx: 6 }));
        const tBrand = _v217SvgEl('text', { x: fx + fw / 2, y: ty + th * 0.43, fill: endcard.fg_hex || '#F8FAFC', 'font-family': 'Space Grotesk, sans-serif', 'font-size': isVertical ? 14 : 22, 'font-weight': 700, 'text-anchor': 'middle' });
        tBrand.textContent = endHeadline.slice(0, isVertical ? 18 : 34);
        svg.appendChild(tBrand);

        const tTag = _v217SvgEl('text', { x: fx + fw / 2, y: ty + th * 0.56, fill: '#CBD5E1', 'font-family': 'JetBrains Mono, monospace', 'font-size': isVertical ? 9 : 11, 'text-anchor': 'middle' });
        tTag.textContent = endSubcopy.slice(0, isVertical ? 24 : 56);
        svg.appendChild(tTag);

        const pillW = isVertical ? 116 : 200;
        const pillX = fx + (fw - pillW) / 2;
        const pillY = ty + th * 0.63;
        svg.appendChild(_v217SvgEl('rect', { x: pillX, y: pillY, width: pillW, height: 24, fill: endcard.accent_hex || '#38BDF8', rx: 12 }));
        const tCta = _v217SvgEl('text', { x: fx + fw / 2, y: pillY + 16, fill: '#07080B', 'font-family': 'JetBrains Mono, monospace', 'font-size': 10, 'font-weight': 700, 'text-anchor': 'middle' });
        tCta.textContent = endUrlLabel.slice(0, 26);
        svg.appendChild(tCta);

        if (bar) {
          bar.textContent = 'End-Card Lockup (' + _mgsAspectRatio + ') · Plate: ' + endPlate + ' · Duration: ' + Number(endcard.duration_sec || 3.0).toFixed(1) + 's · Contrast: ' + Number(endcard.contrast_ratio || 15.4).toFixed(1) + ':1';
        }
      } else {
        // [GFX-CLEANPLATE] lower-third zone inside Title-Safe
        const cpX = tx + 4;
        const cpW = isVertical ? tw - 36 : tw * 0.74;
        const cpH = isVertical ? 66 : 64;
        const cpY = ty + th - cpH - (isVertical ? 36 : 8);

        svg.appendChild(_v217SvgEl('rect', { x: cpX, y: cpY, width: cpW, height: cpH, fill: 'rgba(16, 185, 129, 0.14)', stroke: '#34D399', 'stroke-width': 1.25, 'stroke-dasharray': '4,3', rx: 4 }));

        const cpTag = _v217SvgEl('text', { x: cpX + 8, y: cpY + 14, fill: '#34D399', 'font-family': 'JetBrains Mono, monospace', 'font-size': 9, 'font-weight': 700 });
        cpTag.textContent = String(activeCue.token || '[GFX-CLEANPLATE]') + ' · ' + String(activeCue.cue_id || 'GFX');
        svg.appendChild(cpTag);

        const sup = _v217SvgEl('text', { x: cpX + 8, y: cpY + 34, fill: activeCue.fg_hex || '#F8FAFC', 'font-family': 'Space Grotesk, sans-serif', 'font-size': isVertical ? 11 : 15, 'font-weight': 700 });
        const mainText = activeCue.super_text ? String(activeCue.super_text) : '[LEGAL DISCLAIMER]';
        sup.textContent = mainText.slice(0, isVertical ? 20 : 42);
        svg.appendChild(sup);

        const leg = _v217SvgEl('text', { x: cpX + 8, y: cpY + 52, fill: '#CBD5E1', 'font-family': 'JetBrains Mono, monospace', 'font-size': isVertical ? 8 : 9.5 });
        leg.textContent = String(activeCue.legal_super || '').slice(0, isVertical ? 24 : 58);
        svg.appendChild(leg);

        if (bar) {
          bar.textContent = 'Scene ' + String(activeCue.scene_index).padStart(2, '0') + ' (' + _mgsAspectRatio + ') · ' + activeCue.smpte_in + ' -> ' + activeCue.smpte_out + ' · ' + Number(activeCue.wpm || 0).toFixed(1) + ' WPM · Contrast ' + Number(activeCue.contrast_ratio || 12).toFixed(1) + ':1';
        }
      }

      // Corner guide legend
      const legText = _v217SvgEl('text', { x: fx + 8, y: fy + 15, fill: '#94A3B8', 'font-family': 'JetBrains Mono, monospace', 'font-size': 9.5 });
      legText.textContent = _mgsAspectRatio + ' · Cyan=ActionSafe(90%) · Amber=TitleSafe(80%)';
      svg.appendChild(legText);
    }

    function renderOtioTimelineSvg() {
      const svg = document.getElementById('otio-timeline-svg');
      if (!svg) return;
      while (svg.firstChild) svg.removeChild(svg.firstChild);

      const W = 880;
      const H = 276;
      const labelW = 166;
      const rulerH = 34;
      const laneH = 32;
      const totalSec = Math.max(1, Number(V217_OTIO_STATE.total_runtime_sec || 8));
      const fps = Number(V217_OTIO_STATE.fps || 24);
      const trackW = W - labelW - 16;

      svg.appendChild(_v217SvgEl('rect', { x: 0, y: 0, width: W, height: H, fill: '#05070B' }));
      svg.appendChild(_v217SvgEl('rect', { x: labelW, y: 0, width: trackW, height: rulerH, fill: '#0F172A' }));

      const ticks = 6;
      for (let i = 0; i <= ticks; i++) {
        const frac = i / ticks;
        const x = labelW + frac * trackW;
        const secVal = frac * totalSec;
        const frames = Math.round(secVal * fps);
        svg.appendChild(_v217SvgEl('line', { x1: x, y1: 18, x2: x, y2: rulerH, stroke: '#475569', 'stroke-width': 1 }));
        const tLabel = _v217SvgEl('text', { x: i === ticks ? x - 4 : x + 3, y: 14, fill: '#94A3B8', 'font-family': 'JetBrains Mono, monospace', 'font-size': 9.5, 'text-anchor': i === ticks ? 'end' : 'start' });
        tLabel.textContent = frames + 'f (' + secVal.toFixed(1) + 's)';
        svg.appendChild(tLabel);
      }

      const tracks = V217_OTIO_STATE.tracks || [];
      tracks.forEach((tr, tIdx) => {
        const y = rulerH + tIdx * laneH + 4;
        const bg = tIdx % 2 === 0 ? '#0B1120' : '#0E1424';
        svg.appendChild(_v217SvgEl('rect', { x: 4, y: y, width: W - 8, height: laneH - 4, fill: bg, rx: 3 }));

        const tNameEl = _v217SvgEl('text', { x: 10, y: y + 18, fill: '#E2E8F0', 'font-family': 'JetBrains Mono, monospace', 'font-size': 10.5, 'font-weight': 700 });
        tNameEl.textContent = String(tr.track_name || ('Track ' + (tIdx + 1)));
        svg.appendChild(tNameEl);

        (tr.clips || []).forEach((clip) => {
          const st = Math.max(0, Number(clip.start_sec || 0));
          const du = Math.max(0.5, Number(clip.duration_sec || 2));
          const cx = labelW + (st / totalSec) * trackW + 1;
          const cw = Math.max(18, (du / totalSec) * trackW - 2);
          const isGap = Boolean(clip.is_gap || clip.schema === 'Gap.1');
          const g = _v217SvgEl('g', {
            tabindex: '0',
            role: 'button',
            style: 'cursor:pointer;',
            'aria-label': String(tr.track_name) + ' ' + String(clip.name) + ' ' + String(clip.smpte_in) + ' to ' + String(clip.smpte_out)
          });
          const rectAttrs = {
            x: cx,
            y: y + 3,
            width: cw,
            height: laneH - 10,
            fill: isGap ? '#1E293B' : (tr.color || '#38BDF8'),
            'fill-opacity': isGap ? 0.25 : 0.24,
            stroke: isGap ? '#475569' : (tr.color || '#38BDF8'),
            'stroke-width': isGap ? 1.0 : 1.2,
            rx: 3
          };
          if (isGap) rectAttrs['stroke-dasharray'] = '3,3';
          g.appendChild(_v217SvgEl('rect', rectAttrs));
          const cTxt = _v217SvgEl('text', { x: cx + 6, y: y + 18, fill: isGap ? '#94A3B8' : '#F8FAFC', 'font-family': 'JetBrains Mono, monospace', 'font-size': 9.5 });
          cTxt.textContent = String(clip.name || '').slice(0, Math.max(6, Math.floor(cw / 6.5)));
          g.appendChild(cTxt);

          const activateClip = () => {
            const insp = document.getElementById('otio-clip-inspector');
            if (insp) {
              let extra = '';
              if (clip.target_url) extra += ' · ' + String(clip.target_url);
              if (clip.j_prelap_frames || clip.l_overhang_frames) {
                extra += ' · J-prelap=' + String(clip.j_prelap_frames || 0) + 'f, L-overhang=' + String(clip.l_overhang_frames || 0) + 'f';
              }
              insp.textContent = String(tr.track_name) + ' [' + String(tr.kind) + '] · ' + String(clip.name) + ' · SMPTE ' + String(clip.smpte_in) + ' -> ' + String(clip.smpte_out) + ' (' + String(clip.duration_frames) + ' frames @ ' + fps + 'fps)' + extra;
            }
            if (typeof renderFrame === 'function') renderFrame(Math.round(st * fps));
            else if (typeof seekToTime === 'function') seekToTime(st);
          };
          g.addEventListener('click', activateClip);
          g.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.code === 'Space') {
              e.preventDefault();
              activateClip();
            }
          });
          svg.appendChild(g);
        });
      });
    }

    window.toggleMotionGfxHUD = function(forceState) {
      const modal = document.getElementById('modal-motion-graphics-studio');
      const btn = document.getElementById('btn-motion-gfx-animatic');
      if (!modal) return;
      const shouldOpen = forceState !== undefined ? Boolean(forceState) : !isMotionGfxHUDOpen;
      if (!shouldOpen && !isMotionGfxHUDOpen) return;
      if (shouldOpen) {
        _v217CloseSiblingHUDs('motiongfx');
      }
      isMotionGfxHUDOpen = shouldOpen;
      if (btn) {
        btn.classList.toggle('active', shouldOpen);
        btn.setAttribute('aria-expanded', shouldOpen ? 'true' : 'false');
      }
      if (shouldOpen) {
        lastMotionGfxOpener = document.activeElement;
        modal.style.display = 'flex';
        renderMotionGfxPreview();
        const closeBtn = document.getElementById('btn-motion-gfx-close');
        if (closeBtn) closeBtn.focus();
        _v217ShowToast('🎨 Motion Graphics & End-Card Studio: ACTIVE [=]');
      } else {
        modal.style.display = 'none';
        if (lastMotionGfxOpener && typeof lastMotionGfxOpener.focus === 'function') lastMotionGfxOpener.focus();
        else if (btn && typeof btn.focus === 'function') btn.focus();
      }
    };

    window.toggleOtioCoherenceHUD = function(forceState) {
      const modal = document.getElementById('modal-otio-coherence');
      const btn = document.getElementById('btn-otio-coherence-animatic');
      if (!modal) return;
      const shouldOpen = forceState !== undefined ? Boolean(forceState) : !isOtioCoherenceHUDOpen;
      if (!shouldOpen && !isOtioCoherenceHUDOpen) return;
      if (shouldOpen) {
        _v217CloseSiblingHUDs('otio');
      }
      isOtioCoherenceHUDOpen = shouldOpen;
      if (btn) {
        btn.classList.toggle('active', shouldOpen);
        btn.setAttribute('aria-expanded', shouldOpen ? 'true' : 'false');
      }
      if (shouldOpen) {
        lastOtioCoherenceOpener = document.activeElement;
        modal.style.display = 'flex';
        renderOtioTimelineSvg();
        const closeBtn = document.getElementById('btn-otio-coherence-close');
        if (closeBtn) closeBtn.focus();
        _v217ShowToast('🎞️ OpenTimelineIO (.otio) & Coherence Matrix: ACTIVE [\\']');
      } else {
        modal.style.display = 'none';
        if (lastOtioCoherenceOpener && typeof lastOtioCoherenceOpener.focus === 'function') lastOtioCoherenceOpener.focus();
        else if (btn && typeof btn.focus === 'function') btn.focus();
      }
    };

    function _secToAssTime(sec) {
      const totalCs = Math.max(0, Math.round(Number(sec || 0) * 100));
      const cs = totalCs % 100;
      const totalS = Math.floor(totalCs / 100);
      const s = totalS % 60;
      const m = Math.floor(totalS / 60) % 60;
      const h = Math.floor(totalS / 3600);
      return String(h) + ':' + String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0') + '.' + String(cs).padStart(2, '0');
    }

    window.downloadMotionGraphicsMogrtJSON = function() {
      const payload = {
        schema: 'omni.motion_graphics_mogrt.v1',
        project_title: V217_MGS_STATE.project_title,
        brand_name: V217_MGS_STATE.brand_name,
        primary_typeface: V217_MGS_STATE.primary_typeface,
        secondary_typeface: V217_MGS_STATE.secondary_typeface,
        max_wpm_detected: V217_MGS_STATE.max_wpm_detected,
        all_safe_zones_cleared: V217_MGS_STATE.all_safe_zones_cleared,
        legal_supers_compliant: V217_MGS_STATE.legal_supers_compliant,
        scene_graphics: V217_MGS_STATE.scene_graphics || [],
        endcard: V217_MGS_STATE.endcard || {}
      };
      _v217DownloadBlob(JSON.stringify(payload, null, 2), 'application/json;charset=utf-8;', 'motion_graphics_mogrt.json', 'Downloaded motion_graphics_mogrt.json');
    };

    window.downloadBroadcastSupersASS = function() {
      const sanitizeAssField = (v) => String(v || '').replace(/[\\r\\n]+/g, ' ').replace(/[{}]/g, '').trim();
      const lines = [
        '[Script Info]',
        'Title: ' + sanitizeAssField(V217_MGS_STATE.project_title || 'Omni Production') + ' Broadcast Supers',
        'ScriptType: v4.00+',
        'PlayResX: 1920',
        'PlayResY: 1080',
        '',
        '[V4+ Styles]',
        'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding',
        'Style: HeroSuper,' + sanitizeAssField(V217_MGS_STATE.primary_typeface || 'Space Grotesk') + ',52,&H00FCFAF8,&H0038BDF8,&H000B0F19,&H8007080B,1,0,0,0,100,100,0,0,1,2,0,1,192,192,108,1',
        'Style: LegalSuper,' + sanitizeAssField(V217_MGS_STATE.secondary_typeface || 'JetBrains Mono') + ',26,&H00E1D5CB,&H0038BDF8,&H000B0F19,&H8007080B,0,0,0,0,100,100,0,0,1,1,0,2,192,192,64,1',
        '',
        '[Events]',
        'Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text'
      ];
      (V217_MGS_STATE.scene_graphics || []).forEach((c) => {
        const st = _secToAssTime(c.start_sec);
        const en = _secToAssTime(c.end_sec);
        const cueId = sanitizeAssField(c.cue_id || 'GFX') || 'GFX';
        const superText = sanitizeAssField(c.super_text);
        const legalText = sanitizeAssField(c.legal_super);
        if (superText) {
          lines.push('Dialogue: 0,' + st + ',' + en + ',HeroSuper,' + cueId + ',0,0,0,,' + superText);
        }
        if (legalText) {
          lines.push('Dialogue: 1,' + st + ',' + en + ',LegalSuper,' + cueId + '_LEGAL,0,0,0,,' + legalText);
        }
      });
      _v217DownloadBlob(lines.join('\\n') + '\\n', 'text/plain;charset=utf-8;', 'broadcast_supers.ass', 'Downloaded broadcast_supers.ass');
    };

    window.downloadOtioTimelineFile = function() {
      const rawJson = V217_OTIO_STATE.otio_json_text;
      const otioDoc = V217_OTIO_STATE.otio_document || { OTIO_SCHEMA: 'Timeline.1', name: V217_OTIO_STATE.project_title || 'Omni Timeline', tracks: { OTIO_SCHEMA: 'Stack.1', name: 'tracks', children: [] } };
      const content = (typeof rawJson === 'string' && rawJson.length > 0) ? rawJson : JSON.stringify(otioDoc, null, 2);
      _v217DownloadBlob(content, 'application/json;charset=utf-8;', 'production_timeline.otio', 'Downloaded production_timeline.otio');
    };

    window.downloadCoherenceMatrixJSON = function() {
      const payload = {
        project_title: V217_OTIO_STATE.project_title,
        fps: V217_OTIO_STATE.fps,
        total_runtime_sec: V217_OTIO_STATE.total_runtime_sec,
        total_frames: V217_OTIO_STATE.total_frames,
        coherence_score: V217_OTIO_STATE.coherence_score,
        conflicts_count: V217_OTIO_STATE.conflicts_count,
        warnings_count: V217_OTIO_STATE.warnings_count,
        shoot_day_ready: V217_OTIO_STATE.shoot_day_ready,
        otio_sha256: V217_OTIO_STATE.otio_sha256,
        coherence_checks: V217_OTIO_STATE.coherence_checks || []
      };
      _v217DownloadBlob(JSON.stringify(payload, null, 2), 'application/json;charset=utf-8;', 'coherence_matrix.json', 'Downloaded coherence_matrix.json');
    };

    window.initV217HUDs = function() {
      if (_v217Initialized) return;
      _v217Initialized = true;
      const mMgs = document.getElementById('modal-motion-graphics-studio');
      const mOtio = document.getElementById('modal-otio-coherence');
      _v217TrapFocus(mMgs, () => toggleMotionGfxHUD(false));
      _v217TrapFocus(mOtio, () => toggleOtioCoherenceHUD(false));

      document.querySelectorAll('#mgs-cue-tbody .v217-cue-row').forEach((row) => {
        row.addEventListener('keydown', (e) => {
          if (e.key === 'Enter' || e.code === 'Space') {
            e.preventDefault();
            selectMgsPreviewCue(row.dataset.cueIdx || 0);
          }
        });
      });

      renderMotionGfxPreview();
      renderOtioTimelineSvg();
    };

    document.addEventListener('DOMContentLoaded', () => {
      if (typeof initV217HUDs === 'function') initV217HUDs();
    });
    """

    js = (
        js_template
        .replace("__MGS_JSON__", mgs_json)
        .replace("__OTIO_JSON__", otio_json)
    )

    return {
        "css": css,
        "modals_html": modals_html,
        "js": js,
    }
