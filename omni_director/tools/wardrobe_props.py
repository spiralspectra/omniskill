"""Wardrobe, Prop & Art Dressing Continuity Engine (PM-FEAT-031)."""

import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from omni_director.schemas import (
    ArtDressingAnchorSpec,
    MasterProductionBible,
    MasterWardrobePropBible,
    PropActionStateEnum,
    SceneArtContinuitySpec,
    ScenePromptSpec,
    ScenePropContinuityState,
    SceneWardrobeStateSpec,
)

_ARCHETYPE_ART_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "automotive_robotics": {
        "prop_name": "Carbon-Fiber Telemetry Keyfob",
        "prop_id": "PROP_KEYFOB_01",
        "anchor": "cockpit_console",
        "surface": "matte_carbon_clean",
        "garment": "Tailored charcoal tech-knit racing jacket with matte titanium zipper",
        "weathering": "dry_tailored",
        "accessories": ["titanium_chronograph", "driving_gloves"],
        "dressing_zone": "Garage Wind-Tunnel Bay",
        "material_finish": "Brushed anodized aluminum & wet-look epoxy floor",
    },
    "culinary_asmr": {
        "prop_name": "Hand-Forged Gyuto Chef Knife",
        "prop_id": "PROP_KNIFE_01",
        "anchor": "end_grain_walnut_block",
        "surface": "honed_damascus_clean",
        "garment": "Indigo Japanese canvas chef apron over crisp linen shirt",
        "weathering": "crisp_starched",
        "accessories": ["linen_side_towel"],
        "dressing_zone": "Hero Prep Counter",
        "material_finish": "Oiled walnut butcher block & hand-thrown stoneware",
    },
    "luxury_fashion": {
        "prop_name": "Sculpted Calfskin Atelier Clutch",
        "prop_id": "PROP_CLUTCH_01",
        "anchor": "travertine_pedestal",
        "surface": "supple_gloss_clean",
        "garment": "Architectural ivory silk trench coat with structured lapels",
        "weathering": "runway_pressed",
        "accessories": ["brushed_gold_cuff", "silk_scarf"],
        "dressing_zone": "Travertine Salon Gallery",
        "material_finish": "Honed Roman travertine & warm brass architectural trim",
    },
    "kinetic_action": {
        "prop_name": "Reinforced Tactical Relay Beacon",
        "prop_id": "PROP_BEACON_01",
        "anchor": "utility_belt_holster",
        "surface": "scuffed_anodized_clean",
        "garment": "Weather-resistant slate ripstop field shell with articulated elbows",
        "weathering": "field_dusted",
        "accessories": ["ballistic_watch", "carabiner_rig"],
        "dressing_zone": "Concrete Rooftop Corridor",
        "material_finish": "Raw poured concrete & galvanized steel conduit",
    },
    "tech_hardware": {
        "prop_name": "Precision Machined Silicon Unibody Device",
        "prop_id": "PROP_DEVICE_01",
        "anchor": "optical_calibration_plinth",
        "surface": "oleophobic_glass_spotless",
        "garment": "Minimalist obsidian merino mock-neck with tailored wool trousers",
        "weathering": "studio_immaculate",
        "accessories": ["anti_static_wristband"],
        "dressing_zone": "Cleanroom Acoustic Stage",
        "material_finish": "Bead-blasted aluminum & optical-grade acoustic glass",
    },
    "architectural_sanctuary": {
        "prop_name": "Hand-Cast Bronze Tea Vessel",
        "prop_id": "PROP_VESSEL_01",
        "anchor": "cedar_low_table",
        "surface": "warm_patina_dry",
        "garment": "Oatmeal raw-silk kimono wrap over wide-leg linen trousers",
        "weathering": "soft_draped",
        "accessories": ["wooden_hairpin"],
        "dressing_zone": "Timber Courtyard Pavilion",
        "material_finish": "Charred cedar Shou Sugi Ban & honed basalt water basin",
    },
}


def detect_prop_state_transitions(scenes: List[ScenePromptSpec]) -> List[Dict[str, Any]]:
    """Detects unmotivated prop state reversals or hand swaps across consecutive scenes.

    Flags:
    - ``damaged -> intact`` reversals unless ``continuity_delta_note`` motivates it.
    - ``in_hand_left <-> in_hand_right`` swaps across consecutive scenes unless
      ``continuity_delta_note`` motivates it.
    """
    violations: List[Dict[str, Any]] = []
    ordered_scenes = sorted(
        list(scenes or []),
        key=lambda sc: int(getattr(sc, "scene_index", 0) or 0),
    )
    last_seen: Dict[str, Tuple[int, ScenePropContinuityState]] = {}

    for sc in ordered_scenes:
        scene_idx = int(getattr(sc, "scene_index", 0) or 0)
        art_spec = getattr(sc, "art_continuity_spec", None)
        if art_spec is None:
            continue

        note = str(getattr(art_spec, "continuity_delta_note", "") or "").strip()
        is_motivated = len(note) >= 4

        for prop in list(getattr(art_spec, "prop_states", None) or []):
            prop_id = str(getattr(prop, "prop_id", "") or "")
            if not prop_id:
                continue

            curr_state = str(getattr(prop, "action_state", "intact") or "intact")
            if prop_id in last_seen:
                prev_scene_idx, prev_prop = last_seen[prop_id]
                prev_state = str(getattr(prev_prop, "action_state", "intact") or "intact")

                if prev_state == "damaged" and curr_state == "intact" and not is_motivated:
                    violations.append({
                        "prop_id": prop_id,
                        "prop_name": getattr(prop, "prop_name", prop_id),
                        "from_scene": prev_scene_idx,
                        "to_scene": scene_idx,
                        "from_state": prev_state,
                        "to_state": curr_state,
                        "violation_type": "damaged_reversal",
                        "message": (
                            f"Prop '{prop_id}' reversed from 'damaged' (Scene {prev_scene_idx}) "
                            f"to 'intact' (Scene {scene_idx}) without continuity_delta_note."
                        ),
                    })
                elif (
                    prev_state in ("in_hand_left", "in_hand_right")
                    and curr_state in ("in_hand_left", "in_hand_right")
                    and prev_state != curr_state
                    and not is_motivated
                ):
                    violations.append({
                        "prop_id": prop_id,
                        "prop_name": getattr(prop, "prop_name", prop_id),
                        "from_scene": prev_scene_idx,
                        "to_scene": scene_idx,
                        "from_state": prev_state,
                        "to_state": curr_state,
                        "violation_type": "unmotivated_hand_swap",
                        "message": (
                            f"Prop '{prop_id}' swapped hands ({prev_state} -> {curr_state}) "
                            f"between Scene {prev_scene_idx} and Scene {scene_idx} without continuity_delta_note."
                        ),
                    })

            last_seen[prop_id] = (scene_idx, prop)

    return violations


def validate_reference_slot_budget(
    wardrobe_count: int,
    env_plates: int,
    prop_plates: int,
) -> Tuple[bool, List[str]]:
    """Enforces the <= 3 ``<image_1..3>`` Nano Banana reference slot ceiling.

    Returns ``(within_budget, prioritized_slots)`` where ``prioritized_slots``
    contains at most 3 slot descriptors tagged with ``<image_1>``..``<image_3>``.
    """
    w = max(0, int(wardrobe_count))
    e = max(0, int(env_plates))
    p = max(0, int(prop_plates))
    total = w + e + p
    within_budget = total <= 3

    ordered_labels: List[str] = []
    # Prioritize 1 slot per active department first so no department is starved, then fill remainder up to 3.
    remaining = {"wardrobe": w, "env": e, "prop": p}
    counters = {"wardrobe": 0, "env": 0, "prop": 0}

    while len(ordered_labels) < 3 and any(v > 0 for v in remaining.values()):
        for dept in ("wardrobe", "env", "prop"):
            if remaining[dept] > 0 and len(ordered_labels) < 3:
                counters[dept] += 1
                remaining[dept] -= 1
                ordered_labels.append(f"{dept}_{counters[dept]}")

    prioritized_slots = [
        f"<image_{idx + 1}>:{label}" for idx, label in enumerate(ordered_labels)
    ]
    return within_budget, prioritized_slots


def format_art_continuity_token(spec: SceneArtContinuitySpec) -> str:
    """Formats compact machine telemetry tokens for PM-FEAT-031 wardrobe and prop continuity."""
    wardrobe_states = list(getattr(spec, "wardrobe_states", None) or [])
    if wardrobe_states:
        w_parts = [
            f"{w.character_id}:{w.look_id}({w.weathering_stage})"
            for w in wardrobe_states[:2]
        ]
        w_str = ", ".join(w_parts)
    else:
        w_str = "HERO:LOOK_A(dry_tailored)"

    prop_states = list(getattr(spec, "prop_states", None) or [])
    if prop_states:
        p_parts = [
            f"{p.prop_id}={p.action_state}@{p.hand_or_anchor}"
            for p in prop_states[:2]
        ]
        p_str = ", ".join(p_parts)
    else:
        p_str = "NONE=intact@center_table"

    slots = list(getattr(spec, "assigned_reference_slots", None) or [])
    slot_tag = f" | slots={len(slots)}/3" if slots else ""
    return f"[WARDROBE-LOCK: {w_str}][PROP-STATE: {p_str}{slot_tag}]"


def _infer_prop_state_from_scene(scene: ScenePromptSpec, default_anchor: str) -> Tuple[PropActionStateEnum, str]:
    """Infers deterministic prop action state and surface condition from scene prose/beats."""
    text = " ".join([
        str(getattr(scene, "omni_prose_prompt", "") or ""),
        str(getattr(scene, "kinetic_contact_chain", "") or ""),
        " ".join(str(b) for b in (getattr(scene, "action_beats", None) or [])),
    ]).lower()

    if any(k in text for k in ("shatter", "scratch", "dent", "crack", "broken", "damage")):
        return "damaged", "impact_scuffed"
    if any(k in text for k in ("rain", "splash", "mist", "sweat", "steam", "dust", "mud")):
        return "weathered", "moisture_dusted"
    if any(k in text for k in ("ignite", "activate", "glow", "power on", "trigger", "pour")):
        return "activated", "active_energized"
    if "left hand" in text:
        return "in_hand_left", "held_clean"
    if "right hand" in text or any(k in text for k in ("grip", "hold", "lift", "grasp")):
        return "in_hand_right", "held_clean"
    return "intact", f"dry_clean@{default_anchor}"


def compile_wardrobe_prop_bible(bible: MasterProductionBible) -> MasterWardrobePropBible:
    """Deterministically builds or hydrates PM-FEAT-031 Wardrobe, Prop & Art Continuity Bible."""
    domain = str(getattr(bible, "domain_archetype", None) or "architectural_sanctuary")
    defaults = _ARCHETYPE_ART_DEFAULTS.get(domain, _ARCHETYPE_ART_DEFAULTS["architectural_sanctuary"])

    title = str(getattr(bible, "project_title", "OmniProject") or "OmniProject")
    digest = hashlib.sha256(f"{title}:{domain}".encode("utf-8")).hexdigest()[:8].upper()
    bible_id = f"ART-BIBLE-{digest}"

    characters = list(getattr(bible, "characters", None) or [])
    env = getattr(bible, "environments", None) or getattr(bible, "environment", None)
    env_name = str(getattr(env, "location_name", None) or defaults["dressing_zone"])
    env_invariants = list(getattr(env, "positive_invariants", None) or [])
    material_finish = (
        ", ".join(str(i) for i in env_invariants[:2])
        if env_invariants
        else str(defaults["material_finish"])
    )

    scenes: List[ScenePromptSpec] = list(getattr(bible, "scenes", None) or [])
    scene_art_specs: List[SceneArtContinuitySpec] = []
    slot_contention_scenes: List[int] = []
    looks_registry: Dict[Tuple[str, str], SceneWardrobeStateSpec] = {}
    props_registry: Dict[str, ScenePropContinuityState] = {}

    for idx, sc in enumerate(scenes):
        sc_idx = int(getattr(sc, "scene_index", idx + 1) or (idx + 1))
        existing = getattr(sc, "art_continuity_spec", None)

        if existing is not None:
            art_spec = existing.model_copy(deep=True)
            if not art_spec.assigned_reference_slots:
                within, slots = validate_reference_slot_budget(
                    wardrobe_count=max(1, len(art_spec.wardrobe_states)),
                    env_plates=1,
                    prop_plates=1 if art_spec.prop_states else 0,
                )
                art_spec.assigned_reference_slots = slots
                if not within:
                    art_spec.slot_contention_detected = True
        else:
            w_states: List[SceneWardrobeStateSpec] = []
            if characters:
                for c_idx, ch in enumerate(characters[:2]):
                    char_id = str(getattr(ch, "name", f"CHAR_{c_idx + 1}") or f"CHAR_{c_idx + 1}")
                    w_states.append(
                        SceneWardrobeStateSpec(
                            character_id=char_id,
                            look_id=f"LOOK_{chr(65 + c_idx)}",
                            garment_summary=str(getattr(ch, "wardrobe_polarity", defaults["garment"])),
                            weathering_stage=str(defaults["weathering"]),
                            accessory_lock=list(defaults["accessories"]),
                        )
                    )
            else:
                w_states.append(
                    SceneWardrobeStateSpec(
                        character_id="HERO_SUBJECT",
                        look_id="LOOK_A",
                        garment_summary=str(defaults["garment"]),
                        weathering_stage=str(defaults["weathering"]),
                        accessory_lock=list(defaults["accessories"]),
                    )
                )

            inferred_state, inferred_surface = _infer_prop_state_from_scene(sc, defaults["anchor"])
            p_states = [
                ScenePropContinuityState(
                    prop_id=str(defaults["prop_id"]),
                    prop_name=str(defaults["prop_name"]),
                    action_state=inferred_state,
                    hand_or_anchor=str(defaults["anchor"]),
                    surface_condition=inferred_surface,
                    continuity_critical=True,
                )
            ]
            d_anchors = [
                ArtDressingAnchorSpec(
                    anchor_id=f"ANCHOR_S{sc_idx:02d}_01",
                    zone_label=env_name,
                    hero_material_finish=material_finish,
                    must_persist_across_cuts=True,
                )
            ]
            within, slots = validate_reference_slot_budget(
                wardrobe_count=len(w_states),
                env_plates=1,
                prop_plates=len(p_states),
            )
            art_spec = SceneArtContinuitySpec(
                scene_index=sc_idx,
                wardrobe_states=w_states,
                prop_states=p_states,
                dressing_anchors=d_anchors,
                assigned_reference_slots=slots,
                slot_contention_detected=not within,
                continuity_delta_note="",
                art_prompt_token="",
            )

        art_spec.art_prompt_token = format_art_continuity_token(art_spec)
        if art_spec.slot_contention_detected and sc_idx not in slot_contention_scenes:
            slot_contention_scenes.append(sc_idx)

        for w in art_spec.wardrobe_states:
            looks_registry[(w.character_id, w.look_id)] = w
        for p in art_spec.prop_states:
            props_registry[p.prop_id] = p

        sc.art_continuity_spec = art_spec
        scene_art_specs.append(art_spec)

    # Detect inter-scene continuity breaks across the populated scenes
    breaks = detect_prop_state_transitions(scenes)

    return MasterWardrobePropBible(
        bible_id=bible_id,
        archetype=domain,
        total_looks=max(1, len(looks_registry)),
        total_hero_props=len(props_registry),
        continuity_breaks_detected=len(breaks),
        slot_contention_scenes=slot_contention_scenes,
        wardrobe_looks_summary=list(looks_registry.values()),
        hero_prop_registry=list(props_registry.values()),
        scene_art_specs=scene_art_specs,
        pull_list_ready=(len(breaks) == 0),
    )


def synthesize_default_wardrobe_prop_bible(bible: MasterProductionBible) -> MasterWardrobePropBible:
    """Convenience helper to synthesize a default MasterWardrobePropBible."""
    return compile_wardrobe_prop_bible(bible)


def export_wardrobe_prop_bundle(
    bible: MasterProductionBible,
    output_dir: Union[str, Path],
) -> Dict[str, str]:
    """Exports wardrobe_prop_bible.json, prop_continuity_matrix.csv, and art_dept_pull_list.md."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    master = getattr(bible, "master_wardrobe_prop_bible", None) or compile_wardrobe_prop_bible(bible)

    json_path = out_dir / "wardrobe_prop_bible.json"
    json_path.write_text(json.dumps(master.model_dump(mode="json"), indent=2), encoding="utf-8")

    csv_path = out_dir / "prop_continuity_matrix.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Scene",
            "Prop_ID",
            "Prop_Name",
            "Action_State",
            "Hand_Or_Anchor",
            "Surface_Condition",
            "Reference_Slots",
            "Slot_Contention",
            "Continuity_Delta_Note",
        ])
        for art_spec in master.scene_art_specs:
            slots_str = "|".join(art_spec.assigned_reference_slots)
            if art_spec.prop_states:
                for p in art_spec.prop_states:
                    writer.writerow([
                        art_spec.scene_index,
                        p.prop_id,
                        p.prop_name,
                        p.action_state,
                        p.hand_or_anchor,
                        p.surface_condition,
                        slots_str,
                        art_spec.slot_contention_detected,
                        art_spec.continuity_delta_note,
                    ])
            else:
                writer.writerow([
                    art_spec.scene_index,
                    "",
                    "",
                    "",
                    "",
                    "",
                    slots_str,
                    art_spec.slot_contention_detected,
                    art_spec.continuity_delta_note,
                ])

    md_path = out_dir / "art_dept_pull_list.md"
    lines = [
        f"# Art Department Pull List — {getattr(bible, 'project_title', 'Production')}",
        "",
        f"- **Bible ID**: `{master.bible_id}`",
        f"- **Domain Archetype**: `{master.archetype}`",
        f"- **Total Wardrobe Looks**: {master.total_looks}",
        f"- **Total Hero Props**: {master.total_hero_props}",
        f"- **Continuity Breaks Detected**: {master.continuity_breaks_detected}",
        f"- **Pull List Ready**: {master.pull_list_ready}",
        "",
        "## Wardrobe Looks",
    ]
    for w in master.wardrobe_looks_summary:
        acc = ", ".join(w.accessory_lock) if w.accessory_lock else "None"
        lines.append(
            f"- **{w.character_id} (`{w.look_id}`)**: {w.garment_summary} | "
            f"Weathering: `{w.weathering_stage}` | Accessories: {acc}"
        )
    lines.append("")
    lines.append("## Hero Prop Registry")
    for p in master.hero_prop_registry:
        lines.append(
            f"- **{p.prop_id} ({p.prop_name})**: state=`{p.action_state}`, "
            f"anchor=`{p.hand_or_anchor}`, surface=`{p.surface_condition}`"
        )
    lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")

    return {
        "wardrobe_prop_bible_json": str(json_path),
        "prop_continuity_matrix_csv": str(csv_path),
        "art_dept_pull_list_md": str(md_path),
    }
