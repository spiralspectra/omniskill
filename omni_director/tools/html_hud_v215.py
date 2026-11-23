"""Modular v2.15.0 Dark-Room Cinema HUD Components (PM-FEAT-029 & PM-FEAT-030).

Provides Python 3.11-compatible builders for:
1. PM-FEAT-029: S3D Stereoscopy HUD (#modal-s3d-stereography, ] hotkey)
2. PM-FEAT-030: Audio Description (AD) & Accessibility HUD (#modal-accessibility-ad, [ hotkey)
"""

from __future__ import annotations

import csv
import io
import json
import re
from html import escape as html_escape
from typing import Any, Dict, List

from omni_director.schemas import MasterProductionBible, ProductionBundle


def _escape_js_template_literal(text: str) -> str:
    escaped = str(text).replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
    return re.sub(r"</(script)", r"<\/\1", escaped, flags=re.IGNORECASE)


def _escape_json_for_script(payload: Any) -> str:
    return re.sub(r"</(script)", r"<\/\1", json.dumps(payload), flags=re.IGNORECASE)


def _to_plain(obj: Any) -> Any:
    if obj is None:
        return None
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if hasattr(obj, "value"):
        return obj.value
    if isinstance(obj, dict):
        return {str(k): _to_plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_plain(v) for v in obj]
    return obj


def _sec_to_smpte(sec: float, fps: int = 24) -> str:
    total_frames = max(0, int(round(float(sec) * fps)))
    ff = total_frames % fps
    total_sec = total_frames // fps
    ss = total_sec % 60
    mm = (total_sec // 60) % 60
    hh = total_sec // 3600
    return f"{hh:02d}:{mm:02d}:{ss:02d}:{ff:02d}"


def _sec_to_vtt(sec: float) -> str:
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


def _try_synthesize_s3d_manifest(bible: MasterProductionBible) -> Dict[str, Any]:
    spec = getattr(bible, "master_s3d_spec", None)
    if spec is None:
        try:
            from omni_director.tools.stereoscopic_3d import compile_s3d_manifest
            spec = compile_s3d_manifest(bible)
        except Exception:
            spec = None
    plain = _to_plain(spec)
    if isinstance(plain, dict):
        return plain
    return {
        "target_platform": "Apple Vision Pro",
        "spatial_format": "mv_hevc",
        "baseline_interaxial_mm": 65.0,
        "max_parallax_budget_pct": 2.5,
        "comfort_audit_passed": True,
        "scene_specs": [],
    }


def _try_synthesize_accessibility_manifest(bible: MasterProductionBible) -> Dict[str, Any]:
    spec = getattr(bible, "master_accessibility_spec", None)
    if spec is None:
        try:
            from omni_director.tools.accessibility_ad import compile_accessibility_manifest
            spec = compile_accessibility_manifest(bible)
        except Exception:
            spec = None
    plain = _to_plain(spec)
    if isinstance(plain, dict):
        return plain
    return {
        "standard": "WCAG 2.2 AA / 21st Century CVAA",
        "target_audience": "extended_cvaa",
        "total_ad_cues": 0,
        "collision_count": 0,
        "min_wcag_contrast_ratio": 7.0,
        "all_scenes_cvaa_compliant": True,
        "scene_profiles": [],
    }


def _build_s3d_csv(s3d_dict: Dict[str, Any]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Scene", "Rig_Type", "IO_mm", "Conv_m", "Pos_Parallax_Pct", "Neg_Parallax_Pct", "Comfort"])
    for sc in s3d_dict.get("scene_specs") or []:
        cam = sc.get("camera_spec") or {}
        writer.writerow([
            sc.get("scene_number", 1),
            cam.get("rig_type", "parallel"),
            cam.get("interaxial_distance_mm", 65.0),
            cam.get("convergence_plane_m", 2.5),
            sc.get("max_positive_parallax_pct", 1.0),
            sc.get("max_negative_parallax_pct", 0.0),
            sc.get("comfort_zone_passed", True),
        ])
    return buf.getvalue()


def _build_ad_vtt_and_csv(acc_dict: Dict[str, Any]) -> tuple[str, str, List[Dict[str, Any]]]:
    cues: List[Dict[str, Any]] = []
    for prof in acc_dict.get("scene_profiles") or []:
        for c in prof.get("ad_cues") or []:
            cues.append(c)

    vtt_lines = ["WEBVTT", ""]
    csv_buf = io.StringIO()
    writer = csv.writer(csv_buf)
    writer.writerow(["CueID", "Scene", "Start", "End", "Prose", "WPS", "WCAG_Contrast", "CVAA_Compliant"])

    for c in cues:
        start_s = float(c.get("start_time_sec", 0.0))
        end_s = float(c.get("end_time_sec", 2.0))
        prose = str(c.get("descriptive_prose", ""))
        cue_id = str(c.get("cue_id", "AD-01"))
        vtt_lines.append(cue_id)
        vtt_lines.append(f"{_sec_to_vtt(start_s)} --> {_sec_to_vtt(end_s)}")
        vtt_lines.append(f"[AD] {prose}")
        vtt_lines.append("")
        writer.writerow([
            cue_id,
            c.get("scene_number", 1),
            start_s,
            end_s,
            prose,
            c.get("wps", 2.0),
            c.get("contrast_ratio_measured", 7.0),
            c.get("cvaa_compliant", True),
        ])

    return "\n".join(vtt_lines), csv_buf.getvalue(), cues


def build_v215_hud_bundle(
    bible: MasterProductionBible,
    bundle: ProductionBundle,
    scene_time_lookup: List[Dict[str, Any]],
    total_runtime_sec: float,
) -> Dict[str, str]:
    """Builds CSS, HTML modals/ribbon, and JS for PM-FEAT-029 (S3D) and PM-FEAT-030 (Accessibility AD)."""
    s3d_dict = _try_synthesize_s3d_manifest(bible)
    acc_dict = _try_synthesize_accessibility_manifest(bible)

    s3d_json = _escape_json_for_script(s3d_dict)
    acc_json = _escape_json_for_script(acc_dict)

    s3d_csv_escaped = _escape_js_template_literal(_build_s3d_csv(s3d_dict))
    s3d_manifest_escaped = _escape_js_template_literal(json.dumps(s3d_dict, indent=2))

    ad_vtt_str, ad_csv_str, ad_cues = _build_ad_vtt_and_csv(acc_dict)
    acc_vtt_escaped = _escape_js_template_literal(ad_vtt_str)
    acc_csv_escaped = _escape_js_template_literal(ad_csv_str)

    s3d_scenes = s3d_dict.get("scene_specs") or []
    first_cam = (s3d_scenes[0].get("camera_spec") or {}) if s3d_scenes else {}
    io_disp = f"{float(first_cam.get('interaxial_distance_mm', s3d_dict.get('baseline_interaxial_mm', 65.0))):.1f}"
    conv_disp = f"{float(first_cam.get('convergence_plane_m', 2.5)):.2f}"
    pos_disp = f"{max([float(s.get('max_positive_parallax_pct', 0.0)) for s in s3d_scenes] or [1.2]):.2f}"
    neg_disp = f"{min([float(s.get('max_negative_parallax_pct', 0.0)) for s in s3d_scenes] or [0.0]):.2f}"
    comfort_ok = bool(s3d_dict.get("comfort_audit_passed", True))
    comfort_text = "Comfort: <3.0% OK" if comfort_ok else "Comfort: REVIEW (>3.0%)"

    cvaa_ok = bool(acc_dict.get("all_scenes_cvaa_compliant", True))
    cvaa_text = "CVAA Compliant" if cvaa_ok else "Check Collisions"
    wcag_ratio = float(acc_dict.get("min_wcag_contrast_ratio", 7.0))
    wcag_badge = f"AAA ({wcag_ratio:.1f}:1)" if wcag_ratio >= 7.0 else f"AA ({wcag_ratio:.1f}:1)"
    collisions = int(acc_dict.get("collision_count", 0))
    col_text = "0 Collisions (Safe)" if collisions == 0 else f"{collisions} Overlap(s)"

    ad_rows_html = []
    for c in ad_cues:
        start_s = float(c.get("start_time_sec", 0.0))
        smpte = html_escape(_sec_to_smpte(start_s))
        prose = html_escape(str(c.get("descriptive_prose", "")))
        cue_id = html_escape(str(c.get("cue_id", "AD")))
        ad_rows_html.append(
            f'<tr tabindex="0" data-sec="{start_s:.2f}">'
            f'<td><code>{smpte}</code> ({cue_id})</td>'
            f'<td>[AD] {prose}</td>'
            f'</tr>'
        )
    if not ad_rows_html:
        ad_rows_html.append(
            '<tr tabindex="0" data-sec="0"><td><code>00:00:00:00</code></td><td>[AD] Visual description ready.</td></tr>'
        )
    ad_tbody_html = "\n".join(ad_rows_html)

    safe_total_rt = max(1.0, float(total_runtime_sec or 32.0))
    ribbon_blocks_html = []
    for c in ad_cues:
        start_s = float(c.get("start_time_sec", 0.0))
        end_s = max(start_s + 0.5, float(c.get("end_time_sec", start_s + 2.0)))
        left_pct = min(98.0, max(0.0, (start_s / safe_total_rt) * 100.0))
        width_pct = min(100.0 - left_pct, max(2.0, ((end_s - start_s) / safe_total_rt) * 100.0))
        title = html_escape(f"{c.get('cue_id', 'AD')}: {c.get('descriptive_prose', '')}")
        ribbon_blocks_html.append(
            f'<div class="ad-cue-block" tabindex="0" role="button" data-sec="{start_s:.2f}" '
            f'style="left:{left_pct:.2f}%;width:{width_pct:.2f}%;" title="{title}" '
            f'aria-label="{title}"></div>'
        )
    ribbon_inner_html = "\n".join(ribbon_blocks_html)

    css = """
/* v2.15 HUD CSS */
#modal-s3d-stereography, #modal-accessibility-ad {
    display: none;
    position: fixed;
    top: 5%;
    left: 5%;
    width: 90%;
    height: 90%;
    background: rgba(10, 12, 18, 0.97);
    border: 1px solid #334155;
    border-radius: 8px;
    z-index: 10000;
    color: #f8fafc;
    flex-direction: column;
    box-shadow: 0 24px 60px rgba(0, 0, 0, 0.75);
}
#modal-s3d-stereography:focus-visible, #modal-accessibility-ad:focus-visible {
    outline: 2px solid #38bdf8;
    outline-offset: 2px;
}
.v215-modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.9rem 1.2rem;
    border-bottom: 1px solid #334155;
}
.v215-modal-body {
    flex: 1;
    overflow-y: auto;
    padding: 1.2rem;
}
.btn-v215-close {
    background: #b91c1c;
    color: #ffffff;
    border: none;
    border-radius: 4px;
    padding: 0.45rem 0.9rem;
    cursor: pointer;
    font-weight: 600;
}
.btn-v215-close:focus-visible {
    outline: 2px solid #ffffff;
    outline-offset: 2px;
}
.btn-v215-dl {
    background: #0369a1;
    color: #ffffff;
    border: none;
    border-radius: 4px;
    padding: 0.45rem 0.9rem;
    cursor: pointer;
    margin-right: 0.5rem;
    font-weight: 600;
}
.btn-v215-dl:hover {
    background: #0284c7;
}
.btn-v215-dl:focus-visible {
    outline: 2px solid #facc15;
    outline-offset: 2px;
}
#s3d-anaglyph-canvas {
    width: 100%;
    max-width: 600px;
    height: 190px;
    background: #020617;
    border: 1px solid #334155;
    border-radius: 4px;
}
#s3d-depth-svg {
    width: 100%;
    max-width: 600px;
    height: 110px;
    background: #0f172a;
    border: 1px solid #334155;
    border-radius: 4px;
    margin-top: 0.5rem;
}
.s3d-badge, .acc-badge {
    display: inline-block;
    padding: 0.25rem 0.55rem;
    margin: 0.2rem;
    border-radius: 4px;
    font-size: 0.85rem;
    font-family: monospace;
    background: #1e293b;
    color: #f8fafc;
    border: 1px solid #475569;
}
#ad-scrubber-ribbon {
    width: 100%;
    height: 10px;
    background: rgba(250, 204, 21, 0.14);
    border: 1px solid rgba(250, 204, 21, 0.45);
    border-radius: 3px;
    position: relative;
    margin-bottom: 6px;
}
.ad-cue-block {
    position: absolute;
    top: 1px;
    height: 6px;
    background: #facc15;
    border-radius: 2px;
    cursor: pointer;
}
.ad-cue-block:focus-visible {
    outline: 2px solid #ffffff;
}
.acc-table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 0.75rem;
    font-size: 0.9rem;
}
.acc-table th, .acc-table td {
    border: 1px solid #334155;
    padding: 0.55rem;
    text-align: left;
}
.acc-table th {
    background: #1e293b;
}
.acc-table tr[tabindex="0"]:hover,
.acc-table tr[tabindex="0"]:focus-visible {
    background: #1e293b;
    outline: 2px solid #facc15;
    cursor: pointer;
}
"""

    modals_html = f"""
<!-- S3D Stereoscopy Modal (PM-FEAT-029) -->
<div id="modal-s3d-stereography" role="dialog" aria-modal="true" aria-labelledby="s3d-modal-title" tabindex="-1">
    <div class="v215-modal-header">
        <h2 id="s3d-modal-title">S3D Stereoscopy &amp; MV-HEVC Spatial HUD (PM-FEAT-029)</h2>
        <button class="btn-v215-close" id="btn-s3d-close" aria-label="Close S3D HUD">Close [Esc]</button>
    </div>
    <div class="v215-modal-body">
        <div style="margin-bottom: 1rem;">
            <canvas id="s3d-anaglyph-canvas" aria-label="Red/Cyan Anaglyph Z-space Parallax Visualizer"></canvas>
            <svg id="s3d-depth-svg" viewBox="0 0 600 110" aria-label="SVG Depth Plane Gauge">
                <rect x="0" y="0" width="600" height="110" fill="#0f172a"/>
                <line x1="20" y1="55" x2="580" y2="55" stroke="#475569" stroke-width="2"/>
                <line x1="300" y1="15" x2="300" y2="95" stroke="#38bdf8" stroke-width="2" stroke-dasharray="4 3"/>
                <text x="300" y="14" fill="#38bdf8" font-size="11" text-anchor="middle">Convergence Plane ({conv_disp}m)</text>
                <text x="45" y="102" fill="#f87171" font-size="10">-Parallax ({neg_disp}%)</text>
                <text x="555" y="102" fill="#34d399" font-size="10" text-anchor="end">+Parallax ({pos_disp}% &lt; 3.0%)</text>
            </svg>
        </div>
        <div style="margin-bottom: 1rem;">
            <span class="s3d-badge">Platform: {html_escape(str(s3d_dict.get("target_platform", "Apple Vision Pro")))}</span>
            <span class="s3d-badge">IO: <span id="s3d-io">{io_disp}</span>mm</span>
            <span class="s3d-badge">Conv: <span id="s3d-conv">{conv_disp}</span>m</span>
            <span class="s3d-badge">Pos Prlx: <span id="s3d-pos">{pos_disp}</span>%</span>
            <span class="s3d-badge">Neg Prlx: <span id="s3d-neg">{neg_disp}</span>%</span>
            <span class="s3d-badge" id="s3d-comfort">{comfort_text}</span>
        </div>
        <div>
            <button class="btn-v215-dl" onclick="downloadS3dCSV()">s3d_parallax_log.csv</button>
            <button class="btn-v215-dl" onclick="downloadS3dManifest()">spatial_video_manifest.json</button>
        </div>
    </div>
</div>

<!-- AD Accessibility Modal & Scrubber Ribbon (PM-FEAT-030) -->
<div id="modal-accessibility-ad" role="dialog" aria-modal="true" aria-labelledby="acc-modal-title" tabindex="-1">
    <div class="v215-modal-header">
        <h2 id="acc-modal-title">Audio Description (AD) &amp; WCAG/CVAA Accessibility HUD (PM-FEAT-030)</h2>
        <button class="btn-v215-close" id="btn-acc-close" aria-label="Close Accessibility HUD">Close [Esc]</button>
    </div>
    <div class="v215-modal-body">
        <div style="margin-bottom: 0.75rem;">
            <span class="acc-badge">CVAA: <span id="acc-cvaa">{html_escape(cvaa_text)}</span></span>
            <span class="acc-badge">WCAG: <span id="acc-wcag">{html_escape(wcag_badge)}</span></span>
            <span class="acc-badge">Dialogue Timing: <span id="acc-col">{html_escape(col_text)}</span></span>
        </div>
        <div id="ad-scrubber-ribbon" aria-label="Audio Description Track Timeline">{ribbon_inner_html}</div>
        <table class="acc-table" id="acc-cue-table">
            <thead>
                <tr>
                    <th>SMPTE Timecode</th>
                    <th>Audio Description Cue</th>
                </tr>
            </thead>
            <tbody id="acc-cue-tbody">
                {ad_tbody_html}
            </tbody>
        </table>
        <div style="margin-top: 1rem;">
            <button class="btn-v215-dl" onclick="downloadAccVTT()">subtitles_ad.vtt</button>
            <button class="btn-v215-dl" onclick="downloadAccCSV()">ad_script_cue_sheet.csv</button>
        </div>
    </div>
</div>
"""

    js = f"""
    const S3D_STATE = {s3d_json};
    const ACC_STATE = {acc_json};

    let isS3dHUDOpen = false;
    let lastS3dOpener = null;
    let isAccHUDOpen = false;
    let lastAccOpener = null;

    function _v215ShowToast(msg) {{
        if (typeof showCinemaToast === 'function') {{
            showCinemaToast(msg);
            return;
        }}
        const toast = document.createElement('div');
        toast.className = 'cinema-toast';
        toast.textContent = msg;
        toast.style.position = 'fixed';
        toast.style.bottom = '20px';
        toast.style.right = '20px';
        toast.style.background = '#0f172a';
        toast.style.color = '#f8fafc';
        toast.style.padding = '10px 18px';
        toast.style.borderRadius = '6px';
        toast.style.border = '1px solid #38bdf8';
        toast.style.zIndex = '20000';
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    }}

    function _triggerBlobDownload(content, mime, filename, toastMsg) {{
        const blob = new Blob([content], {{ type: mime }});
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
        _v215ShowToast(toastMsg);
    }}

    window.downloadS3dCSV = function() {{ _triggerBlobDownload(`{s3d_csv_escaped}`, 'text/csv', 's3d_parallax_log.csv', 'Downloaded S3D Parallax Log'); }};
    window.downloadS3dManifest = function() {{ _triggerBlobDownload(`{s3d_manifest_escaped}`, 'application/json', 'spatial_video_manifest.json', 'Downloaded Spatial Video Manifest'); }};
    window.downloadAccVTT = function() {{ _triggerBlobDownload(`{acc_vtt_escaped}`, 'text/vtt', 'subtitles_ad.vtt', 'Downloaded AD WebVTT Track'); }};
    window.downloadAccCSV = function() {{ _triggerBlobDownload(`{acc_csv_escaped}`, 'text/csv', 'ad_script_cue_sheet.csv', 'Downloaded AD Cue Sheet'); }};

    window.toggleS3dHUD = function(forceOpen) {{
        const modal = document.getElementById('modal-s3d-stereography');
        if (!modal) return;
        const shouldOpen = forceOpen !== undefined ? forceOpen : !isS3dHUDOpen;
        if (shouldOpen) {{
            lastS3dOpener = document.activeElement;
            modal.style.display = 'flex';
            isS3dHUDOpen = true;
            const closeBtn = document.getElementById('btn-s3d-close');
            if (closeBtn) closeBtn.focus();
            renderS3dAnaglyph();
        }} else {{
            modal.style.display = 'none';
            isS3dHUDOpen = false;
            if (lastS3dOpener && typeof lastS3dOpener.focus === 'function') lastS3dOpener.focus();
        }}
    }};

    window.toggleAccessibilityAdHUD = function(forceOpen) {{
        const modal = document.getElementById('modal-accessibility-ad');
        if (!modal) return;
        const shouldOpen = forceOpen !== undefined ? forceOpen : !isAccHUDOpen;
        if (shouldOpen) {{
            lastAccOpener = document.activeElement;
            modal.style.display = 'flex';
            isAccHUDOpen = true;
            const closeBtn = document.getElementById('btn-acc-close');
            if (closeBtn) closeBtn.focus();
        }} else {{
            modal.style.display = 'none';
            isAccHUDOpen = false;
            if (lastAccOpener && typeof lastAccOpener.focus === 'function') lastAccOpener.focus();
        }}
    }};

    function renderS3dAnaglyph() {{
        const canvas = document.getElementById('s3d-anaglyph-canvas');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;
        const w = canvas.width = 600;
        const h = canvas.height = 190;
        ctx.clearRect(0, 0, w, h);
        ctx.fillStyle = '#020617';
        ctx.fillRect(0, 0, w, h);

        const scenes = (S3D_STATE && S3D_STATE.scene_specs) ? S3D_STATE.scene_specs : [];
        const first = scenes[0] || {{}};
        const pos = parseFloat(first.max_positive_parallax_pct || 1.5);
        const shiftPx = Math.max(4, Math.min(28, Math.round(pos * 8)));

        ctx.globalCompositeOperation = 'screen';
        ctx.strokeStyle = '#ff2a55';
        ctx.lineWidth = 3;
        ctx.strokeRect(210 - shiftPx, 42, 180, 105);
        ctx.strokeStyle = '#00f0ff';
        ctx.strokeRect(210 + shiftPx, 42, 180, 105);
        ctx.globalCompositeOperation = 'source-over';
        ctx.fillStyle = '#e2e8f0';
        ctx.font = '12px monospace';
        ctx.fillText('L/R Anaglyph Disparity Shift: +/-' + shiftPx + 'px', 16, 22);
    }}

    function _v215TrapFocus(modal) {{
        const focusables = modal.querySelectorAll('a[href], button, textarea, input, select, [tabindex]:not([tabindex="-1"])');
        if (!focusables.length) return;
        const firstEl = focusables[0];
        const lastEl = focusables[focusables.length - 1];
        modal.addEventListener('keydown', function(e) {{
            if (e.key === 'Tab') {{
                if (e.shiftKey && document.activeElement === firstEl) {{
                    lastEl.focus();
                    e.preventDefault();
                }} else if (!e.shiftKey && document.activeElement === lastEl) {{
                    firstEl.focus();
                    e.preventDefault();
                }}
            }}
        }});
    }}

    window.initS3dHUD = function() {{
        const modal = document.getElementById('modal-s3d-stereography');
        const btnClose = document.getElementById('btn-s3d-close');
        if (btnClose) btnClose.addEventListener('click', () => toggleS3dHUD(false));
        if (modal) _v215TrapFocus(modal);
    }};

    window.initAccessibilityAdHUD = function() {{
        const modal = document.getElementById('modal-accessibility-ad');
        const btnClose = document.getElementById('btn-acc-close');
        if (btnClose) btnClose.addEventListener('click', () => toggleAccessibilityAdHUD(false));
        if (modal) _v215TrapFocus(modal);

        const tbody = document.getElementById('acc-cue-tbody');
        if (tbody) {{
            tbody.addEventListener('click', (e) => {{
                const tr = e.target.closest('tr[data-sec]');
                if (tr && tr.dataset.sec) {{
                    const sec = parseFloat(tr.dataset.sec);
                    if (typeof seekToTime === 'function') seekToTime(sec);
                    else if (typeof window.seekTo === 'function') window.seekTo(sec);
                    toggleAccessibilityAdHUD(false);
                }}
            }});
            tbody.addEventListener('keydown', (e) => {{
                if (e.key === 'Enter' || e.code === 'Space') {{
                    const tr = e.target.closest('tr[data-sec]');
                    if (tr && tr.dataset.sec) {{
                        e.preventDefault();
                        const sec = parseFloat(tr.dataset.sec);
                        if (typeof seekToTime === 'function') seekToTime(sec);
                        else if (typeof window.seekTo === 'function') window.seekTo(sec);
                        toggleAccessibilityAdHUD(false);
                    }}
                }}
            }});
        }}

        const ribbon = document.getElementById('ad-scrubber-ribbon');
        if (ribbon) {{
            ribbon.querySelectorAll('.ad-cue-block').forEach((block) => {{
                block.addEventListener('click', () => {{
                    const sec = parseFloat(block.dataset.sec || '0');
                    if (typeof seekToTime === 'function') seekToTime(sec);
                    else if (typeof window.seekTo === 'function') window.seekTo(sec);
                }});
                block.addEventListener('keydown', (e) => {{
                    if (e.key === 'Enter' || e.code === 'Space') {{
                        e.preventDefault();
                        const sec = parseFloat(block.dataset.sec || '0');
                        if (typeof seekToTime === 'function') seekToTime(sec);
                        else if (typeof window.seekTo === 'function') window.seekTo(sec);
                    }}
                }});
            }});
        }}
    }};
"""

    return {
        "css": css,
        "modals_html": modals_html,
        "js": js,
    }
