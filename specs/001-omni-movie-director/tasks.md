# Task Breakdown: 001-omni-movie-director

The implementation tasks are organized into sequential, testable milestones linked directly to Acceptance Criteria AC-1 through AC-10.

| Task ID | Description | Output Files / Target | Linked AC | Status |
| :--- | :--- | :--- | :--- | :--- |
| **TSK-1.1** | Create Spark Spec Portfolio | `specs/registry.md`, `specs/001-omni-movie-director/{brief.md, spec.md, plan.md, tasks.md}` | AC-1 | Completed |
| **TSK-2.1** | Author Foundational Gemini Omni Prompting Skill | `skills/gemini-omni-prompting/SKILL.md` (Prescription Spectrum, 5 Core Elements, DeepMind capabilities, Seedance 4.1-4.6, 4-step workflow, 10 templates, 7-item checklist) | AC-2 | In Progress |
| **TSK-3.1** | Author Master Movie Director Agent Skill | `skills/omni-movie-director/SKILL.md` (Exhaustive 400+ lines covering 6 stages: Intake, Bible SSOT, Nano Banana Pre-Vis, Sonic, Parallel Prompts, HTML Treatment) | AC-3, AC-4, AC-5, AC-6, AC-7, AC-8 | In Progress |
| **TSK-3.2** | Author Director Intake & Bible Reference | `skills/omni-movie-director/references/director-intake-and-bible.md` (Pydantic models, JSON schema, 5 questions, default heuristics) | AC-4, AC-5 | Pending |
| **TSK-3.3** | Author Nano Banana Storyboard Reference | `skills/omni-movie-director/references/nano-banana-storyboard-system.md` (3-Anchor templates, inclusion/exclusion matrix, optics, cinema HTML spec) | AC-6 | Pending |
| **TSK-3.4** | Author ADK 2.0 Multi-Agent Architecture Reference | `skills/omni-movie-director/references/adk-2-architecture.md` (Sequential/Parallel composite agents, Workflow DAG, tools, state contracts) | AC-5 | Pending |
| **TSK-3.5** | Author Golden Demos Reference | `skills/omni-movie-director/references/golden-demos.md` (IKEA ASMR 2.0, SEPHORA London Mode A Parallel & Mode B Continuous Extension) | AC-9, AC-10 | Pending |
| **TSK-4.1** | Package Configuration & Python Dependencies | `pyproject.toml`, `.gitignore`, `README.md` configured for `uv` | AC-1 | Pending |
| **TSK-4.2** | Implement ADK 2.0 Pydantic Schemas | `omni_director/schemas/{intake,production_bible,scene,bundle}.py` | AC-5 | Pending |
| **TSK-4.3** | Implement ADK 2.0 Tools & Agents | `omni_director/tools/`, `omni_director/agents/` | AC-5 | Pending |
| **TSK-4.4** | Implement Typer CLI & HTML Compiler Engine | `omni_director/cli.py`, `omni_director/core/compiler.py` | AC-10 | Pending |
| **TSK-5.1** | Author Unit & Integration Test Suite | `tests/unit/`, `tests/integration/` | AC-1 to AC-10 | Pending |
| **TSK-5.2** | Generate Golden Demo Assets & Run Verification | `demos/ikea_asmr_2_0/`, `demos/sephora_london_pulse_2_0/` | AC-10 | Pending |
