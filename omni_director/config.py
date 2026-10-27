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
    re.compile(r"veo[-_]?3\.0", re.IGNORECASE),
    re.compile(r"\b3\.0\b", re.IGNORECASE),
    re.compile(r"[-_]3\.0", re.IGNORECASE),
    re.compile(r"imagen[-_]?3", re.IGNORECASE),
    re.compile(r"\b2\.5\b|[-_]2\.5", re.IGNORECASE),
    re.compile(r"\b2\.0\b|[-_]2\.0", re.IGNORECASE),
    re.compile(r"\b1\.5\b|[-_]1\.5", re.IGNORECASE),
]

APPROVED_2026_MODEL_PREFIXES = (
    "gemini-4-argon",
    "gemini-argon",
    "gemini-3.8-flash",
    "gemini-3.5-flash-lite",
    "gemini-3-pro-image",
    "gemini-3.8-flash-image",
    "nano-banana",
    "gemini-omni-1.1-flash-preview",
    "gemini-omni",
)


def validate_model_identifier(model_name: str, field_name: str = "model") -> None:
    """Validates that a model identifier complies with the 2026 standards and whitelist.

    Raises:
        ValueError: If a legacy model (1.5, 2.0, 2.5, 3.0, 3.1, veo, imagen-3) is detected
                    or if the model is not on the approved 2026 whitelist.
    """
    if not model_name:
        return

    # Specific check for 3.1 to preserve precise deprecation notice
    if re.search(r"gemini[-_]?3\.1|veo[-_]?3\.1|\b3\.1\b|[-_]3\.1", model_name, re.IGNORECASE):
        raise ValueError(
            f"Legacy 3.1 model detected for {field_name}: '{model_name}'. "
            f"Per 2026 DeepMind standards, all 3.1 models (gemini-3.1-*, veo-3.1-*) are deprecated. "
            f"Mandatory 2026 model matrix: 'gemini-4-argon' (Director), 'gemini-3.8-flash' (Fast Workhorse), "
            f"'gemini-3-pro-image' (Nano Banana Concept Art), 'gemini-omni-1.1-flash-preview' (Omni Video Engine)."
        )

    # General legacy blocklist check
    for pattern in FORBIDDEN_LEGACY_PATTERNS:
        if pattern.search(model_name):
            raise ValueError(
                f"Legacy deprecated model detected for {field_name}: '{model_name}'. "
                f"Per 2026 standards, legacy models (1.5, 2.0, 2.5, 3.0, 3.1, veo-3.0, veo-3.1, imagen-3) are forbidden."
            )

    # Approved 2026 whitelist check
    model_lower = model_name.lower()
    if not any(model_lower.startswith(p.lower()) for p in APPROVED_2026_MODEL_PREFIXES):
        raise ValueError(
            f"Model '{model_name}' for {field_name} is not in the approved 2026 model whitelist: "
            f"{APPROVED_2026_MODEL_PREFIXES}."
        )


def validate_no_legacy_3_1_models(model_name: str, field_name: str = "model") -> None:
    """Validates that no legacy 3.1 or older deprecated models are used."""
    validate_model_identifier(model_name, field_name)


class DirectorConfig(BaseModel):
    """Runtime configuration for the Omni Movie Director ADK 2.0 pipeline."""

    api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY", "")
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
        default_factory=lambda: os.getenv("OMNI_DRY_RUN", "true").lower() in ("true", "1", "yes")
    )

    def validate_no_legacy_3_1_models(self) -> None:
        validate_model_identifier(self.director_model, "director_model")
        validate_model_identifier(self.fast_model, "fast_model")
        validate_model_identifier(self.image_model, "image_model")
        validate_model_identifier(self.video_model, "video_model")

    @model_validator(mode="after")
    def verify_no_legacy_models(self) -> "DirectorConfig":
        self.validate_no_legacy_3_1_models()
        return self


_settings_instance: Optional[DirectorConfig] = None


def get_settings(reload: bool = False) -> DirectorConfig:
    """Returns the singleton runtime DirectorConfig instance."""
    global _settings_instance
    if _settings_instance is None or reload:
        _settings_instance = DirectorConfig()
    return _settings_instance


cfg = get_settings()
