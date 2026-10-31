"""Comprehensive Test Suite for Omni Movie Director 2.0.

Validates:
1. Strict Model Matrix (Rejection of deprecated 3.1 models, mandatory 2026 models)
2. Pydantic V2 State Contracts (3-image ceiling, 3-beat cap, wardrobe polarity)
3. 7-Point Prompt Auditor (Markdown header rejection, speed lock, contact chain)
4. Golden Presets Integrity (IKEA ASMR, Sephora London Pulse, 40s Oner, Kinetic Fabric)
5. End-to-End Multi-Agent Pipeline (Mode A Montage & Mode B Extension Chain)
6. Skill and Reference Guide Presence
"""

from pathlib import Path
import pytest
from pydantic import ValidationError

from omni_director.agents import DirectorPipeline
from omni_director.config import DirectorConfig, validate_no_legacy_3_1_models
from omni_director.presets import (
    IKEA_ASMR_BIBLE,
    KINETIC_FABRIC_BIBLE,
    PRESETS,
    SEPHORA_EXTENSION_40S_BIBLE,
    SEPHORA_PULSE_BIBLE,
    get_preset_bible,
)
from omni_director.schemas import (
    ActionBeatSpec,
    AspectRatio,
    CharacterTurnaroundSpec,
    CraftCameraSpec,
    DiegeticSonicSpec,
    MasterBgmSpec,
    MasterEnvironmentSpec,
    MasterProductionBible,
    NanoBananaReference,
    ProductionBundle,
    RegimeType,
    ScenePromptSpec,
    StorytellingMode,
)
from omni_director.tools.prompt_auditor import audit_omni_scene_prompt


# ==============================================================================
# 1. Strict Model Tiering Matrix & Deprecation Tests
# ==============================================================================
class TestModelTieringMatrix:
    """Verifies strict 2026 DeepMind model standards and rejection of legacy 3.1 models."""

    def test_default_models_are_2026_standards(self):
        cfg = DirectorConfig()
        assert cfg.director_model == "gemini-4-argon"
        assert cfg.fast_model == "gemini-3.8-flash"
        assert cfg.image_model == "gemini-3-pro-image"
        assert cfg.video_model == "gemini-omni-1.1-flash-preview"

    @pytest.mark.parametrize(
        "forbidden_model",
        [
            "gemini-3.1-pro",
            "gemini-3.1-flash",
            "veo-3.1",
            "veo-3.1-generate",
            "gemini-3.1",
            "gemini_3.1",
        ],
    )
    def test_rejection_of_legacy_3_1_models(self, forbidden_model):
        with pytest.raises(ValueError, match="Legacy 3.1 model detected"):
            validate_no_legacy_3_1_models(forbidden_model)

    def test_config_validation_catches_legacy_model(self):
        with pytest.raises(ValidationError):
            DirectorConfig(director_model="gemini-3.1-pro")

        with pytest.raises(ValidationError):
            DirectorConfig(video_model="veo-3.1")


# ==============================================================================
# 2. Pydantic State Contracts & Guardrails
# ==============================================================================
class TestStateContracts:
    """Tests Pydantic V2 schemas for reference ceiling, action beats, and wardrobe polarity."""

    def test_reference_image_ceiling_enforces_max_3(self):
        """Gemini Omni enforces an architectural ceiling of at most 3 image references."""
        refs = [
            NanoBananaReference(
                asset_id=f"<image_{i}>",
                job_description="Anchor",
                exclusion_clause="None",
                generation_prompt="Prompt",
            )
            for i in range(1, 5)  # 4 references exceeds ceiling
        ]

        with pytest.raises(ValidationError, match=r"(Reference ceiling exceeded|too_long)"):
            MasterProductionBible(
                project_title="Ceiling Test",
                logline="Testing 3-image ceiling",
                creative_regime=RegimeType.REGIME_2_KINETIC,
                storytelling_mode=StorytellingMode.MODE_A_PARALLEL_CUT,
                aspect_ratio=AspectRatio.RATIO_16_9,
                environment=MasterEnvironmentSpec(
                    location_name="Test Loc",
                    spatial_architecture="Room",
                    lighting_setup="Daylight",
                    atmospheric_particles="None",
                ),
                sonic_blueprint=DiegeticSonicSpec(room_acoustics="Silent"),
                master_bgm=MasterBgmSpec(
                    track_title="Test Score",
                    genre_style="Ambient",
                    tempo_bpm=120,
                    key_signature="C Major",
                    dynamic_arc="Flat",
                    lyria_prompt="Lyria prompt",
                ),
                nano_banana_assets=refs,
                scenes=[],
            )

    def test_action_beats_cap_enforces_max_3_per_scene(self):
        """ScenePromptSpec strictly enforces max 3 action beats per 10s window."""
        with pytest.raises(ValidationError, match=r"(Action beats cap exceeded|too_long)"):
            ScenePromptSpec(
                scene_index=1,
                timestamp_range="00:00 - 00:08",
                scene_title="Too Many Beats",
                regime=RegimeType.REGIME_2_KINETIC,
                action_beats=[
                    "Beat 1: Run",
                    "Beat 2: Jump",
                    "Beat 3: Fall",
                    "Beat 4: Roll",  # 4 beats exceeds cap!
                ],
                omni_prose_prompt="Natural prose prompt at 1.0x real-time speed with audio.",
            )

    def test_wardrobe_polarity_enforcement_for_multi_character(self):
        """When 2+ characters are present, high-contrast wardrobe polarity must be distinct."""
        char1 = CharacterTurnaroundSpec(
            name="Alice",
            silhouette="Tall",
            wardrobe_polarity="Black leather jacket",
            movement_signature="Fast",
        )
        char2 = CharacterTurnaroundSpec(
            name="Bob",
            silhouette="Athletic",
            wardrobe_polarity="Black leather jacket",  # Collision with Alice!
            movement_signature="Slow",
        )

        with pytest.raises(ValidationError, match="High-contrast wardrobe polarity collision"):
            MasterProductionBible(
                project_title="Polarity Collision Test",
                logline="Testing polarity collision",
                creative_regime=RegimeType.REGIME_2_KINETIC,
                storytelling_mode=StorytellingMode.MODE_A_PARALLEL_CUT,
                aspect_ratio=AspectRatio.RATIO_16_9,
                characters=[char1, char2],
                environment=MasterEnvironmentSpec(
                    location_name="Test Loc",
                    spatial_architecture="Room",
                    lighting_setup="Daylight",
                    atmospheric_particles="None",
                ),
                sonic_blueprint=DiegeticSonicSpec(room_acoustics="Silent"),
                master_bgm=MasterBgmSpec(
                    track_title="Test",
                    genre_style="Jazz",
                    tempo_bpm=100,
                    key_signature="F",
                    dynamic_arc="Arc",
                    lyria_prompt="Lyria",
                ),
                nano_banana_assets=[],
                scenes=[],
            )


# ==============================================================================
# 3. 7-Point Prompt Auditor Verification
# ==============================================================================
class TestPromptAuditor:
    """Verifies the 7-Point Gemini Omni Prompt Auditor checklist."""

    def test_rule_1_rejects_markdown_headers_inside_prompt(self):
        scene = ScenePromptSpec(
            scene_index=1,
            timestamp_range="00:00 - 00:08",
            scene_title="Header Violation",
            regime=RegimeType.REGIME_2_KINETIC,
            action_beats=["Beat 1", "Beat 2"],
            omni_prose_prompt="### Camera Action\nThe camera tracks at 1.0x real-time speed. Foley sound thuds.",
            kinetic_contact_chain="1 -> 2 -> 3 -> 4 -> 5",
        )
        result = audit_omni_scene_prompt(scene, regime=RegimeType.REGIME_2_KINETIC)
        assert not result.passed
        assert any("Rule 1 Violation" in err for err in result.errors)

    def test_rule_3_rejects_regime_2_without_speed_lock(self):
        scene = ScenePromptSpec(
            scene_index=1,
            timestamp_range="00:00 - 00:08",
            scene_title="Missing Speed Lock",
            regime=RegimeType.REGIME_2_KINETIC,
            action_beats=["Beat 1", "Beat 2"],
            omni_prose_prompt="The camera floats gracefully through the kitchen with audio hum.",
            kinetic_contact_chain="A -> B -> C -> D -> E",
        )
        result = audit_omni_scene_prompt(scene, regime=RegimeType.REGIME_2_KINETIC)
        assert not result.passed
        assert any("Rule 3 Violation" in err and "1.0x" in err for err in result.errors)

    def test_rule_5_rejects_image_ref_greater_than_3(self):
        scene = ScenePromptSpec(
            scene_index=1,
            timestamp_range="00:00 - 00:08",
            scene_title="Bad Ref",
            regime=RegimeType.REGIME_1_ATMOSPHERIC,
            action_beats=["Beat 1"],
            omni_prose_prompt="The subject matches <image_4> exactly with audio sound tone.",
        )
        result = audit_omni_scene_prompt(scene, regime=RegimeType.REGIME_1_ATMOSPHERIC)
        assert not result.passed
        assert any("Rule 5 Violation" in err for err in result.errors)

    def test_rule_6_rejects_missing_diegetic_audio(self):
        scene = ScenePromptSpec(
            scene_index=1,
            timestamp_range="00:00 - 00:08",
            scene_title="No Audio",
            regime=RegimeType.REGIME_1_ATMOSPHERIC,
            action_beats=["Beat 1"],
            omni_prose_prompt="The camera glides over the silent landscape with visual brilliance.",
        )
        result = audit_omni_scene_prompt(scene, regime=RegimeType.REGIME_1_ATMOSPHERIC)
        assert not result.passed
        assert any("Rule 6 Violation" in err for err in result.errors)


# ==============================================================================
# 4. Golden Presets Integrity
# ==============================================================================
class TestGoldenPresets:
    """Verifies that all built-in golden presets pass schema checks and the 7-Point Auditor."""

    @pytest.mark.parametrize(
        "preset_name",
        ["ikea-asmr", "sephora-pulse", "sephora-extension-40s", "kinetic-fabric"],
    )
    def test_preset_bible_loads_and_passes_all_audits(self, preset_name):
        bible = get_preset_bible(preset_name)
        assert isinstance(bible, MasterProductionBible)
        assert len(bible.scenes) >= 1
        assert len(bible.nano_banana_assets) <= 3

        for scene in bible.scenes:
            result = audit_omni_scene_prompt(scene, regime=bible.creative_regime)
            assert result.passed, f"Preset '{preset_name}' Scene {scene.scene_index} failed audit: {result.errors}"


# ==============================================================================
# 5. End-to-End Pipeline Verification (Dry-Run Mode A & B)
# ==============================================================================
class TestDirectorPipeline:
    """Tests the full multi-agent DirectorPipeline execution in dry-run mode."""

    def test_pipeline_runs_mode_a_montage(self, tmp_path):
        pipeline = DirectorPipeline()
        bundle = pipeline.run(
            preset_name="ikea-asmr",
            output_dir=str(tmp_path),
            render_video=False,
            dry_run=True,
        )

        assert isinstance(bundle, ProductionBundle)
        assert Path(bundle.storyboard_html_path).exists()
        assert Path(bundle.bundle_json_path).exists()
        assert len(bundle.bible.scenes) == 4
        assert len(bundle.audit_reports) == 4
        assert all(r.passed for r in bundle.audit_reports)

        # Inspect generated HTML content
        html_text = Path(bundle.storyboard_html_path).read_text(encoding="utf-8")
        assert "IKEA: The Living Room Unfolds" in html_text
        assert "Omni Movie Director Cinema UI" in html_text

    def test_pipeline_runs_mode_b_continuous_extension(self, tmp_path):
        pipeline = DirectorPipeline()
        bundle = pipeline.run(
            preset_name="sephora-extension-40s",
            output_dir=str(tmp_path),
            render_video=False,
            dry_run=True,
            continuous_mode=True,
        )

        assert isinstance(bundle, ProductionBundle)
        assert Path(bundle.storyboard_html_path).exists()
        assert Path(bundle.bundle_json_path).exists()
        assert bundle.bible.storytelling_mode == StorytellingMode.MODE_B_CONTINUOUS_CHAIN
        assert all(r.passed for r in bundle.audit_reports)


# ==============================================================================
# 6. Skill and Reference Guides Presence Tests
# ==============================================================================
class TestSkillIntegrity:
    """Verifies that the skill files and reference guides exist and are populated."""

    def test_skills_exist_and_non_empty(self):
        prompting_skill = Path("skills/gemini-omni-prompting/SKILL.md")
        director_skill = Path("skills/omni-movie-director/SKILL.md")

        assert prompting_skill.exists()
        assert len(prompting_skill.read_text(encoding="utf-8")) > 500

        assert director_skill.exists()
        assert len(director_skill.read_text(encoding="utf-8")) > 500

    def test_reference_guides_exist(self):
        ref_dir = Path("skills/omni-movie-director/references")
        expected_guides = [
            "adk-2-architecture.md",
            "director-intake-and-bible.md",
            "golden-demos.md",
            "nano-banana-storyboard-system.md",
        ]
        for guide in expected_guides:
            guide_path = ref_dir / guide
            assert guide_path.exists(), f"Reference guide {guide} missing!"
            assert len(guide_path.read_text(encoding="utf-8")) > 200


# ==============================================================================
# 7. Adversary Review Findings Verification Tests
# ==============================================================================
class TestAdversaryReviewFindings:
    """Verifies all 8 adversary review fixes are locked in."""

    def test_finding_1_gemini_omni_prompting_skill_comprehensiveness(self):
        content = Path("skills/gemini-omni-prompting/SKILL.md").read_text(encoding="utf-8")
        assert "Gemini Omni 1.1 Prompting Handbook" in content
        assert "Seedance 2.5 Kinetic Physics Engine" in content
        assert "Mode A: Atmospheric & World Exploration" in content
        assert "Mode I: Continuous Scene Extension" in content
        assert "7-Item Pre-Output Verification Checklist" in content

    def test_finding_2_module_exports_and_adk2_alignment(self):
        import omni_director
        from omni_director import agents, get_settings
        from omni_director.agents.agent import (
            IntakeAndResearchAgent,
            CreativeDirectorAgent,
            VisualBibleGeneratorAgent,
            StoryboardParallelAgent,
            ScenePromptAgent,
            ParallelScenePromptAgent,
            BGMComposerAgent,
            StoryboardHTMLCompilerAgent,
        )

        # Check export presence on top-level and agents sub-module
        for name in [
            "IntakeAndResearchAgent",
            "CreativeDirectorAgent",
            "VisualBibleGeneratorAgent",
            "StoryboardParallelAgent",
            "ScenePromptAgent",
            "ParallelScenePromptAgent",
            "BGMComposerAgent",
            "StoryboardHTMLCompilerAgent",
            "get_settings",
        ]:
            assert hasattr(omni_director, name), f"Missing {name} in omni_director"
            if "get_settings" not in name:
                assert hasattr(agents, name), f"Missing {name} in omni_director.agents"

        # Check uppercase model property aliases on DirectorConfig / settings
        settings = get_settings()
        assert settings.DIRECTOR_MODEL == settings.director_model
        assert settings.FAST_MODEL == settings.fast_model
        assert settings.IMAGE_MODEL == settings.image_model
        assert settings.OMNI_VIDEO_MODEL == settings.video_model

        # Check agent constructors take name and model_name kwargs without error
        all_agent_classes = [
            IntakeAndResearchAgent,
            CreativeDirectorAgent,
            VisualBibleGeneratorAgent,
            StoryboardParallelAgent,
            ScenePromptAgent,
            ParallelScenePromptAgent,
            BGMComposerAgent,
            StoryboardHTMLCompilerAgent,
        ]
        for cls in all_agent_classes:
            inst = cls(name=f"test_{cls.__name__}", model_name=settings.FAST_MODEL)
            assert inst.name == f"test_{cls.__name__}"
            assert inst.model_name == settings.FAST_MODEL

    def test_finding_round2_custom_prompt_no_keyword_hijacking(self, tmp_path):
        """Custom prompts containing keywords like 'fabric' or 'perfume' must NOT be hijacked into presets."""
        pipeline = DirectorPipeline()
        prompt_with_keywords = "A documentary on silk fabric manufacturing and perfume making with ASMR audio"
        bundle = pipeline.run(
            prompt=prompt_with_keywords,
            output_dir=str(tmp_path),
            render_video=False,
            dry_run=True,
        )
        assert bundle.bible.project_title != "IKEA: The Living Room Unfolds"
        assert bundle.bible.project_title != "Sephora London: Glow In The Rain"
        assert bundle.bible.project_title != "Kinetic Fabric: Silk in Freefall"
        assert bundle.bible.logline == prompt_with_keywords

    def test_finding_round2_vertical_9_16_svg_geometry_strictly_bounded(self, tmp_path):
        """In 9:16 vertical productions, all SVG elements must strictly fit inside viewBox 0 0 1080 1920."""
        import xml.etree.ElementTree as ET
        pipeline = DirectorPipeline()
        bundle = pipeline.run(
            preset_name="sephora-pulse",
            output_dir=str(tmp_path),
            render_video=False,
            dry_run=True,
        )

        svg_files = list((tmp_path / "storyboards").glob("*.svg"))
        assert len(svg_files) >= 3, "Expected storyboard SVGs to be generated"

        for svg_file in svg_files:
            content = svg_file.read_text(encoding="utf-8")
            root = ET.fromstring(content)
            viewbox = root.attrib.get("viewBox", "")
            assert viewbox == "0 0 1080 1920", f"{svg_file.name} unexpected viewBox: {viewbox}"

            # Verify no <rect> exceeds viewBox width (1080) or height (1920)
            for rect in root.iter("{http://www.w3.org/2000/svg}rect"):
                x = float(rect.attrib.get("x", 0))
                y = float(rect.attrib.get("y", 0))
                width = float(rect.attrib.get("width", 0))
                height = float(rect.attrib.get("height", 0))
                assert x + width <= 1080, f"{svg_file.name} rect exceeds viewBox width: x={x}, w={width}, right={x+width}"
                assert y + height <= 1920, f"{svg_file.name} rect exceeds viewBox height: y={y}, h={height}, bottom={y+height}"

    def test_finding_4_render_video_default_hybrid_mode(self, tmp_path):
        from omni_director.agents.agent import OmniVideoRenderAgent
        agent = OmniVideoRenderAgent()
        context = {
            "bible": get_preset_bible("ikea-asmr"),
            "render_video": False,
            "dry_run": True,
            "output_dir": str(tmp_path),
        }
        res = agent.run(context)
        assert len(res["rendered_videos"]) == len(context["bible"].scenes)
        assert res["rendered_videos"][0]["status"] == "skipped_by_default_hybrid_mode"

    def test_finding_6_storyboard_preview_contains_inline_svgs(self, tmp_path):
        pipeline = DirectorPipeline()
        bundle = pipeline.run(
            preset_name="ikea-asmr",
            output_dir=str(tmp_path),
            dry_run=True,
            render_video=False,
        )
        html_content = Path(bundle.storyboard_html_path).read_text(encoding="utf-8")
        assert "<svg" in html_content
        assert '<div class="svg-placeholder">' not in html_content

    def test_finding_7_cli_flags_and_env_var_resolution(self, monkeypatch):
        import os
        from omni_director.config import get_settings
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
        settings = get_settings(reload=True)
        assert settings.api_key == "test-gemini-key"


# ==============================================================================
# 8. V2.1 Doctor, Diagnostics & Structured Telemetry Tests (AC-2, AC-4)
# ==============================================================================
class TestV21DoctorAndTelemetry:
    """Verifies FDE preflight doctor and structured runtime telemetry."""

    def test_run_doctor_valid_environment(self):
        from omni_director.doctor import run_doctor
        report = run_doctor()
        assert report.passed is True
        assert report.exit_code == 0
        assert len(report.checks) >= 4

    def test_run_doctor_rejects_legacy_3_1_models(self):
        from omni_director.doctor import run_doctor
        cfg = DirectorConfig()
        cfg.fast_model = "gemini-3.1-flash"
        report = run_doctor(cfg)
        assert report.passed is False
        assert report.exit_code == 1
        assert any(c.name == "model_matrix_compliance" and c.status.value in ("FAIL", "FAILED") for c in report.checks)

    def test_doctor_cli_subcommands(self):
        from omni_director.cli import main
        assert main(["doctor"]) == 0
        assert main(["--doctor"]) == 0

    def test_runtime_telemetry_emission_and_redaction(self, tmp_path):
        import json
        from omni_director.telemetry import RuntimeTelemetry
        pipeline = DirectorPipeline()
        pipeline.telemetry = RuntimeTelemetry()
        pipeline.telemetry.metadata["api_key"] = "AIzaSyTestSecretKey123456"
        pipeline.telemetry.add_timing(
            "custom_auth",
            5.0,
            details={"token": "sk-secret123", "secret_key": "AIzaSyTestSecretKey123456"},
        )
        bundle = pipeline.run(
            preset_name="ikea-asmr",
            output_dir=str(tmp_path),
            dry_run=True,
            render_video=False,
        )
        telemetry_file = tmp_path / "telemetry.json"
        assert telemetry_file.is_file(), "telemetry.json must be written to output directory"
        data = json.loads(telemetry_file.read_text(encoding="utf-8"))
        for required_key in ["session_id", "model_matrix", "stage_timings", "total_duration_ms", "audit_summary"]:
            assert required_key in data, f"telemetry.json missing key: {required_key}"
        assert data["total_duration_ms"] >= 0
        telemetry_text = telemetry_file.read_text(encoding="utf-8")
        assert "AIzaSyTestSecretKey123456" not in telemetry_text
        assert "sk-secret123" not in telemetry_text
        assert "[REDACTED]" in telemetry_text
        assert data["metadata"]["api_key"] == "[REDACTED]"


# ==============================================================================
# 9. V2.1 Bible Ingestion & Round-Trip Tests (AC-3)
# ==============================================================================
class TestV21BibleRoundTrip:
    """Verifies MasterProductionBible and ProductionBundle JSON serialization/ingestion."""

    def test_load_bible_from_raw_bible_json(self, tmp_path):
        from omni_director.schemas import load_bible_from_json
        bible_path = tmp_path / "raw_bible.json"
        bible_path.write_text(IKEA_ASMR_BIBLE.model_dump_json(indent=2), encoding="utf-8")
        loaded = load_bible_from_json(bible_path)
        assert isinstance(loaded, MasterProductionBible)
        assert loaded.project_title == IKEA_ASMR_BIBLE.project_title
        assert len(loaded.scenes) == len(IKEA_ASMR_BIBLE.scenes)

    def test_load_bible_from_bundle_json(self, tmp_path):
        from omni_director.schemas import load_bible_from_json
        pipeline = DirectorPipeline()
        bundle = pipeline.run(
            preset_name="ikea-asmr",
            output_dir=str(tmp_path),
            dry_run=True,
            render_video=False,
        )
        loaded = load_bible_from_json(bundle.bundle_json_path)
        assert isinstance(loaded, MasterProductionBible)
        assert loaded.project_title == IKEA_ASMR_BIBLE.project_title

    def test_load_bible_from_dict(self):
        from omni_director.schemas import load_bible_from_json
        loaded = load_bible_from_json(IKEA_ASMR_BIBLE.model_dump())
        assert isinstance(loaded, MasterProductionBible)
        assert loaded.project_title == IKEA_ASMR_BIBLE.project_title

    def test_load_bible_invalid_json_raises_value_error(self, tmp_path):
        from omni_director.schemas import load_bible_from_json
        non_existent = tmp_path / "does_not_exist.json"
        with pytest.raises(ValueError):
            load_bible_from_json(non_existent)

        malformed = tmp_path / "malformed.json"
        malformed.write_text('{"project_title": 12345, "invalid": true}', encoding="utf-8")
        with pytest.raises(ValueError):
            load_bible_from_json(malformed)

    def test_pipeline_run_from_bible(self, tmp_path):
        pipeline = DirectorPipeline()
        bundle = pipeline.run_from_bible(
            bible=IKEA_ASMR_BIBLE,
            output_dir=str(tmp_path),
            dry_run=True,
            render_video=False,
        )
        assert isinstance(bundle, ProductionBundle)
        assert Path(bundle.storyboard_html_path).is_file()
        assert Path(bundle.bundle_json_path).is_file()

    def test_cli_bible_file_flag(self, tmp_path):
        from omni_director.cli import main
        bible_path = tmp_path / "cli_bible.json"
        bible_path.write_text(IKEA_ASMR_BIBLE.model_dump_json(), encoding="utf-8")
        out_dir = tmp_path / "cli_out"
        exit_code = main(["--bible-file", str(bible_path), "-o", str(out_dir), "--dry-run"])
        assert exit_code == 0
        assert (out_dir / "storyboard_preview.html").is_file()


# ==============================================================================
# 10. V2.1 Prompt Self-Healing Tests (AC-5)
# ==============================================================================
class TestV21PromptSelfHealing:
    """Verifies prompt self-healing loop repairing all 7-point audit defects."""

    def test_healing_strips_markdown_and_html_headers(self):
        from omni_director.tools.prompt_auditor import heal_omni_scene_prompt
        defective_scene = ScenePromptSpec(
            scene_index=1,
            timestamp_range="00:00 - 00:08",
            scene_title="Header Defect Scene",
            regime=RegimeType.REGIME_1_ATMOSPHERIC,
            action_beats=[
                ActionBeatSpec(beat_index=1, beat_title="Beat 1", action_description="Action 1", timecode="00:00 - 00:08")
            ],
            prompt_text="# SCENE 1: THE REVEAL\n### Camera: 35mm\n<h1>Defective HTML Header</h1>\nObservational wide static shot with natural room tone foley.",
            camera_spec=CraftCameraSpec(
                rig_type="Tripod", focal_length_mm=35, composition="Wide", route="Static", action_anchor="Anchor", focus_axis="Deep", tone_rig="Clean"
            ),
            diegetic_sound=DiegeticSonicSpec(foley_cues=["Natural room tone"], dialogue_lines=[], room_acoustics="Quiet room"),
        )
        initial_audit = audit_omni_scene_prompt(defective_scene, regime=RegimeType.REGIME_1_ATMOSPHERIC)
        assert initial_audit.passed is False
        assert initial_audit.rule_details["rule_1_no_markdown_headers"]["passed"] is False

        healed_scene, healed_audit = heal_omni_scene_prompt(defective_scene, audit_result=initial_audit, regime=RegimeType.REGIME_1_ATMOSPHERIC)
        assert "#" not in healed_scene.prompt_text
        assert "<h1>" not in healed_scene.prompt_text
        assert healed_audit.rule_details["rule_1_no_markdown_headers"]["passed"] is True

    def test_healing_adds_speed_lock_in_regime_2(self):
        from omni_director.tools.prompt_auditor import heal_omni_scene_prompt
        defective_scene = ScenePromptSpec(
            scene_index=1,
            timestamp_range="00:00 - 00:08",
            scene_title="Speed Lock Defect Scene",
            regime=RegimeType.REGIME_2_KINETIC,
            action_beats=[
                ActionBeatSpec(beat_index=1, beat_title="Beat 1", action_description="Action 1", timecode="00:00 - 00:08")
            ],
            prompt_text="Kinetic camera tracking shot of high-velocity vehicle with loud tire friction foley.",
            camera_spec=CraftCameraSpec(
                rig_type="Russian Arm", focal_length_mm=28, composition="Low tracking", route="Linear", action_anchor="Chassis", focus_axis="Sharp", tone_rig="Kinetic"
            ),
            diegetic_sound=DiegeticSonicSpec(foley_cues=["Loud tire friction"], dialogue_lines=[], room_acoustics="Open road"),
        )
        initial_audit = audit_omni_scene_prompt(defective_scene, regime=RegimeType.REGIME_2_KINETIC)
        assert initial_audit.rule_details["rule_3_speed_lock_regime_2"]["passed"] is False

        healed_scene, healed_audit = heal_omni_scene_prompt(defective_scene, audit_result=initial_audit, regime=RegimeType.REGIME_2_KINETIC)
        assert "1.0x" in healed_scene.prompt_text
        assert healed_audit.rule_details["rule_3_speed_lock_regime_2"]["passed"] is True

    def test_healing_adds_diegetic_foley(self):
        from omni_director.tools.prompt_auditor import heal_omni_scene_prompt
        defective_scene = ScenePromptSpec(
            scene_index=1,
            timestamp_range="00:00 - 00:08",
            scene_title="Silent Scene Defect",
            regime=RegimeType.REGIME_1_ATMOSPHERIC,
            action_beats=[
                ActionBeatSpec(beat_index=1, beat_title="Beat 1", action_description="Action 1", timecode="00:00 - 00:08")
            ],
            prompt_text="Observational wide static shot with zero cues mentioned.",
            camera_spec=CraftCameraSpec(
                rig_type="Tripod", focal_length_mm=35, composition="Wide", route="Static", action_anchor="Anchor", focus_axis="Deep", tone_rig="Clean"
            ),
            diegetic_sound=DiegeticSonicSpec(foley_cues=[], dialogue_lines=[], room_acoustics="Quiet"),
        )
        initial_audit = audit_omni_scene_prompt(defective_scene, regime=RegimeType.REGIME_1_ATMOSPHERIC)
        assert initial_audit.rule_details["rule_6_diegetic_audio_cues"]["passed"] is False

        healed_scene, healed_audit = heal_omni_scene_prompt(defective_scene, audit_result=initial_audit, regime=RegimeType.REGIME_1_ATMOSPHERIC)
        assert healed_audit.rule_details["rule_6_diegetic_audio_cues"]["passed"] is True
        assert len(healed_scene.diegetic_sound.foley_cues) >= 1

    def test_healing_mode_b_continuous_continuity(self):
        from omni_director.tools.prompt_auditor import heal_omni_scene_prompt
        defective_scene = ScenePromptSpec(
            scene_index=2,
            timestamp_range="00:08 - 00:16",
            scene_title="Mode B Discontinuous Scene",
            regime=RegimeType.REGIME_1_ATMOSPHERIC,
            action_beats=[
                ActionBeatSpec(beat_index=1, beat_title="Beat 1", action_description="Action 1", timecode="00:08 - 00:16")
            ],
            prompt_text="A completely disconnected shot of a mountain with birds singing foley.",
            camera_spec=CraftCameraSpec(
                rig_type="Tripod", focal_length_mm=35, composition="Wide", route="Static", action_anchor="Anchor", focus_axis="Deep", tone_rig="Clean"
            ),
            diegetic_sound=DiegeticSonicSpec(foley_cues=["Birds singing"], dialogue_lines=[], room_acoustics="Mountain air"),
        )
        initial_audit = audit_omni_scene_prompt(
            defective_scene,
            regime=RegimeType.REGIME_1_ATMOSPHERIC,
            storytelling_mode=StorytellingMode.MODE_B_CONTINUOUS_CHAIN,
        )
        assert initial_audit.rule_details["rule_7_continuous_continuity"]["passed"] is False

        healed_scene, healed_audit = heal_omni_scene_prompt(
            defective_scene,
            audit_result=initial_audit,
            regime=RegimeType.REGIME_1_ATMOSPHERIC,
            storytelling_mode=StorytellingMode.MODE_B_CONTINUOUS_CHAIN,
        )
        assert healed_audit.rule_details["rule_7_continuous_continuity"]["passed"] is True
        assert healed_audit.score >= 90

    def test_prompt_auditor_agent_auto_heals_failing_scene_in_pipeline(self):
        from omni_director.agents.agent import PromptAuditorAgent
        import copy
        bible = copy.deepcopy(IKEA_ASMR_BIBLE)
        bible.storytelling_mode = StorytellingMode.MODE_B_CONTINUOUS_CHAIN
        # Break scene 1 with markdown headers and missing continuity cues
        bible.scenes[0].prompt_text = "# SCENE 1: BROKEN HEADER\nObservational wide static shot with natural room tone foley. No speed lock."

        agent = PromptAuditorAgent()
        context = agent.run(bible)
        assert context["passed"] is True
        assert context["audit_results"][0].passed is True
        assert context["audit_results"][0].score >= 90.0
        assert "#" not in bible.scenes[0].prompt_text


# ==============================================================================
# 11. V2.1 Autonomous Product Council & Strict Gate Tests (AC-1, AC-6, AC-9)
# ==============================================================================
class TestV21ProductCouncilAndStrictGate:
    """Verifies 4-persona Product Council evaluation, 100-pt rubric, and strict gate enforcement."""

    def test_ac1_all_agents_and_council_instantiation(self):
        from omni_director.agents.agent import (
            BGMComposerAgent,
            CreativeDirectorAgent,
            IntakeAndResearchAgent,
            OmniVideoRenderAgent,
            ParallelScenePromptAgent,
            PromptAuditorAgent,
            ScenePromptAgent,
            StoryboardHTMLCompilerAgent,
            StoryboardParallelAgent,
            VisualBibleGeneratorAgent,
            VisualStoryboardAgent,
        )
        from omni_director.agents.council import ProductCouncilOrchestrator

        agents = [
            IntakeAndResearchAgent(),
            CreativeDirectorAgent(),
            VisualStoryboardAgent(),
            VisualBibleGeneratorAgent(),
            StoryboardParallelAgent(),
            ScenePromptAgent(),
            ParallelScenePromptAgent(),
            BGMComposerAgent(),
            PromptAuditorAgent(),
            OmniVideoRenderAgent(),
            StoryboardHTMLCompilerAgent(),
            ProductCouncilOrchestrator(),
        ]
        assert len(agents) == 12

    def test_council_scores_all_canonical_presets_above_90(self):
        from omni_director.agents.council import ProductCouncilOrchestrator
        orchestrator = ProductCouncilOrchestrator()
        preset_names = ["ikea-asmr", "sephora-pulse", "sephora-extension-40s", "kinetic-fabric"]

        for name in preset_names:
            bible = get_preset_bible(name)
            report = orchestrator.audit(bible)
            assert report.passed is True, f"Preset '{name}' failed council audit"
            assert report.overall_score >= 90.0, f"Preset '{name}' scored {report.overall_score} < 90.0"
            assert report.critical_findings_count == 0, f"Preset '{name}' has critical findings"
            assert len(report.persona_results) == 4

    def test_council_strict_negative_falsification_exit_code_2(self, tmp_path):
        import copy
        from omni_director.cli import main

        defective_bible = copy.deepcopy(IKEA_ASMR_BIBLE)
        # Inject forbidden legacy model to trigger CRITICAL finding and cause score failure
        defective_bible.logline = "Defective run violating 2026 model rules with gemini-3.1-pro."
        defective_path = tmp_path / "defective_strict_bible.json"
        defective_path.write_text(defective_bible.model_dump_json(), encoding="utf-8")

        out_dir = tmp_path / "strict_out"
        exit_code = main(["--bible-file", str(defective_path), "-o", str(out_dir), "--council-strict", "--dry-run"])
        assert exit_code == 2, f"Expected exit code 2 on strict council violation, got {exit_code}"

    def test_ac9_council_artifacts_and_runner_presence(self):
        assert Path("AGENTS.md").is_file(), "AGENTS.md constitutional law must exist"
        assert Path("skills/omni-product-council/SKILL.md").is_file(), "Council skill must exist"
        assert Path("scripts/run_daily_council.py").is_file(), "scripts/run_daily_council.py must exist"


# ==============================================================================
# 12. V2.1 Domain Archetypes & Custom Brief Synthesis Tests (AC-7)
# ==============================================================================
class TestV21DomainArchetypes:
    """Verifies deterministic 6-archetype domain classification, tie-breaking, and synthesis."""

    def test_domain_classification_all_six_archetypes(self):
        from omni_director.presets import classify_brief_domain
        archetype_samples = {
            "automotive_robotics": "Autonomous electric hypercar drone pursuit through neon streets at night",
            "culinary_asmr": "Slow pour matcha latte with frothy steamed oat milk in a minimalist kitchen",
            "luxury_fashion": "High-fashion catwalk runway show with couture velvet gown and diamond jewelry",
            "kinetic_action": "Extreme parkour athlete jumping across skyscraper rooftops with martial arts agility",
            "tech_hardware": "CNC machined aluminum smartphone chassis unibody with cleanroom silicon chip",
            "architectural_sanctuary": "Brutalist concrete museum sanctuary with serene travertine courtyard and pavilion",
        }
        for expected_domain, prompt in archetype_samples.items():
            detected = classify_brief_domain(prompt)
            assert detected == expected_domain, f"Prompt '{prompt}' detected as '{detected}', expected '{expected_domain}'"

    def test_domain_classification_fallback_and_tie_breaking(self):
        from omni_director.presets import classify_brief_domain
        # Zero-keyword fallback to architectural_sanctuary
        assert classify_brief_domain("A completely abstract entity dissolved in empty timeless void") == "architectural_sanctuary"

        # Deterministic tie-breaking: 1 automotive kw vs 1 architectural kw -> automotive_robotics wins priority
        assert classify_brief_domain("Drone pavilion") == "automotive_robotics"

    def test_custom_bible_synthesis_per_domain_without_preset_hijacking(self):
        from omni_director.agents.agent import CreativeDirectorAgent
        agent = CreativeDirectorAgent()
        domain_prompts = [
            ("Hypercar race at dusk", "automotive_robotics"),
            ("Artisanal bread baking in ceramic oven", "culinary_asmr"),
            ("Runway perfume launch with silk wardrobe", "luxury_fashion"),
            ("Boxing athlete heavy bag training workout", "kinetic_action"),
            ("Semiconductor microchip macro probe inspection", "tech_hardware"),
            ("Zen garden stone architecture residence", "architectural_sanctuary"),
        ]
        for prompt, expected_domain in domain_prompts:
            bible = agent.synthesize_custom_bible(prompt)
            assert bible.domain_archetype == expected_domain
            assert "IKEA" not in bible.project_title
            assert "Sephora" not in bible.project_title
            for scene in bible.scenes:
                audit = audit_omni_scene_prompt(scene, regime=bible.creative_regime)
                assert audit.passed is True, f"Scene {scene.scene_index} in synthesized {expected_domain} failed audit: {audit.errors}"


# ==============================================================================
# 13. V2.1 Interactive Animatic HTML Screening Room Tests (AC-8)
# ==============================================================================
class TestV21InteractiveAnimaticHTML:
    """Verifies dark-room cinema animatic transport, SMPTE scrubber, and a11y compliance."""

    def test_animatic_html_contains_all_v21_elements(self, tmp_path):
        pipeline = DirectorPipeline()
        bundle = pipeline.run(
            preset_name="ikea-asmr",
            output_dir=str(tmp_path),
            dry_run=True,
            render_video=False,
        )
        html_content = Path(bundle.storyboard_html_path).read_text(encoding="utf-8")

        assert 'id="btn-play-animatic"' in html_content
        assert 'id="btn-loop-animatic"' in html_content
        assert 'class="hud-hotkeys"' in html_content
        assert 'id="smpte-timecode"' in html_content
        assert 'class="scrubber-track"' in html_content
        assert 'class="audit-drawer"' in html_content
        assert 'id="btn-export-bible"' in html_content
        assert 'aria-live="polite"' in html_content
        assert "alert(" not in html_content

    def test_animatic_html_beat_timecodes_match_scene_action_beats(self, tmp_path):
        import re
        pipeline = DirectorPipeline()
        bundle = pipeline.run(
            preset_name="ikea-asmr",
            output_dir=str(tmp_path),
            dry_run=True,
            render_video=False,
        )
        html_content = Path(bundle.storyboard_html_path).read_text(encoding="utf-8")
        assert "beat-timecode" in html_content
        total_beats = sum(len(s.action_beats) for s in bundle.bible.scenes)
        rendered_beats = len(re.findall(r'data-beat-index="(\d+)"', html_content))
        assert rendered_beats == total_beats

        for scene in bundle.bible.scenes:
            for beat in scene.action_beats:
                assert (beat.beat_title if hasattr(beat, "beat_title") else str(beat)) in html_content

        for preview_file in Path(__file__).parent.parent.glob("examples/*_2_0/storyboard_preview.html"):
            content = preview_file.read_text(encoding="utf-8")
            assert "alert(" not in content, f"alert( found in {preview_file}"

    def test_council_ux_designer_audits_transport_controls(self, tmp_path):
        from omni_director.agents.council import ProductCouncilOrchestrator
        pipeline = DirectorPipeline()
        bundle = pipeline.run(
            preset_name="ikea-asmr",
            output_dir=str(tmp_path),
            dry_run=True,
            render_video=False,
            run_council=True,
        )
        orchestrator = ProductCouncilOrchestrator()
        report = orchestrator.audit(bundle.bible, bundle=bundle)
        ux_review = report.persona_results["council-ux-designer"]
        assert ux_review.score == 25.0
        assert not any(f.category == "animatic_transport" for f in ux_review.findings)
        assert not any(f.category == "animatic_loop_control" for f in ux_review.findings)


# ==============================================================================
# 14. V2.1 Product Council Proposals Tests (AC-4 proposals)
# ==============================================================================
class TestV21CouncilProposals:
    """Verifies the 4 surgical improvements proposed by the autonomous Product Council."""

    def test_telemetry_artifact_checksums_and_verify_bundle(self, tmp_path):
        """FDE proposal: RuntimeTelemetry records sha256 checksums and verify_bundle_checksums detects tampering."""
        from omni_director.telemetry import verify_bundle_checksums
        pipeline = DirectorPipeline()
        bundle = pipeline.run(
            preset_name="ikea-asmr",
            output_dir=str(tmp_path),
            dry_run=True,
            render_video=False,
        )
        # Verify telemetry recorded artifact_checksums in manifest
        manifest_path = tmp_path / "telemetry.json"
        assert manifest_path.is_file()
        assert pipeline.telemetry.artifact_checksums
        assert "storyboard_preview.html" in pipeline.telemetry.artifact_checksums

        # Verify bundle integrity passes
        is_valid, errors = verify_bundle_checksums(tmp_path)
        assert is_valid is True, f"Expected clean bundle verification, got errors: {errors}"
        assert errors == []

        # Tamper with an artifact
        html_file = tmp_path / "storyboard_preview.html"
        html_file.write_text(html_file.read_text(encoding="utf-8") + "<!-- tampered -->", encoding="utf-8")

        # Verify bundle integrity detects mismatch
        is_valid_tampered, errors_tampered = verify_bundle_checksums(tmp_path)
        assert is_valid_tampered is False
        assert any("Checksum mismatch" in err for err in errors_tampered)

    def test_cli_verify_bundle_flag(self, tmp_path):
        """CLI flag --verify-bundle returns 0 on valid bundle and non-zero on tampered bundle."""
        from omni_director.cli import main
        pipeline = DirectorPipeline()
        pipeline.run(
            preset_name="ikea-asmr",
            output_dir=str(tmp_path),
            dry_run=True,
            render_video=False,
        )
        assert main(["--verify-bundle", str(tmp_path)]) == 0

        # Tamper
        (tmp_path / "production_bundle.json").write_text("{}", encoding="utf-8")
        assert main(["--verify-bundle", str(tmp_path)]) == 1

    def test_video_render_agent_blocked_by_failed_audit(self):
        """Agent Engineer proposal: OmniVideoRenderAgent blocks video rendering when prompt audit fails."""
        from omni_director.agents.agent import OmniVideoRenderAgent
        agent = OmniVideoRenderAgent()
        context = {
            "bible": IKEA_ASMR_BIBLE,
            "render_video": True,
            "audit_passed": False,
            "audit_results": [],
        }
        out_ctx = agent.run(context)
        assert out_ctx["video_render_status"] == "blocked_by_failed_audit"
        assert out_ctx["video_manifests"] == []
        assert out_ctx["rendered_videos"] == []

    def test_custom_bible_uses_domain_archetype_defaults(self):
        """Strategist proposal: synthesize_custom_bible incorporates DOMAIN_ARCHETYPES camera, lighting, foley defaults."""
        from omni_director.agents.agent import synthesize_custom_bible
        from omni_director.presets import DOMAIN_ARCHETYPES

        archetype = DOMAIN_ARCHETYPES["automotive_robotics"]
        bible = synthesize_custom_bible("Autonomous electric vehicle robotics pursuit across asphalt with high-torque motor")
        assert bible.domain_archetype == "automotive_robotics"
        assert bible.creative_regime == RegimeType.REGIME_2_KINETIC
        assert bible.camera_rig.rig_type == archetype["default_camera"]
        assert bible.environment.lighting_setup == archetype["default_lighting"]
        assert bible.sonic_blueprint.foley_cues == archetype["default_foley"]
        assert bible.color_palette == archetype["color_palette"]

    def test_html_compiler_beat_row_click_to_seek(self, tmp_path):
        """UX/UI Designer proposal: Animatic .beat-row has interactive click-to-seek, keyboard handling, and jumpToBeat."""
        pipeline = DirectorPipeline()
        bundle = pipeline.run(
            preset_name="ikea-asmr",
            output_dir=str(tmp_path),
            dry_run=True,
            render_video=False,
        )
        html_content = Path(bundle.storyboard_html_path).read_text(encoding="utf-8")

        # Verify interactive attributes on beat-row
        assert 'role="button"' in html_content
        assert 'tabindex="0"' in html_content
        assert 'onclick="jumpToBeat(' in html_content
        assert 'jumpToBeat(' in html_content
        assert 'cursor: pointer;' in html_content

    def test_verify_bundle_checksums_path_traversal_and_directory_guard(self, tmp_path):
        """Verifies verify_bundle_checksums guards against directory paths and path traversal."""
        import json
        from omni_director.telemetry import verify_bundle_checksums

        manifest_traversal = {
            "session_id": "test-session",
            "artifact_checksums": {
                "../../etc/hosts": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                "/etc/passwd": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                ".": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            },
        }
        (tmp_path / "telemetry.json").write_text(json.dumps(manifest_traversal), encoding="utf-8")
        is_valid, errors = verify_bundle_checksums(tmp_path)
        assert is_valid is False
        assert any("Path traversal" in err for err in errors)
        assert any("Missing or non-file artifact" in err or "Path traversal" in err for err in errors)

    def test_pipeline_sequential_runs_have_isolated_telemetry(self, tmp_path):
        """Verifies that sequential runs on the same DirectorPipeline instance have isolated telemetry."""
        pipeline = DirectorPipeline()
        dir1 = tmp_path / "run1"
        dir2 = tmp_path / "run2"

        bundle1 = pipeline.run(
            preset_name="ikea-asmr",
            output_dir=str(dir1),
            dry_run=True,
            run_council=True,
        )
        assert len(pipeline.telemetry.stage_timings) == 8
        session1 = pipeline.telemetry.session_id

        bundle2 = pipeline.run(
            preset_name="ikea-asmr",
            output_dir=str(dir2),
            dry_run=True,
            run_council=True,
        )
        assert len(pipeline.telemetry.stage_timings) == 8
        session2 = pipeline.telemetry.session_id
        assert session1 != session2

    def test_production_bundle_persists_telemetry_and_council_report(self, tmp_path):
        """Verifies that production_bundle.json on disk includes telemetry and council_report with valid checksum."""
        import json
        from omni_director.telemetry import verify_bundle_checksums

        pipeline = DirectorPipeline()
        bundle = pipeline.run(
            preset_name="ikea-asmr",
            output_dir=str(tmp_path),
            dry_run=True,
            run_council=True,
        )
        disk_bundle_path = tmp_path / "production_bundle.json"
        assert disk_bundle_path.is_file()
        disk_data = json.loads(disk_bundle_path.read_text(encoding="utf-8"))

        assert disk_data.get("telemetry") is not None
        assert disk_data["telemetry"]["session_id"] == pipeline.telemetry.session_id
        assert disk_data.get("council_report") is not None
        assert disk_data["council_report"]["overall_score"] >= 88.0

        is_valid, errors = verify_bundle_checksums(tmp_path)
        assert is_valid is True, f"Expected valid checksums, got: {errors}"
        assert errors == []

    def test_preset_builders_and_domain_archetypes(self):
        """Verifies preset builder functions and their domain_archetype assignments."""
        from omni_director.presets import (
            build_ikea_asmr_bible,
            build_sephora_pulse_bible,
            build_sephora_extension_40s_bible,
            build_kinetic_fabric_bible,
            build_sephora_london_pulse_bible,
        )

        b1 = build_ikea_asmr_bible()
        assert b1.domain_archetype == "architectural_sanctuary"

        b2 = build_sephora_pulse_bible()
        assert b2.domain_archetype == "luxury_fashion"

        b3 = build_sephora_extension_40s_bible()
        assert b3.domain_archetype == "luxury_fashion"

        b4 = build_kinetic_fabric_bible()
        assert b4.domain_archetype == "kinetic_action"

        b5 = build_sephora_london_pulse_bible()
        assert b5.domain_archetype == "luxury_fashion"


class TestV21CouncilIteration2:
    """Council Iteration 2 Test Suite:
    1. FDE active SHA-256 integrity verification during council review
    2. Agent Systems Engineer prompt healing history telemetry
    3. Agent Strategist 6-domain coverage in daily council showcases
    4. UX/UI Designer animatic loop toggle and copy prompt controls
    """

    def test_fde_council_detects_tampered_artifact_checksum(self, tmp_path):
        from omni_director.agents.agent import DirectorPipeline
        from omni_director.agents.council import ProductCouncilOrchestrator
        from omni_director.schemas import CouncilFindingSeverity

        pipeline = DirectorPipeline()
        bundle = pipeline.run(
            preset_name="ikea-asmr",
            output_dir=str(tmp_path),
            dry_run=True,
            render_video=False,
            run_council=True,
        )

        orchestrator = ProductCouncilOrchestrator()
        clean_report = orchestrator.audit(bundle, output_dir=tmp_path)
        fde_clean = next(r for r in clean_report.reviews if r.persona.value == "council-fde")
        integrity_clean_findings = [f for f in fde_clean.findings if f.category == "artifact_integrity"]
        assert len(integrity_clean_findings) == 0

        # Tamper with an artifact
        html_file = tmp_path / "storyboard_preview.html"
        assert html_file.exists()
        original_content = html_file.read_text(encoding="utf-8")
        html_file.write_text(original_content + "\n<!-- Tampered content by adversary -->\n", encoding="utf-8")

        # Re-audit with tampered artifact
        tampered_report = orchestrator.audit(bundle, output_dir=tmp_path)
        fde_tampered = next(r for r in tampered_report.reviews if r.persona.value == "council-fde")
        integrity_findings = [f for f in fde_tampered.findings if f.category == "artifact_integrity"]
        assert len(integrity_findings) >= 1
        assert any(f.severity == CouncilFindingSeverity.CRITICAL for f in integrity_findings)
        assert any("Checksum mismatch" in f.message for f in integrity_findings)
        assert fde_tampered.score < fde_clean.score

    def test_agent_engineer_prompt_healing_history_telemetry(self):
        from omni_director.tools.prompt_auditor import audit_omni_scene_prompt, heal_omni_scene_prompt
        from omni_director.schemas import RegimeType

        unhealed_prompt = (
            "### SCENE 1 - INITIATION\n"
            "Subject standing in room. A dynamic cut to wide angle.\n"
            "* Point 1: Slow camera pan across surface.\n"
            "* Point 2: Visual glance toward horizon.\n"
            "Reference tags: <image_1>, <image_2>, <image_3>, <image_4>."
        )

        initial_audit = audit_omni_scene_prompt(
            scene=unhealed_prompt,
            regime=RegimeType.REGIME_2_KINETIC,
        )
        assert initial_audit.score < 90

        healed_prompt, final_audit = heal_omni_scene_prompt(
            scene=unhealed_prompt,
            regime=RegimeType.REGIME_2_KINETIC,
            max_attempts=3,
        )

        assert "healing_history" in final_audit.details
        history = final_audit.details["healing_history"]
        assert "applied_patches" in history
        assert "attempts_executed" in history
        assert "initial_score" in history
        assert "final_score" in history
        assert "healed" in history

        assert isinstance(history["applied_patches"], list)
        assert len(history["applied_patches"]) > 0
        assert history["attempts_executed"] >= 1
        assert history["final_score"] >= history["initial_score"]
        assert history["healed"] is True

        # Test ScenePromptSpec structural field healing (short kinetic_contact_chain & empty action_beats)
        from omni_director.schemas import ScenePromptSpec
        spec = ScenePromptSpec(
            scene_index=1,
            scene_title="Kinetic Sprint",
            timestamp_range="00:00 - 00:08",
            regime=RegimeType.REGIME_2_KINETIC,
            kinetic_contact_chain="short",
            action_beats=[],
            omni_prose_prompt="Runner accelerates at natural 1.0x real-time speed with solid momentum and ground friction. Synchronized diegetic audio has heavy footsteps.",
        )
        healed_spec, spec_audit = heal_omni_scene_prompt(
            scene=spec,
            regime=RegimeType.REGIME_2_KINETIC,
        )
        spec_history = spec_audit.details.get("healing_history", {})
        assert "repaired_kinetic_contact_chain" in spec_history.get("applied_patches", [])
        assert "populated_action_beats" in spec_history.get("applied_patches", [])
        assert spec_history.get("healed") is True

    def test_strategist_all_six_domains_in_daily_council_showcases(self):
        from scripts.run_daily_council import CANONICAL_SHOWCASES
        from omni_director.presets import DOMAIN_ARCHETYPES, classify_brief_domain, get_preset_bible

        assert len(CANONICAL_SHOWCASES) == 10

        constitutional_domains = set(DOMAIN_ARCHETYPES.keys())
        assert len(constitutional_domains) == 6

        observed_domains = set()
        for item in CANONICAL_SHOWCASES:
            if item.get("preset"):
                bible = get_preset_bible(item["preset"])
                domain = getattr(bible, "domain_archetype", None)
                if not domain:
                    domain = classify_brief_domain(bible.logline)
            else:
                domain = classify_brief_domain(item["brief"])
            observed_domains.add(domain)

        assert observed_domains == constitutional_domains, (
            f"Missing domain coverage! Expected {constitutional_domains}, got {observed_domains}"
        )


class TestV21CouncilIteration3Improvements:
    """Validation suite for Council Iteration 3 enhancements across telemetry, doctor, schemas, tools, and presets."""

    def test_telemetry_safe_keys_preserves_musical_key_and_author(self):
        from omni_director.telemetry import _sanitize_value

        payload = {
            "key_signature": "D Minor",
            "musical_key": "F Minor",
            "author": "Creative Director Agent",
            "authenticity": "verified",
            "api_key": "AIzaSyD-SecretKey123456",
            "secret_token": "sk-test9876543210",
            "nested": {
                "keyframe": "shot_01.svg",
                "auth_token": "bearer xyz123",
            }
        }
        sanitized = _sanitize_value(payload)

        # Legitimate keys preserved
        assert sanitized["key_signature"] == "D Minor"
        assert sanitized["musical_key"] == "F Minor"
        assert sanitized["author"] == "Creative Director Agent"
        assert sanitized["authenticity"] == "verified"
        assert sanitized["nested"]["keyframe"] == "shot_01.svg"

        # Sensitive keys redacted
        assert sanitized["api_key"] == "[REDACTED]"
        assert sanitized["secret_token"] == "[REDACTED]"
        assert sanitized["nested"]["auth_token"] == "[REDACTED]"

    def test_scene_prompt_payload_alias_export(self):
        from omni_director import ScenePromptPayload, ScenePromptSpec
        from omni_director.schemas import ScenePromptPayload as SchemasPayload
        from omni_director.schemas import RegimeType

        assert ScenePromptPayload is ScenePromptSpec
        assert SchemasPayload is ScenePromptSpec

        spec = ScenePromptPayload(
            scene_index=1,
            scene_title="Alias Test Scene",
            timestamp_range="00:00 - 00:05",
            regime=RegimeType.REGIME_2_KINETIC,
            action_beats=["Beat 1: Acceleration"],
            omni_prose_prompt="A dynamic high-speed camera tracking shot at 1.0x real-time speed.",
        )
        assert isinstance(spec, ScenePromptSpec)
        assert spec.scene_title == "Alias Test Scene"

    def test_heal_omni_scene_prompt_trims_kwargs_action_beats(self):
        from omni_director.tools.prompt_auditor import heal_omni_scene_prompt
        from omni_director.schemas import RegimeType

        raw_prompt = "Camera sweeps across the mountain ridge at 1.0x real-time speed with solid gravity."
        four_beats = ["Beat 1", "Beat 2", "Beat 3", "Beat 4"]

        result = heal_omni_scene_prompt(
            scene=raw_prompt,
            regime=RegimeType.REGIME_2_KINETIC,
            action_beats=four_beats,
        )

        assert result.audit.passed
        assert "trimmed_action_beats" in result.audit.details.get("healing_history", {}).get("applied_patches", [])
        assert len(result.audit.details.get("action_beats_count", 0)) if isinstance(result.audit.details.get("action_beats_count"), list) else result.audit.details.get("action_beats_count") <= 3

    def test_synthesize_custom_bible_storytelling_mode_and_bgm_archetypes(self):
        from omni_director.agents.agent import synthesize_custom_bible
        from omni_director.schemas import StorytellingMode, RegimeType

        # 1. Culinary brief should map to culinary_asmr archetype with 68 BPM and C Major
        culinary_bible = synthesize_custom_bible(
            "Slow motion macro pour of ceremonial matcha into hot foaming water with bamboo whisk",
            storytelling_mode=StorytellingMode.MODE_B_CONTINUOUS_CHAIN,
        )
        assert culinary_bible.storytelling_mode == StorytellingMode.MODE_B_CONTINUOUS_CHAIN
        assert culinary_bible.master_bgm.tempo_bpm == 68
        assert culinary_bible.master_bgm.key_signature == "C Major"
        assert "ASMR" in culinary_bible.master_bgm.genre_style

        # 2. Automotive brief should map to automotive_robotics archetype with 130 BPM and F Minor
        auto_bible = synthesize_custom_bible(
            "Hypercar autonomous pursuit on night race track with telemetry and high-torque electric motor",
        )
        assert auto_bible.creative_regime == RegimeType.REGIME_2_KINETIC
        assert auto_bible.master_bgm.tempo_bpm == 130
        assert auto_bible.master_bgm.key_signature == "F Minor"

    def test_doctor_reports_warn_or_pass_for_core_dependencies(self):
        from omni_director.doctor import run_doctor, CheckStatus

        report = run_doctor()
        assert report.passed
        core_check = next(c for c in report.checks if c.name == "core_dependencies")
        assert core_check.status in (CheckStatus.PASS, CheckStatus.WARN)


class TestV21CouncilIteration4ProductCouncilImprovements:
    """Verifies council iteration 4 audit findings and product improvements."""

    def test_cli_bible_file_nonexistent_returns_exit_1(self, capsys):
        from omni_director.cli import main
        ret = main(["run", "--bible-file", "nonexistent_file_xyz.json"])
        assert ret == 1
        captured = capsys.readouterr()
        assert "does not exist" in captured.err or "does not exist" in captured.out

    def test_cli_verify_bundle_flag_order_disambiguation(self, tmp_path):
        from omni_director.cli import main
        ret = main(["verify-bundle", "--strict", str(tmp_path / "missing")])
        assert ret == 1

    def test_doctor_disk_space_check(self):
        from omni_director.doctor import run_doctor, CheckStatus
        report = run_doctor()
        disk_check = next((c for c in report.checks if c.name == "disk_space"), None)
        assert disk_check is not None
        assert disk_check.status in (CheckStatus.PASS, CheckStatus.WARN)

    def test_telemetry_mandatory_bundle_files_enforced(self, tmp_path):
        import json
        from omni_director.telemetry import verify_bundle_checksums
        manifest = tmp_path / "telemetry.json"
        manifest.write_text(json.dumps({"artifact_checksums": {"dummy.txt": "abc"}}), encoding="utf-8")
        is_valid, errors = verify_bundle_checksums(tmp_path)
        assert not is_valid
        assert any("Mandatory bundle file" in e for e in errors)

    def test_prompt_auditor_zero_image_reference_rejection_and_healing(self):
        from omni_director.tools.prompt_auditor import audit_omni_scene_prompt, heal_omni_scene_prompt
        from omni_director.schemas import RegimeType

        prompt_with_zero = "A camera pans across the horizon adhering to character <image_0> at 1.0x real-time speed."
        audit = audit_omni_scene_prompt(prompt_with_zero, regime=RegimeType.REGIME_2_KINETIC)
        assert not audit.passed
        assert any("Rule 5 Violation" in e for e in audit.errors)

        healed = heal_omni_scene_prompt(prompt_with_zero, regime=RegimeType.REGIME_2_KINETIC)
        assert "<image_1>" in healed.healed_prompt
        assert "<image_0>" not in healed.healed_prompt
        assert "capped_image_references" in healed.audit.details.get("healing_history", {}).get("applied_patches", [])

    def test_prompt_healing_sanitizes_negative_constraints(self):
        from omni_director.tools.prompt_auditor import heal_omni_scene_prompt
        from omni_director.schemas import RegimeType

        negative_prompt = "Camera pans across room with no blur and without camera shake at 1.0x real-time speed."
        healed = heal_omni_scene_prompt(negative_prompt, regime=RegimeType.REGIME_2_KINETIC)
        assert "no blur" not in healed.healed_prompt.lower()
        assert "without camera shake" not in healed.healed_prompt.lower()
        assert "sanitized_negative_constraints" in healed.audit.details.get("healing_history", {}).get("applied_patches", [])

    def test_bible_is_mode_b_continuous_property(self):
        from omni_director.presets import SEPHORA_EXTENSION_40S_BIBLE, IKEA_ASMR_BIBLE
        assert SEPHORA_EXTENSION_40S_BIBLE.is_mode_b_continuous is True
        assert IKEA_ASMR_BIBLE.is_mode_b_continuous is False

    def test_agent_model_validation_rejects_legacy_models(self):
        import pytest
        from omni_director.agents.agent import ScenePromptAgent, CreativeDirectorAgent

        with pytest.raises(ValueError, match="not in the approved 2026 model whitelist|deprecated"):
            ScenePromptAgent(scene_index=1, model_name="gemini-1.5-pro")

        with pytest.raises(ValueError, match="not in the approved 2026 model whitelist|deprecated"):
            CreativeDirectorAgent(model_name="gemini-1.0-ultra")

    def test_html_compiler_contrast_and_keyboard_nav(self, tmp_path):
        from omni_director.presets import IKEA_ASMR_BIBLE
        from omni_director.schemas import ProductionBundle
        from omni_director.tools.html_compiler import compile_storyboard_html

        bundle = ProductionBundle(
            bible=IKEA_ASMR_BIBLE,
            storyboard_html_path="",
            bundle_json_path="",
            visual_plates={},
            audit_reports=[],
        )
        html_path = compile_storyboard_html(bundle, output_dir=tmp_path)
        content = Path(html_path).read_text(encoding="utf-8")

        assert "--text-dim: #7E88A4;" in content
        assert "⌨ [Space] Play" in content
        assert "[,/.] Frame" in content
        assert "Home/0" in content
        assert "renderFrame(currentFrame - 1)" in content
        assert "renderFrame(currentFrame + 1)" in content
        assert "renderFrame(0)" in content






