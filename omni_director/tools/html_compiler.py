"""HTML Animatic Compiler and Storyboard UI Generator."""

import base64
import json
from pathlib import Path
from typing import Optional
from omni_director.schemas import ProductionBundle


def _render_plate_html(plate_value: Optional[str], alt: str = "Visual Plate") -> str:
    """Renders plate value into self-contained HTML (inline SVG or base64 img).

    - If plate_value starts with '<svg', returns it directly.
    - If plate_value is an existing .svg file path on disk, returns the SVG content.
    - If plate_value is an existing .png/.jpg file path on disk, returns a base64-encoded img tag.
    - Otherwise returns a clean placeholder.
    """
    if not plate_value or not str(plate_value).strip():
        return f'<div class="svg-placeholder">{alt}</div>'

    val = str(plate_value).strip()
    if val.startswith("<svg"):
        return val

    try:
        p = Path(val)
        if p.exists() and p.is_file():
            suffix = p.suffix.lower()
            if suffix == ".svg":
                return p.read_text(encoding="utf-8")
            elif suffix in (".png", ".jpg", ".jpeg", ".webp"):
                raw_bytes = p.read_bytes()
                b64 = base64.b64encode(raw_bytes).decode("ascii")
                mime = "image/png" if suffix == ".png" else "image/jpeg"
                return f'<img src="data:{mime};base64,{b64}" alt="{alt}" style="width:100%;height:100%;object-fit:cover;border-radius:8px;" />'
    except Exception:
        pass

    return f'<div class="svg-placeholder">{alt}</div>'


def compile_storyboard_html(bundle: ProductionBundle, output_dir: Path) -> Path:
    """Compiles a ProductionBundle into a dark-room Cinema HTML Storyboard and JSON bundle."""
    output_dir.mkdir(parents=True, exist_ok=True)
    bible = bundle.bible

    # Also save the complete JSON production bundle
    bundle_json_path = output_dir / "production_bundle.json"
    bundle_json_path.write_text(bundle.model_dump_json(indent=2), encoding="utf-8")
    bundle.bundle_json_path = str(bundle_json_path)

    # Build color swatches
    swatches_html = "".join([
        f'<div class="swatch-box" style="background: {c};" onclick="navigator.clipboard.writeText(\'{c}\')"><span>{c}</span></div>'
        for c in (bible.color_palette or ["#1A1A24", "#FF4B4B", "#00F0FF", "#F0F0F5"])
    ])

    # Build 3-Tier Visual Continuity Bible cards
    bible_cards_html = []
    for asset in bible.nano_banana_assets:
        plate_val = asset.svg_markup or asset.local_path or bundle.visual_plates.get(asset.asset_id, "")
        svg_preview = _render_plate_html(plate_val, alt=asset.job_description)
        bible_cards_html.append(f"""
        <div class="bible-card">
          <div class="bible-preview-wrap">
            <div class="bible-tag">{asset.asset_id}</div>
            <div class="plate-svg-container">{svg_preview}</div>
          </div>
          <div class="bible-content">
            <div class="bible-title">{asset.job_description}</div>
            <div class="bible-dna"><strong style="color: #FF4B4B;">Exclusion Clause:</strong> {asset.exclusion_clause}</div>
            <details class="prompt-drawer">
              <summary class="prompt-drawer-btn"><span>NANO BANANA GENERATION PROMPT</span> ▾</summary>
              <div class="prompt-drawer-content">
                <pre>{asset.generation_prompt}</pre>
                <button class="btn-copy-sm" onclick="copyText(this, `{asset.generation_prompt.replace('`', "'")}`)">Copy Prompt</button>
              </div>
            </details>
          </div>
        </div>
        """)
    continuity_grid_html = "\n".join(bible_cards_html)

    # Build Shot-by-Shot Timeline Scenes
    scenes_html = []
    for scene in bible.scenes:
        audit_rep = next((a for a in bundle.audit_reports if a.scene_index == scene.scene_index), None)
        audit_badge = '<span class="badge-pass">✓ 7-POINT AUDIT PASS</span>' if (audit_rep and audit_rep.passed) else '<span class="badge-audit">AUDITED</span>'
        
        # Action beats
        beats_html = "".join([
            f'<div class="beat-item"><span class="beat-num">BEAT {i+1}</span> {beat}</div>'
            for i, beat in enumerate(scene.action_beats)
        ])

        # Kinetic Contact Chain
        chain_html = f'<div class="chain-box"><strong>KINETIC CONTACT CHAIN:</strong> {scene.kinetic_contact_chain}</div>' if scene.kinetic_contact_chain else ''

        # CRAFT camera summary
        craft_summary = scene.craft_camera.to_summary() if scene.craft_camera else "35mm Studio Prime | Centered"

        # SVG plate for scene
        scene_plate_val = bundle.visual_plates.get(f"scene_{scene.scene_index}", "")
        if not scene_plate_val and scene.scene_index == 1:
            scene_plate_val = bundle.visual_plates.get("<image_3>", "")
        if not scene_plate_val and scene.scene_keyframe:
            scene_plate_val = scene.scene_keyframe.svg_markup or scene.scene_keyframe.image_path

        scene_plate_svg = _render_plate_html(scene_plate_val, alt=f"Scene {scene.scene_index} Keyframe")

        escaped_omni_prompt = scene.omni_prose_prompt.replace('`', "'").replace('"', '&quot;')

        scenes_html.append(f"""
        <div class="scene-card" id="scene-{scene.scene_index}">
          <div class="scene-header">
            <div class="scene-title-wrap">
              <span class="scene-badge">SCENE {scene.scene_index}</span>
              <h3 class="scene-title">{scene.scene_title}</h3>
              <span class="scene-time">{scene.timestamp_range}</span>
            </div>
            <div class="scene-actions">
              {audit_badge}
              <button class="btn-copy" onclick="copyPrompt('prompt-{scene.scene_index}')">Copy Omni Prompt</button>
            </div>
          </div>

          <div class="scene-body">
            <div class="scene-visual-col">
              <div class="scene-visual-frame">
                {scene_plate_svg}
              </div>
              <div class="camera-telemetry">
                <span class="craft-tag">CRAFT CAMERA</span> {craft_summary}
              </div>
            </div>

            <div class="scene-spec-col">
              <div class="beats-container">
                <div class="col-heading">ACTION BEATS (MAX 3 CAP)</div>
                {beats_html}
              </div>

              {chain_html}

              <div class="omni-prompt-box">
                <div class="col-heading">GEMINI OMNI 1.1 PROSE PROMPT (NO MARKDOWN HEADINGS)</div>
                <div class="prompt-text" id="prompt-{scene.scene_index}">{scene.omni_prose_prompt}</div>
              </div>

              {f'<div class="edit-deltas"><strong>Conversational Edit Deltas:</strong> {" | ".join(scene.conversational_edit_deltas)}</div>' if scene.conversational_edit_deltas else ''}
            </div>
          </div>
        </div>
        """)
    timeline_html = "\n".join(scenes_html)

    # Master BGM Sonic Card
    bgm = bible.master_bgm
    bgm_stems_html = "".join([f'<span class="meta-tag">{s}</span>' for s in bgm.instrumentation])
    escaped_lyria = bgm.lyria_prompt.replace('`', "'")

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{bible.project_title} | Omni Movie Director Cinema UI</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Space+Grotesk:wght@500;700&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg-base: #07080B;
      --bg-surface: #0E1017;
      --bg-card: #141722;
      --border-subtle: #202434;
      --border-focus: #3A425D;
      --cyan-telemetry: #00F0FF;
      --crimson-accent: #FF3366;
      --amber-gold: #FFB800;
      --text-main: #F0F2F8;
      --text-muted: #8E95AA;
      --text-dim: #545B73;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: var(--bg-base);
      color: var(--text-main);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      line-height: 1.5;
      padding-bottom: 80px;
    }}
    /* Top Cinema HUD */
    .hud-header {{
      background: rgba(14, 16, 23, 0.95);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--border-subtle);
      position: sticky;
      top: 0;
      z-index: 100;
      padding: 16px 36px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .hud-left {{ display: flex; align-items: center; gap: 20px; }}
    .project-title {{
      font-family: 'Space Grotesk', sans-serif;
      font-size: 19px;
      font-weight: 700;
      color: var(--text-main);
      letter-spacing: -0.02em;
    }}
    .hud-meta {{
      display: flex;
      gap: 12px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
    }}
    .meta-tag {{
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      padding: 4px 10px;
      border-radius: 4px;
      color: var(--text-muted);
    }}
    .meta-tag strong {{ color: var(--cyan-telemetry); }}
    .btn-theater {{
      background: var(--cyan-telemetry);
      color: #000;
      border: none;
      font-family: 'Space Grotesk', sans-serif;
      font-weight: 700;
      font-size: 12px;
      padding: 8px 16px;
      border-radius: 4px;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: opacity 0.2s;
    }}
    .btn-theater:hover {{ opacity: 0.9; }}

    .container {{
      max-width: 1440px;
      margin: 0 auto;
      padding: 36px;
    }}
    .section-title {{
      font-family: 'Space Grotesk', sans-serif;
      font-size: 13px;
      font-weight: 700;
      letter-spacing: 0.15em;
      text-transform: uppercase;
      color: var(--text-dim);
      margin: 32px 0 16px 0;
      display: flex;
      align-items: center;
      gap: 12px;
    }}
    .section-title::after {{
      content: "";
      flex: 1;
      height: 1px;
      background: var(--border-subtle);
    }}

    /* Overview Grid */
    .overview-grid {{
      display: grid;
      grid-template-columns: 2fr 1fr;
      gap: 24px;
      margin-bottom: 24px;
    }}
    .overview-card, .sonic-card {{
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: 8px;
      padding: 24px;
    }}
    .logline {{
      font-size: 16px;
      color: var(--text-main);
      line-height: 1.6;
      margin-bottom: 16px;
    }}
    .palette-strip {{
      display: flex;
      gap: 12px;
      margin-top: 12px;
    }}
    .swatch-box {{
      flex: 1;
      height: 52px;
      border-radius: 6px;
      border: 1px solid var(--border-subtle);
      display: flex;
      align-items: flex-end;
      padding: 6px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 10px;
      cursor: pointer;
      transition: transform 0.15s;
    }}
    .swatch-box:hover {{ transform: translateY(-2px); }}

    /* 3-Tier Visual Continuity Cards */
    .bible-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
      gap: 24px;
      margin-bottom: 32px;
    }}
    .bible-card {{
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: 8px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }}
    .bible-preview-wrap {{
      width: 100%;
      height: 250px;
      background: #000;
      position: relative;
      overflow: hidden;
    }}
    .plate-svg-container {{
      width: 100%;
      height: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    .plate-svg-container svg {{
      width: 100%;
      height: 100%;
      display: block;
    }}
    .bible-tag {{
      position: absolute;
      top: 12px;
      left: 12px;
      background: rgba(0, 240, 255, 0.2);
      border: 1px solid var(--cyan-telemetry);
      color: var(--cyan-telemetry);
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      font-weight: 700;
      padding: 2px 8px;
      border-radius: 4px;
      z-index: 10;
    }}
    .bible-content {{
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }}
    .bible-title {{
      font-family: 'Space Grotesk', sans-serif;
      font-size: 15px;
      font-weight: 700;
      color: var(--text-main);
    }}
    .bible-dna {{
      font-size: 12px;
      color: var(--text-muted);
      line-height: 1.4;
    }}
    .prompt-drawer {{
      margin-top: 6px;
      background: var(--bg-base);
      border: 1px solid var(--border-subtle);
      border-radius: 4px;
      overflow: hidden;
    }}
    .prompt-drawer-btn {{
      padding: 8px 12px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      color: var(--text-dim);
      cursor: pointer;
      list-style: none;
    }}
    .prompt-drawer-btn:hover {{ color: var(--cyan-telemetry); }}
    .prompt-drawer-content {{
      padding: 12px;
      border-top: 1px solid var(--border-subtle);
      background: #050608;
    }}
    .prompt-drawer-content pre {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      color: #A5B4FC;
      white-space: pre-wrap;
      word-break: break-word;
      line-height: 1.4;
      margin-bottom: 8px;
    }}

    /* Shot-by-Shot Timeline */
    .scene-card {{
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: 8px;
      margin-bottom: 24px;
      overflow: hidden;
    }}
    .scene-header {{
      background: var(--bg-card);
      border-bottom: 1px solid var(--border-subtle);
      padding: 14px 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .scene-title-wrap {{
      display: flex;
      align-items: center;
      gap: 14px;
    }}
    .scene-badge {{
      background: #1E2235;
      color: var(--cyan-telemetry);
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      font-weight: 700;
      padding: 3px 8px;
      border-radius: 4px;
    }}
    .scene-title {{
      font-family: 'Space Grotesk', sans-serif;
      font-size: 16px;
      font-weight: 700;
    }}
    .scene-time {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      color: var(--text-dim);
    }}
    .scene-actions {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}
    .badge-pass {{
      background: rgba(16, 185, 129, 0.15);
      border: 1px solid #10B981;
      color: #10B981;
      font-family: 'JetBrains Mono', monospace;
      font-size: 10px;
      font-weight: 700;
      padding: 3px 8px;
      border-radius: 4px;
    }}
    .btn-copy {{
      background: transparent;
      border: 1px solid var(--cyan-telemetry);
      color: var(--cyan-telemetry);
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      padding: 6px 14px;
      border-radius: 4px;
      cursor: pointer;
      transition: background 0.15s;
    }}
    .btn-copy:hover {{ background: rgba(0, 240, 255, 0.15); }}
    .btn-copy-sm {{
      background: #1A1F2C;
      border: 1px solid var(--border-subtle);
      color: var(--text-main);
      font-family: 'JetBrains Mono', monospace;
      font-size: 10px;
      padding: 4px 10px;
      border-radius: 4px;
      cursor: pointer;
    }}
    .btn-copy-sm:hover {{ border-color: var(--cyan-telemetry); }}

    .scene-body {{
      display: grid;
      grid-template-columns: 480px 1fr;
      min-height: 270px;
    }}
    .scene-visual-col {{
      background: #000;
      border-right: 1px solid var(--border-subtle);
      display: flex;
      flex-direction: column;
    }}
    .scene-visual-frame {{
      width: 100%;
      height: 270px;
      display: flex;
      align-items: center;
      justify-content: center;
      overflow: hidden;
      background: #050508;
    }}
    .scene-visual-frame svg {{
      width: 100%;
      height: 100%;
      display: block;
    }}
    .camera-telemetry {{
      background: #0A0C12;
      border-top: 1px solid var(--border-subtle);
      padding: 8px 16px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      color: var(--text-muted);
    }}
    .craft-tag {{
      color: var(--amber-gold);
      font-weight: 700;
      margin-right: 6px;
    }}

    .scene-spec-col {{
      padding: 20px 24px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }}
    .col-heading {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 0.1em;
      color: var(--text-dim);
      margin-bottom: 6px;
      text-transform: uppercase;
    }}
    .beats-container {{
      display: flex;
      flex-direction: column;
      gap: 6px;
    }}
    .beat-item {{
      background: var(--bg-card);
      border-left: 3px solid var(--cyan-telemetry);
      padding: 6px 12px;
      font-size: 12px;
      border-radius: 0 4px 4px 0;
    }}
    .beat-num {{
      font-family: 'JetBrains Mono', monospace;
      font-weight: 700;
      color: var(--cyan-telemetry);
      margin-right: 8px;
    }}
    .chain-box {{
      background: #121017;
      border: 1px solid rgba(255, 51, 102, 0.3);
      border-left: 3px solid var(--crimson-accent);
      padding: 8px 12px;
      font-size: 12px;
      color: #FDA4AF;
      border-radius: 0 4px 4px 0;
    }}
    .omni-prompt-box {{
      background: #0A0C12;
      border: 1px solid var(--border-subtle);
      border-radius: 6px;
      padding: 12px;
    }}
    .prompt-text {{
      font-size: 13px;
      line-height: 1.6;
      color: #CBD5E1;
      user-select: text;
    }}
    .edit-deltas {{
      margin-top: 12px;
      font-size: 12px;
      color: var(--text-muted);
      font-family: 'JetBrains Mono', monospace;
    }}
    .svg-placeholder {{
      color: var(--text-dim);
      font-family: 'JetBrains Mono', monospace;
      font-size: 12px;
      padding: 20px;
      text-align: center;
    }}
  </style>
</head>
<body>

  <!-- Top Cinema HUD -->
  <header class="hud-header">
    <div class="hud-left">
      <div class="project-title">{bible.project_title}</div>
      <div class="hud-meta">
        <span class="meta-tag">CANVAS: <strong>{bible.aspect_ratio.value}</strong></span>
        <span class="meta-tag">REGIME: <strong>{bible.creative_regime.value.split(':')[0]}</strong></span>
        <span class="meta-tag">RUNTIME: <strong>{bible.total_runtime_seconds}s</strong></span>
        <span class="meta-tag">MODE: <strong>{bible.storytelling_mode.value.split(':')[0]}</strong></span>
      </div>
    </div>
    <button class="btn-theater" onclick="window.scrollTo({{ top: document.getElementById('timeline-section').offsetTop - 80, behavior: 'smooth' }})">
      ▶ STORYBOARD TIMELINE
    </button>
  </header>

  <div class="container">
    <!-- Overview & Palette -->
    <div class="overview-grid">
      <div class="overview-card">
        <div class="col-heading">DIRECTOR'S LOGLINE</div>
        <div class="logline">{bible.logline}</div>
        <div class="col-heading">COLOR SCRIPT PALETTE (CLICK HEX TO COPY)</div>
        <div class="palette-strip">{swatches_html}</div>
      </div>

      <div class="sonic-card">
        <div class="col-heading">MASTER BGM BLUEPRINT</div>
        <div style="font-family: 'Space Grotesk', sans-serif; font-size: 15px; font-weight: 700; margin-bottom: 6px;">
          {bgm.track_title}
        </div>
        <div style="font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--cyan-telemetry); margin-bottom: 12px;">
          {bgm.tempo_bpm} BPM | {bgm.key_signature} | {bgm.genre_style}
        </div>
        <div style="display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px;">
          {bgm_stems_html}
        </div>
        <button class="btn-copy-sm" onclick="navigator.clipboard.writeText(`{escaped_lyria}`); this.innerText = 'Copied Lyria Prompt!'; setTimeout(() => this.innerText = 'Copy Lyria Prompt', 2000)">
          Copy Lyria BGM Prompt
        </button>
      </div>
    </div>

    <!-- 3-Tier Visual Continuity Bible -->
    <div class="section-title">3-TIER VISUAL CONTINUITY BIBLE (NANO BANANA PRO PRE-VIS)</div>
    <div class="bible-grid">
      {continuity_grid_html}
    </div>

    <!-- Shot-by-Shot Timeline -->
    <div class="section-title" id="timeline-section">SHOT-BY-SHOT TIMELINE ({len(bible.scenes)} SEQUENTIAL CUTS)</div>
    {timeline_html}
  </div>

  <script>
    function copyPrompt(elementId) {{
      const text = document.getElementById(elementId).innerText;
      navigator.clipboard.writeText(text).then(() => {{
        alert("Omni 1.1 Natural Prose Prompt copied to clipboard!");
      }});
    }}
    function copyText(btn, text) {{
      navigator.clipboard.writeText(text).then(() => {{
        btn.innerText = "Copied!";
        setTimeout(() => btn.innerText = "Copy Prompt", 2000);
      }});
    }}
  </script>
</body>
</html>"""

    html_file = output_dir / "storyboard_preview.html"
    html_file.write_text(html_content, encoding="utf-8")
    bundle.storyboard_html_path = str(html_file)
    return html_file
