# Implementation Plan: 001-omni-movie-director

## 1. Executive Summary & Council Synthesis
This implementation plan synthesizes the four domain blueprints:
1. **Creative Director Blueprint**: Establishes the 5-Question Intake Protocol, Master Production Bible (SSOT 2.0), CRAFT camera rigs, Regime 1 vs. Regime 2 prescription, and Dual-Mode storytelling (Mode A Parallel Montage vs. Mode B Continuous 40s Oner).
2. **Storyboard Designer Blueprint**: Establishes the Nano Banana 3-Anchor Pre-Visualization engine (`gemini-3-pro-image`), the "One Job Per Reference" inclusion/exclusion contracts for `<image_1>`, `<image_2>`, `<image_3>`, and the dark-room cinema HTML animatic player UI.
3. **ADK 2.0 Agent Engineer Blueprint**: Establishes the typed Pydantic v2 schemas (`schemas/`), composite multi-agent hierarchy (`SequentialAgent` + `ParallelAgent` Fan-Out/Fan-In), artifact management (`LocalDiskArtifactService`), and Gemini Omni video synthesis tools.
4. **Forward Deployed Engineer Blueprint**: Establishes repo layout for `spiralspectra/omniskill`, PEP 621 `pyproject.toml` with `uv`, Tri-Mode execution ergonomics (`--dry-run`, `--hybrid`, `--render-video`), and verification suites.

## 2. Architectural Architecture & Module Decomposition

```
[Phase 1: Spark Spec Portfolio]
  specs/registry.md -> specs/001-omni-movie-director/{brief.md, spec.md, plan.md, tasks.md}
        │
        ▼
[Phase 2: Core Portable Skills]
  ├── skills/gemini-omni-prompting/SKILL.md (Foundational Omni + Seedance Grammar)
  └── skills/omni-movie-director/SKILL.md (Master Multi-Persona Director Suite)
        │
        ▼
[Phase 3: Reference Documentation & Golden Demos]
  skills/omni-movie-director/references/
  ├── director-intake-and-bible.md (Pydantic Schemas & Intake Interview)
  ├── nano-banana-storyboard-system.md (3-Anchor Prompts, Optics & UI Spec)
  ├── adk-2-architecture.md (ADK 2.0 DAG & Topology)
  └── golden-demos.md (IKEA ASMR 2.0 + SEPHORA London Mode A & Mode B)
        │
        ▼
[Phase 4: ADK 2.0 Python Pipeline Implementation]
  omni_director/ package with typed schemas, agents, tools, compiler, and CLI runner.
        │
        ▼
[Phase 5: Golden Demo Execution & Verification]
  demos/ikea_asmr_2_0/, demos/sephora_london_pulse_2_0/ and automated test suite.
```

## 3. Phased Implementation Roadmap

### Phase 1: Specifications & Portable Skills Foundation (Current Priority)
- Formulate the Spark Spec Portfolio under `specs/`.
- Author `skills/gemini-omni-prompting/SKILL.md` covering the 5 Core Elements, DeepMind capabilities, Seedance Upgrades 4.1-4.6, 10 Master Templates, and 7-Item Verification Checklist.
- Author `skills/omni-movie-director/SKILL.md` (400+ lines) detailing all 6 production stages.
- Populate the 4 authoritative reference guides in `skills/omni-movie-director/references/`.

### Phase 2: Python Packaging & Schemas (`omni_director/`)
- Set up PEP 621 compliant `pyproject.toml` targeting Python `>=3.11` using `uv`.
- Implement `omni_director/schemas/` with strict Pydantic v2 data models:
  * `intake.py`: `UserCreativeBrief`, `BrandGuidelines`, `IntakeDossier`.
  * `production_bible.py`: `CharacterProfile`, `EnvironmentPlate`, `SceneSlice`, `ProductionBible`.
  * `scene.py`: `GeminiOmniScenePrompt`, `BGMScoreDirective`.
  * `bundle.py`: `ProductionBundle`, `PipelineRunSummary`.

### Phase 3: ADK 2.0 Agents & Tools Execution Graph
- Implement ADK 2.0 FunctionTools:
  * `tools/research_tools.py`: Search and web scraping wrappers.
  * `tools/nano_banana_tools.py`: Image generation calling `gemini-3-pro-image`.
  * `tools/omni_video_tools.py`: Video and synchronized audio generation calling `gemini-omni-1.1-flash-preview` via `interactions.create`.
  * `tools/compiler_tools.py`: HTML treatment renderer and JSON bundle packager.
- Implement specialized agents:
  * `IntakeAndResearchAgent`
  * `CreativeDirectorAgent` (`gemini-4-argon`)
  * `VisualBibleGeneratorAgent` & `StoryboardParallelAgent` (`gemini-3-pro-image`)
  * `ScenePromptFanOutAgent` (`gemini-3.8-flash`) + `BGMComposerAgent`
  * `OptionalOmniVideoRenderAgent` (`gemini-omni-1.1-flash-preview`)
  * `StoryboardHTMLCompilerAgent`

### Phase 4: CLI & Ergonomics (`omni` command)
- Build Typer/Rich CLI in `omni_director/cli.py`:
  * `omni run --input brief.json --mode hybrid`
  * Support `--dry-run` for instant mock tests.
  * Support `--continuous` for Mode B scene extension.
  * Support `--render-video` for live video output.

### Phase 5: Verification & Golden Demos
- Write unit and mock integration tests under `tests/`.
- Execute and package Golden Demos:
  * IKEA ASMR 2.0 ("The Living Room Unfolds")
  * SEPHORA London Pulse 2.0 ("Midnight Velvet" - Mode A and Mode B)
- Validate skills and package readiness.

## 4. Risk Mitigation & Defenses
- **Risk**: API Rate Limiting or High Latency on Video Generation.
  * **Defense**: Tri-Mode Architecture defaults to `--hybrid` (storyboard pre-vis and prompts only), saving video quota for final verified runs.
- **Risk**: Multi-Subject Feature Bleed in Gemini Omni.
  * **Defense**: Mandatory High-Contrast Wardrobe Polarity in Stage 2 and strict "One Job Per Reference" inclusion/exclusion clauses in Stage 5.
- **Risk**: Heading-Induced Graphic Text Artifacts in Video.
  * **Defense**: Final prompt synthesis strictly compiles into continuous natural-language prose with zero markdown headings.
