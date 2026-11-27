"""Modular v2.18.0 Dark-Room Cinema HUD Components (PM-FEAT-035 & PM-FEAT-036).

Provides Python 3.11-compatible builders for:
1. PM-FEAT-035: Live-Render Jobs, Take A/B/C QA & Mode B Frame-Anchor Handoff (#modal-render-jobs, [`] hotkey)
2. PM-FEAT-036: Director's Pitch Treatment Carousel, Revision Diff & Lookbook Studio (#modal-pitch-treatment, [-] hotkey)
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


def _normalize_qa_status(raw_status: Any, qa_score: float) -> str:
    """Normalizes render job QA status into canonical qa_passed / qa_flagged / pending."""
    val = str(raw_status or "").strip().lower()
    if val in {"qa_passed", "passed", "pass", "approved", "hero_locked"}:
        return "qa_passed"
    if val in {"qa_flagged", "flagged", "warn", "warning", "review", "failed"}:
        return "qa_flagged"
    if val in {"queued", "rendering", "pending", "simulated"}:
        return "qa_passed" if qa_score >= 90.0 else "qa_flagged"
    return "qa_passed" if qa_score >= 90.0 else "qa_flagged"


def _deterministic_seed(project_title: str, scene_index: int, take_key: str) -> int:
    digest = hashlib.sha256(f"{project_title}:{scene_index}:{take_key}".encode("utf-8")).hexdigest()
    return 1000 + (int(digest[:6], 16) % 8999)


def synthesize_v218_render_jobs_state(bible: Any, bundle: Any = None) -> Dict[str, Any]:
    """Extracts or deterministically synthesizes PM-FEAT-035 Live-Render Jobs & Take QA state."""
    project_title = str(_get_field(bible, "project_title", "Omni Production") or "Omni Production")
    aspect_val = _to_plain(_get_field(bible, "aspect_ratio", "16:9")) or "16:9"
    regime_val = str(_to_plain(_get_field(bible, "creative_regime", "REGIME 1: Photorealism")) or "REGIME 1: Photorealism")
    mode_val = str(_to_plain(_get_field(bible, "storytelling_mode", "Mode B: Continuous Narrative")) or "Mode B: Continuous Narrative")
    mode_b_enabled = "mode b" in mode_val.lower() or "continuous" in mode_val.lower()

    telemetry = _to_plain(_get_field(bundle, "telemetry", {}) or {}) if bundle is not None else {}
    existing = (
        _get_field(bible, "master_render_jobs", None)
        or _get_field(bible, "render_jobs", None)
        or _get_field(bundle, "master_render_jobs", None)
        or _get_field(bundle, "render_jobs", None)
        or (telemetry.get("master_render_jobs") if isinstance(telemetry, dict) else None)
    )
    plain_existing = _to_plain(existing)
    rendered_videos = _to_plain(_get_field(bundle, "rendered_videos", []) or []) if bundle is not None else []
    bundle_mode = str(_get_field(bundle, "mode", "dry-run") or "dry-run") if bundle is not None else "dry-run"

    scenes = _to_plain(_get_field(bible, "scenes", []) or [])
    if not scenes:
        scenes = [
            {
                "scene_index": 1,
                "scene_title": "Opening Hero Plate",
                "timestamp_range": "00:00-00:08",
            }
        ]

    raw_jobs_by_scene: Dict[int, Dict[str, Any]] = {}
    raw_handoffs: List[Dict[str, Any]] = []
    if isinstance(plain_existing, dict):
        raw_list = (
            plain_existing.get("jobs")
            or plain_existing.get("scene_jobs")
            or plain_existing.get("scene_renders")
            or []
        )
        if isinstance(raw_list, list):
            for idx, item in enumerate(raw_list):
                if isinstance(item, dict):
                    s_i = int(item.get("scene_index", idx + 1) or (idx + 1))
                    raw_jobs_by_scene[s_i] = item
        if isinstance(plain_existing.get("frame_anchor_handoffs"), list):
            raw_handoffs = [h for h in plain_existing["frame_anchor_handoffs"] if isinstance(h, dict)]
    elif isinstance(plain_existing, list):
        for idx, item in enumerate(plain_existing):
            if isinstance(item, dict):
                s_i = int(item.get("scene_index", idx + 1) or (idx + 1))
                raw_jobs_by_scene[s_i] = item

    handoffs_by_from: Dict[int, Dict[str, Any]] = {}
    handoffs_by_to: Dict[int, Dict[str, Any]] = {}
    for ho in raw_handoffs:
        if ho.get("from_scene_index") is not None:
            handoffs_by_from[int(ho["from_scene_index"])] = ho
        if ho.get("to_scene_index") is not None:
            handoffs_by_to[int(ho["to_scene_index"])] = ho

    def _map_take_slot(raw_take_id: Any, fallback_idx: Optional[int] = None) -> Optional[str]:
        val = str(raw_take_id or "").strip().upper()
        if val in {"A", "T1"} or val.endswith("_T1") or val.endswith("_A"):
            return "A"
        if val in {"B", "T2"} or val.endswith("_T2") or val.endswith("_B"):
            return "B"
        if val in {"C", "T3"} or val.endswith("_T3") or val.endswith("_C"):
            return "C"
        if fallback_idx is not None and 0 <= fallback_idx < 3:
            return ("A", "B", "C")[fallback_idx]
        return None

    rendered_by_scene: Dict[int, Dict[str, Any]] = {}
    if isinstance(rendered_videos, list):
        for idx, rv in enumerate(rendered_videos):
            if isinstance(rv, dict):
                s_i = int(rv.get("scene_index", idx + 1) or (idx + 1))
                rendered_by_scene[s_i] = rv

    scene_jobs: List[Dict[str, Any]] = []
    cursor_s = 0.0
    for idx, sc in enumerate(scenes):
        sc_dict = sc if isinstance(sc, dict) else {}
        s_idx = int(sc_dict.get("scene_index", idx + 1) or (idx + 1))
        s_title = str(sc_dict.get("scene_title") or f"Scene {s_idx}")
        st_s, en_s = _parse_scene_window(str(sc_dict.get("timestamp_range") or ""), cursor_s)
        dur_s = max(1.0, round(en_s - st_s, 2))
        cursor_s = en_s

        raw_job = raw_jobs_by_scene.get(s_idx, {})
        rv_item = rendered_by_scene.get(s_idx, {})

        # Map canonical take_scorecards (TakeQaScorecardSpec list) alongside legacy takes dict/list
        scorecards_by_slot: Dict[str, Dict[str, Any]] = {}
        raw_scorecards = raw_job.get("take_scorecards")
        if isinstance(raw_scorecards, list):
            for c_idx, card in enumerate(raw_scorecards):
                if not isinstance(card, dict):
                    continue
                slot = _map_take_slot(card.get("take_id"), c_idx)
                if slot and slot in scorecards_by_slot:
                    slot = next((k for k in ("A", "B", "C") if k not in scorecards_by_slot), None)
                if slot:
                    scorecards_by_slot[slot] = card
        qa_single = raw_job.get("qa_scorecard") if isinstance(raw_job.get("qa_scorecard"), dict) else None
        if qa_single is not None:
            q_slot = _map_take_slot(qa_single.get("take_id"), 0)
            if q_slot and q_slot not in scorecards_by_slot:
                scorecards_by_slot[q_slot] = qa_single

        takes_by_slot: Dict[str, Dict[str, Any]] = {}
        raw_takes_val = raw_job.get("takes")
        if isinstance(raw_takes_val, dict):
            for k, v in raw_takes_val.items():
                if not isinstance(v, dict):
                    continue
                slot = _map_take_slot(k) or _map_take_slot(v.get("take_id"))
                if slot:
                    takes_by_slot[slot] = v
        elif isinstance(raw_takes_val, list):
            for t_idx, v in enumerate(raw_takes_val):
                if not isinstance(v, dict):
                    continue
                slot = _map_take_slot(v.get("take_id"), t_idx)
                if slot:
                    takes_by_slot[slot] = v

        takes: Dict[str, Dict[str, Any]] = {}
        take_specs = [
            ("A", "T1", "Take A · Hero Primary", 95.4, 96.2, 4, 1.25),
            ("B", "T2", "Take B · Alt Kinetics", 92.6, 93.8, -8, 1.25),
            ("C", "T3", "Take C · Micro-Hold", 88.4, 89.5, 14, 1.15),
        ]
        for t_key, t_num, default_lbl, base_qa, base_opt, base_sync, base_cost in take_specs:
            sc_card = scorecards_by_slot.get(t_key, {})
            rt = takes_by_slot.get(t_key, {})
            adj = ((s_idx - 1) % 3) * 0.4
            qa_raw = (
                sc_card.get("composite_qa_score")
                if sc_card.get("composite_qa_score") is not None
                else (
                    rt.get("composite_qa_score")
                    if rt.get("composite_qa_score") is not None
                    else (rt.get("qa_score") if rt.get("qa_score") is not None else rt.get("audit_score"))
                )
            )
            qa_score = round(float(qa_raw if qa_raw is not None else (base_qa + adj)), 1)
            opt_raw = (
                sc_card.get("temporal_stability_score")
                if sc_card.get("temporal_stability_score") is not None
                else (
                    rt.get("temporal_stability_score")
                    if rt.get("temporal_stability_score") is not None
                    else rt.get("optical_score")
                )
            )
            opt_score = round(float(opt_raw if opt_raw is not None else (base_opt + adj * 0.5)), 1)
            rms_raw = (
                sc_card.get("audio_sync_rms_db")
                if sc_card.get("audio_sync_rms_db") is not None
                else rt.get("audio_sync_rms_db")
            )
            audio_rms_db = round(float(rms_raw if rms_raw is not None else -18.0), 2)
            sync_ms = int(rt.get("audio_sync_ms") if rt.get("audio_sync_ms") is not None else base_sync)
            cost_raw = rt.get("cost_usd") if rt.get("cost_usd") is not None else rt.get("estimated_cost_usd")
            cost_usd = round(float(cost_raw if cost_raw is not None else base_cost), 2)
            seed_val = int(sc_card.get("seed") or rt.get("seed") or _deterministic_seed(project_title, s_idx, t_key))
            canonical_tid = str(sc_card.get("take_id") or rt.get("take_id") or f"SC{s_idx:02d}_{t_num}")
            promoted = (
                bool(sc_card["promoted_hero"])
                if "promoted_hero" in sc_card
                else bool(rt.get("promoted_hero", False))
            )
            retry_rec = bool(sc_card.get("retry_recommended", qa_score < 85.0))
            raw_t_status = rt.get("status") or rt.get("qa_status") or ("qa_flagged" if retry_rec else None)
            t_status = _normalize_qa_status(raw_t_status, qa_score)
            takes[t_key] = {
                "take_id": t_key,
                "canonical_take_id": canonical_tid,
                "label": str(rt.get("label") or default_lbl),
                "seed": seed_val,
                "qa_score": qa_score,
                "composite_qa_score": qa_score,
                "optical_score": opt_score,
                "temporal_stability_score": opt_score,
                "prompt_adherence_score": round(float(sc_card.get("prompt_adherence_score") if sc_card.get("prompt_adherence_score") is not None else qa_score), 1),
                "reference_drift_score": round(float(sc_card.get("reference_drift_score") if sc_card.get("reference_drift_score") is not None else qa_score), 1),
                "audio_sync_rms_db": audio_rms_db,
                "audio_sync_ms": sync_ms,
                "cost_usd": cost_usd,
                "promoted_hero": promoted,
                "retry_recommended": retry_rec,
                "status": t_status,
            }

        raw_selected_take = raw_job.get("selected_take_id") or raw_job.get("hero_take") or raw_job.get("selected_take")
        hero_take = _map_take_slot(raw_selected_take)
        if hero_take is None and raw_selected_take:
            sel_upper = str(raw_selected_take).strip().upper()
            hero_take = next(
                (k for k in ("A", "B", "C") if takes[k]["canonical_take_id"].upper() == sel_upper),
                None,
            )
        if hero_take is None:
            hero_take = next((k for k in ("A", "B", "C") if takes[k]["promoted_hero"]), "A")
        takes[hero_take]["promoted_hero"] = True
        hero_info = takes[hero_take]
        selected_take_id = str(raw_selected_take or hero_info["canonical_take_id"])

        job_status = _normalize_qa_status(
            raw_job.get("status") or raw_job.get("qa_status") or rv_item.get("status"),
            hero_info["qa_score"],
        )

        handoff_in = handoffs_by_to.get(s_idx)
        handoff_out = handoffs_by_from.get(s_idx)
        end_frame_path = str(
            raw_job.get("end_frame_path")
            or raw_job.get("anchor_out")
            or (handoff_out.get("end_frame_asset_id") if handoff_out else None)
            or f"End_Frame_{s_idx:02d}.png"
        )
        anchor_in = str(
            raw_job.get("anchor_in")
            or (handoff_in.get("end_frame_asset_id") if handoff_in else None)
            or ("START_PLATE_01.svg" if s_idx == 1 else f"End_Frame_{s_idx - 1:02d}.png")
        )
        anchor_out = str(raw_job.get("anchor_out") or end_frame_path)
        lum_raw = raw_job.get("luminance_delta_pct")
        if lum_raw is None and handoff_out is not None:
            lum_raw = handoff_out.get("luminance_delta_pct")
        if lum_raw is None and handoff_in is not None:
            lum_raw = handoff_in.get("luminance_delta_pct")
        lum_delta = round(
            float(lum_raw if lum_raw is not None else (0.6 + ((s_idx * 0.45) % 2.1))),
            2,
        )
        if handoff_out is not None:
            continuity_locked = bool(handoff_out.get("continuity_locked", True))
        elif handoff_in is not None:
            continuity_locked = bool(handoff_in.get("continuity_locked", True))
        else:
            continuity_locked = True
        lock_status = str(
            raw_job.get("continuity_lock_status")
            or (
                ("FRAME_LOCKED" if continuity_locked else "DRIFT_WARNING")
                if (handoff_out is not None or handoff_in is not None)
                else ("FRAME_LOCKED" if (mode_b_enabled and s_idx > 1) else ("KEYFRAME_ROOT" if s_idx == 1 else "PARALLEL_ASSET_LOCK"))
            )
        )
        output_media = str(
            raw_job.get("output_media_path")
            or raw_job.get("output_clip_uri")
            or rv_item.get("video_path")
            or f"renders/scene_{s_idx:02d}_take_{hero_take}.mp4"
        )

        scene_jobs.append(
            {
                "scene_index": s_idx,
                "scene_title": s_title,
                "job_id": str(raw_job.get("job_id") or f"JOB-S{s_idx:02d}"),
                "status": job_status,
                "model_id": str(raw_job.get("model_id") or "gemini-omni-1.1-flash-preview"),
                "execution_mode": str(raw_job.get("execution_mode") or rv_item.get("mode") or bundle_mode),
                "start_sec": round(st_s, 2),
                "duration_sec": dur_s,
                "smpte_in": _sec_to_smpte(st_s, 24),
                "smpte_out": _sec_to_smpte(en_s, 24),
                "selected_take_id": selected_take_id,
                "hero_take": hero_take,
                "hero_qa_score": hero_info["qa_score"],
                "hero_seed": hero_info["seed"],
                "hero_cost_usd": hero_info["cost_usd"],
                "anchor_in": anchor_in,
                "anchor_out": anchor_out,
                "end_frame_path": end_frame_path,
                "luminance_delta_pct": lum_delta,
                "continuity_locked": continuity_locked,
                "continuity_lock_status": lock_status,
                "output_media_path": output_media,
                "output_clip_uri": output_media,
                "takes": takes,
            }
        )

    passed_cnt = sum(1 for j in scene_jobs if j["status"] == "qa_passed")
    flagged_cnt = len(scene_jobs) - passed_cnt
    total_cost = round(sum(float(j["hero_cost_usd"]) for j in scene_jobs), 2)
    avg_qa = round(
        sum(float(j["hero_qa_score"]) for j in scene_jobs) / max(1, len(scene_jobs)),
        1,
    )
    anchor_locks = (
        sum(1 for h in raw_handoffs if h.get("continuity_locked", True))
        if raw_handoffs
        else sum(1 for j in scene_jobs if j["scene_index"] > 1 and mode_b_enabled)
    )

    return {
        "schema": "omni.live_render_jobs.v1",
        "project_title": project_title,
        "aspect_ratio": str(aspect_val),
        "creative_regime": regime_val,
        "storytelling_mode": mode_val,
        "mode_b_enabled": mode_b_enabled,
        "execution_mode": bundle_mode,
        "fps": 24,
        "total_jobs": len(scene_jobs),
        "passed_count": passed_cnt,
        "flagged_count": flagged_cnt,
        "total_render_cost_usd": total_cost,
        "average_qa_score": avg_qa,
        "mode_b_anchor_locks": anchor_locks,
        "frame_anchor_handoffs": raw_handoffs,
        "scene_jobs": scene_jobs,
    }


def synthesize_v218_pitch_treatment_state(bible: Any, bundle: Any = None) -> Dict[str, Any]:
    """Extracts or deterministically synthesizes PM-FEAT-036 Director Pitch Treatment state."""
    project_title = str(_get_field(bible, "project_title", "Omni Production") or "Omni Production")
    logline = str(_get_field(bible, "logline", "") or "A precision-crafted cinematic production built with Gemini 2026 SSOT.")
    regime_val = str(_to_plain(_get_field(bible, "creative_regime", "REGIME 1: Photorealism")) or "REGIME 1: Photorealism")
    mode_val = str(_to_plain(_get_field(bible, "storytelling_mode", "Mode B: Continuous Narrative")) or "Mode B: Continuous Narrative")
    aspect_val = str(_to_plain(_get_field(bible, "aspect_ratio", "16:9")) or "16:9")
    runtime_sec = int(_get_field(bible, "total_runtime_seconds", 32) or 32)
    archetype = str(_get_field(bible, "domain_archetype", "commercial_showcase") or "commercial_showcase")

    telemetry = _to_plain(_get_field(bundle, "telemetry", {}) or {}) if bundle is not None else {}
    existing = (
        _get_field(bible, "master_pitch_treatment", None)
        or _get_field(bible, "pitch_treatment", None)
        or _get_field(bundle, "master_pitch_treatment", None)
        or _get_field(bundle, "pitch_treatment", None)
        or (telemetry.get("master_pitch_treatment") if isinstance(telemetry, dict) else None)
    )
    plain_existing = _to_plain(existing) if isinstance(_to_plain(existing), dict) else {}

    palette = _to_plain(_get_field(bible, "color_palette", []) or [])
    if (not isinstance(palette, list) or not palette) and isinstance(plain_existing.get("color_script_strip"), list):
        palette = [str(c) for c in plain_existing["color_script_strip"] if c]
    if not isinstance(palette, list) or not palette:
        palette = ["#0F172A", "#38BDF8", "#F59E0B", "#E2E8F0"]
    palette = [str(c) for c in palette[:8]]

    color_look = _to_plain(
        _get_field(bible, "color_look", None)
        or _get_field(bible, "master_color_look", {})
        or {}
    ) or {}
    look_name = str(
        color_look.get("look_preset")
        or color_look.get("look_name")
        or color_look.get("preset_name")
        or "Rec.709 Master Grade"
    )

    scenes = _to_plain(_get_field(bible, "scenes", []) or [])
    scene_beats: List[Dict[str, Any]] = []
    cursor_s = 0.0
    for idx, sc in enumerate(scenes):
        sc_d = sc if isinstance(sc, dict) else {}
        s_idx = int(sc_d.get("scene_index", idx + 1) or (idx + 1))
        st_s, en_s = _parse_scene_window(str(sc_d.get("timestamp_range") or ""), cursor_s)
        cursor_s = en_s
        cam = (
            sc_d.get("craft_camera")
            if isinstance(sc_d.get("craft_camera"), dict)
            else (sc_d.get("camera_spec") if isinstance(sc_d.get("camera_spec"), dict) else {})
        )
        raw_fl = cam.get("focal_length_mm")
        if raw_fl is not None and str(raw_fl).strip():
            fl_s = str(raw_fl).strip()
            lens_txt = f"{fl_s}mm" if fl_s.isdigit() else fl_s
        else:
            lens_txt = str(cam.get("lens_mm") or cam.get("focal_length") or "35mm")
        move_txt = str(
            cam.get("route")
            or cam.get("rig_type")
            or cam.get("camera_movement")
            or cam.get("movement")
            or "Controlled Dolly"
        )
        prompt_excerpt = str(
            sc_d.get("omni_prose_prompt")
            or sc_d.get("visual_action")
            or sc_d.get("narrative_beat")
            or sc_d.get("final_prompt")
            or sc_d.get("scene_prompt")
            or f"Scene {s_idx} hero cinematic composition."
        )
        scene_beats.append(
            {
                "scene_index": s_idx,
                "scene_title": str(sc_d.get("scene_title") or f"Scene {s_idx}"),
                "timestamp_range": str(sc_d.get("timestamp_range") or f"{_sec_to_smpte(st_s)} - {_sec_to_smpte(en_s)}"),
                "smpte_in": _sec_to_smpte(st_s, 24),
                "lens_movement": f"{lens_txt} · {move_txt}",
                "beat_summary": prompt_excerpt[:180],
            }
        )

    bgm = _to_plain(_get_field(bible, "master_bgm", {}) or {}) or {}
    bgm_title = str(bgm.get("track_title") or "Master Sonic Blueprint")
    bgm_bpm = int(bgm.get("tempo_bpm") or 108)
    bgm_key = str(bgm.get("key_signature") or "D Minor")
    bgm_genre = str(bgm.get("genre_style") or "Modern Cinematic Hybrid")
    raw_stems = bgm.get("stems")
    if isinstance(raw_stems, dict):
        bgm_stems = [f"{k}: {v}" if v else str(k) for k, v in raw_stems.items()]
    elif isinstance(raw_stems, list):
        bgm_stems = [str(s) for s in raw_stems]
    else:
        bgm_stems = ["Strings", "Sub Bass", "Percussion", "Foley Bed"]
    lyria_prompt = str(bgm.get("lyria_prompt") or f"{bgm_genre} at {bgm_bpm} BPM in {bgm_key} with tactile diegetic dynamics.")

    econ = _to_plain(
        _get_field(bible, "master_render_economics_spec", None)
        or _get_field(bible, "render_economics_manifest", None)
        or _get_field(bible, "render_economics", {})
        or {}
    ) or {}
    aicp = _to_plain(
        _get_field(bible, "master_aicp_bid", None)
        or _get_field(bible, "aicp_bid", None)
        or _get_field(bible, "master_aicp_budget", None)
        or _get_field(bible, "aicp_budget", {})
        or {}
    ) or {}
    guard = econ.get("guardrail") if isinstance(econ.get("guardrail"), dict) else {}
    scene_ests = econ.get("scene_estimates") if isinstance(econ.get("scene_estimates"), list) else []
    est_sum = sum(float(s.get("estimated_scene_usd") or 0.0) for s in scene_ests if isinstance(s, dict))
    est_ai_usd = round(
        float(
            guard.get("estimated_total_usd")
            or econ.get("estimated_total_compute_usd")
            or econ.get("estimated_spend_usd")
            or (est_sum if est_sum > 0 else 0.0)
            or (len(scene_beats) * 1.35 + 0.45)
        ),
        2,
    )
    top_sheet = aicp.get("top_sheet") if isinstance(aicp.get("top_sheet"), dict) else {}
    aicp_base_usd = round(
        float(
            econ.get("aicp_traditional_baseline_usd")
            or aicp.get("grand_total_usd")
            or aicp.get("grand_total")
            or top_sheet.get("grand_total_bid_usd")
            or top_sheet.get("grand_total_bid")
            or top_sheet.get("grand_total")
            or aicp.get("total_bid_usd")
            or 48500.0
        ),
        2,
    )
    savings_pct = round(max(0.0, (1.0 - (est_ai_usd / max(1.0, aicp_base_usd))) * 100.0), 2)

    def _normalize_delta_item(d: Any) -> Optional[Dict[str, Any]]:
        if not isinstance(d, dict):
            return None
        field_val = str(d.get("field_path") or d.get("field") or "")
        prev_raw = d.get("previous_value") if d.get("previous_value") is not None else d.get("baseline")
        curr_raw = d.get("current_value") if d.get("current_value") is not None else d.get("current")
        imp_raw = d.get("impact_severity") or d.get("impact") or "SYNCED"
        prev_val = str(prev_raw if prev_raw is not None else "")
        curr_val = str(curr_raw if curr_raw is not None else "")
        imp_val = str(imp_raw)
        return {
            "field_path": field_val,
            "previous_value": prev_val,
            "current_value": curr_val,
            "impact_severity": imp_val,
            "field": field_val,
            "baseline": prev_val,
            "current": curr_val,
            "impact": imp_val,
            "section": str(d.get("section") or "Bible"),
            "change_type": str(d.get("change_type") or "modified"),
            "department_owner": str(d.get("department_owner") or "Direction"),
        }

    raw_diff = plain_existing.get("revision_diff")
    revision_diff: Dict[str, Any]
    if isinstance(raw_diff, dict):
        raw_deltas = raw_diff.get("deltas") or raw_diff.get("changes") or []
        norm_deltas = [
            nd for nd in (_normalize_delta_item(x) for x in (_to_plain(raw_deltas) if isinstance(raw_deltas, list) else [])) if nd is not None
        ]
        revision_diff = {
            "baseline_version": str(raw_diff.get("baseline_title") or raw_diff.get("baseline_version") or raw_diff.get("from_version") or "v1.0-bible-ssot"),
            "current_version": str(raw_diff.get("target_title") or raw_diff.get("current_version") or raw_diff.get("to_version") or "v2.18.0-treatment"),
            "status": str(raw_diff.get("status") or (f"{len(norm_deltas)} REVISION DELTA(S)" if norm_deltas else "SYNCED · 0 UNRECONCILED DELTAS")),
            "deltas": norm_deltas,
        }
    elif isinstance(raw_diff, list):
        norm_deltas = [nd for nd in (_normalize_delta_item(x) for x in _to_plain(raw_diff)) if nd is not None]
        revision_diff = {
            "baseline_version": "v1.0-bible-ssot",
            "current_version": "v2.18.0-treatment",
            "status": f"{len(norm_deltas)} REVISION DELTA(S)" if norm_deltas else "SYNCED · 0 UNRECONCILED DELTAS",
            "deltas": norm_deltas,
        }
    else:
        revision_diff = {
            "baseline_version": "v1.0-bible-ssot",
            "current_version": "v2.18.0-treatment",
            "status": "BASELINE SYNCED · 0 UNRECONCILED DELTAS",
            "deltas": [
                {
                    "field_path": "total_runtime_seconds",
                    "previous_value": f"{runtime_sec}s @ 24fps",
                    "current_value": f"{runtime_sec}s @ 24fps",
                    "impact_severity": "LOCKED",
                    "field": "total_runtime_seconds",
                    "baseline": f"{runtime_sec}s @ 24fps",
                    "current": f"{runtime_sec}s @ 24fps",
                    "impact": "LOCKED",
                },
                {
                    "field_path": "color_palette",
                    "previous_value": f"{len(palette)} swatches",
                    "current_value": ", ".join(palette[:4]),
                    "impact_severity": "LOCKED",
                    "field": "color_palette",
                    "baseline": f"{len(palette)} swatches",
                    "current": ", ".join(palette[:4]),
                    "impact": "LOCKED",
                },
                {
                    "field_path": "scene_count",
                    "previous_value": f"{len(scene_beats)} scenes",
                    "current_value": f"{len(scene_beats)} scenes",
                    "impact_severity": "LOCKED",
                    "field": "scene_count",
                    "baseline": f"{len(scene_beats)} scenes",
                    "current": f"{len(scene_beats)} scenes",
                    "impact": "LOCKED",
                },
                {
                    "field_path": "model_matrix",
                    "previous_value": "2026 Matrix (argon/3.8-flash/3-pro-image/omni-1.1)",
                    "current_value": "2026 Matrix Verified",
                    "impact_severity": "COMPLIANT",
                    "field": "model_matrix",
                    "baseline": "2026 Matrix (argon/3.8-flash/3-pro-image/omni-1.1)",
                    "current": "2026 Matrix Verified",
                    "impact": "COMPLIANT",
                },
            ],
        }

    slides = [
        {
            "id": "cover",
            "index": 1,
            "label": "01 · Cover & Mandate",
            "title": project_title,
            "subtitle": f"{regime_val} · {mode_val} · {aspect_val} · {runtime_sec}s",
            "archetype": archetype,
            "logline": logline,
        },
        {
            "id": "palette",
            "index": 2,
            "label": "02 · Color Script",
            "title": f"Color Script & Look Science ({look_name})",
            "palette": palette,
            "look_name": look_name,
        },
        {
            "id": "beats",
            "index": 3,
            "label": "03 · Scene Beats",
            "title": f"Director's Beat Sheet ({len(scene_beats)} Scenes)",
            "scenes": scene_beats,
        },
        {
            "id": "bgm",
            "index": 4,
            "label": "04 · BGM Sonic Arc",
            "title": bgm_title,
            "tempo_bpm": bgm_bpm,
            "key_signature": bgm_key,
            "genre_style": bgm_genre,
            "stems": [str(s) for s in bgm_stems[:6]],
            "lyria_prompt": lyria_prompt,
        },
        {
            "id": "roi",
            "index": 5,
            "label": "05 · AI vs AICP ROI",
            "title": "Production Economics & Executive ROI",
            "estimated_ai_usd": est_ai_usd,
            "aicp_baseline_usd": aicp_base_usd,
            "savings_pct": savings_pct,
            "turnaround_delta": "45s Pre-Viz vs 14 Days Traditional",
        },
    ]

    return {
        "schema": "omni.pitch_treatment.v1",
        "project_title": project_title,
        "logline": logline,
        "creative_regime": regime_val,
        "storytelling_mode": mode_val,
        "aspect_ratio": aspect_val,
        "runtime_sec": runtime_sec,
        "archetype": archetype,
        "palette": palette,
        "look_name": look_name,
        "scene_beats": scene_beats,
        "bgm": {
            "track_title": bgm_title,
            "tempo_bpm": bgm_bpm,
            "key_signature": bgm_key,
            "genre_style": bgm_genre,
            "stems": [str(s) for s in bgm_stems[:6]],
            "lyria_prompt": lyria_prompt,
        },
        "roi": {
            "estimated_ai_usd": est_ai_usd,
            "aicp_baseline_usd": aicp_base_usd,
            "savings_pct": savings_pct,
        },
        "revision_diff": revision_diff,
        "slides": slides,
    }


def build_v218_hud_bundle(bible: Any, bundle: Any = None) -> Tuple[str, str, str]:
    """Builds Dark-Room Cinema v2.18.0 HUD bundle returning (css_str, modals_html, js_str)."""
    rj_state = synthesize_v218_render_jobs_state(bible, bundle)
    pt_state = synthesize_v218_pitch_treatment_state(bible, bundle)

    rj_json = _escape_json_for_script(rj_state)
    pt_json = _escape_json_for_script(pt_state)

    # Pre-render Render Jobs table rows
    rj_rows_html: List[str] = []
    for job in rj_state.get("scene_jobs") or []:
        s_idx = int(job.get("scene_index", 1))
        st = str(job.get("status", "qa_passed"))
        st_cls = "v218-badge-pass" if st == "qa_passed" else "v218-badge-warn"
        hero_take = str(job.get("hero_take", "A")).upper()
        takes = job.get("takes") or {}

        take_cells: List[str] = []
        for t_key in ("A", "B", "C"):
            tk = takes.get(t_key) or {}
            t_score = float(tk.get("qa_score", 92.0))
            t_seed = int(tk.get("seed", 1001))
            t_cost = float(tk.get("cost_usd", 1.25))
            is_hero = hero_take == t_key
            btn_cls = "v218-take-btn active" if is_hero else "v218-take-btn"
            pressed = "true" if is_hero else "false"
            take_cells.append(
                f'<td>'
                f'<div class="v218-take-cell">'
                f'<span class="v218-take-score">{t_score:.1f} QA · #{t_seed}</span>'
                f'<span class="v218-sub">${t_cost:.2f} · {int(tk.get("audio_sync_ms", 0)):+d}ms</span>'
                f'<button type="button" class="{btn_cls}" data-scene-idx="{s_idx}" data-take="{t_key}" '
                f'aria-pressed="{pressed}" onclick="promoteRenderHeroTake({s_idx}, \'{t_key}\')">'
                f'{"★ Hero " + t_key if is_hero else "Promote " + t_key}'
                f'</button>'
                f'</div>'
                f'</td>'
            )

        rj_rows_html.append(
            f'<tr data-rj-scene="{s_idx}">'
            f'<td><strong>S{s_idx:02d}</strong> · {html_escape(str(job.get("scene_title", "")))}<br>'
            f'<code class="v218-code">{html_escape(str(job.get("job_id", "")))}</code> · '
            f'<span class="v218-sub">{html_escape(str(job.get("smpte_in", "")))}</span></td>'
            f'<td><span id="rj-status-pill-{s_idx}" class="v218-badge {st_cls}">{html_escape(st)}</span><br>'
            f'<span class="v218-sub">Hero: <strong id="rj-hero-badge-{s_idx}">Take {hero_take}</strong></span></td>'
            + "".join(take_cells)
            + f'<td><code class="v218-code">{html_escape(str(job.get("anchor_out", "")))}</code><br>'
            f'<span class="v218-sub">ΔY {float(job.get("luminance_delta_pct", 1.0)):.2f}% · {html_escape(str(job.get("continuity_lock_status", "")))}</span></td>'
            f'</tr>'
        )
    rj_tbody_html = "\n".join(rj_rows_html)

    # Pre-render Pitch Treatment slide pills & initial diff rows
    slide_pills_html: List[str] = []
    for sl in pt_state.get("slides") or []:
        sl_idx = int(sl.get("index", 1)) - 1
        is_first = sl_idx == 0
        slide_pills_html.append(
            f'<button type="button" class="v218-slide-pill{" active" if is_first else ""}" '
            f'data-slide-idx="{sl_idx}" aria-pressed="{"true" if is_first else "false"}" '
            f'onclick="setTreatmentSlide({sl_idx})">{html_escape(str(sl.get("label", "")))}</button>'
        )

    diff_obj = pt_state.get("revision_diff") or {}
    diff_rows_html: List[str] = []
    for d in diff_obj.get("deltas") or []:
        if not isinstance(d, dict):
            continue
        field_val = str(d.get("field_path") or d.get("field") or "")
        prev_raw = d.get("previous_value") if d.get("previous_value") is not None else d.get("baseline")
        curr_raw = d.get("current_value") if d.get("current_value") is not None else d.get("current")
        imp = str(d.get("impact_severity") or d.get("impact") or "SYNCED")
        imp_cls = "v218-badge-pass" if imp.upper() in {"LOCKED", "COMPLIANT", "SYNCED", "PASS", "LOW"} else "v218-badge-warn"
        diff_rows_html.append(
            f'<tr>'
            f'<td><code class="v218-code">{html_escape(field_val)}</code></td>'
            f'<td><span class="v218-sub">{html_escape(str(prev_raw if prev_raw is not None else ""))}</span></td>'
            f'<td><span class="v218-sub">{html_escape(str(curr_raw if curr_raw is not None else ""))}</span></td>'
            f'<td><span class="v218-badge {imp_cls}">{html_escape(imp)}</span></td>'
            f'</tr>'
        )
    diff_tbody_html = "\n".join(diff_rows_html)

    css_str = """
    /* v2.18.0 Live-Render Jobs & Director Pitch Treatment HUDs */
    #modal-render-jobs,
    #modal-pitch-treatment {
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(7, 8, 11, 0.92);
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
      z-index: 10065;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }
    .v218-modal-card {
      background: #0E1017;
      color: #F8FAFC;
      border: 1px solid #38BDF8;
      border-radius: 10px;
      width: 100%;
      max-width: 1120px;
      max-height: 92vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      box-shadow: 0 24px 60px rgba(0, 0, 0, 0.9);
    }
    .v218-modal-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      padding: 14px 20px;
      background: #141722;
      border-bottom: 1px solid #334155;
    }
    .v218-modal-title {
      margin: 0;
      font-family: 'Space Grotesk', sans-serif;
      font-size: 16px;
      font-weight: 700;
      color: #F8FAFC;
    }
    .v218-modal-sub {
      display: block;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      color: #38BDF8;
      margin-top: 2px;
    }
    .v218-close-btn {
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
    .v218-close-btn:hover,
    .v218-close-btn:focus-visible {
      background: #DC2626;
      outline: 2px solid #FACC15;
      outline-offset: 2px;
    }
    .v218-modal-body {
      padding: 18px 20px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }
    .v218-kpi-row {
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
    .v218-badge-group {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }
    .v218-badge {
      display: inline-block;
      padding: 3px 8px;
      border-radius: 4px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      font-weight: 700;
    }
    .v218-badge-pass {
      background: rgba(16, 185, 129, 0.18);
      color: #34D399;
      border: 1px solid #10B981;
    }
    .v218-badge-warn {
      background: rgba(245, 158, 11, 0.18);
      color: #FBBF24;
      border: 1px solid #F59E0B;
    }
    .v218-badge-info {
      background: rgba(56, 189, 248, 0.16);
      color: #38BDF8;
      border: 1px solid #38BDF8;
    }
    .v218-code {
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      color: #FDE047;
    }
    .v218-sub {
      font-size: 11px;
      color: #CBD5E1;
    }
    .v218-svg-frame {
      background: #05070B;
      border: 1px solid #334155;
      border-radius: 8px;
      padding: 10px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .v218-svg-frame svg {
      width: 100%;
      height: auto;
      display: block;
      border-radius: 4px;
    }
    .v218-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
    }
    .v218-table th,
    .v218-table td {
      border: 1px solid #334155;
      padding: 8px 10px;
      text-align: left;
      vertical-align: top;
    }
    .v218-table th {
      background: #1E293B;
      color: #F8FAFC;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
    }
    .v218-take-cell {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    .v218-take-score {
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      font-weight: 700;
      color: #F8FAFC;
    }
    .v218-take-btn,
    .v218-slide-pill,
    .v218-nav-btn {
      background: #07080B;
      color: #CBD5E1;
      border: 1px solid #475569;
      border-radius: 5px;
      padding: 5px 10px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      font-weight: 700;
      cursor: pointer;
    }
    .v218-take-btn.active,
    .v218-take-btn[aria-pressed="true"],
    .v218-slide-pill.active,
    .v218-slide-pill[aria-pressed="true"] {
      background: #0369A1;
      color: #FFFFFF;
      border-color: #38BDF8;
    }
    .v218-take-btn:hover,
    .v218-slide-pill:hover,
    .v218-nav-btn:hover {
      border-color: #38BDF8;
      color: #F8FAFC;
    }
    .v218-take-btn:focus-visible,
    .v218-slide-pill:focus-visible,
    .v218-nav-btn:focus-visible,
    .v218-dl-btn:focus-visible {
      outline: 2px solid #FACC15;
      outline-offset: 2px;
    }
    .v218-carousel-bar {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
      justify-content: space-between;
      background: #141722;
      border: 1px solid #334155;
      border-radius: 6px;
      padding: 10px 12px;
    }
    .v218-slide-pills {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }
    .v218-carousel-stage {
      background: #0B1120;
      border: 1px solid #38BDF8;
      border-radius: 8px;
      padding: 18px;
      min-height: 220px;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .v218-swatch-strip {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }
    .v218-swatch-chip {
      display: flex;
      align-items: center;
      gap: 8px;
      background: #141722;
      border: 1px solid #334155;
      border-radius: 6px;
      padding: 6px 10px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
    }
    .v218-swatch-color {
      width: 22px;
      height: 22px;
      border-radius: 4px;
      border: 1px solid rgba(255, 255, 255, 0.25);
    }
    .v218-beat-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 10px;
    }
    .v218-beat-card {
      background: #141722;
      border: 1px solid #334155;
      border-radius: 6px;
      padding: 10px;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    .v218-diff-panel {
      background: #141722;
      border: 1px solid #334155;
      border-radius: 8px;
      padding: 12px 14px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .v218-actions-row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      justify-content: flex-end;
    }
    .v218-dl-btn {
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
    .v218-dl-btn:hover {
      background: #0284C7;
    }
    @media (prefers-reduced-motion: reduce) {
      #modal-render-jobs *,
      #modal-pitch-treatment * {
        transition: none !important;
      }
    }
    """

    modals_html = f"""
<!-- v2.18.0 PM-FEAT-035: Live-Render Jobs, Take A/B/C QA & Frame-Anchor Handoff HUD -->
<div id="modal-render-jobs" role="dialog" aria-modal="true" aria-labelledby="modal-render-jobs-title" tabindex="-1">
  <div class="v218-modal-card">
    <div class="v218-modal-header">
      <div>
        <h2 id="modal-render-jobs-title" class="v218-modal-title">Live-Render Jobs, Take A/B/C QA &amp; Frame-Anchor Handoff</h2>
        <span class="v218-modal-sub">Per-Scene Render QA Scorecard, Promote Hero Take &amp; Mode B End_Frame_0n Locks [`]</span>
      </div>
      <button type="button" class="v218-close-btn" id="btn-render-jobs-close" onclick="toggleRenderJobsHUD(false)" aria-label="Close Live-Render Jobs and QA HUD">Close [Esc]</button>
    </div>
    <div class="v218-modal-body">
      <div class="v218-kpi-row">
        <div class="v218-badge-group">
          <span class="v218-badge v218-badge-info" id="rj-kpi-jobs">{int(rj_state["total_jobs"])} RENDER JOBS</span>
          <span class="v218-badge v218-badge-pass" id="rj-kpi-passed">{int(rj_state["passed_count"])} QA PASSED</span>
          <span class="v218-badge {'v218-badge-pass' if rj_state['flagged_count'] == 0 else 'v218-badge-warn'}" id="rj-kpi-flagged">{int(rj_state["flagged_count"])} QA FLAGGED</span>
          <span class="v218-badge v218-badge-info" id="rj-kpi-avg">AVG QA {float(rj_state["average_qa_score"]):.1f}</span>
          <span class="v218-badge v218-badge-pass" id="rj-kpi-cost">HERO COST ${float(rj_state["total_render_cost_usd"]):.2f}</span>
        </div>
        <span class="v218-sub">Mode: <strong class="v218-code">{html_escape(str(rj_state["storytelling_mode"]))}</strong> · {html_escape(str(rj_state["execution_mode"]).upper())}</span>
      </div>

      <div class="v218-svg-frame">
        <div class="v218-sub"><strong>Mode B Frame-Anchor Handoff Continuity</strong> · <span id="rj-anchor-telemetry" aria-live="polite">Inspecting End_Frame_0n.png continuity chain &amp; luminance delta (ΔY).</span></div>
        <svg id="render-anchor-svg" viewBox="0 0 880 180" role="img" aria-label="Mode B Frame-Anchor Handoff Continuity SVG showing End_Frame locks and luminance delta"></svg>
      </div>

      <table class="v218-table" aria-label="Take A B C QA Scorecard and Hero Take Promotion">
        <thead>
          <tr>
            <th>Scene / Job</th>
            <th>QA Status &amp; Hero</th>
            <th>Take A (Primary)</th>
            <th>Take B (Alt)</th>
            <th>Take C (Hold)</th>
            <th>Frame-Anchor Out</th>
          </tr>
        </thead>
        <tbody id="rj-scorecard-tbody">
          {rj_tbody_html}
        </tbody>
      </table>

      <div class="v218-actions-row">
        <button type="button" class="v218-dl-btn" id="btn-dl-render-manifest" onclick="downloadRenderJobManifestJSON()">⤓ render_job_manifest.json</button>
        <button type="button" class="v218-dl-btn" id="btn-dl-take-qa-csv" onclick="downloadTakeQaScorecardCSV()">⤓ take_qa_scorecard.csv</button>
        <button type="button" class="v218-dl-btn" id="btn-dl-rough-cut-sh" onclick="downloadRoughCutAssemblySH()">⤓ rough_cut_assembly.sh</button>
      </div>
    </div>
  </div>
</div>

<!-- v2.18.0 PM-FEAT-036: Director Pitch Treatment Carousel, Revision Diff & Lookbook HUD -->
<div id="modal-pitch-treatment" role="dialog" aria-modal="true" aria-labelledby="modal-pitch-treatment-title" tabindex="-1">
  <div class="v218-modal-card">
    <div class="v218-modal-header">
      <div>
        <h2 id="modal-pitch-treatment-title" class="v218-modal-title">Director&apos;s Pitch Treatment &amp; Lookbook Studio</h2>
        <span class="v218-modal-sub">Interactive Treatment Carousel, Bible Revision Diff &amp; Client Lookbook Export [-]</span>
      </div>
      <button type="button" class="v218-close-btn" id="btn-pitch-treatment-close" onclick="togglePitchTreatmentHUD(false)" aria-label="Close Director Pitch Treatment HUD">Close [Esc]</button>
    </div>
    <div class="v218-modal-body">
      <div class="v218-carousel-bar">
        <div class="v218-slide-pills" id="pt-slide-pills" role="group" aria-label="Pitch Treatment Slides">
          {"".join(slide_pills_html)}
        </div>
        <div class="v218-badge-group">
          <button type="button" class="v218-nav-btn" id="btn-treatment-prev" onclick="stepTreatmentSlide(-1)" aria-label="Previous Treatment Slide">◀ Prev</button>
          <span class="v218-code" id="pt-slide-counter" aria-live="polite">Slide 1 / {len(pt_state["slides"])}</span>
          <button type="button" class="v218-nav-btn" id="btn-treatment-next" onclick="stepTreatmentSlide(1)" aria-label="Next Treatment Slide">Next ▶</button>
        </div>
      </div>

      <div id="pt-carousel-stage" class="v218-carousel-stage" aria-live="polite"></div>

      <div class="v218-diff-panel" aria-label="Bible Revision Diff Summary">
        <div class="v218-kpi-row" style="padding: 8px 10px;">
          <div>
            <strong>Bible Revision Diff Summary</strong>
            <span class="v218-sub"> · <code class="v218-code">{html_escape(str(diff_obj.get("baseline_version", "v1.0-bible-ssot")))}</code> → <code class="v218-code">{html_escape(str(diff_obj.get("current_version", "v2.18.0-treatment")))}</code></span>
          </div>
          <span class="v218-badge v218-badge-pass">{html_escape(str(diff_obj.get("status", "SYNCED")))}</span>
        </div>
        <table class="v218-table" aria-label="Bible Revision Comparison">
          <thead>
            <tr>
              <th>Contract Field</th>
              <th>Baseline SSOT</th>
              <th>Current Treatment</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody id="pt-revision-diff-tbody">
            {diff_tbody_html}
          </tbody>
        </table>
      </div>

      <div class="v218-actions-row">
        <button type="button" class="v218-dl-btn" id="btn-dl-treatment-lookbook" onclick="downloadTreatmentLookbookHTML()">⤓ director_treatment_lookbook.html</button>
        <button type="button" class="v218-dl-btn" id="btn-dl-treatment-brief" onclick="downloadTreatmentBriefMD()">⤓ director_treatment_brief.md</button>
        <button type="button" class="v218-dl-btn" id="btn-dl-treatment-manifest" onclick="downloadPitchTreatmentManifestJSON()">⤓ pitch_treatment_manifest.json</button>
      </div>
    </div>
  </div>
</div>
"""

    js_template = """
    // v2.18.0 Live-Render Jobs (PM-FEAT-035) & Director Pitch Treatment (PM-FEAT-036)
    const V218_RENDER_JOBS_STATE = __RJ_JSON__;
    const V218_TREATMENT_STATE = __PT_JSON__;
    window.V218_RENDER_JOBS_STATE = V218_RENDER_JOBS_STATE;
    window.V218_TREATMENT_STATE = V218_TREATMENT_STATE;

    let isRenderJobsHUDOpen = false;
    window.isRenderJobsHUDOpen = false;
    let lastRenderJobsOpener = null;

    let isPitchTreatmentHUDOpen = false;
    window.isPitchTreatmentHUDOpen = false;
    let lastPitchTreatmentOpener = null;

    let _ptSlideIndex = 0;
    let _v218Initialized = false;

    if (typeof V216_HUD_COMMANDS !== 'undefined' && Array.isArray(V216_HUD_COMMANDS)) {
      if (!V216_HUD_COMMANDS.some((c) => c.id === 'renderjobs')) {
        V216_HUD_COMMANDS.push({ id: 'renderjobs', name: 'Live-Render Jobs & Take QA', dept: 'Prep', key: '`', fn: 'toggleRenderJobsHUD' });
      }
      if (!V216_HUD_COMMANDS.some((c) => c.id === 'treatment')) {
        V216_HUD_COMMANDS.push({ id: 'treatment', name: 'Director Pitch Treatment & Lookbook', dept: 'Delivery', key: '-', fn: 'togglePitchTreatmentHUD' });
      }
    }

    function _v218ShowToast(msg) {
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

    function _v218DownloadBlob(content, mime, filename, toastMsg) {
      const blob = new Blob([content], { type: mime });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      _v218ShowToast(toastMsg);
    }

    function _v218SvgEl(tag, attrs) {
      const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
      Object.keys(attrs || {}).forEach((k) => el.setAttribute(k, String(attrs[k])));
      return el;
    }

    function _v218TrapFocus(modal, onEscape) {
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

    function renderFrameAnchorSvg() {
      const svg = document.getElementById('render-anchor-svg');
      if (!svg) return;
      while (svg.firstChild) svg.removeChild(svg.firstChild);

      const jobs = V218_RENDER_JOBS_STATE.scene_jobs || [];
      const W = 880;
      const H = 180;
      svg.appendChild(_v218SvgEl('rect', { x: 0, y: 0, width: W, height: H, fill: '#05070B' }));

      if (!jobs.length) return;
      const pad = 16;
      const gap = 26;
      const cardW = Math.max(105, Math.min(180, Math.floor((W - pad * 2 - gap * (jobs.length - 1)) / jobs.length)));
      const cardH = 112;
      const startY = 34;

      jobs.forEach((job, idx) => {
        const x = pad + idx * (cardW + gap);
        const isPassed = job.status === 'qa_passed';
        const strokeCol = isPassed ? '#34D399' : '#FBBF24';

        const g = _v218SvgEl('g', {
          tabindex: '0',
          role: 'button',
          style: 'cursor:pointer;',
          'aria-label': 'Scene ' + String(job.scene_index) + ' Hero Take ' + String(job.hero_take) + ' Anchor ' + String(job.anchor_out)
        });
        g.appendChild(_v218SvgEl('rect', {
          x: x, y: startY, width: cardW, height: cardH, rx: 6,
          fill: '#0F172A', stroke: strokeCol, 'stroke-width': 1.5
        }));

        const t1 = _v218SvgEl('text', { x: x + 8, y: startY + 20, fill: '#F8FAFC', 'font-family': 'Space Grotesk, sans-serif', 'font-size': 12, 'font-weight': 700 });
        t1.textContent = 'S' + String(job.scene_index).padStart(2, '0') + ' · Take ' + String(job.hero_take || 'A');
        g.appendChild(t1);

        const t2 = _v218SvgEl('text', { x: x + 8, y: startY + 38, fill: strokeCol, 'font-family': 'JetBrains Mono, monospace', 'font-size': 10, 'font-weight': 700 });
        t2.textContent = String(job.status || 'qa_passed') + ' (' + Number(job.hero_qa_score || 95).toFixed(1) + ')';
        g.appendChild(t2);

        const t3 = _v218SvgEl('text', { x: x + 8, y: startY + 58, fill: '#38BDF8', 'font-family': 'JetBrains Mono, monospace', 'font-size': 9.5 });
        t3.textContent = 'IN: ' + String(job.anchor_in || '').slice(0, 16);
        g.appendChild(t3);

        const t4 = _v218SvgEl('text', { x: x + 8, y: startY + 75, fill: '#FDE047', 'font-family': 'JetBrains Mono, monospace', 'font-size': 9.5 });
        t4.textContent = 'OUT: ' + String(job.anchor_out || '').slice(0, 15);
        g.appendChild(t4);

        const t5 = _v218SvgEl('text', { x: x + 8, y: startY + 95, fill: '#CBD5E1', 'font-family': 'JetBrains Mono, monospace', 'font-size': 9.5 });
        t5.textContent = 'ΔY ' + Number(job.luminance_delta_pct || 1.0).toFixed(2) + '%';
        g.appendChild(t5);

        const inspectAnchor = () => {
          const tel = document.getElementById('rj-anchor-telemetry');
          if (tel) {
            tel.textContent = 'S' + String(job.scene_index).padStart(2, '0') + ' (' + String(job.job_id) + '): ' + String(job.anchor_in) + ' → ' + String(job.anchor_out) + ' · ΔY=' + Number(job.luminance_delta_pct || 1.0).toFixed(2) + '% · ' + String(job.continuity_lock_status);
          }
        };
        g.addEventListener('click', inspectAnchor);
        g.addEventListener('keydown', (e) => {
          if (e.key === 'Enter' || e.code === 'Space') {
            e.preventDefault();
            inspectAnchor();
          }
        });
        svg.appendChild(g);

        if (idx < jobs.length - 1) {
          const ax1 = x + cardW + 2;
          const ax2 = x + cardW + gap - 4;
          const ay = startY + cardH / 2;
          const isModeB = Boolean(V218_RENDER_JOBS_STATE.mode_b_enabled);
          svg.appendChild(_v218SvgEl('line', {
            x1: ax1, y1: ay, x2: ax2, y2: ay,
            stroke: isModeB ? '#38BDF8' : '#64748B',
            'stroke-width': 2,
            'stroke-dasharray': isModeB ? '' : '4,3'
          }));
          const lockLbl = _v218SvgEl('text', {
            x: (ax1 + ax2) / 2, y: ay - 8,
            fill: isModeB ? '#38BDF8' : '#94A3B8',
            'font-family': 'JetBrains Mono, monospace',
            'font-size': 9,
            'text-anchor': 'middle'
          });
          lockLbl.textContent = isModeB ? 'LOCK' : 'PAR';
          svg.appendChild(lockLbl);
        }
      });

      const hdr = _v218SvgEl('text', { x: 16, y: 18, fill: '#94A3B8', 'font-family': 'JetBrains Mono, monospace', 'font-size': 10 });
      hdr.textContent = (V218_RENDER_JOBS_STATE.mode_b_enabled ? 'MODE B SEQUENTIAL FRAME-ANCHOR CHAIN' : 'MODE A PARALLEL ASSET LOCKS') + ' · Click any scene node to inspect handoff telemetry';
      svg.appendChild(hdr);
    }

    window.promoteRenderHeroTake = function(sceneIndex, takeKey) {
      const jobs = V218_RENDER_JOBS_STATE.scene_jobs || [];
      const job = jobs.find((j) => Number(j.scene_index) === Number(sceneIndex));
      if (!job || !job.takes || !job.takes[takeKey]) return;

      const tk = job.takes[takeKey];
      job.hero_take = takeKey;
      job.selected_take_id = tk.canonical_take_id || takeKey;
      job.hero_qa_score = Number(tk.qa_score || 92.0);
      job.hero_seed = Number(tk.seed || 1001);
      job.hero_cost_usd = Number(tk.cost_usd || 1.25);
      job.status = String(tk.status || (job.hero_qa_score >= 90 ? 'qa_passed' : 'qa_flagged'));
      job.output_clip_uri = 'renders/scene_' + String(sceneIndex).padStart(2, '0') + '_take_' + takeKey + '.mp4';
      job.output_media_path = job.output_clip_uri;

      // Update row controls & badges
      document.querySelectorAll('button.v218-take-btn[data-scene-idx="' + sceneIndex + '"]').forEach((btn) => {
        const isHero = btn.getAttribute('data-take') === takeKey;
        btn.classList.toggle('active', isHero);
        btn.setAttribute('aria-pressed', isHero ? 'true' : 'false');
        btn.textContent = isHero ? ('★ Hero ' + takeKey) : ('Promote ' + btn.getAttribute('data-take'));
      });

      const statusPill = document.getElementById('rj-status-pill-' + sceneIndex);
      if (statusPill) {
        statusPill.textContent = job.status;
        statusPill.className = 'v218-badge ' + (job.status === 'qa_passed' ? 'v218-badge-pass' : 'v218-badge-warn');
      }
      const heroBadge = document.getElementById('rj-hero-badge-' + sceneIndex);
      if (heroBadge) heroBadge.textContent = 'Take ' + takeKey;

      // Recalculate summary KPIs
      const passedCount = jobs.filter((j) => j.status === 'qa_passed').length;
      const flaggedCount = jobs.length - passedCount;
      const totalCost = jobs.reduce((acc, j) => acc + Number(j.hero_cost_usd || 0), 0);
      const avgQa = jobs.length ? (jobs.reduce((acc, j) => acc + Number(j.hero_qa_score || 0), 0) / jobs.length) : 0;

      V218_RENDER_JOBS_STATE.passed_count = passedCount;
      V218_RENDER_JOBS_STATE.flagged_count = flaggedCount;
      V218_RENDER_JOBS_STATE.total_render_cost_usd = Math.round(totalCost * 100) / 100;
      V218_RENDER_JOBS_STATE.average_qa_score = Math.round(avgQa * 10) / 10;

      const elPass = document.getElementById('rj-kpi-passed');
      const elFlag = document.getElementById('rj-kpi-flagged');
      const elAvg = document.getElementById('rj-kpi-avg');
      const elCost = document.getElementById('rj-kpi-cost');
      if (elPass) elPass.textContent = passedCount + ' QA PASSED';
      if (elFlag) {
        elFlag.textContent = flaggedCount + ' QA FLAGGED';
        elFlag.className = 'v218-badge ' + (flaggedCount === 0 ? 'v218-badge-pass' : 'v218-badge-warn');
      }
      if (elAvg) elAvg.textContent = 'AVG QA ' + avgQa.toFixed(1);
      if (elCost) elCost.textContent = 'HERO COST $' + totalCost.toFixed(2);

      renderFrameAnchorSvg();
      _v218ShowToast('★ Scene ' + String(sceneIndex).padStart(2, '0') + ' Hero Take promoted to Take ' + takeKey + ' (' + job.status + ')');
    };

    function renderPitchTreatmentSlide() {
      const stage = document.getElementById('pt-carousel-stage');
      const counter = document.getElementById('pt-slide-counter');
      const slides = V218_TREATMENT_STATE.slides || [];
      if (!stage || !slides.length) return;
      if (_ptSlideIndex < 0) _ptSlideIndex = slides.length - 1;
      if (_ptSlideIndex >= slides.length) _ptSlideIndex = 0;

      const sl = slides[_ptSlideIndex];
      if (counter) counter.textContent = 'Slide ' + (_ptSlideIndex + 1) + ' / ' + slides.length;
      document.querySelectorAll('#pt-slide-pills .v218-slide-pill').forEach((btn, idx) => {
        const active = idx === _ptSlideIndex;
        btn.classList.toggle('active', active);
        btn.setAttribute('aria-pressed', active ? 'true' : 'false');
      });

      while (stage.firstChild) stage.removeChild(stage.firstChild);

      const h3 = document.createElement('h3');
      h3.style.margin = '0';
      h3.style.fontFamily = "'Space Grotesk', sans-serif";
      h3.style.fontSize = '18px';
      h3.style.color = '#38BDF8';
      h3.textContent = String(sl.title || '');
      stage.appendChild(h3);

      if (sl.id === 'cover') {
        const sub = document.createElement('div');
        sub.className = 'v218-code';
        sub.textContent = String(sl.subtitle || '');
        const p = document.createElement('p');
        p.style.margin = '8px 0 0';
        p.style.fontSize = '14px';
        p.style.lineHeight = '1.6';
        p.style.color = '#F8FAFC';
        p.textContent = String(sl.logline || '');
        const arch = document.createElement('div');
        arch.className = 'v218-sub';
        arch.textContent = 'Commercial Archetype: ' + String(sl.archetype || 'commercial_showcase');
        stage.appendChild(sub);
        stage.appendChild(p);
        stage.appendChild(arch);
      } else if (sl.id === 'palette') {
        const sub = document.createElement('div');
        sub.className = 'v218-sub';
        sub.textContent = 'Color Science Profile: ' + String(sl.look_name || 'Rec.709 Master Grade');
        stage.appendChild(sub);
        const strip = document.createElement('div');
        strip.className = 'v218-swatch-strip';
        (sl.palette || []).forEach((hex) => {
          const chip = document.createElement('div');
          chip.className = 'v218-swatch-chip';
          const box = document.createElement('span');
          box.className = 'v218-swatch-color';
          box.style.background = String(hex);
          const lbl = document.createElement('span');
          lbl.textContent = String(hex);
          chip.appendChild(box);
          chip.appendChild(lbl);
          strip.appendChild(chip);
        });
        stage.appendChild(strip);
      } else if (sl.id === 'beats') {
        const grid = document.createElement('div');
        grid.className = 'v218-beat-grid';
        (sl.scenes || []).forEach((sc) => {
          const card = document.createElement('div');
          card.className = 'v218-beat-card';
          const t = document.createElement('strong');
          t.textContent = 'S' + String(sc.scene_index).padStart(2, '0') + ' · ' + String(sc.scene_title || '');
          const meta = document.createElement('span');
          meta.className = 'v218-code';
          meta.textContent = String(sc.smpte_in || '') + ' · ' + String(sc.lens_movement || '');
          const desc = document.createElement('span');
          desc.className = 'v218-sub';
          desc.textContent = String(sc.beat_summary || '');
          card.appendChild(t);
          card.appendChild(meta);
          card.appendChild(desc);
          grid.appendChild(card);
        });
        stage.appendChild(grid);
      } else if (sl.id === 'bgm') {
        const meta = document.createElement('div');
        meta.className = 'v218-code';
        meta.textContent = String(sl.tempo_bpm || 108) + ' BPM · ' + String(sl.key_signature || 'D Minor') + ' · ' + String(sl.genre_style || '');
        const stems = document.createElement('div');
        stems.className = 'v218-badge-group';
        (sl.stems || []).forEach((st) => {
          const b = document.createElement('span');
          b.className = 'v218-badge v218-badge-info';
          b.textContent = String(st);
          stems.appendChild(b);
        });
        const lyr = document.createElement('p');
        lyr.className = 'v218-sub';
        lyr.style.marginTop = '8px';
        lyr.textContent = 'Lyria Prompt: ' + String(sl.lyria_prompt || '');
        stage.appendChild(meta);
        stage.appendChild(stems);
        stage.appendChild(lyr);
      } else if (sl.id === 'roi') {
        const row = document.createElement('div');
        row.className = 'v218-badge-group';
        const b1 = document.createElement('span');
        b1.className = 'v218-badge v218-badge-pass';
        b1.textContent = 'AI Compute: $' + Number(sl.estimated_ai_usd || 0).toFixed(2);
        const b2 = document.createElement('span');
        b2.className = 'v218-badge v218-badge-info';
        b2.textContent = 'AICP Baseline: $' + Number(sl.aicp_baseline_usd || 48500).toLocaleString();
        const b3 = document.createElement('span');
        b3.className = 'v218-badge v218-badge-pass';
        b3.textContent = Number(sl.savings_pct || 99.9).toFixed(2) + '% Cost Reduction';
        row.appendChild(b1);
        row.appendChild(b2);
        row.appendChild(b3);
        const turn = document.createElement('div');
        turn.className = 'v218-sub';
        turn.style.marginTop = '8px';
        turn.textContent = 'Turnaround Delta: ' + String(sl.turnaround_delta || '45s Pre-Viz vs 14 Days Traditional');
        stage.appendChild(row);
        stage.appendChild(turn);
      }
    }

    window.setTreatmentSlide = function(idx) {
      _ptSlideIndex = Number(idx) || 0;
      renderPitchTreatmentSlide();
    };

    window.stepTreatmentSlide = function(delta) {
      _ptSlideIndex += Number(delta || 1);
      renderPitchTreatmentSlide();
    };

    window.toggleRenderJobsHUD = function(forceState) {
      const modal = document.getElementById('modal-render-jobs');
      const btn = document.getElementById('btn-render-jobs-animatic');
      if (!modal) return;
      const shouldOpen = forceState !== undefined ? Boolean(forceState) : !isRenderJobsHUDOpen;
      if (!shouldOpen && !isRenderJobsHUDOpen) return;
      if (shouldOpen && typeof closeSecondaryOpenHUDs === 'function') closeSecondaryOpenHUDs();
      isRenderJobsHUDOpen = shouldOpen;
      window.isRenderJobsHUDOpen = shouldOpen;
      if (btn) {
        btn.classList.toggle('active', shouldOpen);
        btn.setAttribute('aria-expanded', shouldOpen ? 'true' : 'false');
      }
      if (shouldOpen) {
        lastRenderJobsOpener = document.activeElement;
        modal.style.display = 'flex';
        renderFrameAnchorSvg();
        const closeBtn = document.getElementById('btn-render-jobs-close');
        if (closeBtn) closeBtn.focus();
        _v218ShowToast('🎬 Live-Render Jobs & Take QA HUD: ACTIVE [`]');
      } else {
        modal.style.display = 'none';
        if (lastRenderJobsOpener && typeof lastRenderJobsOpener.focus === 'function') lastRenderJobsOpener.focus();
        else if (btn && typeof btn.focus === 'function') btn.focus();
      }
    };

    window.togglePitchTreatmentHUD = function(forceState) {
      const modal = document.getElementById('modal-pitch-treatment');
      const btn = document.getElementById('btn-treatment-animatic');
      if (!modal) return;
      const shouldOpen = forceState !== undefined ? Boolean(forceState) : !isPitchTreatmentHUDOpen;
      if (!shouldOpen && !isPitchTreatmentHUDOpen) return;
      if (shouldOpen && typeof closeSecondaryOpenHUDs === 'function') closeSecondaryOpenHUDs();
      isPitchTreatmentHUDOpen = shouldOpen;
      window.isPitchTreatmentHUDOpen = shouldOpen;
      if (btn) {
        btn.classList.toggle('active', shouldOpen);
        btn.setAttribute('aria-expanded', shouldOpen ? 'true' : 'false');
      }
      if (shouldOpen) {
        lastPitchTreatmentOpener = document.activeElement;
        modal.style.display = 'flex';
        renderPitchTreatmentSlide();
        const closeBtn = document.getElementById('btn-pitch-treatment-close');
        if (closeBtn) closeBtn.focus();
        _v218ShowToast('📽️ Director Pitch Treatment HUD: ACTIVE [-]');
      } else {
        modal.style.display = 'none';
        if (lastPitchTreatmentOpener && typeof lastPitchTreatmentOpener.focus === 'function') lastPitchTreatmentOpener.focus();
        else if (btn && typeof btn.focus === 'function') btn.focus();
      }
    };

    function _csvCellV218(val) {
      const s = String(val == null ? '' : val);
      return '"' + s.replace(/"/g, '""') + '"';
    }

    window.downloadRenderJobManifestJSON = function() {
      _v218DownloadBlob(
        JSON.stringify(V218_RENDER_JOBS_STATE, null, 2),
        'application/json;charset=utf-8;',
        'render_job_manifest.json',
        'Downloaded render_job_manifest.json'
      );
    };

    window.downloadTakeQaScorecardCSV = function() {
      const rows = [['Scene', 'Job_ID', 'Hero_Take', 'Status', 'Take_ID', 'Seed', 'QA_Score', 'Optical_Score', 'Audio_Sync_ms', 'Cost_USD', 'Anchor_Out', 'Luminance_Delta_Pct']];
      (V218_RENDER_JOBS_STATE.scene_jobs || []).forEach((job) => {
        ['A', 'B', 'C'].forEach((tKey) => {
          const tk = (job.takes && job.takes[tKey]) ? job.takes[tKey] : {};
          rows.push([
            job.scene_index,
            job.job_id,
            job.hero_take,
            tk.status || job.status,
            tKey,
            tk.seed || '',
            tk.qa_score || '',
            tk.optical_score || '',
            tk.audio_sync_ms || 0,
            tk.cost_usd || 1.25,
            job.anchor_out || '',
            job.luminance_delta_pct || 0
          ]);
        });
      });
      const csvText = rows.map((r) => r.map(_csvCellV218).join(',')).join('\\n') + '\\n';
      _v218DownloadBlob(csvText, 'text/csv;charset=utf-8;', 'take_qa_scorecard.csv', 'Downloaded take_qa_scorecard.csv');
    };

    window.downloadRoughCutAssemblySH = function() {
      const lines = [
        '#!/usr/bin/env bash',
        'set -euo pipefail',
        '# Omni Movie Director v2.18.0 Hero Rough-Cut Assembly Script',
        '# Project: ' + String(V218_RENDER_JOBS_STATE.project_title || 'Omni Production'),
        'CONCAT_LIST="rough_cut_concat.txt"',
        ': > "$CONCAT_LIST"'
      ];
      (V218_RENDER_JOBS_STATE.scene_jobs || []).forEach((job) => {
        const uri = String(job.output_media_path || job.output_clip_uri || ('renders/scene_' + job.scene_index + '.mp4'));
        lines.push('printf "file \\'%s\\'\\n" "' + uri + '" >> "$CONCAT_LIST"');
      });
      lines.push('ffmpeg -y -f concat -safe 0 -i "$CONCAT_LIST" -r 24 -c:v libx264 -pix_fmt yuv420p -c:a aac -b:a 192k rough_cut_master.mp4');
      lines.push('echo "Assembled rough_cut_master.mp4"');
      _v218DownloadBlob(lines.join('\\n') + '\\n', 'text/x-shellscript;charset=utf-8;', 'rough_cut_assembly.sh', 'Downloaded rough_cut_assembly.sh');
    };

    window.downloadTreatmentLookbookHTML = function() {
      const esc = (s) => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
      const swatches = (V218_TREATMENT_STATE.palette || []).map((hex) => '<span style="display:inline-block;padding:6px 10px;margin:4px;border-radius:4px;background:' + esc(hex) + ';color:#0F172A;font-family:monospace;font-weight:700;">' + esc(hex) + '</span>').join('');
      const beats = (V218_TREATMENT_STATE.scene_beats || []).map((b) => '<div style="border:1px solid #334155;padding:12px;border-radius:6px;margin-bottom:10px;"><strong>S' + b.scene_index + ' · ' + esc(b.scene_title) + '</strong> <small>(' + esc(b.smpte_in) + ' · ' + esc(b.lens_movement) + ')</small><p>' + esc(b.beat_summary) + '</p></div>').join('');
      const htmlDoc = '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><title>' + esc(V218_TREATMENT_STATE.project_title) + ' · Lookbook</title></head>'
        + '<body style="background:#07080B;color:#F8FAFC;font-family:sans-serif;max-width:960px;margin:40px auto;padding:20px;">'
        + '<h1>' + esc(V218_TREATMENT_STATE.project_title) + ' — Director&apos;s Treatment Lookbook</h1>'
        + '<p><em>' + esc(V218_TREATMENT_STATE.creative_regime) + ' · ' + esc(V218_TREATMENT_STATE.storytelling_mode) + ' · ' + esc(V218_TREATMENT_STATE.aspect_ratio) + '</em></p>'
        + '<blockquote>' + esc(V218_TREATMENT_STATE.logline) + '</blockquote>'
        + '<h2>Color Script Palette</h2><div>' + swatches + '</div>'
        + '<h2>Scene Beats</h2>' + beats
        + '</body></html>';
      _v218DownloadBlob(htmlDoc, 'text/html;charset=utf-8;', 'director_treatment_lookbook.html', 'Downloaded director_treatment_lookbook.html');
    };

    window.downloadTreatmentBriefMD = function() {
      const t = V218_TREATMENT_STATE;
      const lines = [
        '# Director Pitch Treatment: ' + (t.project_title || 'Omni Production'),
        '',
        '- **Regime**: `' + (t.creative_regime || '') + '`',
        '- **Storytelling Mode**: `' + (t.storytelling_mode || '') + '`',
        '- **Aspect & Runtime**: `' + (t.aspect_ratio || '16:9') + '` · `' + (t.runtime_sec || 32) + 's`',
        '',
        '## Logline',
        String(t.logline || ''),
        '',
        '## Color Script Palette',
        (t.palette || []).map((c) => '`' + c + '`').join(' · '),
        '',
        '## Scene Beats'
      ];
      (t.scene_beats || []).forEach((b) => {
        lines.push('- **S' + String(b.scene_index).padStart(2, '0') + ' · ' + b.scene_title + '** (`' + b.smpte_in + '`, `' + b.lens_movement + '`): ' + b.beat_summary);
      });
      lines.push('', '## AI vs AICP ROI', '- Estimated AI Compute: `$' + Number((t.roi && t.roi.estimated_ai_usd) || 0).toFixed(2) + '` vs AICP Baseline `$' + Number((t.roi && t.roi.aicp_baseline_usd) || 48500).toFixed(2) + '` (`' + Number((t.roi && t.roi.savings_pct) || 99.9).toFixed(2) + '%` savings)');
      _v218DownloadBlob(lines.join('\\n') + '\\n', 'text/markdown;charset=utf-8;', 'director_treatment_brief.md', 'Downloaded director_treatment_brief.md');
    };

    window.downloadPitchTreatmentManifestJSON = function() {
      _v218DownloadBlob(
        JSON.stringify(V218_TREATMENT_STATE, null, 2),
        'application/json;charset=utf-8;',
        'pitch_treatment_manifest.json',
        'Downloaded pitch_treatment_manifest.json'
      );
    };

    window.initV218HUDs = function() {
      if (_v218Initialized) return;
      _v218Initialized = true;
      _v218TrapFocus(document.getElementById('modal-render-jobs'), () => toggleRenderJobsHUD(false));
      _v218TrapFocus(document.getElementById('modal-pitch-treatment'), () => togglePitchTreatmentHUD(false));
      renderFrameAnchorSvg();
      renderPitchTreatmentSlide();
    };

    document.addEventListener('DOMContentLoaded', () => {
      if (typeof initV218HUDs === 'function') initV218HUDs();
    });
    """

    js_str = (
        js_template
        .replace("__RJ_JSON__", rj_json)
        .replace("__PT_JSON__", pt_json)
    )

    return css_str, modals_html, js_str


__all__ = [
    "synthesize_v218_render_jobs_state",
    "synthesize_v218_pitch_treatment_state",
    "build_v218_hud_bundle",
]
