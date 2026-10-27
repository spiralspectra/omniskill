"""Configuration and strict model tiering enforcement for omni-movie-director."""

import os
import re
from typing import Optional
from pydantic import BaseModel, Field, model_validator

FORBIDDEN_LEGACY_PATTERNS = [
    re.compile(r"gemini[-_]?3\.1", re.IGNORECASE),
    re.compile(r"veo[-_]?3\.1", re.IGNORECASE),
    re.compile(r"\b3\.1\b", re.IGNORECASE),
    re.compile(r"[-_]3\.1", re.IGNORECASE),
]


def validate_no_legacy_3_1_models(model_name: str, field_name: str = "model") -> None:
    """Strictly validates that no deprecated 3.1 model identifiers are used.

    Raises:
        ValueError: If a legacy 3.1 model identifier (e.g. gemini-3.1-*, veo-3.1-*) is detected.
    """
    if not model_name:
        return
    for pattern in FORBIDDEN_LEGACY_PATTERNS:
        if pattern.search(model_name):
            raise ValueError(
                f"Legacy 3.1 model detected for {field_name}: '{model_name}'. "
                f"Per 2026 DeepMind standards, all 3.1 models (gemini-3.1-*, veo-3.1-*) are deprecated. "
                f"Mandatory 2026 model matrix: 'gemini-4-argon' (Director), 'gemini-3.8-flash' (Fast Workhorse), "
                f"'gemini-3-pro-image' (Nano Banana Concept Art), 'gemini-omni-1.1-flash-preview' (Omni Video Engine)."
            )


class DirectorConfig(BaseModel):
    """Runtime configuration for the Omni Movie Director ADK 2.0 pipeline."""

    api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("GOOGLE_API_KEY", "")
    )
    director_model: str = Field(
        default_factory=lambda: os.getenv("DIRECTOR_MODEL", "gemini-4-argon")
    )
    fast_model: str = Field(
        default_factory=lambda: os.getenv("FAST_MODEL", "gemini-3.8-flash")
    )
    image_model: str = Field(
        default_factory=lambda: os.getenv("IMAGE_MODEL", "gemini-3-pro-image")
    )
    video_model: str = Field(
        default_factory=lambda: os.getenv("VIDEO_MODEL", "gemini-omni-1.1-flash-preview")
    )
    output_dir: str = Field(
        default_factory=lambda: os.getenv("OMNI_OUTPUT_DIR", "./outputs")
    )
    artifact_dir: str = Field(
        default_factory=lambda: os.getenv("OMNI_ARTIFACT_DIR", "./artifacts")
    )
    dry_run: bool = Field(
        default_factory=lambda: os.getenv("OMNI_DRY_RUN", "false").lower() in ("true", "1", "yes")
    )

    def validate_no_legacy_3_1_models(self) -> None:
        validate_no_legacy_3_1_models(self.director_model, "director_model")
        validate_no_legacy_3_1_models(self.fast_model, "fast_model")
        validate_no_legacy_3_1_models(self.image_model, "image_model")
        validate_no_legacy_3_1_models(self.video_model, "video_model")

    @model_validator(mode="after")
    def verify_no_legacy_models(self) -> "DirectorConfig":
        self.validate_no_legacy_3_1_models()
        return self


cfg = DirectorConfig()
