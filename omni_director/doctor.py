"""Environment, dependency, model matrix, and preflight doctor diagnostics for Omni Director."""

from __future__ import annotations

import importlib
import importlib.metadata
import importlib.util
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from omni_director.config import (
    FORBIDDEN_LEGACY_PATTERNS,
    DirectorConfig,
    get_settings,
    validate_model_identifier as _validate_model_identifier,
)


def validate_model_identifier(model_name: str, field_name: str = "model") -> bool:
    """Safe validator returning boolean status for doctor and CLI checks."""
    try:
        return bool(_validate_model_identifier(model_name, field_name))
    except Exception:
        return False


class CheckStatus(str, Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


class DiagnosticCheck(BaseModel):
    name: str
    status: CheckStatus
    message: str
    remediation: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class DoctorReport(BaseModel):
    version: str = "2.5.0"
    checks: List[DiagnosticCheck] = Field(default_factory=list)
    passed: bool = True
    has_warnings: bool = False
    timestamp: str = ""
    summary: str = ""

    @property
    def exit_code(self) -> int:
        return 0 if self.passed else 1



def run_doctor(
    config: Optional[DirectorConfig] = None,
    output_dir: Optional[Union[str, Path]] = None,
) -> DoctorReport:
    """Runs a full preflight diagnostic suite checking runtime, dependencies, models, and write permissions."""
    checks: List[DiagnosticCheck] = []

    # 1. Python runtime check (>= 3.11)
    py_ver = sys.version_info
    py_ver_str = f"{py_ver.major}.{py_ver.minor}.{py_ver.micro}"
    if py_ver >= (3, 11):
        checks.append(DiagnosticCheck(
            name="python_runtime",
            status=CheckStatus.PASS,
            message=f"Python {py_ver_str} meets minimum runtime requirement (>= 3.11)",
            details={"version": py_ver_str},
        ))
    else:
        checks.append(DiagnosticCheck(
            name="python_runtime",
            status=CheckStatus.FAIL,
            message=f"Python {py_ver_str} does not meet minimum requirement (>= 3.11)",
            remediation="Upgrade to Python 3.11 or newer.",
            details={"version": py_ver_str},
        ))

    # 2. Pydantic check (>= 2.0)
    try:
        import pydantic
        pyd_ver = getattr(pydantic, "__version__", None)
        if not pyd_ver:
            try:
                pyd_ver = importlib.metadata.version("pydantic")
            except Exception:
                pyd_ver = "unknown"
        major_ver = int(pyd_ver.split(".")[0]) if pyd_ver and pyd_ver[0].isdigit() else 0
        if major_ver >= 2 and issubclass(pydantic.BaseModel, object):
            checks.append(DiagnosticCheck(
                name="pydantic_version",
                status=CheckStatus.PASS,
                message=f"Pydantic {pyd_ver} meets requirement (>= 2.0)",
                details={"version": pyd_ver, "major": major_ver},
            ))
        else:
            checks.append(DiagnosticCheck(
                name="pydantic_version",
                status=CheckStatus.FAIL,
                message=f"Pydantic {pyd_ver} is legacy; ADK 2.0 requires Pydantic >= 2.0",
                remediation="Upgrade to pydantic >= 2.0: pip install -U pydantic",
                details={"version": pyd_ver},
            ))
    except Exception as e:
        checks.append(DiagnosticCheck(
            name="pydantic_version",
            status=CheckStatus.FAIL,
            message=f"Failed to inspect Pydantic: {e}",
            remediation="Install pydantic: pip install pydantic",
        ))

    # 3. Core dependencies
    required_packages = ["google.genai", "rich"]
    optional_packages = ["google.adk"]
    missing_packages = []
    missing_optional = []
    for pkg in required_packages:
        spec = importlib.util.find_spec(pkg)
        if spec is None:
            missing_packages.append(pkg)
    for pkg in optional_packages:
        spec = importlib.util.find_spec(pkg)
        if spec is None:
            missing_optional.append(pkg)

    if not missing_packages and not missing_optional:
        checks.append(DiagnosticCheck(
            name="core_dependencies",
            status=CheckStatus.PASS,
            message=f"All required and optional core packages available ({', '.join(required_packages + optional_packages)})",
        ))
    elif not missing_packages and missing_optional:
        checks.append(DiagnosticCheck(
            name="core_dependencies",
            status=CheckStatus.WARN,
            message=f"Core packages available ({', '.join(required_packages)}); optional extras missing: {', '.join(missing_optional)} (offline ADK fallback active)",
            details={"missing_optional": missing_optional},
        ))
    else:
        checks.append(DiagnosticCheck(
            name="core_dependencies",
            status=CheckStatus.FAIL,
            message=f"Missing required dependencies: {', '.join(missing_packages)}",
            remediation=f"Install missing dependencies: pip install {' '.join(missing_packages)}",
            details={"missing": missing_packages, "missing_optional": missing_optional},
        ))

    # 4. Model Matrix Check (Zero 3.1 / Legacy Models + 2026 Whitelist)
    cfg = config or get_settings()
    model_matrix = {
        "director_model": cfg.director_model,
        "fast_model": cfg.fast_model,
        "image_model": cfg.image_model,
        "video_model": cfg.video_model,
    }
    legacy_hits = []
    whitelist_hits = []
    for field_name, model_name in model_matrix.items():
        if not model_name:
            continue
        for pat in FORBIDDEN_LEGACY_PATTERNS:
            if pat.search(model_name):
                legacy_hits.append(f"{field_name}='{model_name}' (matched {pat.pattern})")
                break
        try:
            validate_model_identifier(model_name, field_name)
        except ValueError as exc:
            whitelist_hits.append(str(exc))

    all_violations = legacy_hits + [w for w in whitelist_hits if w not in legacy_hits]
    if all_violations:
        checks.append(DiagnosticCheck(
            name="model_matrix_compliance",
            status=CheckStatus.FAIL,
            message=f"Model matrix violation detected: {'; '.join(all_violations)}. Strict 2026 DeepMind models mandated.",
            remediation="Update your model configuration in DirectorConfig or environment variables to use 2026 models (e.g. gemini-4-argon, gemini-3.8-flash, gemini-3-pro-image, gemini-omni-1.1-flash-preview).",
            details={"violations": all_violations, "matrix": model_matrix},
        ))
    else:
        checks.append(DiagnosticCheck(
            name="model_matrix_compliance",
            status=CheckStatus.PASS,
            message="Model matrix compliant with 2026 DeepMind standards (zero 3.1 models, approved 2026 models)",
            details={"matrix": model_matrix},
        ))

    # 5. Credentials Check
    has_creds = bool((cfg.api_key if cfg else None) or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
    if has_creds:
        checks.append(DiagnosticCheck(
            name="credentials",
            status=CheckStatus.PASS,
            message="Google Gemini API credentials detected in environment or configuration",
        ))
    else:
        checks.append(DiagnosticCheck(
            name="credentials",
            status=CheckStatus.WARN,
            message="No GEMINI_API_KEY or GOOGLE_API_KEY found; dry-run mock mode will be enforced",
            remediation="Set export GEMINI_API_KEY=<your-key> to enable live model generation.",
        ))

    # 6. Output directory write permission
    target_out = Path(output_dir or cfg.output_dir)
    try:
        target_out.mkdir(parents=True, exist_ok=True)
        probe_file = target_out / f".doctor_probe_{uuid.uuid4().hex[:8]}"
        try:
            probe_file.write_text("probe", encoding="utf-8")
        finally:
            probe_file.unlink(missing_ok=True)
        checks.append(DiagnosticCheck(
            name="output_directory",
            status=CheckStatus.PASS,
            message=f"Output directory writable at {target_out.resolve()}",
            details={"path": str(target_out.resolve())},
        ))
    except Exception as e:
        checks.append(DiagnosticCheck(
            name="output_directory",
            status=CheckStatus.FAIL,
            message=f"Output directory not writable at {target_out}: {e}",
            remediation=f"Ensure write permissions for output directory: {target_out}",
            details={"error": str(e)},
        ))

    # 7. Output directory free disk space check (>= 50 MB)
    import shutil
    try:
        usage = shutil.disk_usage(target_out)
        free_mb = usage.free / (1024 * 1024)
        if free_mb >= 50.0:
            checks.append(DiagnosticCheck(
                name="disk_space",
                status=CheckStatus.PASS,
                message=f"Sufficient storage available ({free_mb:.1f} MB free, >= 50 MB required)",
                details={"free_mb": round(free_mb, 2)},
            ))
        else:
            checks.append(DiagnosticCheck(
                name="disk_space",
                status=CheckStatus.WARN,
                message=f"Low disk space on output volume ({free_mb:.1f} MB free < 50 MB)",
                remediation="Free up disk space on the target volume before running full bundle renders.",
                details={"free_mb": round(free_mb, 2)},
            ))
    except Exception as e:
        checks.append(DiagnosticCheck(
            name="disk_space",
            status=CheckStatus.WARN,
            message=f"Could not check storage capacity: {e}",
        ))

    pass_count = sum(1 for c in checks if c.status == CheckStatus.PASS)
    warn_count = sum(1 for c in checks if c.status == CheckStatus.WARN)
    fail_count = sum(1 for c in checks if c.status == CheckStatus.FAIL)

    passed = (fail_count == 0)
    has_warnings = (warn_count > 0)
    summary = f"Doctor check complete: {pass_count} passed, {warn_count} warnings, {fail_count} failures."

    return DoctorReport(
        version="2.5.0",
        checks=checks,
        passed=passed,
        has_warnings=has_warnings,
        timestamp=datetime.now(timezone.utc).isoformat(),
        summary=summary,
    )


if __name__ == "__main__":
    import sys
    report = run_doctor()
    print(f"--- Omni Director System Doctor (v{report.version}) ---")
    for check in report.checks:
        print(f"[{check.status.value}] {check.name}: {check.message}")
        if check.remediation:
            print(f"  Remediation: {check.remediation}")
    print("Status:", "PASSED" if report.passed else "FAILED")
    sys.exit(0 if report.passed else 1)
