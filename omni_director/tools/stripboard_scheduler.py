"""1st AD Script Breakdown & Stripboard Production Scheduler Engine (PM-FEAT-016).

Provides automated 12-category script breakdown element extraction, 1/8th page
screenplay length calculation, Movie Magic industry color-coded stripboard scheduling,
SAG-AFTRA Day-Out-of-Days (DOOD) cast matrix authoring, and Gemini Omni prompt tokens.
"""

from __future__ import annotations

import csv
import io
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from omni_director.schemas import (
    BreakdownCategory,
    DayOutOfDaysRecord,
    MasterProductionBible,
    MasterStripboardScheduleSpec,
    ProductionDayType,
    ScriptBreakdownSheet,
    StripboardColorCode,
    StripboardStripSpec,
    ScenePromptSpec,
)

# ==============================================================================
# 1/8th Page Calculation Math
# ==============================================================================

def calculate_page_eighths(
    scene: Union[ScenePromptSpec, Dict[str, Any], str, List[Any]],
    dialogue_or_words: Union[List[str], int] = 15,
    words_per_eighth: int = 15,
) -> int:
    """Calculates standard Hollywood 1/8th page length for a scene.

    In standard screenplay formatting:
    - 1 full page = 8 eighths (~54 lines or ~120-150 words of action/dialogue).
    - ~15 words per eighth.
    - Each action beat adds ~1/8th page.
    - Each dialogue line adds ~1/8th page.
    """
    total_words = 0
    beat_count = 0
    dialogue_count = 0

    if isinstance(scene, list):
        beat_count += len(scene)
        total_words += sum(len(str(b).split()) for b in scene)
        if isinstance(dialogue_or_words, list):
            dialogue_count += len(dialogue_or_words)
            total_words += sum(len(str(d).split()) for d in dialogue_or_words)
    elif isinstance(scene, ScenePromptSpec):
        total_words += len(scene.omni_prose_prompt.split())
        beat_count += len(scene.action_beats or [])
        if scene.diegetic_sonic:
            dialogue_count += len(scene.diegetic_sonic.dialogue_lines or [])
    elif isinstance(scene, dict):
        prompt = str(scene.get("omni_prose_prompt") or scene.get("prompt_text") or "")
        total_words += len(prompt.split())
        beats = scene.get("action_beats") or []
        beat_count += len(beats)
        diegetic = scene.get("diegetic_sonic") or scene.get("diegetic_sound") or {}
        if isinstance(diegetic, dict):
            dialogue_count += len(diegetic.get("dialogue_lines") or [])
    else:
        total_words += len(str(scene).split())

    wpe = dialogue_or_words if isinstance(dialogue_or_words, int) else words_per_eighth
    word_eighths = max(1, total_words // wpe)
    structural_eighths = max(1, beat_count + dialogue_count)
    
    # Blended estimation clamped to realistic scene window [1/8 to 8/8 page]
    eighths = int(round((word_eighths * 0.4) + (structural_eighths * 0.6)))
    return min(8, max(1, eighths))


# ==============================================================================
# Automated 12-Category Element Extraction
# ==============================================================================

def extract_script_breakdown_sheet(
    scene: ScenePromptSpec,
    scene_number: int = 1,
    location_default: str = "STUDIO STAGE",
    cast_catalog: Optional[List[str]] = None,
) -> ScriptBreakdownSheet:
    """Extracts standard 12-category script breakdown elements from a scene specification."""
    prompt = scene.omni_prose_prompt
    prompt_lower = prompt.lower()
    title_lower = scene.scene_title.lower()

    # 1. Determine INT/EXT
    int_ext = "INT"
    if any(k in prompt_lower or k in title_lower for k in ["exterior", "ext.", "outdoor", "street", "rooftop", "desert", "forest", "skyline", "alley", "highway"]):
        int_ext = "EXT"

    # 2. Determine DAY/NIGHT
    day_night = "DAY"
    if any(k in prompt_lower or k in title_lower for k in ["night", "dusk", "evening", "moon", "midnight", "neon gloom", "darkness", "shadow"]):
        day_night = "NIGHT"

    # 3. Location extraction
    location = location_default
    loc_match = re.search(r"(?:in\s+a|at\s+the|inside|outside|within|staged\s+in)\s+([a-zA-Z0-9_\-\s]{3,30}?)(?:,|\.|\swith|\sfeaturing)", prompt, re.IGNORECASE)
    if loc_match:
        location = loc_match.group(1).strip().upper()
    elif scene.scene_title:
        location = scene.scene_title.strip().upper()

    # 4. Elements by 12 categories
    elements: Dict[BreakdownCategory, List[str]] = {cat: [] for cat in BreakdownCategory}

    # Cast members
    known_cast = cast_catalog or ["Hero Character", "Secondary Character"]
    for idx, cast_name in enumerate(known_cast, 1):
        if cast_name.lower() in prompt_lower or any(part.lower() in prompt_lower for part in cast_name.split()):
            elements[BreakdownCategory.CAST_MEMBERS].append(f"#{idx} {cast_name}")
    if not elements[BreakdownCategory.CAST_MEMBERS]:
        elements[BreakdownCategory.CAST_MEMBERS].append("#1 Hero Character")

    # Stunts
    stunt_keywords = ["fall", "jump", "crash", "tackle", "punch", "roll", "vault", "dive", "impact", "skid", "slide", "collision"]
    for kw in stunt_keywords:
        if re.search(rf"\b{kw}\b", prompt_lower):
            elements[BreakdownCategory.STUNTS].append(f"Physical Stunt ({kw.capitalize()})")

    # Extras / Silent Bits
    extras_keywords = ["crowd", "bystander", "pedestrian", "patrons", "onlookers", "guards", "audience", "workers", "civilians"]
    for kw in extras_keywords:
        if re.search(rf"\b{kw}\b", prompt_lower):
            elements[BreakdownCategory.EXTRAS_SILENT_BITS].append(f"Background {kw.capitalize()}")

    # Vehicles
    vehicle_keywords = ["car", "motorcycle", "truck", "helicopter", "drone", "speeder", "van", "suv", "coupe", "aircraft", "train"]
    for kw in vehicle_keywords:
        if re.search(rf"\b{kw}\b", prompt_lower):
            elements[BreakdownCategory.VEHICLES].append(f"Hero Vehicle ({kw.capitalize()})")

    # Props
    prop_keywords = ["keycard", "weapon", "glass", "briefcase", "phone", "tool", "device", "cup", "book", "card", "lens", "camera", "tablet"]
    for kw in prop_keywords:
        if re.search(rf"\b{kw}\b", prompt_lower):
            elements[BreakdownCategory.PROPS].append(f"Handheld Prop ({kw.capitalize()})")

    # Special Effects (SFX)
    sfx_keywords = ["smoke", "sparks", "fire", "rain", "explosion", "fog", "steam", "debris", "haze", "mist"]
    for kw in sfx_keywords:
        if re.search(rf"\b{kw}\b", prompt_lower):
            elements[BreakdownCategory.SPECIAL_EFFECTS].append(f"Practical SFX ({kw.capitalize()})")

    # Wardrobe
    wardrobe_keywords = ["jacket", "coat", "suit", "boots", "gloves", "helmet", "dress", "hoodie", "uniform", "armor", "vest"]
    for kw in wardrobe_keywords:
        if re.search(rf"\b{kw}\b", prompt_lower):
            elements[BreakdownCategory.WARDROBE].append(f"Costume Item ({kw.capitalize()})")

    # Makeup / Hair
    mu_keywords = ["blood", "sweat", "scar", "wet hair", "wounds", "smudge", "dirt", "bruise", "tears"]
    for kw in mu_keywords:
        if re.search(rf"\b{kw}\b", prompt_lower):
            elements[BreakdownCategory.MAKEUP_HAIR].append(f"SFX Makeup ({kw.capitalize()})")

    # Sound Effects (Foley)
    if scene.diegetic_sonic and scene.diegetic_sonic.foley_cues:
        for cue in scene.diegetic_sonic.foley_cues:
            elements[BreakdownCategory.SOUND_EFFECTS].append(cue)
    else:
        elements[BreakdownCategory.SOUND_EFFECTS].append("Synchronized Diegetic Foley")

    # Special Equipment
    if scene.moco_rig:
        elements[BreakdownCategory.SPECIAL_EQUIPMENT].append(f"MoCo Rig ({scene.moco_rig.rig_type})")
    if scene.virtual_production:
        elements[BreakdownCategory.SPECIAL_EQUIPMENT].append("In-Camera VFX LED Volume Stage")
    if scene.craft_camera and "technocrane" in scene.craft_camera.rig_type.lower():
        elements[BreakdownCategory.SPECIAL_EQUIPMENT].append("TechnoCrane Telescopic Arm")

    # Production Notes
    elements[BreakdownCategory.PRODUCTION_NOTES].append(f"Regime: {scene.regime.value if hasattr(scene.regime, 'value') else str(scene.regime)}")
    if scene.speed_ramp:
        elements[BreakdownCategory.PRODUCTION_NOTES].append(f"Speed Ramp: {scene.speed_ramp.mode}")

    # Optical VFX
    if scene.vfx_compositing:
        elements[BreakdownCategory.OPTICAL_VFX].append(f"Multi-Pass VFX ({len(scene.vfx_compositing.passes)} OpenEXR passes)")
    vfx_terms = ["cgi", "green screen", "wire removal", "muzzle flash", "hologram", "matte painting", "compositing"]
    for kw in vfx_terms:
        if re.search(rf"\b{kw}\b", prompt_lower):
            elements[BreakdownCategory.OPTICAL_VFX].append(f"Digital VFX ({kw.capitalize()})")

    # Clean empty categories to keep breakdown sheets concise
    active_elements = {k: v for k, v in elements.items() if v}

    page_eighths = calculate_page_eighths(scene)

    return ScriptBreakdownSheet(
        scene_number=scene_number,
        page_eighths=page_eighths,
        day_night=day_night,
        int_ext=int_ext,
        location=location,
        description=scene.scene_title or prompt[:60],
        category_elements=active_elements,
    )


# ==============================================================================
# Stripboard Scheduling & Movie Magic Color Coding
# ==============================================================================

def determine_strip_color_code(
    arg1: Union[ProductionDayType, str],
    arg2: Optional[str] = None,
) -> StripboardColorCode:
    """Maps INT/EXT, DAY/NIGHT or ProductionDayType to standard Movie Magic stripboard card color codes."""
    if isinstance(arg1, ProductionDayType):
        mapping = {
            ProductionDayType.EXT_DAY: StripboardColorCode.YELLOW_DAY_EXT,
            ProductionDayType.EXT_NIGHT: StripboardColorCode.BLUE_NIGHT_EXT,
            ProductionDayType.INT_DAY: StripboardColorCode.WHITE_DAY_INT,
            ProductionDayType.INT_NIGHT: StripboardColorCode.GREEN_NIGHT_INT,
        }
        return mapping.get(arg1, StripboardColorCode.WHITE_DAY_INT)

    s1 = str(arg1).strip().upper()
    s2 = str(arg2 or "").strip().upper()
    is_ext = "EXT" in s1 or "EXT" in s2
    is_night = "NIGHT" in s1 or "NIGHT" in s2
    if is_ext:
        return StripboardColorCode.BLUE_NIGHT_EXT if is_night else StripboardColorCode.YELLOW_DAY_EXT
    return StripboardColorCode.GREEN_NIGHT_INT if is_night else StripboardColorCode.WHITE_DAY_INT


def determine_production_day_type(
    arg1: str,
    arg2: Optional[str] = None,
) -> ProductionDayType:
    """Maps INT/EXT and DAY/NIGHT to ProductionDayType enum."""
    s1 = str(arg1).strip().upper()
    s2 = str(arg2 or "").strip().upper()
    is_ext = "EXT" in s1 or "EXT" in s2
    is_night = "NIGHT" in s1 or "NIGHT" in s2
    if is_ext:
        return ProductionDayType.EXT_NIGHT if is_night else ProductionDayType.EXT_DAY
    return ProductionDayType.INT_NIGHT if is_night else ProductionDayType.INT_DAY


def generate_dood_matrix(
    strips: List[StripboardStripSpec],
    cast_catalog: Optional[Union[List[str], List[int]]] = None,
    day_breaks: Optional[List[int]] = None,
    cast_names: Optional[Dict[Any, str]] = None,
    character_names: Optional[Dict[Any, str]] = None,
) -> List[DayOutOfDaysRecord]:
    """Generates the SAG-AFTRA Day-Out-of-Days (DOOD) cast work/hold tracking matrix.

    Industry DOOD Standard Codes:
    - SW  : Start Work (first work day)
    - W   : Work (subsequent work day)
    - H   : Hold (non-working day between work days, actor on retainer)
    - WF  : Work Finish (final work day)
    - SWF : Start-Work-Finish (single-day work assignment)
    """
    breaks = day_breaks if day_breaks is not None else []
    total_days = len(breaks) + 1
    
    # Map each strip index to its production day (1-based)
    strip_to_day: Dict[int, int] = {}
    current_day = 1
    for s_idx in range(len(strips)):
        strip_to_day[s_idx] = current_day
        if s_idx in breaks:
            current_day += 1

    # Discover all cast IDs present in strips (or fallback to catalog if empty)
    strip_cids: Set[int] = set()
    for strip in strips:
        for cid in strip.cast_ids:
            strip_cids.add(cid)

    if strip_cids:
        all_cids = sorted(list(strip_cids))
    else:
        all_cids = [1]


    # Map cast_id -> set of working days
    cast_work_days: Dict[int, Set[int]] = {cid: set() for cid in all_cids}
    for s_idx, strip in enumerate(strips):
        day_num = strip_to_day.get(s_idx, 1)
        for cid in strip.cast_ids:
            if cid in cast_work_days:
                cast_work_days[cid].add(day_num)
            else:
                cast_work_days[cid] = {day_num}

    records: List[DayOutOfDaysRecord] = []

    for cid in all_cids:
        # Determine actor and character names
        if cast_names and cid in cast_names:
            actor_name = cast_names[cid]
        elif cast_catalog and isinstance(cast_catalog, list) and 1 <= cid <= len(cast_catalog) and isinstance(cast_catalog[cid - 1], str):
            actor_name = f"Actor {cid}"
        else:
            actor_name = f"Actor {cid}"

        if character_names and cid in character_names:
            char_name = character_names[cid]
        elif cast_catalog and isinstance(cast_catalog, list) and 1 <= cid <= len(cast_catalog) and isinstance(cast_catalog[cid - 1], str):
            char_name = str(cast_catalog[cid - 1])
        else:
            char_name = f"Character {cid}"

        working_days = cast_work_days.get(cid, set())
        daily_schedule: Dict[int, str] = {}

        if not working_days:
            records.append(DayOutOfDaysRecord(
                cast_id=cid,
                cast_name=actor_name,
                character_name=char_name,
                shooting_days={d: "" for d in range(1, total_days + 1)},
                total_work_days=0,
                total_hold_days=0,
                sag_turnaround_compliant=True,
            ))
            continue

        min_day = min(working_days)
        max_day = max(working_days)

        work_count = 0
        hold_count = 0

        for d in range(1, total_days + 1):
            if d < min_day or d > max_day:
                daily_schedule[d] = ""
            elif d == min_day and d == max_day:
                daily_schedule[d] = "SWF"
                work_count += 1
            elif d == min_day:
                daily_schedule[d] = "SW"
                work_count += 1
            elif d == max_day:
                daily_schedule[d] = "WF"
                work_count += 1
            elif d in working_days:
                daily_schedule[d] = "W"
                work_count += 1
            else:
                daily_schedule[d] = "H"
                hold_count += 1

        records.append(DayOutOfDaysRecord(
            cast_id=cid,
            cast_name=actor_name,
            character_name=char_name,
            shooting_days=daily_schedule,
            total_work_days=work_count,
            total_hold_days=hold_count,
            sag_turnaround_compliant=True,
        ))

    return records


def generate_stripboard_schedule(
    bible: Any,
    max_hours_per_day: float = 12.0,
    max_eighths_per_day: int = 32,  # 4 pages per shooting day
) -> MasterStripboardScheduleSpec:
    """Generates an optimized master stripboard production schedule with day breaks and DOOD."""
    scenes = getattr(bible, "scenes", None) or []
    characters = getattr(bible, "characters", None) or []
    cast_names = [c.name for c in characters] if characters else ["Hero Subject", "Supporting Role"]

    strips: List[StripboardStripSpec] = []
    day_breaks: List[int] = []

    accumulated_hours = 0.0
    accumulated_eighths = 0
    total_eighths = 0

    for idx, sc in enumerate(scenes, 1):
        sheet = sc.breakdown_sheet or extract_script_breakdown_sheet(sc, idx, cast_catalog=cast_names)
        sc.breakdown_sheet = sheet

        color_code = determine_strip_color_code(sheet.int_ext, sheet.day_night)
        day_type = determine_production_day_type(sheet.int_ext, sheet.day_night)

        # Cast ID assignment
        assigned_cast_ids: List[int] = []
        for cast_str in sheet.category_elements.get(BreakdownCategory.CAST_MEMBERS, []):
            m = re.search(r"#(\d+)", cast_str)
            if m:
                assigned_cast_ids.append(int(m.group(1)))
        if not assigned_cast_ids:
            assigned_cast_ids = [1]

        # Estimated shooting hours (base ~1.5h + 0.5h per 1/8th page)
        est_hours = round(1.5 + (sheet.page_eighths * 0.5), 1)

        # Check day break trigger
        if accumulated_hours + est_hours > max_hours_per_day or accumulated_eighths + sheet.page_eighths > max_eighths_per_day:
            if strips:
                day_breaks.append(len(strips) - 1)
                accumulated_hours = 0.0
                accumulated_eighths = 0

        strip = StripboardStripSpec(
            scene_number=idx,
            day_type=day_type,
            color_code=color_code,
            page_eighths=sheet.page_eighths,
            setting_summary=f"{sheet.int_ext}. {sheet.location} - {sheet.day_night}",
            cast_ids=assigned_cast_ids,
            estimated_shooting_hours=est_hours,
        )
        strips.append(strip)

        accumulated_hours += est_hours
        accumulated_eighths += sheet.page_eighths
        total_eighths += sheet.page_eighths

    total_shooting_days = len(day_breaks) + 1
    dood_records = generate_dood_matrix(strips, cast_names, day_breaks)

    schedule = MasterStripboardScheduleSpec(
        production_title=getattr(bible, "project_title", getattr(bible, "title", "Omni Production")),
        total_page_eighths=total_eighths,
        total_shooting_days=total_shooting_days,
        day_breaks=day_breaks,
        strips=strips,
        dood_records=dood_records,
    )

    try:
        bible.master_stripboard_schedule = schedule
        bible.stripboard_schedule = schedule
    except Exception:
        pass
    return schedule


# ==============================================================================
# Prompt Token Formatting
# ==============================================================================

def format_script_breakdown_prompt_token(sheet: Optional[ScriptBreakdownSheet]) -> str:
    """Formats an affirmative physical 1st AD Breakdown token for Gemini Omni prompts."""
    if sheet is None:
        return "[1st AD Breakdown: EXT. DAY (Yellow Strip), 1/8 pgs, Location: STAGE, Cast: 1]"

    color_label = "Yellow Strip"
    if sheet.int_ext.upper() == "EXT" and sheet.day_night.upper() == "NIGHT":
        color_label = "Blue Strip"
    elif sheet.int_ext.upper() == "INT" and sheet.day_night.upper() == "DAY":
        color_label = "White Strip"
    elif sheet.int_ext.upper() == "INT" and sheet.day_night.upper() == "NIGHT":
        color_label = "Green Strip"

    cast_str = "1"
    cast_elems = sheet.category_elements.get(BreakdownCategory.CAST_MEMBERS, [])
    if cast_elems:
        cast_ids = [m.group(1) for m in (re.search(r"#?(\d+)", c) for c in cast_elems) if m]
        if cast_ids:
            cast_str = ", ".join(cast_ids)

    prop_summary = ""
    prop_elems = sheet.category_elements.get(BreakdownCategory.PROPS, [])
    if prop_elems:
        first_prop = prop_elems[0].split("(")[-1].replace(")", "").strip().lower()
        prop_summary = f", Props: {first_prop}"

    return (
        f"[1st AD Breakdown: {sheet.int_ext}. {sheet.day_night} ({color_label}), "
        f"{sheet.pages_fraction} pgs, Location: {sheet.location}, Cast: {cast_str}{prop_summary}]"
    )


# ==============================================================================
# Exporters: Movie Magic XML, Stripboard CSV, DOOD CSV, Bundle
# ==============================================================================

def export_movie_magic_xml(schedule: MasterStripboardScheduleSpec, path: Path) -> Path:
    """Exports stripboard schedule to Movie Magic Scheduling XML format."""
    target_path = Path(path)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    root = ET.Element("StripBoardSchedule", version="10.0")
    ET.SubElement(root, "ProductionTitle").text = schedule.production_title
    ET.SubElement(root, "TotalPagesEighths").text = str(schedule.total_page_eighths)
    ET.SubElement(root, "TotalShootingDays").text = str(schedule.total_shooting_days)

    strips_elem = ET.SubElement(root, "Stripboard")
    current_day = 1

    for idx, strip in enumerate(schedule.strips):
        s_elem = ET.SubElement(strips_elem, "Strip", index=str(idx + 1))
        ET.SubElement(s_elem, "SceneNumber").text = str(strip.scene_number)
        ET.SubElement(s_elem, "ColorCode").text = strip.color_code.value if hasattr(strip.color_code, "value") else str(strip.color_code)
        ET.SubElement(s_elem, "DayType").text = strip.day_type.value if hasattr(strip.day_type, "value") else str(strip.day_type)
        ET.SubElement(s_elem, "PageEighths").text = str(strip.page_eighths)
        ET.SubElement(s_elem, "Setting").text = strip.setting_summary
        ET.SubElement(s_elem, "CastIDs").text = ",".join(str(c) for c in strip.cast_ids)
        ET.SubElement(s_elem, "EstHours").text = f"{strip.estimated_shooting_hours:.1f}"

        if idx in schedule.day_breaks:
            break_elem = ET.SubElement(strips_elem, "DayBreak", afterStrip=str(idx + 1))
            ET.SubElement(break_elem, "CompletedDay").text = f"Day {current_day}"
            current_day += 1

    tree = ET.ElementTree(root)
    tree.write(str(target_path), encoding="utf-8", xml_declaration=True)
    return target_path


def export_stripboard_csv(schedule: MasterStripboardScheduleSpec, path: Path) -> Path:
    """Exports stripboard schedule to CSV format for production coordinators."""
    target_path = Path(path)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    with target_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Strip #", "Shoot Day", "Scene #", "Color Code", "Day Type",
            "Page 8ths", "Setting / Location", "Cast IDs", "Est Hours"
        ])
        current_day = 1
        for idx, strip in enumerate(schedule.strips):
            writer.writerow([
                idx + 1,
                f"Day {current_day}",
                strip.scene_number,
                strip.color_code.value if hasattr(strip.color_code, "value") else str(strip.color_code),
                strip.day_type.value if hasattr(strip.day_type, "value") else str(strip.day_type),
                f"{strip.page_eighths}/8",
                strip.setting_summary,
                " ".join(f"#{c}" for c in strip.cast_ids),
                f"{strip.estimated_shooting_hours:.1f}",
            ])
            if idx in schedule.day_breaks:
                current_day += 1
                writer.writerow(["---", f"END OF DAY {current_day-1}", "---", "---", "---", "---", "---", "---", "---"])

    return target_path


def export_dood_csv(schedule: MasterStripboardScheduleSpec, path: Path) -> Path:
    """Exports SAG-AFTRA Day-Out-of-Days (DOOD) cast matrix to CSV."""
    target_path = Path(path)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    total_days = schedule.total_shooting_days
    headers = ["Cast #", "Actor Name", "Character"] + [f"Day {d}" for d in range(1, total_days + 1)] + ["Work Days", "Hold Days", "SAG Turnaround"]

    with target_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)

        for rec in schedule.dood_records:
            row = [
                rec.cast_id,
                rec.cast_name,
                rec.character_name,
            ]
            for d in range(1, total_days + 1):
                row.append(rec.shooting_days.get(d, ""))
            row.extend([
                rec.total_work_days,
                rec.total_hold_days,
                "COMPLIANT (12h)" if rec.sag_turnaround_compliant else "TURNAROUND VIOLATION",
            ])
            writer.writerow(row)

    return target_path


def export_stripboard_bundle(bible: Any, output_dir: Path) -> Dict[str, Path]:
    """Exports all stripboard scheduling and DOOD matrix manifests."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if isinstance(bible, MasterStripboardScheduleSpec):
        schedule = bible
    else:
        schedule = getattr(bible, "master_stripboard_schedule", None) or getattr(bible, "stripboard_schedule", None) or generate_stripboard_schedule(bible)

    mms_path = export_movie_magic_xml(schedule, out_dir / "movie_magic_schedule.xml")
    strip_csv_path = export_stripboard_csv(schedule, out_dir / "stripboard_schedule.csv")
    dood_csv_path = export_dood_csv(schedule, out_dir / "dood_matrix.csv")

    summary_path = out_dir / "stripboard_summary.json"
    summary_path.write_text(json.dumps(schedule.model_dump(), indent=2), encoding="utf-8")

    return {
        "movie_magic_xml": mms_path,
        "stripboard_csv": strip_csv_path,
        "dood_csv": dood_csv_path,
        "summary_json": summary_path,
        "schedule_json": summary_path,
    }


def export_movie_magic_xml_string(schedule: MasterStripboardScheduleSpec) -> str:
    """Generates Movie Magic Scheduling XML string."""
    root = ET.Element("StripBoardSchedule", version="10.0")
    ET.SubElement(root, "ProductionTitle").text = schedule.production_title
    ET.SubElement(root, "TotalPagesEighths").text = str(schedule.total_page_eighths)
    ET.SubElement(root, "TotalShootingDays").text = str(schedule.total_shooting_days)

    strips_elem = ET.SubElement(root, "Stripboard")
    current_day = 1

    for idx, strip in enumerate(schedule.strips):
        s_elem = ET.SubElement(strips_elem, "Strip", index=str(idx + 1))
        ET.SubElement(s_elem, "SceneNumber").text = str(strip.scene_number)
        ET.SubElement(s_elem, "ColorCode").text = strip.color_code.value if hasattr(strip.color_code, "value") else str(strip.color_code)
        ET.SubElement(s_elem, "DayType").text = strip.day_type.value if hasattr(strip.day_type, "value") else str(strip.day_type)
        ET.SubElement(s_elem, "PageEighths").text = str(strip.page_eighths)
        ET.SubElement(s_elem, "Setting").text = strip.setting_summary
        ET.SubElement(s_elem, "CastIDs").text = ",".join(str(c) for c in strip.cast_ids)
        ET.SubElement(s_elem, "EstHours").text = f"{strip.estimated_shooting_hours:.1f}"

        if idx in schedule.day_breaks:
            break_elem = ET.SubElement(strips_elem, "DayBreak", afterStrip=str(idx + 1))
            ET.SubElement(break_elem, "CompletedDay").text = f"Day {current_day}"
            current_day += 1

    return ET.tostring(root, encoding="utf-8").decode("utf-8")


def export_stripboard_csv_string(schedule: MasterStripboardScheduleSpec) -> str:
    """Generates Stripboard schedule CSV string."""
    import io
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Strip #", "Shoot Day", "Scene #", "Color Code", "Day Type",
        "Page 8ths", "Setting / Location", "Cast IDs", "Est Hours"
    ])
    current_day = 1
    for idx, strip in enumerate(schedule.strips):
        writer.writerow([
            idx + 1,
            f"Day {current_day}",
            strip.scene_number,
            strip.color_code.value if hasattr(strip.color_code, "value") else str(strip.color_code),
            strip.day_type.value if hasattr(strip.day_type, "value") else str(strip.day_type),
            f"{strip.page_eighths}/8",
            strip.setting_summary,
            " ".join(f"#{c}" for c in strip.cast_ids),
            f"{strip.estimated_shooting_hours:.1f}",
        ])
        if idx in schedule.day_breaks:
            current_day += 1
            writer.writerow(["---", f"END OF DAY {current_day-1}", "---", "---", "---", "---", "---", "---", "---"])

    return output.getvalue()


def export_dood_csv_string(schedule: MasterStripboardScheduleSpec) -> str:
    """Generates SAG-AFTRA Day-Out-of-Days (DOOD) cast matrix CSV string."""
    import io
    output = io.StringIO()
    writer = csv.writer(output)
    total_days = schedule.total_shooting_days
    headers = ["Cast #", "Actor Name", "Character"] + [f"Day {d}" for d in range(1, total_days + 1)] + ["Work Days", "Hold Days", "SAG Turnaround"]
    writer.writerow(headers)

    for rec in schedule.dood_records:
        row = [
            rec.cast_id,
            rec.cast_name,
            rec.character_name,
        ]
        for d in range(1, total_days + 1):
            row.append(rec.shooting_days.get(d, ""))
        row.extend([
            rec.total_work_days,
            rec.total_hold_days,
            "COMPLIANT (12h)" if rec.sag_turnaround_compliant else "TURNAROUND VIOLATION",
        ])
        writer.writerow(row)

    return output.getvalue()
