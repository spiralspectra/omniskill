"""Modular v2.16.0 Dark-Room Cinema HUD Components.

Provides Python 3.11-compatible builders for:
1. Unified HUD Command Palette (#modal-hud-command-palette, [/] hotkey)
2. Art & Wardrobe Continuity Locker (#modal-art-wardrobe-continuity, [\\] hotkey)
3. Compute Economics & Take-Variant Inspector (#modal-render-economics, [;] hotkey)
"""

from __future__ import annotations

import csv
import io
import json
import re
from html import escape as html_escape
from typing import Any, Dict, List


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


def _synthesize_wardrobe_prop_bible(bible: Any) -> Dict[str, Any]:
    """Extracts or safely synthesizes the Art & Wardrobe Continuity Locker payload."""
    existing = _get_field(bible, "master_wardrobe_prop_bible", None)
    plain = _to_plain(existing)
    if isinstance(plain, dict) and plain.get("scene_entries"):
        return plain

    project_title = str(_get_field(bible, "project_title", "Omni Production") or "Omni Production")
    characters = _to_plain(_get_field(bible, "characters", []) or [])
    scenes = _to_plain(_get_field(bible, "scenes", []) or [])
    nano_assets = _to_plain(_get_field(bible, "nano_banana_assets", []) or [])

    if isinstance(plain, dict) and plain.get("scene_art_specs"):
        scene_title_map: Dict[int, str] = {}
        for idx, sc in enumerate(scenes):
            if isinstance(sc, dict):
                s_idx = int(sc.get("scene_index", idx + 1) or (idx + 1))
                scene_title_map[s_idx] = str(sc.get("scene_title") or f"Scene {s_idx}")

        char_looks: List[Dict[str, str]] = []
        seen_looks = set()
        for lk in plain.get("wardrobe_looks_summary") or []:
            if not isinstance(lk, dict):
                continue
            char_name = str(lk.get("character_id") or lk.get("character") or "Hero Subject")
            look_id = str(lk.get("look_id") or "LOOK_A")
            garment = str(lk.get("garment_summary") or lk.get("wardrobe_spec") or "Hero signature wardrobe")
            key = (char_name, look_id)
            if key not in seen_looks:
                seen_looks.add(key)
                char_looks.append({"character": char_name, "look_id": look_id, "wardrobe_spec": garment})

        scene_entries: List[Dict[str, Any]] = []
        prev_prop_states: Dict[str, str] = {}
        for idx, spec in enumerate(plain.get("scene_art_specs") or []):
            if not isinstance(spec, dict):
                continue
            s_idx = int(spec.get("scene_index", idx + 1) or (idx + 1))
            s_title = str(spec.get("scene_title") or scene_title_map.get(s_idx) or f"Scene {s_idx}")
            w_states = spec.get("wardrobe_states") or []
            p_states = spec.get("prop_states") or []
            art_anchors = spec.get("dressing_anchors") or spec.get("art_anchors") or []

            first_w = w_states[0] if w_states and isinstance(w_states[0], dict) else {}
            char_name = str(first_w.get("character_id") or first_w.get("character") or (char_looks[0]["character"] if char_looks else "Hero Subject"))
            look_id = str(first_w.get("look_id") or "LOOK_A")
            wardrobe_spec = str(first_w.get("garment_summary") or first_w.get("wardrobe_spec") or "Hero signature wardrobe")
            weathering = str(first_w.get("weathering_stage") or "").strip()
            if weathering and weathering not in wardrobe_spec:
                wardrobe_spec = f"{wardrobe_spec} ({weathering})"

            if (char_name, look_id) not in seen_looks:
                seen_looks.add((char_name, look_id))
                char_looks.append({"character": char_name, "look_id": look_id, "wardrobe_spec": wardrobe_spec})

            first_p = p_states[0] if p_states and isinstance(p_states[0], dict) else {}
            prop_id = str(first_p.get("prop_id") or f"PROP_S{s_idx:02d}")
            prop_name = str(first_p.get("prop_name") or f"Hero Prop S{s_idx:02d}")
            prop_state = str(first_p.get("action_state") or "intact")

            assigned_slots = spec.get("assigned_reference_slots") or []
            raw_slot_count = spec.get("reference_slot_count")
            slot_count = int(raw_slot_count) if raw_slot_count is not None else len(assigned_slots)
            slot_count = min(3, max(1, slot_count if slot_count > 0 else 1))

            delta_note = str(spec.get("continuity_delta_note") or "").strip()
            has_break = bool(spec.get("slot_contention_detected", False))
            if not has_break and prop_id in prev_prop_states and len(delta_note) < 4:
                prev_st = prev_prop_states[prop_id]
                if (prev_st == "damaged" and prop_state == "intact") or (
                    prev_st in ("in_hand_left", "in_hand_right")
                    and prop_state in ("in_hand_left", "in_hand_right")
                    and prev_st != prop_state
                ):
                    has_break = True
            prev_prop_states[prop_id] = prop_state

            anchor_note = ""
            if art_anchors and isinstance(art_anchors[0], dict):
                anchor_note = str(art_anchors[0].get("zone_label") or art_anchors[0].get("hero_material_finish") or "")

            note_text = delta_note or (f"Anchor: {anchor_note}" if anchor_note else "Continuity locked")
            if spec.get("slot_contention_detected") and "contention" not in note_text.lower():
                note_text = f"Reference slot contention (>3) · {note_text}"

            scene_entries.append({
                "scene_index": s_idx,
                "scene_title": s_title,
                "character": char_name,
                "look_id": look_id,
                "wardrobe_spec": wardrobe_spec,
                "prop_name": prop_name,
                "prop_state": prop_state,
                "reference_slots_used": slot_count,
                "continuity_break": has_break,
                "continuity_note": note_text[:96],
            })

        if scene_entries:
            if not char_looks:
                char_looks.append({
                    "character": scene_entries[0]["character"],
                    "look_id": scene_entries[0]["look_id"],
                    "wardrobe_spec": scene_entries[0]["wardrobe_spec"],
                })
            max_slots_used = min(3, max(1, max(int(r.get("reference_slots_used", 1)) for r in scene_entries)))
            declared_breaks = int(plain.get("continuity_breaks_detected") or 0)
            row_breaks = sum(1 for row in scene_entries if row.get("continuity_break"))
            break_count = max(declared_breaks, row_breaks)
            return {
                "project_title": project_title,
                "reference_slots_max": 3,
                "reference_slots_used": max_slots_used,
                "continuity_break_count": break_count,
                "continuity_status": "VERIFIED" if break_count == 0 else f"{break_count} BREAK RISK(S)",
                "wardrobe_looks": char_looks,
                "scene_entries": scene_entries,
            }

    char_looks: List[Dict[str, str]] = []
    for idx, ch in enumerate(characters):
        if isinstance(ch, dict):
            name = str(ch.get("name") or f"Talent {idx + 1}")
            wardrobe = str(ch.get("wardrobe_polarity") or "Hero signature wardrobe")
        else:
            name = str(ch or f"Talent {idx + 1}")
            wardrobe = "Hero signature wardrobe"
        char_looks.append({
            "character": name,
            "look_id": f"LOOK-{idx + 1:02d}",
            "wardrobe_spec": wardrobe,
        })
    if not char_looks:
        char_looks.append({
            "character": "Hero Subject",
            "look_id": "LOOK-01",
            "wardrobe_spec": "Primary Hero Wardrobe Anchor",
        })

    slot_count = min(3, max(1, len(nano_assets) if nano_assets else min(3, len(char_looks) + 1)))
    prop_states = ["intact", "in_hand_left", "in_hand_right", "on_surface"]

    scene_entries: List[Dict[str, Any]] = []
    for idx, sc in enumerate(scenes):
        sc_dict = sc if isinstance(sc, dict) else {}
        s_idx = int(sc_dict.get("scene_index", idx + 1))
        s_title = str(sc_dict.get("scene_title") or f"Scene {s_idx}")
        primary_look = char_looks[idx % len(char_looks)]
        prop_name = f"Hero Prop S{s_idx:02d}"
        prose = str(sc_dict.get("omni_prose_prompt") or "")
        action_beats = sc_dict.get("action_beats") or []
        state_val = prop_states[idx % len(prop_states)]
        if "left" in prose.lower():
            state_val = "in_hand_left"
        elif "right" in prose.lower():
            state_val = "in_hand_right"
        elif idx == 0:
            state_val = "intact"

        has_break = False
        break_reason = "Verified"
        if idx > 0 and scene_entries:
            prev_state = scene_entries[-1]["prop_state"]
            if prev_state == "in_hand_left" and state_val == "in_hand_right":
                has_break = True
                break_reason = "Hand-off delta (L->R) without insert cut"

        scene_entries.append({
            "scene_index": s_idx,
            "scene_title": s_title,
            "character": primary_look["character"],
            "look_id": primary_look["look_id"],
            "wardrobe_spec": primary_look["wardrobe_spec"],
            "prop_name": prop_name,
            "prop_state": state_val,
            "reference_slots_used": slot_count,
            "continuity_break": has_break,
            "continuity_note": break_reason if has_break else (str(action_beats[0])[:64] if action_beats else "Continuity locked"),
        })

    if not scene_entries:
        scene_entries.append({
            "scene_index": 1,
            "scene_title": "Opening Master",
            "character": char_looks[0]["character"],
            "look_id": char_looks[0]["look_id"],
            "wardrobe_spec": char_looks[0]["wardrobe_spec"],
            "prop_name": "Hero Anchor Prop",
            "prop_state": "intact",
            "reference_slots_used": slot_count,
            "continuity_break": False,
            "continuity_note": "Baseline continuity anchor established",
        })

    break_count = sum(1 for row in scene_entries if row.get("continuity_break"))
    return {
        "project_title": project_title,
        "reference_slots_max": 3,
        "reference_slots_used": slot_count,
        "continuity_break_count": break_count,
        "continuity_status": "VERIFIED" if break_count == 0 else f"{break_count} BREAK RISK(S)",
        "wardrobe_looks": char_looks,
        "scene_entries": scene_entries,
    }


def _get_2026_rate_lookup() -> Dict[str, Dict[str, Any]]:
    """Returns 2026 Model Matrix unit rates keyed by approved model_id."""
    try:
        from omni_director.tools.render_economics import get_2026_model_matrix_rates

        rates = get_2026_model_matrix_rates()
        return {
            r.model_id: {
                "model_id": r.model_id,
                "role_label": r.role_label,
                "input_per_1m_usd": float(r.input_per_1m_usd),
                "output_per_1m_usd": float(r.output_per_1m_usd),
                "unit_render_usd": float(r.unit_render_usd),
            }
            for r in rates
        }
    except Exception:
        return {
            "gemini-4-argon": {
                "model_id": "gemini-4-argon",
                "role_label": "Lead Creative Director",
                "input_per_1m_usd": 2.50,
                "output_per_1m_usd": 10.00,
                "unit_render_usd": 0.0,
            },
            "gemini-3.8-flash": {
                "model_id": "gemini-3.8-flash",
                "role_label": "Fast Workhorse Fan-Out",
                "input_per_1m_usd": 0.15,
                "output_per_1m_usd": 0.60,
                "unit_render_usd": 0.0,
            },
            "gemini-3-pro-image": {
                "model_id": "gemini-3-pro-image",
                "role_label": "Visual Concept & Continuity",
                "input_per_1m_usd": 1.25,
                "output_per_1m_usd": 5.00,
                "unit_render_usd": 0.08,
            },
            "gemini-omni-1.1-flash-preview": {
                "model_id": "gemini-omni-1.1-flash-preview",
                "role_label": "Video & Multimodal Audio",
                "input_per_1m_usd": 0.50,
                "output_per_1m_usd": 2.00,
                "unit_render_usd": 0.25,
            },
        }


def _resolve_aicp_baseline_usd(bible: Any, plain: Any = None) -> float:
    """Resolves traditional AICP baseline USD from manifest or MasterProductionBible."""
    if isinstance(plain, dict) and plain.get("aicp_post_baseline_usd"):
        val = float(plain["aicp_post_baseline_usd"])
        if val > 0.0:
            return val
    aicp_spec = _to_plain(_get_field(bible, "master_aicp_bid", None) or _get_field(bible, "aicp_bid", None))
    if isinstance(aicp_spec, dict):
        for key in ("grand_total_usd", "grand_total"):
            if aicp_spec.get(key) and float(aicp_spec[key]) > 0.0:
                return float(aicp_spec[key])
        top_sheet = aicp_spec.get("top_sheet")
        if isinstance(top_sheet, dict) and top_sheet.get("grand_total_bid_usd"):
            val = float(top_sheet["grand_total_bid_usd"])
            if val > 0.0:
                return val
    return 120000.0


def _synthesize_render_economics_spec(bible: Any) -> Dict[str, Any]:
    """Extracts or safely synthesizes the Compute Economics & Take-Variant Inspector payload."""
    existing = _get_field(bible, "master_render_economics_spec", None)
    plain = _to_plain(existing)
    if isinstance(plain, dict) and plain.get("scene_takes"):
        return plain

    project_title = str(_get_field(bible, "project_title", "Omni Production") or "Omni Production")
    scenes = _to_plain(_get_field(bible, "scenes", []) or [])
    rates = _get_2026_rate_lookup()

    if isinstance(plain, dict) and plain.get("model_rates"):
        for mr in plain.get("model_rates") or []:
            if isinstance(mr, dict) and mr.get("model_id"):
                mid = str(mr["model_id"])
                rates[mid] = {
                    "model_id": mid,
                    "role_label": str(mr.get("role_label") or rates.get(mid, {}).get("role_label", mid)),
                    "input_per_1m_usd": float(mr.get("input_per_1m_usd", rates.get(mid, {}).get("input_per_1m_usd", 0.0))),
                    "output_per_1m_usd": float(mr.get("output_per_1m_usd", rates.get(mid, {}).get("output_per_1m_usd", 0.0))),
                    "unit_render_usd": float(mr.get("unit_render_usd", rates.get(mid, {}).get("unit_render_usd", 0.0))),
                }

    argon_r = rates["gemini-4-argon"]
    flash_r = rates["gemini-3.8-flash"]
    image_r = rates["gemini-3-pro-image"]
    omni_r = rates["gemini-omni-1.1-flash-preview"]

    argon_per_call = round((3500 / 1_000_000.0) * (argon_r["input_per_1m_usd"] + argon_r["output_per_1m_usd"]), 4)
    flash_per_call = round((2000 / 1_000_000.0) * (flash_r["input_per_1m_usd"] + flash_r["output_per_1m_usd"]), 4)
    image_unit = float(image_r["unit_render_usd"] or 0.08)
    omni_unit = float(omni_r["unit_render_usd"] or 0.25)

    if isinstance(plain, dict) and plain.get("scene_estimates"):
        scene_title_map: Dict[int, str] = {}
        for idx, sc in enumerate(scenes):
            if isinstance(sc, dict):
                s_idx = int(sc.get("scene_index", idx + 1) or (idx + 1))
                scene_title_map[s_idx] = str(sc.get("scene_title") or f"Scene {s_idx}")

        scene_estimates = list(plain.get("scene_estimates") or [])
        scene_takes: List[Dict[str, Any]] = []
        total_reasoning_tokens = 0
        total_plate_renders = 0
        total_selected_video_sec = 0

        for idx, est in enumerate(scene_estimates):
            if not isinstance(est, dict):
                continue
            s_idx = int(est.get("scene_index", idx + 1) or (idx + 1))
            s_title = str(est.get("scene_title") or scene_title_map.get(s_idx) or f"Scene {s_idx}")
            dur_s = int(est.get("duration_seconds", 8) or 8)
            total_reasoning_tokens += int(est.get("reasoning_tokens_est", 3500) or 3500)
            total_plate_renders += int(est.get("plate_renders", 1) or 1)
            base_video_cost = round(dur_s * omni_unit, 2)

            raw_takes = est.get("takes")
            takes_dict: Dict[str, Dict[str, Any]] = {}
            sel_key = str(est.get("selected_take") or "")

            if isinstance(raw_takes, dict):
                for tk in ("A", "B", "C"):
                    t_info = raw_takes.get(tk) or {}
                    takes_dict[tk] = {
                        "label": str(t_info.get("label") or f"Take {tk}"),
                        "cost_usd": round(float(t_info.get("cost_usd", t_info.get("estimated_cost_usd", base_video_cost)) or base_video_cost), 2),
                        "audit_score": int(t_info.get("audit_score", 95) or 95),
                        "seed": int(t_info.get("seed", 1041 + s_idx) or (1041 + s_idx)),
                    }
                if sel_key not in ("A", "B", "C"):
                    sel_key = "A"
            else:
                take_list = list(raw_takes or []) if isinstance(raw_takes, list) else []
                default_labels = {
                    "A": "Primary 1080p24 Hero",
                    "B": "Alt Camera Coverage",
                    "C": "4K Hero Upscale",
                }
                cost_mults = {"A": 1.0, "B": 1.2, "C": 1.6}
                for t_idx, tk in enumerate(("A", "B", "C")):
                    if t_idx < len(take_list) and isinstance(take_list[t_idx], dict):
                        rec = take_list[t_idx]
                        if not sel_key and rec.get("selected"):
                            sel_key = tk
                        rec_cost = float(rec.get("estimated_cost_usd", rec.get("cost_usd", base_video_cost)) or base_video_cost)
                        note = str(rec.get("director_note") or default_labels[tk])
                        takes_dict[tk] = {
                            "label": f"Take {tk} ({note[:28]})",
                            "cost_usd": round(rec_cost, 2),
                            "audit_score": int(rec.get("audit_score", 95) or 95),
                            "seed": int(rec.get("seed", 1041 + s_idx + t_idx * 1000) or (1041 + s_idx + t_idx * 1000)),
                        }
                    else:
                        takes_dict[tk] = {
                            "label": f"Take {tk} ({default_labels[tk]})",
                            "cost_usd": round(base_video_cost * cost_mults[tk], 2),
                            "audit_score": min(99, 94 + t_idx * 2),
                            "seed": 1041 + s_idx + t_idx * 1000,
                        }
                if sel_key not in ("A", "B", "C"):
                    sel_key = "A"

            total_selected_video_sec += dur_s
            scene_takes.append({
                "scene_index": s_idx,
                "scene_title": s_title,
                "selected_take": sel_key,
                "takes": takes_dict,
            })

        if scene_takes:
            num_sc = len(scene_takes)
            argon_sub = round((total_reasoning_tokens / 1_000_000.0) * (argon_r["input_per_1m_usd"] + argon_r["output_per_1m_usd"]), 4)
            flash_sub = round(num_sc * flash_per_call, 4)
            image_sub = round(total_plate_renders * image_unit, 4)
            video_spend = round(sum(float(st["takes"][st["selected_take"]]["cost_usd"]) for st in scene_takes), 2)

            guardrail = plain.get("guardrail") if isinstance(plain.get("guardrail"), dict) else {}
            manifest_est = float(
                plain.get("estimated_total_compute_usd")
                or guardrail.get("estimated_total_usd")
                or 0.0
            )
            estimated_spend = round(manifest_est if manifest_est > 0.0 else (argon_sub + flash_sub + image_sub + video_spend), 2)
            fixed_overhead = round(max(0.0, estimated_spend - video_spend), 4)
            budget_ceiling = round(float(guardrail.get("max_render_budget_usd") or max(25.0, estimated_spend * 2.2)), 2)

            aicp_baseline = _resolve_aicp_baseline_usd(bible, plain)
            savings_raw = plain.get("aicp_savings_pct") or guardrail.get("simulation_savings_vs_aicp_pct")
            savings_pct = (
                round(float(savings_raw), 2)
                if savings_raw is not None and float(savings_raw) > 0.0
                else round(max(0.0, (1.0 - (estimated_spend / max(1.0, aicp_baseline))) * 100.0), 2)
            )

            model_breakdown = [
                {
                    "model_id": "gemini-4-argon",
                    "role": argon_r["role_label"],
                    "unit_cost_usd": argon_per_call,
                    "calls": num_sc,
                    "subtotal_usd": round(argon_sub, 2),
                },
                {
                    "model_id": "gemini-3.8-flash",
                    "role": flash_r["role_label"],
                    "unit_cost_usd": flash_per_call,
                    "calls": num_sc,
                    "subtotal_usd": round(flash_sub, 2),
                },
                {
                    "model_id": "gemini-3-pro-image",
                    "role": image_r["role_label"],
                    "unit_cost_usd": image_unit,
                    "calls": total_plate_renders,
                    "subtotal_usd": round(image_sub, 2),
                },
                {
                    "model_id": "gemini-omni-1.1-flash-preview",
                    "role": omni_r["role_label"],
                    "unit_cost_usd": omni_unit,
                    "calls": total_selected_video_sec,
                    "subtotal_usd": video_spend,
                },
            ]

            return {
                "project_title": project_title,
                "budget_ceiling_usd": budget_ceiling,
                "fixed_pipeline_overhead_usd": fixed_overhead,
                "estimated_spend_usd": estimated_spend,
                "aicp_traditional_baseline_usd": round(aicp_baseline, 2),
                "aicp_baseline_usd": round(aicp_baseline, 2),
                "ai_vs_aicp_savings_pct": savings_pct,
                "savings_pct": savings_pct,
                "model_breakdown": model_breakdown,
                "scene_takes": scene_takes,
            }

    num_scenes = max(1, len(scenes))
    default_dur = 8
    take_a_cost = round(default_dur * omni_unit, 2)
    take_b_cost = round(take_a_cost * 1.2, 2)
    take_c_cost = round(take_a_cost * 1.6, 2)

    # 2026 Model Matrix cost breakdown (strictly approved 2026 models aligned with get_2026_model_matrix_rates)
    model_breakdown = [
        {
            "model_id": "gemini-4-argon",
            "role": argon_r["role_label"],
            "unit_cost_usd": argon_per_call,
            "calls": num_scenes,
            "subtotal_usd": round(argon_per_call * num_scenes, 2),
        },
        {
            "model_id": "gemini-3.8-flash",
            "role": flash_r["role_label"],
            "unit_cost_usd": flash_per_call,
            "calls": num_scenes,
            "subtotal_usd": round(flash_per_call * num_scenes, 2),
        },
        {
            "model_id": "gemini-3-pro-image",
            "role": image_r["role_label"],
            "unit_cost_usd": image_unit,
            "calls": num_scenes,
            "subtotal_usd": round(image_unit * num_scenes, 2),
        },
        {
            "model_id": "gemini-omni-1.1-flash-preview",
            "role": omni_r["role_label"],
            "unit_cost_usd": omni_unit,
            "calls": num_scenes * default_dur,
            "subtotal_usd": round(take_a_cost * num_scenes, 2),
        },
    ]

    scene_takes = []
    for idx, sc in enumerate(scenes):
        sc_dict = sc if isinstance(sc, dict) else {}
        s_idx = int(sc_dict.get("scene_index", idx + 1))
        s_title = str(sc_dict.get("scene_title") or f"Scene {s_idx}")
        scene_takes.append({
            "scene_index": s_idx,
            "scene_title": s_title,
            "selected_take": "A",
            "takes": {
                "A": {"label": "Take A (Primary 1080p24 Hero)", "cost_usd": take_a_cost, "audit_score": 95, "seed": 1041 + s_idx},
                "B": {"label": "Take B (Alt Camera Coverage)", "cost_usd": take_b_cost, "audit_score": 96, "seed": 2041 + s_idx},
                "C": {"label": "Take C (4K Hero Upscale)", "cost_usd": take_c_cost, "audit_score": 98, "seed": 3041 + s_idx},
            },
        })

    if not scene_takes:
        scene_takes.append({
            "scene_index": 1,
            "scene_title": "Opening Master",
            "selected_take": "A",
            "takes": {
                "A": {"label": "Take A (Primary 1080p24 Hero)", "cost_usd": take_a_cost, "audit_score": 95, "seed": 1042},
                "B": {"label": "Take B (Alt Camera Coverage)", "cost_usd": take_b_cost, "audit_score": 96, "seed": 2042},
                "C": {"label": "Take C (4K Hero Upscale)", "cost_usd": take_c_cost, "audit_score": 98, "seed": 3042},
            },
        })

    fixed_overhead = round(sum(float(m["subtotal_usd"]) for m in model_breakdown if m["model_id"] != "gemini-omni-1.1-flash-preview"), 2)
    initial_video_spend = round(sum(float(st["takes"][st["selected_take"]]["cost_usd"]) for st in scene_takes), 2)
    estimated_spend = round(fixed_overhead + initial_video_spend, 2)
    budget_ceiling = round(max(25.0, estimated_spend * 2.2), 2)

    aicp_baseline = _resolve_aicp_baseline_usd(bible, plain)
    savings_pct = round(max(0.0, (1.0 - (estimated_spend / max(1.0, aicp_baseline))) * 100.0), 2)

    return {
        "project_title": project_title,
        "budget_ceiling_usd": budget_ceiling,
        "fixed_pipeline_overhead_usd": fixed_overhead,
        "estimated_spend_usd": estimated_spend,
        "aicp_traditional_baseline_usd": round(aicp_baseline, 2),
        "aicp_baseline_usd": round(aicp_baseline, 2),
        "ai_vs_aicp_savings_pct": savings_pct,
        "savings_pct": savings_pct,
        "model_breakdown": model_breakdown,
        "scene_takes": scene_takes,
    }


def _build_prop_continuity_csv(wardrobe_spec: Dict[str, Any]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Scene", "Title", "Character", "Look_ID", "Wardrobe_Spec", "Prop", "Prop_State", "Ref_Slots_Used", "Continuity_Break", "Notes"])
    for row in wardrobe_spec.get("scene_entries") or []:
        writer.writerow([
            row.get("scene_index", 1),
            row.get("scene_title", ""),
            row.get("character", ""),
            row.get("look_id", ""),
            row.get("wardrobe_spec", ""),
            row.get("prop_name", ""),
            row.get("prop_state", "intact"),
            row.get("reference_slots_used", 1),
            row.get("continuity_break", False),
            row.get("continuity_note", ""),
        ])
    return buf.getvalue()


def _build_art_dept_pull_list_md(wardrobe_spec: Dict[str, Any]) -> str:
    lines = [
        f"# Art & Wardrobe Department Pull List: {wardrobe_spec.get('project_title', 'Omni Production')}",
        "",
        f"- **Continuity Status**: `{wardrobe_spec.get('continuity_status', 'VERIFIED')}`",
        f"- **Omni Reference Slots Used**: `{wardrobe_spec.get('reference_slots_used', 1)} / {wardrobe_spec.get('reference_slots_max', 3)}`",
        "",
        "## Wardrobe Looks",
    ]
    for lk in wardrobe_spec.get("wardrobe_looks") or []:
        lines.append(f"- **{lk.get('look_id', 'LOOK-01')}** ({lk.get('character', 'Subject')}): {lk.get('wardrobe_spec', '')}")
    lines.extend(["", "## Per-Scene Prop & Continuity Matrix", "| Scene | Character | Look | Prop | State | Continuity |", "|---|---|---|---|---|---|"])
    for row in wardrobe_spec.get("scene_entries") or []:
        status = "BREAK RISK" if row.get("continuity_break") else "OK"
        lines.append(
            f"| S{int(row.get('scene_index', 1)):02d} | {row.get('character', '')} | {row.get('look_id', '')} | "
            f"{row.get('prop_name', '')} | `{row.get('prop_state', 'intact')}` | {status} |"
        )
    return "\n".join(lines) + "\n"


def _build_take_ledger_csv(econ_spec: Dict[str, Any]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Scene", "Title", "Selected_Take", "Label", "Video_Cost_USD", "Audit_Score", "Seed"])
    for sc in econ_spec.get("scene_takes") or []:
        sel = sc.get("selected_take", "A")
        t = (sc.get("takes") or {}).get(sel, {})
        writer.writerow([
            sc.get("scene_index", 1),
            sc.get("scene_title", ""),
            sel,
            t.get("label", ""),
            t.get("cost_usd", 1.25),
            t.get("audit_score", 94),
            t.get("seed", 1001),
        ])
    return buf.getvalue()


def _build_compute_estimate_md(econ_spec: Dict[str, Any]) -> str:
    lines = [
        f"# AI Compute Economics Estimate: {econ_spec.get('project_title', 'Omni Production')}",
        "",
        f"- **Estimated Spend**: `${econ_spec.get('estimated_spend_usd', 0.0):.2f}`",
        f"- **Budget Ceiling**: `${econ_spec.get('budget_ceiling_usd', 25.0):.2f}`",
        f"- **Traditional AICP Baseline**: `${econ_spec.get('aicp_traditional_baseline_usd', 48500.0):,.2f}`",
        f"- **AI vs AICP Savings**: `{econ_spec.get('ai_vs_aicp_savings_pct', 99.9):.2f}%`",
        "",
        "## 2026 Model Matrix Breakdown",
        "| Model ID | Pipeline Role | Calls | Unit Cost | Subtotal |",
        "|---|---|---|---|---|",
    ]
    for m in econ_spec.get("model_breakdown") or []:
        lines.append(
            f"| `{m.get('model_id', '')}` | {m.get('role', '')} | {m.get('calls', 1)} | "
            f"${float(m.get('unit_cost_usd', 0.0)):.2f} | ${float(m.get('subtotal_usd', 0.0)):.2f} |"
        )
    return "\n".join(lines) + "\n"


def build_v216_hud_bundle(bible: Any) -> Dict[str, str]:
    """Builds Dark-Room Cinema v2.16.0 HUD CSS, modals HTML, and JS controllers."""
    wardrobe_spec = _synthesize_wardrobe_prop_bible(bible)
    econ_spec = _synthesize_render_economics_spec(bible)

    wardrobe_json = _escape_json_for_script(wardrobe_spec)
    econ_json = _escape_json_for_script(econ_spec)

    # Pre-rendered Art & Wardrobe rows
    slots_used = int(wardrobe_spec.get("reference_slots_used", 1))
    slots_max = int(wardrobe_spec.get("reference_slots_max", 3))
    slot_pct = min(100, max(0, int(round((slots_used / max(1, slots_max)) * 100))))
    continuity_ok = int(wardrobe_spec.get("continuity_break_count", 0)) == 0
    continuity_badge_cls = "v216-badge-pass" if continuity_ok else "v216-badge-warn"

    wardrobe_rows_html: List[str] = []
    for row in wardrobe_spec.get("scene_entries") or []:
        s_idx = int(row.get("scene_index", 1))
        is_brk = bool(row.get("continuity_break"))
        brk_cls = "v216-badge-warn" if is_brk else "v216-badge-pass"
        brk_txt = "BREAK RISK" if is_brk else "CONTINUITY OK"
        wardrobe_rows_html.append(
            f"<tr>"
            f"<td><strong>S{s_idx:02d}</strong> · {html_escape(str(row.get('scene_title', '')))}</td>"
            f"<td><span class=\"v216-pill\">{html_escape(str(row.get('look_id', 'LOOK-01')))}</span> "
            f"{html_escape(str(row.get('character', '')))}<br>"
            f"<span class=\"v216-sub\">{html_escape(str(row.get('wardrobe_spec', '')))}</span></td>"
            f"<td>{html_escape(str(row.get('prop_name', '')))}<br>"
            f"<code class=\"v216-code\">{html_escape(str(row.get('prop_state', 'intact')))}</code></td>"
            f"<td><span class=\"v216-badge {brk_cls}\">{brk_txt}</span><br>"
            f"<span class=\"v216-sub\">{html_escape(str(row.get('continuity_note', '')))}</span></td>"
            f"</tr>"
        )
    wardrobe_tbody_html = "\n".join(wardrobe_rows_html)

    # Pre-rendered Compute Economics rows
    est_spend = float(econ_spec.get("estimated_spend_usd", 0.0))
    budget_ceil = max(1.0, float(econ_spec.get("budget_ceiling_usd", 25.0)))
    spend_pct = min(100.0, max(0.0, round((est_spend / budget_ceil) * 100.0, 1)))
    aicp_base = float(econ_spec.get("aicp_traditional_baseline_usd", 48500.0))
    savings_pct = float(econ_spec.get("ai_vs_aicp_savings_pct", 99.9))

    model_rows_html: List[str] = []
    for m in econ_spec.get("model_breakdown") or []:
        m_id = html_escape(str(m.get("model_id", "")))
        subtotal = float(m.get("subtotal_usd", 0.0))
        model_rows_html.append(
            f"<tr data-model-id=\"{m_id}\">"
            f"<td><code class=\"v216-code\">{m_id}</code></td>"
            f"<td>{html_escape(str(m.get('role', '')))}</td>"
            f"<td>{int(m.get('calls', 1))}</td>"
            f"<td>${float(m.get('unit_cost_usd', 0.0)):.2f}</td>"
            f"<td class=\"v216-model-subtotal\">${subtotal:.2f}</td>"
            f"</tr>"
        )
    model_tbody_html = "\n".join(model_rows_html)

    take_rows_html: List[str] = []
    for sc in econ_spec.get("scene_takes") or []:
        s_idx = int(sc.get("scene_index", 1))
        sel = str(sc.get("selected_take", "A"))
        takes = sc.get("takes") or {}
        radios_html: List[str] = []
        for tk in ("A", "B", "C"):
            t_info = takes.get(tk) or {}
            checked = "checked" if sel == tk else ""
            cost = float(t_info.get("cost_usd", 1.25))
            score = int(t_info.get("audit_score", 94))
            radios_html.append(
                f"<label class=\"v216-take-option\">"
                f"<input type=\"radio\" name=\"take-scene-{s_idx}\" value=\"{tk}\" {checked} "
                f"onchange=\"selectSceneTakeVariant({s_idx}, '{tk}')\" "
                f"aria-label=\"Scene {s_idx} Take {tk} (${cost:.2f}, Score {score})\">"
                f"<span><strong>Take {tk}</strong> · ${cost:.2f} · {score}/100</span>"
                f"</label>"
            )
        active_t = takes.get(sel) or {}
        take_rows_html.append(
            f"<tr>"
            f"<td><strong>S{s_idx:02d}</strong> · {html_escape(str(sc.get('scene_title', '')))}</td>"
            f"<td><div class=\"v216-take-group\" role=\"radiogroup\" aria-label=\"Take selector for Scene {s_idx}\">{''.join(radios_html)}</div></td>"
            f"<td><code id=\"v216-take-seed-{s_idx}\" class=\"v216-code\">#{int(active_t.get('seed', 1001))}</code></td>"
            f"</tr>"
        )
    take_tbody_html = "\n".join(take_rows_html)

    css = """
    /* v2.16.0 Unified HUD Command Palette, Art & Wardrobe Locker, Compute Economics Inspector */
    #modal-hud-command-palette,
    #modal-art-wardrobe-continuity,
    #modal-render-economics {
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(7, 8, 11, 0.9);
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
      z-index: 10050;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }
    .v216-modal-card {
      background: #0E1017;
      color: #F8FAFC;
      border: 1px solid #38BDF8;
      border-radius: 10px;
      width: 100%;
      max-width: 1040px;
      max-height: 90vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      box-shadow: 0 24px 60px rgba(0, 0, 0, 0.88);
    }
    .v216-palette-card {
      max-width: 760px;
    }
    .v216-modal-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      padding: 14px 20px;
      background: #141722;
      border-bottom: 1px solid #334155;
    }
    .v216-modal-title {
      margin: 0;
      font-family: 'Space Grotesk', sans-serif;
      font-size: 16px;
      font-weight: 700;
      color: #F8FAFC;
    }
    .v216-modal-sub {
      display: block;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      color: #38BDF8;
      margin-top: 2px;
    }
    .v216-close-btn {
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
    .v216-close-btn:hover,
    .v216-close-btn:focus-visible {
      background: #DC2626;
      outline: 2px solid #FFFFFF;
      outline-offset: 2px;
    }
    .v216-modal-body {
      padding: 18px 20px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }
    .v216-palette-search {
      width: 100%;
      box-sizing: border-box;
      padding: 10px 14px;
      border-radius: 6px;
      border: 1px solid #38BDF8;
      background: #07080B;
      color: #F8FAFC;
      font-family: 'JetBrains Mono', monospace;
      font-size: 13px;
    }
    .v216-palette-search:focus-visible {
      outline: 2px solid #FACC15;
      outline-offset: 2px;
    }
    .v216-palette-list {
      list-style: none;
      margin: 0;
      padding: 0;
      display: flex;
      flex-direction: column;
      gap: 6px;
      max-height: 55vh;
      overflow-y: auto;
    }
    .v216-palette-item {
      width: 100%;
      text-align: left;
      background: #141722;
      color: #F8FAFC;
      border: 1px solid #334155;
      border-radius: 6px;
      padding: 9px 12px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      cursor: pointer;
      font-family: 'Space Grotesk', sans-serif;
      font-size: 13px;
    }
    .v216-palette-item:hover,
    .v216-palette-item:focus-visible,
    .v216-palette-item.selected {
      background: #1E293B;
      border-color: #38BDF8;
      outline: 2px solid #38BDF8;
      outline-offset: 1px;
    }
    .v216-palette-meta {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .v216-kbd {
      background: #07080B;
      color: #FACC15;
      border: 1px solid #475569;
      border-radius: 4px;
      padding: 2px 7px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      font-weight: 700;
    }
    .v216-dept-tag {
      background: #0F172A;
      color: #93C5FD;
      border: 1px solid #334155;
      border-radius: 999px;
      padding: 2px 8px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 10px;
    }
    .v216-kpi-row {
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
    .v216-gauge-wrap {
      flex: 1 1 260px;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .v216-gauge-bar {
      width: 100%;
      height: 12px;
      background: #07080B;
      border: 1px solid #475569;
      border-radius: 999px;
      overflow: hidden;
    }
    .v216-gauge-fill {
      height: 100%;
      background: linear-gradient(90deg, #0284C7, #22D3EE);
      transition: width 0.2s ease;
    }
    .v216-badge {
      display: inline-block;
      padding: 3px 8px;
      border-radius: 4px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      font-weight: 700;
    }
    .v216-badge-pass {
      background: rgba(16, 185, 129, 0.16);
      color: #34D399;
      border: 1px solid #10B981;
    }
    .v216-badge-warn {
      background: rgba(245, 158, 11, 0.16);
      color: #FBBF24;
      border: 1px solid #F59E0B;
    }
    .v216-pill {
      display: inline-block;
      background: #1E293B;
      color: #38BDF8;
      border: 1px solid #38BDF8;
      border-radius: 4px;
      padding: 1px 6px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 10px;
      font-weight: 700;
    }
    .v216-code {
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      color: #FDE047;
    }
    .v216-sub {
      font-size: 11px;
      color: #CBD5E1;
    }
    .v216-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
    }
    .v216-table th,
    .v216-table td {
      border: 1px solid #334155;
      padding: 8px 10px;
      text-align: left;
      vertical-align: top;
    }
    .v216-table th {
      background: #1E293B;
      color: #F8FAFC;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
    }
    .v216-take-group {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }
    .v216-take-option {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      background: #07080B;
      border: 1px solid #475569;
      border-radius: 4px;
      padding: 4px 8px;
      cursor: pointer;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      color: #F8FAFC;
    }
    .v216-take-option:has(input:checked) {
      border-color: #38BDF8;
      background: rgba(56, 189, 248, 0.14);
    }
    .v216-actions-row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      justify-content: flex-end;
    }
    .v216-dl-btn {
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
    .v216-dl-btn:hover,
    .v216-dl-btn:focus-visible {
      background: #0284C7;
      outline: 2px solid #FACC15;
      outline-offset: 2px;
    }
    """

    modals_html = f"""
<!-- v2.16.0 Unified HUD Command Palette -->
<div id="modal-hud-command-palette" role="dialog" aria-modal="true" aria-labelledby="cmd-palette-title" tabindex="-1">
  <div class="v216-modal-card v216-palette-card">
    <div class="v216-modal-header">
      <div>
        <h2 id="cmd-palette-title" class="v216-modal-title">Unified HUD Command Palette</h2>
        <span class="v216-modal-sub">Type to filter departmental HUDs · Enter to launch · Esc to close [/]</span>
      </div>
      <button type="button" class="v216-close-btn" id="btn-cmd-palette-close" onclick="toggleHudCommandPalette(false)" aria-label="Close HUD Command Palette">Close [Esc]</button>
    </div>
    <div class="v216-modal-body">
      <input type="search" id="cmd-palette-search" class="v216-palette-search" placeholder="Search HUDs (e.g. Gaffer, LUT, Wardrobe, Compute, S3D, QC)..." aria-label="Search departmental HUDs" autocomplete="off">
      <div id="cmd-palette-count" class="v216-sub" aria-live="polite"></div>
      <ul id="cmd-palette-list" class="v216-palette-list" role="listbox" aria-label="Departmental HUD Launchers"></ul>
    </div>
  </div>
</div>

<!-- v2.16.0 Art & Wardrobe Continuity Locker -->
<div id="modal-art-wardrobe-continuity" role="dialog" aria-modal="true" aria-labelledby="art-wardrobe-title" tabindex="-1">
  <div class="v216-modal-card">
    <div class="v216-modal-header">
      <div>
        <h2 id="art-wardrobe-title" class="v216-modal-title">Art &amp; Wardrobe Continuity Locker</h2>
        <span class="v216-modal-sub">Per-Scene Look IDs, Prop Action-State Matrix &amp; Omni &lt;image_1..3&gt; Slot Contention [\\]</span>
      </div>
      <button type="button" class="v216-close-btn" id="btn-art-wardrobe-close" onclick="toggleArtWardrobeHUD(false)" aria-label="Close Art &amp; Wardrobe Continuity Locker">Close [Esc]</button>
    </div>
    <div class="v216-modal-body">
      <div class="v216-kpi-row">
        <div class="v216-gauge-wrap">
          <div class="v216-sub">Omni &lt;image_1..3&gt; Reference Slot Contention: <strong>{slots_used} / {slots_max}</strong> ({slot_pct}%)</div>
          <div class="v216-gauge-bar" role="progressbar" aria-label="Reference slot contention" aria-valuenow="{slots_used}" aria-valuemin="0" aria-valuemax="{slots_max}">
            <div class="v216-gauge-fill" style="width: {slot_pct}%;"></div>
          </div>
        </div>
        <div>
          <span class="v216-badge {continuity_badge_cls}">{html_escape(str(wardrobe_spec.get("continuity_status", "VERIFIED")))}</span>
        </div>
      </div>

      <table class="v216-table" aria-label="Per-Scene Wardrobe and Prop Action-State Matrix">
        <thead>
          <tr>
            <th>Scene</th>
            <th>Wardrobe Look ID &amp; Talent</th>
            <th>Hero Prop &amp; Action State</th>
            <th>Continuity Gate</th>
          </tr>
        </thead>
        <tbody>
          {wardrobe_tbody_html}
        </tbody>
      </table>

      <div class="v216-actions-row">
        <button type="button" class="v216-dl-btn" id="btn-dl-prop-csv" onclick="downloadPropContinuityCSV()">⤓ prop_continuity_matrix.csv</button>
        <button type="button" class="v216-dl-btn" id="btn-dl-art-pull-md" onclick="downloadArtPullListMD()">⤓ art_dept_pull_list.md</button>
      </div>
    </div>
  </div>
</div>

<!-- v2.16.0 Compute Economics & Take-Variant Inspector -->
<div id="modal-render-economics" role="dialog" aria-modal="true" aria-labelledby="render-economics-title" tabindex="-1">
  <div class="v216-modal-card">
    <div class="v216-modal-header">
      <div>
        <h2 id="render-economics-title" class="v216-modal-title">Compute Economics &amp; Take-Variant Inspector</h2>
        <span class="v216-modal-sub">2026 Gemini Model Matrix Spend, AI-vs-AICP Savings &amp; Take A/B/C Selector [;]</span>
      </div>
      <button type="button" class="v216-close-btn" id="btn-render-economics-close" onclick="toggleRenderEconomicsHUD(false)" aria-label="Close Compute Economics Inspector">Close [Esc]</button>
    </div>
    <div class="v216-modal-body">
      <div class="v216-kpi-row">
        <div class="v216-gauge-wrap">
          <div class="v216-sub">
            Estimated Spend: <strong id="v216-econ-spend">${est_spend:.2f}</strong> / Ceiling <strong id="v216-econ-ceiling">${budget_ceil:.2f}</strong>
            (<span id="v216-econ-pct">{spend_pct:.1f}%</span>)
          </div>
          <div class="v216-gauge-bar" id="v216-econ-progressbar" role="progressbar" aria-label="Estimated compute spend vs budget ceiling" aria-valuenow="{spend_pct:.1f}" aria-valuemin="0" aria-valuemax="100">
            <div class="v216-gauge-fill" id="v216-econ-progress-fill" style="width: {spend_pct:.1f}%;"></div>
          </div>
        </div>
        <div>
          <span class="v216-badge v216-badge-pass" id="v216-aicp-savings-badge">
            AI vs AICP (${aicp_base:,.0f}): {savings_pct:.2f}% Saved
          </span>
        </div>
      </div>

      <table class="v216-table" aria-label="2026 Gemini Model Matrix Cost Breakdown">
        <thead>
          <tr>
            <th>2026 Model ID</th>
            <th>Pipeline Role</th>
            <th>Calls</th>
            <th>Unit Cost</th>
            <th>Subtotal</th>
          </tr>
        </thead>
        <tbody id="v216-model-cost-tbody">
          {model_tbody_html}
        </tbody>
      </table>

      <table class="v216-table" aria-label="Per-Scene Take Variant Selector">
        <thead>
          <tr>
            <th>Scene</th>
            <th>Take A / B / C Variant</th>
            <th>Seed</th>
          </tr>
        </thead>
        <tbody>
          {take_tbody_html}
        </tbody>
      </table>

      <div class="v216-actions-row">
        <button type="button" class="v216-dl-btn" id="btn-dl-take-csv" onclick="downloadTakeVariantLedgerCSV()">⤓ take_variant_ledger.csv</button>
        <button type="button" class="v216-dl-btn" id="btn-dl-compute-md" onclick="downloadComputeEstimateMD()">⤓ ai_compute_estimate.md</button>
      </div>
    </div>
  </div>
</div>
"""

    js_template = """
    // v2.16.0 Unified HUD Command Palette, Art & Wardrobe Locker, Compute Economics Inspector
    const V216_WARDROBE_STATE = __WARDROBE_JSON__;
    const V216_ECON_STATE = __ECON_JSON__;

    let isHudCommandPaletteOpen = false;
    let lastCmdPaletteOpener = null;
    let isArtWardrobeHUDOpen = false;
    let lastArtWardrobeOpener = null;
    let isRenderEconomicsHUDOpen = false;
    let lastRenderEconomicsOpener = null;
    let _cmdPaletteSelectedIdx = 0;

    const V216_HUD_COMMANDS = [
      { id: 'cc', name: 'Closed Captions (CC)', dept: 'Delivery', key: 'C', fn: 'toggleCC' },
      { id: 'mixer', name: 'Audio Stem Console Mixer', dept: 'Audio', key: 'M', fn: 'toggleMixer' },
      { id: 'viewfinder', name: 'Optical Viewfinder & Safe Guides', dept: 'Camera', key: 'V', fn: 'toggleViewfinder' },
      { id: 'safeguides', name: 'SMPTE Safe Guides Overlay', dept: 'Camera', key: 'U', fn: 'toggleSafeGuides' },
      { id: 'vpstage', name: 'Virtual Production LED Stage', dept: 'Camera', key: 'P', fn: 'toggleVPStageModal' },
      { id: 'moco', name: 'Motion Control Trajectory', dept: 'Camera', key: 'K', fn: 'toggleMoCoHUD' },
      { id: 'gaffer', name: 'Studio Gaffer & Lighting Rig', dept: 'Lighting', key: 'G', fn: 'toggleGafferHUD' },
      { id: 'dof', name: 'Optical Depth of Field (DoF)', dept: 'Camera', key: 'F', fn: 'toggleDoFHUD' },
      { id: 'lut', name: 'DIT 3D LUT Color Suite', dept: 'Color', key: 'L', fn: 'toggleDitLutHUD' },
      { id: 'spatial', name: 'Spatial Audio 7.1.4 Soundfield', dept: 'Audio', key: 'S', fn: 'toggleSpatialHUD' },
      { id: 'vfx', name: 'Multi-Pass VFX Compositing', dept: 'VFX', key: 'X', fn: 'toggleVfxHUD' },
      { id: 'hdr', name: 'HDR10 / HLG Color Volume', dept: 'Color', key: 'H', fn: 'toggleHdrHUD' },
      { id: 'stripboard', name: '1st AD Stripboard Schedule', dept: 'Prep', key: 'B', fn: 'toggleStripboardHUD' },
      { id: 'film', name: 'Physical Film Stock Emulation', dept: 'Color', key: 'E', fn: 'toggleFilmHUD' },
      { id: 'slate', name: 'SMPTE 12M Clapper Slate', dept: 'Prep', key: 'T', fn: 'toggleSlateHUD' },
      { id: 'drone', name: 'Aerial Drone Flight Path', dept: 'Camera', key: 'D', fn: 'toggleDroneHUD' },
      { id: 'aicp', name: 'AICP Commercial Production Bid', dept: 'Budget', key: 'A', fn: 'toggleAicpHUD' },
      { id: 'reframe', name: 'Multi-Aspect Social Reframe', dept: 'Delivery', key: 'R', fn: 'toggleReframeHUD' },
      { id: 'qc', name: 'Broadcast QC & Clearances', dept: 'Delivery', key: 'Q', fn: 'toggleQcHUD' },
      { id: 'blocking', name: '180-Degree Continuity Blocking', dept: 'Camera', key: 'W', fn: 'toggleBlockingHUD' },
      { id: 'review', name: 'Client Review & Pin Annotations', dept: 'Review', key: 'N', fn: 'toggleReviewHUD' },
      { id: 'c2pa', name: 'C2PA Content Credentials', dept: 'Delivery', key: 'Y', fn: 'toggleC2paHUD' },
      { id: 'safety', name: 'On-Set Safety JSA & Exclusion', dept: 'Prep', key: 'Z', fn: 'toggleSafetyHUD' },
      { id: 'localization', name: 'Localization, ADR & Safe-Supers', dept: 'Delivery', key: 'I', fn: 'toggleLocalizationHUD' },
      { id: 'spotting', name: 'Editorial J/L-Cut Spotting', dept: 'Audio', key: 'J', fn: 'toggleSpottingHUD' },
      { id: 's3d', name: 'S3D Stereoscopy & MV-HEVC', dept: 'Camera', key: ']', fn: 'toggleS3dHUD' },
      { id: 'ad', name: 'Audio Description (AD) & CVAA', dept: 'Delivery', key: '[', fn: 'toggleAccessibilityAdHUD' },
      { id: 'art', name: 'Art & Wardrobe Continuity Locker', dept: 'Prep', key: '\\\\', fn: 'toggleArtWardrobeHUD' },
      { id: 'econ', name: 'Compute Economics & Take-Variant Inspector', dept: 'Budget', key: ';', fn: 'toggleRenderEconomicsHUD' },
      { id: 'motiongfx', name: 'Motion Graphics, Supers & End-Card Studio', dept: 'Color', key: '=', fn: 'toggleMotionGfxHUD' },
      { id: 'otiocoherence', name: 'OpenTimelineIO (.otio) & Cross-Dept Coherence Matrix', dept: 'Delivery', key: "'", fn: 'toggleOtioCoherenceHUD' }
    ];

    function _v216ShowToast(msg) {
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

    function _v216DownloadBlob(content, mime, filename, toastMsg) {
      const blob = new Blob([content], { type: mime });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      _v216ShowToast(toastMsg);
    }

    function _v216TrapFocus(modal) {
      if (!modal) return;
      modal.addEventListener('keydown', function(e) {
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

    function _getFilteredPaletteCommands(query) {
      const q = String(query || '').trim().toLowerCase();
      if (!q) return V216_HUD_COMMANDS.slice();
      return V216_HUD_COMMANDS.filter((cmd) => (
        cmd.name.toLowerCase().includes(q) ||
        cmd.dept.toLowerCase().includes(q) ||
        cmd.key.toLowerCase().includes(q)
      ));
    }

    function _launchPaletteCommand(cmd) {
      if (!cmd) return;
      toggleHudCommandPalette(false);
      const fn = window[cmd.fn];
      if (typeof fn === 'function') {
        fn();
      } else {
        _v216ShowToast('HUD unavailable: ' + cmd.name);
      }
    }

    function renderHudCommandPalette() {
      const input = document.getElementById('cmd-palette-search');
      const list = document.getElementById('cmd-palette-list');
      const countEl = document.getElementById('cmd-palette-count');
      if (!list) return;
      const items = _getFilteredPaletteCommands(input ? input.value : '');
      if (_cmdPaletteSelectedIdx >= items.length) _cmdPaletteSelectedIdx = 0;
      if (_cmdPaletteSelectedIdx < 0) _cmdPaletteSelectedIdx = Math.max(0, items.length - 1);

      while (list.firstChild) list.removeChild(list.firstChild);
      if (countEl) {
        countEl.textContent = items.length + ' departmental HUD' + (items.length === 1 ? '' : 's') + ' available';
      }

      if (!items.length) {
        const emptyLi = document.createElement('li');
        emptyLi.className = 'v216-sub';
        emptyLi.textContent = 'No matching HUD commands found.';
        list.appendChild(emptyLi);
        return;
      }

      items.forEach((cmd, idx) => {
        const li = document.createElement('li');
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'v216-palette-item' + (idx === _cmdPaletteSelectedIdx ? ' selected' : '');
        btn.setAttribute('role', 'option');
        btn.setAttribute('aria-selected', idx === _cmdPaletteSelectedIdx ? 'true' : 'false');
        btn.setAttribute('data-cmd-id', cmd.id);

        const left = document.createElement('span');
        left.textContent = cmd.name;

        const meta = document.createElement('span');
        meta.className = 'v216-palette-meta';
        const dept = document.createElement('span');
        dept.className = 'v216-dept-tag';
        dept.textContent = cmd.dept;
        const kbd = document.createElement('kbd');
        kbd.className = 'v216-kbd';
        kbd.textContent = cmd.key;
        meta.appendChild(dept);
        meta.appendChild(kbd);

        btn.appendChild(left);
        btn.appendChild(meta);
        btn.addEventListener('click', () => _launchPaletteCommand(cmd));
        li.appendChild(btn);
        list.appendChild(li);
      });
    }

    window.toggleHudCommandPalette = function(forceOpen) {
      const modal = document.getElementById('modal-hud-command-palette');
      const btn = document.getElementById('btn-command-palette-animatic');
      if (!modal) return;
      const shouldOpen = forceOpen !== undefined ? Boolean(forceOpen) : !isHudCommandPaletteOpen;
      if (!shouldOpen && !isHudCommandPaletteOpen) return;
      if (shouldOpen && typeof closeSecondaryOpenHUDs === 'function') closeSecondaryOpenHUDs();
      isHudCommandPaletteOpen = shouldOpen;
      if (btn) {
        btn.classList.toggle('active', shouldOpen);
        btn.setAttribute('aria-expanded', shouldOpen ? 'true' : 'false');
      }
      if (shouldOpen) {
        lastCmdPaletteOpener = document.activeElement;
        modal.style.display = 'flex';
        _cmdPaletteSelectedIdx = 0;
        const searchEl = document.getElementById('cmd-palette-search');
        if (searchEl) {
          searchEl.value = '';
          renderHudCommandPalette();
          searchEl.focus();
        } else {
          renderHudCommandPalette();
        }
        _v216ShowToast('⌘ Unified HUD Command Palette: ACTIVE [/]');
      } else {
        modal.style.display = 'none';
        if (lastCmdPaletteOpener && typeof lastCmdPaletteOpener.focus === 'function') lastCmdPaletteOpener.focus();
        else if (btn && typeof btn.focus === 'function') btn.focus();
      }
    };

    window.toggleArtWardrobeHUD = function(forceOpen) {
      const modal = document.getElementById('modal-art-wardrobe-continuity');
      const btn = document.getElementById('btn-art-dept-animatic');
      if (!modal) return;
      const shouldOpen = forceOpen !== undefined ? Boolean(forceOpen) : !isArtWardrobeHUDOpen;
      if (!shouldOpen && !isArtWardrobeHUDOpen) return;
      if (shouldOpen && typeof closeSecondaryOpenHUDs === 'function') closeSecondaryOpenHUDs();
      isArtWardrobeHUDOpen = shouldOpen;
      if (btn) {
        btn.classList.toggle('active', shouldOpen);
        btn.setAttribute('aria-expanded', shouldOpen ? 'true' : 'false');
      }
      if (shouldOpen) {
        lastArtWardrobeOpener = document.activeElement;
        modal.style.display = 'flex';
        const closeBtn = document.getElementById('btn-art-wardrobe-close');
        if (closeBtn) closeBtn.focus();
        _v216ShowToast('👗 Art & Wardrobe Continuity Locker: ACTIVE [\\\\]');
      } else {
        modal.style.display = 'none';
        if (lastArtWardrobeOpener && typeof lastArtWardrobeOpener.focus === 'function') lastArtWardrobeOpener.focus();
        else if (btn && typeof btn.focus === 'function') btn.focus();
      }
    };

    window.toggleRenderEconomicsHUD = function(forceOpen) {
      const modal = document.getElementById('modal-render-economics');
      const btn = document.getElementById('btn-economics-animatic');
      if (!modal) return;
      const shouldOpen = forceOpen !== undefined ? Boolean(forceOpen) : !isRenderEconomicsHUDOpen;
      if (!shouldOpen && !isRenderEconomicsHUDOpen) return;
      if (shouldOpen && typeof closeSecondaryOpenHUDs === 'function') closeSecondaryOpenHUDs();
      isRenderEconomicsHUDOpen = shouldOpen;
      if (btn) {
        btn.classList.toggle('active', shouldOpen);
        btn.setAttribute('aria-expanded', shouldOpen ? 'true' : 'false');
      }
      if (shouldOpen) {
        lastRenderEconomicsOpener = document.activeElement;
        modal.style.display = 'flex';
        const closeBtn = document.getElementById('btn-render-economics-close');
        if (closeBtn) closeBtn.focus();
        _v216ShowToast('💎 Compute Economics & Take-Variant Inspector: ACTIVE [;]');
      } else {
        modal.style.display = 'none';
        if (lastRenderEconomicsOpener && typeof lastRenderEconomicsOpener.focus === 'function') lastRenderEconomicsOpener.focus();
        else if (btn && typeof btn.focus === 'function') btn.focus();
      }
    };

    window.selectSceneTakeVariant = function(sceneIndex, takeKey) {
      const sceneRow = (V216_ECON_STATE.scene_takes || []).find((s) => Number(s.scene_index) === Number(sceneIndex));
      if (!sceneRow || !sceneRow.takes || !sceneRow.takes[takeKey]) return;
      sceneRow.selected_take = takeKey;
      const takeInfo = sceneRow.takes[takeKey];

      const seedEl = document.getElementById('v216-take-seed-' + sceneIndex);
      if (seedEl) seedEl.textContent = '#' + String(takeInfo.seed || 1001);

      let videoSpend = 0;
      (V216_ECON_STATE.scene_takes || []).forEach((s) => {
        const k = s.selected_take || 'A';
        const t = (s.takes && s.takes[k]) ? s.takes[k] : { cost_usd: 1.25 };
        videoSpend += Number(t.cost_usd || 0);
      });
      const totalSpend = Number(V216_ECON_STATE.fixed_pipeline_overhead_usd || 0) + videoSpend;
      V216_ECON_STATE.estimated_spend_usd = Math.round(totalSpend * 100) / 100;

      const ceiling = Math.max(1, Number(V216_ECON_STATE.budget_ceiling_usd || 25));
      const pct = Math.min(100, Math.max(0, Math.round((totalSpend / ceiling) * 1000) / 10));
      const spendEl = document.getElementById('v216-econ-spend');
      const pctEl = document.getElementById('v216-econ-pct');
      const barEl = document.getElementById('v216-econ-progressbar');
      const fillEl = document.getElementById('v216-econ-progress-fill');
      if (spendEl) spendEl.textContent = '$' + totalSpend.toFixed(2);
      if (pctEl) pctEl.textContent = pct.toFixed(1) + '%';
      if (barEl) barEl.setAttribute('aria-valuenow', pct.toFixed(1));
      if (fillEl) fillEl.style.width = pct.toFixed(1) + '%';

      const videoModelRow = document.querySelector('#v216-model-cost-tbody tr[data-model-id="gemini-omni-1.1-flash-preview"] .v216-model-subtotal');
      if (videoModelRow) videoModelRow.textContent = '$' + videoSpend.toFixed(2);

      const aicpBase = Math.max(1, Number(V216_ECON_STATE.aicp_traditional_baseline_usd || 48500));
      const savingsPct = Math.max(0, (1 - (totalSpend / aicpBase)) * 100);
      V216_ECON_STATE.ai_vs_aicp_savings_pct = Math.round(savingsPct * 100) / 100;
      const savingsBadge = document.getElementById('v216-aicp-savings-badge');
      if (savingsBadge) {
        savingsBadge.textContent = 'AI vs AICP ($' + Math.round(aicpBase).toLocaleString() + '): ' + savingsPct.toFixed(2) + '% Saved';
      }

      _v216ShowToast('Scene ' + String(sceneIndex).padStart(2, '0') + ' switched to Take ' + takeKey + ' ($' + Number(takeInfo.cost_usd || 0).toFixed(2) + ')');
    };

    function _csvCell(val) {
      const s = String(val == null ? '' : val);
      return '"' + s.replace(/"/g, '""') + '"';
    }

    window.downloadPropContinuityCSV = function() {
      const rows = [['Scene', 'Title', 'Character', 'Look_ID', 'Wardrobe_Spec', 'Prop', 'Prop_State', 'Ref_Slots_Used', 'Continuity_Break', 'Notes']];
      (V216_WARDROBE_STATE.scene_entries || []).forEach((r) => {
        rows.push([
          r.scene_index, r.scene_title, r.character, r.look_id, r.wardrobe_spec,
          r.prop_name, r.prop_state, r.reference_slots_used, r.continuity_break, r.continuity_note
        ]);
      });
      const csvStr = rows.map((r) => r.map(_csvCell).join(',')).join('\\n') + '\\n';
      _v216DownloadBlob(csvStr, 'text/csv;charset=utf-8;', 'prop_continuity_matrix.csv', 'Downloaded prop_continuity_matrix.csv');
    };

    window.downloadArtPullListMD = function() {
      const lines = [
        '# Art & Wardrobe Department Pull List: ' + (V216_WARDROBE_STATE.project_title || 'Omni Production'),
        '',
        '- **Continuity Status**: `' + (V216_WARDROBE_STATE.continuity_status || 'VERIFIED') + '`',
        '- **Omni Reference Slots Used**: `' + (V216_WARDROBE_STATE.reference_slots_used || 1) + ' / ' + (V216_WARDROBE_STATE.reference_slots_max || 3) + '`',
        '',
        '## Wardrobe Looks'
      ];
      (V216_WARDROBE_STATE.wardrobe_looks || []).forEach((lk) => {
        lines.push('- **' + lk.look_id + '** (' + lk.character + '): ' + lk.wardrobe_spec);
      });
      lines.push('', '## Per-Scene Prop & Continuity Matrix', '| Scene | Character | Look | Prop | State | Continuity |', '|---|---|---|---|---|---|');
      (V216_WARDROBE_STATE.scene_entries || []).forEach((r) => {
        lines.push('| S' + String(r.scene_index).padStart(2, '0') + ' | ' + r.character + ' | ' + r.look_id + ' | ' + r.prop_name + ' | `' + r.prop_state + '` | ' + (r.continuity_break ? 'BREAK RISK' : 'OK') + ' |');
      });
      _v216DownloadBlob(lines.join('\\n') + '\\n', 'text/markdown;charset=utf-8;', 'art_dept_pull_list.md', 'Downloaded art_dept_pull_list.md');
    };

    window.downloadTakeVariantLedgerCSV = function() {
      const rows = [['Scene', 'Title', 'Selected_Take', 'Label', 'Video_Cost_USD', 'Audit_Score', 'Seed']];
      (V216_ECON_STATE.scene_takes || []).forEach((sc) => {
        const k = sc.selected_take || 'A';
        const t = (sc.takes && sc.takes[k]) ? sc.takes[k] : {};
        rows.push([sc.scene_index, sc.scene_title, k, t.label || '', t.cost_usd || 1.25, t.audit_score || 94, t.seed || 1001]);
      });
      const csvStr = rows.map((r) => r.map(_csvCell).join(',')).join('\\n') + '\\n';
      _v216DownloadBlob(csvStr, 'text/csv;charset=utf-8;', 'take_variant_ledger.csv', 'Downloaded take_variant_ledger.csv');
    };

    window.downloadComputeEstimateMD = function() {
      const lines = [
        '# AI Compute Economics Estimate: ' + (V216_ECON_STATE.project_title || 'Omni Production'),
        '',
        '- **Estimated Spend**: `$' + Number(V216_ECON_STATE.estimated_spend_usd || 0).toFixed(2) + '`',
        '- **Budget Ceiling**: `$' + Number(V216_ECON_STATE.budget_ceiling_usd || 25).toFixed(2) + '`',
        '- **Traditional AICP Baseline**: `$' + Number(V216_ECON_STATE.aicp_traditional_baseline_usd || 48500).toFixed(2) + '`',
        '- **AI vs AICP Savings**: `' + Number(V216_ECON_STATE.ai_vs_aicp_savings_pct || 99.9).toFixed(2) + '%`',
        '',
        '## 2026 Model Matrix Breakdown',
        '| Model ID | Pipeline Role | Calls | Unit Cost | Subtotal |',
        '|---|---|---|---|---|'
      ];
      (V216_ECON_STATE.model_breakdown || []).forEach((m) => {
        lines.push('| `' + m.model_id + '` | ' + m.role + ' | ' + m.calls + ' | $' + Number(m.unit_cost_usd || 0).toFixed(2) + ' | $' + Number(m.subtotal_usd || 0).toFixed(2) + ' |');
      });
      _v216DownloadBlob(lines.join('\\n') + '\\n', 'text/markdown;charset=utf-8;', 'ai_compute_estimate.md', 'Downloaded ai_compute_estimate.md');
    };

    window.initV216HUDs = function() {
      const mPalette = document.getElementById('modal-hud-command-palette');
      const mArt = document.getElementById('modal-art-wardrobe-continuity');
      const mEcon = document.getElementById('modal-render-economics');
      _v216TrapFocus(mPalette);
      _v216TrapFocus(mArt);
      _v216TrapFocus(mEcon);

      const searchEl = document.getElementById('cmd-palette-search');
      if (searchEl) {
        searchEl.addEventListener('input', () => {
          _cmdPaletteSelectedIdx = 0;
          renderHudCommandPalette();
        });
        searchEl.addEventListener('keydown', (e) => {
          const items = _getFilteredPaletteCommands(searchEl.value);
          if (e.key === 'ArrowDown') {
            e.preventDefault();
            _cmdPaletteSelectedIdx = items.length ? (_cmdPaletteSelectedIdx + 1) % items.length : 0;
            renderHudCommandPalette();
          } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            _cmdPaletteSelectedIdx = items.length ? (_cmdPaletteSelectedIdx - 1 + items.length) % items.length : 0;
            renderHudCommandPalette();
          } else if (e.key === 'Enter' && items.length) {
            e.preventDefault();
            _launchPaletteCommand(items[_cmdPaletteSelectedIdx] || items[0]);
          }
        });
      }
      renderHudCommandPalette();
    };
    """

    scripts = (
        js_template
        .replace("__WARDROBE_JSON__", wardrobe_json)
        .replace("__ECON_JSON__", econ_json)
    )

    return {
        "css": css,
        "modals_html": modals_html,
        "scripts": scripts,
    }
