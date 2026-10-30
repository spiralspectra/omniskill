"""Runtime telemetry, stage latency profiling, and audit metric collection."""

import hashlib
import json
import re
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Union
from pydantic import BaseModel, Field

SAFE_KEYS = {"keyframe", "keyframes", "preset_key", "key_signature", "musical_key", "author", "authenticity", "authority"}
SENSITIVE_KEY_TERMS = ("token", "secret", "password", "credential", "auth_token", "api_key", "private_key", "access_key", "secret_key")
SECRET_PATTERN = re.compile(r"AIza[0-9A-Za-z\-_]+|sk-[0-9A-Za-z\-_]+")


def _is_sensitive_key(key: str) -> bool:
    """Checks if a dictionary key contains sensitive credential terms while preserving safe keys."""
    k_lower = str(key).lower()
    if k_lower in SAFE_KEYS or any(safe in k_lower for safe in ("keyframe", "preset_key", "key_signature", "musical_key", "author", "authenticity", "authority")):
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
        """Computes SHA-256 hex digests for production_bundle.json, storyboard_preview.html, and all *.svg files."""
        out_path = Path(output_dir)
        checksums: Dict[str, str] = {}
        target_files: List[Path] = []

        for name in ["production_bundle.json", "production_bible.json", "storyboard_preview.html"]:
            p = out_path / name
            if p.is_file() and p not in target_files:
                target_files.append(p)

        for svg_file in sorted(out_path.rglob("*.svg")):
            if svg_file.is_file() and svg_file not in target_files:
                target_files.append(svg_file)

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
        """Writes telemetry payload to a JSON file safely."""
        target = Path(file_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        if not self.artifact_checksums and target.parent.is_dir():
            self.compute_artifact_checksums(target.parent)
        payload = self.to_dict()
        target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
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
        return False, [f"telemetry manifest not found in {out_path}"]

    try:
        data = json.loads(telemetry_file.read_text(encoding="utf-8"))
    except Exception as exc:
        return False, [f"Failed to parse {telemetry_file.name}: {exc}"]

    checksums = data.get("artifact_checksums")
    if not checksums or not isinstance(checksums, dict):
        return False, ["artifact_checksums is empty or missing in telemetry.json"]

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

        hasher = hashlib.sha256()
        hasher.update(artifact_path.read_bytes())
        actual_hash = hasher.hexdigest()
        if actual_hash != expected_hash:
            errors.append(f"Checksum mismatch for '{rel_path}': expected {expected_hash}, got {actual_hash}")

    is_valid = len(errors) == 0
    return is_valid, errors
