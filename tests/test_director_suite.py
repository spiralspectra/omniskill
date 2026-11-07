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


class TestV21CouncilIteration5ProductCouncilExcellence:
    """Verifies Council Iteration 5 specialist findings, accessibility, and strategic rigor."""

    def test_doctor_dependency_version_check(self):
        from omni_director.doctor import run_doctor, CheckStatus
        report = run_doctor()
        pyd_check = next((c for c in report.checks if c.name == "pydantic_version"), None)
        assert pyd_check is not None
        assert pyd_check.status == CheckStatus.PASS
        assert pyd_check.details.get("major", 0) >= 2

    def test_verify_bundle_missing_telemetry_diagnostic(self, tmp_path):
        from omni_director.telemetry import verify_bundle_checksums
        empty_dir = tmp_path / "empty_bundle"
        empty_dir.mkdir(parents=True)
        is_valid, errors = verify_bundle_checksums(empty_dir)
        assert not is_valid
        assert any("manifest not found" in e for e in errors)

    def test_prompt_auditor_heals_extended_negative_phrases(self):
        from omni_director.tools.prompt_auditor import heal_omni_scene_prompt
        from omni_director.schemas import RegimeType

        raw_prompt = "Tracking shot with no jitter, without artifacts, and natural speed."
        healed = heal_omni_scene_prompt(raw_prompt, regime=RegimeType.REGIME_2_KINETIC)
        assert "no jitter" not in healed.healed_prompt.lower()
        assert "without artifacts" not in healed.healed_prompt.lower()
        assert "steady and stable motion" in healed.healed_prompt.lower()
        assert "pristine organic texture" in healed.healed_prompt.lower()
        assert "sanitized_negative_constraints" in healed.audit.details.get("healing_history", {}).get("applied_patches", [])

    def test_strategist_mode_b_continuous_narrative_continuity(self):
        from omni_director.agents.council import ProductCouncilOrchestrator
        from omni_director.presets import SEPHORA_EXTENSION_40S_BIBLE
        orchestrator = ProductCouncilOrchestrator()
        review = orchestrator._review_strategist(SEPHORA_EXTENSION_40S_BIBLE)
        assert review.score >= 24.0
        # Check that no narrative continuity defect was found for valid Mode B preset
        continuity_defects = [f for f in review.findings if f.category == "narrative_continuity"]
        assert len(continuity_defects) == 0

    def test_animatic_reduced_motion_and_aria_live_management(self, tmp_path):
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

        # Reduced motion check
        assert "@media (prefers-reduced-motion: reduce)" in content
        # Dynamic ARIA-live management check
        assert "smpteEl.setAttribute('aria-live', 'off')" in content
        assert "smpteEl.setAttribute('aria-live', 'polite')" in content

    def test_all_six_domain_archetypes_sonic_and_visual_integrity(self):
        from omni_director.agents.agent import synthesize_custom_bible
        from omni_director.presets import DOMAIN_ARCHETYPES

        archetype_briefs = {
            "automotive_robotics": "Precision CNC robotics assembling carbon-fiber hypercar chassis on high-speed track",
            "culinary_asmr": "Macro 100mm optics tracking ceremonial matcha powder sifting into black ceramic bowl with steam",
            "luxury_fashion": "Haute couture silk velvet runway fashion campaign in brutalist travertine marble gallery",
            "kinetic_action": "High-speed parkour athletic sprint and acrobatic martial arts stunt sequence with dynamic movement and jumping across rooftops",
            "tech_hardware": "Cleanroom nanoscale silicon wafer positioning under laser etching beams in anodized aluminum cryo-chamber",
            "architectural_sanctuary": "Curved bamboo pavilions and cascading vertical gardens with photovoltaic glass domes in morning mist",
        }

        for domain, brief in archetype_briefs.items():
            bible = synthesize_custom_bible(brief)
            assert bible.domain_archetype == domain
            assert bible.master_bgm.tempo_bpm > 0
            assert len(bible.master_bgm.key_signature) > 0
            assert len(bible.master_bgm.instrumentation) > 0
            assert len(bible.scenes) >= 2
            for scene in bible.scenes:
                assert scene.craft_camera is not None
                assert scene.diegetic_sonic is not None

    def test_svg_vector_plates_all_aspect_ratios(self):
        from omni_director.tools.nano_banana import NanoBananaStoryboardEngine
        from omni_director.schemas import (
            AspectRatio,
            CraftCameraSpec,
            MasterProductionBible,
            RegimeType,
            ScenePromptSpec,
        )

        dummy_scene = ScenePromptSpec(
            scene_index=1,
            scene_title="Sanctuary Arrival",
            timestamp_range="00:00 - 00:08",
            regime=RegimeType.REGIME_1_ATMOSPHERIC,
            action_beats=["Beat 1: Establishing initial movement", "Beat 2: Kinetic culmination"],
            omni_prose_prompt="Wide shot of architectural sanctuary.",
            craft_camera=CraftCameraSpec(
                rig_type="35mm Prime",
                focal_length_mm=35,
                composition="Wide establishing",
                route="Static",
                action_anchor="Center",
                focus_axis="180-degree",
                tone_rig="Cinematic Prime",
            )
        )

        ratios = [
            (AspectRatio.RATIO_16_9, "viewBox=\"0 0 1920 1080\""),
            (AspectRatio.RATIO_9_16, "viewBox=\"0 0 1080 1920\""),
            (AspectRatio.RATIO_1_1, "viewBox=\"0 0 1080 1080\""),
            (AspectRatio.RATIO_2_39_1, "viewBox=\"0 0 2560 1071\""),
        ]

        from omni_director.presets import IKEA_ASMR_BIBLE
        engine = NanoBananaStoryboardEngine()
        for ratio, expected_viewbox in ratios:
            dummy_bible = IKEA_ASMR_BIBLE.model_copy(update={"aspect_ratio": ratio})
            svg = engine.render_scene_keyframe_svg(dummy_bible.scenes[0], dummy_bible, show_safe_guides=True)
            assert expected_viewbox in svg
            assert "safe-guide-action" in svg or 'stroke-dasharray="6,6"' in svg or 'stroke-dasharray="8 6"' in svg
            assert "safe-guide-title" in svg or 'stroke-dasharray="3,3"' in svg or 'stroke-dasharray="4 4"' in svg

    def test_telemetry_redacts_oauth_and_github_tokens(self):
        from omni_director.telemetry import _sanitize_value

        sample_data = {
            "oauth_token": "ya29.a0AfH6SMB_secret_oauth_token_payload",
            "gh_pat": "ghp_1234567890abcdefghijklmnopqrstuvwxyz",
            "fine_grained": "github_pat_11ABCDEF_very_secret_personal_token",
            "api_key": "AIzaSyD-dummy_google_api_key_for_testing",
            "musical_key": "C Major",
            "key_signature": "D Minor",
            "author": "Creative Director",
        }
        sanitized = _sanitize_value(sample_data)
        assert sanitized["oauth_token"] == "[REDACTED]"
        assert sanitized["gh_pat"] == "[REDACTED]"
        assert sanitized["fine_grained"] == "[REDACTED]"
        assert sanitized["api_key"] == "[REDACTED]"
        assert sanitized["musical_key"] == "C Major"
        assert sanitized["key_signature"] == "D Minor"
        assert sanitized["author"] == "Creative Director"

    def test_verify_bundle_detects_zero_byte_corrupted_files(self, tmp_path):
        import hashlib
        import json
        from omni_director.telemetry import verify_bundle_checksums

        bundle_dir = tmp_path / "corrupted_bundle"
        bundle_dir.mkdir(parents=True)
        corrupted_html = bundle_dir / "storyboard_preview.html"
        corrupted_html.touch()  # 0 bytes!

        bundle_json = bundle_dir / "production_bundle.json"
        bundle_json.write_text("{\"test\": 1}", encoding="utf-8")

        telemetry_file = bundle_dir / "telemetry.json"
        telemetry_payload = {
            "artifact_checksums": {
                "production_bundle.json": hashlib.sha256(bundle_json.read_bytes()).hexdigest(),
                "storyboard_preview.html": hashlib.sha256(b"").hexdigest(),
            }
        }
        telemetry_file.write_text(json.dumps(telemetry_payload), encoding="utf-8")

        is_valid, errors = verify_bundle_checksums(bundle_dir)
        assert not is_valid
        assert any("Zero-byte empty artifact" in e for e in errors)

    def test_prompt_healing_preserves_aperture_and_timestamps(self):
        """Verifies prompt self-healing replaces legacy model IDs without corrupting optical apertures or timestamps."""
        from omni_director.tools.prompt_auditor import heal_omni_scene_prompt

        raw_prompt = (
            "Shot on 35mm at f/3.1 aperture with soft bokeh. At 3.1s into the scene, "
            "reference model gemini-3.1-pro or gemini-3.1-flash should not appear. "
            "Do not rotate camera."
        )
        healed_text, result = heal_omni_scene_prompt(
            scene=raw_prompt,
            regime=RegimeType.REGIME_1_ATMOSPHERIC,
            scene_index=1,
            storytelling_mode=StorytellingMode.MODE_A_PARALLEL_CUT,
        )
        # Aperture and timestamps must be strictly preserved
        assert "f/3.1" in healed_text
        assert "3.1s" in healed_text
        # Legacy model IDs must be healed to 2026 standard
        assert "gemini-3.1" not in healed_text
        assert "gemini-4-argon" in healed_text
        # Negative constraint converted affirmatively
        assert "do not rotate" not in healed_text.lower()
        assert "maintain locked static framing" in healed_text.lower()

    def test_craft_camera_focal_length_bounds(self):
        """Verifies CraftCameraSpec enforces optical focal length limits between 10mm and 500mm."""
        # Valid focal lengths
        spec = CraftCameraSpec(
            rig_type="Tripod",
            focal_length_mm=24,
            composition="Centered",
            route="Static",
            action_anchor="Subject",
            focus_axis="180-degree",
            tone_rig="Anamorphic",
        )
        assert spec.focal_length_mm == 24

        spec_tele = CraftCameraSpec(
            rig_type="Technocrane",
            focal_length_mm=400,
            composition="Tight",
            route="Crane Up",
            action_anchor="Subject",
            focus_axis="Locked",
            tone_rig="Spherical",
        )
        assert spec_tele.focal_length_mm == 400

        # Below 10mm
        with pytest.raises(ValidationError):
            CraftCameraSpec(
                rig_type="Tripod",
                focal_length_mm=5,
                composition="Centered",
                route="Static",
                action_anchor="Subject",
                focus_axis="180-degree",
                tone_rig="Anamorphic",
            )

        # Above 500mm
        with pytest.raises(ValidationError):
            CraftCameraSpec(
                rig_type="Tripod",
                focal_length_mm=800,
                composition="Centered",
                route="Static",
                action_anchor="Subject",
                focus_axis="180-degree",
                tone_rig="Anamorphic",
            )

    def test_master_production_bible_mode_b_40s_ceiling(self):
        """Verifies MasterProductionBible enforces a 40-second ceiling on continuous oner Mode B scenes."""
        from omni_director.presets import SEPHORA_EXTENSION_40S_BIBLE

        # 40s Mode B scene is valid
        assert SEPHORA_EXTENSION_40S_BIBLE.storytelling_mode == StorytellingMode.MODE_B_CONTINUOUS_CHAIN
        assert len(SEPHORA_EXTENSION_40S_BIBLE.scenes) == 4
        assert SEPHORA_EXTENSION_40S_BIBLE.total_runtime_seconds == 40
        assert SEPHORA_EXTENSION_40S_BIBLE.is_mode_b_continuous is True

        # A continuous Mode B scene with total_runtime_seconds > 40 must raise ValidationError
        with pytest.raises(ValidationError, match="40-second ceiling"):
            SEPHORA_EXTENSION_40S_BIBLE.model_validate(
                {**SEPHORA_EXTENSION_40S_BIBLE.model_dump(), "total_runtime_seconds": 45}
            )

    def test_custom_bible_domain_dna_characters_and_invariants(self):
        """Verifies synthesize_custom_bible loads domain-specific characters and invariants."""
        from omni_director.agents.agent import CreativeDirectorAgent

        agent = CreativeDirectorAgent(DirectorConfig())

        # Culinary ASMR domain
        culinary_bible = agent.synthesize_custom_bible(
            project_title="Artisan Truffle Symphony",
            creative_brief="Handcrafted artisanal chocolate truffle dusting and tempering",
            genre="culinary_asmr",
            aspect_ratio=AspectRatio.RATIO_1_1,
            total_runtime_sec=20,
        )
        assert len(culinary_bible.characters) > 0
        char_desc = (culinary_bible.characters[0].name + " " + culinary_bible.characters[0].wardrobe_polarity).lower()
        assert "chef" in char_desc or "apron" in char_desc or "artisan" in char_desc or "hero" in char_desc
        invariants_str = " ".join(culinary_bible.environment.positive_invariants).lower()
        assert "ceramic" in invariants_str or "hinoki" in invariants_str or "rigid" in invariants_str

        # Tech Hardware domain
        tech_bible = agent.synthesize_custom_bible(
            project_title="Neural Core Matrix",
            creative_brief="Quantum silicon chip assembly in cleanroom",
            genre="tech_hardware",
            aspect_ratio=AspectRatio.RATIO_16_9,
            total_runtime_sec=20,
        )
        assert len(tech_bible.characters) > 0
        tech_char = (tech_bible.characters[0].name + " " + tech_bible.characters[0].wardrobe_polarity).lower()
        assert "cleanroom" in tech_char or "bunny suit" in tech_char or "hero" in tech_char or "engineer" in tech_char
        tech_invariants_str = " ".join(tech_bible.environment.positive_invariants).lower()
        assert "cleanroom" in tech_invariants_str or "silicon" in tech_invariants_str or "rigid" in tech_invariants_str

    def test_doctor_model_whitelist_enforcement(self):
        """Verifies doctor preflight fails on unapproved model identifiers."""
        from omni_director.doctor import validate_model_identifier

        # Valid 2026 models
        assert validate_model_identifier("gemini-4-argon") is True
        assert validate_model_identifier("gemini-3.8-flash") is True
        assert validate_model_identifier("gemini-3-pro-image") is True
        assert validate_model_identifier("gemini-omni-1.1-flash-preview") is True

        # Unapproved / legacy models
        assert validate_model_identifier("gemini-3.1-pro") is False
        assert validate_model_identifier("gpt-4o") is False
        assert validate_model_identifier("claude-3-opus") is False


class TestV22ProductManagerFeatures:
    """Verifies v2.2.0 features recommended by the Senior Product Manager (council-product-manager):
    1. NLE Post-Production Exporter (CMX 3600 EDL, FCPXML v1.10, CSV Shot List, Call Sheet MD, CLI omni export)
    2. Dialogue Pacing Guardrail (2.5 WPS ceiling) & Subtitle Compiler (SRT/VTT + Animatic CC HUD)
    3. Multi-Cam Coverage & Conversational Iteration Engine (3-angle coverage + Turn 2-4 deltas + UI tabs)
    4. Senior Product Manager Persona & Daily Council Consultation
    """

    def test_nle_exporter_edl_fcpxml_csv_callsheet(self, tmp_path):
        import xml.etree.ElementTree as ET
        from omni_director.presets import IKEA_ASMR_BIBLE
        from omni_director.tools.nle_export import (
            export_all_nle_artifacts,
            export_cmx3600_edl,
            export_fcpxml,
            export_production_callsheet_md,
            export_shot_list_csv,
        )

        # 1. CMX 3600 EDL
        edl_text = export_cmx3600_edl(IKEA_ASMR_BIBLE, fps=24)
        assert "TITLE:" in edl_text
        assert "FCM: NON-DROP FRAME" in edl_text
        assert "001  AX       V     C        00:00:00:00" in edl_text
        assert "* FROM CLIP NAME:" in edl_text

        # 2. FCPXML v1.10
        fcpxml_text = export_fcpxml(IKEA_ASMR_BIBLE, fps=24)
        root = ET.fromstring(fcpxml_text)
        assert root.tag == "fcpxml"
        assert root.attrib.get("version") == "1.10"
        spine_clips = list(root.iter("asset-clip"))
        assert len(spine_clips) == len(IKEA_ASMR_BIBLE.scenes)

        # 3. CSV Shot List
        csv_text = export_shot_list_csv(IKEA_ASMR_BIBLE)
        lines = [line for line in csv_text.strip().splitlines() if line.strip()]
        assert len(lines) == len(IKEA_ASMR_BIBLE.scenes) + 1
        assert "scene_index,timecode_start,timecode_end,rig_type,focal_length_mm,composition,action_beats,audio_cues" in lines[0]

        # 4. Call Sheet Markdown
        md_text = export_production_callsheet_md(IKEA_ASMR_BIBLE)
        assert "# Production Call Sheet:" in md_text
        assert "## 1. Visual Continuity & Lighting Setup" in md_text
        assert "## 3. Scene-by-Scene Shooting Schedule" in md_text

        # 5. Export All Bundle
        artifacts = export_all_nle_artifacts(IKEA_ASMR_BIBLE, tmp_path, fps=24)
        assert {"edl", "fcpxml", "csv", "call_sheet"}.issubset(set(artifacts.keys()))
        for path_str in artifacts.values():
            p = Path(path_str)
            assert p.is_file() and p.stat().st_size > 0

    def test_cli_export_subcommand_all_formats(self, tmp_path):
        from omni_director.cli import main

        ret = main(["export", "--preset", "sephora-pulse", "--format", "all", "-o", str(tmp_path)])
        assert ret == 0
        expected_files = [
            "timeline.edl",
            "sequence.fcpxml",
            "shot_list.csv",
            "call_sheet.md",
            "subtitles.srt",
            "subtitles.vtt",
        ]
        for fname in expected_files:
            fpath = tmp_path / fname
            assert fpath.is_file(), f"Missing exported artifact: {fname}"
            assert fpath.stat().st_size > 0

    def test_dialogue_pacing_guardrail_and_srt_vtt_subtitles(self):
        from omni_director.presets import IKEA_ASMR_BIBLE
        from omni_director.tools.dialogue import (
            audit_dialogue_pacing,
            compile_subtitles_srt,
            compile_subtitles_vtt,
        )

        # Clean scene with concise dialogue passes <= 2.5 WPS
        concise_scene = ScenePromptSpec(
            scene_index=1,
            scene_title="Whisper Reveal",
            timestamp_range="00:00 - 00:08",
            regime=RegimeType.REGIME_1_ATMOSPHERIC,
            action_beats=["Beat 1: Slow reveal"],
            omni_prose_prompt="Observational camera captures the quiet room.",
            diegetic_sonic=DiegeticSonicSpec(
                foley_cues=["Soft linen rustle"],
                dialogue_lines=['Narrator: "Welcome home to stillness."'],
                room_acoustics="Warm damped studio",
            ),
        )
        passed_ok, wps_ok, warnings_ok = audit_dialogue_pacing(concise_scene)
        assert passed_ok is True
        assert wps_ok <= 2.5
        assert warnings_ok == []

        # Overloaded dialogue (> 20 words in 8s) triggers pacing violation
        overloaded_scene = concise_scene.model_copy(
            update={
                "diegetic_sonic": DiegeticSonicSpec(
                    foley_cues=["Footsteps"],
                    dialogue_lines=[
                        "Lead: This dialogue line contains far too many spoken words for an eight second cinematic window and will rush lip sync articulation significantly."
                    ],
                    room_acoustics="Hall",
                )
            }
        )
        passed_fail, wps_fail, warnings_fail = audit_dialogue_pacing(overloaded_scene)
        assert passed_fail is False
        assert wps_fail > 2.5
        assert len(warnings_fail) >= 1

        # SRT and WebVTT generation
        srt = compile_subtitles_srt(IKEA_ASMR_BIBLE)
        vtt = compile_subtitles_vtt(IKEA_ASMR_BIBLE)
        assert "00:00:00,000 -->" in srt
        assert "WEBVTT" in vtt
        assert "00:00:00.000 -->" in vtt

    def test_multicam_coverage_and_conversational_deltas(self):
        from omni_director.presets import IKEA_ASMR_BIBLE, KINETIC_FABRIC_BIBLE
        from omni_director.tools.coverage import (
            generate_scene_coverage,
            synthesize_conversational_deltas,
        )
        from omni_director.tools.prompt_auditor import audit_omni_scene_prompt

        for bible in (IKEA_ASMR_BIBLE, KINETIC_FABRIC_BIBLE):
            scene = bible.scenes[0]
            variants = generate_scene_coverage(scene, bible)
            assert len(variants) == 3
            assert list(variants.keys()) == ["master", "dynamic", "macro"]

            for v in variants.values():
                # Every coverage variant must pass the 7-Point Gemini Omni Prompting Standard
                variant_scene = scene.model_copy(
                    update={
                        "craft_camera": v.craft_camera,
                        "omni_prose_prompt": v.prompt_text,
                    }
                )
                audit = audit_omni_scene_prompt(
                    variant_scene,
                    regime=bible.creative_regime,
                    storytelling_mode=bible.storytelling_mode,
                )
                assert audit.passed is True, f"Coverage variant {v.coverage_type} failed audit: {audit.errors}"
                assert audit.score >= 90.0

            deltas = synthesize_conversational_deltas(scene, bible)
            assert len(deltas) == 3
            assert any("Turn 2" in d for d in deltas)
            assert any("Turn 3" in d for d in deltas)
            assert any("Turn 4" in d for d in deltas)

    def test_animatic_cc_hud_and_coverage_tabs(self, tmp_path):
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

        # Closed Caption HUD & Toggle
        assert 'id="animatic-cc-hud"' in content
        assert 'id="btn-cc-animatic"' in content
        assert "function toggleCC()" in content
        assert "CC [C]" in content

        # Multi-Cam Coverage Selector Tabs
        assert 'class="coverage-selector"' in content
        assert "function selectCoverage(" in content
        assert "[A: Master 24mm]" in content
        assert "[B: Dynamic Hero]" in content
        assert "[C: Macro 100mm]" in content

    def test_senior_product_manager_persona_and_council_consultation(self):
        from omni_director import (
            ProductCouncilOrchestrator,
            ProductFeatureProposal,
            ProductManagerAgent,
            SENIOR_PM_PERSONA_PROMPT,
            __version__,
        )
        from omni_director.presets import IKEA_ASMR_BIBLE

        assert __version__ in ("2.2.0", "2.3.0", "2.4.0", "2.5.0", "2.6.0", "2.7.0")
        assert "world-class senior product manager that recently joined this project from a top software company" in SENIOR_PM_PERSONA_PROMPT

        pm_agent = ProductManagerAgent()
        assert pm_agent.persona_prompt == SENIOR_PM_PERSONA_PROMPT
        proposals = pm_agent.inspect_product(IKEA_ASMR_BIBLE)
        assert len(proposals) >= 3
        assert all(isinstance(p, ProductFeatureProposal) for p in proposals)
        assert {p.feature_id for p in proposals} >= {"PM-FEAT-001", "PM-FEAT-002", "PM-FEAT-003"}

        orchestrator = ProductCouncilOrchestrator()
        report = orchestrator.audit(IKEA_ASMR_BIBLE)
        assert report.version in ("2.2.0", "2.3.0", "2.4.0", "2.5.0", "2.6.0", "2.7.0")
        assert report.pm_persona_prompt == SENIOR_PM_PERSONA_PROMPT
        assert len(report.pm_recommendations) >= 3
        md = orchestrator.generate_markdown_report(report)
        assert "Senior Product Manager Roadmap & Feature Inspection" in md
        assert "PM-FEAT-001" in md


class TestV23SchemaAndPromptAuditor:
    """Verifies v2.3.0 schema models, shutter camera grammar, speed-ramp kinetic momentum auditing, and PM proposals."""

    def test_asc_cdl_and_color_look_spec_serialization(self):
        from omni_director.schemas import AscCdlSpec, ColorLookPreset, ColorLookSpec

        cdl = AscCdlSpec(slope=(1.05, 0.98, 0.95), offset=(-0.01, 0.0, 0.02), power=(1.0, 1.02, 1.05), saturation=1.1)
        spec = ColorLookSpec(
            look_preset=ColorLookPreset.KODAK_5219_VISION3,
            working_color_space="ACEScg",
            target_display="Rec.709",
            cdl=cdl,
            contrast_pivot=0.435,
            halation_bloom=0.15,
        )

        dumped = spec.model_dump()
        assert dumped["look_preset"] == "kodak_5219_vision3"
        assert dumped["cdl"]["saturation"] == 1.1
        json_str = spec.model_dump_json()
        assert "kodak_5219_vision3" in json_str

        # Test defaults
        default_look = ColorLookSpec()
        assert default_look.look_preset == ColorLookPreset.REC709_NEUTRAL
        assert default_look.cdl.slope == (1.0, 1.0, 1.0)
        assert default_look.cdl.saturation == 1.0

    def test_speed_ramp_curve_spec(self):
        from omni_director.schemas import SpeedRampCurveSpec, SpeedRampMode

        ramp = SpeedRampCurveSpec(
            mode=SpeedRampMode.PULSE_TIME_DILATION,
            base_fps=24.0,
            peak_capture_fps=120.0,
            shutter_angle_deg=90.0,
            curve_keyframe_points=[(0.0, 1.0), (0.4, 0.2), (0.7, 0.2), (1.0, 1.0)],
            motion_blur_character="crisp staccato action trail",
        )
        assert ramp.mode == SpeedRampMode.PULSE_TIME_DILATION
        assert ramp.peak_capture_fps == 120.0
        assert len(ramp.curve_keyframe_points) == 4

        # Bounds validation
        import pytest
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            SpeedRampCurveSpec(shutter_angle_deg=400.0)

    def test_audio_stem_mixer_spec_and_stem_types(self):
        from omni_director.schemas import AudioStemMixerSpec, StemChannelStrip, StemType

        mixer = AudioStemMixerSpec()
        assert len(mixer.channels) == 4
        assert StemType.DIALOGUE in mixer
        assert StemType.MUSIC in mixer
        assert mixer["dialogue"].target_lufs == -18.0
        assert mixer.master_lufs_target == -23.0

        # String dict input normalization
        custom_mixer = AudioStemMixerSpec(
            master_gain_db=-1.5,
            channels={
                "dialogue": StemChannelStrip(stem=StemType.DIALOGUE, label="Main Vocals", gain_db=-2.0),
                "foley": StemChannelStrip(stem=StemType.FOLEY, label="Foley SFX", gain_db=-6.0),
                "ambience": StemChannelStrip(stem=StemType.AMBIENCE, label="Room Tone", gain_db=-12.0),
                "music": StemChannelStrip(stem=StemType.MUSIC, label="Lyria Score", gain_db=-3.0),
            },
        )
        assert custom_mixer["dialogue"].label == "Main Vocals"
        assert custom_mixer.model_dump()["master_gain_db"] == -1.5

    def test_craft_camera_spec_shutter_angle_extension(self):
        from omni_director.schemas import CraftCameraSpec

        cam = CraftCameraSpec(
            rig_type="Steadicam",
            focal_length_mm=28,
            composition="Dynamic low-angle",
            route="Tracking forward",
            action_anchor="Subject torso",
            focus_axis="Continuous follow",
            tone_rig="Spherical Prime",
            shutter_angle_deg=90.0,
            shutter_timing_token="90° action staccato shutter",
        )
        assert cam.shutter_angle_deg == 90.0
        assert cam.shutter_timing_token == "90° action staccato shutter"

        # Default shutter values
        default_cam = CraftCameraSpec(
            rig_type="Tripod",
            focal_length_mm=50,
            composition="Center",
            route="Static",
            action_anchor="Face",
            focus_axis="Locked",
            tone_rig="Spherical",
        )
        assert default_cam.shutter_angle_deg == 180.0
        assert default_cam.shutter_timing_token is None

    def test_bible_and_scene_spec_v23_fields_integration(self):
        from omni_director.presets import IKEA_ASMR_BIBLE
        from omni_director.schemas import (
            AudioStemMixerSpec,
            ColorLookPreset,
            ColorLookSpec,
            SpeedRampCurveSpec,
            SpeedRampMode,
        )

        bible = IKEA_ASMR_BIBLE.model_copy(
            update={
                "master_color_look": ColorLookSpec(look_preset=ColorLookPreset.FUJI_ETERNA_500T),
                "master_audio_mixer": AudioStemMixerSpec(),
            }
        )
        assert bible.master_color_look.look_preset == ColorLookPreset.FUJI_ETERNA_500T
        assert len(bible.master_audio_mixer.channels) == 4

        scene = bible.scenes[0].model_copy(
            update={
                "speed_ramp": SpeedRampCurveSpec(mode=SpeedRampMode.DECELERATION_IMPACT),
                "scene_color_look": ColorLookSpec(look_preset=ColorLookPreset.BLEACH_BYPASS_SILVER),
            }
        )
        assert scene.speed_ramp.mode == SpeedRampMode.DECELERATION_IMPACT
        assert scene.scene_color_look.look_preset == ColorLookPreset.BLEACH_BYPASS_SILVER

    def test_prompt_auditor_shutter_recognition_and_reward(self):
        from omni_director.schemas import RegimeType
        from omni_director.tools.prompt_auditor import audit_omni_scene_prompt

        prompt_with_shutter = (
            "A fluid Steadicam moves through the rain-swept courtyard at natural 1.0x real-time speed. "
            "Filmed with a 90° staccato shutter angle at 1/48s exposure timing, rendering crisp micro-droplet kinetic contact. "
            "Synchronized diegetic audio captures heavy rhythmic downpour."
        )
        audit = audit_omni_scene_prompt(prompt_with_shutter, regime=RegimeType.REGIME_2_KINETIC)
        assert audit.passed is True
        assert audit.details.get("shutter_angle_compliant") is True
        assert audit.details.get("shutter_angle_reward") == 5.0

    def test_prompt_auditor_speed_ramp_kinetic_momentum_check_and_healing(self):
        from omni_director.schemas import RegimeType, ScenePromptSpec, SpeedRampCurveSpec, SpeedRampMode
        from omni_director.tools.prompt_auditor import audit_omni_scene_prompt, heal_omni_scene_prompt

        # Scene with speed ramp but missing kinetic momentum descriptors
        scene = ScenePromptSpec(
            scene_index=1,
            scene_title="Impact Burst",
            timestamp_range="00:00 - 00:05",
            regime=RegimeType.REGIME_2_KINETIC,
            action_beats=["Beat 1: Explosive burst"],
            omni_prose_prompt="Subject leaps into frame in slow motion with floating drift and disconnected weight.",
            speed_ramp=SpeedRampCurveSpec(mode=SpeedRampMode.DECELERATION_IMPACT, peak_capture_fps=120.0),
        )

        audit = audit_omni_scene_prompt(scene, regime=RegimeType.REGIME_2_KINETIC)
        assert any("kinetic momentum conservation" in e for e in audit.errors)

        healed_scene, healed_audit = heal_omni_scene_prompt(scene, regime=RegimeType.REGIME_2_KINETIC)
        assert "injected_speed_ramp_momentum" in healed_audit.details.get("healing_history", {}).get("applied_patches", [])
        assert healed_audit.passed is True

    def test_senior_pm_proposals_include_v23_roadmap_features(self):
        from omni_director.agents.council import ProductManagerAgent
        from omni_director.presets import IKEA_ASMR_BIBLE

        pm = ProductManagerAgent()
        proposals = pm.inspect_product(IKEA_ASMR_BIBLE)
        feature_ids = {p.feature_id for p in proposals}
        assert {"PM-FEAT-001", "PM-FEAT-002", "PM-FEAT-003", "PM-FEAT-004", "PM-FEAT-005", "PM-FEAT-006"} <= feature_ids

        p4 = next(p for p in proposals if p.feature_id == "PM-FEAT-004")
        assert p4.title == "ASC CDL Color Science, Cinematic Look Presets & SVG Filter Grading Engine"
        assert p4.priority == "P0"

        p5 = next(p for p in proposals if p.feature_id == "PM-FEAT-005")
        assert p5.title == "Dynamic Speed Ramping, Shutter Angle & Motion Timing Engine"
        assert p5.priority == "P0"

        p6 = next(p for p in proposals if p.feature_id == "PM-FEAT-006")
        assert p6.title == "Interactive Diegetic Stem Audio Mixer & Metering Console"
        assert p6.priority == "P0"


class TestV23ToolsAndExports:
    """Tests for PM-FEAT-004, PM-FEAT-005, and PM-FEAT-006 tool and export layers."""

    def test_color_grade_presets_and_cdl_xml(self, tmp_path):
        import xml.etree.ElementTree as ET
        from omni_director.presets import IKEA_ASMR_BIBLE
        from omni_director.schemas import ColorLookPreset
        from omni_director.tools.color_grade import (
            cdl_to_svg_matrix_filter,
            embed_cdl_in_edl,
            export_asc_cdl_file,
            export_asc_cdl_xml,
            get_preset_color_look,
        )

        # 1. Preset look verification for all 6 presets
        presets = [
            ColorLookPreset.REC709_NEUTRAL,
            ColorLookPreset.KODAK_5219_VISION3,
            ColorLookPreset.FUJI_ETERNA_500T,
            ColorLookPreset.BLEACH_BYPASS_SILVER,
            ColorLookPreset.TEAL_AND_ORANGE_BLOCKBUSTER,
            ColorLookPreset.MONOCHROME_PANATOMIC_X,
        ]
        for p in presets:
            look = get_preset_color_look(p)
            assert look.look_preset == p
            assert len(look.cdl.slope) == 3
            assert len(look.cdl.offset) == 3
            assert len(look.cdl.power) == 3
            assert 0.0 <= look.cdl.saturation <= 4.0

        # String lookup check
        look_str = get_preset_color_look("kodak_5219_vision3")
        assert look_str.look_preset == ColorLookPreset.KODAK_5219_VISION3

        # 2. ASC CDL XML export
        cdl_xml = export_asc_cdl_xml(IKEA_ASMR_BIBLE)
        root = ET.fromstring(cdl_xml)
        assert "ColorDecisionList" in root.tag
        decisions = list(root.iter("{urn:ASC:CDL:v1.01}ColorDecision")) or list(root.iter("ColorDecision"))
        assert len(decisions) >= 1

        # File export
        out_cdl = tmp_path / "test_grade.cdl"
        res_path = export_asc_cdl_file(IKEA_ASMR_BIBLE, out_cdl)
        assert res_path.is_file() and res_path.stat().st_size > 0

        # 3. EDL comment injection
        edl_mock = (
            "TITLE: TEST\nFCM: NON-DROP FRAME\n\n"
            "001  AX       V     C        00:00:00:00 00:00:08:00 00:00:00:00 00:00:08:00\n"
            "* FROM CLIP NAME: SCENE_01_PLATE.MP4\n"
        )
        embedded_edl = embed_cdl_in_edl(edl_mock, IKEA_ASMR_BIBLE)
        assert "*ASC_SOP" in embedded_edl
        assert "*ASC_SAT" in embedded_edl

        # 4. SVG matrix filter
        svg_filt = cdl_to_svg_matrix_filter(look_str.cdl, filter_id="custom-filter")
        assert '<filter id="custom-filter"' in svg_filt
        assert "<feColorMatrix" in svg_filt
        assert "<feComponentTransfer" in svg_filt

    def test_speed_ramp_curves_and_fcpxml_timemap(self):
        import xml.etree.ElementTree as ET
        from omni_director.presets import IKEA_ASMR_BIBLE
        from omni_director.schemas import SpeedRampMode
        from omni_director.tools.speed_ramp import (
            export_fcpxml_timemap,
            format_craft_shutter_tokens,
            synthesize_speed_ramp_curve,
        )

        # 1. Synthesize curves across all modes
        modes = [
            SpeedRampMode.CONSTANT_REALTIME,
            SpeedRampMode.DECELERATION_IMPACT,
            SpeedRampMode.ACCELERATION_BURST,
            SpeedRampMode.SNAP_FREEZE_RESUME,
            SpeedRampMode.PULSE_TIME_DILATION,
        ]
        for m in modes:
            curve = synthesize_speed_ramp_curve(m, base_fps=24, peak_capture_fps=120, shutter_angle_deg=180.0)
            assert curve.mode == m
            assert len(curve.curve_keyframe_points) >= 2
            assert curve.curve_keyframe_points[0][0] == 0.0
            assert curve.curve_keyframe_points[-1][0] == 1.0

        # 2. Shutter token formatting
        token_180 = format_craft_shutter_tokens(180.0, base_fps=24)
        assert token_180 == "180° optical shutter at 1/48s exposure"
        token_90 = format_craft_shutter_tokens(90.0, base_fps=24)
        assert token_90 == "90° optical shutter at 1/96s exposure"

        # 3. FCPXML timemap export
        scene = IKEA_ASMR_BIBLE.scenes[0].model_copy(deep=True)
        scene.speed_ramp = synthesize_speed_ramp_curve(SpeedRampMode.DECELERATION_IMPACT)
        timemap_xml = export_fcpxml_timemap(scene, sequence_fps=24.0)
        timemap_root = ET.fromstring(timemap_xml.strip())
        assert timemap_root.tag == "timeMap"
        timepts = list(timemap_root.iter("timept"))
        assert len(timepts) >= 2

    def test_audio_mixer_stems_and_loudness(self, tmp_path):
        import json
        from omni_director.presets import IKEA_ASMR_BIBLE
        from omni_director.tools.audio_mixer import (
            estimate_broadcast_loudness,
            export_audio_stems_file,
            export_audio_stems_manifest,
            synthesize_default_stem_mixer,
        )

        mixer = synthesize_default_stem_mixer(master_lufs_target=-23.0)
        assert len(mixer.channels) == 4
        assert "dialogue" in mixer.channels
        assert "music" in mixer.channels

        loudness = estimate_broadcast_loudness(mixer)
        assert "integrated_lufs" in loudness
        assert "true_peak_dbfs" in loudness
        assert loudness["integrated_lufs"] < 0.0

        # Export manifest dict
        manifest = export_audio_stems_manifest(IKEA_ASMR_BIBLE)
        assert manifest["project_title"] == IKEA_ASMR_BIBLE.project_title
        assert "stems" in manifest
        assert len(manifest["stems"]) == 4
        assert "fairlight_routing" in manifest
        assert "premiere_layout" in manifest

        # Export file
        out_file = tmp_path / "audio_stems_manifest.json"
        res_file = export_audio_stems_file(IKEA_ASMR_BIBLE, out_file)
        assert res_file.is_file()
        loaded = json.loads(res_file.read_text(encoding="utf-8"))
        assert loaded["project_title"] == IKEA_ASMR_BIBLE.project_title

    def test_nle_export_integration_with_cdl_and_speed_ramp(self, tmp_path):
        import xml.etree.ElementTree as ET
        from omni_director.presets import IKEA_ASMR_BIBLE
        from omni_director.schemas import ColorLookPreset, SpeedRampMode
        from omni_director.tools.color_grade import get_preset_color_look
        from omni_director.tools.nle_export import export_cmx3600_edl, export_fcpxml
        from omni_director.tools.speed_ramp import synthesize_speed_ramp_curve

        bible = IKEA_ASMR_BIBLE.model_copy(deep=True)
        bible.master_color_look = get_preset_color_look(ColorLookPreset.KODAK_5219_VISION3)
        bible.scenes[0].speed_ramp = synthesize_speed_ramp_curve(SpeedRampMode.DECELERATION_IMPACT)

        # 1. CMX 3600 EDL embeds CDL
        edl_text = export_cmx3600_edl(bible, fps=24)
        assert "*ASC_SOP" in edl_text
        assert "*ASC_SAT" in edl_text

        # 2. FCPXML embeds timeMap
        fcpxml_text = export_fcpxml(bible, fps=24)
        root = ET.fromstring(fcpxml_text)
        assert root.tag == "fcpxml"
        timemaps = list(root.iter("timeMap"))
        assert len(timemaps) >= 1

    def test_cli_export_cdl_and_stems(self, tmp_path):
        from omni_director.cli import main

        # 1. Export cdl only
        ret_cdl = main(["export", "--preset", "ikea-asmr", "--format", "cdl", "-o", str(tmp_path)])
        assert ret_cdl == 0
        assert (tmp_path / "production_grade.cdl").is_file()

        # 2. Export stems only
        ret_stems = main(["export", "--preset", "ikea-asmr", "--format", "stems", "-o", str(tmp_path)])
        assert ret_stems == 0
        assert (tmp_path / "audio_stems_manifest.json").is_file()


class TestV23DarkRoomCinemaAnimatic:
    """Verifies Council UX Designer v2.3.0 Dark-Room Cinema Animatic features."""

    def test_animatic_svg_cdl_filters_and_look_selector(self, tmp_path):
        from omni_director.tools.html_compiler import compile_storyboard_html
        from omni_director.schemas import ProductionBundle, ColorLookPreset
        from omni_director.presets import IKEA_ASMR_BIBLE
        from omni_director.tools.color_grade import get_preset_color_look

        bible = IKEA_ASMR_BIBLE.model_copy(deep=True)
        bible.master_color_look = get_preset_color_look(ColorLookPreset.KODAK_5219_VISION3)
        bundle = ProductionBundle(
            bible=bible,
            storyboard_html_path="",
            bundle_json_path="",
            visual_plates={},
            audit_reports=[],
        )

        html_path = compile_storyboard_html(bundle, output_dir=tmp_path)
        content = Path(html_path).read_text(encoding="utf-8")

        # 1. All 6 SVG CDL Filter definitions present
        assert 'id="cdl-filter-rec709_neutral"' in content
        assert 'id="cdl-filter-kodak_5219_vision3"' in content
        assert 'id="cdl-filter-fuji_eterna_500t"' in content
        assert 'id="cdl-filter-bleach_bypass_silver"' in content
        assert 'id="cdl-filter-teal_and_orange_blockbuster"' in content
        assert 'id="cdl-filter-monochrome_panatomic_x"' in content

        # 2. Transport Look controls
        assert 'id="look-selector"' in content
        assert 'id="look-badge"' in content
        assert 'class="look-grading-controls"' in content

        # 3. Look Switching Logic & Hotkey [L]
        assert "function setLook(preset)" in content
        assert "function cycleLook()" in content
        assert "cycleLook()" in content

    def test_animatic_speed_ramp_badge_and_velocity_track(self, tmp_path):
        from omni_director.tools.html_compiler import compile_storyboard_html
        from omni_director.schemas import ProductionBundle, SpeedRampMode
        from omni_director.presets import IKEA_ASMR_BIBLE
        from omni_director.tools.speed_ramp import synthesize_speed_ramp_curve

        bible = IKEA_ASMR_BIBLE.model_copy(deep=True)
        bible.scenes[0].speed_ramp = synthesize_speed_ramp_curve(
            SpeedRampMode.DECELERATION_IMPACT,
            peak_capture_fps=120,
            shutter_angle_deg=180.0
        )
        bundle = ProductionBundle(
            bible=bible,
            storyboard_html_path="",
            bundle_json_path="",
            visual_plates={},
            audit_reports=[],
        )

        html_path = compile_storyboard_html(bundle, output_dir=tmp_path)
        content = Path(html_path).read_text(encoding="utf-8")

        # 1. Velocity track bar inside scrubber track wrap
        assert 'class="velocity-track-container"' in content
        assert 'class="velocity-track-bar"' in content
        assert 'class="velocity-marker' in content
        assert '⚡ S1 120fps' in content

        # 2. Speed ramp badge in scene card header
        assert 'class="badge-speed-ramp"' in content
        assert "120fps Deceleration Impact" in content
        assert "180° Shutter" in content

    def test_animatic_dark_room_audio_mixer_console(self, tmp_path):
        from omni_director.tools.html_compiler import compile_storyboard_html
        from omni_director.schemas import ProductionBundle
        from omni_director.presets import IKEA_ASMR_BIBLE
        from omni_director.tools.audio_mixer import synthesize_default_stem_mixer

        bible = IKEA_ASMR_BIBLE.model_copy(deep=True)
        bible.master_audio_mixer = synthesize_default_stem_mixer()
        bundle = ProductionBundle(
            bible=bible,
            storyboard_html_path="",
            bundle_json_path="",
            visual_plates={},
            audit_reports=[],
        )

        html_path = compile_storyboard_html(bundle, output_dir=tmp_path)
        content = Path(html_path).read_text(encoding="utf-8")

        # 1. Mixer Toggle Button in HUD Actions
        assert 'id="btn-toggle-mixer"' in content
        assert 'AUDIO [M]' in content

        # 2. Mixer Slide-out Drawer & Accessibility
        assert 'id="animatic-audio-mixer"' in content
        assert 'role="region"' in content
        assert 'aria-label="Audio Mixing Console"' in content

        # 3. 4 Channel Strips + Master Strip
        assert 'id="strip-dia"' in content
        assert 'id="strip-sfx"' in content
        assert 'id="strip-amb"' in content
        assert 'id="strip-mus"' in content
        assert 'id="strip-master"' in content

        # 4. Faders, Pans, Mutes, Solos, and LUFS readouts
        assert 'id="fader-dia"' in content
        assert 'id="pan-dia"' in content
        assert 'id="mute-dia"' in content
        assert 'id="solo-dia"' in content
        assert 'id="fader-master"' in content
        assert 'id="master-lufs-display"' in content
        assert 'id="val-master-lufs"' in content

        # 5. Dual LED VU meters
        assert 'id="vu-meter-left"' in content
        assert 'id="vu-meter-right"' in content

        # 6. Web Audio tone synthesis engine & hotkey [M]
        assert "function toggleMixer()" in content
        assert "function initWebAudio()" in content
        assert "function toggleAudioPreview()" in content
        assert "function drawVUMeter(canvas, levelDb)" in content
        assert "function startVUMeterLoop()" in content
        assert "function recalcBroadcastLoudness()" in content
        assert "toggleMixer()" in content


class TestCouncilStrategistCommercialDomainAlignment:
    """Verifies Council Strategist domain mapping across all 6 Commercial Domain Archetypes."""

    def test_six_domain_archetypes_return_expected_cdl_looks_and_speed_ramps(self):
        from omni_director.presets import (
            DOMAIN_ARCHETYPES,
            get_domain_color_look,
            get_domain_speed_ramp,
            get_domain_audio_mixer,
        )
        from omni_director.schemas import ColorLookPreset, SpeedRampMode

        expected_mappings = {
            "automotive_robotics": (ColorLookPreset.BLEACH_BYPASS_SILVER, SpeedRampMode.SNAP_FREEZE_RESUME, 90.0),
            "culinary_asmr": (ColorLookPreset.KODAK_5219_VISION3, SpeedRampMode.DECELERATION_IMPACT, 180.0),
            "luxury_fashion": (ColorLookPreset.FUJI_ETERNA_500T, SpeedRampMode.PULSE_TIME_DILATION, 180.0),
            "kinetic_action": (ColorLookPreset.TEAL_AND_ORANGE_BLOCKBUSTER, SpeedRampMode.ACCELERATION_BURST, 180.0),
            "tech_hardware": (ColorLookPreset.REC709_NEUTRAL, SpeedRampMode.CONSTANT_REALTIME, 180.0),
            "architectural_sanctuary": (ColorLookPreset.REC709_NEUTRAL, SpeedRampMode.CONSTANT_REALTIME, 180.0),
        }

        for domain, (exp_look, exp_ramp, exp_shutter) in expected_mappings.items():
            assert domain in DOMAIN_ARCHETYPES
            arch_meta = DOMAIN_ARCHETYPES[domain]
            assert arch_meta["color_look_preset"] == exp_look
            assert arch_meta["speed_ramp_mode"] == exp_ramp
            assert arch_meta["default_shutter_angle"] == exp_shutter

            look = get_domain_color_look(domain)
            assert look.look_preset == exp_look

            ramp = get_domain_speed_ramp(domain)
            assert ramp.mode == exp_ramp
            assert ramp.shutter_angle_deg == exp_shutter

            mixer = get_domain_audio_mixer(domain)
            assert len(mixer.channels) == 4
            for ch_name in ["dialogue", "foley", "ambience", "music"]:
                assert ch_name in mixer.channels
                assert mixer.channels[ch_name].gain_db == arch_meta["default_stem_levels"][ch_name]["gain_db"]
                assert mixer.channels[ch_name].target_lufs == arch_meta["default_stem_levels"][ch_name]["target_lufs"]

    def test_golden_preset_bibles_have_aligned_domain_specs(self):
        from omni_director.presets import (
            IKEA_ASMR_BIBLE,
            SEPHORA_PULSE_BIBLE,
            SEPHORA_EXTENSION_40S_BIBLE,
            KINETIC_FABRIC_BIBLE,
        )
        from omni_director.schemas import ColorLookPreset, SpeedRampMode

        bibles = [
            (IKEA_ASMR_BIBLE, "architectural_sanctuary", ColorLookPreset.REC709_NEUTRAL, SpeedRampMode.CONSTANT_REALTIME),
            (SEPHORA_PULSE_BIBLE, "luxury_fashion", ColorLookPreset.FUJI_ETERNA_500T, SpeedRampMode.PULSE_TIME_DILATION),
            (SEPHORA_EXTENSION_40S_BIBLE, "luxury_fashion", ColorLookPreset.FUJI_ETERNA_500T, SpeedRampMode.PULSE_TIME_DILATION),
            (KINETIC_FABRIC_BIBLE, "kinetic_action", ColorLookPreset.TEAL_AND_ORANGE_BLOCKBUSTER, SpeedRampMode.ACCELERATION_BURST),
        ]

        for bible, exp_domain, exp_look, exp_ramp in bibles:
            assert bible.domain_archetype == exp_domain
            assert bible.master_color_look is not None
            assert bible.master_color_look.look_preset == exp_look
            assert bible.master_audio_mixer is not None
            for scene in bible.scenes:
                assert scene.speed_ramp is not None
                assert scene.speed_ramp.mode == exp_ramp
                assert scene.scene_color_look is not None
                assert scene.scene_color_look.look_preset == exp_look

    def test_council_strategist_review_awards_full_score_on_aligned_bibles(self):
        from omni_director.agents.council import ProductCouncilOrchestrator
        from omni_director.presets import IKEA_ASMR_BIBLE, SEPHORA_PULSE_BIBLE, KINETIC_FABRIC_BIBLE

        orchestrator = ProductCouncilOrchestrator()
        for bible in [IKEA_ASMR_BIBLE, SEPHORA_PULSE_BIBLE, KINETIC_FABRIC_BIBLE]:
            review = orchestrator._review_strategist(bible)
            assert review.score == 25.0
            assert review.max_score == 25.0
            assert not any(f.severity == "critical" for f in review.findings)
            finding_msgs = [f.message for f in review.findings]
            assert any("Deterministic ASC CDL look preset aligned" in m for m in finding_msgs)
            assert any("Calibrated 4-stem audio mixer verified" in m for m in finding_msgs)
            assert any("Kinetic speed ramp curves verified" in m for m in finding_msgs)

    def test_council_strategist_penalizes_missing_domain_alignment(self):
        from omni_director.agents.council import ProductCouncilOrchestrator
        from omni_director.presets import IKEA_ASMR_BIBLE

        unaligned_bible = IKEA_ASMR_BIBLE.model_copy(deep=True)
        unaligned_bible.master_color_look = None
        unaligned_bible.master_audio_mixer = None
        for sc in unaligned_bible.scenes:
            sc.speed_ramp = None

        orchestrator = ProductCouncilOrchestrator()
        review = orchestrator._review_strategist(unaligned_bible)
        assert review.score < 25.0
        finding_msgs = [f.message for f in review.findings]
        assert any("Master color look spec missing" in m for m in finding_msgs)
        assert any("Master 4-stem audio mixer missing" in m for m in finding_msgs)
        assert any("lack kinetic speed ramp curves" in m for m in finding_msgs)

    def test_cli_export_cdl_and_stems_for_all_golden_presets(self, tmp_path):
        import json
        from omni_director.cli import main

        for preset_name in ["ikea-asmr", "sephora-pulse", "kinetic-fabric"]:
            target_dir = tmp_path / preset_name
            ret_cdl = main(["export", "--preset", preset_name, "--format", "cdl", "-o", str(target_dir)])
            assert ret_cdl == 0
            cdl_file = target_dir / "production_grade.cdl"
            assert cdl_file.is_file()
            assert "<ColorCorrection" in cdl_file.read_text(encoding="utf-8")

            ret_stems = main(["export", "--preset", preset_name, "--format", "stems", "-o", str(target_dir)])
            assert ret_stems == 0
            stems_file = target_dir / "audio_stems_manifest.json"
            assert stems_file.is_file()
            manifest = json.loads(stems_file.read_text(encoding="utf-8"))
            assert "stems" in manifest
            assert len(manifest["stems"]) == 4
            assert "fairlight_routing" in manifest

    def test_synthesized_custom_bible_domain_alignment_and_council_passing(self, tmp_path):
        from omni_director.agents.agent import synthesize_custom_bible
        from omni_director.agents.council import ProductCouncilOrchestrator
        from omni_director.schemas import ColorLookPreset, SpeedRampMode, ProductionBundle

        custom_brief = "Autonomous electric hypercar pursuit through neo-Tokyo streets with telemetry HUD and ceramic brake glow."
        bible = synthesize_custom_bible(custom_brief)
        assert bible.domain_archetype == "automotive_robotics"
        assert bible.master_color_look is not None
        assert bible.master_color_look.look_preset == ColorLookPreset.BLEACH_BYPASS_SILVER
        assert bible.scenes[0].speed_ramp.mode == SpeedRampMode.SNAP_FREEZE_RESUME

        bundle = ProductionBundle(
            bible=bible,
            storyboard_html_path="",
            bundle_json_path="",
            visual_plates={},
            audit_reports=[],
        )
        orchestrator = ProductCouncilOrchestrator()
        report = orchestrator.audit(bundle, bible=bible, auto_heal=True, output_dir=tmp_path)
        assert report.passed is True
        assert report.overall_score >= 90.0
        assert report.critical_findings_count == 0
        assert report.persona_reviews["council-strategist"].score == 25.0


# ==============================================================================
# Optical Lens & Virtual Production Stage Suite (PM-FEAT-007 & PM-FEAT-008)
# ==============================================================================
class TestOpticalLensAndVirtualProduction:
    """Verifies PM-FEAT-007 (Optical Lens Suite) and PM-FEAT-008 (Virtual Production Stage)."""

    def test_optical_lens_schemas_and_fov_calculations(self):
        from omni_director.schemas import (
            AnamorphicSqueeze,
            OpticalLensSpec,
            SensorFormat,
        )
        from omni_director.tools.optical_lens import (
            calculate_hyperfocal_distance,
            calculate_sensor_fov,
            format_optical_prompt_token,
        )

        assert SensorFormat.SUPER_35 == "Super35 (24.89 x 18.66mm)"
        assert SensorFormat.FULL_FRAME == "Full Frame (36.00 x 24.00mm)"
        assert SensorFormat.ARRI_LF == "Large Format / ARRI LF (36.70 x 25.54mm)"
        assert SensorFormat.IMAX_70MM == "IMAX 15/70mm (70.41 x 52.63mm)"
        assert SensorFormat.VISTAVISION == "VistaVision (40.96 x 21.60mm)"
        assert AnamorphicSqueeze.ANAMORPHIC_2_0X == 2.0

        lens = OpticalLensSpec(
            sensor_format=SensorFormat.FULL_FRAME,
            focal_length_mm=35,
            aperture_t_stop=2.8,
            anamorphic_squeeze=1.0,
        )
        hfov, vfov = calculate_sensor_fov(lens.sensor_format, lens.focal_length_mm, lens.anamorphic_squeeze)
        assert hfov == 54.43
        assert vfov == 37.85

        hyperfocal = calculate_hyperfocal_distance(lens.focal_length_mm, lens.aperture_t_stop)
        assert hyperfocal == 14.58

        token = format_optical_prompt_token(lens)
        assert "Full Frame" in token
        assert "35mm T2.8" in token
        assert "spherical" in token

        # Test anamorphic 2.0x on Super35
        lens_ana = OpticalLensSpec(
            sensor_format="super35",
            focal_length_mm=50,
            aperture_t_stop=2.0,
            anamorphic_squeeze=2.0,
            lens_series="Kowa Anamorphic",
        )
        assert lens_ana.sensor_format == SensorFormat.SUPER_35
        h_ana, v_ana = calculate_sensor_fov(lens_ana.sensor_format, lens_ana.focal_length_mm, lens_ana.anamorphic_squeeze)
        assert h_ana > 50.0  # Wider field of view due to 2.0x horizontal squeeze
        token_ana = format_optical_prompt_token(lens_ana)
        assert "2.00x anamorphic squeeze" in token_ana

    def test_lens_metadata_csv_export(self, tmp_path):
        import csv
        from omni_director.presets import IKEA_ASMR_BIBLE
        from omni_director.tools.optical_lens import export_lens_metadata_csv, export_lens_metadata_file

        csv_str = export_lens_metadata_csv(IKEA_ASMR_BIBLE)
        assert "scene_index,scene_title,sensor_format" in csv_str
        assert "ARRI Signature Prime" in csv_str

        out_path = tmp_path / "lens_test.csv"
        saved_p = export_lens_metadata_file(IKEA_ASMR_BIBLE, out_path)
        assert saved_p.is_file()

        reader = list(csv.DictReader(saved_p.read_text(encoding="utf-8").splitlines()))
        assert len(reader) == len(IKEA_ASMR_BIBLE.scenes)
        assert float(reader[0]["horizontal_fov_deg"]) > 0.0
        assert float(reader[0]["hyperfocal_distance_m"]) > 0.0

    def test_virtual_production_stage_schemas_and_synthesis(self, tmp_path):
        import json
        from omni_director.presets import IKEA_ASMR_BIBLE
        from omni_director.schemas import VirtualProductionStageSpec
        from omni_director.tools.virtual_production import (
            export_dmx_patch_csv,
            export_ue_ndisplay_manifest,
            export_virtual_production_bundle,
            synthesize_default_vp_stage,
        )

        stage = synthesize_default_vp_stage("StageCraft Prime")
        assert isinstance(stage, VirtualProductionStageSpec)
        assert stage.stage_name == "StageCraft Prime"
        assert stage.led_wall.diameter_meters == 24.0
        assert len(stage.dmx_lighting_rig) == 4

        # nDisplay JSON manifest
        ndisplay_json = export_ue_ndisplay_manifest(stage)
        data = json.loads(ndisplay_json)
        assert "nDisplay" in data
        assert data["nDisplay"]["cluster"]["master_node"]["id"] == "Node_Primary_Controller"
        assert data["nDisplay"]["projection"]["geometry"]["native_resolution"] == "15360x2880"

        # DMX patch CSV
        dmx_csv = export_dmx_patch_csv(stage)
        assert "KEY_SKY_01" in dmx_csv
        assert "Arri SkyPanel S360-C" in dmx_csv

        # Bundle export
        bundle_out = export_virtual_production_bundle(IKEA_ASMR_BIBLE, tmp_path)
        assert "ndisplay" in bundle_out
        assert "dmx" in bundle_out
        assert "stage_spec" in bundle_out
        assert Path(bundle_out["ndisplay"]).is_file()
        assert Path(bundle_out["dmx"]).is_file()
        assert Path(bundle_out["stage_spec"]).is_file()

    def test_cli_export_lens_and_vp_formats(self, tmp_path):
        from omni_director.cli import main

        # Export lens format
        target_lens = tmp_path / "lens_export"
        ret_lens = main(["export", "--preset", "ikea-asmr", "--format", "lens", "-o", str(target_lens)])
        assert ret_lens == 0
        lens_file = target_lens / "lens_package.csv"
        assert lens_file.is_file()
        assert "horizontal_fov_deg" in lens_file.read_text(encoding="utf-8")

        # Export vp format
        target_vp = tmp_path / "vp_export"
        ret_vp = main(["export", "--preset", "ikea-asmr", "--format", "vp", "-o", str(target_vp)])
        assert ret_vp == 0
        assert (target_vp / "ndisplay_stage_manifest.json").is_file()
        assert (target_vp / "dmx_patch.csv").is_file()
        assert (target_vp / "vp_stage_spec.json").is_file()

        # Export all includes lens and vp
        target_all = tmp_path / "all_export"
        ret_all = main(["export", "--preset", "ikea-asmr", "--format", "all", "-o", str(target_all)])
        assert ret_all == 0
        assert (target_all / "lens_package.csv").is_file()
        assert (target_all / "ndisplay_stage_manifest.json").is_file()
        assert (target_all / "dmx_patch.csv").is_file()

    def test_senior_pm_proposals_include_v24_features(self):
        from omni_director.agents.council import ProductManagerAgent
        from omni_director.presets import IKEA_ASMR_BIBLE

        pm = ProductManagerAgent()
        proposals = pm.inspect_product(bible=IKEA_ASMR_BIBLE)
        p_ids = [p.feature_id for p in proposals]
        assert "PM-FEAT-007" in p_ids
        assert "PM-FEAT-008" in p_ids

        p7 = next(p for p in proposals if p.feature_id == "PM-FEAT-007")
        assert p7.priority == "P0"
        assert p7.status == "implemented"
        assert "Optical Lens" in p7.title

        p8 = next(p for p in proposals if p.feature_id == "PM-FEAT-008")
        assert p8.priority == "P0"
        assert p8.status == "implemented"
        assert "Virtual Production" in p8.title

    def test_domain_optical_lens_and_vp_presets(self):
        from omni_director.presets import (
            get_domain_optical_lens,
            get_domain_virtual_production,
            DOMAINS_6,
        )
        from omni_director.schemas import OpticalLensSpec, VirtualProductionStageSpec

        for domain in DOMAINS_6:
            lens = get_domain_optical_lens(domain)
            assert isinstance(lens, OpticalLensSpec)
            assert lens.focal_length_mm > 0
            assert lens.aperture_t_stop > 0
            assert lens.horizontal_fov_deg is not None
            assert lens.horizontal_fov_deg > 0

            vp = get_domain_virtual_production(domain)
            assert isinstance(vp, VirtualProductionStageSpec)
            assert vp.stage_name
            assert len(vp.dmx_fixtures) > 0

    def test_animatic_viewfinder_and_vp_stage_hud(self, tmp_path):
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
        html_path = compile_storyboard_html(bundle, tmp_path)
        assert html_path.is_file()
        content = html_path.read_text(encoding="utf-8")

        # Viewfinder elements
        assert 'id="btn-viewfinder-animatic"' in content
        assert 'id="animatic-viewfinder-overlay"' in content
        assert 'toggleViewfinder()' in content
        assert 'class="badge-lens"' in content
        assert 'class="viewfinder-overlay"' in content

        # Virtual Production Stage elements
        assert 'id="btn-vp-stage-animatic"' in content
        assert 'id="animatic-vp-stage-modal"' in content
        assert 'toggleVPStageModal()' in content
        assert 'class="badge-vp"' in content
        assert 'class="vp-schematic-svg"' in content

    def test_prompt_auditor_optical_and_vp_compliance(self):
        from omni_director.tools.prompt_auditor import audit_omni_scene_prompt, heal_omni_scene_prompt
        from omni_director.presets import IKEA_ASMR_BIBLE

        scene = IKEA_ASMR_BIBLE.scenes[0]
        res = audit_omni_scene_prompt(scene)
        assert res.score >= 90.0

        # Test prompt healing injects optical and VP tokens when missing
        test_scene = scene.model_copy(deep=True)
        test_scene.omni_prose_prompt = "A simple camera shot of wooden table with soft light."
        healed_scene, healed_res = heal_omni_scene_prompt(test_scene)
        assert "T" in healed_scene.omni_prose_prompt or "mm" in healed_scene.omni_prose_prompt
        assert healed_res.score >= 90.0

    def test_product_council_v24_audit_pass(self, tmp_path):
        from omni_director.agents.council import ProductCouncilOrchestrator
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
        compile_storyboard_html(bundle, tmp_path)

        council = ProductCouncilOrchestrator()
        report = council.convene_council(bible=IKEA_ASMR_BIBLE, bundle=bundle, output_dir=tmp_path)

        assert report.version in ("2.4.0", "2.5.0", "2.6.0", "2.7.0")
        assert report.passed is True
        assert report.critical_findings_count == 0
        assert report.overall_score >= 90.0


class TestV25MotionControlAndStudioLightingAnimatic:
    """Verifies PM-FEAT-009 (MoCo Trajectory HUD) and PM-FEAT-010 (Studio Gaffer & Lighting HUD) in animatic HTML."""

    def test_animatic_moco_and_gaffer_hud_elements(self, tmp_path):
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
        html_path = compile_storyboard_html(bundle, tmp_path)
        assert html_path.is_file()
        content = html_path.read_text(encoding="utf-8")

        # 1. Transport Bar Buttons & Hotkey Remappings
        assert 'id="btn-moco-animatic"' in content
        assert '🤖 MoCo [K]' in content
        assert 'id="btn-gaffer-animatic"' in content
        assert '💡 Gaffer [G]' in content
        assert 'id="btn-loop-animatic"' in content
        assert '🔁 Loop [O]' in content

        # 2. Header Cheat Sheet includes remapped hotkeys
        assert '[O] Loop' in content
        assert '[K] MoCo' in content
        assert '[G] Gaffer' in content
        assert '[U] Guides' in content

        # 3. Motion Control Trajectory HUD (PM-FEAT-009)
        assert 'id="animatic-moco-hud"' in content
        assert 'role="dialog"' in content
        assert 'aria-modal="true"' in content
        assert 'MOTION CONTROL TRAJECTORY HUD' in content
        assert 'id="moco-val-x"' in content
        assert 'id="moco-val-y"' in content
        assert 'id="moco-val-z"' in content
        assert 'id="moco-val-roll"' in content
        assert 'id="moco-val-pitch"' in content
        assert 'id="moco-val-yaw"' in content
        assert 'id="moco-vel-val"' in content
        assert 'id="moco-vel-bar"' in content
        assert 'id="wp-btn-1"' in content
        assert 'id="wp-btn-2"' in content
        assert 'id="wp-btn-3"' in content
        assert 'id="moco-trajectory-svg"' in content
        assert 'id="moco-rig-indicator"' in content

        # 4. Studio Gaffer & Lighting HUD (PM-FEAT-010)
        assert 'id="animatic-gaffer-hud"' in content
        assert 'STUDIO GAFFER &amp; LIGHTING HUD' in content
        assert 'id="slider-key-light"' in content
        assert 'id="slider-fill-light"' in content
        assert 'id="slider-rim-light"' in content
        assert 'id="contrast-ratio-badge"' in content
        assert 'id="slider-kelvin-cct"' in content
        assert 'id="cct-color-swatch"' in content
        assert 'id="slider-haze-density"' in content
        assert 'id="badge-haze-status"' in content
        assert '3200K Tungsten' in content
        assert '5600K Daylight' in content

        # 5. JavaScript Controllers & Hooks
        assert 'function toggleMoCoHUD()' in content
        assert 'function selectMoCoWaypoint(' in content
        assert 'function updateMoCoFromTimeline(' in content
        assert 'function toggleGafferHUD()' in content
        assert 'function updateGafferLighting()' in content
        assert 'function updateKelvinCCT(' in content
        assert 'function setKelvinPreset(' in content
        assert 'function updateHazeDensity(' in content

        # 6. Keyboard events mapped
        assert "e.key === 'o' || e.key === 'O'" in content
        assert "e.key === 'k' || e.key === 'K'" in content
        assert "e.key === 'g' || e.key === 'G'" in content
        assert "e.key === 'u' || e.key === 'U'" in content

    def test_moco_rig_schemas_and_kinematics_math(self):
        from omni_director.schemas import MotionControlRigType, TrajectoryWaypoint6DOF, MocoRigSpec
        from omni_director.tools.moco_kinematics import (
            calculate_trajectory_distance,
            calculate_peak_velocity,
            calculate_mean_acceleration,
            interpolate_waypoints_6dof,
            format_moco_prompt_token,
            synthesize_default_moco_rig,
        )

        # 1. Enum & Schemas
        assert MotionControlRigType.BOLT_CINEBOT.value == "bolt_cinebot"
        assert MotionControlRigType.TECHNOCRANE.value == "technocrane"
        assert MotionControlRigType.CABLECAM.value == "cablecam"
        assert MotionControlRigType.STEADICAM.value == "steadicam"
        assert MotionControlRigType.DRONE_FPV.value == "drone_fpv"
        assert MotionControlRigType.RUSSIAN_ARM.value == "russian_arm"
        assert MotionControlRigType.MOTORIZED_DOLLY.value == "motorized_dolly"

        wp1 = TrajectoryWaypoint6DOF(timecode_sec=0.0, x_meters=0.0, y_meters=0.0, z_meters=1.0, roll_deg=0.0, pitch_deg=0.0, yaw_deg=0.0, velocity_mps=0.0)
        wp2 = TrajectoryWaypoint6DOF(timecode_sec=2.0, x_meters=3.0, y_meters=4.0, z_meters=1.0, roll_deg=5.0, pitch_deg=-10.0, yaw_deg=30.0, velocity_mps=2.5)
        wp3 = TrajectoryWaypoint6DOF(timecode_sec=4.0, x_meters=6.0, y_meters=8.0, z_meters=1.0, roll_deg=0.0, pitch_deg=0.0, yaw_deg=0.0, velocity_mps=0.0)

        rig = MocoRigSpec(
            rig_type=MotionControlRigType.BOLT_CINEBOT,
            payload_kg=18.5,
            track_length_meters=10.0,
            max_velocity_mps=5.0,
            waypoints=[wp1, wp2, wp3],
        )
        assert rig.payload_kg == 18.5
        assert len(rig.waypoints) == 3

        # 2. Kinematics Math
        dist = calculate_trajectory_distance(rig.waypoints)
        assert round(dist, 2) == 10.0

        peak_v = calculate_peak_velocity(rig.waypoints)
        assert peak_v == 2.5

        mean_acc = calculate_mean_acceleration(rig.waypoints)
        assert mean_acc > 0.0

        # 3. 6-DOF Waypoint Interpolation at 24Hz
        interpolated = interpolate_waypoints_6dof(rig.waypoints, sample_rate_hz=24.0)
        assert len(interpolated) >= 90
        assert interpolated[0].timecode_sec == 0.0
        assert round(interpolated[-1].timecode_sec, 2) == 4.0

        # 4. Prompt Token
        token = format_moco_prompt_token(rig)
        assert "bolt_cinebot" in token
        assert "10.0m" in token
        assert "5.0m/s" in token

        # 5. Default Rig Synthesis
        default_rig = synthesize_default_moco_rig()
        assert default_rig.rig_type == MotionControlRigType.BOLT_CINEBOT
        assert len(default_rig.waypoints) >= 3

    def test_lighting_rig_schemas_and_photometric_calculations(self):
        from omni_director.schemas import (
            LightingFixtureRole,
            DiffusionGrade,
            ParticulateHazeType,
            StudioLightFixtureSpec,
            AtmosphericHazeSpec,
            LightingRigSpec,
        )
        from omni_director.tools.lighting_rig import (
            calculate_key_to_fill_ratio,
            calculate_key_to_rim_ratio,
            calculate_total_lux,
            calculate_cct_deltas,
            calculate_lighting_photometrics,
            format_lighting_prompt_token,
            synthesize_default_lighting_rig,
        )

        # 1. Enums
        assert LightingFixtureRole.KEY_LIGHT.value == "key_light"
        assert DiffusionGrade.HALF_GRID.value == "half_grid"
        assert ParticulateHazeType.MINERAL_HAZE.value == "mineral_haze"

        # 2. Spec synthesis and photometrics
        rig = synthesize_default_lighting_rig()
        assert isinstance(rig, LightingRigSpec)
        assert len(rig.fixtures) >= 3

        k2f = calculate_key_to_fill_ratio(rig)
        assert k2f == 4.0

        k2r = calculate_key_to_rim_ratio(rig)
        assert k2r == 2.0

        total_lux = calculate_total_lux(rig)
        assert total_lux > 5000.0

        cct_deltas = calculate_cct_deltas(rig)
        assert "KEY_01" in cct_deltas
        assert cct_deltas["KEY_01"] == 0

        metrics = calculate_lighting_photometrics(rig)
        assert metrics["key_to_fill_ratio"] == 4.0
        assert metrics["fixture_count"] == len(rig.fixtures)

        token = format_lighting_prompt_token(rig)
        assert "4.0:1" in token
        assert "lux" in token.lower()

    def test_moco_track_exports_json_csv_fbx(self, tmp_path):
        import json
        from pathlib import Path
        from omni_director.presets import IKEA_ASMR_BIBLE
        from omni_director.tools.moco_kinematics import (
            export_moco_track_json,
            export_moco_track_csv,
            export_moco_fbx_ascii,
            export_moco_bundle,
        )

        # JSON
        json_out = export_moco_track_json(IKEA_ASMR_BIBLE, tmp_path / "moco.json")
        assert (tmp_path / "moco.json").is_file()
        data = json.loads(json_out)
        assert "motion_control_rig" in data
        assert "waypoints" in data["motion_control_rig"]

        # CSV
        csv_out = export_moco_track_csv(IKEA_ASMR_BIBLE, tmp_path / "moco.csv")
        assert (tmp_path / "moco.csv").is_file()
        assert "x_meters" in csv_out
        assert "roll_deg" in csv_out

        # FBX ASCII
        fbx_out = export_moco_fbx_ascii(IKEA_ASMR_BIBLE, tmp_path / "moco.fbx")
        assert (tmp_path / "moco.fbx").is_file()
        assert "Model: \"Camera::MocoCamera\"" in fbx_out

        # Bundle
        bundle_out = export_moco_bundle(IKEA_ASMR_BIBLE, tmp_path / "moco_bundle")
        assert "json" in bundle_out
        assert "csv" in bundle_out
        assert "fbx" in bundle_out
        assert Path(bundle_out["json"]).is_file()
        assert Path(bundle_out["csv"]).is_file()
        assert Path(bundle_out["fbx"]).is_file()

    def test_lighting_plot_exports_json_csv(self, tmp_path):
        import json
        from pathlib import Path
        from omni_director.presets import IKEA_ASMR_BIBLE
        from omni_director.tools.lighting_rig import (
            export_lighting_plot_json,
            export_gaffer_callsheet_csv,
            export_lighting_bundle,
        )

        # JSON
        json_out = export_lighting_plot_json(IKEA_ASMR_BIBLE, tmp_path / "lighting.json")
        assert (tmp_path / "lighting.json").is_file()
        data = json.loads(json_out)
        assert "lighting_rig" in data
        assert "fixtures" in data["lighting_rig"]

        # CSV
        csv_out = export_gaffer_callsheet_csv(IKEA_ASMR_BIBLE, tmp_path / "gaffer.csv")
        assert (tmp_path / "gaffer.csv").is_file()
        assert "fixture_id" in csv_out
        assert "cct_kelvin" in csv_out

        # Bundle
        bundle_out = export_lighting_bundle(IKEA_ASMR_BIBLE, tmp_path / "lighting_bundle")
        assert "json" in bundle_out
        assert "callsheet_csv" in bundle_out
        assert Path(bundle_out["json"]).is_file()
        assert Path(bundle_out["callsheet_csv"]).is_file()

    def test_cli_export_moco_and_lighting(self, tmp_path):
        from omni_director.cli import main

        # Export moco format
        target_moco = tmp_path / "moco_export"
        ret_moco = main(["export", "--preset", "ikea-asmr", "--format", "moco", "-o", str(target_moco)])
        assert ret_moco == 0
        assert (target_moco / "moco_camera_track.json").is_file()
        assert (target_moco / "moco_waypoints.csv").is_file()
        assert (target_moco / "moco_trajectory.fbx").is_file()

        # Export lighting format
        target_light = tmp_path / "lighting_export"
        ret_light = main(["export", "--preset", "ikea-asmr", "--format", "lighting", "-o", str(target_light)])
        assert ret_light == 0
        assert (target_light / "studio_lighting_plot.json").is_file()
        assert (target_light / "gaffer_call_sheet.csv").is_file()

        # Export all format includes moco and lighting
        target_all = tmp_path / "all_export_v25"
        ret_all = main(["export", "--preset", "ikea-asmr", "--format", "all", "-o", str(target_all)])
        assert ret_all == 0
        assert (target_all / "moco_camera_track.json").is_file()
        assert (target_all / "studio_lighting_plot.json").is_file()

    def test_senior_pm_proposals_include_v25_features(self):
        from omni_director.agents.council import ProductManagerAgent
        from omni_director.presets import IKEA_ASMR_BIBLE

        pm = ProductManagerAgent()
        proposals = pm.inspect_product(bible=IKEA_ASMR_BIBLE)
        p_ids = [p.feature_id for p in proposals]
        assert "PM-FEAT-009" in p_ids
        assert "PM-FEAT-010" in p_ids

        p9 = next(p for p in proposals if p.feature_id == "PM-FEAT-009")
        assert p9.priority == "P0"
        assert p9.status == "implemented"
        assert "Motion Control" in p9.title

        p10 = next(p for p in proposals if p.feature_id == "PM-FEAT-010")
        assert p10.priority == "P0"
        assert p10.status == "implemented"
        assert "Lighting Rig" in p10.title

    def test_domain_moco_and_lighting_presets(self):
        from omni_director.presets import (
            get_domain_moco_rig,
            get_domain_lighting_rig,
            DOMAINS_6,
        )
        from omni_director.schemas import MocoRigSpec, LightingRigSpec

        for domain in DOMAINS_6:
            moco = get_domain_moco_rig(domain)
            assert isinstance(moco, MocoRigSpec)
            assert len(moco.waypoints) > 0
            assert moco.track_length_meters > 0

            light = get_domain_lighting_rig(domain)
            assert isinstance(light, LightingRigSpec)
            assert len(light.fixtures) > 0
            assert light.key_to_fill_ratio > 0

    def test_prompt_auditor_moco_and_lighting_compliance(self):
        from omni_director.tools.prompt_auditor import audit_omni_scene_prompt, heal_omni_scene_prompt
        from omni_director.presets import IKEA_ASMR_BIBLE

        scene = IKEA_ASMR_BIBLE.scenes[0]
        res = audit_omni_scene_prompt(scene)
        assert res.score >= 90.0

        # Test prompt healing injects MoCo and lighting tokens when missing
        test_scene = scene.model_copy(deep=True)
        test_scene.omni_prose_prompt = "A simple camera shot of flat pack box on wood floor."
        healed_scene, healed_res = heal_omni_scene_prompt(test_scene)
        assert "motion control" in healed_scene.omni_prose_prompt.lower() or "moco" in healed_scene.omni_prose_prompt.lower()
        assert "lighting" in healed_scene.omni_prose_prompt.lower() or "contrast" in healed_scene.omni_prose_prompt.lower()
        assert healed_res.score >= 90.0

    def test_product_council_v25_audit_pass(self, tmp_path):
        from omni_director.agents.council import ProductCouncilOrchestrator
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
        compile_storyboard_html(bundle, tmp_path)

        council = ProductCouncilOrchestrator()
        report = council.convene_council(bible=IKEA_ASMR_BIBLE, bundle=bundle, output_dir=tmp_path)

        assert report.passed is True
        assert report.critical_findings_count == 0
        assert report.overall_score >= 90.0
        assert report.persona_reviews["council-agent-engineer"].score >= 24.0
        assert report.persona_reviews["council-strategist"].score == 25.0
        assert report.persona_reviews["council-ux-designer"].score == 25.0


class TestV25MotionControlAndStudioLightingSchemasAndPresets:
    """Verifies PM-FEAT-009 (MoCo Rig & Kinematics) and PM-FEAT-010 (Studio Lighting Rig) schemas, presets, tools, and council audits."""

    def test_moco_schema_contracts_and_validation(self):
        from omni_director.schemas import (
            MotionControlRigType,
            TrajectoryWaypoint6DOF,
            MocoRigSpec,
        )

        # Test Rig Types enum
        assert MotionControlRigType.BOLT_CINEBOT.value == "bolt_cinebot"
        assert MotionControlRigType.RUSSIAN_ARM.value == "russian_arm"
        assert MotionControlRigType.CABLECAM.value == "cablecam"
        assert MotionControlRigType.STEADICAM.value == "steadicam"
        assert MotionControlRigType.TECHNOCRANE.value == "technocrane"
        assert MotionControlRigType.DRONE_FPV.value == "drone_fpv"
        assert MotionControlRigType.MOTORIZED_DOLLY.value == "motorized_dolly"

        # Test TrajectoryWaypoint6DOF
        wp = TrajectoryWaypoint6DOF(
            timecode_sec=1.5,
            x_meters=1.2,
            y_meters=-0.8,
            z_meters=1.5,
            roll_deg=-2.0,
            pitch_deg=5.0,
            yaw_deg=45.0,
            velocity_mps=3.2,
        )
        assert wp.timecode_sec == 1.5
        assert wp.x_meters == 1.2
        assert wp.yaw_deg == 45.0

        # Test MocoRigSpec
        rig = MocoRigSpec(
            rig_type=MotionControlRigType.BOLT_CINEBOT,
            payload_kg=15.0,
            track_length_meters=6.0,
            max_velocity_mps=4.5,
            waypoints=[wp],
            locked_roll_stabilization=True,
            mechanical_backlash_mm=0.05,
        )
        assert rig.rig_type == MotionControlRigType.BOLT_CINEBOT
        assert len(rig.waypoints) == 1
        assert rig.mechanical_backlash_mm == 0.05

        # String rig_type alias parsing
        rig2 = MocoRigSpec(
            rig_type="russian_arm",
            waypoints=[wp],
        )
        assert rig2.rig_type == MotionControlRigType.RUSSIAN_ARM

    def test_lighting_schema_contracts_and_validation(self):
        from omni_director.schemas import (
            LightingFixtureRole,
            DiffusionGrade,
            ParticulateHazeType,
            StudioLightFixtureSpec,
            AtmosphericHazeSpec,
            LightingRigSpec,
        )

        # Test Enums
        assert LightingFixtureRole.KEY_LIGHT.value == "key_light"
        assert LightingFixtureRole.FILL_LIGHT.value == "fill_light"
        assert LightingFixtureRole.RIM_BACKLIGHT.value == "rim_backlight"
        assert DiffusionGrade.HALF_GRID.value == "half_grid"
        assert ParticulateHazeType.MINERAL_HAZE.value == "mineral_haze"

        # Test Fixture Spec
        fix = StudioLightFixtureSpec(
            fixture_id="KEY_01",
            role=LightingFixtureRole.KEY_LIGHT,
            fixture_type="ARRI SkyPanel S360-C",
            cct_kelvin=5600,
            lux_intensity=3500.0,
            beam_angle_deg=45.0,
            diffusion_grade=DiffusionGrade.HALF_GRID,
            distance_meters=3.5,
            dmx_channel=1,
        )
        assert fix.fixture_id == "KEY_01"
        assert fix.cct_kelvin == 5600
        assert fix.lux_intensity == 3500.0

        # Test Atmospheric Haze Spec
        haze = AtmosphericHazeSpec(
            haze_type=ParticulateHazeType.MINERAL_HAZE,
            particulate_density=0.15,
            scattering_coefficient=0.45,
            shaft_visibility=0.6,
        )
        assert haze.particulate_density == 0.15

        # Test Lighting Rig Spec
        rig = LightingRigSpec(
            fixtures=[fix],
            key_to_fill_ratio=4.0,
            key_to_rim_ratio=2.0,
            total_lux=3500.0,
            atmospheric_haze=haze,
        )
        assert len(rig.fixtures) == 1
        assert rig.key_to_fill_ratio == 4.0

    def test_domain_archetypes_moco_and_lighting_rig_calibration(self):
        from omni_director.presets import (
            DOMAIN_ARCHETYPES,
            get_domain_moco_rig,
            get_domain_lighting_rig,
        )

        for domain in DOMAIN_ARCHETYPES.keys():
            moco = get_domain_moco_rig(domain)
            assert moco is not None
            assert len(moco.waypoints) >= 2
            assert moco.track_length_meters > 0.0
            assert moco.max_velocity_mps > 0.0

            lighting = get_domain_lighting_rig(domain)
            assert lighting is not None
            assert len(lighting.fixtures) >= 1
            assert lighting.total_lux > 0.0
            assert lighting.key_to_fill_ratio > 0.0

    def test_prompt_auditor_moco_and_lighting_compliance_and_healing(self):
        from omni_director.presets import get_domain_moco_rig, get_domain_lighting_rig
        from omni_director.schemas import RegimeType, ScenePromptSpec
        from omni_director.tools.prompt_auditor import (
            audit_omni_scene_prompt,
            heal_omni_scene_prompt,
        )

        raw_prompt = (
            "A high-speed vehicle powers through wet asphalt with kinetic momentum. "
            "Robotic MoCo camera move on russian_arm with 6-DOF precision waypoints. "
            "Calibrated studio lighting with Key:Fill 4.0:1 contrast ratio, 5600K CCT daylight balance, and subtle mineral haze. "
            "Diegetic audio captures roaring twin-turbo engine exhaust and tires splashing through wet gravel."
        )
        audit = audit_omni_scene_prompt(raw_prompt)
        assert audit.details.get("moco_rig_compliant") is True
        assert audit.details.get("lighting_rig_compliant") is True
        assert audit.score >= 90.0

        # Test self-healing injection
        base_prompt = "A sleek robotic arm assembles a titanium core in a dark room."
        scene = ScenePromptSpec(
            scene_index=1,
            scene_title="Assembly",
            timestamp_range="00:00 - 00:05",
            regime=RegimeType.REGIME_2_KINETIC,
            action_beats=["Precision robot arm moves rapidly"],
            omni_prose_prompt=base_prompt,
            moco_rig=get_domain_moco_rig("automotive_robotics"),
            lighting_rig=get_domain_lighting_rig("automotive_robotics"),
        )
        healed_prompt = heal_omni_scene_prompt(base_prompt, scene)
        assert "russian_arm" in healed_prompt or "MoCo" in healed_prompt
        assert "Key:Fill" in healed_prompt or "lighting" in healed_prompt

    def test_moco_kinematics_math_and_exports(self, tmp_path):
        from omni_director.presets import IKEA_ASMR_BIBLE, get_domain_moco_rig
        from omni_director.tools.moco_kinematics import (
            calculate_trajectory_distance,
            calculate_peak_velocity,
            calculate_mean_acceleration,
            interpolate_waypoints_6dof,
            format_moco_prompt_token,
            export_moco_bundle,
        )

        moco = get_domain_moco_rig("kinetic_action")
        dist = calculate_trajectory_distance(moco)
        assert dist > 0.0

        peak_v = calculate_peak_velocity(moco)
        assert peak_v > 0.0

        mean_a = calculate_mean_acceleration(moco)
        assert mean_a >= 0.0

        interp = interpolate_waypoints_6dof(moco, sample_rate_hz=24.0)
        assert len(interp) >= len(moco.waypoints)

        token = format_moco_prompt_token(moco)
        assert "cablecam" in token.lower() or "moco" in token.lower()

        bundle_files = export_moco_bundle(IKEA_ASMR_BIBLE, tmp_path)
        assert "moco_json" in bundle_files
        assert "moco_csv" in bundle_files
        assert "moco_fbx" in bundle_files
        assert (tmp_path / "moco_track.json").is_file()
        assert (tmp_path / "moco_track.csv").is_file()
        assert (tmp_path / "moco_camera.fbx").is_file()

    def test_lighting_rig_photometrics_and_exports(self, tmp_path):
        from omni_director.presets import IKEA_ASMR_BIBLE, get_domain_lighting_rig
        from omni_director.tools.lighting_rig import (
            calculate_key_to_fill_ratio,
            calculate_key_to_rim_ratio,
            calculate_total_lux,
            calculate_lighting_photometrics,
            format_lighting_prompt_token,
            export_lighting_bundle,
        )

        rig = get_domain_lighting_rig("culinary_asmr")
        k2f = calculate_key_to_fill_ratio(rig)
        assert k2f > 0.0

        k2r = calculate_key_to_rim_ratio(rig)
        assert k2r > 0.0

        tot_lux = calculate_total_lux(rig)
        assert tot_lux > 0.0

        metrics = calculate_lighting_photometrics(rig)
        assert "key_to_fill_ratio" in metrics
        assert "total_lux" in metrics

        token = format_lighting_prompt_token(rig)
        assert "key:fill" in token.lower() or "lighting" in token.lower()

        bundle_files = export_lighting_bundle(IKEA_ASMR_BIBLE, tmp_path)
        assert "lighting_json" in bundle_files
        assert "gaffer_csv" in bundle_files
        assert (tmp_path / "lighting_plot.json").is_file()
        assert (tmp_path / "gaffer_callsheet.csv").is_file()


class TestV26DofAndLutSuite:
    """Rigorous tests for PM-FEAT-011 (DoF simulator) and PM-FEAT-012 (3D LUT color science)."""

    def test_cli_export_dof_and_lut_formats(self, tmp_path):
        from omni_director.cli import main

        out_dof = tmp_path / "dof_export"
        rc = main(["export", "--preset", "ikea-asmr", "--format", "dof", "-o", str(out_dof), "--json"])
        assert rc == 0
        assert (out_dof / "dof_chart.json").is_file()
        assert (out_dof / "focus_puller_cue_sheet.csv").is_file()

        out_lut = tmp_path / "lut_export"
        rc = main(["export", "--preset", "ikea-asmr", "--format", "lut", "-o", str(out_lut), "--json"])
        assert rc == 0
        assert (out_lut / "production_look.cube").is_file()
        assert (out_lut / "dit_cart_manifest.json").is_file()

    def test_cli_export_granular_dof_and_lut_flags(self, tmp_path):
        from omni_director.cli import main

        out_granular = tmp_path / "granular_export"
        rc = main([
            "export",
            "--preset", "ikea-asmr",
            "--dof-chart",
            "--cue-sheet",
            "--cube-lut",
            "--dit-manifest",
            "-o", str(out_granular),
            "--json",
        ])
        assert rc == 0
        assert (out_granular / "dof_chart.json").is_file()
        assert (out_granular / "focus_puller_cue_sheet.csv").is_file()
        assert (out_granular / "production_look.cube").is_file()
        assert (out_granular / "dit_cart_manifest.json").is_file()

    def test_telemetry_checksums_tracks_dof_and_lut_artifacts(self, tmp_path):
        from omni_director.cli import main
        from omni_director.telemetry import RuntimeTelemetry

        out_all = tmp_path / "all_export"
        rc = main(["export", "--preset", "ikea-asmr", "--format", "all", "-o", str(out_all), "--json"])
        assert rc == 0

        telemetry = RuntimeTelemetry()
        checksums = telemetry.compute_artifact_checksums(str(out_all))

        expected_artifacts = [
            "dof_chart.json",
            "focus_puller_cue_sheet.csv",
            "production_look.cube",
            "dit_cart_manifest.json",
        ]
        for artifact in expected_artifacts:
            assert artifact in checksums, f"Artifact {artifact} not found in checksum manifest: {list(checksums.keys())}"
            assert len(checksums[artifact]) == 64, f"Invalid SHA-256 for {artifact}"

    def test_fde_council_review_scores_25_on_v26_artifacts(self, tmp_path):
        from omni_director.agents.council import ProductCouncilOrchestrator
        from omni_director.cli import main
        from omni_director.presets import IKEA_ASMR_BIBLE

        out_dir = tmp_path / "bundle"
        rc = main(["export", "--preset", "ikea-asmr", "--format", "all", "-o", str(out_dir), "--json"])
        assert rc == 0

        council = ProductCouncilOrchestrator()
        review = council._review_fde(bible=IKEA_ASMR_BIBLE, bundle=None, output_dir=out_dir)
        criticals = [f for f in review.findings if f.severity == "critical"]

        assert review.score == 25.0
        assert len(criticals) == 0
        assert any("DoF" in f.message for f in review.findings)
        assert any("LUT" in f.message for f in review.findings)


class TestV26DomainDofAndLutSpecs:
    """Verifies PM-FEAT-011 (Domain Depth of Field) and PM-FEAT-012 (Domain 3D LUT Suite)."""

    def test_domain_dof_specs_all_six_archetypes(self):
        from omni_director.presets import get_domain_dof_spec
        from omni_director.schemas import DomainDofSpec

        # 1. culinary_asmr: Macro shallow focus (T1.4, 100mm, nonagonal iris, razor-thin DoF)
        culinary_dof = get_domain_dof_spec("culinary_asmr")
        assert isinstance(culinary_dof, DomainDofSpec)
        assert culinary_dof.focus_style == "Macro shallow focus"
        assert culinary_dof.aperture_t_stop == 1.4
        assert culinary_dof.focal_length_mm == 100
        assert "nonagonal" in culinary_dof.iris_geometry.lower()
        assert "razor-thin" in culinary_dof.depth_character.lower() or "shallow" in culinary_dof.depth_character.lower()

        # 2. luxury_fashion: Anamorphic shallow portraiture (T1.8, 85mm, 2x oval bokeh, rack-focus)
        fashion_dof = get_domain_dof_spec("luxury_fashion")
        assert isinstance(fashion_dof, DomainDofSpec)
        assert fashion_dof.focus_style == "Anamorphic shallow portraiture"
        assert fashion_dof.aperture_t_stop == 1.8
        assert fashion_dof.focal_length_mm == 85
        assert "oval" in fashion_dof.iris_geometry.lower()

        # 3. automotive_robotics: Dynamic deep focus (T5.6, 24mm, circular iris, hyperfocal tracking)
        auto_dof = get_domain_dof_spec("automotive_robotics")
        assert isinstance(auto_dof, DomainDofSpec)
        assert auto_dof.focus_style == "Dynamic deep focus"
        assert auto_dof.aperture_t_stop == 5.6
        assert auto_dof.focal_length_mm == 24
        assert "circular" in auto_dof.iris_geometry.lower()

        # 4. kinetic_action: Wide action depth (T4.0, 35mm, octagonal iris, fast focus pull)
        action_dof = get_domain_dof_spec("kinetic_action")
        assert isinstance(action_dof, DomainDofSpec)
        assert action_dof.focus_style == "Wide action depth"
        assert action_dof.aperture_t_stop == 4.0
        assert action_dof.focal_length_mm == 35
        assert "octagonal" in action_dof.iris_geometry.lower()

        # 5. tech_hardware: Cleanroom macro isolation (T2.0, 90mm, nonagonal iris, tight CoC)
        tech_dof = get_domain_dof_spec("tech_hardware")
        assert isinstance(tech_dof, DomainDofSpec)
        assert tech_dof.focus_style == "Cleanroom macro isolation"
        assert tech_dof.aperture_t_stop == 2.0
        assert tech_dof.focal_length_mm == 90
        assert "nonagonal" in tech_dof.iris_geometry.lower()

        # 6. architectural_sanctuary: Panoramic deep focus (T8.0, 18mm, circular iris, infinite far limit)
        arch_dof = get_domain_dof_spec("architectural_sanctuary")
        assert isinstance(arch_dof, DomainDofSpec)
        assert arch_dof.focus_style == "Panoramic deep focus"
        assert arch_dof.aperture_t_stop == 8.0
        assert arch_dof.focal_length_mm == 18
        assert "circular" in arch_dof.iris_geometry.lower()

    def test_domain_lut_specs_all_six_archetypes(self):
        from omni_director.presets import get_domain_lut_spec
        from omni_director.schemas import DomainLutSpec

        # 1. culinary_asmr: Warm Kodak 5219 Vision3 emulation 33x33 .cube
        culinary_lut = get_domain_lut_spec("culinary_asmr")
        assert isinstance(culinary_lut, DomainLutSpec)
        assert "kodak" in culinary_lut.film_emulation.lower() or "5219" in culinary_lut.film_emulation.lower()
        assert culinary_lut.grid_size == 33
        assert culinary_lut.cube_filename.endswith(".cube")

        # 2. luxury_fashion: Bleach Bypass Silver high-contrast 33x33 .cube
        fashion_lut = get_domain_lut_spec("luxury_fashion")
        assert isinstance(fashion_lut, DomainLutSpec)
        assert "bleach" in fashion_lut.film_emulation.lower()
        assert fashion_lut.grid_size == 33
        assert fashion_lut.cube_filename.endswith(".cube")

        # 3. automotive_robotics: Teal & Orange high-velocity metallic 33x33 .cube
        auto_lut = get_domain_lut_spec("automotive_robotics")
        assert isinstance(auto_lut, DomainLutSpec)
        assert "teal" in auto_lut.lut_name.lower() or "orange" in auto_lut.lut_name.lower()
        assert auto_lut.grid_size == 33
        assert auto_lut.cube_filename.endswith(".cube")

        # 4. kinetic_action: High-contrast Fuji Eterna dynamic 33x33 .cube
        action_lut = get_domain_lut_spec("kinetic_action")
        assert isinstance(action_lut, DomainLutSpec)
        assert "eterna" in action_lut.film_emulation.lower() or "fuji" in action_lut.film_emulation.lower()
        assert action_lut.grid_size == 33
        assert action_lut.cube_filename.endswith(".cube")

        # 5. tech_hardware: Neutral surgical Rec.709 cold precision 33x33 .cube
        tech_lut = get_domain_lut_spec("tech_hardware")
        assert isinstance(tech_lut, DomainLutSpec)
        assert "surgical" in tech_lut.film_emulation.lower() or "rec.709" in tech_lut.lut_name.lower() or "cold" in tech_lut.film_emulation.lower()
        assert tech_lut.grid_size == 33
        assert tech_lut.cube_filename.endswith(".cube")

        # 6. architectural_sanctuary: Verdant warm daylight organic 33x33 .cube
        arch_lut = get_domain_lut_spec("architectural_sanctuary")
        assert isinstance(arch_lut, DomainLutSpec)
        assert "daylight" in arch_lut.film_emulation.lower() or "organic" in arch_lut.film_emulation.lower() or "verdant" in arch_lut.film_emulation.lower()
        assert arch_lut.grid_size == 33
        assert arch_lut.cube_filename.endswith(".cube")

    def test_pm_features_registered_in_council(self):
        from omni_director.agents.council import ProductManagerAgent

        pm = ProductManagerAgent()
        proposals = pm.inspect_product()
        feat_ids = {p.feature_id: p for p in proposals}

        assert "PM-FEAT-011" in feat_ids
        p11 = feat_ids["PM-FEAT-011"]
        assert p11.status == "implemented"
        assert p11.priority == "P0"
        assert "depth of field" in p11.title.lower()

        assert "PM-FEAT-012" in feat_ids
        p12 = feat_ids["PM-FEAT-012"]
        assert p12.status == "implemented"
        assert p12.priority == "P0"
        assert "3d lut" in p12.title.lower()

    def test_strategist_review_evaluates_domain_dof_and_lut(self):
        from omni_director.agents.council import ProductCouncilOrchestrator
        from omni_director.presets import IKEA_ASMR_BIBLE

        orchestrator = ProductCouncilOrchestrator()
        result = orchestrator._review_strategist(IKEA_ASMR_BIBLE)

        assert result.score == 25.0
        categories = {f.category for f in result.findings}
        assert "domain_dof_calibration" in categories
        assert "domain_lut_calibration" in categories

    def test_roundtrip_serialization_with_domain_specs(self):
        from omni_director.presets import IKEA_ASMR_BIBLE
        from omni_director.schemas import MasterProductionBible

        raw_dict = IKEA_ASMR_BIBLE.model_dump()
        restored = MasterProductionBible.model_validate(raw_dict)
        assert restored.project_title == IKEA_ASMR_BIBLE.project_title
        assert restored.master_dof_spec is not None
        assert restored.master_lut_spec is not None
        assert restored.master_dof_spec.focus_style == "Panoramic deep focus"
        assert restored.master_lut_spec.grid_size == 33


class TestV26UXAnimaticDofAndLutHUDs:
    """Verifies UX/UI Storyboard Designer deliverables for PM-FEAT-011 and PM-FEAT-012."""

    def test_storyboard_animatic_dof_and_lut_hud_elements(self, tmp_path):
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
        html_path = compile_storyboard_html(bundle, tmp_path)
        assert html_path.is_file()
        content = html_path.read_text(encoding="utf-8")

        # 1. Transport Bar Control Buttons & Shortcuts
        assert 'id="btn-dof-animatic"' in content
        assert 'Optical DoF HUD [F]' in content
        assert 'id="btn-dit-lut-animatic"' in content
        assert 'DIT 3D LUT Suite [L]' in content

        # 2. Header Cheat Sheet includes hotkeys
        assert '[F] DoF' in content
        assert '[L] 3D LUT' in content

        # 3. Optical Depth-of-Field HUD (PM-FEAT-011)
        assert 'id="animatic-dof-hud"' in content
        assert 'role="dialog"' in content
        assert 'aria-modal="true"' in content
        assert 'OPTICAL DEPTH OF FIELD (DOF) &amp; APERTURE HUD' in content
        assert 'id="dof-raytrace-svg"' in content
        assert 'id="slider-focal-length"' in content
        assert 'id="slider-t-stop"' in content
        assert 'id="slider-subject-distance"' in content
        assert 'id="slider-rack-focus"' in content
        assert 'id="bokeh-geometry-badge"' in content
        assert 'id="dof-cue-sheet-table"' in content
        assert 'id="dof-cue-sheet-body"' in content
        assert 'id="val-near-limit"' in content
        assert 'id="val-far-limit"' in content
        assert 'id="val-total-dof"' in content
        assert 'id="val-focus-plane"' in content
        assert 'id="val-hyperfocal"' in content

        # 4. DIT 3D LUT Color Science Suite HUD (PM-FEAT-012)
        assert 'id="animatic-dit-lut-hud"' in content
        assert 'DIT 3D LUT COLOR GRADING SUITE' in content
        assert 'id="lut-split-wipe"' in content
        assert 'id="lut-plate-raw"' in content
        assert 'id="lut-plate-graded"' in content
        assert 'id="lut-split-slider"' in content
        assert 'id="lut-divider-line"' in content
        assert 'id="btn-download-master-cube"' in content
        assert 'id="btn-download-scene-cube"' in content
        assert 'id="lut-metadata-badge"' in content
        assert 'id="color-continuity-status"' in content

        # 5. JavaScript Logic, Hotkeys & Toast System
        assert "function toggleDoFHUD()" in content
        assert "function toggleDitLutHUD()" in content
        assert "function calculateDoFLimits(" in content
        assert "function updateRackFocus(" in content
        assert "function updateLutSplitWipe(" in content
        assert "function generateCubeLUT(" in content
        assert "function downloadMasterCubeLUT()" in content
        assert "function downloadSceneCubeLUT()" in content
        assert "e.key === 'f' || e.key === 'F'" in content
        assert "e.key === 'l' || e.key === 'L'" in content
        assert "showToast(" in content

    def test_council_ux_designer_scores_25_with_dof_and_lut_huds(self, tmp_path):
        from omni_director.agents.council import ProductCouncilOrchestrator
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
        html_path = compile_storyboard_html(bundle, tmp_path)
        bundle.storyboard_html_path = str(html_path)

        council = ProductCouncilOrchestrator()
        ux_review = council._review_ux_designer(bible=IKEA_ASMR_BIBLE, bundle=bundle, output_dir=tmp_path)

        criticals = [f for f in ux_review.findings if f.severity.value == "critical"]
        assert len(criticals) == 0
        assert ux_review.score == 25.0

        findings_msgs = [f.message for f in ux_review.findings]
        assert any("Optical Depth-of-Field (DoF) interactive HUD verified" in msg for msg in findings_msgs)
        assert any("DIT 3D LUT Color Science & Film Emulation Suite HUD verified" in msg for msg in findings_msgs)

    def test_council_ux_designer_flags_missing_dof_and_lut_huds(self, tmp_path):
        from omni_director.agents.council import ProductCouncilOrchestrator
        from omni_director.presets import IKEA_ASMR_BIBLE
        from omni_director.schemas import ProductionBundle, CouncilFindingSeverity

        # Create minimal HTML missing the new DoF and LUT HUD controls
        fake_html = tmp_path / "storyboard_preview.html"
        fake_html.write_text(
            '<html><body>'
            '<button id="btn-play-animatic"></button>'
            '<div id="smpte-timecode"></div>'
            '<button id="btn-loop-animatic"></button>'
            '<button id="btn-viewfinder-animatic"></button>'
            '<div id="animatic-viewfinder-overlay"></div>'
            '<button id="btn-vp-stage-animatic"></button>'
            '<div id="animatic-vp-stage-modal"></div>'
            '<button id="btn-moco-animatic"></button>'
            '<div id="animatic-moco-hud"></div>'
            '<button id="btn-gaffer-animatic"></button>'
            '<div id="animatic-gaffer-hud"></div>'
            '<button id="btn-spatial-animatic"></button>'
            '<div id="animatic-spatial-hud"></div>'
            '<button id="btn-vfx-animatic"></button>'
            '<div id="animatic-vfx-hud"></div>'
            '<div role="tablist"></div>'
            '<div class="cinema-toast" id="cinema-toast"></div>'
            '<script>function jumpToBeat() {}</script>'
            '</body></html>',
            encoding="utf-8"
        )
        bundle = ProductionBundle(
            bible=IKEA_ASMR_BIBLE,
            storyboard_html_path=str(fake_html),
            bundle_json_path="",
            visual_plates={},
            audit_reports=[],
        )

        council = ProductCouncilOrchestrator()
        ux_review = council._review_ux_designer(bible=IKEA_ASMR_BIBLE, bundle=bundle, output_dir=tmp_path)

        dof_findings = [f for f in ux_review.findings if f.category == "animatic_dof_hud" and "lacks interactive" in f.message]
        lut_findings = [f for f in ux_review.findings if f.category == "animatic_dit_lut_hud" and "lacks interactive" in f.message]

        assert len(dof_findings) == 1
        assert dof_findings[0].severity in (CouncilFindingSeverity.LOW, CouncilFindingSeverity.INFO, CouncilFindingSeverity.WARNING)
        assert len(lut_findings) == 1
        assert lut_findings[0].severity in (CouncilFindingSeverity.LOW, CouncilFindingSeverity.INFO, CouncilFindingSeverity.WARNING)
        assert ux_review.score == 23.0  # 25.0 - 1.0 (dof) - 1.0 (lut)

    def test_depth_of_field_schema_and_physics_simulation(self, tmp_path):
        import json
        from omni_director.schemas import (
            ApertureIrisGeometry,
            DepthOfFieldSpec,
            OpticalAberrationProfile,
            RackFocusTransitionCurve,
            SensorFormat,
        )
        from omni_director.tools.dof_simulator import (
            calculate_dof_limits,
            calculate_hyperfocal_distance,
            export_dof_bundle,
            export_focus_puller_cue_sheet,
            export_optical_chart_json,
            format_dof_prompt_token,
            interpolate_rack_focus,
            resolve_circle_of_confusion,
            synthesize_default_dof_spec,
        )
        from omni_director.presets import IKEA_ASMR_BIBLE

        # Circle of Confusion
        assert resolve_circle_of_confusion(SensorFormat.FULL_FRAME) == 0.030
        assert resolve_circle_of_confusion(SensorFormat.SUPER_35) == 0.020
        assert resolve_circle_of_confusion(SensorFormat.IMAX_70MM) == 0.045

        # Hyperfocal and DoF limits
        H = calculate_hyperfocal_distance(50, 2.0, 0.030)
        assert H > 20.0 and H < 60.0
        near_l, far_l, total_d, hyper_m = calculate_dof_limits(50, 2.0, subject_distance_m=2.5)
        assert near_l > 0.0
        assert near_l < 2.5
        assert far_l > 2.5
        assert total_d > 0.0

        # Rack focus interpolation
        linear_val = interpolate_rack_focus(1.0, 5.0, 0.5, curve=RackFocusTransitionCurve.LINEAR)
        assert linear_val == 3.0
        cubic_val = interpolate_rack_focus(1.0, 5.0, 0.5, curve=RackFocusTransitionCurve.CUBIC_EASE_IN_OUT)
        assert cubic_val == 3.0

        # DepthOfFieldSpec synthesis
        dof_spec = synthesize_default_dof_spec(
            focal_length_mm=85,
            aperture_f_stop=1.4,
            focus_distance_m=2.0,
            iris_geometry=ApertureIrisGeometry.CIRCULAR_11_BLADE,
            rack_focus_enabled=True,
            rack_focus_start_m=1.2,
            rack_focus_target_m=3.8,
            rack_focus_curve=RackFocusTransitionCurve.CUBIC_EASE_IN_OUT,
        )
        assert dof_spec.focal_length_mm == 85
        assert dof_spec.aperture_f_stop == 1.4
        assert dof_spec.rack_focus_enabled is True
        token = format_dof_prompt_token(dof_spec)
        assert "rack focus from 1.2m to 3.8m" in token
        assert "T1.4" in token
        assert "85mm" in token

        # Static DoF token
        static_dof = synthesize_default_dof_spec(focal_length_mm=35, aperture_f_stop=2.8, focus_distance_m=3.0)
        static_token = format_dof_prompt_token(static_dof)
        assert "shallow focus" in static_token
        assert "3.0m" in static_token

        # Cue sheet CSV and optical chart JSON
        csv_str = export_focus_puller_cue_sheet(IKEA_ASMR_BIBLE)
        assert "scene_index" in csv_str
        assert "near_limit_m" in csv_str

        json_str = export_optical_chart_json(IKEA_ASMR_BIBLE)
        parsed = json.loads(json_str)
        assert "master_dof" in parsed
        assert "scenes" in parsed

        # Bundle export
        bundle_res = export_dof_bundle(IKEA_ASMR_BIBLE, tmp_path / "dof_out")
        assert (tmp_path / "dof_out" / "dof_chart.json").exists()
        assert (tmp_path / "dof_out" / "focus_puller_cue_sheet.csv").exists()

    def test_3d_lut_schema_and_cube_compilation(self, tmp_path):
        import json
        from omni_director.schemas import (
            AscCdlSpec,
            ColorGamutTransform,
            LutGridDimension,
            ThreeDimensionalLutSpec,
        )
        from omni_director.tools.dit_lut import (
            export_dit_bundle,
            export_dit_cart_manifest_json,
            export_master_cube_lut,
            export_scene_cube_lut,
            format_lut_prompt_token,
            generate_3d_cube_lut,
            generate_3d_lut_cube_data,
            synthesize_default_3d_lut,
            verify_color_continuity,
        )
        from omni_director.presets import IKEA_ASMR_BIBLE

        # ThreeDimensionalLutSpec validation
        lut_spec = synthesize_default_3d_lut(
            title="CINEMATIC_GOLDEN_HOUR",
            grid_dimension=LutGridDimension.GRID_17,
            gamut_transform=ColorGamutTransform.ACESCG_TO_REC709,
            cdl=AscCdlSpec(slope=(1.1, 1.0, 0.9), offset=(0.02, 0.0, -0.01), power=(0.95, 1.0, 1.05), saturation=1.15),
        )
        assert lut_spec.grid_dimension.cube_size == 17

        # Adobe .cube compilation
        cube_str = generate_3d_lut_cube_data(lut_spec=lut_spec)
        assert 'TITLE "CINEMATIC_GOLDEN_HOUR"' in cube_str
        assert "LUT_3D_SIZE 17" in cube_str
        assert "DOMAIN_MIN 0.0 0.0 0.0" in cube_str
        assert "DOMAIN_MAX 1.0 1.0 1.0" in cube_str

        # Token formatting
        lut_token = format_lut_prompt_token(lut_spec)
        assert "3D LUT 'CINEMATIC_GOLDEN_HOUR'" in lut_token
        assert "17x17x17" in lut_token
        assert "tetrahedral" in lut_token

        # Continuity audit
        continuity = verify_color_continuity(IKEA_ASMR_BIBLE)
        assert continuity.is_continuous is True
        assert continuity.scenes_evaluated >= 1

        # Manifest JSON
        manifest_json = export_dit_cart_manifest_json(IKEA_ASMR_BIBLE)
        manifest = json.loads(manifest_json)
        assert manifest["lut_title"] == "OMNI_DIRECTOR_MASTER_3DLUT"
        assert "continuity_audit" in manifest

        # Bundle export
        bundle_res = export_dit_bundle(IKEA_ASMR_BIBLE, tmp_path / "dit_out", cube_size=17)
        assert (tmp_path / "dit_out" / "production_look.cube").exists()
        assert (tmp_path / "dit_out" / "dit_cart_manifest.json").exists()

        # Scene cube export
        scene_cube_path = tmp_path / "scene_01.cube"
        export_scene_cube_lut(IKEA_ASMR_BIBLE.scenes[0], scene_cube_path, cube_size=17)
        assert scene_cube_path.exists()

    def test_prompt_auditor_dof_and_lut_compliance_and_healing(self):
        from omni_director.schemas import DepthOfFieldSpec, ThreeDimensionalLutSpec, RegimeType
        from omni_director.tools.dof_simulator import synthesize_default_dof_spec
        from omni_director.tools.dit_lut import synthesize_default_3d_lut
        from omni_director.tools.prompt_auditor import audit_omni_scene_prompt, heal_omni_scene_prompt

        dof = synthesize_default_dof_spec(focal_length_mm=50, aperture_f_stop=1.8, focus_distance_m=2.2)
        lut = synthesize_default_3d_lut(title="NEO_NOIR_3DLUT")

        raw_prompt = "Protagonist enters rainy alley. Steadicam tracking forward at 1.0x real-time speed. Diegetic foley of footsteps in puddles and distant foghorn."

        # Audit with specs attached as kwargs
        audit = audit_omni_scene_prompt(raw_prompt, regime=RegimeType.REGIME_2_KINETIC, dof_spec=dof, lut_spec=lut)
        assert audit.details.get("dof_spec_compliant") is True
        assert audit.details.get("lut_spec_compliant") is True

        # Healing injection
        healed = heal_omni_scene_prompt(raw_prompt, regime=RegimeType.REGIME_2_KINETIC, dof_spec=dof, lut_spec=lut)
        patches = healed.audit.details.get("healing_history", {}).get("applied_patches", [])
        assert "injected_dof_spec" in patches
        assert "injected_lut_spec" in patches
        assert "optical depth of field" in healed.healed_prompt.lower() or "focus" in healed.healed_prompt.lower()
        assert "3d lut" in healed.healed_prompt.lower()
        assert healed.score >= 90.0

    def test_craft_camera_and_color_look_spec_integration(self):
        from omni_director.schemas import (
            ColorLookSpec,
            CraftCameraSpec,
            MasterProductionBible,
            ScenePromptSpec,
        )
        from omni_director.tools.dof_simulator import synthesize_default_dof_spec
        from omni_director.tools.dit_lut import synthesize_default_3d_lut
        from omni_director.presets import IKEA_ASMR_BIBLE

        dof = synthesize_default_dof_spec(focal_length_mm=35, aperture_f_stop=2.0)
        lut = synthesize_default_3d_lut(title="IKEA_WARMTH_LUT")

        cam = CraftCameraSpec(
            rig_type="Tripod locked",
            focal_length_mm=35,
            composition="Rule of thirds center",
            route="Static framing",
            action_anchor="Table top",
            focus_axis="180-degree axis",
            tone_rig="Spherical prime",
            dof_spec=dof,
        )
        assert cam.dof_spec is not None
        assert cam.dof_spec.focal_length_mm == 35

        look = ColorLookSpec(lut_spec=lut)
        assert look.lut_spec is not None
        assert look.lut_spec.lut_title == "IKEA_WARMTH_LUT"

        # Bible alias synchronization test
        bible_dict = IKEA_ASMR_BIBLE.model_dump()
        bible_dict["dof_spec"] = dof.model_dump()
        bible_dict["lut_spec"] = lut.model_dump()
        bible = MasterProductionBible.model_validate(bible_dict)
        assert bible.master_dof_spec is not None
        assert bible.dof_spec is not None
        assert bible.master_lut_spec is not None
        assert bible.lut_spec is not None


class TestV27SpatialAudioAndVfxCompositingSuite:
    """Comprehensive test suite for v2.7.0 Spatial Audio and Multi-Pass VFX Compositing (PM-FEAT-013 & PM-FEAT-014)."""

    def test_spatial_audio_acoustic_formulas(self) -> None:
        """Validates Sabine RT60, Eyring RT60, early reflections, Ambisonics weights, and VBAP gains."""
        from omni_director.tools.spatial_audio import (
            calculate_sabine_rt60,
            calculate_eyring_rt60,
            calculate_early_reflection_delay_ms,
            calculate_ambisonic_b_format,
            calculate_vbap_gains_7_1_4,
            SpatialCoordinate3D,
            AcousticMaterialType,
            get_material_absorption,
        )

        # Sabine RT60 formula test: 0.161 * V / (S * alpha)
        # V = 1000 m3, S = 600 m2, alpha = 0.20 -> A = 120 -> RT60 = 0.161 * 1000 / 120 = 1.3417s
        sabine = calculate_sabine_rt60(1000.0, 600.0, 0.20)
        assert 1.30 <= sabine <= 1.40

        # Eyring RT60 test
        eyring = calculate_eyring_rt60(1000.0, 600.0, 0.20)
        assert eyring > 0.0
        assert eyring < sabine  # Eyring is always slightly shorter than Sabine for non-zero absorption

        # Early reflection delay (ms) for 10m3 room:
        delay_ms = calculate_early_reflection_delay_ms(10.0)
        assert 7.0 <= delay_ms <= 8.0

        # Ambisonic B-format weights
        # At azimuth=0, elevation=0: W=0.7071, X=1.0, Y=0.0, Z=0.0
        b_fmt = calculate_ambisonic_b_format(0.0, 0.0)
        assert b_fmt["W"] == 0.7071
        assert b_fmt["X"] == 1.0
        assert b_fmt["Y"] == 0.0
        assert b_fmt["Z"] == 0.0

        # VBAP 7.1.4 gains: source right in front (azimuth 0, elevation 0)
        coord = SpatialCoordinate3D(azimuth_deg=0.0, elevation_deg=0.0, distance_meters=2.0)
        gains = calculate_vbap_gains_7_1_4(coord)
        assert "C" in gains
        assert gains["C"] > 0.5  # Center channel should dominate for front-center source

        # Material absorption lookups
        assert get_material_absorption(AcousticMaterialType.STUDIO_ACOUSTIC_FOAM) >= 0.70
        assert get_material_absorption(AcousticMaterialType.MARBLE_GLASS) <= 0.05

    def test_spatial_audio_adm_and_exports(self, tmp_path: Path) -> None:
        """Validates Dolby Atmos ADM JSON, Ambisonics CSV, Web Audio JSON, and bundle exports."""
        from omni_director.tools.spatial_audio import (
            export_dolby_atmos_adm_manifest,
            export_ambisonic_panning_table,
            export_webaudio_spatial_config,
            export_spatial_audio_bundle,
            format_spatial_audio_prompt_token,
        )
        from omni_director.presets import get_domain_spatial_audio_spec

        spec = get_domain_spatial_audio_spec("kinetic_action")
        assert spec.bed_format.value == "ambisonic_hoa_3rd_order"
        assert len(spec.audio_objects) >= 2

        # ADM Manifest
        adm = export_dolby_atmos_adm_manifest(spec, project_title="Test Action")
        assert adm["admVersion"] == "ITU-R BS.2076-2"
        assert adm["soundfieldBedFormat"] == "ambisonic_hoa_3rd_order"
        assert len(adm["audioObjects"]) >= 2

        # Ambisonics CSV
        csv_text = export_ambisonic_panning_table(spec)
        assert "object_id,stem_type" in csv_text
        assert "W,X,Y,Z" in csv_text

        # Web Audio Config
        wa_cfg = export_webaudio_spatial_config(spec)
        assert wa_cfg["panningModel"] == "HRTF"

        # Prompt Token
        token = format_spatial_audio_prompt_token(spec)
        assert "[SPATIAL AUDIO:" in token
        assert "Ambisonic" in token

        # Bundle export
        bundle_files = export_spatial_audio_bundle(spec, tmp_path / "spatial_out")
        assert (tmp_path / "spatial_out" / "spatial_audio_adm.json").is_file()
        assert (tmp_path / "spatial_out" / "ambisonic_b_format.csv").is_file()
        assert (tmp_path / "spatial_out" / "webaudio_spatial_panner.json").is_file()

    def test_vfx_compositing_engine(self, tmp_path: Path) -> None:
        """Validates Murmur3 Cryptomatte hashing, OpenEXR channel manifests, and Nuke .nk script generation."""
        from omni_director.tools.vfx_compositor import (
            hash_identifier_32bit,
            generate_cryptomatte_manifest,
            synthesize_openexr_channel_manifest,
            generate_nuke_composite_script,
            format_vfx_compositing_prompt_token,
            export_vfx_bundle,
        )
        from omni_director.presets import get_domain_vfx_manifest

        # Hash algorithm consistency
        h1 = hash_identifier_32bit("hero_vehicle")
        h2 = hash_identifier_32bit("hero_vehicle")
        assert h1 == h2
        assert len(h1) == 10  # 32-bit hex string with 0x prefix
        assert h1.startswith("0x")

        manifest = get_domain_vfx_manifest("kinetic_action")
        assert len(manifest.render_passes) >= 7
        assert manifest.cryptomatte is not None

        # Cryptomatte manifest
        crypto = generate_cryptomatte_manifest(["character_hero", "prop_sword"], ["carbon_fiber", "gold_trim"])
        assert crypto.hash_algorithm == "MurmurHash3_32"
        assert "character_hero" in crypto.object_manifest

        # OpenEXR channels
        exr = synthesize_openexr_channel_manifest(manifest, project_title="VFX Master")
        assert exr["fileFormat"] == "OpenEXR v2.3 Multi-Layer"
        assert exr["colorSpace"] == "ACEScg"
        assert len(exr["channels"]) >= 7

        # Foundry Nuke script
        nk = generate_nuke_composite_script(manifest, project_title="VFX Master")
        assert "Nuke" in nk
        assert "Read_MultiPass_EXR" in nk
        assert "Write_Final_Comp" in nk
        assert "ACEScg" in nk

        # Prompt Token
        token = format_vfx_compositing_prompt_token(manifest)
        assert "[VFX COMPOSITING:" in token
        assert "ACEScg" in token

        # Bundle export
        bundle_files = export_vfx_bundle(manifest, tmp_path / "vfx_out")
        assert (tmp_path / "vfx_out" / "openexr_channels.json").is_file()
        assert (tmp_path / "vfx_out" / "cryptomatte_manifest.json").is_file()
        assert (tmp_path / "vfx_out" / "nuke_composite.nk").is_file()

    def test_domain_presets_spatial_and_vfx(self) -> None:
        """Ensures all 6 commercial domain archetypes are equipped with valid spatial audio and VFX manifests."""
        from omni_director.presets import (
            DOMAIN_ARCHETYPES,
            get_domain_spatial_audio_spec,
            get_domain_vfx_manifest,
            get_preset_bible,
        )

        for archetype in DOMAIN_ARCHETYPES.keys():
            spatial = get_domain_spatial_audio_spec(archetype)
            assert spatial is not None
            assert spatial.bed_format is not None
            assert spatial.acoustic_room is not None
            assert len(spatial.audio_objects) >= 2

            vfx = get_domain_vfx_manifest(archetype)
            assert vfx is not None
            assert len(vfx.render_passes) >= 6
            assert vfx.cryptomatte is not None

            bible = get_preset_bible(archetype)
            assert bible.master_spatial_audio is not None
            assert bible.master_vfx_manifest is not None
            assert bible.scenes[0].spatial_audio is not None
            assert bible.scenes[0].vfx_compositing is not None

    def test_prompt_auditor_spatial_and_vfx_tokens(self) -> None:
        """Verifies PromptAuditor rewards spatial audio and VFX compositing tokens and self-healing convergence."""
        from omni_director.presets import get_preset_bible
        from omni_director.tools.prompt_auditor import audit_omni_scene_prompt, heal_omni_scene_prompt

        bible = get_preset_bible("kinetic_action")
        scene = bible.scenes[0]

        res = audit_omni_scene_prompt(scene, regime=bible.creative_regime, storytelling_mode=bible.storytelling_mode)
        assert res.score >= 90.0
        assert res.details.get("spatial_audio_compliant") is True
        assert res.details.get("vfx_compositing_compliant") is True

    def test_html_compiler_spatial_and_vfx_huds(self, tmp_path: Path) -> None:
        """Verifies compiled HTML5 animatic embeds spatial audio and VFX modal HUDs and keybindings."""
        from omni_director.presets import get_preset_bible
        from omni_director.tools.html_compiler import compile_storyboard_html
        from omni_director.schemas import ProductionBundle

        bible = get_preset_bible("kinetic_action")
        bundle = ProductionBundle(
            bible=bible,
            storyboard_html_path="",
            bundle_json_path="",
            visual_plates={},
            audit_reports=[],
        )
        html_file = compile_storyboard_html(bundle, tmp_path / "cinema_ui")
        assert html_file.is_file()
        content = html_file.read_text(encoding="utf-8")

        # Check DOM elements
        assert 'id="btn-spatial-animatic"' in content
        assert 'id="animatic-spatial-hud"' in content
        assert 'id="btn-vfx-animatic"' in content
        assert 'id="animatic-vfx-hud"' in content

        # Check JavaScript controllers
        assert "function toggleSpatialHUD()" in content
        assert "function downloadSpatialAdmJSON()" in content
        assert "function toggleVfxHUD()" in content
        assert "function downloadExrManifestJSON()" in content
        assert "function downloadNukeScript()" in content

        # Check keybindings
        assert "toggleSpatialHUD()" in content
        assert "toggleVfxHUD()" in content

    def test_product_council_v27_audit(self, tmp_path: Path) -> None:
        """Verifies ProductCouncilOrchestrator audits and passes a v2.7.0 production bundle with >= 90.0 score."""
        from omni_director.presets import get_preset_bible
        from omni_director.tools.html_compiler import compile_storyboard_html
        from omni_director.tools.nle_export import export_all_nle_artifacts
        from omni_director.agents.council import ProductCouncilOrchestrator, ProductManagerAgent
        from omni_director.schemas import ProductionBundle

        # PM inspection test
        pm = ProductManagerAgent()
        recs = pm.inspect_product()
        rec_ids = [r.feature_id for r in recs]
        assert "PM-FEAT-013" in rec_ids
        assert "PM-FEAT-014" in rec_ids

        # Build bundle
        bible = get_preset_bible("kinetic_action")
        bundle_dir = tmp_path / "bundle_v27"
        bundle_dir.mkdir(parents=True, exist_ok=True)

        bundle = ProductionBundle(
            bible=bible,
            storyboard_html_path=str(bundle_dir / "storyboard.html"),
            bundle_json_path=str(bundle_dir / "bundle.json"),
            visual_plates={},
            audit_reports=[],
        )
        compile_storyboard_html(bundle, bundle_dir)
        export_all_nle_artifacts(bible, bundle_dir)

        council = ProductCouncilOrchestrator()
        report = council.convene_council(bible=bible, bundle=bundle, output_dir=bundle_dir)

        assert report.passed is True
        assert report.overall_score >= 90.0
        assert report.critical_findings_count == 0

















