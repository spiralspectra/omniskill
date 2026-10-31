"""Autonomous Product Council Orchestrator for Omni Movie Director ADK 2.0.

Evaluates productions across 4 specialized personas:
1. council-fde: Forward Deployed Engineer & Production Rigor (Schema, outputs, bundle structure)
2. council-agent-engineer: Prompt Architect & Heuristics (7-Point audit, self-healing, zero 3.1)
3. council-strategist: Creative Strategist (Domain archetypes, narrative, positive invariants)
4. council-ux-designer: UX & Visual Continuity (ViewBox, SMPTE safe guides, SVG keyframes)
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from pydantic import ConfigDict

from omni_director.config import FORBIDDEN_LEGACY_PATTERNS, DirectorConfig, cfg
from omni_director.presets import DOMAIN_ARCHETYPES, classify_brief_domain
from omni_director.schemas import (
    CouncilFinding,
    CouncilFindingSeverity,
    CouncilPersona,
    MasterProductionBible,
    PersonaReviewResult,
    ProductCouncilReport,
    ProductionBundle,
    load_bible_from_json,
)
from omni_director.telemetry import verify_bundle_checksums
from omni_director.tools.prompt_auditor import audit_omni_scene_prompt, heal_omni_scene_prompt

logger = logging.getLogger("omni_director.council")

try:
    from google.adk.agents import BaseAgent
except ImportError:
    class BaseAgent:  # type: ignore[no-redef]
        def __init__(self, name: str, description: str = "", **kwargs: Any) -> None:
            self.name = name
            self.description = description
            self.kwargs = kwargs

        def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
            return context


FORBIDDEN_COUNCIL_MODEL_PATTERNS = [
    re.compile(r"gemini[-_]?(?:1\.5|2\.0|2\.5|3\.0|3\.1)", re.IGNORECASE),
    re.compile(r"veo[-_]?(?:3\.0|3\.1)", re.IGNORECASE),
    re.compile(r"imagen[-_]?3", re.IGNORECASE),
    re.compile(r"\b3\.1\b", re.IGNORECASE),
    re.compile(r"[-_]3\.1", re.IGNORECASE),
]


class ProductCouncilOrchestrator(BaseAgent):
    """Orchestrates 4-persona autonomous product council audit of production bibles and bundles."""

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    def __init__(
        self,
        config: Optional[DirectorConfig] = None,
        *,
        name: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        agent_name = name or "ProductCouncilOrchestrator"
        desc = kwargs.pop("description", kwargs.pop("instruction", "Autonomous Product Council Orchestrator"))
        super().__init__(name=agent_name, description=desc, **kwargs)
        self.config = config or cfg

    def audit(
        self,
        bundle_or_bible: Optional[Union[ProductionBundle, MasterProductionBible, Dict[str, Any], str, Path]] = None,
        output_dir: Optional[Union[str, Path]] = None,
        auto_heal: bool = True,
        *,
        bundle: Optional[ProductionBundle] = None,
        bible: Optional[MasterProductionBible] = None,
    ) -> ProductCouncilReport:
        """Executes a 100-point council audit across all 4 personas."""
        resolved_bundle: Optional[ProductionBundle] = bundle
        resolved_bible: Optional[MasterProductionBible] = bible
        resolved_out_dir: Optional[Path] = None

        target = bundle_or_bible if bundle_or_bible is not None else (bundle or bible)
        if target is None:
            raise ValueError("No target bundle or bible provided for council audit.")

        if isinstance(target, ProductionBundle):
            resolved_bundle = target
            resolved_bible = target.bible
            if target.bundle_json_path:
                resolved_out_dir = Path(target.bundle_json_path).parent
        elif isinstance(target, MasterProductionBible):
            resolved_bible = target
        elif isinstance(target, dict):
            if "bible" in target and isinstance(target["bible"], dict):
                try:
                    resolved_bundle = ProductionBundle.model_validate(target)
                    resolved_bible = resolved_bundle.bible
                except Exception:
                    resolved_bible = load_bible_from_json(target)
            else:
                resolved_bible = load_bible_from_json(target)
        elif isinstance(target, (str, Path)):
            path = Path(target)
            if path.is_file():
                resolved_out_dir = path.parent
            resolved_bible = load_bible_from_json(path)
        else:
            raise ValueError(f"Unsupported payload for council audit: {type(target)}")

        bundle = resolved_bundle
        bible = resolved_bible

        if output_dir:
            resolved_out_dir = Path(output_dir)
        elif not resolved_out_dir:
            resolved_out_dir = Path(self.config.output_dir)

        reviews: List[PersonaReviewResult] = []
        recommendations: List[str] = []

        # 1. Council FDE Review (25 pts max)
        fde_review = self._review_fde(bible=bible, bundle=bundle, output_dir=resolved_out_dir)
        reviews.append(fde_review)

        # 2. Council Agent Engineer Review (25 pts max)
        ae_review = self._review_agent_engineer(bible=bible, auto_heal=auto_heal)
        reviews.append(ae_review)

        # 3. Council Strategist Review (25 pts max)
        strat_review = self._review_strategist(bible=bible)
        reviews.append(strat_review)

        # 4. Council UX Designer Review (25 pts max)
        ux_review = self._review_ux_designer(bible=bible, bundle=bundle, output_dir=resolved_out_dir)
        reviews.append(ux_review)

        total_score = round(sum(r.score for r in reviews), 2)
        critical_count = sum(
            len([f for f in r.findings if f.severity == CouncilFindingSeverity.CRITICAL])
            for r in reviews
        )
        passed = (total_score >= 88.0 and critical_count == 0)

        for r in reviews:
            for f in r.findings:
                if f.suggested_fix and f.suggested_fix not in recommendations:
                    recommendations.append(f.suggested_fix)

        report = ProductCouncilReport(
            version="2.1.0",
            project_title=bible.project_title if bible else "Omni Production",
            timestamp=datetime.now(timezone.utc).isoformat(),
            overall_score=total_score,
            passed=passed,
            critical_findings_count=critical_count,
            reviews=reviews,
            recommendations=recommendations,
        )

        if bundle is not None:
            bundle.council_report = report

        # Write reports to output directory
        if resolved_out_dir:
            try:
                resolved_out_dir.mkdir(parents=True, exist_ok=True)
                json_path = resolved_out_dir / "council_report.json"
                json_path.write_text(json.dumps(report.model_dump(), indent=2), encoding="utf-8")
                # Also create council_audit_report.json alias
                (resolved_out_dir / "council_audit_report.json").write_text(
                    json.dumps(report.model_dump(), indent=2), encoding="utf-8"
                )
                md_path = resolved_out_dir / "council_report.md"
                md_path.write_text(self.generate_markdown_report(report), encoding="utf-8")
            except Exception as e:
                logger.warning(f"Could not persist council reports to {resolved_out_dir}: {e}")

        return report

    def evaluate_bundle(
        self,
        bundle_or_bible: Optional[Union[ProductionBundle, MasterProductionBible, Dict[str, Any], str, Path]] = None,
        output_dir: Optional[Union[str, Path]] = None,
        auto_heal: bool = True,
        *,
        bundle: Optional[ProductionBundle] = None,
        bible: Optional[MasterProductionBible] = None,
    ) -> ProductCouncilReport:
        """Alias for audit()."""
        return self.audit(
            bundle_or_bible=bundle_or_bible,
            output_dir=output_dir,
            auto_heal=auto_heal,
            bundle=bundle,
            bible=bible,
        )

    def _review_fde(
        self,
        bible: Optional[MasterProductionBible],
        bundle: Optional[ProductionBundle],
        output_dir: Optional[Path],
    ) -> PersonaReviewResult:
        """Evaluates schema integrity, output structure, and bundle artifacts."""
        findings: List[CouncilFinding] = []
        score = 25.0

        if bible is None:
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.CRITICAL,
                category="schema_integrity",
                message="MasterProductionBible is missing or could not be loaded.",
                suggested_fix="Ensure valid MasterProductionBible is provided."
            ))
            return PersonaReviewResult(
                persona=CouncilPersona.COUNCIL_FDE,
                score=0.0,
                findings=findings,
                summary="Fatal: MasterProductionBible missing."
            )

        if not bible.scenes:
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.CRITICAL,
                category="scene_completeness",
                message="Bible has zero scenes defined.",
                suggested_fix="Define at least one scene in bible.scenes."
            ))
            score -= 25.0
        else:
            scene_indices = [s.scene_index for s in bible.scenes]
            expected = list(range(1, len(bible.scenes) + 1))
            if scene_indices != expected:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.MEDIUM,
                    category="scene_indexing",
                    message=f"Scene indices {scene_indices} are not 1-indexed sequential {expected}.",
                    suggested_fix="Renumber scenes sequentially starting at 1."
                ))
                score -= 3.0

        if bundle is not None:
            if not bundle.storyboard_html_path or not Path(bundle.storyboard_html_path).exists():
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.MEDIUM,
                    category="artifact_delivery",
                    message="storyboard_preview.html is missing or does not exist on disk.",
                    suggested_fix="Compile storyboard HTML before compiling bundle."
                ))
                score -= 4.0
            if not bundle.bundle_json_path or not Path(bundle.bundle_json_path).exists():
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.LOW,
                    category="artifact_delivery",
                    message="production_bundle.json file path does not exist on disk.",
                    suggested_fix="Persist production_bundle.json to output directory."
                ))
                score -= 2.0

        # Active Checksum Integrity Verification
        eval_dir = Path(output_dir) if output_dir else (Path(bundle.bundle_json_path).parent if bundle and bundle.bundle_json_path else None)
        if eval_dir and (eval_dir / "telemetry.json").is_file():
            is_valid, checksum_errors = verify_bundle_checksums(eval_dir)
            if not is_valid:
                has_mismatch = any("Checksum mismatch" in err for err in checksum_errors)
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.CRITICAL if has_mismatch else CouncilFindingSeverity.HIGH,
                    category="artifact_integrity",
                    message=f"Bundle artifact checksum verification failed ({len(checksum_errors)} issue(s)): {'; '.join(checksum_errors[:2])}",
                    suggested_fix="Re-run compilation to regenerate artifacts with matching SHA-256 digests."
                ))
                score -= 6.0 if has_mismatch else 4.0

        score = max(0.0, min(25.0, round(score, 2)))
        summary = f"FDE review completed with score {score}/25.0. {len(findings)} findings."
        return PersonaReviewResult(
            persona=CouncilPersona.COUNCIL_FDE,
            score=score,
            findings=findings,
            summary=summary,
        )

    def _review_agent_engineer(
        self,
        bible: Optional[MasterProductionBible],
        auto_heal: bool = True,
    ) -> PersonaReviewResult:
        """Audits scene prompts against 7-Point standards and self-heals defects."""
        findings: List[CouncilFinding] = []
        if bible is None or not bible.scenes:
            return PersonaReviewResult(
                persona=CouncilPersona.COUNCIL_AGENT_ENGINEER,
                score=0.0,
                findings=[CouncilFinding(
                    severity=CouncilFindingSeverity.CRITICAL,
                    category="prompt_architecture",
                    message="No scenes available to audit.",
                    suggested_fix="Add valid scenes to MasterProductionBible."
                )],
                summary="Agent Engineer review failed: no scenes."
            )

        # Check for forbidden 3.1 models in bible metadata
        bible_str = bible.model_dump_json()
        for pat in FORBIDDEN_COUNCIL_MODEL_PATTERNS:
            match = pat.search(bible_str)
            if match:
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.CRITICAL,
                    category="model_matrix_violation",
                    message=f"Legacy model reference '{match.group(0)}' detected in production bible.",
                    suggested_fix="Replace all legacy models with approved 2026 models (gemini-4-argon, etc.)."
                ))

        audit_scores = []
        for scene in bible.scenes:
            res = audit_omni_scene_prompt(
                scene,
                regime=bible.creative_regime,
                storytelling_mode=getattr(bible, "storytelling_mode", None),
            )
            if (not res.passed or res.score < 90.0) and auto_heal:
                logger.info(f"Self-healing prompt for Scene {scene.scene_index}...")
                healed_target, res = heal_omni_scene_prompt(
                    scene,
                    audit_result=res,
                    regime=bible.creative_regime,
                    storytelling_mode=getattr(bible, "storytelling_mode", None),
                )
                findings.append(CouncilFinding(
                    severity=CouncilFindingSeverity.INFO,
                    category="auto_heal",
                    message=f"Scene {scene.scene_index} prompt was automatically self-healed.",
                    details={"scene_index": scene.scene_index}
                ))

            audit_scores.append(res.score)
            if not res.passed:
                for err in res.errors:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.HIGH,
                        category="prompt_defect",
                        message=f"Scene {scene.scene_index}: {err}",
                        suggested_fix=f"Refine scene {scene.scene_index} prompt to comply with 7-Point standard."
                    ))

        avg_audit_score = sum(audit_scores) / len(audit_scores) if audit_scores else 0.0
        score = 25.0 * (avg_audit_score / 100.0)
        critical_count = len([f for f in findings if f.severity == CouncilFindingSeverity.CRITICAL])
        score -= (critical_count * 10.0)
        score = max(0.0, min(25.0, round(score, 2)))

        summary = f"Agent Engineer review completed with score {score}/25.0 (Prompt Audit avg: {avg_audit_score:.1f}%)."
        return PersonaReviewResult(
            persona=CouncilPersona.COUNCIL_AGENT_ENGINEER,
            score=score,
            findings=findings,
            summary=summary,
        )

    def _review_strategist(self, bible: Optional[MasterProductionBible]) -> PersonaReviewResult:
        """Evaluates creative domain alignment, 6-archetype styling, and positive invariants."""
        findings: List[CouncilFinding] = []
        score = 25.0

        if bible is None:
            return PersonaReviewResult(
                persona=CouncilPersona.COUNCIL_STRATEGIST,
                score=0.0,
                findings=[],
                summary="Strategist review failed: bible missing."
            )

        combined_text = f"{bible.project_title} {bible.logline}"
        detected_domain = classify_brief_domain(combined_text)
        archetype = DOMAIN_ARCHETYPES.get(detected_domain, {})

        # Check positive invariants across scene prompts (no negative prompt constraints)
        negative_phrases = [
            "don't ", "do not ", "avoid ", "no blur", "never ", "without any ",
            "no shaking", "no camera shake", "no cuts", "without cuts", "not blurry",
        ]
        for scene in bible.scenes:
            prompt_str = getattr(scene, "scene_prompt", getattr(scene, "omni_prose_prompt", ""))
            prompt_lower = prompt_str.lower()
            for phrase in negative_phrases:
                if phrase in prompt_lower:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.LOW,
                        category="positive_invariants",
                        message=f"Scene {scene.scene_index} uses negative constraint '{phrase}'. Use positive direction instead.",
                        suggested_fix=f"Rephrase Scene {scene.scene_index} prompt with affirmative physical descriptions."
                    ))
                    score -= 1.0

        # Check sonic identity presence
        bgm_desc = ""
        if hasattr(bible, "master_bgm") and bible.master_bgm:
            bgm_desc = (
                getattr(bible.master_bgm, "sonic_description", "")
                or getattr(bible.master_bgm, "lyria_prompt", "")
                or getattr(bible.master_bgm, "genre_style", "")
            )
        elif hasattr(bible, "sonic_identity") and bible.sonic_identity:
            bgm_obj = getattr(bible.sonic_identity, "master_bgm", bible.sonic_identity)
            bgm_desc = (
                getattr(bgm_obj, "sonic_description", "")
                or getattr(bgm_obj, "lyria_prompt", "")
                or getattr(bgm_obj, "genre_style", "")
            )

        if not bgm_desc:
            findings.append(CouncilFinding(
                severity=CouncilFindingSeverity.MEDIUM,
                category="sonic_strategy",
                message="Master BGM sonic description is empty.",
                suggested_fix="Define clear tempo, instrumentation, and sonic atmosphere in master_bgm."
            ))
            score -= 3.0

        score = max(0.0, min(25.0, round(score, 2)))
        summary = f"Strategist review completed with score {score}/25.0 (Domain: {detected_domain})."
        return PersonaReviewResult(
            persona=CouncilPersona.COUNCIL_STRATEGIST,
            score=score,
            findings=findings,
            summary=summary,
        )

    def _review_ux_designer(
        self,
        bible: Optional[MasterProductionBible],
        bundle: Optional[ProductionBundle],
        output_dir: Optional[Path] = None,
    ) -> PersonaReviewResult:
        """Evaluates viewBox geometry, SMPTE safe guides, and visual storyboard plate completeness."""
        findings: List[CouncilFinding] = []
        score = 25.0

        if bible is None or not bible.scenes:
            return PersonaReviewResult(
                persona=CouncilPersona.COUNCIL_UX_DESIGNER,
                score=0.0,
                findings=[],
                summary="UX Designer review failed: no scenes."
            )

        for scene in bible.scenes:
            svg = ""
            kf = getattr(scene, "keyframe_spec", None)
            if kf and hasattr(kf, "svg_markup") and kf.svg_markup:
                svg = kf.svg_markup or ""
            elif bundle and bundle.visual_plates:
                svg = bundle.visual_plates.get(f"scene_{scene.scene_index}", "")

            if svg:
                # If svg is a path to an SVG file, load the content
                if svg.endswith(".svg") or (len(svg) < 500 and Path(svg).is_file()):
                    try:
                        p = Path(svg)
                        if p.is_file():
                            svg = p.read_text(encoding="utf-8")
                    except Exception:
                        pass

                # Check viewBox attribute
                if not re.search(r'viewBox=["\']\s*0\s+0\s+\d+(\.\d+)?\s+\d+(\.\d+)?\s*["\']', svg):
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.MEDIUM,
                        category="viewbox_geometry",
                        message=f"Scene {scene.scene_index} SVG keyframe lacks standard valid viewBox attribute.",
                        suggested_fix="Render SVG keyframe with standard viewBox='0 0 1920 1080'."
                    ))
                    score -= 2.0

                # Check safe guides
                has_action_safe = "safe-guide-action" in svg or 'stroke-dasharray="8 6"' in svg or 'stroke-dasharray="6,6"' in svg
                has_title_safe = "safe-guide-title" in svg or 'stroke-dasharray="4 4"' in svg or 'stroke-dasharray="3,3"' in svg
                if not (has_action_safe and has_title_safe):
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.LOW,
                        category="safe_guides",
                        message=f"Scene {scene.scene_index} SVG keyframe missing SMPTE action-safe or title-safe guide rects.",
                        suggested_fix="Enable show_safe_guides=True when rendering keyframe SVGs."
                    ))
                    score -= 1.5

        # Verify compiled storyboard HTML transport controls if present
        html_path = (
            Path(bundle.storyboard_html_path)
            if (bundle and bundle.storyboard_html_path)
            else (Path(output_dir) / "storyboard_preview.html" if output_dir else None)
        )
        if html_path and html_path.is_file():
            try:
                html_content = html_path.read_text(encoding="utf-8")
                if 'id="btn-play-animatic"' not in html_content or 'id="smpte-timecode"' not in html_content:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.MEDIUM,
                        category="animatic_transport",
                        message="Compiled storyboard preview HTML lacks interactive play transport or SMPTE timecode display.",
                        suggested_fix="Ensure compile_storyboard_html generates #btn-play-animatic and #smpte-timecode controls."
                    ))
                    score -= 2.0
                if 'id="btn-loop-animatic"' not in html_content or "jumpToBeat(" not in html_content:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.LOW,
                        category="animatic_transport",
                        message="Compiled storyboard preview HTML lacks continuous loop playback toggle button (#btn-loop-animatic) or jumpToBeat controls.",
                        suggested_fix="Ensure compile_storyboard_html generates #btn-loop-animatic and jumpToBeat handlers."
                    ))
                    score -= 1.0
                if 'role="tablist"' not in html_content or "cinema-toast" not in html_content:
                    findings.append(CouncilFinding(
                        severity=CouncilFindingSeverity.LOW,
                        category="animatic_accessibility",
                        message="Compiled storyboard preview HTML lacks accessible tablist semantics or non-blocking cinema-toast container.",
                        suggested_fix="Ensure compile_storyboard_html generates role='tablist' and #cinema-toast elements."
                    ))
                    score -= 1.0
            except Exception:
                pass

        score = max(0.0, min(25.0, round(score, 2)))
        summary = f"UX Designer review completed with score {score}/25.0."
        return PersonaReviewResult(
            persona=CouncilPersona.COUNCIL_UX_DESIGNER,
            score=score,
            findings=findings,
            summary=summary,
        )

    def generate_markdown_report(self, report: ProductCouncilReport) -> str:
        """Formats the ProductCouncilReport as a publication-ready Markdown document."""
        status_badge = "PASSED" if report.passed else "FAILED"
        lines = [
            f"# Product Council Audit Report: {report.project_title}",
            "",
            f"**Version**: {report.version} | **Timestamp**: `{report.timestamp}`",
            f"**Overall Score**: **`{report.overall_score} / 100.0`** | **Status**: **{status_badge}**",
            f"**Critical Findings**: {report.critical_findings_count}",
            "",
            "## Persona Scorecard",
            "",
            "| Persona | Role | Score (/25) | Findings Count | Summary |",
            "| :--- | :--- | :---: | :---: | :--- |",
        ]

        role_map = {
            CouncilPersona.COUNCIL_FDE: "Forward Deployed Engineer (Schema & Delivery)",
            CouncilPersona.COUNCIL_AGENT_ENGINEER: "Agent Engineer (7-Point Prompts & Models)",
            CouncilPersona.COUNCIL_STRATEGIST: "Creative Strategist (Domain & Invariants)",
            CouncilPersona.COUNCIL_UX_DESIGNER: "UX & Visual Continuity (ViewBox & Safe Guides)",
        }

        for rev in report.reviews:
            role = role_map.get(rev.persona, rev.persona.value)
            lines.append(
                f"| `{rev.persona.value}` | {role} | **{rev.score:.1f}** | {len(rev.findings)} | {rev.summary} |"
            )

        lines.extend([
            "",
            "## Findings & Action Items",
            "",
        ])

        if not any(r.findings for r in report.reviews):
            lines.append("No findings or defects identified. All criteria met with highest honors.")
        else:
            for rev in report.reviews:
                if not rev.findings:
                    continue
                lines.append(f"### {rev.persona.value.upper()}")
                for f in rev.findings:
                    badge = f"[{f.severity.value.upper()}]"
                    lines.append(f"- {badge} **{f.category}**: {f.message}")
                    if f.suggested_fix:
                        lines.append(f"  - *Suggested Fix*: {f.suggested_fix}")
                lines.append("")

        if report.recommendations:
            lines.extend([
                "## Recommendations",
                "",
            ])
            for rec in report.recommendations:
                lines.append(f"1. {rec}")
            lines.append("")

        return "\n".join(lines)

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """ADK 2.0 Agent invocation hook."""
        bundle_or_bible = context.get("bundle") or context.get("bible")
        out_dir = context.get("output_dir")
        auto_heal = context.get("auto_heal", True)
        report = self.audit(bundle_or_bible, output_dir=out_dir, auto_heal=auto_heal)
        context["council_report"] = report
        return context
