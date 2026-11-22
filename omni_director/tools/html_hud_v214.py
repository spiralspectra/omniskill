"""Modular v2.14.0 Dark-Room Cinema HUD Components (PM-FEAT-027 & PM-FEAT-028).

Provides Python 3.11-compatible builders for:
1. PM-FEAT-027: Multi-Language Localization, ADR Dubbing & Safe-Supers HUD (#animatic-localization-hud, [I] hotkey)
2. PM-FEAT-028: Editorial J-Cut / L-Cut Spotting & BPM Beat-Grid HUD (#animatic-spotting-hud, [J] hotkey)
"""

from __future__ import annotations

import csv
import io
import json
import re
from html import escape as html_escape
from typing import Any, Dict, List, Optional, Tuple
from xml.sax.saxutils import escape as xml_escape

from omni_director.schemas import MasterProductionBible, ProductionBundle


CANONICAL_TERRITORIES: List[Dict[str, Any]] = [
    {
        "locale": "en-US",
        "bcp47_tag": "en-US",
        "territory_label": "North America (US)",
        "direction": "ltr",
        "expansion_factor": 1.00,
        "sample_super_prefix": "ENGINEERED FOR PRECISION",
    },
    {
        "locale": "de-DE",
        "bcp47_tag": "de-DE",
        "territory_label": "DACH (Germany / Austria)",
        "direction": "ltr",
        "expansion_factor": 1.24,
        "sample_super_prefix": "PRÄZISION BIS INS DETAIL",
    },
    {
        "locale": "fr-FR",
        "bcp47_tag": "fr-FR",
        "territory_label": "France / Benelux",
        "direction": "ltr",
        "expansion_factor": 1.18,
        "sample_super_prefix": "CONÇU POUR LA PRÉCISION",
    },
    {
        "locale": "es-419",
        "bcp47_tag": "es-419",
        "territory_label": "LATAM (Neutral Spanish)",
        "direction": "ltr",
        "expansion_factor": 1.16,
        "sample_super_prefix": "DISEÑADO CON PRECISIÓN",
    },
    {
        "locale": "ja-JP",
        "bcp47_tag": "ja-JP",
        "territory_label": "Japan (JP)",
        "direction": "ltr",
        "expansion_factor": 0.92,
        "sample_super_prefix": "精密なクラフトマンシップ",
    },
    {
        "locale": "ar-SA",
        "bcp47_tag": "ar-SA",
        "territory_label": "MENA (Arabic RTL)",
        "direction": "rtl",
        "expansion_factor": 1.12,
        "sample_super_prefix": "صُمم بدقة متناهية",
    },
]


def _escape_js_template_literal(text: str) -> str:
    """Escapes backslashes, backticks, template interpolations, and closing script tags for safe JS template literals."""
    escaped = str(text).replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
    return re.sub(r"</(script)", r"<\/\1", escaped, flags=re.IGNORECASE)


def _escape_json_for_script(payload: Any) -> str:
    """Serializes JSON safely for embedding inside HTML <script> tags."""
    return re.sub(r"</(script)", r"<\/\1", json.dumps(payload), flags=re.IGNORECASE)


def _to_plain(obj: Any) -> Any:
    """Converts Pydantic models, enums, or nested objects into plain JSON-safe Python structures."""
    if obj is None:
        return None
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "value"):
        return obj.value
    if isinstance(obj, dict):
        return {str(k): _to_plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_plain(v) for v in obj]
    return obj


def _sec_to_smpte(sec: float, fps: int = 24) -> str:
    """Converts seconds to 24fps SMPTE HH:MM:SS:FF timecode."""
    total_frames = max(0, int(round(float(sec) * fps)))
    ff = total_frames % fps
    total_sec = total_frames // fps
    ss = total_sec % 60
    mm = (total_sec // 60) % 60
    hh = total_sec // 3600
    return f"{hh:02d}:{mm:02d}:{ss:02d}:{ff:02d}"


def _smpte_to_sec(tc: str, fps: int = 24) -> Optional[float]:
    """Parses HH:MM:SS:FF SMPTE timecode to seconds."""
    m = re.match(r"^\s*(\d{2}):(\d{2}):(\d{2})[:;](\d{2})\s*$", str(tc or ""))
    if not m:
        return None
    hh, mm, ss, ff = (int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)))
    frames = ((hh * 3600) + (mm * 60) + ss) * fps + ff
    return round(frames / float(fps), 4)


def _try_synthesize_localization_manifest(bible: MasterProductionBible) -> Any:
    """Lazily invokes localization_adr module if available; otherwise returns None."""
    try:
        from omni_director.tools import localization_adr  # type: ignore
    except ImportError:
        return None

    for fn_name in (
        "compile_localization_manifest",
        "synthesize_default_localization_manifest",
        "build_localization_manifest",
        "synthesize_localization_manifest",
        "generate_localization_manifest",
    ):
        fn = getattr(localization_adr, fn_name, None)
        if callable(fn):
            try:
                return fn(bible)
            except TypeError:
                try:
                    return fn(bible=bible)
                except Exception:
                    return None
            except Exception:
                return None
    return None


def _try_synthesize_spotting_manifest(bible: MasterProductionBible) -> Any:
    """Lazily invokes editorial_spotting module if available; otherwise returns None."""
    try:
        from omni_director.tools import editorial_spotting  # type: ignore
    except ImportError:
        return None

    for fn_name in (
        "build_spotting_manifest",
        "synthesize_default_spotting_manifest",
        "synthesize_spotting_manifest",
        "generate_spotting_manifest",
    ):
        fn = getattr(editorial_spotting, fn_name, None)
        if callable(fn):
            try:
                return fn(bible)
            except TypeError:
                try:
                    return fn(bible=bible)
                except Exception:
                    return None
            except Exception:
                return None
    return None


def _classify_sync_status(ratio: float, max_drift: float = 1.15) -> str:
    del max_drift  # Aligned with localization_adr._classify_sync_status
    if ratio <= 1.15:
        return "locked"
    if ratio <= 1.25:
        return "stretch_caution"
    return "rescript_required"


def _classify_supers_status(expansion_pct: float) -> str:
    if expansion_pct > 25.0:
        return "safe_zone_overflow"
    if expansion_pct > 15.0:
        return "tight_wrap"
    return "clear"


def _normalize_localization_state(
    bible: MasterProductionBible,
    scene_time_lookup: Dict[int, Tuple[float, float]],
    total_runtime_sec: float,
) -> Dict[str, Any]:
    """Builds normalized PM-FEAT-027 localization, ADR, and IMSC1 state from bible or resilient fallback."""
    manifest_obj = getattr(bible, "localization_manifest", None)
    has_explicit_manifest = manifest_obj is not None
    if manifest_obj is None:
        manifest_obj = _try_synthesize_localization_manifest(bible)
    raw = _to_plain(manifest_obj) or {}

    scenes = getattr(bible, "scenes", []) or []
    project_title = str(getattr(bible, "project_title", "Omni Production") or "Omni Production")
    max_allowed_wps = float(raw.get("max_allowed_wps") or 2.5)
    max_allowed_drift = float(raw.get("max_allowed_drift_ratio") or 1.15)
    source_locale = str(raw.get("source_locale") or "en-US")
    imsc1_profile = str(raw.get("imsc1_profile") or "imsc1-text-1.1")

    master_dlg = getattr(bible, "master_dialogue", None)
    master_lines = list(getattr(master_dlg, "dialogue_lines", None) or []) if master_dlg is not None else []

    scene_meta: List[Dict[str, Any]] = []
    scene_cue_slots: List[Dict[str, Any]] = []
    for pos, scene in enumerate(scenes, start=1):
        s_idx = int(getattr(scene, "scene_index", pos))
        st_s, en_s = scene_time_lookup.get(s_idx, ((pos - 1) * 8.0, pos * 8.0))
        dur_s = max(2.0, float(en_s - st_s))
        title = str(getattr(scene, "scene_title", f"Scene {s_idx}") or f"Scene {s_idx}")
        ds = getattr(scene, "diegetic_sonic", None)
        raw_dlg_lines = getattr(ds, "dialogue_lines", None) if ds is not None else None
        non_empty_dlg: List[str] = []
        if isinstance(raw_dlg_lines, (list, tuple)):
            non_empty_dlg = [str(x).strip() for x in raw_dlg_lines if str(x or "").strip()]
        elif isinstance(raw_dlg_lines, str) and raw_dlg_lines.strip():
            non_empty_dlg = [raw_dlg_lines.strip()]

        if non_empty_dlg:
            vo_raw = " ".join(non_empty_dlg)
        elif pos <= len(master_lines) and str(master_lines[pos - 1] or "").strip():
            vo_raw = str(master_lines[pos - 1]).strip()
            non_empty_dlg = [vo_raw]
        else:
            beats = getattr(scene, "action_beats", []) or []
            vo_raw = str(beats[0]) if beats else f"{title} — precision visual sequence."

        vo_clean = " ".join(vo_raw.split())[:140]
        words = max(4, len(vo_clean.split()))
        syllables = max(words, int(round(words * 1.45)))
        sm_entry = {
            "scene_index": s_idx,
            "scene_title": title,
            "start_sec": round(st_s, 3),
            "end_sec": round(en_s, 3),
            "duration_sec": round(dur_s, 3),
            "in_tc": _sec_to_smpte(st_s),
            "out_tc": _sec_to_smpte(en_s),
            "source_line": vo_clean,
            "base_words": words,
            "base_syllables": syllables,
        }
        scene_meta.append(sm_entry)

        if non_empty_dlg:
            step = dur_s / len(non_empty_dlg)
            for d_idx, dlg_line in enumerate(non_empty_dlg):
                c_st = st_s + d_idx * step
                c_en = st_s + (d_idx + 1) * step
                c_dur = max(1.0, c_en - c_st)
                c_clean = " ".join(dlg_line.split())[:140]
                c_words = max(1, len(c_clean.split()))
                c_syl = max(c_words, int(round(c_words * 1.45)))
                scene_cue_slots.append(
                    {
                        "scene_index": s_idx,
                        "scene_title": title,
                        "start_sec": round(c_st, 3),
                        "end_sec": round(c_en, 3),
                        "duration_sec": round(c_dur, 3),
                        "in_tc": _sec_to_smpte(c_st),
                        "out_tc": _sec_to_smpte(c_en),
                        "source_line": c_clean,
                        "base_words": c_words,
                        "base_syllables": c_syl,
                    }
                )
        else:
            scene_cue_slots.append(dict(sm_entry))

    if not scene_meta:
        fallback_sm = {
            "scene_index": 1,
            "scene_title": "Opening Sequence",
            "start_sec": 0.0,
            "end_sec": max(8.0, float(total_runtime_sec or 8.0)),
            "duration_sec": max(8.0, float(total_runtime_sec or 8.0)),
            "in_tc": "00:00:00:00",
            "out_tc": _sec_to_smpte(max(8.0, float(total_runtime_sec or 8.0))),
            "source_line": f"{project_title} — signature opening frame.",
            "base_words": 6,
            "base_syllables": 9,
        }
        scene_meta.append(fallback_sm)
        scene_cue_slots.append(dict(fallback_sm))

    scene_lookup_map: Dict[int, Dict[str, Any]] = {sm["scene_index"]: sm for sm in scene_meta}

    raw_territories = raw.get("territories") or []
    terr_by_locale: Dict[str, Dict[str, Any]] = {}
    ordered_manifest_locales: List[str] = []
    for rt in raw_territories:
        if isinstance(rt, dict) and rt.get("locale"):
            loc_str = str(rt["locale"])
            terr_by_locale[loc_str] = rt
            if loc_str not in ordered_manifest_locales:
                ordered_manifest_locales.append(loc_str)

    explicit_target_locales = [str(l) for l in (raw.get("target_locales") or []) if str(l).strip()]
    canonical_order = [t["locale"] for t in CANONICAL_TERRITORIES]
    canonical_map = {t["locale"]: t for t in CANONICAL_TERRITORIES}

    if has_explicit_manifest:
        locales_to_render: List[str] = list(ordered_manifest_locales)
        for loc in explicit_target_locales:
            if loc not in locales_to_render:
                locales_to_render.append(loc)
        if not locales_to_render:
            locales_to_render = list(canonical_order)
    elif ordered_manifest_locales:
        locales_to_render = list(ordered_manifest_locales)
        for loc in explicit_target_locales:
            if loc not in locales_to_render:
                locales_to_render.append(loc)
    else:
        locales_to_render = list(canonical_order)

    raw_cues = raw.get("adr_cues") or []
    raw_cues_by_locale: Dict[str, List[Dict[str, Any]]] = {}
    for cue in raw_cues:
        if isinstance(cue, dict) and cue.get("locale"):
            raw_cues_by_locale.setdefault(str(cue["locale"]), []).append(cue)

    territories_out: List[Dict[str, Any]] = []
    line_source_lookup: Dict[Tuple[str, int, str], str] = {}

    for loc in locales_to_render:
        base_cfg = canonical_map.get(
            loc,
            {
                "locale": loc,
                "bcp47_tag": loc,
                "territory_label": loc,
                "direction": "rtl" if loc.lower().startswith(("ar", "he", "fa", "ur")) else "ltr",
                "expansion_factor": 1.10,
                "sample_super_prefix": project_title.upper()[:28],
            },
        )
        rt = terr_by_locale.get(loc, {})
        direction = str(rt.get("direction") or base_cfg["direction"]).lower()
        if loc.lower().startswith("ar"):
            direction = "rtl"

        raw_lines = rt.get("lines") or []
        locale_cues = raw_cues_by_locale.get(loc, [])
        lines_out: List[Dict[str, Any]] = []
        exp_factor = float(base_cfg.get("expansion_factor", 1.08))

        line_inputs: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
        if raw_lines:
            aligned_from_cues = len(locale_cues) == len(raw_lines)
            for idx, raw_line_obj in enumerate(raw_lines):
                rl = raw_line_obj if isinstance(raw_line_obj, dict) else {}
                if aligned_from_cues:
                    cue = locale_cues[idx]
                    s_idx = int(cue.get("scene_number") or 1)
                    sm = scene_lookup_map.get(s_idx, scene_meta[0])
                    in_tc = str(cue.get("in_tc") or sm["in_tc"])
                    out_tc = str(cue.get("out_tc") or sm["out_tc"])
                    parsed_st = _smpte_to_sec(in_tc)
                    parsed_en = _smpte_to_sec(out_tc)
                    st_s = parsed_st if parsed_st is not None else sm["start_sec"]
                    en_s = parsed_en if parsed_en is not None else sm["end_sec"]
                    src_line = str(cue.get("source_line") or sm["source_line"])
                    slot = {
                        "scene_index": sm["scene_index"],
                        "scene_title": sm["scene_title"],
                        "start_sec": round(st_s, 3),
                        "end_sec": round(en_s, 3),
                        "duration_sec": max(1.0, round(en_s - st_s, 3)),
                        "in_tc": in_tc,
                        "out_tc": out_tc,
                        "source_line": src_line,
                        "base_words": max(1, len(src_line.split())),
                        "base_syllables": max(1, int(round(len(src_line.split()) * 1.45))),
                    }
                elif rl.get("scene_index") is not None or rl.get("scene_number") is not None:
                    s_idx = int(rl.get("scene_index") or rl.get("scene_number") or 1)
                    slot = scene_lookup_map.get(s_idx, scene_meta[0])
                elif idx < len(scene_cue_slots):
                    slot = scene_cue_slots[idx]
                else:
                    slot = scene_meta[min(idx, len(scene_meta) - 1)]
                line_inputs.append((rl, slot))
        else:
            line_inputs = [({}, slot) for slot in scene_cue_slots]

        for idx, (rl, slot) in enumerate(line_inputs):
            dur_s = float(rl.get("duration_sec") or slot["duration_sec"])
            word_count = int(rl.get("word_count") if rl.get("word_count") is not None else max(3, int(round(slot["base_words"] * exp_factor))))
            syllables = int(rl.get("syllable_count") if rl.get("syllable_count") is not None else max(word_count, int(round(slot["base_syllables"] * exp_factor))))
            raw_wps = rl.get("target_wps")
            target_wps = round(float(raw_wps), 2) if raw_wps is not None else round(word_count / max(1.0, dur_s), 2)
            raw_ratio = rl.get("lip_sync_ratio")
            lip_ratio = round(float(raw_ratio), 2) if raw_ratio is not None else round(max(0.82, min(1.28, exp_factor * (0.98 if idx % 2 == 0 else 1.03))), 2)
            sync_status = str(rl.get("sync_status") or _classify_sync_status(lip_ratio, max_allowed_drift)).lower()

            if rl.get("translated_text"):
                translated_text = str(rl["translated_text"])
            elif loc == "en-US":
                translated_text = slot["source_line"]
            elif loc == "de-DE":
                translated_text = f"[DE] {slot['source_line']} (Präzisions-Synchronfassung)"
            elif loc == "fr-FR":
                translated_text = f"[FR] {slot['source_line']} (Version doublage studio)"
            elif loc == "es-419":
                translated_text = f"[ES-419] {slot['source_line']} (Doblaje neutro)"
            elif loc == "ja-JP":
                translated_text = f"[JA] {slot['scene_title']} — リップシンク調整済み吹替ライン"
            elif loc == "ar-SA":
                translated_text = f"النسخة العربية المتزامنة — {slot['scene_title']}"
            else:
                translated_text = f"[{loc}] {slot['source_line']}"

            line_source_lookup[(loc, slot["scene_index"], slot["in_tc"])] = slot["source_line"]
            lines_out.append(
                {
                    "scene_index": slot["scene_index"],
                    "scene_title": slot["scene_title"],
                    "start_sec": slot["start_sec"],
                    "end_sec": slot["end_sec"],
                    "duration_sec": dur_s,
                    "in_tc": slot["in_tc"],
                    "out_tc": slot["out_tc"],
                    "locale": loc,
                    "bcp47_tag": str(rl.get("bcp47_tag") or loc),
                    "translated_text": translated_text,
                    "syllable_count": syllables,
                    "word_count": word_count,
                    "target_wps": target_wps,
                    "lip_sync_ratio": lip_ratio,
                    "sync_status": sync_status,
                    "requires_viseme_retime": bool(rl.get("requires_viseme_retime", lip_ratio > 1.15)),
                }
            )

        exp_pct = float(rt.get("supers_expansion_pct") if rt.get("supers_expansion_pct") is not None else round((exp_factor - 1.0) * 100.0, 1))
        supers_status = str(rt.get("supers_status") or _classify_supers_status(exp_pct)).lower()
        supers_text = str(rt.get("localized_supers_text") or f"{base_cfg['sample_super_prefix']} · {project_title[:36]}")
        max_ratio = float(rt.get("max_lip_sync_ratio") or max((ln["lip_sync_ratio"] for ln in lines_out), default=1.0))

        territories_out.append(
            {
                "locale": loc,
                "bcp47_tag": str(rt.get("bcp47_tag") or base_cfg["bcp47_tag"]),
                "territory_label": str(rt.get("territory_label") or base_cfg["territory_label"]),
                "direction": direction,
                "adr_required": bool(rt.get("adr_required", loc != source_locale)),
                "lines": lines_out,
                "localized_supers_text": supers_text,
                "supers_expansion_pct": round(exp_pct, 1),
                "supers_status": supers_status,
                "max_lip_sync_ratio": round(max_ratio, 2),
                "compliance_notes": [str(n) for n in (rt.get("compliance_notes") or [])],
            }
        )

    adr_cues_out: List[Dict[str, Any]] = []
    if raw_cues:
        for idx, cue in enumerate(raw_cues, start=1):
            if not isinstance(cue, dict):
                continue
            s_idx = int(cue.get("scene_number") or 1)
            sm = scene_lookup_map.get(s_idx, scene_meta[0])
            in_tc = str(cue.get("in_tc") or sm["in_tc"])
            out_tc = str(cue.get("out_tc") or sm["out_tc"])
            start_sec = _smpte_to_sec(in_tc)
            if start_sec is None:
                start_sec = sm["start_sec"]
            loc = str(cue.get("locale") or "en-US")
            ratio = float(cue.get("lip_sync_ratio") or 1.0)
            adr_cues_out.append(
                {
                    "cue_id": str(cue.get("cue_id") or f"ADR-{idx:03d}"),
                    "scene_number": s_idx,
                    "start_sec": start_sec,
                    "character_name": str(cue.get("character_name") or "NARRATOR"),
                    "locale": loc,
                    "direction": "rtl" if loc.lower().startswith("ar") else "ltr",
                    "in_tc": in_tc,
                    "out_tc": out_tc,
                    "pre_roll_beeps": int(cue.get("pre_roll_beeps") if cue.get("pre_roll_beeps") is not None else 3),
                    "source_line": str(cue.get("source_line") or sm["source_line"]),
                    "adapted_line": str(cue.get("adapted_line") or sm["source_line"]),
                    "emotion_tag": str(cue.get("emotion_tag") or "controlled"),
                    "lip_sync_ratio": round(ratio, 2),
                    "sync_status": _classify_sync_status(ratio, max_allowed_drift),
                    "loop_group_flag": bool(cue.get("loop_group_flag", False)),
                }
            )
    if not adr_cues_out:
        cue_counter = 1
        for terr in territories_out:
            for ln in terr["lines"]:
                fallback_src = line_source_lookup.get(
                    (terr["locale"], ln["scene_index"], ln["in_tc"]),
                    scene_lookup_map.get(ln["scene_index"], scene_meta[0])["source_line"],
                )
                adr_cues_out.append(
                    {
                        "cue_id": f"ADR-{cue_counter:03d}",
                        "scene_number": ln["scene_index"],
                        "start_sec": ln["start_sec"],
                        "character_name": "VO / LEAD",
                        "locale": terr["locale"],
                        "direction": terr["direction"],
                        "in_tc": ln["in_tc"],
                        "out_tc": ln["out_tc"],
                        "pre_roll_beeps": 3,
                        "source_line": fallback_src,
                        "adapted_line": ln["translated_text"],
                        "emotion_tag": "focused",
                        "lip_sync_ratio": ln["lip_sync_ratio"],
                        "sync_status": ln["sync_status"],
                        "loop_group_flag": False,
                    }
                )
                cue_counter += 1

    if has_explicit_manifest and explicit_target_locales:
        target_locales = explicit_target_locales
    else:
        target_locales = [t["locale"] for t in territories_out]
    broadcast_ready = bool(raw.get("broadcast_ready", True))

    return {
        "project_title": project_title,
        "source_locale": source_locale,
        "target_locales": target_locales,
        "imsc1_profile": imsc1_profile,
        "max_allowed_wps": max_allowed_wps,
        "max_allowed_drift_ratio": max_allowed_drift,
        "broadcast_ready": broadcast_ready,
        "territories": territories_out,
        "adr_cues": adr_cues_out,
        "summary_notes": [str(n) for n in (raw.get("summary_notes") or [])],
    }


def _build_adr_csv(loc_state: Dict[str, Any]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "cue_id",
            "scene_number",
            "character_name",
            "locale",
            "in_tc",
            "out_tc",
            "pre_roll_beeps",
            "source_line",
            "adapted_line",
            "emotion_tag",
            "lip_sync_ratio",
            "loop_group_flag",
        ]
    )
    for cue in loc_state["adr_cues"]:
        writer.writerow(
            [
                cue["cue_id"],
                cue["scene_number"],
                cue["character_name"],
                cue["locale"],
                cue["in_tc"],
                cue["out_tc"],
                cue["pre_roll_beeps"],
                cue["source_line"],
                cue["adapted_line"],
                cue["emotion_tag"],
                f"{cue['lip_sync_ratio']:.2f}",
                str(cue["loop_group_flag"]).lower(),
            ]
        )
    return buf.getvalue()


def _build_localized_ttml(loc_state: Dict[str, Any]) -> str:
    """Generates W3C IMSC1 TTML 1.1 XML timed-text document with multi-locale div blocks."""
    title_esc = xml_escape(loc_state["project_title"])
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<tt xml:lang="en-US" xmlns="http://www.w3.org/ns/ttml" '
        'xmlns:tts="http://www.w3.org/ns/ttml#styling" '
        'xmlns:ttp="http://www.w3.org/ns/ttml#parameter" '
        'ttp:timeBase="smpte" ttp:frameRate="24" ttp:frameRateMultiplier="1 1" '
        'ttp:profile="http://www.w3.org/ns/ttml/profile/imsc1/text">',
        "  <head>",
        f"    <metadata><ttm:title xmlns:ttm=\"http://www.w3.org/ns/ttml#metadata\">{title_esc}</ttm:title></metadata>",
        "    <styling>",
        '      <style xml:id="sDefault" tts:fontFamily="proportionalSansSerif" tts:fontSize="100%" tts:color="#FFFFFF" tts:backgroundColor="#000000CC" tts:textAlign="center"/>',
        '      <style xml:id="sRtl" tts:direction="rtl" tts:unicodeBidi="embed" tts:textAlign="right"/>',
        "    </styling>",
        "    <layout>",
        '      <region xml:id="rBottomSafe" tts:origin="10% 80%" tts:extent="80% 12%" tts:displayAlign="after"/>',
        "    </layout>",
        "  </head>",
        "  <body>",
    ]
    for terr in loc_state["territories"]:
        loc_esc = xml_escape(terr["bcp47_tag"])
        style_ref = "sRtl" if terr["direction"] == "rtl" else "sDefault"
        lines.append(f'    <div xml:lang="{loc_esc}" region="rBottomSafe" style="{style_ref}">')
        for ln in terr["lines"]:
            begin_tc = xml_escape(ln["in_tc"])
            end_tc = xml_escape(ln["out_tc"])
            txt_esc = xml_escape(ln["translated_text"])
            lines.append(f'      <p begin="{begin_tc}" end="{end_tc}">{txt_esc}</p>')
        lines.append("    </div>")
    lines.extend(["  </body>", "</tt>", ""])
    return "\n".join(lines)


def _normalize_spotting_state(
    bible: MasterProductionBible,
    scene_time_lookup: Dict[int, Tuple[float, float]],
    total_runtime_sec: float,
) -> Dict[str, Any]:
    """Builds normalized PM-FEAT-028 J-Cut / L-Cut Spotting & BPM Beat-Grid state."""
    manifest_obj = getattr(bible, "spotting_manifest", None)
    if manifest_obj is None:
        manifest_obj = _try_synthesize_spotting_manifest(bible)
    raw = _to_plain(manifest_obj) or {}

    fps = int(raw.get("fps") or 24)
    bgm = getattr(bible, "master_bgm", None)
    default_bpm = float(getattr(bgm, "tempo_bpm", 120.0) or 120.0)
    tempo_bpm = float(raw.get("tempo_bpm") or default_bpm)
    if tempo_bpm <= 0:
        tempo_bpm = 120.0
    frames_per_beat = float(raw.get("frames_per_beat") or round((60.0 / tempo_bpm) * fps, 2))
    bar_length_beats = int(raw.get("bar_length_beats") or 4)
    project_title = str(getattr(bible, "project_title", "Omni Production") or "Omni Production")

    scenes = getattr(bible, "scenes", []) or []
    scene_blocks: List[Dict[str, Any]] = []
    for pos, scene in enumerate(scenes, start=1):
        s_idx = int(getattr(scene, "scene_index", pos))
        st_s, en_s = scene_time_lookup.get(s_idx, ((pos - 1) * 8.0, pos * 8.0))
        scene_blocks.append(
            {
                "scene_index": s_idx,
                "scene_title": str(getattr(scene, "scene_title", f"Scene {s_idx}") or f"Scene {s_idx}"),
                "start_sec": round(st_s, 3),
                "end_sec": round(en_s, 3),
                "in_tc": _sec_to_smpte(st_s, fps),
                "out_tc": _sec_to_smpte(en_s, fps),
                "edit_bridge_in": _to_plain(getattr(scene, "edit_bridge_in", None)),
            }
        )
    if not scene_blocks:
        dur = max(8.0, float(total_runtime_sec or 8.0))
        scene_blocks.append(
            {
                "scene_index": 1,
                "scene_title": "Scene 1",
                "start_sec": 0.0,
                "end_sec": dur,
                "in_tc": "00:00:00:00",
                "out_tc": _sec_to_smpte(dur, fps),
                "edit_bridge_in": None,
            }
        )

    runtime_sec = max(float(total_runtime_sec or 0.0), scene_blocks[-1]["end_sec"], 8.0)

    # Beat grid timestamps
    beat_sec = 60.0 / tempo_bpm
    beat_times: List[float] = []
    beat_grid_tc: List[str] = [str(tc) for tc in (raw.get("beat_grid_tc") or [])]
    if beat_grid_tc:
        for tc in beat_grid_tc:
            parsed = _smpte_to_sec(tc, fps)
            if parsed is not None:
                beat_times.append(parsed)
    if not beat_times:
        t = 0.0
        while t <= runtime_sec + 0.001 and len(beat_times) < 256:
            beat_times.append(round(t, 4))
            beat_grid_tc.append(_sec_to_smpte(t, fps))
            t += beat_sec

    # Bridges
    raw_bridges = raw.get("bridges") or []
    bridges_out: List[Dict[str, Any]] = []
    block_by_idx = {b["scene_index"]: b for b in scene_blocks}

    if raw_bridges:
        for idx, br in enumerate(raw_bridges):
            if not isinstance(br, dict):
                continue
            from_s = int(br.get("from_scene") or max(1, idx + 1))
            to_s = int(br.get("to_scene") or (from_s + 1))
            cut_tc = str(br.get("cut_tc") or block_by_idx.get(to_s, scene_blocks[0])["in_tc"])
            cut_sec = _smpte_to_sec(cut_tc, fps)
            if cut_sec is None:
                cut_sec = float(block_by_idx.get(to_s, scene_blocks[0])["start_sec"])
            btype = str(br.get("bridge_type") or "j_cut").lower()
            j_f = int(br.get("j_prelap_frames") or 0)
            l_f = int(br.get("l_overhang_frames") or 0)
            bridges_out.append(
                {
                    "bridge_index": idx + 1,
                    "from_scene": from_s,
                    "to_scene": to_s,
                    "cut_tc": cut_tc,
                    "cut_sec": round(cut_sec, 3),
                    "bridge_type": btype,
                    "j_prelap_frames": j_f,
                    "l_overhang_frames": l_f,
                    "bridge_duration_sec": round(float(br.get("bridge_duration_sec") or ((j_f + l_f) / float(fps))), 3),
                    "nearest_beat_index": int(br.get("nearest_beat_index") or 0),
                    "beat_offset_frames": int(br.get("beat_offset_frames") or 0),
                    "beat_locked": bool(br.get("beat_locked", True)),
                    "sonic_anchor_cue": str(br.get("sonic_anchor_cue") or f"Pre-lap atmospheric bed S{to_s:02d}"),
                    "rationale": str(br.get("rationale") or "Beat-locked split edit across picture cut."),
                }
            )
    else:
        for i in range(1, len(scene_blocks)):
            prev_b = scene_blocks[i - 1]
            curr_b = scene_blocks[i]
            eb = curr_b.get("edit_bridge_in") or {}
            cut_sec = float(curr_b["start_sec"])
            cut_tc = str(eb.get("cut_tc") or curr_b["in_tc"])
            if eb:
                btype = str(eb.get("bridge_type") or "j_cut").lower()
                j_f = int(eb.get("j_prelap_frames") or 0)
                l_f = int(eb.get("l_overhang_frames") or 0)
                beat_idx = int(eb.get("nearest_beat_index") or max(0, round(cut_sec / beat_sec)))
                beat_off = int(eb.get("beat_offset_frames") or 0)
                anchor = str(eb.get("sonic_anchor_cue") or f"Audio bridge S{prev_b['scene_index']:02d}->S{curr_b['scene_index']:02d}")
                rationale = str(eb.get("rationale") or "Scene-level J/L split edit.")
            else:
                if i % 3 == 1:
                    btype, j_f, l_f = "j_cut", 12, 0
                    anchor = f"A2 SFX pre-lap into {curr_b['scene_title']}"
                elif i % 3 == 2:
                    btype, j_f, l_f = "l_cut", 0, 12
                    anchor = f"A1 Dialogue overhang from {prev_b['scene_title']}"
                else:
                    btype, j_f, l_f = "jl_overlap", 8, 8
                    anchor = f"A3 Music stem cross-bridge S{prev_b['scene_index']:02d}->{curr_b['scene_index']:02d}"
                nearest_bt = min(range(len(beat_times)), key=lambda bi: abs(beat_times[bi] - cut_sec)) if beat_times else 0
                beat_idx = nearest_bt
                beat_off = int(round((cut_sec - (beat_times[nearest_bt] if beat_times else cut_sec)) * fps))
                rationale = "Smooths editorial picture cut onto rhythmic bar downbeat."
            bridges_out.append(
                {
                    "bridge_index": i,
                    "from_scene": prev_b["scene_index"],
                    "to_scene": curr_b["scene_index"],
                    "cut_tc": cut_tc,
                    "cut_sec": round(cut_sec, 3),
                    "bridge_type": btype,
                    "j_prelap_frames": j_f,
                    "l_overhang_frames": l_f,
                    "bridge_duration_sec": round((j_f + l_f) / float(fps), 3),
                    "nearest_beat_index": beat_idx,
                    "beat_offset_frames": beat_off,
                    "beat_locked": abs(beat_off) <= 3,
                    "sonic_anchor_cue": anchor,
                    "rationale": rationale,
                }
            )

    # Spotting cues
    raw_cues = raw.get("spotting_cues") or []
    cues_out: List[Dict[str, Any]] = []
    if raw_cues:
        for idx, cue in enumerate(raw_cues, start=1):
            if not isinstance(cue, dict):
                continue
            s_num = int(cue.get("scene_number") or 1)
            sb = block_by_idx.get(s_num, scene_blocks[0])
            in_tc = str(cue.get("in_tc") or sb["in_tc"])
            out_tc = str(cue.get("out_tc") or sb["out_tc"])
            cues_out.append(
                {
                    "cue_id": str(cue.get("cue_id") or f"SPOT-{idx:03d}"),
                    "scene_number": s_num,
                    "cue_category": str(cue.get("cue_category") or "music_stem"),
                    "in_tc": in_tc,
                    "out_tc": out_tc,
                    "duration_frames": int(cue.get("duration_frames") or max(24, round((sb["end_sec"] - sb["start_sec"]) * fps))),
                    "stem_target": str(cue.get("stem_target") or "A3_MUSIC"),
                    "downbeat_bar": int(cue.get("downbeat_bar") or idx),
                    "lufs_target": float(cue.get("lufs_target") if cue.get("lufs_target") is not None else -24.0),
                    "description": str(cue.get("description") or sb["scene_title"]),
                }
            )
    else:
        for idx, sb in enumerate(scene_blocks, start=1):
            dur_f = max(24, int(round((sb["end_sec"] - sb["start_sec"]) * fps)))
            cues_out.append(
                {
                    "cue_id": f"SPOT-M{idx:02d}",
                    "scene_number": sb["scene_index"],
                    "cue_category": "music_underscore",
                    "in_tc": sb["in_tc"],
                    "out_tc": sb["out_tc"],
                    "duration_frames": dur_f,
                    "stem_target": "A3_MUSIC",
                    "downbeat_bar": max(1, 1 + (idx - 1) * 2),
                    "lufs_target": -24.0,
                    "description": f"BPM {tempo_bpm:.0f} rhythmic pulse — {sb['scene_title']}",
                }
            )
            cues_out.append(
                {
                    "cue_id": f"SPOT-FX{idx:02d}",
                    "scene_number": sb["scene_index"],
                    "cue_category": "foley_hit",
                    "in_tc": sb["in_tc"],
                    "out_tc": sb["out_tc"],
                    "duration_frames": dur_f,
                    "stem_target": "A2_SFX",
                    "downbeat_bar": max(1, 1 + (idx - 1) * 2),
                    "lufs_target": -20.0,
                    "description": f"Diegetic foley & transition transient — {sb['scene_title']}",
                }
            )

    beat_alignment_score = float(raw.get("beat_alignment_score") if raw.get("beat_alignment_score") is not None else 96.0)
    total_split_edits = int(raw.get("total_split_edits") if raw.get("total_split_edits") is not None else len(bridges_out))
    recommended_tracks = int(raw.get("recommended_nle_track_count") or 6)

    return {
        "project_title": project_title,
        "fps": fps,
        "tempo_bpm": round(tempo_bpm, 1),
        "frames_per_beat": round(frames_per_beat, 2),
        "bar_length_beats": bar_length_beats,
        "runtime_sec": round(runtime_sec, 3),
        "beat_grid_tc": beat_grid_tc,
        "beat_times": beat_times,
        "scenes": [
            {
                "scene_index": sb["scene_index"],
                "scene_title": sb["scene_title"],
                "start_sec": sb["start_sec"],
                "end_sec": sb["end_sec"],
                "in_tc": sb["in_tc"],
                "out_tc": sb["out_tc"],
            }
            for sb in scene_blocks
        ],
        "bridges": bridges_out,
        "spotting_cues": cues_out,
        "beat_alignment_score": round(beat_alignment_score, 1),
        "total_split_edits": total_split_edits,
        "recommended_nle_track_count": recommended_tracks,
    }


def _build_spotting_csv(spot_state: Dict[str, Any]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "cue_id",
            "scene_number",
            "cue_category",
            "in_tc",
            "out_tc",
            "duration_frames",
            "stem_target",
            "downbeat_bar",
            "lufs_target",
            "description",
        ]
    )
    for cue in spot_state["spotting_cues"]:
        writer.writerow(
            [
                cue["cue_id"],
                cue["scene_number"],
                cue["cue_category"],
                cue["in_tc"],
                cue["out_tc"],
                cue["duration_frames"],
                cue["stem_target"],
                cue["downbeat_bar"],
                f"{cue['lufs_target']:.1f}",
                cue["description"],
            ]
        )
    return buf.getvalue()


def _build_spotting_markdown(spot_state: Dict[str, Any]) -> str:
    def _esc_md(val: Any) -> str:
        return str(val or "").replace("|", "\\|").replace("\r", " ").replace("\n", " ")

    lines = [
        f"# Editorial J-Cut / L-Cut Spotting Sheet: {_esc_md(spot_state['project_title'])}",
        "",
        f"- **FPS**: `{spot_state['fps']}`",
        f"- **Tempo**: `{spot_state['tempo_bpm']} BPM` (`{spot_state['frames_per_beat']} frames/beat`, `{spot_state['bar_length_beats']}/4` bar)",
        f"- **Beat Alignment Score**: `{spot_state['beat_alignment_score']}/100`",
        f"- **Total Split Edits**: `{spot_state['total_split_edits']}`",
        "",
        "## J-Cut / L-Cut Audio Bridges",
        "| Cut | SMPTE Cut TC | Type | J-Pre-Lap | L-Overhang | Beat Offset | Sonic Anchor Cue |",
        "|---|---|---|---|---|---|---|",
    ]
    for br in spot_state["bridges"]:
        lines.append(
            f"| S{br['from_scene']:02d} -> S{br['to_scene']:02d} | `{_esc_md(br['cut_tc'])}` | `{_esc_md(br['bridge_type'].upper())}` | "
            f"`-{br['j_prelap_frames']}f` | `+{br['l_overhang_frames']}f` | `{br['beat_offset_frames']:+d}f` | {_esc_md(br['sonic_anchor_cue'])} |"
        )
    lines.extend(
        [
            "",
            "## Music & Foley Spotting Cues",
            "| Cue ID | Scene | Category | Stem | In TC | Out TC | Bar | LUFS | Description |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
    )
    for cue in spot_state["spotting_cues"]:
        lines.append(
            f"| `{_esc_md(cue['cue_id'])}` | {cue['scene_number']} | {_esc_md(cue['cue_category'])} | `{_esc_md(cue['stem_target'])}` | "
            f"`{_esc_md(cue['in_tc'])}` | `{_esc_md(cue['out_tc'])}` | {cue['downbeat_bar']} | {cue['lufs_target']:.1f} | {_esc_md(cue['description'])} |"
        )
    return "\n".join(lines) + "\n"


def _build_split_edits_edl(spot_state: Dict[str, Any]) -> str:
    """Generates CMX 3600 EDL capturing V1 picture cuts and staggered A1/A2/A3 J-Cut/L-Cut tracks."""
    fps = int(spot_state.get("fps") or 24)
    title_clean = re.sub(r"[^A-Za-z0-9_ -]+", "", spot_state["project_title"]).strip() or "OMNI_SPOTTING"
    lines = [
        f"TITLE: {title_clean[:48]}_SPLIT_EDITS",
        "FCM: NON-DROP FRAME",
        "",
    ]
    evt = 1
    bridges_by_to = {br["to_scene"]: br for br in spot_state["bridges"]}
    bridges_by_from = {br["from_scene"]: br for br in spot_state["bridges"]}

    for sc in spot_state["scenes"]:
        s_idx = sc["scene_index"]
        in_sec = float(sc["start_sec"])
        out_sec = float(sc["end_sec"])
        v_in = _sec_to_smpte(in_sec, fps)
        v_out = _sec_to_smpte(out_sec, fps)
        lines.append(f"{evt:03d}  AX       V     C        {v_in} {v_out} {v_in} {v_out}")
        lines.append(f"* FROM CLIP NAME: SCENE_{s_idx:02d}_{sc['scene_title'][:28].upper()}")
        evt += 1

        br_in = bridges_by_to.get(s_idx)
        br_out = bridges_by_from.get(s_idx)
        j_sec = (float(br_in["j_prelap_frames"]) / float(fps)) if br_in else 0.0
        l_sec = (float(br_out["l_overhang_frames"]) / float(fps)) if br_out else 0.0
        a_in = max(0.0, in_sec - j_sec)
        a_out = max(a_in + 0.5, out_sec + l_sec)
        a_in_tc = _sec_to_smpte(a_in, fps)
        a_out_tc = _sec_to_smpte(a_out, fps)
        lines.append(f"{evt:03d}  AX       A1A2  C        {a_in_tc} {a_out_tc} {a_in_tc} {a_out_tc}")
        if br_in and br_in["j_prelap_frames"] > 0:
            lines.append(f"* SPLIT: J-CUT PRE-LAP -{br_in['j_prelap_frames']}F ({br_in['sonic_anchor_cue']})")
        if br_out and br_out["l_overhang_frames"] > 0:
            lines.append(f"* SPLIT: L-CUT OVERHANG +{br_out['l_overhang_frames']}F ({br_out['sonic_anchor_cue']})")
        evt += 1

    lines.append("")
    return "\n".join(lines)


def _resolve_localized_ttml_payload(
    bible: MasterProductionBible,
    loc_state: Dict[str, Any],
) -> str:
    """Uses canonical localization_adr.build_imsc1_ttml_xml when importable; falls back to local builder on ImportError."""
    try:
        from omni_director.tools.localization_adr import build_imsc1_ttml_xml
    except ImportError:
        return _build_localized_ttml(loc_state)
    return build_imsc1_ttml_xml(bible)


def _resolve_split_edit_edl_payload(
    bible: MasterProductionBible,
    spot_state: Dict[str, Any],
) -> str:
    """Uses canonical editorial_spotting.build_split_edit_edl_text when importable; falls back to local builder on ImportError."""
    try:
        from omni_director.tools.editorial_spotting import build_split_edit_edl_text
    except ImportError:
        return _build_split_edits_edl(spot_state)
    return build_split_edit_edl_text(bible, fps=24)


def build_v214_hud_bundle(
    bible: MasterProductionBible,
    bundle: ProductionBundle,
    scene_time_lookup: Dict[int, Tuple[float, float]],
    total_runtime_sec: float,
) -> Dict[str, str]:
    """Builds CSS, modals HTML, and JS for PM-FEAT-027 (Localization & ADR) and PM-FEAT-028 (Spotting & Beat-Grid)."""
    del bundle
    loc_state = _normalize_localization_state(bible, scene_time_lookup, total_runtime_sec)
    spot_state = _normalize_spotting_state(bible, scene_time_lookup, total_runtime_sec)

    loc_json_escaped = _escape_js_template_literal(json.dumps(loc_state, indent=2))
    adr_csv_escaped = _escape_js_template_literal(_build_adr_csv(loc_state))
    loc_ttml_escaped = _escape_js_template_literal(_resolve_localized_ttml_payload(bible, loc_state))
    loc_state_json = _escape_json_for_script(loc_state)

    spot_json_escaped = _escape_js_template_literal(json.dumps(spot_state, indent=2))
    spot_csv_escaped = _escape_js_template_literal(_build_spotting_csv(spot_state))
    spot_md_escaped = _escape_js_template_literal(_build_spotting_markdown(spot_state))
    spot_edl_escaped = _escape_js_template_literal(_resolve_split_edit_edl_payload(bible, spot_state))
    spot_state_json = _escape_json_for_script(spot_state)

    first_terr = loc_state["territories"][0]
    first_supers_cls = (
        "v214-badge-pass"
        if first_terr["supers_status"] == "clear"
        else ("v214-badge-warn" if first_terr["supers_status"] == "tight_wrap" else "v214-badge-fail")
    )
    loc_ready_cls = "v214-badge-pass" if loc_state["broadcast_ready"] else "v214-badge-warn"
    loc_ready_lbl = "BROADCAST READY" if loc_state["broadcast_ready"] else "REVIEW NEEDED"

    territory_pills = "".join(
        f'<button type="button" class="btn-loc-locale{" active" if idx == 0 else ""}" '
        f'id="loc-locale-pill-{html_escape(t["locale"])}" data-locale="{html_escape(t["locale"])}">'
        f'{html_escape(t["locale"])} {"(RTL)" if t["direction"] == "rtl" else ""}</button>'
        for idx, t in enumerate(loc_state["territories"])
    )

    adr_rows_html = "".join(
        f'<tr class="loc-adr-row" data-locale="{html_escape(cue["locale"])}" data-scene-index="{cue["scene_number"]}" '
        f'data-start-sec="{cue["start_sec"]:.3f}" data-cue-id="{html_escape(cue["cue_id"])}" tabindex="0">'
        f'<td><code>{html_escape(cue["cue_id"])}</code></td>'
        f'<td><strong>S{cue["scene_number"]:02d}</strong></td>'
        f'<td>{html_escape(cue["character_name"])}</td>'
        f'<td><code>{html_escape(cue["locale"])}</code></td>'
        f'<td><code>{html_escape(cue["in_tc"])} → {html_escape(cue["out_tc"])}</code></td>'
        f'<td><span class="v214-badge v214-badge-cyan">{cue["pre_roll_beeps"]} Beeps</span></td>'
        f'<td dir="{html_escape(cue["direction"])}">{html_escape(cue["adapted_line"])}</td>'
        f'<td><span class="v214-badge {"v214-badge-pass" if cue["sync_status"] == "locked" else ("v214-badge-warn" if cue["sync_status"] == "stretch_caution" else "v214-badge-fail")}">{cue["lip_sync_ratio"]:.2f}x</span></td>'
        f'</tr>'
        for cue in loc_state["adr_cues"]
    )

    bridge_rows_html = "".join(
        f'<tr class="spotting-bridge-row{" active-row" if idx == 0 else ""}" data-bridge-index="{br["bridge_index"]}" '
        f'data-cut-sec="{br["cut_sec"]:.3f}" tabindex="0">'
        f'<td><strong>S{br["from_scene"]:02d} → S{br["to_scene"]:02d}</strong></td>'
        f'<td><code>{html_escape(br["cut_tc"])}</code></td>'
        f'<td><span class="v214-badge {"v214-badge-cyan" if br["bridge_type"] == "j_cut" else ("v214-badge-warn" if br["bridge_type"] == "l_cut" else "v214-badge-pass")}">{html_escape(br["bridge_type"].upper())}</span></td>'
        f'<td><code>-{br["j_prelap_frames"]}f</code></td>'
        f'<td><code>+{br["l_overhang_frames"]}f</code></td>'
        f'<td><code>{br["beat_offset_frames"]:+d}f</code></td>'
        f'<td>{html_escape(br["sonic_anchor_cue"])}</td>'
        f'</tr>'
        for idx, br in enumerate(spot_state["bridges"])
    )
    if not bridge_rows_html:
        bridge_rows_html = (
            '<tr><td colspan="7" style="text-align:center;color:var(--text-muted);">'
            "Single-scene timeline — no inter-scene split edits required."
            "</td></tr>"
        )

    spotting_cue_rows_html = "".join(
        f'<tr>'
        f'<td><code>{html_escape(cue["cue_id"])}</code></td>'
        f'<td><strong>S{cue["scene_number"]:02d}</strong></td>'
        f'<td><code>{html_escape(cue["stem_target"])}</code></td>'
        f'<td><code>{html_escape(cue["in_tc"])} → {html_escape(cue["out_tc"])}</code></td>'
        f'<td>Bar {cue["downbeat_bar"]}</td>'
        f'<td><code>{cue["lufs_target"]:.1f} LUFS</code></td>'
        f'<td>{html_escape(cue["description"])}</td>'
        f'</tr>'
        for cue in spot_state["spotting_cues"]
    )

    beat_score_cls = "v214-badge-pass" if spot_state["beat_alignment_score"] >= 85.0 else "v214-badge-warn"

    v214_css = """
    /* PM-FEAT-027 Localization & ADR Dubbing HUD + PM-FEAT-028 Editorial Spotting & Beat-Grid HUD */
    .localization-hud-modal, .spotting-hud-modal {
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
    .localization-modal-content, .spotting-modal-content {
      background: var(--bg-surface);
      border: 1px solid var(--border-focus);
      border-radius: 8px;
      max-width: 1180px;
      width: 100%;
      max-height: 90vh;
      overflow-y: auto;
      box-shadow: 0 24px 48px rgba(0, 0, 0, 0.8), 0 0 20px rgba(0, 240, 255, 0.15);
      display: flex;
      flex-direction: column;
    }
    .localization-modal-header, .spotting-modal-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 16px 20px;
      border-bottom: 1px solid var(--border-subtle);
      background: var(--bg-card);
    }
    .v214-title-wrap {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .v214-heading {
      font-family: 'Space Grotesk', sans-serif;
      font-size: 16px;
      font-weight: 700;
      letter-spacing: 0.05em;
      color: var(--text-main);
      margin: 0;
    }
    .v214-subheading {
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      color: var(--cyan-telemetry);
      display: block;
    }
    .btn-localization-close, .btn-spotting-close {
      background: transparent;
      border: 1px solid var(--border-subtle);
      color: var(--text-muted);
      width: 32px;
      height: 32px;
      border-radius: 4px;
      cursor: pointer;
      font-size: 15px;
    }
    .btn-localization-close:hover, .btn-localization-close:focus-visible,
    .btn-spotting-close:hover, .btn-spotting-close:focus-visible {
      border-color: var(--crimson-accent);
      color: var(--crimson-accent);
      outline: 2px solid var(--border-focus);
      outline-offset: 2px;
    }
    .v214-modal-body {
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    .v214-toolbar {
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
    .v214-badge-group, .v214-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }
    .v214-badge {
      display: inline-block;
      padding: 2px 7px;
      border-radius: 3px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 0.04em;
    }
    .v214-badge-pass {
      color: #10B981;
      background: rgba(16, 185, 129, 0.14);
      border: 1px solid rgba(16, 185, 129, 0.45);
    }
    .v214-badge-warn {
      color: var(--amber-gold);
      background: rgba(255, 184, 0, 0.14);
      border: 1px solid rgba(255, 184, 0, 0.45);
    }
    .v214-badge-fail {
      color: var(--red-rec);
      background: rgba(255, 59, 48, 0.14);
      border: 1px solid rgba(255, 59, 48, 0.45);
    }
    .v214-badge-cyan {
      color: var(--cyan-telemetry);
      background: rgba(0, 240, 255, 0.12);
      border: 1px solid rgba(0, 240, 255, 0.4);
    }
    .btn-v214-action {
      background: rgba(0, 240, 255, 0.12);
      border: 1px solid rgba(0, 240, 255, 0.4);
      color: var(--cyan-telemetry);
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      font-weight: 700;
      padding: 6px 12px;
      border-radius: 4px;
      cursor: pointer;
    }
    .btn-v214-action:hover, .btn-v214-action:focus-visible {
      background: rgba(0, 240, 255, 0.22);
      outline: 2px solid var(--border-focus);
      outline-offset: 2px;
    }
    .btn-v214-primary {
      background: rgba(255, 184, 0, 0.16);
      border: 1px solid rgba(255, 184, 0, 0.55);
      color: var(--amber-gold);
    }
    .btn-v214-primary:hover, .btn-v214-primary:focus-visible {
      background: rgba(255, 184, 0, 0.28);
      outline: 2px solid var(--amber-gold);
      outline-offset: 2px;
    }
    .v214-grid {
      display: grid;
      grid-template-columns: 1.05fr 1.15fr;
      gap: 16px;
    }
    @media (max-width: 920px) {
      .v214-grid {
        grid-template-columns: 1fr;
      }
    }
    .v214-panel {
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      border-radius: 6px;
      padding: 14px;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .v214-svg-wrap {
      background: #07080B;
      border: 1px solid var(--border-subtle);
      border-radius: 6px;
      overflow: hidden;
    }
    .v214-svg-wrap svg {
      width: 100%;
      height: auto;
      display: block;
    }
    .btn-loc-locale {
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      color: var(--text-muted);
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      font-weight: 700;
      padding: 5px 10px;
      border-radius: 4px;
      cursor: pointer;
    }
    .btn-loc-locale.active, .btn-loc-locale:hover, .btn-loc-locale:focus-visible {
      border-color: var(--cyan-telemetry);
      color: var(--cyan-telemetry);
      background: rgba(0, 240, 255, 0.14);
      outline: 2px solid var(--border-focus);
      outline-offset: 1px;
    }
    .loc-supers-safebox {
      background: #07080B;
      border: 1px dashed rgba(0, 240, 255, 0.45);
      border-radius: 6px;
      padding: 12px 14px;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .loc-supers-preview-text {
      font-family: 'Space Grotesk', 'Segoe UI', Tahoma, sans-serif;
      font-size: 14px;
      font-weight: 700;
      color: var(--text-main);
      padding: 8px 12px;
      background: rgba(20, 23, 34, 0.85);
      border: 1px solid var(--border-subtle);
      border-radius: 4px;
    }
    .loc-supers-preview-text[dir="rtl"], .loc-dialogue-preview[dir="rtl"] {
      text-align: right;
      unicode-bidi: isolate;
      border-right: 3px solid var(--cyan-telemetry);
    }
    .loc-dialogue-preview {
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      color: var(--text-main);
      background: #090B10;
      border: 1px solid var(--border-subtle);
      border-radius: 4px;
      padding: 8px 10px;
      min-height: 40px;
    }
    .v214-table-wrap {
      overflow-x: auto;
      max-height: 260px;
      overflow-y: auto;
      border: 1px solid var(--border-subtle);
      border-radius: 6px;
    }
    .v214-table {
      width: 100%;
      border-collapse: collapse;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
    }
    .v214-table th {
      background: #0B0D14;
      color: var(--text-muted);
      text-align: left;
      padding: 8px 10px;
      border-bottom: 1px solid var(--border-subtle);
      font-size: 10px;
      position: sticky;
      top: 0;
      z-index: 1;
    }
    .v214-table td {
      padding: 7px 10px;
      border-bottom: 1px solid rgba(32, 36, 52, 0.65);
      color: var(--text-main);
      vertical-align: top;
    }
    .loc-adr-row, .spotting-bridge-row {
      cursor: pointer;
    }
    .loc-adr-row:hover, .loc-adr-row:focus-visible, .loc-adr-row.active-row,
    .spotting-bridge-row:hover, .spotting-bridge-row:focus-visible, .spotting-bridge-row.active-row {
      background: rgba(0, 240, 255, 0.10);
      outline: none;
    }
    """

    v214_modals_html = f"""
  <!-- PM-FEAT-027: Multi-Language Localization, ADR Dubbing & Safe-Supers HUD -->
  <div id="animatic-localization-hud" class="localization-hud-modal" role="dialog" aria-modal="true" aria-labelledby="localization-hud-title" tabindex="-1" style="display:none;">
    <div class="localization-modal-content">
      <div class="localization-modal-header">
        <div class="v214-title-wrap">
          <span style="font-size:20px;" aria-hidden="true">🌐</span>
          <div>
            <h2 id="localization-hud-title" class="v214-heading">LOCALIZATION, ADR DUBBING &amp; SAFE-SUPERS HUD</h2>
            <span class="v214-subheading">PM-FEAT-027 · 6-TERRITORY BCP-47 · LIP-SYNC WPS DRIFT GATE · RTL SAFE-ZONE · IMSC1 TTML</span>
          </div>
        </div>
        <button type="button" class="btn-localization-close" onclick="toggleLocalizationHUD()" aria-label="Close Localization and ADR Dubbing HUD">✕</button>
      </div>

      <div class="v214-modal-body">
        <div class="v214-toolbar">
          <div class="v214-badge-group">
            <span class="aicp-badge">STATUS: <span class="v214-badge {loc_ready_cls}">{loc_ready_lbl}</span></span>
            <span class="aicp-badge">IMSC1: <strong>{html_escape(loc_state['imsc1_profile'])}</strong></span>
            <span class="aicp-badge">WPS CEILING: <strong>{loc_state['max_allowed_wps']:.1f} WPS</strong></span>
            <span class="aicp-badge">DRIFT GATE: <strong>{loc_state['max_allowed_drift_ratio']:.2f}x</strong></span>
            <span class="aicp-badge">SUPERS SAFE-ZONE: <span id="loc-supers-badge" class="v214-badge {first_supers_cls}">{html_escape(first_terr['supers_status'])} ({first_terr['supers_expansion_pct']:+.1f}%)</span></span>
          </div>
          <div class="v214-actions">
            <button type="button" class="btn-v214-action" id="btn-download-localization-json" onclick="downloadLocalizationJSON()" aria-label="Download Localization Manifest JSON">
              ⤓ localization_manifest.json
            </button>
            <button type="button" class="btn-v214-action" id="btn-download-adr-csv" onclick="downloadAdrCueSheetCSV()" aria-label="Download ADR Cue Sheet CSV">
              ⤓ adr_cue_sheet.csv
            </button>
            <button type="button" class="btn-v214-action" id="btn-download-localized-ttml" onclick="downloadLocalizedTTML()" aria-label="Download Localized IMSC1 Subtitles TTML">
              ⤓ subtitles_localized.ttml
            </button>
          </div>
        </div>

        <div class="v214-panel">
          <div class="drone-panel-header">
            <span>LIVE TERRITORY SWITCHER (BCP-47 · DIR=RTL ON AR-SA)</span>
            <span class="badge-canvas-telemetry" id="loc-active-locale-badge">{html_escape(first_terr['locale'])} · {html_escape(first_terr['territory_label'])}</span>
          </div>
          <div id="loc-locale-tablist" style="display:flex;flex-wrap:wrap;gap:6px;" role="tablist" aria-label="Localization Territory Switcher">
            {territory_pills}
          </div>
          <div class="loc-supers-safebox">
            <div style="display:flex;justify-content:space-between;align-items:center;font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--text-muted);">
              <span>SMPTE 80% TITLE-SAFE SUPERS PREVIEW (<span id="loc-dir-label">{html_escape(first_terr['direction'].upper())}</span>)</span>
              <span id="loc-expansion-label">EXPANSION: {first_terr['supers_expansion_pct']:+.1f}%</span>
            </div>
            <div id="loc-supers-preview" class="loc-supers-preview-text" dir="{html_escape(first_terr['direction'])}">
              {html_escape(first_terr['localized_supers_text'])}
            </div>
            <div id="loc-dialogue-preview" class="loc-dialogue-preview" dir="{html_escape(first_terr['direction'])}">
              {html_escape(first_terr['lines'][0]['translated_text'] if first_terr['lines'] else '')}
            </div>
          </div>
        </div>

        <div class="v214-grid">
          <div class="v214-panel">
            <div class="drone-panel-header">
              <span>LIP-SYNC SYLLABLE STRETCH TIMELINE (VS {loc_state['max_allowed_wps']:.1f} WPS &amp; {loc_state['max_allowed_drift_ratio']:.2f}x DRIFT)</span>
              <span class="badge-canvas-telemetry" id="loc-max-ratio-badge">MAX {first_terr['max_lip_sync_ratio']:.2f}x</span>
            </div>
            <div class="v214-svg-wrap">
              <svg id="localization-lipsync-svg" viewBox="0 0 640 260" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Lip-Sync Syllable Stretch and WPS Timeline"></svg>
            </div>
          </div>

          <div class="v214-panel">
            <div class="drone-panel-header">
              <span>ADR 3-BEEP SPOTTING CUE TABLE</span>
              <span class="badge-canvas-telemetry" id="loc-cue-count-badge">{len(loc_state['adr_cues'])} CUES</span>
            </div>
            <div class="v214-table-wrap">
              <table class="v214-table" aria-label="ADR 3-Beep Dubbing Cue Table">
                <thead>
                  <tr><th>Cue</th><th>Sc</th><th>Char</th><th>Locale</th><th>In → Out TC</th><th>Pre-Roll</th><th>Adapted Line</th><th>Drift</th></tr>
                </thead>
                <tbody id="loc-adr-tbody">
                  {adr_rows_html}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- PM-FEAT-028: Editorial J-Cut / L-Cut Spotting & Beat-Grid HUD -->
  <div id="animatic-spotting-hud" class="spotting-hud-modal" role="dialog" aria-modal="true" aria-labelledby="spotting-hud-title" tabindex="-1" style="display:none;">
    <div class="spotting-modal-content">
      <div class="spotting-modal-header">
        <div class="v214-title-wrap">
          <span style="font-size:20px;" aria-hidden="true">🎚️</span>
          <div>
            <h2 id="spotting-hud-title" class="v214-heading">EDITORIAL J-CUT / L-CUT SPOTTING &amp; BEAT-GRID HUD</h2>
            <span class="v214-subheading">PM-FEAT-028 · V1 PICTURE VS A1/A2/A3 SPLIT EDITS · BPM DOWNBEAT TICKS · CMX 3600 EDL</span>
          </div>
        </div>
        <button type="button" class="btn-spotting-close" onclick="toggleSpottingHUD()" aria-label="Close Editorial Spotting and Beat-Grid HUD">✕</button>
      </div>

      <div class="v214-modal-body">
        <div class="v214-toolbar">
          <div class="v214-badge-group">
            <span class="aicp-badge">TEMPO: <strong>{spot_state['tempo_bpm']:.1f} BPM</strong></span>
            <span class="aicp-badge">GRID: <strong>{spot_state['frames_per_beat']:.1f} f/beat</strong></span>
            <span class="aicp-badge">BEAT SYNC: <span class="v214-badge {beat_score_cls}">{spot_state['beat_alignment_score']:.1f}%</span></span>
            <span class="aicp-badge">SPLIT EDITS: <strong>{spot_state['total_split_edits']}</strong></span>
            <span class="aicp-badge">NLE TRACKS: <strong>{spot_state['recommended_nle_track_count']}</strong></span>
          </div>
          <div class="v214-actions">
            <button type="button" class="btn-v214-action btn-v214-primary" id="btn-spotting-next-bridge" onclick="jumpToNextSpottingBridge()" aria-label="Jump Playback to Next Audio Bridge">
              ⏭ Jump Playback to Next Bridge
            </button>
            <button type="button" class="btn-v214-action" id="btn-download-spotting-json" onclick="downloadSpottingJSON()" aria-label="Download Spotting Manifest JSON">
              ⤓ spotting_manifest.json
            </button>
            <button type="button" class="btn-v214-action" id="btn-download-spotting-csv" onclick="downloadSpottingCSV()" aria-label="Download Spotting Cue Sheet CSV">
              ⤓ spotting_cue_sheet.csv
            </button>
            <button type="button" class="btn-v214-action" id="btn-download-spotting-md" onclick="downloadSpottingMD()" aria-label="Download Spotting Sheet Markdown">
              ⤓ spotting_sheet.md
            </button>
            <button type="button" class="btn-v214-action" id="btn-download-spotting-edl" onclick="downloadSpottingEDL()" aria-label="Download Split-Edit Timeline EDL">
              ⤓ timeline_split_edits.edl
            </button>
          </div>
        </div>

        <div class="v214-panel">
          <div class="drone-panel-header">
            <span>V1 PICTURE CUTS VS STAGGERED A1 DIALOGUE / A2 SFX / A3 MUSIC PRE-LAP (-Nf) &amp; OVERHANG (+Nf)</span>
            <span class="badge-canvas-telemetry" id="spotting-active-bridge-badge">BRIDGE 01</span>
          </div>
          <div class="v214-svg-wrap">
            <svg id="spotting-timeline-svg" viewBox="0 0 640 270" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Editorial J-Cut L-Cut Beat-Grid and Audio Bridge Visualizer"></svg>
          </div>
        </div>

        <div class="v214-grid">
          <div class="v214-panel">
            <div class="drone-panel-header">
              <span>PER-CUT J/L BRIDGE TABLE</span>
              <span class="badge-canvas-telemetry">{len(spot_state['bridges'])} BRIDGES</span>
            </div>
            <div class="v214-table-wrap">
              <table class="v214-table" aria-label="Per-Cut J-Cut and L-Cut Audio Bridge Table">
                <thead>
                  <tr><th>Cut</th><th>Cut TC</th><th>Type</th><th>J-Cut</th><th>L-Cut</th><th>Beat Off</th><th>Sonic Anchor Cue</th></tr>
                </thead>
                <tbody id="spotting-bridge-tbody">
                  {bridge_rows_html}
                </tbody>
              </table>
            </div>
          </div>

          <div class="v214-panel">
            <div class="drone-panel-header">
              <span>MUSIC &amp; FOLEY SPOTTING CUES</span>
              <span class="badge-canvas-telemetry">{len(spot_state['spotting_cues'])} CUES</span>
            </div>
            <div class="v214-table-wrap">
              <table class="v214-table" aria-label="Music and Foley Spotting Cue Sheet Table">
                <thead>
                  <tr><th>Cue ID</th><th>Sc</th><th>Stem</th><th>In → Out TC</th><th>Bar</th><th>LUFS</th><th>Description</th></tr>
                </thead>
                <tbody>
                  {spotting_cue_rows_html}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
"""

    v214_js_template = """
    // PM-FEAT-027: Multi-Language Localization, ADR Dubbing & Safe-Supers HUD Controller
    const LOCALIZATION_STATE = __LOC_STATE_JSON__;
    let isLocalizationHUDOpen = false;
    let lastLocalizationOpener = null;
    let activeLocalizationLocale = (LOCALIZATION_STATE.territories && LOCALIZATION_STATE.territories.length)
      ? LOCALIZATION_STATE.territories[0].locale
      : 'en-US';
    let activeLocalizationSceneIdx = 1;

    function _renderLocalizationLipSyncSVG(terr) {
      const svg = document.getElementById('localization-lipsync-svg');
      if (!svg || !terr) return;
      const svgNS = 'http://www.w3.org/2000/svg';
      while (svg.firstChild) svg.removeChild(svg.firstChild);

      const addEl = (tag, attrs, textVal) => {
        const el = document.createElementNS(svgNS, tag);
        Object.keys(attrs).forEach((k) => el.setAttribute(k, String(attrs[k])));
        if (textVal !== undefined) el.textContent = String(textVal);
        svg.appendChild(el);
        return el;
      };

      const W = 640;
      const H = 260;
      const padL = 56;
      const padR = 24;
      const padT = 26;
      const padB = 42;
      const plotW = W - padL - padR;
      const plotH = H - padT - padB;
      const maxWpsCeiling = Number(LOCALIZATION_STATE.max_allowed_wps || 2.5);
      const maxDriftGate = Number(LOCALIZATION_STATE.max_allowed_drift_ratio || 1.15);
      const maxY = Math.max(3.5, maxWpsCeiling + 1.0);

      addEl('rect', { width: W, height: H, fill: '#07080B', rx: 6 });

      // Horizontal 2.5 WPS threshold line
      const yThresh = padT + plotH * (1 - (maxWpsCeiling / maxY));
      addEl('line', { x1: padL, y1: yThresh, x2: W - padR, y2: yThresh, stroke: '#FFB800', 'stroke-width': 1.5, 'stroke-dasharray': '5 4' });
      addEl('text', { x: padL + 4, y: yThresh - 5, fill: '#FFB800', 'font-family': 'JetBrains Mono, monospace', 'font-size': 9.5, 'font-weight': 700 }, maxWpsCeiling.toFixed(1) + ' WPS CEILING · ' + maxDriftGate.toFixed(2) + 'x DRIFT LIMIT');

      // Baseline axis
      addEl('line', { x1: padL, y1: padT + plotH, x2: W - padR, y2: padT + plotH, stroke: '#2A3045', 'stroke-width': 1.2 });
      addEl('line', { x1: padL, y1: padT, x2: padL, y2: padT + plotH, stroke: '#2A3045', 'stroke-width': 1.2 });

      const lines = terr.lines || [];
      if (!lines.length) {
        addEl('text', { x: W / 2, y: H / 2, 'text-anchor': 'middle', fill: '#8E95AA', 'font-family': 'JetBrains Mono, monospace', 'font-size': 11 }, 'No dialogue lines in territory');
        return;
      }

      const slotW = plotW / lines.length;
      const barW = Math.min(54, Math.max(8, slotW * 0.56));

      lines.forEach((ln, idx) => {
        const wps = Number(ln.target_wps || 0);
        const ratio = Number(ln.lip_sync_ratio || 1.0);
        const syncSt = String(ln.sync_status || '').toLowerCase();
        const isActive = Number(ln.scene_index) === Number(activeLocalizationSceneIdx);
        const cx = padL + slotW * idx + slotW / 2;
        const barH = Math.max(8, Math.min(plotH, (wps / maxY) * plotH));
        const bx = cx - barW / 2;
        const by = padT + plotH - barH;

        let color = '#10B981';
        if (ratio > 1.25 || syncSt === 'rescript_required') color = '#FF3B30';
        else if (ratio > 1.15 || syncSt === 'stretch_caution') color = '#FFB800';

        const bar = addEl('rect', {
          x: bx,
          y: by,
          width: barW,
          height: barH,
          rx: 4,
          fill: color,
          'fill-opacity': isActive ? '0.92' : '0.62',
          stroke: isActive ? '#00F0FF' : color,
          'stroke-width': isActive ? 2 : 1,
          style: 'cursor:pointer;'
        });
        bar.addEventListener('click', () => {
          seekLocalizationCue(ln.scene_index, ln.start_sec, 'S' + String(ln.scene_index).padStart(2, '0'));
        });

        addEl('text', { x: cx, y: by - 6, 'text-anchor': 'middle', fill: '#F0F2F8', 'font-family': 'JetBrains Mono, monospace', 'font-size': 9.5, 'font-weight': 700 }, ratio.toFixed(2) + 'x');
        addEl('text', { x: cx, y: padT + plotH + 15, 'text-anchor': 'middle', fill: isActive ? '#00F0FF' : '#8E95AA', 'font-family': 'JetBrains Mono, monospace', 'font-size': 9.5, 'font-weight': 700 }, 'S' + String(ln.scene_index).padStart(2, '0'));
        addEl('text', { x: cx, y: padT + plotH + 28, 'text-anchor': 'middle', fill: '#8E95AA', 'font-family': 'JetBrains Mono, monospace', 'font-size': 8.5 }, wps.toFixed(1) + ' wps');
      });

      addEl('text', { x: padL - 8, y: padT + 8, 'text-anchor': 'end', fill: '#8E95AA', 'font-family': 'JetBrains Mono, monospace', 'font-size': 9 }, maxY.toFixed(1));
      addEl('text', { x: padL - 8, y: padT + plotH, 'text-anchor': 'end', fill: '#8E95AA', 'font-family': 'JetBrains Mono, monospace', 'font-size': 9 }, '0.0');
    }

    function selectLocalizationLocale(locale) {
      const terr = (LOCALIZATION_STATE.territories || []).find((t) => t.locale === locale) || (LOCALIZATION_STATE.territories || [])[0];
      if (!terr) return;
      activeLocalizationLocale = terr.locale;

      document.querySelectorAll('.btn-loc-locale').forEach((btn) => {
        btn.classList.toggle('active', btn.getAttribute('data-locale') === terr.locale);
      });

      const locBadge = document.getElementById('loc-active-locale-badge');
      if (locBadge) locBadge.textContent = terr.locale + ' · ' + terr.territory_label;

      const dirLabel = document.getElementById('loc-dir-label');
      if (dirLabel) dirLabel.textContent = String(terr.direction || 'ltr').toUpperCase();

      const expVal = Number(terr.supers_expansion_pct || 0);
      const expFormatted = (expVal >= 0 ? '+' : '') + expVal.toFixed(1) + '%';
      const expLabel = document.getElementById('loc-expansion-label');
      if (expLabel) expLabel.textContent = 'EXPANSION: ' + expFormatted;

      const supersPreview = document.getElementById('loc-supers-preview');
      if (supersPreview) {
        supersPreview.setAttribute('dir', terr.direction || 'ltr');
        supersPreview.textContent = terr.localized_supers_text || '';
      }

      const activeLine = (terr.lines || []).find((l) => Number(l.scene_index) === Number(activeLocalizationSceneIdx)) || (terr.lines || [])[0];
      const dlgPreview = document.getElementById('loc-dialogue-preview');
      if (dlgPreview) {
        dlgPreview.setAttribute('dir', terr.direction || 'ltr');
        dlgPreview.textContent = activeLine ? ('S' + String(activeLine.scene_index).padStart(2, '0') + ': ' + activeLine.translated_text) : '';
      }

      const supersBadge = document.getElementById('loc-supers-badge');
      if (supersBadge) {
        const st = String(terr.supers_status || 'clear').toLowerCase();
        supersBadge.className = 'v214-badge ' + (st === 'clear' ? 'v214-badge-pass' : (st === 'tight_wrap' ? 'v214-badge-warn' : 'v214-badge-fail'));
        supersBadge.textContent = st + ' (' + expFormatted + ')';
      }

      const maxRatioBadge = document.getElementById('loc-max-ratio-badge');
      if (maxRatioBadge) maxRatioBadge.textContent = 'MAX ' + Number(terr.max_lip_sync_ratio || 1.0).toFixed(2) + 'x';

      // Filter ADR cue rows to prioritize selected territory while keeping multi-territory visibility clear
      let visibleCount = 0;
      document.querySelectorAll('.loc-adr-row').forEach((row) => {
        const rowLoc = row.getAttribute('data-locale');
        const matches = rowLoc === terr.locale;
        row.style.display = matches ? '' : 'none';
        if (matches) visibleCount += 1;
      });
      if (visibleCount === 0) {
        document.querySelectorAll('.loc-adr-row').forEach((row) => {
          row.style.display = '';
          visibleCount += 1;
        });
      }
      const cueCountBadge = document.getElementById('loc-cue-count-badge');
      if (cueCountBadge) cueCountBadge.textContent = visibleCount + ' CUES (' + terr.locale + ')';

      _renderLocalizationLipSyncSVG(terr);
      showToast('🌐 Localization Territory: ' + terr.locale + ' (' + String(terr.direction || 'ltr').toUpperCase() + ')');
    }

    function seekLocalizationCue(sceneIdx, startSec, cueLabel) {
      activeLocalizationSceneIdx = sceneIdx;
      const fps = (typeof FPS !== 'undefined' && FPS) ? FPS : 24;
      if (typeof renderFrame === 'function') renderFrame(Math.round(Number(startSec || 0) * fps));
      const terr = (LOCALIZATION_STATE.territories || []).find((t) => t.locale === activeLocalizationLocale) || (LOCALIZATION_STATE.territories || [])[0];
      if (terr) {
        const ln = (terr.lines || []).find((l) => Number(l.scene_index) === Number(sceneIdx) && Math.abs(Number(l.start_sec || 0) - Number(startSec || 0)) < 0.05)
          || (terr.lines || []).find((l) => Number(l.scene_index) === Number(sceneIdx));
        const dlgPreview = document.getElementById('loc-dialogue-preview');
        if (dlgPreview && ln) {
          dlgPreview.setAttribute('dir', terr.direction || 'ltr');
          dlgPreview.textContent = 'S' + String(ln.scene_index).padStart(2, '0') + ': ' + ln.translated_text;
        }
        _renderLocalizationLipSyncSVG(terr);
      }
      showToast('🎙️ ADR Cue ' + cueLabel + ' · Scene ' + String(sceneIdx).padStart(2, '0') + ' (' + activeLocalizationLocale + ')');
    }

    function updateLocalizationFromTimeline(tSec) {
      if (!isLocalizationHUDOpen) return;
      const terr = (LOCALIZATION_STATE.territories || []).find((t) => t.locale === activeLocalizationLocale) || (LOCALIZATION_STATE.territories || [])[0];
      if (!terr || !terr.lines || !terr.lines.length) return;
      let match = terr.lines.find((ln) => tSec >= ln.start_sec && tSec < ln.end_sec);
      if (!match) match = terr.lines[terr.lines.length - 1];
      if (match && Number(match.scene_index) !== Number(activeLocalizationSceneIdx)) {
        activeLocalizationSceneIdx = match.scene_index;
        const dlgPreview = document.getElementById('loc-dialogue-preview');
        if (dlgPreview) {
          dlgPreview.setAttribute('dir', terr.direction || 'ltr');
          dlgPreview.textContent = 'S' + String(match.scene_index).padStart(2, '0') + ': ' + match.translated_text;
        }
        _renderLocalizationLipSyncSVG(terr);
      }
    }

    function toggleLocalizationHUD() {
      isLocalizationHUDOpen = !isLocalizationHUDOpen;
      const modal = document.getElementById('animatic-localization-hud');
      const btn = document.getElementById('btn-localization-animatic');
      if (modal) modal.style.display = isLocalizationHUDOpen ? 'flex' : 'none';
      if (btn) {
        btn.classList.toggle('active', isLocalizationHUDOpen);
        btn.setAttribute('aria-expanded', isLocalizationHUDOpen ? 'true' : 'false');
      }
      if (isLocalizationHUDOpen) {
        lastLocalizationOpener = document.activeElement;
        selectLocalizationLocale(activeLocalizationLocale);
        const closeBtn = modal ? modal.querySelector('.btn-localization-close') : null;
        if (closeBtn) closeBtn.focus();
        showToast('🌐 Localization & ADR Dubbing HUD: ACTIVE [I]');
      } else if (lastLocalizationOpener && typeof lastLocalizationOpener.focus === 'function') {
        lastLocalizationOpener.focus();
      }
    }

    function initLocalizationHUD() {
      const tablist = document.getElementById('loc-locale-tablist');
      if (tablist && !tablist.dataset.delegatedBound) {
        tablist.dataset.delegatedBound = '1';
        tablist.addEventListener('click', (e) => {
          const btn = e.target.closest('[data-locale]');
          if (btn && tablist.contains(btn)) {
            selectLocalizationLocale(btn.dataset.locale);
          }
        });
      }
      const adrTbody = document.getElementById('loc-adr-tbody');
      if (adrTbody && !adrTbody.dataset.delegatedBound) {
        adrTbody.dataset.delegatedBound = '1';
        const triggerAdrRow = (row) => {
          const scIdx = Number(row.dataset.sceneIndex || 1);
          const startSec = Number(row.dataset.startSec || 0);
          const cueId = row.dataset.cueId || '';
          seekLocalizationCue(scIdx, startSec, cueId);
        };
        adrTbody.addEventListener('click', (e) => {
          const row = e.target.closest('.loc-adr-row[data-cue-id]');
          if (row && adrTbody.contains(row)) triggerAdrRow(row);
        });
        adrTbody.addEventListener('keydown', (e) => {
          if (e.key === 'Enter' || e.key === ' ' || e.code === 'Space') {
            const row = e.target.closest('.loc-adr-row[data-cue-id]');
            if (row && adrTbody.contains(row)) {
              e.preventDefault();
              e.stopPropagation();
              triggerAdrRow(row);
            }
          }
        });
      }
      selectLocalizationLocale(activeLocalizationLocale);
    }

    function downloadLocalizationJSON() {
      _triggerBlobDownload(`__LOC_JSON_ESCAPED__`, 'application/json;charset=utf-8;', 'localization_manifest.json', 'Downloaded Localization Manifest (localization_manifest.json)');
    }

    function downloadAdrCueSheetCSV() {
      _triggerBlobDownload(`__ADR_CSV_ESCAPED__`, 'text/csv;charset=utf-8;', 'adr_cue_sheet.csv', 'Downloaded ADR Cue Sheet (adr_cue_sheet.csv)');
    }

    function downloadLocalizedTTML() {
      _triggerBlobDownload(`__LOC_TTML_ESCAPED__`, 'application/ttml+xml;charset=utf-8;', 'subtitles_localized.ttml', 'Downloaded Localized IMSC1 Subtitles (subtitles_localized.ttml)');
    }

    // PM-FEAT-028: Editorial J-Cut / L-Cut Spotting & Beat-Grid HUD Controller
    const SPOTTING_STATE = __SPOT_STATE_JSON__;
    let isSpottingHUDOpen = false;
    let lastSpottingOpener = null;
    let activeSpottingBridgeIdx = (SPOTTING_STATE.bridges && SPOTTING_STATE.bridges.length) ? SPOTTING_STATE.bridges[0].bridge_index : 1;

    function _renderSpottingTimelineSVG(tSec) {
      const svg = document.getElementById('spotting-timeline-svg');
      if (!svg) return;
      const svgNS = 'http://www.w3.org/2000/svg';
      while (svg.firstChild) svg.removeChild(svg.firstChild);

      const addEl = (tag, attrs, textVal) => {
        const el = document.createElementNS(svgNS, tag);
        Object.keys(attrs).forEach((k) => el.setAttribute(k, String(attrs[k])));
        if (textVal !== undefined) el.textContent = String(textVal);
        svg.appendChild(el);
        return el;
      };

      const W = 640;
      const H = 270;
      const padL = 78;
      const padR = 20;
      const plotW = W - padL - padR;
      const runtime = Math.max(1.0, Number(SPOTTING_STATE.runtime_sec || 16.0));
      const fps = Number(SPOTTING_STATE.fps || 24);
      const xAt = (sec) => padL + (Math.max(0, Math.min(runtime, sec)) / runtime) * plotW;

      addEl('rect', { width: W, height: H, fill: '#07080B', rx: 6 });

      // BPM downbeat ticks
      const beats = SPOTTING_STATE.beat_times || [];
      const barLen = Number(SPOTTING_STATE.bar_length_beats || 4);
      beats.forEach((bt, idx) => {
        const bx = xAt(bt);
        const isDownbeat = (idx % barLen) === 0;
        addEl('line', {
          x1: bx,
          y1: 24,
          x2: bx,
          y2: 238,
          stroke: isDownbeat ? 'rgba(255, 184, 0, 0.32)' : 'rgba(142, 149, 170, 0.14)',
          'stroke-width': isDownbeat ? 1.4 : 0.8,
          'stroke-dasharray': isDownbeat ? 'none' : '2 3'
        });
        if (isDownbeat) {
          addEl('text', { x: bx + 2, y: 18, fill: '#FFB800', 'font-family': 'JetBrains Mono, monospace', 'font-size': 8.5, 'font-weight': 700 }, 'B' + (Math.floor(idx / barLen) + 1));
        }
      });

      const tracks = [
        { label: 'V1 PICTURE', y: 34, h: 36, color: '#00F0FF' },
        { label: 'A1 DIALOGUE', y: 84, h: 34, color: '#10B981' },
        { label: 'A2 SFX/FOLEY', y: 132, h: 34, color: '#A78BFA' },
        { label: 'A3 MUSIC', y: 180, h: 34, color: '#FFB800' }
      ];
      tracks.forEach((tr) => {
        addEl('text', { x: 10, y: tr.y + 21, fill: tr.color, 'font-family': 'JetBrains Mono, monospace', 'font-size': 9.5, 'font-weight': 700 }, tr.label);
        addEl('rect', { x: padL, y: tr.y, width: plotW, height: tr.h, rx: 4, fill: 'rgba(20, 23, 34, 0.72)', stroke: '#1E2336', 'stroke-width': 1 });
      });

      const bridges = SPOTTING_STATE.bridges || [];
      const bridgeByTo = {};
      const bridgeByFrom = {};
      bridges.forEach((b) => {
        bridgeByTo[b.to_scene] = b;
        bridgeByFrom[b.from_scene] = b;
      });

      (SPOTTING_STATE.scenes || []).forEach((sc, idx) => {
        const vx1 = xAt(sc.start_sec);
        const vx2 = xAt(sc.end_sec);
        const vw = Math.max(8, vx2 - vx1 - 2);
        addEl('rect', { x: vx1 + 1, y: 38, width: vw, height: 28, rx: 3, fill: 'rgba(0, 240, 255, 0.16)', stroke: '#00F0FF', 'stroke-width': 1.2 });
        addEl('text', { x: vx1 + vw / 2, y: 56, 'text-anchor': 'middle', fill: '#F0F2F8', 'font-family': 'JetBrains Mono, monospace', 'font-size': 9, 'font-weight': 700 }, 'S' + String(sc.scene_index).padStart(2, '0'));

        const brIn = bridgeByTo[sc.scene_index];
        const brOut = bridgeByFrom[sc.scene_index];
        const jSec = brIn ? (Number(brIn.j_prelap_frames || 0) / fps) : 0;
        const lSec = brOut ? (Number(brOut.l_overhang_frames || 0) / fps) : 0;

        // A1 Dialogue (L-Cut overhang extends right)
        const a1x1 = xAt(sc.start_sec);
        const a1x2 = xAt(Math.min(runtime, sc.end_sec + lSec));
        addEl('rect', { x: a1x1 + 1, y: 88, width: Math.max(8, a1x2 - a1x1 - 2), height: 26, rx: 3, fill: 'rgba(16, 185, 129, 0.22)', stroke: '#10B981', 'stroke-width': 1 });
        if (lSec > 0) {
          addEl('text', { x: a1x2 - 4, y: 104, 'text-anchor': 'end', fill: '#10B981', 'font-family': 'JetBrains Mono, monospace', 'font-size': 8.5, 'font-weight': 700 }, '+' + brOut.l_overhang_frames + 'f L');
        }

        // A2 SFX (J-Cut pre-lap extends left)
        const a2x1 = xAt(Math.max(0, sc.start_sec - jSec));
        const a2x2 = xAt(sc.end_sec);
        addEl('rect', { x: a2x1 + 1, y: 136, width: Math.max(8, a2x2 - a2x1 - 2), height: 26, rx: 3, fill: 'rgba(167, 139, 250, 0.22)', stroke: '#A78BFA', 'stroke-width': 1 });
        if (jSec > 0) {
          addEl('text', { x: a2x1 + 4, y: 152, fill: '#C4B5FD', 'font-family': 'JetBrains Mono, monospace', 'font-size': 8.5, 'font-weight': 700 }, '-' + brIn.j_prelap_frames + 'f J');
        }

        // A3 Music stem spans beat-locked bar
        const a3x1 = xAt(Math.max(0, sc.start_sec - jSec * 0.5));
        const a3x2 = xAt(Math.min(runtime, sc.end_sec + lSec * 0.5));
        addEl('rect', { x: a3x1 + 1, y: 184, width: Math.max(8, a3x2 - a3x1 - 2), height: 26, rx: 3, fill: 'rgba(255, 184, 0, 0.18)', stroke: '#FFB800', 'stroke-width': 1 });
        addEl('text', { x: a3x1 + 6, y: 200, fill: '#FFB800', 'font-family': 'JetBrains Mono, monospace', 'font-size': 8.5 }, 'M' + (idx + 1));
      });

      // Cut bridge markers
      bridges.forEach((br) => {
        const cx = xAt(br.cut_sec);
        const isActive = Number(br.bridge_index) === Number(activeSpottingBridgeIdx);
        addEl('line', { x1: cx, y1: 28, x2: cx, y2: 224, stroke: isActive ? '#FF3B30' : '#00F0FF', 'stroke-width': isActive ? 2.2 : 1.2, 'stroke-dasharray': isActive ? 'none' : '3 2' });
        const marker = addEl('circle', { cx: cx, cy: 230, r: isActive ? 6 : 4, fill: isActive ? '#FF3B30' : '#00F0FF', style: 'cursor:pointer;' });
        marker.addEventListener('click', () => jumpToSpottingBridge(br.bridge_index));
      });

      // Live playhead line
      const px = xAt(typeof tSec === 'number' ? tSec : 0);
      addEl('line', { x1: px, y1: 24, x2: px, y2: 238, stroke: '#FFFFFF', 'stroke-width': 1.5, opacity: 0.85 });

      addEl('text', { x: padL, y: 256, fill: '#8E95AA', 'font-family': 'JetBrains Mono, monospace', 'font-size': 9.5 },
        'BPM ' + Number(SPOTTING_STATE.tempo_bpm || 120).toFixed(1) + ' · ' + Number(SPOTTING_STATE.frames_per_beat || 12).toFixed(1) + ' f/beat · Click red/cyan cut nodes or "Jump Playback to Next Bridge"');
    }

    function highlightSpottingBridge(bridgeIdx, tSec) {
      activeSpottingBridgeIdx = bridgeIdx;
      document.querySelectorAll('.spotting-bridge-row').forEach((row) => {
        const idx = parseInt(row.getAttribute('data-bridge-index') || '0', 10);
        row.classList.toggle('active-row', idx === Number(bridgeIdx));
      });
      const badge = document.getElementById('spotting-active-bridge-badge');
      if (badge) badge.textContent = 'BRIDGE ' + String(bridgeIdx).padStart(2, '0');
      _renderSpottingTimelineSVG(tSec);
    }

    function jumpToSpottingBridge(bridgeIdx) {
      const bridges = SPOTTING_STATE.bridges || [];
      const br = bridges.find((b) => Number(b.bridge_index) === Number(bridgeIdx)) || bridges[0];
      if (!br) {
        showToast('🎚️ Single-scene timeline — no split-edit bridge to seek.');
        return;
      }
      const fps = Number(SPOTTING_STATE.fps || (typeof FPS !== 'undefined' ? FPS : 24) || 24);
      if (typeof renderFrame === 'function') {
        renderFrame(Math.round(Number(br.cut_sec || 0) * fps));
      }
      highlightSpottingBridge(br.bridge_index, br.cut_sec);
      showToast('🎚️ Bridge S' + String(br.from_scene).padStart(2, '0') + '→S' + String(br.to_scene).padStart(2, '0') + ' @ ' + br.cut_tc + ' (' + br.bridge_type.toUpperCase() + ')');
    }

    function jumpToNextSpottingBridge() {
      const bridges = SPOTTING_STATE.bridges || [];
      if (!bridges.length) {
        showToast('🎚️ No inter-scene J/L bridges in this single-scene sequence.');
        return;
      }
      const fps = Number(SPOTTING_STATE.fps || (typeof FPS !== 'undefined' ? FPS : 24) || 24);
      const currSec = (typeof currentFrame === 'number' ? currentFrame : 0) / fps;
      let nextBr = bridges.find((b) => Number(b.cut_sec) > currSec + 0.08);
      if (!nextBr) nextBr = bridges[0];
      jumpToSpottingBridge(nextBr.bridge_index);
    }

    function updateSpottingFromTimeline(tSec) {
      if (!isSpottingHUDOpen) return;
      const bridges = SPOTTING_STATE.bridges || [];
      if (bridges.length) {
        const nearest = bridges.reduce((best, b) => (Math.abs(b.cut_sec - tSec) < Math.abs(best.cut_sec - tSec) ? b : best), bridges[0]);
        activeSpottingBridgeIdx = nearest.bridge_index;
      }
      highlightSpottingBridge(activeSpottingBridgeIdx, tSec);
    }

    function toggleSpottingHUD() {
      isSpottingHUDOpen = !isSpottingHUDOpen;
      const modal = document.getElementById('animatic-spotting-hud');
      const btn = document.getElementById('btn-spotting-animatic');
      if (modal) modal.style.display = isSpottingHUDOpen ? 'flex' : 'none';
      if (btn) {
        btn.classList.toggle('active', isSpottingHUDOpen);
        btn.setAttribute('aria-expanded', isSpottingHUDOpen ? 'true' : 'false');
      }
      if (isSpottingHUDOpen) {
        lastSpottingOpener = document.activeElement;
        const fps = Number(SPOTTING_STATE.fps || (typeof FPS !== 'undefined' ? FPS : 24) || 24);
        const currSec = (typeof currentFrame === 'number' ? currentFrame : 0) / fps;
        highlightSpottingBridge(activeSpottingBridgeIdx, currSec);
        const closeBtn = modal ? modal.querySelector('.btn-spotting-close') : null;
        if (closeBtn) closeBtn.focus();
        showToast('🎚️ Editorial J-Cut / L-Cut Spotting HUD: ACTIVE [J]');
      } else if (lastSpottingOpener && typeof lastSpottingOpener.focus === 'function') {
        lastSpottingOpener.focus();
      }
    }

    function initSpottingHUD() {
      const bridgeTbody = document.getElementById('spotting-bridge-tbody');
      if (bridgeTbody && !bridgeTbody.dataset.delegatedBound) {
        bridgeTbody.dataset.delegatedBound = '1';
        const triggerBridgeRow = (row) => {
          const brIdx = parseInt(row.dataset.bridgeIndex || '0', 10);
          if (brIdx > 0) jumpToSpottingBridge(brIdx);
        };
        bridgeTbody.addEventListener('click', (e) => {
          const row = e.target.closest('.spotting-bridge-row[data-bridge-index]');
          if (row && bridgeTbody.contains(row)) triggerBridgeRow(row);
        });
        bridgeTbody.addEventListener('keydown', (e) => {
          if (e.key === 'Enter' || e.key === ' ' || e.code === 'Space') {
            const row = e.target.closest('.spotting-bridge-row[data-bridge-index]');
            if (row && bridgeTbody.contains(row)) {
              e.preventDefault();
              e.stopPropagation();
              triggerBridgeRow(row);
            }
          }
        });
      }
      highlightSpottingBridge(activeSpottingBridgeIdx, 0);
    }

    function downloadSpottingJSON() {
      _triggerBlobDownload(`__SPOT_JSON_ESCAPED__`, 'application/json;charset=utf-8;', 'spotting_manifest.json', 'Downloaded Spotting Manifest (spotting_manifest.json)');
    }

    function downloadSpottingCSV() {
      _triggerBlobDownload(`__SPOT_CSV_ESCAPED__`, 'text/csv;charset=utf-8;', 'spotting_cue_sheet.csv', 'Downloaded Spotting Cue Sheet (spotting_cue_sheet.csv)');
    }

    function downloadSpottingMD() {
      _triggerBlobDownload(`__SPOT_MD_ESCAPED__`, 'text/markdown;charset=utf-8;', 'spotting_sheet.md', 'Downloaded Spotting Sheet (spotting_sheet.md)');
    }

    function downloadSpottingEDL() {
      _triggerBlobDownload(`__SPOT_EDL_ESCAPED__`, 'text/plain;charset=utf-8;', 'timeline_split_edits.edl', 'Downloaded Split-Edit Timeline EDL (timeline_split_edits.edl)');
    }
"""

    v214_js = (
        v214_js_template
        .replace("__LOC_STATE_JSON__", loc_state_json)
        .replace("__LOC_JSON_ESCAPED__", loc_json_escaped)
        .replace("__ADR_CSV_ESCAPED__", adr_csv_escaped)
        .replace("__LOC_TTML_ESCAPED__", loc_ttml_escaped)
        .replace("__SPOT_STATE_JSON__", spot_state_json)
        .replace("__SPOT_JSON_ESCAPED__", spot_json_escaped)
        .replace("__SPOT_CSV_ESCAPED__", spot_csv_escaped)
        .replace("__SPOT_MD_ESCAPED__", spot_md_escaped)
        .replace("__SPOT_EDL_ESCAPED__", spot_edl_escaped)
    )

    return {
        "css": v214_css,
        "modals_html": v214_modals_html,
        "js": v214_js,
    }
