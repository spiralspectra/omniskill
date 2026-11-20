"""Client Review Notes, Frame-Accurate Annotations & Signoff Gate Engine (PM-FEAT-024).

Pure-Python post-production review & client approval engine providing:
- Per-scene and master client/agency signoff synthesis with live-render approval gating
- Frame-accurate pin annotations & conversational Gemini Omni edit delta compilation
- DaVinci Resolve / Avid CMX 3600 locator marker EDL (* LOC: HH:MM:SS:FF <COLOR> <COMMENT>)
- Final Cut Pro FCPXML v1.10 timeline markers (<marker start="..." duration="1/24s" value="..."/>)
- Frame.io v4-compatible JSON annotation export, CSV review ledger, and Markdown signoff report
"""

from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from xml.sax.saxutils import escape as xml_escape

from omni_director.schemas import (
    MarkerColorTag,
    MasterClientReviewSpec,
    MasterProductionBible,
    ReviewAnnotationSpec,
    ReviewApprovalStatus,
    ReviewerRole,
    ReviewPinCoordinate,
    ScenePromptSpec,
    SceneReviewSignoffSpec,
)


def _seconds_to_smpte(seconds: float, fps: int = 24) -> str:
    total_frames = max(0, int(round(float(seconds) * fps)))
    ff = total_frames % fps
    total_sec = total_frames // fps
    ss = total_sec % 60
    mm = (total_sec // 60) % 60
    hh = total_sec // 3600
    return f"{hh:02d}:{mm:02d}:{ss:02d}:{ff:02d}"


def _parse_scene_window(
    scene: Optional[ScenePromptSpec],
    idx: int,
    total_scenes: int = 2,
    total_runtime: float = 10.0,
) -> Tuple[float, float]:
    if scene is not None:
        ts = getattr(scene, "timestamp_range", "") or ""
        m = re.search(r"(\d+):(\d+)\s*[-–—]\s*(\d+):(\d+)", ts)
        if m:
            m1, s1, m2, s2 = map(int, m.groups())
            start_s = float(m1 * 60 + s1)
            end_s = float(m2 * 60 + s2)
            if end_s > start_s:
                return start_s, end_s
    per_scene = max(2.0, float(total_runtime) / max(1, total_scenes))
    return (idx - 1) * per_scene, idx * per_scene


def compile_review_note_to_delta(
    note: ReviewAnnotationSpec,
    scene: Optional[ScenePromptSpec] = None,
) -> str:
    """Compiles a timestamped stakeholder review annotation into a Gemini Omni conversational edit delta."""
    s_idx = scene.scene_index if scene is not None else note.scene_index
    s_title = (scene.scene_title if scene is not None else "") or f"Scene {s_idx}"
    param = (note.target_parameter or "visual").strip().lower()
    comment = note.comment.strip().rstrip(".")
    pin_clause = ""
    if note.pin is not None:
        pin_clause = f" centered at frame coordinates ({note.pin.x_norm:.2f}, {note.pin.y_norm:.2f})"

    if param in ("lighting", "color", "exposure", "lut"):
        directive = f"Adjust lighting/color grading{pin_clause}: {comment}"
    elif param in ("camera", "framing", "lens", "blocking"):
        directive = f"Refine camera framing and blocking{pin_clause}: {comment}"
    elif param in ("audio", "sound", "foley", "bgm"):
        directive = f"Rebalance synchronized diegetic audio/foley mix: {comment}"
    elif param in ("pacing", "timing", "motion"):
        directive = f"Refine kinetic beat timing while preserving 1.0x physical inertia: {comment}"
    else:
        directive = f"Apply targeted {param} refinement{pin_clause}: {comment}"

    return (
        f"Review Edit Delta [Scene {s_idx} '{s_title}' @ {note.timecode_smpte}]: "
        f"{directive}. Preserve <image_1> character identity and <image_2> environment invariants."
    )


def format_review_prompt_token(
    spec: Union[SceneReviewSignoffSpec, MasterClientReviewSpec, Dict[str, Any]],
) -> str:
    """Formats a concise Gemini Omni prompt-auditable client review gate token."""
    if isinstance(spec, dict):
        rev = int(spec.get("revision", 1))
        status = str(spec.get("approval_status", spec.get("overall_status", "approved")))
        open_notes = int(spec.get("open_notes_count", 0))
    elif isinstance(spec, MasterClientReviewSpec):
        rev = spec.revision
        status = spec.overall_status.value if hasattr(spec.overall_status, "value") else str(spec.overall_status)
        open_notes = spec.open_notes_count
    else:
        rev = spec.revision
        status = spec.approval_status.value if hasattr(spec.approval_status, "value") else str(spec.approval_status)
        open_notes = spec.open_notes_count

    return f"[REVIEW_GATE: rev={rev} status={status} open_notes={open_notes}]"


def synthesize_scene_review_signoff(
    scene: Optional[ScenePromptSpec] = None,
    scene_index: int = 1,
    domain: str = "architectural_sanctuary",
    fps: int = 24,
) -> SceneReviewSignoffSpec:
    """Synthesizes an approved SceneReviewSignoffSpec with calibrated frame-accurate annotation."""
    eff_idx = scene.scene_index if scene is not None else max(1, int(scene_index))
    eff_title = (scene.scene_title if scene is not None else "") or f"Scene {eff_idx}"

    start_s, end_s = _parse_scene_window(scene, eff_idx)
    mid_s = round(start_s + max(0.5, (end_s - start_s) * 0.4), 2)
    tc_smpte = _seconds_to_smpte(mid_s, fps=fps)
    frame_num = int(round(mid_s * fps))

    domain_note_map: Dict[str, Tuple[str, str]] = {
        "culinary_asmr": ("lighting", "Warm tungsten key and tactile steam specular highlights verified for appetite appeal."),
        "luxury_fashion": ("wardrobe", "High-contrast silhouette edge separation and 2x oval bokeh falloff approved."),
        "automotive_robotics": ("camera", "Rolling rig velocity, specular paint reflections, and 180-deg travel axis verified."),
        "kinetic_action": ("pacing", "1.0x real-time kinetic contact chain and impact foley transient locked."),
        "tech_hardware": ("lighting", "Cleanroom specular rim highlight and product hero legibility verified."),
        "architectural_sanctuary": ("framing", "Symmetric architectural perspective, daylight shaft balance, and room tone approved."),
    }
    param, msg = domain_note_map.get(
        domain,
        ("lighting", "Composition, lighting contrast, and brand anchor verified."),
    )

    note = ReviewAnnotationSpec(
        note_id=f"REV-S{eff_idx:02d}-01",
        scene_index=eff_idx,
        timecode_smpte=tc_smpte,
        timecode_sec=mid_s,
        frame_number=frame_num,
        reviewer_role=ReviewerRole.DIRECTOR if eff_idx % 2 == 1 else ReviewerRole.CLIENT_BRAND,
        reviewer_name="Lead Creative Director" if eff_idx % 2 == 1 else "Brand Creative Lead",
        marker_color=MarkerColorTag.GREEN,
        comment=msg,
        target_parameter=param,
        resolved=True,
        blocking_gate=False,
        pin=ReviewPinCoordinate(x_norm=0.5, y_norm=0.46, radius_norm=0.06),
    )
    note.compiled_edit_delta = compile_review_note_to_delta(note, scene)

    spec = SceneReviewSignoffSpec(
        scene_index=eff_idx,
        scene_title=eff_title,
        revision=1,
        approval_status=ReviewApprovalStatus.APPROVED,
        annotations=[note],
        open_notes_count=0,
        resolved_notes_count=1,
        signoff_by="Director & Client Brand Producer",
    )
    spec.prompt_token = format_review_prompt_token(spec)
    return spec


def synthesize_default_client_review(
    bible: Union[MasterProductionBible, str, None],
    fps: int = 24,
) -> MasterClientReviewSpec:
    """Synthesizes a complete MasterClientReviewSpec covering all scenes in the bible."""
    if isinstance(bible, MasterProductionBible):
        title = bible.project_title
        domain = getattr(bible, "domain_archetype", None) or "architectural_sanctuary"
        scenes = list(bible.scenes or [])
    else:
        title = str(bible or "Commercial Production")
        domain = "architectural_sanctuary"
        scenes = []

    scene_reviews = [
        synthesize_scene_review_signoff(sc, scene_index=sc.scene_index, domain=domain, fps=fps)
        for sc in scenes
    ]
    if not scene_reviews:
        scene_reviews = [synthesize_scene_review_signoff(None, scene_index=1, domain=domain, fps=fps)]

    total_notes = sum(len(sr.annotations) for sr in scene_reviews)
    open_notes = sum(sr.open_notes_count for sr in scene_reviews)
    blocking_notes = sum(
        1 for sr in scene_reviews for a in sr.annotations if not a.resolved and a.blocking_gate
    )
    has_changes = any(sr.approval_status == ReviewApprovalStatus.CHANGES_REQUESTED for sr in scene_reviews)
    overall = ReviewApprovalStatus.CHANGES_REQUESTED if has_changes else ReviewApprovalStatus.APPROVED
    ready = (not has_changes) and (blocking_notes == 0)

    manifest = MasterClientReviewSpec(
        project_title=title,
        revision=1,
        overall_status=overall,
        scene_reviews=scene_reviews,
        total_notes_count=total_notes,
        open_notes_count=open_notes,
        blocking_notes_count=blocking_notes,
        ready_for_live_render=ready,
        signoff_summary=(
            f"Revision 1 approved across {len(scene_reviews)} scene(s); live render gate cleared."
            if ready
            else f"Revision 1 blocked: {blocking_notes} blocking review note(s) require resolution."
        ),
    )
    manifest.prompt_token = format_review_prompt_token(manifest)
    return manifest


def _resolve_review_manifest(
    spec_or_bible: Union[MasterClientReviewSpec, SceneReviewSignoffSpec, MasterProductionBible],
) -> MasterClientReviewSpec:
    if isinstance(spec_or_bible, MasterClientReviewSpec):
        return spec_or_bible
    if isinstance(spec_or_bible, SceneReviewSignoffSpec):
        m = MasterClientReviewSpec(
            project_title=spec_or_bible.scene_title or f"Scene {spec_or_bible.scene_index}",
            revision=spec_or_bible.revision,
            overall_status=spec_or_bible.approval_status,
            scene_reviews=[spec_or_bible],
        )
        m.prompt_token = format_review_prompt_token(m)
        return m
    existing = getattr(spec_or_bible, "master_client_review", None) or getattr(spec_or_bible, "client_review", None)
    if isinstance(existing, MasterClientReviewSpec):
        return existing
    return synthesize_default_client_review(spec_or_bible)


def generate_resolve_marker_edl(
    spec_or_bible: Union[MasterClientReviewSpec, SceneReviewSignoffSpec, MasterProductionBible],
    fps: int = 24,
) -> str:
    """Generates a CMX 3600 EDL with DaVinci Resolve / Avid locator markers (* LOC: HH:MM:SS:FF <COLOR> <COMMENT>)."""
    manifest = _resolve_review_manifest(spec_or_bible)
    title_upper = re.sub(r"[^A-Z0-9 _-]", "", manifest.project_title.upper())[:56] or "OMNI REVIEW"
    lines: List[str] = [
        f"TITLE: {title_upper} REVIEW MARKERS",
        "FCM: NON-DROP FRAME",
        "",
    ]

    event_idx = 1
    for sr in manifest.scene_reviews:
        annotations = list(sr.annotations)
        if not annotations:
            annotations = [
                ReviewAnnotationSpec(
                    note_id=f"REV-S{sr.scene_index:02d}-00",
                    scene_index=sr.scene_index,
                    timecode_smpte=_seconds_to_smpte(float((sr.scene_index - 1) * 5), fps=fps),
                    timecode_sec=float((sr.scene_index - 1) * 5),
                    frame_number=(sr.scene_index - 1) * 5 * fps,
                    reviewer_role=ReviewerRole.DIRECTOR,
                    marker_color=MarkerColorTag.GREEN if sr.approval_status == ReviewApprovalStatus.APPROVED else MarkerColorTag.RED,
                    comment=f"Scene {sr.scene_index} signoff status: {sr.approval_status.value}",
                    resolved=sr.approval_status != ReviewApprovalStatus.CHANGES_REQUESTED,
                )
            ]

        for note in annotations:
            tc_in = note.timecode_smpte if re.match(r"^\d{2}:\d{2}:\d{2}:\d{2}$", note.timecode_smpte or "") else _seconds_to_smpte(note.timecode_sec, fps=fps)
            tc_out = _seconds_to_smpte(note.timecode_sec + (1.0 / max(1, fps)), fps=fps)
            color_s = note.marker_color.value if hasattr(note.marker_color, "value") else str(note.marker_color)
            role_s = note.reviewer_role.value if hasattr(note.reviewer_role, "value") else str(note.reviewer_role)
            status_tag = "RESOLVED" if note.resolved else "OPEN"
            comment_clean = re.sub(r"\s+", " ", note.comment).strip()

            lines.append(f"{event_idx:03d}  AX       V     C        {tc_in} {tc_out} {tc_in} {tc_out}")
            lines.append(f"* FROM CLIP NAME: SCENE_{sr.scene_index:02d}_PLATE.MP4")
            lines.append(f"* LOC: {tc_in} {color_s} [{note.note_id} | {role_s} | {status_tag}] {comment_clean}")
            lines.append("")
            event_idx += 1

    return "\n".join(lines).strip() + "\n"


def _scene_duration_sec(scene: Optional[ScenePromptSpec], fallback_sec: float = 5.0) -> float:
    if scene is not None:
        ts = getattr(scene, "timestamp_range", "") or ""
        m = re.search(r"(\d+):(\d+)\s*[-–—]\s*(\d+):(\d+)", ts)
        if m:
            m1, s1, m2, s2 = map(int, m.groups())
            start_s = float(m1 * 60 + s1)
            end_s = float(m2 * 60 + s2)
            if end_s > start_s:
                return end_s - start_s
        m_ext = re.search(r"\+(\d+(?:\.\d+)?)\s*s", ts, re.IGNORECASE)
        if m_ext:
            val = float(m_ext.group(1))
            if val > 0:
                return val
    return fallback_sec


def generate_review_fcpxml_markers(
    spec_or_bible: Union[MasterClientReviewSpec, SceneReviewSignoffSpec, MasterProductionBible],
    fps: int = 24,
) -> str:
    """Generates a valid FCPXML v1.10 timeline embedding frame-accurate <marker> elements."""
    manifest = _resolve_review_manifest(spec_or_bible)
    title_esc = xml_escape(manifest.project_title)

    scene_map: Dict[int, ScenePromptSpec] = (
        {sc.scene_index: sc for sc in (spec_or_bible.scenes or [])}
        if isinstance(spec_or_bible, MasterProductionBible)
        else {}
    )

    resources_xml = [
        f'        <format id="r1" name="FFVideoFormat1080p{fps}" frameDuration="1/{fps}s" width="1920" height="1080" colorSpace="1-1-1 (Rec. 709)"/>'
    ]
    spine_xml: List[str] = []

    offset_frames = 0
    for sr in manifest.scene_reviews:
        clip_dur_sec = _scene_duration_sec(scene_map.get(sr.scene_index), fallback_sec=5.0)
        clip_frames = max(1, int(round(clip_dur_sec * fps)))
        scene_start_sec = offset_frames / fps
        res_id = f"r{sr.scene_index + 1}"
        resources_xml.append(
            f'        <asset id="{res_id}" name="SCENE_{sr.scene_index:02d}" start="0s" duration="{clip_frames}/{fps}s" hasVideo="1" hasAudio="1" format="r1"/>'
        )
        markers_xml: List[str] = []
        for note in sr.annotations:
            rel_sec = note.timecode_sec - scene_start_sec if note.timecode_sec >= scene_start_sec else note.timecode_sec
            local_frames = max(0, min(clip_frames - 1, int(round(rel_sec * fps))))
            color_s = note.marker_color.value if hasattr(note.marker_color, "value") else str(note.marker_color)
            role_s = note.reviewer_role.value if hasattr(note.reviewer_role, "value") else str(note.reviewer_role)
            val_esc = xml_escape(f"[{note.note_id} | {color_s} | {role_s}] {note.comment}")
            note_esc = xml_escape(note.compiled_edit_delta or note.comment)
            completed_attr = ' completed="1"' if note.resolved else ' completed="0"'
            markers_xml.append(
                f'                            <marker start="{local_frames}/{fps}s" duration="1/{fps}s" value="{val_esc}" note="{note_esc}"{completed_attr}/>'
            )

        if not markers_xml:
            markers_xml.append(
                f'                            <marker start="0/{fps}s" duration="1/{fps}s" value="{xml_escape(f"Scene {sr.scene_index} Approved")}"/>'
            )

        clip_name = xml_escape(f"Scene_{sr.scene_index:02d}_{sr.scene_title[:36]}")
        spine_xml.append(
            f'                        <asset-clip name="{clip_name}" ref="{res_id}" offset="{offset_frames}/{fps}s" duration="{clip_frames}/{fps}s" start="0s" format="r1">\n'
            + "\n".join(markers_xml) + "\n"
            + '                        </asset-clip>'
        )
        offset_frames += clip_frames

    total_frames = max(fps, offset_frames)

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<fcpxml version="1.10">\n'
        '    <resources>\n'
        + "\n".join(resources_xml) + "\n"
        '    </resources>\n'
        '    <library>\n'
        f'        <event name="{title_esc} Review">\n'
        f'            <project name="{title_esc} Review Markers">\n'
        f'                <sequence format="r1" duration="{total_frames}/{fps}s" tcStart="0s" tcFormat="NDF" audioLayout="stereo" audioRate="48k">\n'
        '                    <spine>\n'
        + "\n".join(spine_xml) + "\n"
        '                    </spine>\n'
        '                </sequence>\n'
        '            </project>\n'
        '        </event>\n'
        '    </library>\n'
        '</fcpxml>\n'
    )


def generate_frameio_review_json(
    spec_or_bible: Union[MasterClientReviewSpec, SceneReviewSignoffSpec, MasterProductionBible],
) -> str:
    """Serializes stakeholder review notes into a Frame.io-compatible JSON payload."""
    manifest = _resolve_review_manifest(spec_or_bible)
    comments: List[Dict[str, Any]] = []
    for sr in manifest.scene_reviews:
        for note in sr.annotations:
            role_s = note.reviewer_role.value if hasattr(note.reviewer_role, "value") else str(note.reviewer_role)
            color_s = note.marker_color.value if hasattr(note.marker_color, "value") else str(note.marker_color)
            comments.append({
                "id": note.note_id,
                "scene_index": note.scene_index,
                "timestamp": note.timecode_sec,
                "timecode_smpte": note.timecode_smpte,
                "frame": note.frame_number,
                "author_role": role_s,
                "author_name": note.reviewer_name,
                "color": color_s,
                "target_parameter": note.target_parameter,
                "text": note.comment,
                "annotation_pin": note.pin.model_dump() if note.pin else None,
                "resolved": note.resolved,
                "blocking_gate": note.blocking_gate,
                "compiled_edit_delta": note.compiled_edit_delta,
            })

    payload = {
        "schema_format": "frameio_review_v4_compatible",
        "project_title": manifest.project_title,
        "revision": manifest.revision,
        "overall_status": manifest.overall_status.value if hasattr(manifest.overall_status, "value") else str(manifest.overall_status),
        "ready_for_live_render": manifest.ready_for_live_render,
        "total_notes_count": manifest.total_notes_count,
        "open_notes_count": manifest.open_notes_count,
        "blocking_notes_count": manifest.blocking_notes_count,
        "signoff_summary": manifest.signoff_summary,
        "comments": comments,
        "scene_signoffs": [sr.model_dump() for sr in manifest.scene_reviews],
    }
    return json.dumps(payload, indent=2)


def generate_review_notes_csv(
    spec_or_bible: Union[MasterClientReviewSpec, SceneReviewSignoffSpec, MasterProductionBible],
) -> str:
    """Exports all frame-accurate review annotations into a structured CSV ledger."""
    manifest = _resolve_review_manifest(spec_or_bible)
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow([
        "note_id",
        "scene_index",
        "scene_title",
        "timecode_smpte",
        "timecode_sec",
        "frame_number",
        "reviewer_role",
        "reviewer_name",
        "marker_color",
        "target_parameter",
        "resolved",
        "blocking_gate",
        "pin_x",
        "pin_y",
        "comment",
        "compiled_edit_delta",
    ])
    for sr in manifest.scene_reviews:
        for note in sr.annotations:
            role_s = note.reviewer_role.value if hasattr(note.reviewer_role, "value") else str(note.reviewer_role)
            color_s = note.marker_color.value if hasattr(note.marker_color, "value") else str(note.marker_color)
            writer.writerow([
                note.note_id,
                note.scene_index,
                sr.scene_title,
                note.timecode_smpte,
                f"{note.timecode_sec:.2f}",
                note.frame_number,
                role_s,
                note.reviewer_name,
                color_s,
                note.target_parameter,
                "TRUE" if note.resolved else "FALSE",
                "TRUE" if note.blocking_gate else "FALSE",
                f"{note.pin.x_norm:.3f}" if note.pin else "",
                f"{note.pin.y_norm:.3f}" if note.pin else "",
                note.comment,
                note.compiled_edit_delta,
            ])
    return buf.getvalue()


def generate_client_signoff_md(
    spec_or_bible: Union[MasterClientReviewSpec, SceneReviewSignoffSpec, MasterProductionBible],
) -> str:
    """Generates an executive Client Review & Live-Render Signoff Report in Markdown."""
    manifest = _resolve_review_manifest(spec_or_bible)
    status_s = manifest.overall_status.value if hasattr(manifest.overall_status, "value") else str(manifest.overall_status)
    gate_badge = "READY FOR LIVE RENDER" if manifest.ready_for_live_render else "BLOCKED PENDING SIGN-OFF"

    lines = [
        f"# Client Review & Stakeholder Signoff Report: {manifest.project_title}",
        "",
        f"- **Revision**: `v{manifest.revision}`",
        f"- **Overall Status**: `{status_s.upper()}`",
        f"- **Live-Render Gate**: **`{gate_badge}`**",
        f"- **Total Notes**: `{manifest.total_notes_count}` | **Open**: `{manifest.open_notes_count}` | **Blocking**: `{manifest.blocking_notes_count}`",
        f"- **Summary**: {manifest.signoff_summary}",
        "",
        "## Per-Scene Signoff Matrix",
        "| Scene | Title | Revision | Status | Open Notes | Resolved | Signoff Authority |",
        "|---|---|---|---|---|---|---|",
    ]

    for sr in manifest.scene_reviews:
        st_s = sr.approval_status.value if hasattr(sr.approval_status, "value") else str(sr.approval_status)
        lines.append(
            f"| {sr.scene_index} | {sr.scene_title} | v{sr.revision} | `{st_s.upper()}` | "
            f"{sr.open_notes_count} | {sr.resolved_notes_count} | {sr.signoff_by} |"
        )

    lines.extend([
        "",
        "## Timestamped Annotation & Edit Delta Log",
        "| Note ID | Scene | Timecode | Role | Color | Status | Comment | Compiled Edit Delta |",
        "|---|---|---|---|---|---|---|---|",
    ])
    for sr in manifest.scene_reviews:
        for note in sr.annotations:
            role_s = note.reviewer_role.value if hasattr(note.reviewer_role, "value") else str(note.reviewer_role)
            color_s = note.marker_color.value if hasattr(note.marker_color, "value") else str(note.marker_color)
            st_label = "RESOLVED" if note.resolved else ("BLOCKING" if note.blocking_gate else "OPEN")
            lines.append(
                f"| `{note.note_id}` | {note.scene_index} | `{note.timecode_smpte}` | `{role_s}` | "
                f"`{color_s}` | `{st_label}` | {note.comment} | {note.compiled_edit_delta or 'N/A'} |"
            )

    return "\n".join(lines) + "\n"


def export_review_bundle(
    bible_or_spec: Union[MasterProductionBible, MasterClientReviewSpec, SceneReviewSignoffSpec],
    output_dir: Union[str, Path],
    fps: int = 24,
) -> Dict[str, Path]:
    """Exports all PM-FEAT-024 client review artifacts into output_dir.

    Writes:
    - review_markers.edl
    - review_markers.fcpxml
    - review_notes_frameio.json
    - review_notes.csv
    - client_signoff_report.md
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    manifest = _resolve_review_manifest(bible_or_spec)

    edl_p = out_path / "review_markers.edl"
    fcpxml_p = out_path / "review_markers.fcpxml"
    frameio_p = out_path / "review_notes_frameio.json"
    csv_p = out_path / "review_notes.csv"
    md_p = out_path / "client_signoff_report.md"

    edl_p.write_text(generate_resolve_marker_edl(manifest, fps=fps), encoding="utf-8")
    fcpxml_p.write_text(generate_review_fcpxml_markers(manifest, fps=fps), encoding="utf-8")
    frameio_p.write_text(generate_frameio_review_json(manifest), encoding="utf-8")
    csv_p.write_text(generate_review_notes_csv(manifest), encoding="utf-8")
    md_p.write_text(generate_client_signoff_md(manifest), encoding="utf-8")

    return {
        "review_markers_edl": edl_p,
        "review_markers_fcpxml": fcpxml_p,
        "review_notes_frameio_json": frameio_p,
        "review_notes_csv": csv_p,
        "client_signoff_report_md": md_p,
    }
