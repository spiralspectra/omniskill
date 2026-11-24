"""AI Compute, Take-Budget & Render Economics Estimator (PM-FEAT-032)."""

import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple, Union

from omni_director.config import validate_model_identifier
from omni_director.schemas import (
    MasterProductionBible,
    MasterRenderEconomicsManifest,
    ModelTierRateSpec,
    RenderBudgetGuardrailSpec,
    SceneComputeEstimateSpec,
    ScenePromptSpec,
    StorytellingMode,
    TakeVariantRecord,
)


def get_2026_model_matrix_rates() -> List[ModelTierRateSpec]:
    """Returns the 2026 Model Matrix pricing table after strict identifier validation."""
    rates = [
        ModelTierRateSpec(
            model_id="gemini-4-argon",
            role_label="Lead Creative Director",
            input_per_1m_usd=2.50,
            output_per_1m_usd=10.00,
            unit_render_usd=0.0,
        ),
        ModelTierRateSpec(
            model_id="gemini-3.8-flash",
            role_label="Fast Workhorse Fan-Out",
            input_per_1m_usd=0.15,
            output_per_1m_usd=0.60,
            unit_render_usd=0.0,
        ),
        ModelTierRateSpec(
            model_id="gemini-3-pro-image",
            role_label="Visual Concept & Continuity",
            input_per_1m_usd=1.25,
            output_per_1m_usd=5.00,
            unit_render_usd=0.08,
        ),
        ModelTierRateSpec(
            model_id="gemini-omni-1.1-flash-preview",
            role_label="Video & Multimodal Audio",
            input_per_1m_usd=0.50,
            output_per_1m_usd=2.00,
            unit_render_usd=0.25,
        ),
    ]
    for rate in rates:
        validate_model_identifier(rate.model_id, "model_rate.model_id")
    return rates


def format_render_profile_token(spec: SceneComputeEstimateSpec) -> str:
    """Formats a compact machine telemetry token for PM-FEAT-032 compute estimates."""
    return (
        f"[RENDER-PROFILE: SC{spec.scene_index:02d} | {spec.prompt_mode} | "
        f"takes={spec.planned_takes} | dur={spec.duration_seconds}s | "
        f"est=${spec.estimated_scene_usd:.2f}]"
    )


def _infer_scene_duration_seconds(scene: ScenePromptSpec) -> int:
    """Parses scene duration in seconds from timestamp_range, defaulting to 8s."""
    ts = str(getattr(scene, "timestamp_range", "") or "")
    matches = re.findall(r"(\d+):(\d+)", ts)
    if len(matches) >= 2:
        start_s = int(matches[0][0]) * 60 + int(matches[0][1])
        end_s = int(matches[1][0]) * 60 + int(matches[1][1])
        if end_s > start_s:
            return max(4, min(15, end_s - start_s))
    ext_match = re.search(r"\+(\d+)s", ts, re.IGNORECASE)
    if ext_match:
        return max(4, min(15, int(ext_match.group(1))))
    return 8


def estimate_scene_compute_cost(
    scene: ScenePromptSpec,
    planned_takes: int = 2,
    mode: str = "mode_a_4step",
) -> SceneComputeEstimateSpec:
    """Deterministically estimates scene compute cost and generates TakeVariantRecord entries."""
    rates = {r.model_id: r for r in get_2026_model_matrix_rates()}
    argon_rate = rates["gemini-4-argon"]
    flash_rate = rates["gemini-3.8-flash"]
    image_rate = rates["gemini-3-pro-image"]
    omni_rate = rates["gemini-omni-1.1-flash-preview"]

    sc_idx = int(getattr(scene, "scene_index", 1) or 1)
    duration_seconds = _infer_scene_duration_seconds(scene)
    n_takes = max(1, int(planned_takes))
    plate_renders = 1

    norm_mode = "mode_b_6step" if "mode_b" in str(mode).lower() else "mode_a_4step"
    reasoning_tokens_est = 5200 if norm_mode == "mode_b_6step" else 3500

    prompt_text = (
        str(getattr(scene, "omni_prose_prompt", "") or "").strip()
        or str(getattr(scene, "scene_title", f"Scene {sc_idx}") or f"Scene {sc_idx}")
    )
    prompt_sha_prefix = hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()[:12]

    per_take_video_cost = round(duration_seconds * omni_rate.unit_render_usd, 4)
    takes: List[TakeVariantRecord] = []
    for t in range(1, n_takes + 1):
        seed_hex = hashlib.sha256(f"{prompt_sha_prefix}:{sc_idx}:{t}".encode("utf-8")).hexdigest()[:8]
        seed = (int(seed_hex, 16) % 2_147_483_646) + 1
        takes.append(
            TakeVariantRecord(
                take_id=f"SC{sc_idx:02d}_T{t}",
                seed=seed,
                prompt_sha256_prefix=prompt_sha_prefix,
                audit_score=95,
                estimated_cost_usd=per_take_video_cost,
                selected=(t == 1),
                director_note="Primary hero take" if t == 1 else f"Coverage safety take {t}",
            )
        )

    director_tokens_cost = (reasoning_tokens_est / 1_000_000.0) * (
        argon_rate.input_per_1m_usd + argon_rate.output_per_1m_usd
    )
    fanout_tokens_cost = (2000 / 1_000_000.0) * (
        flash_rate.input_per_1m_usd + flash_rate.output_per_1m_usd
    )
    plate_cost = plate_renders * image_rate.unit_render_usd
    video_cost = sum(t.estimated_cost_usd for t in takes)
    estimated_scene_usd = round(director_tokens_cost + fanout_tokens_cost + plate_cost + video_cost, 4)

    spec = SceneComputeEstimateSpec(
        scene_index=sc_idx,
        duration_seconds=duration_seconds,
        prompt_mode=norm_mode,
        planned_takes=n_takes,
        plate_renders=plate_renders,
        reasoning_tokens_est=reasoning_tokens_est,
        estimated_scene_usd=estimated_scene_usd,
        takes=takes,
        render_profile_token="",
    )
    spec.render_profile_token = format_render_profile_token(spec)
    return spec


def check_render_budget_guardrail(
    manifest: MasterRenderEconomicsManifest,
    max_budget_usd: float,
) -> Tuple[bool, str]:
    """Verifies whether estimated_total_usd stays within max_budget_usd."""
    budget = float(max_budget_usd)
    est_total = float(getattr(manifest.guardrail, "estimated_total_usd", 0.0))
    within = est_total <= budget
    if within:
        return True, (
            f"Render budget guardrail passed: ${est_total:.2f} <= ${budget:.2f} cap."
        )
    return False, (
        f"Render budget guardrail exceeded: ${est_total:.2f} > ${budget:.2f} cap."
    )


def compile_render_economics_manifest(
    bible: MasterProductionBible,
    max_budget_usd: float = 50.0,
) -> MasterRenderEconomicsManifest:
    """Compiles the MasterRenderEconomicsManifest across all scenes of a bible."""
    rates = get_2026_model_matrix_rates()
    domain = str(getattr(bible, "domain_archetype", None) or "architectural_sanctuary")
    title = str(getattr(bible, "project_title", "OmniProject") or "OmniProject")
    digest = hashlib.sha256(f"{title}:{domain}:econ".encode("utf-8")).hexdigest()[:8].upper()
    manifest_id = f"ECON-{digest}"

    story_mode = getattr(bible, "storytelling_mode", StorytellingMode.MODE_A_PARALLEL_CUT)
    default_mode = (
        "mode_b_6step"
        if story_mode == StorytellingMode.MODE_B_CONTINUOUS_CHAIN
        else "mode_a_4step"
    )

    scenes: List[ScenePromptSpec] = list(getattr(bible, "scenes", None) or [])
    scene_estimates: List[SceneComputeEstimateSpec] = []

    for sc in scenes:
        existing = getattr(sc, "compute_estimate_spec", None)
        if existing is not None:
            est = existing.model_copy(deep=True)
            if not est.render_profile_token:
                est.render_profile_token = format_render_profile_token(est)
        else:
            est = estimate_scene_compute_cost(sc, planned_takes=2, mode=default_mode)
        sc.compute_estimate_spec = est
        scene_estimates.append(est)

    estimated_total_usd = round(sum(e.estimated_scene_usd for e in scene_estimates), 4)
    total_planned_takes = sum(e.planned_takes for e in scene_estimates)
    total_video_seconds_planned = sum(e.duration_seconds * e.planned_takes for e in scene_estimates)

    aicp_bid = getattr(bible, "master_aicp_bid", None) or getattr(bible, "aicp_bid", None)
    aicp_total = 0.0
    if aicp_bid is not None:
        aicp_total = float(getattr(aicp_bid, "grand_total", 0.0) or 0.0)
        if aicp_total <= 0.0 and getattr(aicp_bid, "top_sheet", None) is not None:
            aicp_total = float(getattr(aicp_bid.top_sheet, "grand_total_bid_usd", 0.0) or 0.0)
    if aicp_total <= 0.0:
        aicp_total = 120000.0

    savings_pct = round(max(0.0, (1.0 - (estimated_total_usd / aicp_total)) * 100.0), 4)
    budget_cap = float(max_budget_usd)
    utilization_pct = round((estimated_total_usd / budget_cap) * 100.0, 2) if budget_cap > 0 else 100.0

    guardrail = RenderBudgetGuardrailSpec(
        max_render_budget_usd=budget_cap,
        estimated_total_usd=estimated_total_usd,
        utilization_pct=utilization_pct,
        within_budget=(estimated_total_usd <= budget_cap),
        hard_abort_on_live_exceed=True,
        simulation_savings_vs_aicp_pct=savings_pct,
    )

    return MasterRenderEconomicsManifest(
        manifest_id=manifest_id,
        archetype=domain,
        model_rates=rates,
        scene_estimates=scene_estimates,
        guardrail=guardrail,
        total_planned_takes=total_planned_takes,
        total_video_seconds_planned=total_video_seconds_planned,
        dry_run_billable_usd=0.0,
    )


def synthesize_default_render_economics_manifest(
    bible: MasterProductionBible,
    max_budget_usd: float = 50.0,
) -> MasterRenderEconomicsManifest:
    """Convenience helper to synthesize a default MasterRenderEconomicsManifest."""
    return compile_render_economics_manifest(bible, max_budget_usd=max_budget_usd)


def export_render_economics_bundle(
    bible: MasterProductionBible,
    output_dir: Union[str, Path],
) -> Dict[str, str]:
    """Exports render_economics_manifest.json, take_variant_ledger.csv, and ai_compute_estimate.md."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = (
        getattr(bible, "master_render_economics_spec", None)
        or compile_render_economics_manifest(bible)
    )

    json_path = out_dir / "render_economics_manifest.json"
    json_path.write_text(json.dumps(manifest.model_dump(mode="json"), indent=2), encoding="utf-8")

    csv_path = out_dir / "take_variant_ledger.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Scene",
            "Take_ID",
            "Seed",
            "Prompt_SHA256_Prefix",
            "Audit_Score",
            "Estimated_Cost_USD",
            "Selected",
            "Director_Note",
        ])
        for sc_est in manifest.scene_estimates:
            for take in sc_est.takes:
                writer.writerow([
                    sc_est.scene_index,
                    take.take_id,
                    take.seed,
                    take.prompt_sha256_prefix,
                    take.audit_score,
                    take.estimated_cost_usd,
                    take.selected,
                    take.director_note,
                ])

    md_path = out_dir / "ai_compute_estimate.md"
    lines = [
        f"# AI Compute & Render Economics Estimate — {getattr(bible, 'project_title', 'Production')}",
        "",
        f"- **Manifest ID**: `{manifest.manifest_id}`",
        f"- **Domain Archetype**: `{manifest.archetype}`",
        f"- **Estimated Live Total**: `${manifest.guardrail.estimated_total_usd:.2f}`",
        f"- **Budget Guardrail Cap**: `${manifest.guardrail.max_render_budget_usd:.2f}` "
        f"({manifest.guardrail.utilization_pct:.1f}% utilized | Within Budget: {manifest.guardrail.within_budget})",
        f"- **Dry-Run Billable Cost**: `${manifest.dry_run_billable_usd:.2f}`",
        f"- **Simulation Savings vs Traditional AICP**: `{manifest.guardrail.simulation_savings_vs_aicp_pct:.4f}%`",
        f"- **Total Planned Takes**: {manifest.total_planned_takes} ({manifest.total_video_seconds_planned}s video)",
        "",
        "## 2026 Model Matrix Unit Rates",
    ]
    for rate in manifest.model_rates:
        lines.append(
            f"- **`{rate.model_id}`** ({rate.role_label}): "
            f"in=${rate.input_per_1m_usd:.2f}/1M, out=${rate.output_per_1m_usd:.2f}/1M, "
            f"unit_render=${rate.unit_render_usd:.2f}"
        )
    lines.append("")
    lines.append("## Per-Scene Compute Breakdown")
    for sc_est in manifest.scene_estimates:
        lines.append(
            f"- **Scene {sc_est.scene_index:02d}** (`{sc_est.prompt_mode}`): "
            f"{sc_est.duration_seconds}s x {sc_est.planned_takes} takes = `${sc_est.estimated_scene_usd:.4f}`"
        )
    lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")

    return {
        "render_economics_manifest_json": str(json_path),
        "take_variant_ledger_csv": str(csv_path),
        "ai_compute_estimate_md": str(md_path),
    }
