"""Runtime telemetry, stage latency profiling, and audit metric collection."""

import hashlib
import json
import os
import re
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Union
from pydantic import BaseModel, Field

SAFE_KEYS = {
    "keyframe",
    "keyframes",
    "preset_key",
    "key_signature",
    "musical_key",
    "author",
    "authenticity",
    "authority",
    "prompt_token",
    "dof_prompt_token",
    "lut_prompt_token",
    "lighting_prompt_token",
    "moco_prompt_token",
    "optical_prompt_token",
    "c2pa_prompt_token",
    "provenance_prompt_token",
    "safety_prompt_token",
    "localization_prompt_token",
    "spotting_prompt_token",
    "tokens",
    "token_count",
    "token_rate",
    "dof",
    "lut",
    "cue_sheet",
    "dit_manifest",
    "s3d_prompt_token",
    "s3d_parallax_log",
    "spatial_video_manifest",
    "ad_prompt_token",
    "subtitles_ad",
    "ad_script_cue_sheet",
    "accessibility_ad_manifest",
    "estimated_total_compute_usd",
    "render_budget_ceiling_usd",
    "aicp_savings_pct",
    "total_planned_takes",
    "continuity_breaks_detected",
    "render_profile_token",
    "art_continuity_token",
    "gfx_prompt_token",
    "otio_sync_token",
    "coherence_token",
    "motion_graphics_cues_count",
    "otio_coherence_score",
    "otio_conflicts_count",
    "otio_sha256",
    "render_job_token",
    "frame_anchor_token",
    "render_qa_score",
    "promoted_takes_count",
    "treatment_token",
    "treatment_slides_count",
    "revision_deltas_count",
}
SENSITIVE_KEY_TERMS = ("token", "secret", "password", "credential", "auth_token", "api_key", "private_key", "access_key", "secret_key")
SECRET_PATTERN = re.compile(
    r"AIza[0-9A-Za-z\-_]+|sk-[0-9A-Za-z\-_]+|ya29\.[0-9A-Za-z\-_]+|ghp_[0-9A-Za-z]+|github_pat_[0-9A-Za-z_]+"
)

KNOWN_PRODUCTION_ARTIFACTS: tuple[str, ...] = (
    # Core bundle & storyboard deliverables
    "production_bundle.json",
    "production_bible.json",
    "storyboard_preview.html",
    "council_report.json",
    "council_report.md",
    # PM-FEAT-001..004: NLE timelines, shot lists, call sheets, subtitles, CDL & audio stems
    "timeline.edl",
    "sequence.fcpxml",
    "shot_list.csv",
    "call_sheet.md",
    "subtitles.srt",
    "subtitles.vtt",
    "production_grade.cdl",
    "audio_stems_manifest.json",
    # PM-FEAT-007 & PM-FEAT-008: Optical lens & Virtual Production stage
    "lens_package.csv",
    "optical_lens_framing.csv",
    "virtual_production_manifest.json",
    "unreal_dmx_patch.csv",
    "vp_stage_spec.json",
    "ndisplay_stage_manifest.json",
    "dmx_patch.csv",
    # PM-FEAT-009: MoCo kinematics
    "moco_track.json",
    "moco_track.csv",
    "moco_camera.fbx",
    "moco_camera_track.json",
    "moco_waypoints.csv",
    "moco_trajectory.fbx",
    # PM-FEAT-010: Studio lighting plot & gaffer call sheet
    "lighting_plot.json",
    "studio_lighting_plot.json",
    "gaffer_callsheet.csv",
    "gaffer_call_sheet.csv",
    # PM-FEAT-011: Depth of field & 1st AC focus puller cue sheet
    "dof_chart.json",
    "depth_of_field_chart.json",
    "optical_chart.json",
    "focus_puller_cue_sheet.csv",
    "cue_sheet.csv",
    # PM-FEAT-012: DIT 3D LUT & cart manifest
    "production_look.cube",
    "master_look.cube",
    "dit_cart_manifest.json",
    "dit_manifest.json",
    # PM-FEAT-013: Spatial Audio & Binaural Soundfield
    "spatial_audio_adm.json",
    "spatial_audio_adm_manifest.json",
    "ambisonic_b_format.csv",
    "spatial_audio_ambisonic_channels.csv",
    "webaudio_spatial_config.json",
    "spatial_webaudio_nodes.json",
    "webaudio_spatial_panner.json",
    # PM-FEAT-014: Multi-Pass VFX Compositing
    "openexr_channels.json",
    "openexr_channel_manifest.json",
    "vfx_compositing_manifest.json",
    "cryptomatte_manifest.json",
    "nuke_composite.nk",
    "nuke_composite_template.nk",
    "nuke_comp_script.nk",
    # PM-FEAT-015: HDR Broadcast Color Volume
    "hdr10_metadata.json",
    "hlg_broadcast.xml",
    "resolve_hdr_rcm.xml",
    "hdr_master_report.json",
    # PM-FEAT-016: 1st AD Stripboard & DOOD
    "movie_magic_schedule.xml",
    "stripboard_schedule.csv",
    "dood_matrix.csv",
    "stripboard_summary.json",
    # PM-FEAT-017: Physical Film Stock Emulation
    "film_emulation_spec.json",
    "film_stock_shader.dctl",
    "film_emulation.dctl",
    "film_stock.ale",
    # PM-FEAT-018: Clapper Slate & ASC-MHL
    "slate_manifest.json",
    "asc_mhl_manifest.xml",
    "clapper_slate_log.csv",
    "sound_sync.ale",
    # PM-FEAT-019: Aerial Drone Flight Paths
    "flight_path.kml",
    "flight_waypoints.gpx",
    "drone_flight_sheet.csv",
    "drone_flight_sheet.md",
    "drone_flight_manifest.json",
    # PM-FEAT-020: AICP Commercial Production Bid
    "aicp_bid_sheet.csv",
    "aicp_bid_manifest.json",
    "production_budget_topsheet.md",
    # PM-FEAT-021: Multi-Aspect Social Reframe & Cutdowns
    "reframe_crop_matrix.csv",
    "cutdown_30s.edl",
    "cutdown_15s.edl",
    "cutdown_06s.edl",
    "reframe_9x16.fcpxml",
    "delivery_reframe_manifest.json",
    # PM-FEAT-022: Broadcast QC, PSE Flash-Safety & Rights Clearance
    "broadcast_qc_certificate.md",
    "rights_clearance_matrix.csv",
    "broadcast_qc_manifest.json",
    # PM-FEAT-023: 180-Degree Continuity Axis & Blocking Floorplan
    "continuity_log.csv",
    "blocking_floorplan.svg",
    "continuity_manifest.json",
    # PM-FEAT-024: Client Review Notes, Frame-Accurate Annotations & Signoff Gate
    "review_markers.edl",
    "review_markers.fcpxml",
    "review_notes_frameio.json",
    "review_notes.csv",
    "client_signoff_report.md",
    # PM-FEAT-025: C2PA Content Credentials, AI Disclosure & Talent Likeness Consent
    "c2pa_manifest.json",
    "ai_disclosure_certificate.md",
    "likeness_consent_ledger.csv",
    # PM-FEAT-026: On-Set Safety Risk Assessment, JSA Matrix & Safety Bulletin
    "safety_bulletin.md",
    "safety_jsa_matrix.csv",
    "safety_risk_manifest.json",
    # PM-FEAT-027: Multi-Language Localization, ADR Dubbing & Broadcast TTML Subtitles
    "localization_manifest.json",
    "adr_cue_sheet.csv",
    "subtitles_localized.ttml",
    # PM-FEAT-028: Music Spotting Sheet, Sync Licensing & Split-Edit Audio Timing
    "spotting_manifest.json",
    "spotting_cue_sheet.csv",
    "spotting_sheet.md",
    "timeline_split_edits.edl",
    # PM-FEAT-029: S3D Parallax & Spatial Video
    "s3d_parallax_log.csv",
    "spatial_video_manifest.json",
    # PM-FEAT-030: Audio Description & Accessibility
    "subtitles_ad.vtt",
    "ad_script_cue_sheet.csv",
    "accessibility_ad_manifest.json",
    # PM-FEAT-031: Art Dept, Wardrobe & Prop Continuity
    "wardrobe_prop_bible.json",
    "prop_continuity_matrix.csv",
    "art_dept_pull_list.md",
    # PM-FEAT-032: AI Render Economics & Compute Take Budget
    "render_economics_manifest.json",
    "take_variant_ledger.csv",
    "ai_compute_estimate.md",
    # PM-FEAT-033: Motion Graphics, Kinetic Typography & Brand End-Card
    "motion_graphics_mogrt.json",
    "broadcast_supers.ass",
    "brand_endcard_spec.md",
    # PM-FEAT-034: OpenTimelineIO (.otio) Multi-Track Assembly & Coherence
    "production_timeline.otio",
    "coherence_matrix.json",
    "coherence_readiness_report.md",
    # PM-FEAT-035: Cloud Video Render Job Orchestration, Take QA & Rough Cut Assembly
    "render_job_manifest.json",
    "take_qa_scorecard.csv",
    "rough_cut_assembly.sh",
    # PM-FEAT-036: Director Treatment Lookbook, Pitch Deck & Bible Revision Diff
    "director_treatment_lookbook.html",
    "director_treatment_brief.md",
    "pitch_treatment_manifest.json",
    "bible_revision_diff.json",
    "bible_revision_diff.md",
)

DISCOVERABLE_ARTIFACT_EXTENSIONS: frozenset[str] = frozenset({
    ".json",
    ".html",
    ".svg",
    ".cube",
    ".edl",
    ".fcpxml",
    ".xml",
    ".csv",
    ".md",
    ".srt",
    ".vtt",
    ".ttml",
    ".cdl",
    ".fbx",
    ".nk",
    ".dctl",
    ".ale",
    ".kml",
    ".gpx",
    ".ass",
    ".otio",
    ".sh",
})

_TELEMETRY_MANIFEST_NAMES: frozenset[str] = frozenset({
    "telemetry.json",
    "telemetry_manifest.json",
})


def _is_skippable_artifact(rel_path: Path) -> bool:
    """Returns True for telemetry manifests, hidden files/dirs, and temporary files."""
    if any(part.startswith(".") for part in rel_path.parts):
        return True
    name = rel_path.name
    if name in _TELEMETRY_MANIFEST_NAMES:
        return True
    if name.startswith("~$") or name.endswith((".tmp", ".bak", ".swp", "~")) or ".tmp_" in name:
        return True
    return False


def _is_sensitive_key(key: str) -> bool:
    """Checks if a dictionary key contains sensitive credential terms while preserving safe keys."""
    k_lower = str(key).lower()
    if k_lower in SAFE_KEYS or any(safe in k_lower for safe in ("keyframe", "preset_key", "key_signature", "musical_key", "author", "authenticity", "authority", "prompt_token")):
        return False
    # Check exact match or boundary match for 'key' or 'auth' to avoid redacting legitimate descriptive fields
    if k_lower in ("key", "auth"):
        return True
    return any(term in k_lower for term in SENSITIVE_KEY_TERMS)


def _sanitize_value(val: Any) -> Any:
    """Recursively walks dicts, lists, and strings redacting sensitive keys and credential patterns."""
    if isinstance(val, dict):
        sanitized: Dict[str, Any] = {}
        for k, v in val.items():
            if _is_sensitive_key(str(k)):
                sanitized[k] = "[REDACTED]"
            else:
                sanitized[k] = _sanitize_value(v)
        return sanitized
    elif isinstance(val, list):
        return [_sanitize_value(item) for item in val]
    elif isinstance(val, tuple):
        return tuple(_sanitize_value(item) for item in val)
    elif isinstance(val, str):
        return SECRET_PATTERN.sub("[REDACTED]", val)
    return val


class StageTiming(BaseModel):
    """Execution timing and latency profile for a single pipeline stage."""
    stage_name: str
    start_time: str = ""
    end_time: str = ""
    duration_ms: float = 0.0
    details: Dict[str, Any] = Field(default_factory=dict)


class RuntimeTelemetry(BaseModel):
    """Pipeline runtime telemetry tracking model assignments, stage durations, and audits."""
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    project_title: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    model_matrix: Dict[str, str] = Field(default_factory=dict)
    stage_timings: List[StageTiming] = Field(default_factory=list)
    total_duration_ms: float = 0.0
    audit_summary: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    artifact_checksums: Dict[str, str] = Field(
        default_factory=dict,
        description="SHA-256 hex digests of generated bundle files",
    )

    def add_timing(
        self,
        stage_name: str,
        duration_ms: float,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> StageTiming:
        """Adds a completed stage timing entry and recalculates total_duration_ms."""
        now_iso = datetime.now(timezone.utc).isoformat()
        timing = StageTiming(
            stage_name=stage_name,
            start_time=start_time or now_iso,
            end_time=end_time or now_iso,
            duration_ms=round(duration_ms, 2),
            details=details or {},
        )
        self.stage_timings.append(timing)
        self.total_duration_ms = round(sum(t.duration_ms for t in self.stage_timings), 2)
        return timing

    @contextmanager
    def record_stage(self, stage_name: str, details: Optional[Dict[str, Any]] = None) -> Generator[None, None, None]:
        """Context manager to measure and record execution time of a stage."""
        start_mono = time.perf_counter()
        start_iso = datetime.now(timezone.utc).isoformat()
        try:
            yield
        finally:
            end_mono = time.perf_counter()
            end_iso = datetime.now(timezone.utc).isoformat()
            duration_ms = (end_mono - start_mono) * 1000.0
            self.add_timing(
                stage_name=stage_name,
                duration_ms=duration_ms,
                start_time=start_iso,
                end_time=end_iso,
                details=details,
            )

    def compute_artifact_checksums(self, output_dir: Union[str, Path]) -> Dict[str, str]:
        """Computes SHA-256 hex digests for known production deliverables and discovered artifacts."""
        out_path = Path(output_dir)
        checksums: Dict[str, str] = {}
        if not out_path.is_dir():
            self.artifact_checksums = checksums
            return checksums

        target_files: List[Path] = []
        seen_rel_paths: set[str] = set()

        for name in KNOWN_PRODUCTION_ARTIFACTS:
            p = out_path / name
            if p.is_file():
                rel = p.relative_to(out_path).as_posix()
                if rel not in seen_rel_paths and not _is_skippable_artifact(Path(rel)):
                    seen_rel_paths.add(rel)
                    target_files.append(p)

        discovered_files = sorted(
            (p for p in out_path.rglob("*") if p.is_file()),
            key=lambda p: p.relative_to(out_path).as_posix(),
        )
        for p in discovered_files:
            rel_obj = p.relative_to(out_path)
            if _is_skippable_artifact(rel_obj):
                continue
            if p.suffix.lower() not in DISCOVERABLE_ARTIFACT_EXTENSIONS:
                continue
            rel = rel_obj.as_posix()
            if rel not in seen_rel_paths:
                seen_rel_paths.add(rel)
                target_files.append(p)

        for file in target_files:
            rel_path = file.relative_to(out_path).as_posix()
            hasher = hashlib.sha256()
            hasher.update(file.read_bytes())
            checksums[rel_path] = hasher.hexdigest()

        self.artifact_checksums = checksums
        return checksums

    def write_manifest(self, output_dir: Union[str, Path]) -> Path:
        """Computes artifact checksums and writes telemetry.json manifest to output_dir."""
        out_path = Path(output_dir)
        self.compute_artifact_checksums(out_path)
        telemetry_file = out_path / "telemetry.json"
        return self.write_json(telemetry_file)

    def to_dict(self) -> Dict[str, Any]:
        """Converts telemetry to a dictionary with sensitive values stripped and redacted."""
        data = self.model_dump()
        return _sanitize_value(data)

    def write_json(self, file_path: Union[str, Path]) -> Path:
        """Writes telemetry payload to a JSON file safely and atomically."""
        target = Path(file_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        if not self.artifact_checksums and target.parent.is_dir():
            self.compute_artifact_checksums(target.parent)
        payload = self.to_dict()
        tmp_target = target.with_suffix(f".tmp_{os.getpid()}")
        tmp_target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        os.replace(tmp_target, target)
        return target

    def save_json(self, file_path: Union[str, Path]) -> Path:
        """Alias for write_json."""
        return self.write_json(file_path)


def verify_bundle_checksums(output_dir: Union[str, Path]) -> tuple[bool, List[str]]:
    """Loads telemetry.json from output_dir, checks that artifact_checksums is non-empty,
    recomputes SHA-256 for each recorded file, and returns (is_valid, errors)."""
    out_path = Path(output_dir)
    base_dir = out_path.resolve()
    errors: List[str] = []

    telemetry_file = out_path / "telemetry.json"
    if not telemetry_file.is_file():
        telemetry_file = out_path / "telemetry_manifest.json"
    if not telemetry_file.is_file():
        return False, [f"Bundle verification failed: telemetry.json manifest not found in directory '{out_path}'"]

    try:
        data = json.loads(telemetry_file.read_text(encoding="utf-8"))
    except Exception as exc:
        return False, [f"Failed to parse {telemetry_file.name}: {exc}"]

    checksums = data.get("artifact_checksums")
    if not checksums or not isinstance(checksums, dict):
        return False, ["artifact_checksums is empty or missing in telemetry.json"]

    # Ensure core required bundle artifacts are present in the manifest
    mandatory_files = ("production_bundle.json", "storyboard_preview.html")
    for mandatory in mandatory_files:
        if mandatory not in checksums:
            errors.append(f"Mandatory bundle file '{mandatory}' is missing from artifact_checksums manifest.")

    for rel_path, expected_hash in checksums.items():
        p = Path(rel_path)
        if p.is_absolute() or ".." in p.parts:
            errors.append(f"Path traversal or unsafe artifact path: {rel_path}")
            continue

        artifact_path = (out_path / rel_path).resolve()
        if not artifact_path.is_relative_to(base_dir):
            errors.append(f"Path traversal or unsafe artifact path: {rel_path}")
            continue

        if not artifact_path.exists() or not artifact_path.is_file():
            errors.append(f"Missing or non-file artifact: {rel_path}")
            continue

        if artifact_path.stat().st_size == 0:
            errors.append(f"Zero-byte empty artifact: {rel_path}")
            continue

        hasher = hashlib.sha256()
        hasher.update(artifact_path.read_bytes())
        actual_hash = hasher.hexdigest()
        if actual_hash != expected_hash:
            errors.append(f"Checksum mismatch for '{rel_path}': expected {expected_hash}, got {actual_hash}")

    is_valid = len(errors) == 0
    return is_valid, errors
