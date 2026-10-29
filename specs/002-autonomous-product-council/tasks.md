# Task Breakdown: 002-autonomous-product-council

All tasks are ordered sequentially with explicit done-checks linked to Acceptance Criteria AC-1 through AC-10.

| Task ID | Description | Target Files | Linked AC | Done-Check | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **TSK-1.1** | Create Spark Spec `002-autonomous-product-council` & update `specs/registry.md` | `specs/registry.md`, `specs/002-autonomous-product-council/{brief.md, spec.md, plan.md, tasks.md}` | AC-10 | Spec suite created and integrated into `specs/registry.md`. | Completed |
| **TSK-2.1** | Fix Python 3.12 type union crash (`\| any`) & ADK 2.0 `BaseAgent` (`extra="forbid"`) incompatibility | `omni_director/tools/nano_banana.py`, `omni_director/agents/agent.py` | AC-1 | Verified: all 30 baseline tests pass with zero type or agent init failures. | Completed |
| **TSK-3.1** | Extend Pydantic v2 schemas (`ProductCouncilReport`, `load_bible_from_json`) & Harden Prompt Auditor with `heal_omni_scene_prompt(max_attempts=3)` | `omni_director/schemas.py`, `omni_director/tools/prompt_auditor.py` | AC-3, AC-5, AC-6 | Verified: `load_bible_from_json` handles raw bibles/bundles, `heal_omni_scene_prompt` heals markdown headers, missing speed locks, foley cues, and Mode B continuous continuity. | Completed |
| **TSK-3.2** | Implement 6-Archetype Domain-Aware Brief Synthesizer with priority tie-breaking & fallback | `omni_director/presets.py`, `omni_director/agents/agent.py` | AC-7 | Verified: `classify_brief_domain()` and `synthesize_custom_bible()` tested across all 6 archetypes with tie-breaking and fallback. | Completed |
| **TSK-4.1** | Implement FDE Preflight Doctor (`doctor.py`) & Structured Telemetry (`telemetry.py`) | `omni_director/doctor.py`, `omni_director/telemetry.py` | AC-2, AC-4 | Verified: `run_doctor()` catches legacy 3.1 models (exit 1) and passes valid env (exit 0); `telemetry.json` emits redacted telemetry. | Completed |
| **TSK-4.2** | Implement `ProductCouncilOrchestrator` (`omni_director/agents/council.py`) & Wire into Pipeline & CLI | `omni_director/agents/council.py`, `omni_director/agents/agent.py`, `omni_director/cli.py`, `omni_director/__init__.py`, `omni_director/agents/__init__.py` | AC-1, AC-2, AC-3, AC-4, AC-6 | Verified: `omni doctor`, `omni council`, `--bible-file`, and `--council-strict` negative falsification (exit 2) pass. | Completed |
| **TSK-5.1** | Upgrade Dark-Room Cinema HTML Compiler (`html_compiler.py`) & Nano Banana SVG Guides (`nano_banana.py`) | `omni_director/tools/html_compiler.py`, `omni_director/tools/nano_banana.py` | AC-8 | Verified: `storyboard_preview.html` contains animatic transport, SMPTE scrubber, beat timelines, audit drawer, JSON export, and aria-live polite attributes. | Completed |
| **TSK-6.1** | Author Repository Law (`AGENTS.md`), Portable Council Skill (`skills/omni-product-council/SKILL.md`), & Daily Runner (`scripts/run_daily_council.py`) | `AGENTS.md`, `skills/omni-product-council/SKILL.md`, `scripts/run_daily_council.py`, `README.md` | AC-9 | Verified: `python3 scripts/run_daily_council.py` runs end-to-end and exits 0 with 100.0/100.0 scores across canonical showcase bundles. | Completed |
| **TSK-7.1** | Expand Pytest Suite (`tests/test_director_suite.py`), Regenerate `examples/`, Run Round 2 Council & Adversarial Audit | `tests/test_director_suite.py`, `examples/*` | AC-1 to AC-10 | Verified: `python3 -m pytest tests/test_director_suite.py -v` passes 53/53 tests (exit 0); `run_daily_council.py` exits 0. | Completed |

## Verification Evidence
1. **Pytest Suite**:
   ```bash
   python3 -m pytest tests/test_director_suite.py -v
   # Output: 53 passed, 1 warning in 0.86s (Exit code 0)
   ```
2. **Autonomous Daily Council Routine**:
   ```bash
   python3 scripts/run_daily_council.py
   # Output: ALL DAILY PRODUCT COUNCIL QUALITY GATES PASSED (Exit code 0)
   # Average Composite Council Score: 100.00 / 100.0
   # Canonical showcase bundles regenerated in examples/{cyberpunk_noir_2_0, solarpunk_utopia_2_0, minimalist_luxury_2_0}
   # Council reports written to docs/council_reports/latest_council_report.{json,md}
   ```
