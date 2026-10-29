---
name: omni-product-council
description: Convene the autonomous 4-persona Product Council (FDE, Agent Systems Engineer, Agent Strategist, UX/UI Designer) to audit production bundles, code health, 2026 Model Matrix compliance, and cinematic storyboards for Omni Movie Director.
---

# Omni Product Council Skill (`omni-product-council`)

The **Omni Product Council** is an autonomous multi-agent governance board established to maintain production excellence across all facets of the Omni Movie Director cinematic production suite.

This skill guides agents through convening the council, auditing system health, running multi-persona evaluations, executing automated prompt healing, and verifying quality gates.

---

## 1. Council Persona Composition & 100-Point Rubric

The Council convenes four specialized personas, each evaluating up to 25 points for a total composite score of 100 points:

### 1. Forward Deployed Engineer (`council-fde`, 25 Points)
- **Runtime Health & Doctor (10 pts)**: Validates Python version ($\ge 3.11$), required packages, write access, and environment integrity via `omni doctor`.
- **Model Matrix Compliance (5 pts)**: Guarantees strict 2026 Model Matrix adherence (`gemini-4-argon`, `gemini-3.8-flash`, `gemini-3-pro-image`, `gemini-omni-1.1-flash-preview`). Rejects any legacy unapproved model strings.
- **Zero-Leak Telemetry & Bible Ingestion (10 pts)**: Ensures execution telemetry is written to `telemetry.json` with zero API key leaks, and validates arbitrary Bible JSON ingestion via `--bible-file`.

### 2. Agent Systems Engineer (`council-agent-engineer`, 25 Points)
- **Pydantic Contract Invariants (10 pts)**: Verifies `MasterProductionBible` schema validity, 3-reference ceiling, and wardrobe polarity locks.
- **7-Point Prompt Standards & Healing (10 pts)**: Enforces clean prose without markdown/HTML headers, max 3 action beats per 10s window, CRAFT camera completeness, and self-healing loop convergence.
- **Zero-Video-Before-Storyboard (5 pts)**: Ensures dry-run simulation mode generates SVG plates without premature API video credit consumption.

### 3. Agent Strategist (`council-strategist`, 25 Points)
- **Commercial Domain Alignment (10 pts)**: Validates brief classification across the 6 commercial archetypes (`automotive_robotics`, `culinary_asmr`, `luxury_fashion`, `kinetic_action`, `tech_hardware`, `architectural_sanctuary`) with deterministic tie-breaking.
- **Storytelling Mode Integrity (10 pts)**: Validates narrative arc in Mode A (parallel montage cuts) or Mode B (continuous unbroken +10s extensions up to 40s).
- **Sonic Architecture (5 pts)**: Verifies dynamic BGM blueprints (BPM, key signature, stems) and tactile diegetic audio specs.

### 4. UX/UI Storyboard Designer (`council-ux-designer`, 25 Points)
- **Cinema Animatic & SMPTE Scrubber (10 pts)**: Checks `#btn-play-animatic`, `#smpte-timecode` (24fps), and draggable `.scrubber-track` scaled to total runtime.
- **Dynamic Beat Timeline & Audit Drawer (5 pts)**: Validates dynamic beat rows matching `len(scene.action_beats)` with color-coded audio cues (`[Dialogue]`, `[SFX]`, `[Ambience]`, `[Music]`), and per-scene expandable `.audit-drawer`.
- **Accessibility & Non-Blocking Feedback (10 pts)**: Verifies WCAG 2.2 AA compliance (`role="tablist"`, `aria-live="polite"`, `:focus-visible`), keyboard shortcuts (`Space`, `1-3`, `T`, `E`), one-click `#btn-export-bible` JSON export, and zero blocking dialog calls (using `.cinema-toast`).

---

## 2. Step-by-Step Council Audit Workflow

### Step 1: Preflight Health Diagnostics
Execute the preflight doctor check before starting pipeline operations:
```bash
omni doctor
```
Or in Python:
```python
from omni_director.doctor import run_doctor
report = run_doctor()
assert report.passed, f"Doctor failed: {report.summary}"
```

### Step 2: Generate or Ingest Production Bundle
Generate a fresh treatment from a golden preset or custom domain brief:
```bash
# Golden preset in dry-run mode
omni --preset ikea-asmr -o output/ikea_audit --council

# Or from custom domain brief
omni --prompt "Precision robotics assembling carbon-fiber hypercar chassis" -o output/robotics_audit --council
```

### Step 3: Run Multi-Persona Evaluation
Invoke `ProductCouncilOrchestrator` to audit the production bundle:
```python
from omni_director import DirectorPipeline, get_preset_bible
from omni_director.agents.council import ProductCouncilOrchestrator

pipeline = DirectorPipeline()
bundle = pipeline.run(preset_name="ikea-asmr", output_dir="output/ikea", dry_run=True)

orchestrator = ProductCouncilOrchestrator()
report = orchestrator.audit(bundle)

print(f"Council Score: {report.overall_score}/100.0 (Passed: {report.passed})")
for persona_res in report.reviews:
    print(f"  [{persona_res.persona.value}] {persona_res.score}/25.0 - {len(persona_res.findings)} findings")
```

### Step 4: Validate Quality Gates
Verify that all quality gates are satisfied:
1. `report.overall_score >= 88.0` (Target $\ge 90.0$ for showcase bundles)
2. `report.critical_findings_count == 0`
3. All scene prompt audit scores $\ge 90 / 100$
4. Output HTML contains `#btn-play-animatic`, `#smpte-timecode`, `.scrubber-track`, `.audit-drawer`, and zero blocking dialog calls.

### Step 5: Verification & Daily Routine
Run the full test suite and daily council routine:
```bash
# Pytest suite
python3 -m pytest tests/test_director_suite.py -v

# Daily multi-archetype council routine
python3 scripts/run_daily_council.py
```
