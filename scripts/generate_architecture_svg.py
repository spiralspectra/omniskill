"""Script to generate the Nano Banana Architecture Diagram SVG."""

from pathlib import Path

def generate_svg() -> str:
    return '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 1060" width="100%" height="100%">
  <defs>
    <!-- Background Gradients -->
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#07080D"/>
      <stop offset="50%" stop-color="#0B0D14"/>
      <stop offset="100%" stop-color="#05060A"/>
    </linearGradient>

    <!-- Card Background Gradient -->
    <linearGradient id="cardBg" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#141724" stop-opacity="0.95"/>
      <stop offset="100%" stop-color="#0E1019" stop-opacity="0.98"/>
    </linearGradient>

    <linearGradient id="ssotCardBg" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#1B1728" stop-opacity="0.95"/>
      <stop offset="100%" stop-color="#100E19" stop-opacity="0.98"/>
    </linearGradient>

    <!-- Accent Gradients -->
    <linearGradient id="cyanNeon" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#00F0FF"/>
      <stop offset="100%" stop-color="#3B82F6"/>
    </linearGradient>

    <linearGradient id="crimsonNeon" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#FF4B4B"/>
      <stop offset="100%" stop-color="#EC4899"/>
    </linearGradient>

    <linearGradient id="purpleNeon" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#A855F7"/>
      <stop offset="100%" stop-color="#6366F1"/>
    </linearGradient>

    <linearGradient id="amberNeon" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#F59E0B"/>
      <stop offset="100%" stop-color="#EAB308"/>
    </linearGradient>

    <linearGradient id="emeraldNeon" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#10B981"/>
      <stop offset="100%" stop-color="#059669"/>
    </linearGradient>

    <!-- Glow & Shadow Filters -->
    <filter id="glowCyan" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="6" result="blur"/>
      <feComposite in="SourceGraphic" in2="blur" operator="over"/>
    </filter>

    <filter id="glowPurple" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="6" result="blur"/>
      <feComposite in="SourceGraphic" in2="blur" operator="over"/>
    </filter>

    <filter id="cardShadow" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="8" stdDeviation="10" flood-color="#000000" flood-opacity="0.6"/>
    </filter>

    <!-- Grid Pattern -->
    <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
      <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#191B26" stroke-width="0.75" stroke-opacity="0.6"/>
    </pattern>

    <!-- Arrow Marker -->
    <marker id="arrow" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 8 5 L 0 9 z" fill="#00F0FF" />
    </marker>
    <marker id="arrowPurple" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 8 5 L 0 9 z" fill="#A855F7" />
    </marker>
    <marker id="arrowAmber" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 8 5 L 0 9 z" fill="#F59E0B" />
    </marker>
  </defs>

  <style>
    .title { font-family: 'Space Grotesk', system-ui, -apple-system, sans-serif; font-weight: 700; }
    .mono { font-family: 'JetBrains Mono', 'Fira Code', monospace; }
    .body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }
    .badge { font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 600; letter-spacing: 0.5px; }
  </style>

  <!-- Background Canvas -->
  <rect width="1600" height="1060" fill="url(#bgGrad)"/>
  <rect width="1600" height="1060" fill="url(#grid)"/>

  <!-- ==================== TOP CINEMA HUD HEADER ==================== -->
  <g transform="translate(40, 24)">
    <rect width="1520" height="84" rx="12" fill="#0E1018" stroke="#252838" stroke-width="1.5" filter="url(#cardShadow)"/>
    <rect x="0" y="0" width="1520" height="3" fill="url(#cyanNeon)" rx="1.5"/>

    <!-- Left Brand Title -->
    <text x="28" y="38" class="title" font-size="22" fill="#FFFFFF" letter-spacing="1.5">
      OMNI MOVIE DIRECTOR <tspan fill="#00F0FF">2.1.0</tspan>
    </text>
    <text x="28" y="62" class="mono" font-size="12" fill="#7E849E" letter-spacing="1">
      ADK 2.0 MULTI-AGENT ARCHITECTURE • 2026 DEEPMIND MODEL MATRIX • NANO BANANA PRO
    </text>

    <!-- Center Metric Pills -->
    <g transform="translate(680, 26)">
      <rect width="135" height="32" rx="6" fill="#141826" stroke="#00F0FF" stroke-width="1" stroke-opacity="0.4"/>
      <circle cx="16" cy="16" r="4" fill="#00F0FF" filter="url(#glowCyan)"/>
      <text x="28" y="20" class="badge" fill="#00F0FF">24 FPS SMPTE</text>

      <g transform="translate(145, 0)">
        <rect width="145" height="32" rx="6" fill="#181426" stroke="#A855F7" stroke-width="1" stroke-opacity="0.4"/>
        <circle cx="16" cy="16" r="4" fill="#A855F7" filter="url(#glowPurple)"/>
        <text x="28" y="20" class="badge" fill="#D8B4FE">COUNCIL: 100/100</text>
      </g>

      <g transform="translate(300, 0)">
        <rect width="130" height="32" rx="6" fill="#15201A" stroke="#10B981" stroke-width="1" stroke-opacity="0.4"/>
        <circle cx="16" cy="16" r="4" fill="#10B981"/>
        <text x="28" y="20" class="badge" fill="#6EE7B7">ZERO LEGACY 3.1</text>
      </g>
    </g>

    <!-- Right Mode Badge -->
    <rect x="1350" y="26" width="142" height="32" rx="6" fill="#1E1928" stroke="#EC4899" stroke-width="1" stroke-opacity="0.5"/>
    <text x="1421" y="47" class="badge" fill="#F472B6" text-anchor="middle">MODE A + MODE B</text>
  </g>

  <!-- ==================== COLUMN 1: INTAKE & CREATIVE DIRECTION (SSOT) ==================== -->
  <!-- Stage 0: FDE Preflight Doctor -->
  <g transform="translate(40, 130)">
    <rect width="345" height="185" rx="10" fill="url(#cardBg)" stroke="#262A3C" stroke-width="1.2" filter="url(#cardShadow)"/>
    <rect x="0" y="0" width="345" height="3" fill="url(#cyanNeon)" rx="1.5"/>
    
    <text x="20" y="28" class="title" font-size="14" fill="#00F0FF" letter-spacing="1">STAGE 0: PREFLIGHT DOCTOR</text>
    <text x="20" y="46" class="mono" font-size="11" fill="#7E849E">omni_director.doctor.run_doctor()</text>

    <!-- Checklist Items -->
    <g transform="translate(20, 68)" class="mono" font-size="11" fill="#C5C9D8">
      <circle cx="6" cy="6" r="3.5" fill="#10B981"/>
      <text x="18" y="10">Python &gt;= 3.11 Runtime Verified</text>
      
      <circle cx="6" cy="28" r="3.5" fill="#10B981"/>
      <text x="18" y="32">Pydantic v2.7+ Contract Layer</text>

      <circle cx="6" cy="50" r="3.5" fill="#10B981"/>
      <text x="18" y="54">2026 Model Whitelist Enforced</text>

      <circle cx="6" cy="72" r="3.5" fill="#10B981"/>
      <text x="18" y="76">Filesystem &amp; Telemetry Permissions</text>
    </g>

    <rect x="20" y="152" width="305" height="22" rx="4" fill="#0A2218" stroke="#10B981" stroke-width="0.8"/>
    <text x="172" y="167" class="badge" fill="#34D399" text-anchor="middle">EXIT 0: PREFLIGHT READY</text>
  </g>

  <!-- Stage 1: Intake & Domain Classifier -->
  <g transform="translate(40, 335)">
    <rect width="345" height="205" rx="10" fill="url(#cardBg)" stroke="#262A3C" stroke-width="1.2" filter="url(#cardShadow)"/>
    <rect x="0" y="0" width="345" height="3" fill="url(#purpleNeon)" rx="1.5"/>

    <text x="20" y="28" class="title" font-size="14" fill="#C084FC" letter-spacing="1">STAGE 1: INTAKE &amp; RESEARCH</text>
    <text x="20" y="46" class="mono" font-size="11" fill="#7E849E">classify_brief_domain()</text>

    <text x="20" y="72" class="body" font-size="12" fill="#9CA3AF">6 Commercial Domain Archetypes:</text>

    <!-- Archetype Badges -->
    <g transform="translate(20, 84)" class="badge">
      <rect width="145" height="22" rx="4" fill="#181928" stroke="#373B52" stroke-width="1"/>
      <text x="72" y="15" fill="#E2E8F0" text-anchor="middle">automotive_robotics</text>

      <rect x="155" width="145" height="22" rx="4" fill="#181928" stroke="#373B52" stroke-width="1"/>
      <text x="227" y="15" fill="#E2E8F0" text-anchor="middle">culinary_asmr</text>

      <rect y="28" width="145" height="22" rx="4" fill="#181928" stroke="#373B52" stroke-width="1"/>
      <text x="72" y="43" fill="#E2E8F0" text-anchor="middle">luxury_fashion</text>

      <rect x="155" y="28" width="145" height="22" rx="4" fill="#181928" stroke="#373B52" stroke-width="1"/>
      <text x="227" y="43" fill="#E2E8F0" text-anchor="middle">kinetic_action</text>

      <rect y="56" width="145" height="22" rx="4" fill="#181928" stroke="#373B52" stroke-width="1"/>
      <text x="72" y="71" fill="#E2E8F0" text-anchor="middle">tech_hardware</text>

      <rect x="155" y="56" width="145" height="22" rx="4" fill="#181928" stroke="#373B52" stroke-width="1"/>
      <text x="227" y="71" fill="#E2E8F0" text-anchor="middle">architectural_sanctuary</text>
    </g>

    <text x="20" y="190" class="mono" font-size="10" fill="#6EE7B7">✓ Deterministic Tie-Breaking &amp; Auto-DNA</text>
  </g>

  <!-- Stage 2: Creative Director (SSOT) -->
  <g transform="translate(40, 560)">
    <rect width="345" height="355" rx="10" fill="url(#ssotCardBg)" stroke="#8B5CF6" stroke-width="1.5" filter="url(#cardShadow)"/>
    <rect x="0" y="0" width="345" height="3" fill="url(#purpleNeon)" rx="1.5"/>

    <g transform="translate(20, 20)">
      <rect width="135" height="20" rx="4" fill="#2E1B4E" stroke="#8B5CF6" stroke-width="1"/>
      <text x="67" y="14" class="badge" fill="#D8B4FE" text-anchor="middle">LEAD DIRECTOR</text>
      
      <text x="145" y="15" class="mono" font-size="12" font-weight="700" fill="#00F0FF">gemini-4-argon</text>
    </g>

    <text x="20" y="65" class="title" font-size="16" fill="#FFFFFF">Stage 2: Single Source of Truth</text>
    <text x="20" y="85" class="mono" font-size="12" fill="#A78BFA">MasterProductionBible (Sealed SSOT)</text>

    <!-- Master Bible Spec Box -->
    <rect x="20" y="102" width="305" height="200" rx="8" fill="#0D0B14" stroke="#3B2D54" stroke-width="1"/>
    
    <g transform="translate(32, 122)" class="mono" font-size="11" fill="#DDD6FE">
      <text x="0" y="0" fill="#C084FC" font-weight="700">MASTER BIBLE INVARIANTS:</text>
      <text x="0" y="22" fill="#E2E8F0">• Regime 1: High-Speed Tracking</text>
      <text x="0" y="42" fill="#E2E8F0">• Regime 2: 1.0x Real-Time Speed Lock</text>
      <text x="0" y="64" fill="#E2E8F0">• 3-Tier Visual Continuity Anchors</text>
      <text x="0" y="84" fill="#E2E8F0">• Wardrobe Polarity Separation</text>
      <text x="0" y="104" fill="#E2E8F0">• Strict 40s Continuous Ceiling</text>
      <text x="0" y="126" fill="#E2E8F0">• Synchronized BGM Directive</text>
      <text x="0" y="148" fill="#E2E8F0">• Negative Constraint Ban</text>
      <text x="0" y="168" fill="#34D399">✓ Immutable Downstream Contract</text>
    </g>

    <rect x="20" y="314" width="305" height="26" rx="4" fill="#1C152B" stroke="#A855F7" stroke-width="1"/>
    <text x="172" y="331" class="badge" fill="#F3E8FF" text-anchor="middle">ENFORCED ACROSS ALL STAGES</text>
  </g>

  <!-- ==================== COLUMN 2: NANO BANANA & PARALLEL WORKHORSE ==================== -->
  <!-- Stage 3: Visual Storyboard Agent (Nano Banana Pro) -->
  <g transform="translate(425, 130)">
    <rect width="355" height="390" rx="10" fill="url(#cardBg)" stroke="#262A3C" stroke-width="1.2" filter="url(#cardShadow)"/>
    <rect x="0" y="0" width="355" height="3" fill="url(#amberNeon)" rx="1.5"/>

    <g transform="translate(20, 20)">
      <rect width="140" height="20" rx="4" fill="#2C1D0E" stroke="#F59E0B" stroke-width="1"/>
      <text x="70" y="14" class="badge" fill="#FCD34D" text-anchor="middle">CONCEPT &amp; PLATES</text>
      
      <text x="150" y="15" class="mono" font-size="12" font-weight="700" fill="#F59E0B">gemini-3-pro-image</text>
    </g>

    <text x="20" y="65" class="title" font-size="16" fill="#FFFFFF">Stage 3: Visual Storyboard Agent</text>
    <text x="20" y="85" class="mono" font-size="12" fill="#FBBF24">Nano Banana Pro SVG Vector Engine</text>

    <!-- Visual Anchor Plates Graphic -->
    <g transform="translate(20, 102)">
      <!-- Anchor 1 -->
      <rect width="315" height="68" rx="6" fill="#12141F" stroke="#2D324A" stroke-width="1"/>
      <rect x="8" y="8" width="52" height="52" rx="4" fill="#1A1C2C" stroke="#00F0FF" stroke-width="1"/>
      <!-- Miniature Figure Icon -->
      <circle cx="34" cy="24" r="8" fill="none" stroke="#00F0FF" stroke-width="1.5"/>
      <path d="M 22 52 L 28 36 L 40 36 L 46 52" stroke="#00F0FF" stroke-width="1.5" fill="none"/>
      
      <text x="68" y="26" class="title" font-size="12" fill="#E2E8F0">ANCHOR 1: Character Turnaround</text>
      <text x="68" y="44" class="mono" font-size="10" fill="#94A3B8">&lt;image_1&gt; • DNA, Silhouette, Wardrobe</text>
      <text x="68" y="58" class="badge" font-size="9" fill="#00F0FF">3-PANEL ORTHOGRAPHIC VECTOR</text>

      <!-- Anchor 2 -->
      <g transform="translate(0, 78)">
        <rect width="315" height="68" rx="6" fill="#12141F" stroke="#2D324A" stroke-width="1"/>
        <rect x="8" y="8" width="52" height="52" rx="4" fill="#1A1C2C" stroke="#F59E0B" stroke-width="1"/>
        <!-- Miniature Architecture Icon -->
        <rect x="18" y="22" width="32" height="30" fill="none" stroke="#F59E0B" stroke-width="1.5"/>
        <line x1="14" y1="22" x2="54" y2="22" stroke="#F59E0B" stroke-width="1.5"/>
        <line x1="34" y1="12" x2="34" y2="22" stroke="#F59E0B" stroke-width="1.5"/>

        <text x="68" y="26" class="title" font-size="12" fill="#E2E8F0">ANCHOR 2: Master Environment Plate</text>
        <text x="68" y="44" class="mono" font-size="10" fill="#94A3B8">&lt;image_2&gt; • Spatial Geography &amp; Lighting</text>
        <text x="68" y="58" class="badge" font-size="9" fill="#F59E0B">GRID &amp; ARCHITECTURAL CADENCE</text>
      </g>

      <!-- Anchor 3 -->
      <g transform="translate(0, 156)">
        <rect width="315" height="68" rx="6" fill="#12141F" stroke="#2D324A" stroke-width="1"/>
        <rect x="8" y="8" width="52" height="52" rx="4" fill="#1A1C2C" stroke="#A855F7" stroke-width="1"/>
        <!-- Miniature Camera Keyframe Icon -->
        <circle cx="34" cy="34" r="14" fill="none" stroke="#A855F7" stroke-width="1.5"/>
        <circle cx="34" cy="34" r="5" fill="#A855F7"/>

        <text x="68" y="26" class="title" font-size="12" fill="#E2E8F0">ANCHOR 3: Scene Keyframes</text>
        <text x="68" y="44" class="mono" font-size="10" fill="#94A3B8">&lt;image_3&gt; • Lighting, Composition, Rig</text>
        <text x="68" y="58" class="badge" font-size="9" fill="#C084FC">16:9 • 9:16 • 1:1 • 2.39:1 CANVAS</text>
      </g>
    </g>

    <rect x="20" y="344" width="315" height="26" rx="4" fill="#1B1713" stroke="#F59E0B" stroke-width="0.8"/>
    <text x="177" y="361" class="badge" fill="#FCD34D" text-anchor="middle">OFFLINE ZERO-CREDIT VECTOR EMULATION</text>
  </g>

  <!-- Stage 4: Parallel Fan-Out (Workhorse) -->
  <g transform="translate(425, 540)">
    <rect width="355" height="375" rx="10" fill="url(#cardBg)" stroke="#262A3C" stroke-width="1.2" filter="url(#cardShadow)"/>
    <rect x="0" y="0" width="355" height="3" fill="url(#cyanNeon)" rx="1.5"/>

    <g transform="translate(20, 20)">
      <rect width="135" height="20" rx="4" fill="#0A242E" stroke="#00F0FF" stroke-width="1"/>
      <text x="67" y="14" class="badge" fill="#67E8F9" text-anchor="middle">FAST WORKHORSE</text>
      
      <text x="145" y="15" class="mono" font-size="12" font-weight="700" fill="#00F0FF">gemini-3.8-flash</text>
    </g>

    <text x="20" y="65" class="title" font-size="16" fill="#FFFFFF">Stage 4: Parallel Fan-Out</text>
    <text x="20" y="85" class="mono" font-size="12" fill="#38BDF8">ParallelScenePromptAgent &amp; BGM</text>

    <!-- Fan-out Sub-agents -->
    <g transform="translate(20, 102)">
      <rect width="315" height="42" rx="6" fill="#10131F" stroke="#252A42" stroke-width="1"/>
      <text x="14" y="22" class="title" font-size="12" fill="#E2E8F0">Scene 1: CRAFT Grammar</text>
      <text x="14" y="34" class="mono" font-size="10" fill="#94A3B8">Lens, Angle, Movement, Framing, Motion</text>
      <circle cx="295" cy="21" r="5" fill="#00F0FF"/>

      <g transform="translate(0, 48)">
        <rect width="315" height="42" rx="6" fill="#10131F" stroke="#252A42" stroke-width="1"/>
        <text x="14" y="22" class="title" font-size="12" fill="#E2E8F0">Scene 2: 5-Stage Contact Chain</text>
        <text x="14" y="34" class="mono" font-size="10" fill="#94A3B8">Anticipate → Accelerate → Impact → Settle</text>
        <circle cx="295" cy="21" r="5" fill="#00F0FF"/>
      </g>

      <g transform="translate(0, 96)">
        <rect width="315" height="42" rx="6" fill="#10131F" stroke="#252A42" stroke-width="1"/>
        <text x="14" y="22" class="title" font-size="12" fill="#E2E8F0">Scene 3: Diegetic Foley &amp; Acoustics</text>
        <text x="14" y="34" class="mono" font-size="10" fill="#94A3B8">Tactile textures, reverb, frequency balance</text>
        <circle cx="295" cy="21" r="5" fill="#00F0FF"/>
      </g>

      <g transform="translate(0, 144)">
        <rect width="315" height="42" rx="6" fill="#10131F" stroke="#252A42" stroke-width="1"/>
        <text x="14" y="22" class="title" font-size="12" fill="#E2E8F0">Scene 4: Boundary &amp; Speed Lock</text>
        <text x="14" y="34" class="mono" font-size="10" fill="#94A3B8">1.0x real-time lock &amp; +10s continuity</text>
        <circle cx="295" cy="21" r="5" fill="#00F0FF"/>
      </g>

      <g transform="translate(0, 192)">
        <rect width="315" height="46" rx="6" fill="#191326" stroke="#5B21B6" stroke-width="1"/>
        <text x="14" y="22" class="title" font-size="12" fill="#D8B4FE">BGMComposerAgent</text>
        <text x="14" y="36" class="mono" font-size="10" fill="#C084FC">Lyria prompt, BPM, Musical Key, 4 Stems</text>
        <circle cx="295" cy="23" r="5" fill="#A855F7"/>
      </g>
    </g>

    <text x="20" y="360" class="mono" font-size="11" fill="#38BDF8">⚡ High-Throughput Async Execution</text>
  </g>

  <!-- ==================== COLUMN 3: 7-POINT AUDITOR & VIDEO ENGINE ==================== -->
  <!-- Stage 5: 7-Point Omni Prompt Auditor & Healer -->
  <g transform="translate(810, 130)">
    <rect width="365" height="465" rx="10" fill="url(#cardBg)" stroke="#262A3C" stroke-width="1.2" filter="url(#cardShadow)"/>
    <rect x="0" y="0" width="365" height="3" fill="url(#crimsonNeon)" rx="1.5"/>

    <g transform="translate(20, 20)">
      <rect width="140" height="20" rx="4" fill="#2E0E18" stroke="#FF4B4B" stroke-width="1"/>
      <text x="70" y="14" class="badge" fill="#FCA5A5" text-anchor="middle">QUALITY GOVERNANCE</text>
      
      <text x="150" y="15" class="mono" font-size="12" font-weight="700" fill="#FF4B4B">heal_omni_prompt()</text>
    </g>

    <text x="20" y="65" class="title" font-size="16" fill="#FFFFFF">Stage 5: 7-Point Prompt Auditor</text>
    <text x="20" y="85" class="mono" font-size="12" fill="#F87171">Self-Healing Loop (Max 3 Iterations)</text>

    <!-- 7 Rules Table -->
    <g transform="translate(20, 104)" class="mono" font-size="11">
      <rect width="325" height="34" rx="5" fill="#12131F" stroke="#252A42" stroke-width="0.8"/>
      <text x="12" y="21" fill="#E2E8F0">1. No Markdown / HTML Headings</text>
      <text x="290" y="21" fill="#34D399" font-weight="700">HEAL</text>

      <g transform="translate(0, 40)">
        <rect width="325" height="34" rx="5" fill="#12131F" stroke="#252A42" stroke-width="0.8"/>
        <text x="12" y="21" fill="#E2E8F0">2. Continuous Natural Prose</text>
        <text x="290" y="21" fill="#34D399" font-weight="700">HEAL</text>
      </g>

      <g transform="translate(0, 80)">
        <rect width="325" height="34" rx="5" fill="#12131F" stroke="#252A42" stroke-width="0.8"/>
        <text x="12" y="21" fill="#E2E8F0">3. Regime 2: 1.0x Real-Time Lock</text>
        <text x="290" y="21" fill="#34D399" font-weight="700">LOCK</text>
      </g>

      <g transform="translate(0, 120)">
        <rect width="325" height="34" rx="5" fill="#12131F" stroke="#252A42" stroke-width="0.8"/>
        <text x="12" y="21" fill="#E2E8F0">4. 5-Stage Contact Physics</text>
        <text x="290" y="21" fill="#34D399" font-weight="700">HEAL</text>
      </g>

      <g transform="translate(0, 160)">
        <rect width="325" height="34" rx="5" fill="#12131F" stroke="#252A42" stroke-width="0.8"/>
        <text x="12" y="21" fill="#E2E8F0">5. Maximum 3 Image References</text>
        <text x="290" y="21" fill="#34D399" font-weight="700">TRIM</text>
      </g>

      <g transform="translate(0, 200)">
        <rect width="325" height="34" rx="5" fill="#12131F" stroke="#252A42" stroke-width="0.8"/>
        <text x="12" y="21" fill="#E2E8F0">6. Synchronized Diegetic Audio</text>
        <text x="290" y="21" fill="#34D399" font-weight="700">FUSE</text>
      </g>

      <g transform="translate(0, 240)">
        <rect width="325" height="34" rx="5" fill="#12131F" stroke="#252A42" stroke-width="0.8"/>
        <text x="12" y="21" fill="#E2E8F0">7. Audio Continuity &amp; Stems</text>
        <text x="290" y="21" fill="#34D399" font-weight="700">SYNC</text>
      </g>
    </g>

    <!-- Healing Loop Convergence Box -->
    <rect x="20" y="394" width="325" height="52" rx="6" fill="#1C1016" stroke="#991B1B" stroke-width="1"/>
    <text x="32" y="416" class="title" font-size="12" fill="#FCA5A5">SELF-HEALING CONVERGENCE</text>
    <text x="32" y="434" class="mono" font-size="10" fill="#FECACA">Scores &lt; 90.0 trigger automated prompt surgery</text>
  </g>

  <!-- Stage 6: Video Generation Engine -->
  <g transform="translate(810, 615)">
    <rect width="365" height="300" rx="10" fill="url(#cardBg)" stroke="#262A3C" stroke-width="1.2" filter="url(#cardShadow)"/>
    <rect x="0" y="0" width="365" height="3" fill="url(#cyanNeon)" rx="1.5"/>

    <text x="20" y="28" class="title" font-size="14" fill="#38BDF8" letter-spacing="1">STAGE 6: DUAL VIDEO ENGINE</text>
    <text x="20" y="46" class="mono" font-size="11" fill="#7E849E">Zero-Video-Before-Storyboard Invariant</text>

    <!-- Branch A: Live -->
    <g transform="translate(20, 65)">
      <rect width="325" height="98" rx="6" fill="#0C1B24" stroke="#0284C7" stroke-width="1"/>
      <g transform="translate(14, 12)">
        <rect width="70" height="18" rx="3" fill="#0369A1"/>
        <text x="35" y="13" class="badge" fill="#E0F2FE" text-anchor="middle">LIVE ENGINE</text>
        <text x="80" y="14" class="mono" font-size="11" font-weight="700" fill="#38BDF8">gemini-omni-1.1-flash</text>
        <text x="0" y="38" class="body" font-size="11" fill="#BAE6FD">720p / 24fps cinema video synthesis</text>
        <text x="0" y="54" class="body" font-size="11" fill="#BAE6FD">Native synchronized diegetic audio stream</text>
        <text x="0" y="70" class="mono" font-size="10" fill="#38BDF8">Requires explicit --render-video flag</text>
      </g>
    </g>

    <!-- Branch B: Dry-run -->
    <g transform="translate(20, 175)">
      <rect width="325" height="98" rx="6" fill="#121815" stroke="#059669" stroke-width="1"/>
      <g transform="translate(14, 12)">
        <rect width="105" height="18" rx="3" fill="#047857"/>
        <text x="52" y="13" class="badge" fill="#D1FAE5" text-anchor="middle">OFFLINE DRY-RUN</text>
        <text x="115" y="14" class="mono" font-size="11" font-weight="700" fill="#34D399">Zero-Credit Mode</text>
        <text x="0" y="38" class="body" font-size="11" fill="#A7F3D0">Nano Banana SVG plates &amp; video containers</text>
        <text x="0" y="54" class="body" font-size="11" fill="#A7F3D0">Deterministic local verification with zero cost</text>
        <text x="0" y="70" class="mono" font-size="10" fill="#34D399">Default execution in tests and CI</text>
      </g>
    </g>
  </g>

  <!-- ==================== COLUMN 4: STORYBOARD MONITOR & PRODUCT COUNCIL ==================== -->
  <!-- Stage 7: Dark-Room Cinema HTML5 Animatic -->
  <g transform="translate(1195, 130)">
    <rect width="365" height="390" rx="10" fill="url(#cardBg)" stroke="#262A3C" stroke-width="1.2" filter="url(#cardShadow)"/>
    <rect x="0" y="0" width="365" height="3" fill="url(#cyanNeon)" rx="1.5"/>

    <g transform="translate(20, 20)">
      <rect width="135" height="20" rx="4" fill="#0E232E" stroke="#06B6D4" stroke-width="1"/>
      <text x="67" y="14" class="badge" fill="#A5F3FC" text-anchor="middle">ANIMATIC MONITOR</text>
      
      <text x="145" y="15" class="mono" font-size="12" font-weight="700" fill="#22D3EE">24fps SMPTE</text>
    </g>

    <text x="20" y="65" class="title" font-size="16" fill="#FFFFFF">Stage 7: Storyboard HTML Compiler</text>
    <text x="20" y="85" class="mono" font-size="12" fill="#67E8F9">Dark-Room Cinema HTML5 &amp; Production Bundle</text>

    <!-- Monitor Features List -->
    <g transform="translate(20, 104)" class="mono" font-size="11" fill="#CFFAFE">
      <rect width="325" height="42" rx="5" fill="#0C151D" stroke="#164E63" stroke-width="0.8"/>
      <text x="12" y="20" fill="#E0F2FE" font-weight="600">SMPTE Timecode Engine</text>
      <text x="12" y="34" fill="#7DD3FC" font-size="10">HH:MM:SS:FF at 24fps with scrubber sync</text>

      <g transform="translate(0, 50)">
        <rect width="325" height="42" rx="5" fill="#0C151D" stroke="#164E63" stroke-width="0.8"/>
        <text x="12" y="20" fill="#E0F2FE" font-weight="600">Dynamic Beat &amp; Audio Rows</text>
        <text x="12" y="34" fill="#7DD3FC" font-size="10">Tactile foley badges &amp; stem visualizers</text>
      </g>

      <g transform="translate(0, 100)">
        <rect width="325" height="42" rx="5" fill="#0C151D" stroke="#164E63" stroke-width="0.8"/>
        <text x="12" y="20" fill="#E0F2FE" font-weight="600">Safe Action &amp; Title Guides [G]</text>
        <text x="12" y="34" fill="#7DD3FC" font-size="10">90% Action / 80% Title framing overlays</text>
      </g>

      <g transform="translate(0, 150)">
        <rect width="325" height="42" rx="5" fill="#0C151D" stroke="#164E63" stroke-width="0.8"/>
        <text x="12" y="20" fill="#E0F2FE" font-weight="600">6-Category Audit Drawers</text>
        <text x="12" y="34" fill="#7DD3FC" font-size="10">Expandable 7-point diagnostic cards</text>
      </g>

      <g transform="translate(0, 200)">
        <rect width="325" height="42" rx="5" fill="#0C151D" stroke="#164E63" stroke-width="0.8"/>
        <text x="12" y="20" fill="#E0F2FE" font-weight="600">WCAG 2.2 AA &amp; Keyboard Controls</text>
        <text x="12" y="34" fill="#7DD3FC" font-size="10">Spacebar play/pause, [J][K][L], non-blocking</text>
      </g>
    </g>

    <!-- Bundle Output Badges -->
    <g transform="translate(20, 356)" class="badge" font-size="10">
      <rect width="155" height="20" rx="4" fill="#0E1924" stroke="#0284C7" stroke-width="0.8"/>
      <text x="77" y="14" fill="#38BDF8" text-anchor="middle">storyboard_preview.html</text>

      <rect x="165" width="160" height="20" rx="4" fill="#0E1924" stroke="#0284C7" stroke-width="0.8"/>
      <text x="245" y="14" fill="#38BDF8" text-anchor="middle">production_bundle.json</text>
    </g>
  </g>

  <!-- Stage 8: Autonomous Product Council -->
  <g transform="translate(1195, 540)">
    <rect width="365" height="375" rx="10" fill="url(#ssotCardBg)" stroke="#A855F7" stroke-width="1.5" filter="url(#cardShadow)"/>
    <rect x="0" y="0" width="365" height="3" fill="url(#purpleNeon)" rx="1.5"/>

    <g transform="translate(20, 20)">
      <rect width="140" height="20" rx="4" fill="#2E1B4E" stroke="#A855F7" stroke-width="1"/>
      <text x="70" y="14" class="badge" fill="#E9D5FF" text-anchor="middle">PRODUCT COUNCIL</text>
      
      <text x="150" y="15" class="mono" font-size="12" font-weight="700" fill="#C084FC">4-Persona Board</text>
    </g>

    <text x="20" y="65" class="title" font-size="16" fill="#FFFFFF">Stage 8: Autonomous Council</text>
    <text x="20" y="85" class="mono" font-size="12" fill="#D8B4FE">100-Point Rubric (Passing Gate: &gt;= 90.0)</text>

    <!-- 4 Council Personas -->
    <g transform="translate(20, 102)" class="mono" font-size="11">
      <rect width="325" height="46" rx="5" fill="#140E24" stroke="#4C1D95" stroke-width="1"/>
      <text x="12" y="20" fill="#E9D5FF" font-weight="600">council-fde (25 Pts)</text>
      <text x="12" y="36" fill="#A78BFA" font-size="10">Dependencies, zero-leak telemetry, preflight</text>
      <text x="280" y="28" fill="#34D399" font-weight="700">25/25</text>

      <g transform="translate(0, 52)">
        <rect width="325" height="46" rx="5" fill="#140E24" stroke="#4C1D95" stroke-width="1"/>
        <text x="12" y="20" fill="#E9D5FF" font-weight="600">council-agent-engineer (25 Pts)</text>
        <text x="12" y="36" fill="#A78BFA" font-size="10">Pydantic schemas, 7-pt prompt loop, ADK</text>
        <text x="280" y="28" fill="#34D399" font-weight="700">25/25</text>
      </g>

      <g transform="translate(0, 104)">
        <rect width="325" height="46" rx="5" fill="#140E24" stroke="#4C1D95" stroke-width="1"/>
        <text x="12" y="20" fill="#E9D5FF" font-weight="600">council-strategist (25 Pts)</text>
        <text x="12" y="36" fill="#A78BFA" font-size="10">6 Domains, brand narrative, Mode B continuity</text>
        <text x="280" y="28" fill="#34D399" font-weight="700">25/25</text>
      </g>

      <g transform="translate(0, 156)">
        <rect width="325" height="46" rx="5" fill="#140E24" stroke="#4C1D95" stroke-width="1"/>
        <text x="12" y="20" fill="#E9D5FF" font-weight="600">council-ux-designer (25 Pts)</text>
        <text x="12" y="36" fill="#A78BFA" font-size="10">24fps animatic, safe guides, WCAG 2.2 AA</text>
        <text x="280" y="28" fill="#34D399" font-weight="700">25/25</text>
      </g>
    </g>

    <!-- Strict Gate Status -->
    <rect x="20" y="318" width="325" height="40" rx="6" fill="#180C2E" stroke="#8B5CF6" stroke-width="1.2"/>
    <text x="182" y="342" class="badge" font-size="12" fill="#E9D5FF" text-anchor="middle">
      GATE PASSED: 100.0/100 COMPOSITE SCORE
    </text>
  </g>

  <!-- ==================== CONNECTOR PATHWAYS & FLOW ARROWS ==================== -->
  <!-- Col 1: Stage 0 -> Stage 1 -->
  <path d="M 212 315 L 212 335" stroke="#00F0FF" stroke-width="2" marker-end="url(#arrow)" fill="none"/>
  
  <!-- Col 1: Stage 1 -> Stage 2 -->
  <path d="M 212 540 L 212 560" stroke="#A855F7" stroke-width="2" marker-end="url(#arrowPurple)" fill="none"/>

  <!-- Col 1 (Stage 2 SSOT) -> Col 2 (Stage 3 & Stage 4) -->
  <path d="M 385 620 C 405 620, 405 325, 425 325" stroke="#F59E0B" stroke-width="2" marker-end="url(#arrowAmber)" fill="none"/>
  <path d="M 385 730 L 425 730" stroke="#00F0FF" stroke-width="2" marker-end="url(#arrow)" fill="none"/>

  <!-- Col 2 (Stage 3 & Stage 4) -> Col 3 (Stage 5 Auditor) -->
  <path d="M 780 325 C 795 325, 795 362, 810 362" stroke="#F59E0B" stroke-width="2" marker-end="url(#arrowAmber)" fill="none"/>
  <path d="M 780 730 C 795 730, 795 440, 810 440" stroke="#00F0FF" stroke-width="2" marker-end="url(#arrow)" fill="none"/>

  <!-- Col 3: Stage 5 -> Stage 6 (Video Engine) -->
  <path d="M 992 595 L 992 615" stroke="#38BDF8" stroke-width="2" marker-end="url(#arrow)" fill="none"/>

  <!-- Col 3 -> Col 4 (Stage 7 HTML Compiler) -->
  <path d="M 1175 765 C 1185 765, 1185 325, 1195 325" stroke="#00F0FF" stroke-width="2" marker-end="url(#arrow)" fill="none"/>

  <!-- Col 4: Stage 7 -> Stage 8 (Product Council) -->
  <path d="M 1377 520 L 1377 540" stroke="#A855F7" stroke-width="2" marker-end="url(#arrowPurple)" fill="none"/>

  <!-- ==================== BOTTOM INVARIANTS & TELEMETRY BAR ==================== -->
  <g transform="translate(40, 935)">
    <rect width="1520" height="96" rx="10" fill="#0C0E16" stroke="#25283A" stroke-width="1.2" filter="url(#cardShadow)"/>
    <rect x="0" y="0" width="1520" height="2" fill="url(#cyanNeon)" rx="1"/>

    <!-- Left Header -->
    <text x="24" y="30" class="title" font-size="13" fill="#FFFFFF" letter-spacing="1">
      ARCHITECTURAL INVARIANTS &amp; QUALITY CONTRACTS (v2.1.0)
    </text>

    <!-- Invariant Pills Row -->
    <g transform="translate(24, 46)" class="mono" font-size="11">
      <!-- 1 -->
      <rect width="285" height="36" rx="6" fill="#131622" stroke="#262B40" stroke-width="1"/>
      <circle cx="16" cy="18" r="4" fill="#00F0FF"/>
      <text x="28" y="16" fill="#E2E8F0" font-weight="700">IMMUTABLE SSOT</text>
      <text x="28" y="28" fill="#94A3B8" font-size="9">MasterProductionBible sealed once</text>

      <!-- 2 -->
      <g transform="translate(295, 0)">
        <rect width="285" height="36" rx="6" fill="#131622" stroke="#262B40" stroke-width="1"/>
        <circle cx="16" cy="18" r="4" fill="#A855F7"/>
        <text x="28" y="16" fill="#E2E8F0" font-weight="700">STRICT 2026 MATRIX</text>
        <text x="28" y="28" fill="#94A3B8" font-size="9">Zero legacy 3.1 models permitted</text>
      </g>

      <!-- 3 -->
      <g transform="translate(590, 0)">
        <rect width="285" height="36" rx="6" fill="#131622" stroke="#262B40" stroke-width="1"/>
        <circle cx="16" cy="18" r="4" fill="#10B981"/>
        <text x="28" y="16" fill="#E2E8F0" font-weight="700">ZERO VIDEO PRE-AUDIT</text>
        <text x="28" y="28" fill="#94A3B8" font-size="9">Simulation default; explicit opt-in</text>
      </g>

      <!-- 4 -->
      <g transform="translate(885, 0)">
        <rect width="285" height="36" rx="6" fill="#131622" stroke="#262B40" stroke-width="1"/>
        <circle cx="16" cy="18" r="4" fill="#F59E0B"/>
        <text x="28" y="16" fill="#E2E8F0" font-weight="700">SMPTE 24FPS ANIMATIC</text>
        <text x="28" y="28" fill="#94A3B8" font-size="9">Dark-room cinema player &amp; guides</text>
      </g>

      <!-- 5 -->
      <g transform="translate(1180, 0)">
        <rect width="285" height="36" rx="6" fill="#131622" stroke="#262B40" stroke-width="1"/>
        <circle cx="16" cy="18" r="4" fill="#EF4444"/>
        <text x="28" y="16" fill="#E2E8F0" font-weight="700">PRODUCT COUNCIL GATE</text>
        <text x="28" y="28" fill="#94A3B8" font-size="9">Composite score &gt;= 90.0 required</text>
      </g>
    </g>
  </g>
</svg>'''

if __name__ == "__main__":
    svg_data = generate_svg()
    out_file = Path("docs/assets/architecture_diagram.svg")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(svg_data, encoding="utf-8")
    print(f"Generated Nano Banana Architecture Diagram SVG at: {out_file} ({len(svg_data)} bytes)")
