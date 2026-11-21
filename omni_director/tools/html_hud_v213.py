"""Modular v2.13.0 Dark-Room Cinema HUD Components (PM-FEAT-025 & PM-FEAT-026).

Provides Python 3.11-compatible builders for:
1. PM-FEAT-025: C2PA Content Credentials & Likeness Disclosure HUD (#animatic-c2pa-hud, [Y] hotkey)
2. PM-FEAT-026: On-Set Safety Risk & Exclusion-Zone HUD (#animatic-safety-hud, [Z] hotkey)
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from html import escape as html_escape
from typing import Any, Dict, List, Optional, Tuple

from omni_director.schemas import MasterProductionBible, ProductionBundle


def _escape_js_template_literal(text: str) -> str:
    """Escapes backslashes, backticks, template interpolations, and closing script tags for safe JS template literals."""
    escaped = text.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
    return re.sub(r"</(script)", r"<\/\1", escaped, flags=re.IGNORECASE)


def _escape_json_for_script(payload: Any) -> str:
    """Serializes JSON safely for embedding inside HTML <script> tags."""
    return re.sub(r"</(script)", r"<\/\1", json.dumps(payload), flags=re.IGNORECASE)


def _to_plain(obj: Any) -> Any:
    """Converts Pydantic models, enums, or nested objects into plain JSON-safe Python structures."""
    if obj is None:
        return None
    if hasattr(obj, "model_dump"):
        return _to_plain(obj.model_dump(mode="json"))
    if hasattr(obj, "value"):
        return obj.value
    if isinstance(obj, dict):
        return {k: _to_plain(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_plain(v) for v in obj]
    return obj


def _short_sha256(seed_text: str) -> str:
    return hashlib.sha256(seed_text.encode("utf-8")).hexdigest()


def _extract_ingredients(bible: MasterProductionBible) -> List[Dict[str, str]]:
    """Extracts up to 3 visual continuity <image_1-3> ingredient descriptors."""
    vcb = getattr(bible, "visual_continuity_bible", None)
    ingredients: List[Dict[str, str]] = []
    if vcb is not None:
        char_sheet = getattr(vcb, "character_sheet", None) or getattr(vcb, "character_bible", None)
        env_plate = getattr(vcb, "environment_plate", None) or getattr(vcb, "environment_bible", None)
        prop_plate = getattr(vcb, "prop_sheet", None) or getattr(vcb, "hero_keyframe", None)
        candidates = [
            ("<image_1>", "Character Continuity Sheet", str(char_sheet or "Hero Subject Reference")),
            ("<image_2>", "Environment Master Plate", str(env_plate or "Primary Stage Environment")),
            ("<image_3>", "Hero Keyframe / Prop Anchor", str(prop_plate or "Hero Product & Lighting Anchor")),
        ]
    else:
        candidates = [
            ("<image_1>", "Character Continuity Sheet", "Hero Subject Reference"),
            ("<image_2>", "Environment Master Plate", "Primary Stage Environment"),
            ("<image_3>", "Hero Keyframe / Prop Anchor", "Hero Product & Lighting Anchor"),
        ]
    for slot, label, desc in candidates:
        clean_desc = desc.strip()[:64] if desc.strip() else label
        if clean_desc.startswith("<svg"):
            clean_desc = f"{label} (Inline Vector Plate)"
        ingredients.append({
            "slot": slot,
            "label": label,
            "summary": clean_desc,
            "sha256": _short_sha256(f"{bible.project_title}:{slot}:{clean_desc}")[:16],
        })
    return ingredients


def _normalize_c2pa_state(
    bible: MasterProductionBible,
    scene_time_lookup: Dict[int, Tuple[float, float]],
) -> Dict[str, Any]:
    """Builds C2PA Content Credentials & Likeness state directly from MasterC2paProvenanceSpec or resilient defaults."""
    raw = _to_plain(getattr(bible, "master_c2pa_provenance", None)) or {}
    fallback_ingredients = _extract_ingredients(bible)
    scenes = getattr(bible, "scenes", []) or []

    def _map_ingredients(raw_ings: Any) -> List[Dict[str, str]]:
        mapped: List[Dict[str, str]] = []
        if not isinstance(raw_ings, list):
            return mapped
        for idx, item in enumerate(raw_ings[:3], start=1):
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or item.get("label") or f"<image_{idx}> Reference")
            tag_match = re.search(r"<image_[1-3]>", title)
            slot = str(item.get("slot") or (tag_match.group(0) if tag_match else f"<image_{idx}>"))
            mapped.append({
                "slot": slot,
                "label": title[:48],
                "summary": str(item.get("notes") or title)[:64],
                "sha256": str(item.get("hash_sha256") or item.get("sha256") or _short_sha256(title))[:16],
            })
        return mapped

    top_ingredients = _map_ingredients(raw.get("ingredients")) or fallback_ingredients
    manifest_id = str(raw.get("manifest_id") or f"urn:c2pa:omni-director:2026:{_short_sha256(bible.project_title)[:8]}")

    raw_scenes = raw.get("scene_provenances") or raw.get("scene_provenance") or raw.get("scenes") or []
    raw_by_idx: Dict[int, Dict[str, Any]] = {}
    for item in raw_scenes:
        if isinstance(item, dict) and "scene_index" in item:
            raw_by_idx[int(item["scene_index"])] = item

    scene_provenance: List[Dict[str, Any]] = []
    for pos, scene in enumerate(scenes, start=1):
        s_idx = int(getattr(scene, "scene_index", pos))
        st_s, en_s = scene_time_lookup.get(s_idx, ((s_idx - 1) * 5.0, s_idx * 5.0))
        override = raw_by_idx.get(s_idx, {})
        prompt_text = str(getattr(scene, "omni_prose_prompt", "") or getattr(scene, "scene_title", f"Scene {s_idx}"))
        prompt_hash = str(
            override.get("provenance_hash_sha256")
            or override.get("prompt_sha256")
            or _short_sha256(f"{s_idx}:{prompt_text}")
        )

        sc_ings = _map_ingredients(override.get("ingredients")) or top_ingredients
        ing_refs = override.get("ingredient_slots") or [ing["slot"] for ing in sc_ings]

        actions = override.get("actions") or raw.get("actions") or []
        action_models = [
            str(act.get("model_used"))
            for act in actions
            if isinstance(act, dict) and act.get("model_used")
        ]
        video_model = str(
            override.get("video_model")
            or next((m for m in action_models if "omni" in m), None)
            or (action_models[-1] if action_models else "gemini-omni-1.1-flash-preview")
        )
        director_model = str(
            override.get("director_model")
            or next((m for m in action_models if "argon" in m), "gemini-4-argon")
        )
        prompt_model = str(
            override.get("prompt_model")
            or next((m for m in action_models if "flash" in m and "omni" not in m), "gemini-3.8-flash")
        )
        image_model = str(
            override.get("image_model")
            or next((m for m in action_models if "image" in m), "gemini-3-pro-image")
        )

        synthid_flag = bool(
            override.get("watermark_c2pa_soft_binding", override.get("synthid_embedded", True))
        )
        art50_ok = bool(override.get("eu_ai_act_art50_compliant", raw.get("eu_ai_act_art50_compliant", True)))
        consent_ok = bool(override.get("consent_gate_passed", True))
        default_comp = "VERIFIED" if (art50_ok and consent_ok) else "HOLD"

        scene_provenance.append({
            "scene_index": s_idx,
            "scene_title": str(override.get("scene_title") or getattr(scene, "scene_title", f"Scene {s_idx}")),
            "start_sec": round(st_s, 3),
            "end_sec": round(en_s, 3),
            "director_model": director_model,
            "prompt_model": prompt_model,
            "image_model": image_model,
            "video_model": video_model,
            "prompt_sha256": prompt_hash,
            "ingredients": sc_ings,
            "ingredient_slots": list(ing_refs)[:3],
            "synthid_embedded": synthid_flag,
            "c2pa_assertion_id": str(override.get("c2pa_assertion_id") or f"{manifest_id}#s{s_idx:02d}-{prompt_hash[:8]}"),
            "compliance_status": str(override.get("compliance_status") or default_comp).upper(),
        })

    if not scene_provenance:
        fallback_hash = _short_sha256(bible.project_title)
        scene_provenance.append({
            "scene_index": 1,
            "scene_title": "Hero Sequence",
            "start_sec": 0.0,
            "end_sec": 5.0,
            "director_model": "gemini-4-argon",
            "prompt_model": "gemini-3.8-flash",
            "image_model": "gemini-3-pro-image",
            "video_model": "gemini-omni-1.1-flash-preview",
            "prompt_sha256": fallback_hash,
            "ingredients": top_ingredients,
            "ingredient_slots": [ing["slot"] for ing in top_ingredients],
            "synthid_embedded": True,
            "c2pa_assertion_id": f"{manifest_id}#s01-{fallback_hash[:8]}",
            "compliance_status": "VERIFIED",
        })

    # Collect TalentLikenessRecordSpec from master and per-scene provenances
    raw_likeness_pool: List[Dict[str, Any]] = []
    seen_rec_ids: set[str] = set()
    for src_list in (
        [raw.get("talent_likeness_records"), raw.get("likeness_records"), raw.get("talent_consents")]
        + [sp.get("talent_likeness_records") for sp in raw_scenes if isinstance(sp, dict)]
    ):
        if not isinstance(src_list, list):
            continue
        for rec in src_list:
            if not isinstance(rec, dict):
                continue
            rid = str(rec.get("record_id") or "")
            if rid and rid in seen_rec_ids:
                continue
            if rid:
                seen_rec_ids.add(rid)
            raw_likeness_pool.append(rec)

    likeness_records: List[Dict[str, Any]] = []
    if raw_likeness_pool:
        for idx, rec in enumerate(raw_likeness_pool, start=1):
            char_name = str(rec.get("character_name") or rec.get("role_label") or "Principal")
            perf_name = rec.get("performer_name") or rec.get("subject_name") or rec.get("talent_name")
            if perf_name and char_name and str(perf_name) != char_name:
                subj_label = f"{perf_name} ({char_name})"
            else:
                subj_label = str(perf_name or char_name)
            if rec.get("replica_class"):
                rep_class = str(rec["replica_class"])
            elif rec.get("is_digital_replica"):
                rep_class = "Licensed Digital Replica"
            elif rec.get("is_human_likeness"):
                rep_class = "Human Likeness"
            else:
                rep_class = "Original Composite Persona"
            likeness_records.append({
                "record_id": str(rec.get("record_id") or f"LIKENESS-{idx:03d}"),
                "subject_name": subj_label,
                "role_label": char_name,
                "replica_class": rep_class,
                "sag_aftra_rider": str(
                    rec.get("consent_reference_id")
                    or rec.get("sag_aftra_rider")
                    or rec.get("union_jurisdiction")
                    or "SAG-AFTRA / EU AI Act Art. 50"
                ),
                "consent_status": str(rec.get("consent_status") or "VERIFIED_CONSENT").upper(),
                "territory": str(rec.get("territory") or "Worldwide"),
            })
    else:
        chars = getattr(bible, "characters", None) or []
        for idx, ch in enumerate(chars, start=1):
            ch_name = str(getattr(ch, "name", None) or getattr(ch, "character_name", None) or f"Character {idx}")
            ch_role = str(getattr(ch, "role", None) or "Cast Subject")
            likeness_records.append({
                "record_id": f"LIKENESS-{idx:03d}",
                "subject_name": ch_name,
                "role_label": ch_role,
                "replica_class": "Original Composite Persona",
                "sag_aftra_rider": "SYNTHETIC-NO-BIOMETRIC-MATCH",
                "consent_status": "ORIGINAL_COMPOSITE_PERSONA",
                "territory": "Worldwide",
            })
        if not likeness_records:
            likeness_records.append({
                "record_id": "LIKENESS-001",
                "subject_name": "Zero Human Biometric Subjects",
                "role_label": "Product / Environment Focus",
                "replica_class": "Non-Biometric Synthetic Scene",
                "sag_aftra_rider": "SAG-AFTRA-EXEMPT-NON-HUMAN",
                "consent_status": "SYNTHETIC_NON_HUMAN",
                "territory": "Worldwide",
            })

    blocked = any(
        r["consent_status"] in ("BLOCKED", "MISSING", "REVOKED", "PENDING_CONSENT")
        for r in likeness_records
    )
    if "all_likeness_consents_verified" in raw:
        likeness_gate = "CLEARED" if (bool(raw["all_likeness_consents_verified"]) and not blocked) else "BLOCKED"
    else:
        likeness_gate = str(raw.get("likeness_gate") or ("BLOCKED" if blocked else "CLEARED")).upper()

    raw_ver = str(raw.get("c2pa_spec_version") or raw.get("c2pa_version") or "2.1")
    c2pa_version = raw_ver if raw_ver.lower().startswith("v") else f"v{raw_ver}"
    disclosure_tier = str(raw.get("synthetic_tier") or raw.get("disclosure_tier") or "FULL_AI_SYNTHETIC").upper()
    art50_compliant = bool(raw.get("eu_ai_act_art50_compliant", True))
    art50_label = str(raw.get("eu_ai_act_art50") or ("PASS" if art50_compliant else "REVIEW")).upper()
    synthid_active = bool(
        raw.get("synthid_active", any(sp.get("synthid_embedded", True) for sp in scene_provenance))
    )

    return {
        "project_title": str(raw.get("project_title") or bible.project_title),
        "c2pa_version": c2pa_version,
        "disclosure_tier": disclosure_tier,
        "synthid_active": synthid_active,
        "eu_ai_act_art50": art50_label,
        "model_matrix_verified": bool(raw.get("model_matrix_verified", True)),
        "likeness_gate": likeness_gate,
        "manifest_id": manifest_id,
        "ingredients": top_ingredients,
        "scene_provenance": scene_provenance,
        "likeness_records": likeness_records,
    }


def _normalize_safety_state(
    bible: MasterProductionBible,
    scene_time_lookup: Dict[int, Tuple[float, float]],
) -> Dict[str, Any]:
    """Builds On-Set Safety Risk & Exclusion-Zone JSA state directly from MasterSafetyRiskSpec or resilient defaults."""
    raw = _to_plain(getattr(bible, "master_safety_risk", None)) or {}
    scenes = getattr(bible, "scenes", []) or []

    _CAT_BULLETIN_MAP = {
        "kinetic_moco_arm": "CSATF #39 (MoCo)",
        "stunt_vehicle": "CSATF #36 (Stunt Vehicle)",
        "aerial_uav": "CSATF #23 (UAV)",
        "pyro_atmospheric_sfx": "CSATF #16 (Pyro)",
        "wire_rigging_height": "CSATF #14 (Rigging)",
        "electrical_dmx_wet": "CSATF #06 (Electrical)",
        "laser_optical": "CSATF #25 (Laser)",
        "food_allergen_thermal": "CSATF #01 (Thermal/Culinary)",
    }

    def _extract_bulletin(cat_raw: str, notes: str) -> str:
        m = re.search(r"CSATF[^.;)]*", notes or "", re.IGNORECASE)
        if m:
            return m.group(0).strip()
        return _CAT_BULLETIN_MAP.get(cat_raw.lower(), "CSATF #14 (Rigging)")

    # Primary path: Wave 2 MasterSafetyRiskSpec (`scene_safety_specs` + `standby_emergency`)
    raw_scene_specs = raw.get("scene_safety_specs") or []
    raw_spec_by_idx: Dict[int, Dict[str, Any]] = {
        int(ss["scene_index"]): ss
        for ss in raw_scene_specs
        if isinstance(ss, dict) and "scene_index" in ss
    }

    raw_zones = raw.get("scene_exclusion_zones") or raw.get("scene_zones") or []
    zone_by_idx: Dict[int, Dict[str, Any]] = {
        int(z["scene_index"]): z
        for z in raw_zones
        if isinstance(z, dict) and "scene_index" in z
    }

    hazard_records: List[Dict[str, Any]] = []
    scene_zones: List[Dict[str, Any]] = []

    if raw_spec_by_idx:
        ordered_indices = sorted(raw_spec_by_idx.keys())
        for s_idx in ordered_indices:
            ss = raw_spec_by_idx[s_idx]
            st_s, en_s = scene_time_lookup.get(s_idx, ((s_idx - 1) * 5.0, s_idx * 5.0))
            sc_hazards = ss.get("hazards") or []
            inner_r = float(ss.get("max_exclusion_zone_m") or 3.0)
            buffer_r = round(max(inner_r + 2.0, inner_r * 1.6), 1)
            safe_r = round(max(buffer_r + 3.0, inner_r * 2.4), 1)

            if sc_hazards and isinstance(sc_hazards[0], dict):
                top_h = max(sc_hazards, key=lambda h: float(h.get("exclusion_zone_m") or 0.0))
                cat_raw = str(top_h.get("category") or "rigging")
                primary_cat = cat_raw.replace("_", " ").title()
                ppe_list = top_h.get("ppe_required") or []
                ppe_str = ", ".join(str(p) for p in ppe_list) if isinstance(ppe_list, list) else str(ppe_list)
                bulletin = _extract_bulletin(cat_raw, str(top_h.get("notes") or ""))
                notes_str = str(ss.get("jsa_notes") or top_h.get("hazard_description") or "")
            else:
                primary_cat = "Stage Perimeter"
                ppe_str = "High-visibility stage vest, ANSI Z87.1 eyewear"
                bulletin = "CSATF #14 (Rigging)"
                notes_str = str(ss.get("jsa_notes") or f"Enforce {inner_r:.1f}m exclusion zone.")

            scene_zones.append({
                "scene_index": s_idx,
                "scene_title": str(ss.get("scene_title") or f"Scene {s_idx}"),
                "start_sec": round(st_s, 3),
                "end_sec": round(en_s, 3),
                "hazard_category": primary_cat,
                "inner_keepout_m": round(inner_r, 1),
                "amber_buffer_m": buffer_r,
                "green_safe_m": safe_r,
                "ppe_required": ppe_str or "Standard Stage PPE",
                "csatf_bulletin": bulletin,
                "mitigation_notes": notes_str or f"Enforce {inner_r:.1f}m red keep-out perimeter.",
            })

            for hz in sc_hazards:
                if not isinstance(hz, dict):
                    continue
                cat_raw = str(hz.get("category") or "general_stage")
                ppe_list = hz.get("ppe_required") or []
                ppe_txt = ", ".join(str(p) for p in ppe_list) if isinstance(ppe_list, list) else str(ppe_list)
                hazard_records.append({
                    "hazard_id": str(hz.get("hazard_id") or f"HAZ-S{s_idx:02d}"),
                    "scene_index": s_idx,
                    "category": cat_raw.replace("_", " ").title(),
                    "hazard_summary": str(hz.get("hazard_description") or hz.get("hazard_summary") or "Controlled stage hazard"),
                    "pre_risk": str(hz.get("risk_level") or "MODERATE").upper(),
                    "residual_risk": str(hz.get("residual_risk_level") or "LOW").upper(),
                    "exclusion_m": round(float(hz.get("exclusion_zone_m") or inner_r), 1),
                    "ppe": ppe_txt or "Standard Stage PPE",
                    "csatf_bulletin": _extract_bulletin(cat_raw, str(hz.get("notes") or "")),
                })
    else:
        raw_hazards = raw.get("hazard_records") or raw.get("jsa_hazards") or []
        for pos, scene in enumerate(scenes, start=1):
            s_idx = int(getattr(scene, "scene_index", pos))
            st_s, en_s = scene_time_lookup.get(s_idx, ((s_idx - 1) * 5.0, s_idx * 5.0))
            prose = (str(getattr(scene, "omni_prose_prompt", "")) + " " + str(getattr(scene, "scene_title", ""))).lower()
            has_drone = bool(getattr(scene, "drone_flight", None)) or any(k in prose for k in ("drone", "uav", "aerial", "fpv"))
            has_moco = bool(getattr(scene, "moco_keyframes", None)) or any(k in prose for k in ("moco", "robotic", "arm", "bolt", "high-speed"))
            has_pyro = any(k in prose for k in ("fire", "flame", "spark", "pyro", "smoke", "laser", "torch"))
            has_water = any(k in prose for k in ("water", "rain", "ocean", "pool", "wet", "steam"))

            if has_drone:
                inner_r, buffer_r, safe_r = 12.0, 22.0, 32.0
                primary_cat = "UAV / Aerial Flight"
                ppe = "Hardhat, Hi-Vis Vest, Eye Protection"
                bulletin = "CSATF #23 (UAV)"
            elif has_pyro:
                inner_r, buffer_r, safe_r = 10.0, 18.0, 26.0
                primary_cat = "Pyrotechnics & Thermal"
                ppe = "Nomex FR Suit, Face Shield, CO2 Extinguisher"
                bulletin = "CSATF #16 (Pyro)"
            elif has_moco:
                inner_r, buffer_r, safe_r = 5.0, 9.0, 14.0
                primary_cat = "Motion Control / Robotics"
                ppe = "Steel-Toe Boots, E-Stop Tether, Eye Protection"
                bulletin = "CSATF #39 (MoCo)"
            elif has_water:
                inner_r, buffer_r, safe_r = 4.0, 8.0, 12.0
                primary_cat = "Wet Set & GFCI Electrical"
                ppe = "Insulated Footwear, GFCI Drops, Non-Slip Mats"
                bulletin = "CSATF #06 (Electrical)"
            else:
                inner_r, buffer_r, safe_r = 3.0, 6.0, 10.0
                primary_cat = "Rigging & Grip Perimeter"
                ppe = "Closed-Toe Footwear, Work Gloves, Safety Glasses"
                bulletin = "CSATF #14 (Rigging)"

            z_over = zone_by_idx.get(s_idx, {})
            inner_r = float(z_over.get("inner_keepout_m", inner_r))
            buffer_r = float(z_over.get("amber_buffer_m", buffer_r))
            safe_r = float(z_over.get("green_safe_m", safe_r))
            scene_zones.append({
                "scene_index": s_idx,
                "scene_title": str(getattr(scene, "scene_title", f"Scene {s_idx}")),
                "start_sec": round(st_s, 3),
                "end_sec": round(en_s, 3),
                "hazard_category": str(z_over.get("hazard_category") or primary_cat),
                "inner_keepout_m": round(inner_r, 1),
                "amber_buffer_m": round(buffer_r, 1),
                "green_safe_m": round(safe_r, 1),
                "ppe_required": str(z_over.get("ppe_required") or ppe),
                "csatf_bulletin": str(z_over.get("csatf_bulletin") or bulletin),
                "mitigation_notes": str(
                    z_over.get("mitigation_notes")
                    or f"Enforce {inner_r:.1f}m red keep-out perimeter; stage non-essential crew outside {safe_r:.1f}m video village boundary."
                ),
            })

        if raw_hazards:
            for idx, hz in enumerate(raw_hazards, start=1):
                if not isinstance(hz, dict):
                    continue
                hazard_records.append({
                    "hazard_id": str(hz.get("hazard_id") or f"JSA-{idx:02d}"),
                    "scene_index": int(hz.get("scene_index") or 1),
                    "category": str(hz.get("category") or "General Stage"),
                    "hazard_summary": str(hz.get("hazard_summary") or hz.get("description") or "Controlled production hazard"),
                    "pre_risk": str(hz.get("pre_risk") or "MEDIUM").upper(),
                    "residual_risk": str(hz.get("residual_risk") or "LOW").upper(),
                    "exclusion_m": float(hz.get("exclusion_m") or 5.0),
                    "ppe": str(hz.get("ppe") or "Standard Stage PPE"),
                    "csatf_bulletin": str(hz.get("csatf_bulletin") or "CSATF #14"),
                })

    if not scene_zones:
        scene_zones.append({
            "scene_index": 1,
            "scene_title": "Hero Stage",
            "start_sec": 0.0,
            "end_sec": 5.0,
            "hazard_category": "Rigging & Grip Perimeter",
            "inner_keepout_m": 3.0,
            "amber_buffer_m": 6.0,
            "green_safe_m": 10.0,
            "ppe_required": "Closed-Toe Footwear, Safety Glasses",
            "csatf_bulletin": "CSATF #14 (Rigging)",
            "mitigation_notes": "Enforce 3.0m red keep-out perimeter around overhead trussing.",
        })

    if not hazard_records:
        for sz in scene_zones:
            pre_r = "HIGH" if sz["inner_keepout_m"] >= 8.0 else "MODERATE"
            hazard_records.append({
                "hazard_id": f"JSA-S{sz['scene_index']:02d}",
                "scene_index": sz["scene_index"],
                "category": sz["hazard_category"],
                "hazard_summary": sz["mitigation_notes"],
                "pre_risk": pre_r,
                "residual_risk": "LOW",
                "exclusion_m": sz["inner_keepout_m"],
                "ppe": sz["ppe_required"],
                "csatf_bulletin": sz["csatf_bulletin"],
            })

    standby_raw = raw.get("standby_emergency") or {}
    if not isinstance(standby_raw, dict):
        standby_raw = {}

    max_radius = max([sz["inner_keepout_m"] for sz in scene_zones] + [float(raw.get("max_exclusion_radius_m") or 0.0)])
    unmitigated = int(
        raw.get(
            "open_holds_count",
            raw.get("unmitigated_critical_count", sum(1 for h in hazard_records if h["residual_risk"] in ("CRITICAL", "HIGH"))),
        )
    )
    raw_signoff = raw.get("signoff_status") or raw.get("clearance_status")
    if raw_signoff:
        clearance_status = str(raw_signoff).replace("_", " ").upper()
    else:
        clearance_status = "HOLD REQUIRED" if unmitigated > 0 else "CLEARED"

    standby_medic = bool(standby_raw.get("set_medic_on_standby", raw.get("standby_medic", True)))
    fire_marshal = bool(
        standby_raw.get(
            "fire_safety_officer_required",
            raw.get("fire_marshal", any("pyro" in sz["hazard_category"].lower() for sz in scene_zones)),
        )
    )
    radio_channel = str(standby_raw.get("emergency_radio_channel") or raw.get("radio_channel") or "CH-09 SAFETY")

    return {
        "project_title": str(raw.get("project_title") or bible.project_title),
        "clearance_status": clearance_status,
        "max_exclusion_radius_m": round(max_radius, 1),
        "unmitigated_critical_count": unmitigated,
        "standby_medic": standby_medic,
        "fire_marshal": fire_marshal,
        "radio_channel": radio_channel,
        "scene_exclusion_zones": scene_zones,
        "hazard_records": hazard_records,
    }


def _build_disclosure_markdown(c2pa_state: Dict[str, Any]) -> str:
    def _esc_md(val: Any) -> str:
        return str(val or "").replace("|", "\\|").replace("\r", " ").replace("\n", " ")

    lines = [
        f"# EU AI Act Article 50 & C2PA Content Credentials Disclosure: {_esc_md(c2pa_state['project_title'])}",
        "",
        f"- **Manifest ID**: `{_esc_md(c2pa_state['manifest_id'])}`",
        f"- **C2PA Spec**: `{_esc_md(c2pa_state['c2pa_version'])}`",
        f"- **Disclosure Tier**: `{_esc_md(c2pa_state['disclosure_tier'])}`",
        f"- **SynthID Watermark**: `{'ACTIVE' if c2pa_state['synthid_active'] else 'INACTIVE'}`",
        f"- **EU AI Act Art. 50**: `{_esc_md(c2pa_state['eu_ai_act_art50'])}`",
        f"- **2026 Model Matrix**: `{'VERIFIED' if c2pa_state['model_matrix_verified'] else 'UNVERIFIED'}`",
        f"- **Likeness Gate**: `{_esc_md(c2pa_state['likeness_gate'])}`",
        "",
        "## Per-Scene Provenance & Cryptographic Digests",
        "| Scene | Title | Output Video Model | Prompt SHA-256 | SynthID | Status |",
        "|---|---|---|---|---|---|",
    ]
    for sp in c2pa_state["scene_provenance"]:
        lines.append(
            f"| {sp['scene_index']} | {_esc_md(sp['scene_title'])} | `{_esc_md(sp['video_model'])}` | "
            f"`{sp['prompt_sha256'][:16]}...` | `{'ACTIVE' if sp['synthid_embedded'] else 'OFF'}` | `{_esc_md(sp['compliance_status'])}` |"
        )
    lines.extend([
        "",
        "## Talent Likeness & SAG-AFTRA Digital Replica Ledger",
        "| Record | Subject | Role | Class | SAG-AFTRA Rider | Status |",
        "|---|---|---|---|---|---|",
    ])
    for lr in c2pa_state["likeness_records"]:
        lines.append(
            f"| `{_esc_md(lr['record_id'])}` | {_esc_md(lr['subject_name'])} | {_esc_md(lr['role_label'])} | "
            f"{_esc_md(lr['replica_class'])} | `{_esc_md(lr['sag_aftra_rider'])}` | `{_esc_md(lr['consent_status'])}` |"
        )
    return "\n".join(lines) + "\n"


def _build_likeness_csv(c2pa_state: Dict[str, Any]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["record_id", "subject_name", "role_label", "replica_class", "sag_aftra_rider", "consent_status", "territory"])
    for lr in c2pa_state["likeness_records"]:
        writer.writerow([
            lr["record_id"],
            lr["subject_name"],
            lr["role_label"],
            lr["replica_class"],
            lr["sag_aftra_rider"],
            lr["consent_status"],
            lr["territory"],
        ])
    return buf.getvalue()


def _build_safety_markdown(safety_state: Dict[str, Any]) -> str:
    def _esc_md(val: Any) -> str:
        return str(val or "").replace("|", "\\|").replace("\r", " ").replace("\n", " ")

    lines = [
        f"# On-Set Safety JSA & Exclusion-Zone Report: {_esc_md(safety_state['project_title'])}",
        "",
        f"- **Clearance Status**: `{_esc_md(safety_state['clearance_status'])}`",
        f"- **Max Keep-Out Radius**: `{safety_state['max_exclusion_radius_m']}m`",
        f"- **Unmitigated Criticals**: `{safety_state['unmitigated_critical_count']}`",
        f"- **Standby Medic**: `{'ON SITE' if safety_state['standby_medic'] else 'ON CALL'}`",
        f"- **Fire Marshal**: `{'ASSIGNED' if safety_state['fire_marshal'] else 'NOT REQUIRED'}`",
        f"- **Safety Radio Channel**: `{_esc_md(safety_state['radio_channel'])}`",
        "",
        "## Hazard Control Matrix",
        "| ID | Scene | Category | Pre-Risk | Residual | Exclusion (m) | PPE | CSATF Bulletin |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for hz in safety_state["hazard_records"]:
        lines.append(
            f"| `{_esc_md(hz['hazard_id'])}` | {hz['scene_index']} | {_esc_md(hz['category'])} | "
            f"`{_esc_md(hz['pre_risk'])}` | `{_esc_md(hz['residual_risk'])}` | {hz['exclusion_m']}m | "
            f"{_esc_md(hz['ppe'])} | `{_esc_md(hz['csatf_bulletin'])}` |"
        )
    return "\n".join(lines) + "\n"


def _build_safety_csv(safety_state: Dict[str, Any]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["hazard_id", "scene_index", "category", "hazard_summary", "pre_risk", "residual_risk", "exclusion_m", "ppe", "csatf_bulletin"])
    for hz in safety_state["hazard_records"]:
        writer.writerow([
            hz["hazard_id"],
            hz["scene_index"],
            hz["category"],
            hz["hazard_summary"],
            hz["pre_risk"],
            hz["residual_risk"],
            hz["exclusion_m"],
            hz["ppe"],
            hz["csatf_bulletin"],
        ])
    return buf.getvalue()


def build_v213_hud_bundle(
    bible: MasterProductionBible,
    bundle: ProductionBundle,
    scene_time_lookup: Dict[int, Tuple[float, float]],
    total_runtime_sec: float,
) -> Dict[str, str]:
    """Builds CSS, modals HTML, and JS for PM-FEAT-025 (C2PA) and PM-FEAT-026 (On-Set Safety JSA)."""
    del bundle, total_runtime_sec
    c2pa_state = _normalize_c2pa_state(bible, scene_time_lookup)
    safety_state = _normalize_safety_state(bible, scene_time_lookup)

    c2pa_json_escaped = _escape_js_template_literal(json.dumps(c2pa_state, indent=2))
    c2pa_md_escaped = _escape_js_template_literal(_build_disclosure_markdown(c2pa_state))
    c2pa_csv_escaped = _escape_js_template_literal(_build_likeness_csv(c2pa_state))
    c2pa_state_json = _escape_json_for_script(c2pa_state)

    safety_json_escaped = _escape_js_template_literal(json.dumps(safety_state, indent=2))
    safety_md_escaped = _escape_js_template_literal(_build_safety_markdown(safety_state))
    safety_csv_escaped = _escape_js_template_literal(_build_safety_csv(safety_state))
    safety_state_json = _escape_json_for_script(safety_state)

    # C2PA status pills
    synthid_cls = "c2pa-badge-pass" if c2pa_state["synthid_active"] else "c2pa-badge-warn"
    synthid_lbl = "ACTIVE" if c2pa_state["synthid_active"] else "INACTIVE"
    art50_cls = "c2pa-badge-pass" if c2pa_state["eu_ai_act_art50"] == "PASS" else "c2pa-badge-warn"
    matrix_cls = "c2pa-badge-pass" if c2pa_state["model_matrix_verified"] else "c2pa-badge-fail"
    matrix_lbl = "VERIFIED" if c2pa_state["model_matrix_verified"] else "REVIEW"
    likeness_cls = "c2pa-badge-pass" if c2pa_state["likeness_gate"] == "CLEARED" else "c2pa-badge-fail"

    c2pa_scene_pills = "".join([
        f'<button type="button" class="btn-c2pa-scene{" active" if idx == 0 else ""}" '
        f'data-scene-index="{sp["scene_index"]}" onclick="selectC2paScene({sp["scene_index"]})">'
        f'S{sp["scene_index"]:02d}: {html_escape(sp["scene_title"][:20])}</button>'
        for idx, sp in enumerate(c2pa_state["scene_provenance"])
    ])

    c2pa_scene_rows = "".join([
        f'<tr class="c2pa-scene-row{" active-row" if idx == 0 else ""}" data-scene-index="{sp["scene_index"]}" '
        f'tabindex="0" onclick="selectC2paScene({sp["scene_index"]})" '
        f'onkeydown="if(event.key===\'Enter\'||event.key===\' \'||event.code===\'Space\'){{event.preventDefault();event.stopPropagation();selectC2paScene({sp["scene_index"]});}}">'
        f'<td><strong>S{sp["scene_index"]:02d}</strong></td>'
        f'<td><code>{html_escape(sp["video_model"])}</code></td>'
        f'<td><code>{html_escape(sp["prompt_sha256"][:14])}…</code></td>'
        f'<td>{html_escape(", ".join(sp["ingredient_slots"]))}</td>'
        f'<td><span class="c2pa-badge {"c2pa-badge-pass" if sp["synthid_embedded"] else "c2pa-badge-warn"}">{"ON" if sp["synthid_embedded"] else "OFF"}</span></td>'
        f'<td><span class="c2pa-badge c2pa-badge-pass">{html_escape(sp["compliance_status"])}</span></td>'
        f'</tr>'
        for idx, sp in enumerate(c2pa_state["scene_provenance"])
    ])

    c2pa_likeness_rows = "".join([
        f'<tr>'
        f'<td><code>{html_escape(lr["record_id"])}</code></td>'
        f'<td>{html_escape(lr["subject_name"])}</td>'
        f'<td>{html_escape(lr["replica_class"])}</td>'
        f'<td><code>{html_escape(lr["sag_aftra_rider"])}</code></td>'
        f'<td><span class="c2pa-badge {"c2pa-badge-pass" if lr["consent_status"] in ("CLEARED", "VERIFIED_CONSENT", "SYNTHETIC_NON_HUMAN", "ORIGINAL_COMPOSITE_PERSONA") else ("c2pa-badge-warn" if lr["consent_status"] == "PENDING_CONSENT" else "c2pa-badge-fail")}">{html_escape(lr["consent_status"])}</span></td>'
        f'</tr>'
        for lr in c2pa_state["likeness_records"]
    ])

    # Safety status pills
    clearance_cls = "safety-badge-pass" if safety_state["clearance_status"] in ("CLEARED", "MITIGATED") else "safety-badge-fail"
    crit_cls = "safety-badge-pass" if safety_state["unmitigated_critical_count"] == 0 else "safety-badge-fail"
    medic_cls = "safety-badge-pass" if safety_state["standby_medic"] else "safety-badge-warn"
    marshal_cls = "safety-badge-pass" if safety_state["fire_marshal"] else "safety-badge-muted"

    safety_scene_pills = "".join([
        f'<button type="button" class="btn-safety-scene{" active" if idx == 0 else ""}" '
        f'data-scene-index="{sz["scene_index"]}" onclick="selectSafetyScene({sz["scene_index"]})">'
        f'S{sz["scene_index"]:02d}: {sz["inner_keepout_m"]:.1f}m</button>'
        for idx, sz in enumerate(safety_state["scene_exclusion_zones"])
    ])

    safety_hazard_rows = "".join([
        f'<tr class="safety-hazard-row{" active-row" if hz["scene_index"] == safety_state["scene_exclusion_zones"][0]["scene_index"] else ""}" '
        f'data-scene-index="{hz["scene_index"]}">'
        f'<td><strong>S{hz["scene_index"]:02d}</strong><br><code>{html_escape(hz["hazard_id"])}</code></td>'
        f'<td><strong>{html_escape(hz["category"])}</strong><br><span class="safety-subtext">{html_escape(hz["hazard_summary"][:96])}</span></td>'
        f'<td><span class="safety-badge {"safety-badge-fail" if hz["pre_risk"] in ("HIGH", "CRITICAL") else ("safety-badge-pass" if hz["pre_risk"] == "LOW" else "safety-badge-warn")}">{html_escape(hz["pre_risk"])}</span></td>'
        f'<td><span class="safety-badge {"safety-badge-pass" if hz["residual_risk"] == "LOW" else ("safety-badge-fail" if hz["residual_risk"] in ("HIGH", "CRITICAL") else "safety-badge-warn")}">{html_escape(hz["residual_risk"])}</span></td>'
        f'<td><code>{hz["exclusion_m"]:.1f}m</code></td>'
        f'<td>{html_escape(hz["ppe"])}</td>'
        f'<td><code>{html_escape(hz["csatf_bulletin"])}</code></td>'
        f'</tr>'
        for hz in safety_state["hazard_records"]
    ])

    first_c2pa = c2pa_state["scene_provenance"][0]
    first_safety = safety_state["scene_exclusion_zones"][0]

    v213_css = """
    /* PM-FEAT-025 C2PA Content Credentials HUD & PM-FEAT-026 On-Set Safety JSA HUD */
    .c2pa-hud-modal, .safety-hud-modal {
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
    .c2pa-modal-content, .safety-modal-content {
      background: var(--bg-surface);
      border: 1px solid var(--border-focus);
      border-radius: 8px;
      max-width: 1160px;
      width: 100%;
      max-height: 90vh;
      overflow-y: auto;
      box-shadow: 0 24px 48px rgba(0, 0, 0, 0.8), 0 0 20px rgba(0, 240, 255, 0.15);
      display: flex;
      flex-direction: column;
    }
    .c2pa-modal-header, .safety-modal-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 16px 20px;
      border-bottom: 1px solid var(--border-subtle);
      background: var(--bg-card);
    }
    .c2pa-title-wrap, .safety-title-wrap {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .c2pa-heading, .safety-heading {
      font-family: 'Space Grotesk', sans-serif;
      font-size: 16px;
      font-weight: 700;
      letter-spacing: 0.05em;
      color: var(--text-main);
      margin: 0;
    }
    .c2pa-subheading, .safety-subheading {
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      color: var(--cyan-telemetry);
      display: block;
    }
    .btn-c2pa-close, .btn-safety-close {
      background: transparent;
      border: 1px solid var(--border-subtle);
      color: var(--text-muted);
      width: 32px;
      height: 32px;
      border-radius: 4px;
      cursor: pointer;
      font-size: 15px;
    }
    .btn-c2pa-close:hover, .btn-c2pa-close:focus-visible,
    .btn-safety-close:hover, .btn-safety-close:focus-visible {
      border-color: var(--crimson-accent);
      color: var(--crimson-accent);
      outline: 2px solid var(--border-focus);
      outline-offset: 2px;
    }
    .c2pa-modal-body, .safety-modal-body {
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    .c2pa-toolbar, .safety-toolbar {
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
    .c2pa-badge-group, .safety-badge-group,
    .c2pa-actions, .safety-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }
    .c2pa-badge, .safety-badge {
      display: inline-block;
      padding: 2px 7px;
      border-radius: 3px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 0.04em;
    }
    .c2pa-badge-pass, .safety-badge-pass {
      color: #10B981;
      background: rgba(16, 185, 129, 0.14);
      border: 1px solid rgba(16, 185, 129, 0.45);
    }
    .c2pa-badge-warn, .safety-badge-warn {
      color: var(--amber-gold);
      background: rgba(255, 184, 0, 0.14);
      border: 1px solid rgba(255, 184, 0, 0.45);
    }
    .c2pa-badge-fail, .safety-badge-fail {
      color: var(--red-rec);
      background: rgba(255, 59, 48, 0.14);
      border: 1px solid rgba(255, 59, 48, 0.45);
    }
    .safety-badge-muted {
      color: var(--text-muted);
      background: rgba(142, 149, 170, 0.12);
      border: 1px solid var(--border-subtle);
    }
    .btn-v213-action {
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
    .btn-v213-action:hover, .btn-v213-action:focus-visible {
      background: rgba(0, 240, 255, 0.22);
      outline: 2px solid var(--border-focus);
      outline-offset: 2px;
    }
    .c2pa-grid, .safety-grid {
      display: grid;
      grid-template-columns: 1.05fr 1.15fr;
      gap: 16px;
    }
    @media (max-width: 920px) {
      .c2pa-grid, .safety-grid {
        grid-template-columns: 1fr;
      }
    }
    .c2pa-panel, .safety-panel {
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      border-radius: 6px;
      padding: 14px;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .c2pa-svg-wrap, .safety-svg-wrap {
      background: #07080B;
      border: 1px solid var(--border-subtle);
      border-radius: 6px;
      overflow: hidden;
    }
    .c2pa-svg-wrap svg, .safety-svg-wrap svg {
      width: 100%;
      height: auto;
      display: block;
    }
    .btn-c2pa-scene, .btn-safety-scene {
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      color: var(--text-muted);
      font-family: 'JetBrains Mono', monospace;
      font-size: 10px;
      font-weight: 600;
      padding: 4px 9px;
      border-radius: 4px;
      cursor: pointer;
    }
    .btn-c2pa-scene.active, .btn-safety-scene.active,
    .btn-c2pa-scene:focus-visible, .btn-safety-scene:focus-visible {
      border-color: var(--cyan-telemetry);
      color: var(--cyan-telemetry);
      background: rgba(0, 240, 255, 0.12);
      outline: 2px solid var(--border-focus);
      outline-offset: 1px;
    }
    .v213-table-wrap {
      overflow-x: auto;
      max-height: 240px;
      overflow-y: auto;
      border: 1px solid var(--border-subtle);
      border-radius: 6px;
    }
    .v213-table {
      width: 100%;
      border-collapse: collapse;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
    }
    .v213-table th {
      background: #0B0D14;
      color: var(--text-muted);
      text-align: left;
      padding: 8px 10px;
      border-bottom: 1px solid var(--border-subtle);
      font-size: 10px;
      position: sticky;
      top: 0;
    }
    .v213-table td {
      padding: 7px 10px;
      border-bottom: 1px solid rgba(32, 36, 52, 0.65);
      color: var(--text-main);
      vertical-align: top;
    }
    .c2pa-scene-row {
      cursor: pointer;
    }
    .c2pa-scene-row:hover, .c2pa-scene-row:focus-visible,
    .c2pa-scene-row.active-row, .safety-hazard-row.active-row {
      background: rgba(0, 240, 255, 0.08);
      outline: none;
    }
    .safety-subtext {
      color: var(--text-muted);
      font-size: 10px;
    }
    .v213-kv-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 8px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
    }
    .v213-kv-card {
      background: #090B10;
      border: 1px solid var(--border-subtle);
      border-radius: 5px;
      padding: 8px 10px;
    }
    .v213-kv-label {
      color: var(--text-muted);
      font-size: 10px;
      display: block;
    }
    """

    v213_modals_html = f"""
  <!-- PM-FEAT-025: C2PA Content Credentials & Likeness Disclosure HUD -->
  <div id="animatic-c2pa-hud" class="c2pa-hud-modal" role="dialog" aria-modal="true" aria-labelledby="c2pa-hud-title" tabindex="-1" style="display:none;">
    <div class="c2pa-modal-content">
      <div class="c2pa-modal-header">
        <div class="c2pa-title-wrap">
          <span style="font-size:20px;" aria-hidden="true">🛡️</span>
          <div>
            <h2 id="c2pa-hud-title" class="c2pa-heading">C2PA CONTENT CREDENTIALS &amp; LIKENESS DISCLOSURE HUD</h2>
            <span class="c2pa-subheading">PM-FEAT-025 · CRYPTOGRAPHIC LINEAGE · SYNTHID WATERMARK · EU AI ACT ART. 50 · SAG-AFTRA REPLICA GATE</span>
          </div>
        </div>
        <button type="button" class="btn-c2pa-close" onclick="toggleC2paHUD()" aria-label="Close C2PA Content Credentials HUD">✕</button>
      </div>

      <div class="c2pa-modal-body">
        <div class="c2pa-toolbar">
          <div class="c2pa-badge-group">
            <span class="aicp-badge">C2PA: <strong>{html_escape(c2pa_state['c2pa_version'])}</strong></span>
            <span class="aicp-badge">DISCLOSURE: <span class="c2pa-badge c2pa-badge-pass">{html_escape(c2pa_state['disclosure_tier'])}</span></span>
            <span class="aicp-badge">SYNTHID: <span class="c2pa-badge {synthid_cls}">{synthid_lbl}</span></span>
            <span class="aicp-badge">EU AI ACT ART.50: <span class="c2pa-badge {art50_cls}">{html_escape(c2pa_state['eu_ai_act_art50'])}</span></span>
            <span class="aicp-badge">2026 MODEL MATRIX: <span class="c2pa-badge {matrix_cls}">{matrix_lbl}</span></span>
            <span class="aicp-badge">LIKENESS GATE: <span class="c2pa-badge {likeness_cls}">{html_escape(c2pa_state['likeness_gate'])}</span></span>
          </div>
          <div class="c2pa-actions">
            <button type="button" class="btn-v213-action" id="btn-download-c2pa-json" onclick="downloadC2paJSON()" aria-label="Download C2PA Content Credentials JSON">
              ⤓ c2pa_content_credentials.json
            </button>
            <button type="button" class="btn-v213-action" id="btn-download-disclosure-md" onclick="downloadDisclosureMD()" aria-label="Download EU AI Act Article 50 Disclosure Markdown">
              ⤓ eu_ai_act_art50_disclosure.md
            </button>
            <button type="button" class="btn-v213-action" id="btn-download-likeness-csv" onclick="downloadLikenessCSV()" aria-label="Download Likeness Consent Ledger CSV">
              ⤓ likeness_consent_ledger.csv
            </button>
          </div>
        </div>

        <div class="c2pa-grid">
          <div class="c2pa-panel">
            <div class="drone-panel-header">
              <span>PROVENANCE LINEAGE GRAPH (INGREDIENTS → PROMPT SHA-256 → OMNI OUTPUT)</span>
              <span class="badge-canvas-telemetry" id="c2pa-active-scene-badge">SCENE {int(first_c2pa['scene_index']):02d}</span>
            </div>
            <div style="display:flex;flex-wrap:wrap;gap:6px;" role="navigation" aria-label="C2PA Scene Selector">
              {c2pa_scene_pills}
            </div>
            <div class="c2pa-svg-wrap">
              <svg id="c2pa-lineage-svg" viewBox="0 0 620 270" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="C2PA Cryptographic Provenance Lineage Graph"></svg>
            </div>
            <div class="v213-kv-grid">
              <div class="v213-kv-card">
                <span class="v213-kv-label">ASSERTION URN</span>
                <strong id="c2pa-kv-urn">{html_escape(first_c2pa['c2pa_assertion_id'])}</strong>
              </div>
              <div class="v213-kv-card">
                <span class="v213-kv-label">PROMPT SHA-256 DIGEST</span>
                <strong id="c2pa-kv-hash">{html_escape(first_c2pa['prompt_sha256'][:24])}…</strong>
              </div>
            </div>
          </div>

          <div class="c2pa-panel">
            <div class="drone-panel-header">
              <span>PER-SCENE MODEL &amp; DIGEST MANIFEST</span>
              <span class="badge-canvas-telemetry">{len(c2pa_state['scene_provenance'])} SCENES VERIFIED</span>
            </div>
            <div class="v213-table-wrap">
              <table class="v213-table" aria-label="Per-scene C2PA model and digest table">
                <thead>
                  <tr><th>Scene</th><th>Video Model</th><th>Prompt SHA-256</th><th>Ingredients</th><th>SynthID</th><th>Status</th></tr>
                </thead>
                <tbody>
                  {c2pa_scene_rows}
                </tbody>
              </table>
            </div>

            <div class="drone-panel-header" style="margin-top:4px;">
              <span>TALENT LIKENESS &amp; SAG-AFTRA DIGITAL REPLICA CONSENT</span>
              <span class="badge-canvas-telemetry">{len(c2pa_state['likeness_records'])} RECORDS</span>
            </div>
            <div class="v213-table-wrap">
              <table class="v213-table" aria-label="Talent likeness and SAG-AFTRA digital replica consent table">
                <thead>
                  <tr><th>ID</th><th>Subject</th><th>Classification</th><th>SAG-AFTRA Rider</th><th>Gate</th></tr>
                </thead>
                <tbody>
                  {c2pa_likeness_rows}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- PM-FEAT-026: On-Set Safety Risk & Exclusion-Zone HUD -->
  <div id="animatic-safety-hud" class="safety-hud-modal" role="dialog" aria-modal="true" aria-labelledby="safety-hud-title" tabindex="-1" style="display:none;">
    <div class="safety-modal-content">
      <div class="safety-modal-header">
        <div class="safety-title-wrap">
          <span style="font-size:20px;" aria-hidden="true">🦺</span>
          <div>
            <h2 id="safety-hud-title" class="safety-heading">ON-SET SAFETY RISK &amp; EXCLUSION-ZONE JSA HUD</h2>
            <span class="safety-subheading">PM-FEAT-026 · 2D STAGE EXCLUSION PERIMETER · CSATF SAFETY BULLETINS · STANDBY MEDIC &amp; FIRE MARSHAL GATE</span>
          </div>
        </div>
        <button type="button" class="btn-safety-close" onclick="toggleSafetyHUD()" aria-label="Close On-Set Safety JSA HUD">✕</button>
      </div>

      <div class="safety-modal-body">
        <div class="safety-toolbar">
          <div class="safety-badge-group">
            <span class="aicp-badge">CLEARANCE: <span class="safety-badge {clearance_cls}">{html_escape(safety_state['clearance_status'])}</span></span>
            <span class="aicp-badge">MAX RADIUS: <strong id="safety-max-radius-badge">{safety_state['max_exclusion_radius_m']}m</strong></span>
            <span class="aicp-badge">UNMITIGATED CRITICALS: <span class="safety-badge {crit_cls}">{safety_state['unmitigated_critical_count']}</span></span>
            <span class="aicp-badge">MEDIC: <span class="safety-badge {medic_cls}">{'ON SITE' if safety_state['standby_medic'] else 'ON CALL'}</span></span>
            <span class="aicp-badge">FIRE MARSHAL: <span class="safety-badge {marshal_cls}">{'ASSIGNED' if safety_state['fire_marshal'] else 'NOT REQ'}</span></span>
            <span class="aicp-badge">RADIO: <strong>{html_escape(safety_state['radio_channel'])}</strong></span>
          </div>
          <div class="safety-actions">
            <button type="button" class="btn-v213-action" id="btn-download-safety-md" onclick="downloadSafetyMD()" aria-label="Download On-Set Safety JSA Markdown Report">
              ⤓ on_set_safety_jsa.md
            </button>
            <button type="button" class="btn-v213-action" id="btn-download-safety-csv" onclick="downloadSafetyCSV()" aria-label="Download Safety Hazard Matrix CSV">
              ⤓ safety_hazard_matrix.csv
            </button>
            <button type="button" class="btn-v213-action" id="btn-download-safety-json" onclick="downloadSafetyJSON()" aria-label="Download Safety Risk Manifest JSON">
              ⤓ safety_risk_manifest.json
            </button>
          </div>
        </div>

        <div class="safety-grid">
          <div class="safety-panel">
            <div class="drone-panel-header">
              <span>2D STAGE EXCLUSION-ZONE PERIMETER (SYNCED WITH SCENE PILLS)</span>
              <span class="badge-canvas-telemetry" id="safety-active-scene-badge">SCENE {int(first_safety['scene_index']):02d}</span>
            </div>
            <div style="display:flex;flex-wrap:wrap;gap:6px;" role="navigation" aria-label="Safety JSA Scene Selector">
              {safety_scene_pills}
            </div>
            <div class="safety-svg-wrap">
              <svg id="safety-perimeter-svg" viewBox="0 0 560 320" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="2D Stage Safety Exclusion Zone Perimeter"></svg>
            </div>
            <div class="v213-kv-grid">
              <div class="v213-kv-card">
                <span class="v213-kv-label">PRIMARY HAZARD &amp; BULLETIN</span>
                <strong id="safety-kv-cat">{html_escape(first_safety['hazard_category'])} · {html_escape(first_safety['csatf_bulletin'])}</strong>
              </div>
              <div class="v213-kv-card">
                <span class="v213-kv-label">REQUIRED STAGE PPE</span>
                <strong id="safety-kv-ppe">{html_escape(first_safety['ppe_required'])}</strong>
              </div>
            </div>
          </div>

          <div class="safety-panel">
            <div class="drone-panel-header">
              <span>JSA HAZARD CONTROL MATRIX</span>
              <span class="badge-canvas-telemetry">{len(safety_state['hazard_records'])} HAZARDS LOGGED</span>
            </div>
            <div class="v213-table-wrap" style="max-height:390px;">
              <table class="v213-table" aria-label="Job Safety Analysis Hazard Control Matrix">
                <thead>
                  <tr><th>ID</th><th>Category &amp; Control</th><th>Pre</th><th>Res</th><th>Excl.</th><th>PPE</th><th>CSATF</th></tr>
                </thead>
                <tbody>
                  {safety_hazard_rows}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
"""

    v213_js = f"""
    // PM-FEAT-025: C2PA Content Credentials & Likeness Disclosure HUD Controller
    const C2PA_STATE = {c2pa_state_json};
    let isC2paHUDOpen = false;
    let lastC2paOpener = null;
    let activeC2paSceneIdx = C2PA_STATE.scene_provenance.length ? C2PA_STATE.scene_provenance[0].scene_index : 1;

    function _renderC2paLineageSVG(sp) {{
      const svg = document.getElementById('c2pa-lineage-svg');
      if (!svg || !sp) return;
      const svgNS = 'http://www.w3.org/2000/svg';
      while (svg.firstChild) svg.removeChild(svg.firstChild);

      const addEl = (tag, attrs, textVal) => {{
        const el = document.createElementNS(svgNS, tag);
        Object.keys(attrs).forEach((k) => el.setAttribute(k, String(attrs[k])));
        if (textVal !== undefined) el.textContent = String(textVal);
        svg.appendChild(el);
        return el;
      }};

      addEl('rect', {{ width: 620, height: 270, fill: '#07080B', rx: 6 }});

      const ings = (sp.ingredients && sp.ingredients.length) ? sp.ingredients : (C2PA_STATE.ingredients || []);
      const ySlots = [52, 135, 218];
      ings.slice(0, 3).forEach((ing, idx) => {{
        const y = ySlots[idx];
        addEl('line', {{ x1: 175, y1: y, x2: 245, y2: 135, stroke: '#00F0FF', 'stroke-width': 1.5, 'stroke-dasharray': '4 3', opacity: 0.75 }});
        addEl('rect', {{ x: 16, y: y - 24, width: 160, height: 48, rx: 5, fill: '#141722', stroke: '#00F0FF', 'stroke-width': 1.2 }});
        addEl('text', {{ x: 26, y: y - 5, fill: '#00F0FF', 'font-family': 'JetBrains Mono, monospace', 'font-size': 10, 'font-weight': 700 }}, ing.slot + ' INGREDIENT');
        addEl('text', {{ x: 26, y: y + 12, fill: '#F0F2F8', 'font-family': 'JetBrains Mono, monospace', 'font-size': 9 }}, (ing.label || '').slice(0, 22));
      }});

      addEl('line', {{ x1: 405, y1: 135, x2: 448, y2: 135, stroke: '#10B981', 'stroke-width': 2 }});

      addEl('rect', {{ x: 245, y: 72, width: 160, height: 126, rx: 6, fill: '#141722', stroke: '#FFB800', 'stroke-width': 1.5 }});
      addEl('text', {{ x: 325, y: 96, 'text-anchor': 'middle', fill: '#FFB800', 'font-family': 'JetBrains Mono, monospace', 'font-size': 10, 'font-weight': 700 }}, 'ScenePromptSpec S' + String(sp.scene_index).padStart(2, '0'));
      addEl('text', {{ x: 325, y: 118, 'text-anchor': 'middle', fill: '#F0F2F8', 'font-family': 'JetBrains Mono, monospace', 'font-size': 9 }}, 'SHA-256: ' + (sp.prompt_sha256 || '').slice(0, 12));
      addEl('text', {{ x: 325, y: 140, 'text-anchor': 'middle', fill: '#8E95AA', 'font-family': 'JetBrains Mono, monospace', 'font-size': 9 }}, sp.director_model || 'gemini-4-argon');
      addEl('text', {{ x: 325, y: 158, 'text-anchor': 'middle', fill: '#8E95AA', 'font-family': 'JetBrains Mono, monospace', 'font-size': 9 }}, sp.prompt_model || 'gemini-3.8-flash');
      addEl('text', {{ x: 325, y: 178, 'text-anchor': 'middle', fill: '#10B981', 'font-family': 'JetBrains Mono, monospace', 'font-size': 9, 'font-weight': 700 }}, 'C2PA ' + (C2PA_STATE.c2pa_version || 'v2.1'));

      addEl('rect', {{ x: 448, y: 66, width: 156, height: 138, rx: 6, fill: '#0E1917', stroke: '#10B981', 'stroke-width': 1.8 }});
      addEl('text', {{ x: 526, y: 92, 'text-anchor': 'middle', fill: '#10B981', 'font-family': 'JetBrains Mono, monospace', 'font-size': 10, 'font-weight': 700 }}, 'C2PA OUTPUT NODE');
      addEl('text', {{ x: 526, y: 114, 'text-anchor': 'middle', fill: '#F0F2F8', 'font-family': 'JetBrains Mono, monospace', 'font-size': 8.5 }}, sp.video_model || 'gemini-omni-1.1-flash-preview');
      addEl('text', {{ x: 526, y: 136, 'text-anchor': 'middle', fill: '#00F0FF', 'font-family': 'JetBrains Mono, monospace', 'font-size': 9 }}, 'SynthID: ' + (sp.synthid_embedded ? 'ACTIVE' : 'OFF'));
      addEl('text', {{ x: 526, y: 156, 'text-anchor': 'middle', fill: '#F0F2F8', 'font-family': 'JetBrains Mono, monospace', 'font-size': 9 }}, 'Art.50: ' + (C2PA_STATE.eu_ai_act_art50 || 'PASS'));
      addEl('text', {{ x: 526, y: 180, 'text-anchor': 'middle', fill: '#10B981', 'font-family': 'JetBrains Mono, monospace', 'font-size': 9, 'font-weight': 700 }}, sp.compliance_status || 'VERIFIED');
    }}

    function highlightC2paScene(sIdx) {{
      activeC2paSceneIdx = sIdx;
      const sp = C2PA_STATE.scene_provenance.find((s) => s.scene_index === sIdx) || C2PA_STATE.scene_provenance[0];
      if (!sp) return;
      document.querySelectorAll('.btn-c2pa-scene').forEach((btn) => {{
        const idx = parseInt(btn.getAttribute('data-scene-index') || '0', 10);
        btn.classList.toggle('active', idx === sp.scene_index);
      }});
      document.querySelectorAll('.c2pa-scene-row').forEach((row) => {{
        const idx = parseInt(row.getAttribute('data-scene-index') || '0', 10);
        row.classList.toggle('active-row', idx === sp.scene_index);
      }});
      const badge = document.getElementById('c2pa-active-scene-badge');
      if (badge) badge.textContent = 'SCENE ' + String(sp.scene_index).padStart(2, '0');
      const urnEl = document.getElementById('c2pa-kv-urn');
      if (urnEl) urnEl.textContent = sp.c2pa_assertion_id;
      const hashEl = document.getElementById('c2pa-kv-hash');
      if (hashEl) hashEl.textContent = (sp.prompt_sha256 || '').slice(0, 24) + '…';
      _renderC2paLineageSVG(sp);
    }}

    function selectC2paScene(sIdx) {{
      const sp = C2PA_STATE.scene_provenance.find((s) => s.scene_index === sIdx);
      if (!sp) return;
      highlightC2paScene(sIdx);
      if (typeof jumpToScene === 'function') jumpToScene(sIdx, sp.start_sec);
      showToast('🛡️ C2PA Lineage: Scene ' + String(sIdx).padStart(2, '0') + ' (' + sp.video_model + ')');
    }}

    function updateC2paFromTimeline(tSec) {{
      if (!isC2paHUDOpen || !C2PA_STATE.scene_provenance.length) return;
      let match = C2PA_STATE.scene_provenance.find((s) => tSec >= s.start_sec && tSec < s.end_sec);
      if (!match) match = C2PA_STATE.scene_provenance[C2PA_STATE.scene_provenance.length - 1];
      if (match && match.scene_index !== activeC2paSceneIdx) highlightC2paScene(match.scene_index);
    }}

    function toggleC2paHUD() {{
      isC2paHUDOpen = !isC2paHUDOpen;
      const modal = document.getElementById('animatic-c2pa-hud');
      const btn = document.getElementById('btn-c2pa-animatic');
      if (modal) modal.style.display = isC2paHUDOpen ? 'flex' : 'none';
      if (btn) {{
        btn.classList.toggle('active', isC2paHUDOpen);
        btn.setAttribute('aria-expanded', isC2paHUDOpen ? 'true' : 'false');
      }}
      if (isC2paHUDOpen) {{
        lastC2paOpener = document.activeElement;
        highlightC2paScene(activeC2paSceneIdx);
        const closeBtn = modal ? modal.querySelector('.btn-c2pa-close') : null;
        if (closeBtn) closeBtn.focus();
        showToast('🛡️ C2PA Content Credentials HUD: ACTIVE [Y]');
      }} else if (lastC2paOpener && typeof lastC2paOpener.focus === 'function') {{
        lastC2paOpener.focus();
      }}
    }}

    function initC2paHUD() {{
      highlightC2paScene(activeC2paSceneIdx);
    }}

    function downloadC2paJSON() {{
      _triggerBlobDownload(`{c2pa_json_escaped}`, 'application/json;charset=utf-8;', 'c2pa_content_credentials.json', 'Downloaded C2PA Credentials (c2pa_content_credentials.json)');
    }}

    function downloadDisclosureMD() {{
      _triggerBlobDownload(`{c2pa_md_escaped}`, 'text/markdown;charset=utf-8;', 'eu_ai_act_art50_disclosure.md', 'Downloaded EU AI Act Art. 50 Disclosure (eu_ai_act_art50_disclosure.md)');
    }}

    function downloadLikenessCSV() {{
      _triggerBlobDownload(`{c2pa_csv_escaped}`, 'text/csv;charset=utf-8;', 'likeness_consent_ledger.csv', 'Downloaded Likeness Consent Ledger (likeness_consent_ledger.csv)');
    }}

    // PM-FEAT-026: On-Set Safety Risk & Exclusion-Zone HUD Controller
    const SAFETY_STATE = {safety_state_json};
    let isSafetyHUDOpen = false;
    let lastSafetyOpener = null;
    let activeSafetySceneIdx = SAFETY_STATE.scene_exclusion_zones.length ? SAFETY_STATE.scene_exclusion_zones[0].scene_index : 1;

    function _renderSafetyPerimeterSVG(sz) {{
      const svg = document.getElementById('safety-perimeter-svg');
      if (!svg || !sz) return;
      const svgNS = 'http://www.w3.org/2000/svg';
      while (svg.firstChild) svg.removeChild(svg.firstChild);

      const addEl = (tag, attrs, textVal) => {{
        const el = document.createElementNS(svgNS, tag);
        Object.keys(attrs).forEach((k) => el.setAttribute(k, String(attrs[k])));
        if (textVal !== undefined) el.textContent = String(textVal);
        svg.appendChild(el);
        return el;
      }};

      addEl('rect', {{ width: 560, height: 320, fill: '#07080B', rx: 6 }});
      const cx = 280;
      const cy = 160;
      const maxR = Math.max(10, Number(sz.green_safe_m || 10));
      const scale = 128 / maxR;
      const rSafe = Math.max(85, Math.min(136, Number(sz.green_safe_m || 10) * scale));
      const rBuf = Math.max(54, Math.min(102, Number(sz.amber_buffer_m || 6) * scale));
      const rInner = Math.max(28, Math.min(72, Number(sz.inner_keepout_m || 3) * scale));

      addEl('circle', {{ cx, cy, r: rSafe, fill: 'rgba(16, 185, 129, 0.08)', stroke: '#10B981', 'stroke-width': 1.8, 'stroke-dasharray': '6 4' }});
      addEl('circle', {{ cx, cy, r: rBuf, fill: 'rgba(255, 184, 0, 0.10)', stroke: '#FFB800', 'stroke-width': 1.8, 'stroke-dasharray': '4 3' }});
      addEl('circle', {{ cx, cy, r: rInner, fill: 'rgba(255, 59, 48, 0.18)', stroke: '#FF3B30', 'stroke-width': 2.2 }});
      addEl('circle', {{ cx, cy, r: 7, fill: '#FF3B30', stroke: '#F0F2F8', 'stroke-width': 1.5 }});

      addEl('text', {{ x: cx, y: cy - rSafe - 8, 'text-anchor': 'middle', fill: '#10B981', 'font-family': 'JetBrains Mono, monospace', 'font-size': 10, 'font-weight': 700 }}, 'GREEN CREW / VIDEO VILLAGE SAFE PERIMETER (' + sz.green_safe_m + 'm)');
      addEl('text', {{ x: cx, y: cy - rBuf + 14, 'text-anchor': 'middle', fill: '#FFB800', 'font-family': 'JetBrains Mono, monospace', 'font-size': 10, 'font-weight': 700 }}, 'AMBER RIG / UAV BUFFER (' + sz.amber_buffer_m + 'm)');
      addEl('text', {{ x: cx, y: cy + 20, 'text-anchor': 'middle', fill: '#FF3B30', 'font-family': 'JetBrains Mono, monospace', 'font-size': 10, 'font-weight': 700 }}, 'RED KEEP-OUT (' + sz.inner_keepout_m + 'm)');

      addEl('rect', {{ x: 14, y: 14, width: 152, height: 24, rx: 4, fill: '#141722', stroke: '#10B981', 'stroke-width': 1 }});
      addEl('text', {{ x: 22, y: 30, fill: '#10B981', 'font-family': 'JetBrains Mono, monospace', 'font-size': 9.5, 'font-weight': 700 }}, 'MEDIC: ' + (SAFETY_STATE.standby_medic ? 'ON SITE' : 'ON CALL'));

      addEl('rect', {{ x: 394, y: 14, width: 152, height: 24, rx: 4, fill: '#141722', stroke: '#00F0FF', 'stroke-width': 1 }});
      addEl('text', {{ x: 402, y: 30, fill: '#00F0FF', 'font-family': 'JetBrains Mono, monospace', 'font-size': 9.5, 'font-weight': 700 }}, SAFETY_STATE.radio_channel || 'CH-09 SAFETY');

      addEl('text', {{ x: 280, y: 306, 'text-anchor': 'middle', fill: '#8E95AA', 'font-family': 'JetBrains Mono, monospace', 'font-size': 9.5 }}, 'S' + String(sz.scene_index).padStart(2, '0') + ' · ' + sz.hazard_category + ' · ' + sz.csatf_bulletin);
    }}

    function highlightSafetyScene(sIdx) {{
      activeSafetySceneIdx = sIdx;
      const sz = SAFETY_STATE.scene_exclusion_zones.find((s) => s.scene_index === sIdx) || SAFETY_STATE.scene_exclusion_zones[0];
      if (!sz) return;
      document.querySelectorAll('.btn-safety-scene').forEach((btn) => {{
        const idx = parseInt(btn.getAttribute('data-scene-index') || '0', 10);
        btn.classList.toggle('active', idx === sz.scene_index);
      }});
      document.querySelectorAll('.safety-hazard-row').forEach((row) => {{
        const idx = parseInt(row.getAttribute('data-scene-index') || '0', 10);
        row.classList.toggle('active-row', idx === sz.scene_index);
      }});
      const badge = document.getElementById('safety-active-scene-badge');
      if (badge) badge.textContent = 'SCENE ' + String(sz.scene_index).padStart(2, '0');
      const catEl = document.getElementById('safety-kv-cat');
      if (catEl) catEl.textContent = sz.hazard_category + ' · ' + sz.csatf_bulletin;
      const ppeEl = document.getElementById('safety-kv-ppe');
      if (ppeEl) ppeEl.textContent = sz.ppe_required;
      _renderSafetyPerimeterSVG(sz);
    }}

    function selectSafetyScene(sIdx) {{
      const sz = SAFETY_STATE.scene_exclusion_zones.find((s) => s.scene_index === sIdx);
      if (!sz) return;
      highlightSafetyScene(sIdx);
      if (typeof jumpToScene === 'function') jumpToScene(sIdx, sz.start_sec);
      showToast('🦺 Safety JSA: Scene ' + String(sIdx).padStart(2, '0') + ' (' + sz.inner_keepout_m + 'm Keep-Out)');
    }}

    function updateSafetyFromTimeline(tSec) {{
      if (!isSafetyHUDOpen || !SAFETY_STATE.scene_exclusion_zones.length) return;
      let match = SAFETY_STATE.scene_exclusion_zones.find((s) => tSec >= s.start_sec && tSec < s.end_sec);
      if (!match) match = SAFETY_STATE.scene_exclusion_zones[SAFETY_STATE.scene_exclusion_zones.length - 1];
      if (match && match.scene_index !== activeSafetySceneIdx) highlightSafetyScene(match.scene_index);
    }}

    function toggleSafetyHUD() {{
      isSafetyHUDOpen = !isSafetyHUDOpen;
      const modal = document.getElementById('animatic-safety-hud');
      const btn = document.getElementById('btn-safety-animatic');
      if (modal) modal.style.display = isSafetyHUDOpen ? 'flex' : 'none';
      if (btn) {{
        btn.classList.toggle('active', isSafetyHUDOpen);
        btn.setAttribute('aria-expanded', isSafetyHUDOpen ? 'true' : 'false');
      }}
      if (isSafetyHUDOpen) {{
        lastSafetyOpener = document.activeElement;
        highlightSafetyScene(activeSafetySceneIdx);
        const closeBtn = modal ? modal.querySelector('.btn-safety-close') : null;
        if (closeBtn) closeBtn.focus();
        showToast('🦺 On-Set Safety JSA HUD: ACTIVE [Z]');
      }} else if (lastSafetyOpener && typeof lastSafetyOpener.focus === 'function') {{
        lastSafetyOpener.focus();
      }}
    }}

    function initSafetyHUD() {{
      highlightSafetyScene(activeSafetySceneIdx);
    }}

    function downloadSafetyMD() {{
      _triggerBlobDownload(`{safety_md_escaped}`, 'text/markdown;charset=utf-8;', 'on_set_safety_jsa.md', 'Downloaded On-Set Safety JSA (on_set_safety_jsa.md)');
    }}

    function downloadSafetyCSV() {{
      _triggerBlobDownload(`{safety_csv_escaped}`, 'text/csv;charset=utf-8;', 'safety_hazard_matrix.csv', 'Downloaded Safety Hazard Matrix (safety_hazard_matrix.csv)');
    }}

    function downloadSafetyJSON() {{
      _triggerBlobDownload(`{safety_json_escaped}`, 'application/json;charset=utf-8;', 'safety_risk_manifest.json', 'Downloaded Safety Risk Manifest (safety_risk_manifest.json)');
    }}
"""

    return {
        "css": v213_css,
        "modals_html": v213_modals_html,
        "js": v213_js,
    }
