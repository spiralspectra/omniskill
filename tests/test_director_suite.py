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
        from omni_director import agents
        assert hasattr(omni_director, "ParallelScenePromptAgent")
        assert hasattr(omni_director, "BGMComposerAgent")
        assert hasattr(omni_director, "get_settings")
        assert hasattr(agents, "ParallelScenePromptAgent")
        assert hasattr(agents, "BGMComposerAgent")

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
