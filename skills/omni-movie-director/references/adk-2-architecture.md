# ADK 2.0 Technical Architecture & Multi-Agent DAG Reference

This reference details the production implementation of the `omni-movie-director` multi-agent pipeline using **Google Agent Development Kit 2.0 (`google-adk>=2.13.0`)** and the **Unified Gen AI SDK (`google-genai>=2.33.0`)**.

---

## 1. System Topology Overview

The architecture decomposes the filmmaking process into six functional stages, executing either as a composite agent tree (`SequentialAgent` + `ParallelAgent`) or as a declarative DAG (`google.adk.workflow.Workflow`):

```
[User Input Brief / Attached Brand Docs]
                     │
                     ▼
       ┌───────────────────────────┐
       │   IntakeAndResearchAgent  │  (Grounded with google_search & load_web_page)
       └─────────────┬─────────────┘
                     ▼
       ┌───────────────────────────┐
       │   CreativeDirectorAgent   │  (gemini-4-argon: Synthesizes Master ProductionBible)
       └─────────────┬─────────────┘
                     ▼
       ┌───────────────────────────┐
       │ VisualBibleGeneratorAgent │  (gemini-3-pro-image / Nano Banana: Turnaround & Plates)
       └─────────────┬─────────────┘
                     ▼
     ┌───────────────────────────────┐
     │ StoryboardParallelAgent       │  (gemini-3-pro-image: Parallel Scene Keyframes 1..N)
     └───────────────┬───────────────┘
                     ▼
  ═════════════════════════════════════════════════════════════════
  ScenePromptFanOutAgent (ParallelAgent running on gemini-3.8-flash)
  ┌───────────────────┬───────────────────┬───────────────────────┐
  │ ScenePromptAgent_0│ ScenePromptAgent_1│ ... ScenePromptAgent_N│
  └─────────┬─────────┴─────────┬─────────┴───────────┬───────────┘
            │                   │                     │
            └───────────────────┼─────────────────────┘
                                ▼
                    ┌───────────────────────┐
                    │   BGMComposerAgent    │
                    └───────────┬───────────┘
  ═════════════════════════════════════════════════════════════════
                                │
                                ▼
                 [render_video == True?]
                 ├── No ────────────────────────┐
                 └── Yes ──► ┌──────────────────┴───────────────┐
                             │   OptionalOmniVideoRenderAgent   │
                             │ (Gemini Omni video generation)   │
                             └──────────────────┬───────────────┘
                                                ▼
                             ┌──────────────────────────────────┐
                             │    StoryboardHTMLCompilerAgent   │
                             │  (Fan-In treatment HTML & JSON)  │
                             └──────────────────────────────────┘
```

---

## 2. Model Tiering Matrix

| Pipeline Role | Model Identifier | Config Constant | Responsibilities |
| :--- | :--- | :--- | :--- |
| **Lead Director** | `gemini-4-argon` | `DIRECTOR_MODEL` | Narrative logic, Pydantic schema synthesis, spatial continuity. |
| **Fast Workers** | `gemini-3.8-flash` | `FAST_MODEL` | High-throughput prompt fan-out, BGM composition, audit. |
| **Concept Artist** | `gemini-3-pro-image` | `IMAGE_MODEL` | 2K Turnaround sheets, master environment plates, scene keyframes. |
| **Video Engine** | `gemini-omni-1.1-flash-preview` | `OMNI_VIDEO_MODEL` | 720p/1080p video, 48kHz synced audio, reference conditioning, +10s extensions. |

---

## 3. ADK 2.0 Composite Tree Implementation

```python
"""
Composite Agent Tree Topology using ADK 2.0 SequentialAgent and ParallelAgent.
"""

from google.adk.agents import SequentialAgent, ParallelAgent
from google.adk.tools import FunctionTool
from omni_director.config import get_settings
from omni_director.agents import (
    IntakeAndResearchAgent,
    CreativeDirectorAgent,
    VisualBibleGeneratorAgent,
    StoryboardParallelAgent,
    ScenePromptAgent,
    ParallelScenePromptAgent,
    BGMComposerAgent,
    OptionalOmniVideoRenderAgent,
    StoryboardHTMLCompilerAgent,
)

settings = get_settings()

def build_omni_director_agent(target_scenes: int = 4, render_video: bool = False) -> SequentialAgent:
    """Constructs the complete multi-agent production tree."""
    
    # 1. Parallel Scene Prompt Fan-Out Sub-Agents
    prompt_subagents = [
        ScenePromptAgent(
            name=f"scene_prompt_agent_{i}",
            scene_index=i,
            model_name=settings.FAST_MODEL
        )
        for i in range(target_scenes)
    ]
    
    # 2. Parallel Prompt & Sonic Specialist Group
    prompt_and_sound_group = ParallelAgent(
        name="prompt_and_sound_fanout",
        agents=[*prompt_subagents, BGMComposerAgent(name="bgm_composer", model_name=settings.FAST_MODEL)],
        description="Parallel synthesis of Gemini Omni scene prompts and master BGM score."
    )
    
    # 3. Master Sequential Pipeline
    pipeline_steps = [
        IntakeAndResearchAgent(name="intake_and_research", model_name=settings.FAST_MODEL),
        CreativeDirectorAgent(name="creative_director", model_name=settings.DIRECTOR_MODEL),
        VisualBibleGeneratorAgent(name="visual_bible_artist", model_name=settings.IMAGE_MODEL),
        StoryboardParallelAgent(name="storyboard_artist", model_name=settings.IMAGE_MODEL),
        prompt_and_sound_group,
    ]
    
    if render_video:
        pipeline_steps.append(
            OptionalOmniVideoRenderAgent(
                name="omni_video_renderer",
                model_name=settings.OMNI_VIDEO_MODEL
            )
        )
        
    pipeline_steps.append(
        StoryboardHTMLCompilerAgent(name="storyboard_compiler")
    )
    
    return SequentialAgent(
        name="omni_movie_director_root",
        agents=pipeline_steps,
        description="End-to-end multi-agent AI commercial and film production pipeline."
    )
```

---

## 4. ADK 2.0 Declarative Workflow DAG Implementation

```python
"""
Declarative Workflow Graph using google.adk.workflow.Workflow.
"""

from google.adk.workflow import Workflow, Step
from omni_director.config import get_settings

settings = get_settings()

def build_omni_workflow() -> Workflow:
    workflow = Workflow(name="omni_director_workflow")
    
    # Step 1: Research & Intake
    step_intake = Step(
        id="step_intake",
        agent="intake_and_research_agent",
        inputs=["session.brief"]
    )
    
    # Step 2: Creative Director (Bible Synthesis)
    step_bible = Step(
        id="step_bible",
        agent="creative_director_agent",
        inputs=["step_intake.output"],
        depends_on=["step_intake"]
    )
    
    # Step 3: Visual Concept Art (Character & Room Plates)
    step_visual_bible = Step(
        id="step_visual_bible",
        agent="visual_bible_generator_agent",
        inputs=["step_bible.output.production_bible"],
        depends_on=["step_bible"]
    )
    
    # Step 4: Storyboard Keyframes
    step_storyboard = Step(
        id="step_storyboard",
        agent="storyboard_parallel_agent",
        inputs=["step_bible.output.production_bible"],
        depends_on=["step_bible"]
    )
    
    # Step 5: Scene Prompts & Sound (Parallel)
    step_prompts = Step(
        id="step_prompts",
        agent="scene_prompt_fanout_agent",
        inputs=["step_bible.output.production_bible", "step_visual_bible.output", "step_storyboard.output"],
        depends_on=["step_visual_bible", "step_storyboard"]
    )
    
    # Step 6: Compilation
    step_compiler = Step(
        id="step_compiler",
        agent="storyboard_html_compiler_agent",
        inputs=["step_bible.output", "step_prompts.output"],
        depends_on=["step_prompts"]
    )
    
    workflow.add_steps([
        step_intake,
        step_bible,
        step_visual_bible,
        step_storyboard,
        step_prompts,
        step_compiler
    ])
    
    return workflow
```

---

## 5. Artifact Persistence Architecture (`LocalDiskArtifactService`)

To prevent multi-megabyte base64 strings from polluting model contexts:
1. `VisualBibleGeneratorAgent` and `StoryboardParallelAgent` save generated PNG concept art directly to disk via `LocalDiskArtifactService`.
2. Only the lightweight file path or GCS URI is persisted in the Pydantic state model (`turnaround_artifact_uri`, `plate_artifact_uri`, `keyframe_artifact_uri`).
3. Downstream video rendering and HTML compilation nodes read directly from the filesystem.
