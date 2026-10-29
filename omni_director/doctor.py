"""Environment, dependency, model matrix, and preflight doctor diagnostics for Omni Director."""

from __future__ import annotations

import importlib.util
import os
import re
import sys
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from omni_director.config import FORBIDDEN_LEGACY_PATTERNS, DirectorConfig, get_settings


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
    version: str = "2.1.0"
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
        pyd_ver = getattr(pydantic, "__version__", "unknown")
        if int(pyd_ver.split(".")[0]) >= 2:
            checks.append(DiagnosticCheck(
                name="pydantic_version",
                status=CheckStatus.PASS,
                message=f"Pydantic {pyd_ver} meets requirement (>= 2.0)",
                details={"version": pyd_ver},
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
    required_packages = ["google.adk", "google.genai", "rich"]
    missing_packages = []
    for pkg in required_packages:
        spec = importlib.util.find_spec(pkg)
        if spec is None:
            missing_packages.append(pkg)

    if not missing_packages:
        checks.append(DiagnosticCheck(
            name="core_dependencies",
            status=CheckStatus.PASS,
            message=f"All required core packages available ({', '.join(required_packages)})",
        ))
    else:
        checks.append(DiagnosticCheck(
            name="core_dependencies",
            status=CheckStatus.FAIL,
            message=f"Missing required dependencies: {', '.join(missing_packages)}",
            remediation=f"Install missing dependencies: pip install {' '.join(missing_packages)}",
            details={"missing": missing_packages},
        ))

    # 4. Model Matrix Check (Zero 3.1 / Legacy Models)
    cfg = config or get_settings()
    model_matrix = {
        "director_model": cfg.director_model,
        "fast_model": cfg.fast_model,
        "image_model": cfg.image_model,
        "video_model": cfg.video_model,
    }
    legacy_hits = []
    for field_name, model_name in model_matrix.items():
        if not model_name:
            continue
        for pat in FORBIDDEN_LEGACY_PATTERNS:
            if pat.search(model_name):
                legacy_hits.append(f"{field_name}='{model_name}' (matched {pat.pattern})")
                break

    if legacy_hits:
        checks.append(DiagnosticCheck(
            name="model_matrix_compliance",
            status=CheckStatus.FAIL,
            message=f"Deprecated legacy models detected: {'; '.join(legacy_hits)}. Zero 3.1 models allowed.",
            remediation="Update your model configuration in DirectorConfig or environment variables to use 2026 models (e.g. gemini-4-argon, gemini-3.8-flash, gemini-3-pro-image, gemini-omni-1.1-flash-preview).",
            details={"violations": legacy_hits, "matrix": model_matrix},
        ))
    else:
        checks.append(DiagnosticCheck(
            name="model_matrix_compliance",
            status=CheckStatus.PASS,
            message="Model matrix compliant with 2026 DeepMind standards (zero 3.1 models)",
            details={"matrix": model_matrix},
        ))

    # 5. Credentials Check
    has_creds = bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
    if has_creds:
        checks.append(DiagnosticCheck(
            name="credentials",
            status=CheckStatus.PASS,
            message="Google Gemini API credentials detected in environment",
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
        probe_file = target_out / ".doctor_probe_test"
        probe_file.write_text("probe", encoding="utf-8")
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

    pass_count = sum(1 for c in checks if c.status == CheckStatus.PASS)
    warn_count = sum(1 for c in checks if c.status == CheckStatus.WARN)
    fail_count = sum(1 for c in checks if c.status == CheckStatus.FAIL)

    passed = (fail_count == 0)
    has_warnings = (warn_count > 0)
    summary = f"Doctor check complete: {pass_count} passed, {warn_count} warnings, {fail_count} failures."

    return DoctorReport(
        version="2.1.0",
        checks=checks,
        passed=passed,
        has_warnings=has_warnings,
        timestamp=datetime.now(timezone.utc).isoformat(),
        summary=summary,
    )
