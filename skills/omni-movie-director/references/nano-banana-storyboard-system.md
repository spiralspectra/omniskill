# Nano Banana Storyboard Pre-Visualization System & Cinema UI Specification

This reference contains the prompt engineering templates, optical directives, Inclusion/Exclusion matrix, and Dark-Room Cinema HTML Animatic specification for the **Nano Banana Pro (`gemini-3-pro-image`) Pre-Visualization Engine**.

---

## 1. The Pre-Visualization Imperative

In generative video production, the primary cause of character mutation, wardrobe drift, and lighting inconsistency is generating video directly from raw text without visual anchors.

**The Omniskill Rule of Pre-Visualization**:
> **A complete visual storyboard MUST be rendered deterministically using Nano Banana (`gemini-3-pro-image`) BEFORE generating Gemini Omni video prompts and triggering live video renders.**

By rendering visual anchors first:
1. Character identity, hair, and wardrobe are frozen into an immutable pixel manifold.
2. Architecture, materials, and Kelvin color grading are established as ground truth.
3. Gemini Omni ingests concrete reference images (`<image_1>`, `<image_2>`, `<image_3>`) via `reference_to_video`, reducing character mutation to zero.

---

## 2. Gemini Omni Reference Ceiling & Inclusion/Exclusion Matrix

Gemini Omni 1.1 enforces an architectural ceiling of **up to 3 image references (`<image>`) + 1 video reference (`<video>`) + 1 audio track (`<audio>`)**. The 3-Anchor system maps 1:1 to this ceiling:

| Tag Identifier | Production Anchor | Aspect Ratio | Sole Responsibility ("One Job") |
| :--- | :--- | :--- | :--- |
| `<image_1>` | **Anchor 1: Character Turnaround** | `16:9` or `1:1` | **Subject Identity & Wardrobe**: Locks facial features, ethnic identity, eye color, hairstyle, and wardrobe silhouette. |
| `<image_2>` | **Anchor 2: Master Environment Plate** | `16:9` or `9:16` | **Architecture & Volumetric Lighting**: Locks room geometry, materials, key/fill lighting, color grading, and atmospheric tone. |
| `<image_3>` | **Anchor 3: Scene Keyframe / Boundary** | Master Aspect | **Composition & Spatial Blocking**: Locks camera framing, actor starting posture, spatial depth, and props at $t=0.0s$. |

### 2.1 The Inclusion / Exclusion Contract Clause

To prevent visual bleed (e.g., character wardrobe absorbing wall textures from `<image_2>`), every video prompt embeds this contract clause:

```text
[INCLUSION / EXCLUSION CONTRACT CLAUSE]
"Using the provided reference assets:
- From <image_1>, inherit solely the character's facial features, bone structure, skin tone, hair texture, and wardrobe styling for [CHARACTER_NAME], without copying the neutral studio backdrop.
- From <image_2>, inherit solely the architectural layout, material surfaces, color temperature, and volumetric lighting scheme of [ENVIRONMENT_NAME], without introducing any additional subjects.
- From <image_3>, inherit the exact starting camera perspective, subject placement, and initial physical posture at second 0.0.
No visual bleed between references is permitted: the character styling from <image_1> must not alter the background geometry of <image_2>, and the lighting of <image_2> must not bleach or distort the wardrobe colors of <image_1>."
```

---

## 3. Nano Banana 3-Anchor Prompt Templates

### 3.1 Anchor 1: Character Turnaround Sheet (`CHAR_TURNAROUND`)

```text
A professional cinematic character design turnaround sheet on a clean neutral 18% gray photography studio backdrop, showing three distinct angles of the exact same character side-by-side in one cohesive composite frame:
1. Left Panel: Full-body front view standing in a neutral, relaxed stance.
2. Center Panel: Medium three-quarter angle view showcasing posture and clothing silhouette.
3. Right Panel: Close-up profile portrait focusing on facial features, bone structure, and hair texture.

Subject: [CHARACTER_NAME], a [EXACT AGE]-year-old [ETHNICITY/DEMOGRAPHIC] [GENDER/ROLE].
Facial Invariants: [DETAILED BONE STRUCTURE, E.G., high sharp cheekbones, square jawline, almond-shaped amber-brown eyes, straight nasal bridge, natural skin texture with visible pores and light freckles].
Hair: [EXACT HAIRSTYLE, E.G., cropped raven-black textured buzz-cut with a crisp fade along the temples, natural matte finish].
Wardrobe DNA: [EXACT CLOTHING PIECES, E.G., a tailored heavyweight matte cobalt-blue chore jacket in raw Japanese denim, unbuttoned over a crisp off-white crewneck cotton t-shirt, paired with charcoal-gray relaxed-fit twill trousers and scuffed black leather lace-up service boots].
Lighting: Soft diffuse 5600K daylight-balanced balanced studio lighting with zero dramatic shadows, zero colored gels, and 1:1 key-to-fill ratio for maximum reference clarity.
Optics & Medium: Shot on Arri Alexa 65 with 50mm Prime lens at f/5.6, razor-sharp focus from head to toe, 4K digital concept art quality, perfectly consistent face and outfit across all three views.
```

### 3.2 Anchor 1 (Alternate): Product / Prop Turnaround Sheet

```text
A commercial industrial design hero turnaround sheet on a seamless matte-dark studio backdrop, displaying three distinct orthographic views of the exact same hero product in a single composite frame:
1. Left Panel: Direct front elevation view showing primary face and controls.
2. Center Panel: Dynamic three-quarter perspective hero angle on a solid slate pedestal.
3. Right Panel: Macro detail view focusing on surface materials, knurling, and engraved branding.

Product: [PRODUCT_NAME], a [PRODUCT DESCRIPTION, E.G., precision matte-black ceramic chronograph wristwatch].
Material Invariants: [SURFACE DETAILS, E.G., micro-bead-blasted zirconia ceramic casing, domed scratch-resistant sapphire crystal with anti-reflective purple hue, brushed rose-gold indices, and a textured vulcanized fluoroelastomer strap].
Lighting: Clean commercial studio strip softbox lighting creating a single continuous crisp reflection across the bevel, with a warm 3200K rim light along the right silhouette.
Optics: Hasselblad H6D-100c with 120mm Macro lens at f/8, mechanical geometric rigidity, razor-sharp focus across all surfaces.
```

### 3.3 Anchor 2: Master Environment & Lighting Plate (`ENV_MASTER_PLATE`)

```text
An ultra-wide establishing master architectural interior plate of [ENVIRONMENT_NAME, E.G., a sun-drenched minimalist Nordic loft kitchen], completely empty with zero people, zero animals, and zero character clutter.
Spatial Geometry: [LAYOUT & MATERIALS, E.G., expansive open-concept living space featuring a central waterfall-edge fluted white marble island, light bleached herringbone white oak parquet flooring, raw textured lime-washed plaster walls in soft alabaster, and black steel-framed double-height crittall windows along the entire back wall overlooking a foggy pine forest].
Props & Set Dressing: [FURNITURE & PROPS, E.G., minimalist matte-black architectural barstools tucked under the island, a single ceramic vase holding dry sculptural branches, brushed brass sink fixtures with subtle water droplet reflections].
Lighting & Atmosphere: Morning natural sunlight raking in from the back-left windows at a warm 4200K angle, casting long sharp geometric window-frame shadows across the floorboards and illuminating subtle airborne dust particles; fill light is cool 6500K skylight bouncing off the plaster walls; soft ambient falloff in the corners.
Color Grading: Muted Scandinavian palette with natural warm wood tones, clean architectural whites, deep iron shadows, and crisp window highlights.
Optics: Cinematic wide-angle capture on Panavision Millennium DXL2 with Primo 70 24mm lens at f/4.0, zero barrel distortion, straight architectural verticals, deep depth of field, photorealistic 8K production still.
```

### 3.4 Anchor 3: Scene First Frame Keyframe (`SCENE_KEYFRAME`)

```text
A cinematic narrative keyframe capturing the exact opening frame (timecode 00:00:00) of a scene:
Scene Context: [SLUGLINE, E.G., INT. SUNLIT NORDIC KITCHEN - MORNING].
Subject: [CHARACTER_NAME] from the character turnaround bible, maintaining identical facial features, buzz-cut hairstyle, and wearing the identical [WARDROBE, E.G., cobalt-blue raw denim chore jacket over white crewneck t-shirt].
Environment: Set inside the empty Nordic kitchen master plate, featuring the identical [KEY ROOM FEATURES, E.G., fluted white marble island, bleached herringbone oak floors, and large crittall windows with raking morning sunlight].
Composition & Framing: [CRAFT SPECIFICATION, E.G., An eye-level medium shot framed from the waist up, positioning the character slightly in the left third of the frame facing towards the right].
Action & Gesture at Frame 0: The character stands poised at the marble island with their right hand gently hovering 2 centimeters above a steaming matte-black ceramic coffee cup, eyes cast downward in contemplative focus, shoulders relaxed.
Lighting: Morning sunlight from the crittall windows casts a warm 4200K rim-light along the left shoulder and denim collar, with soft diffuse ambient fill illuminating the facial profile and a gentle steam curl rising from the cup.
Cinematography: Shot on Arri Alexa Mini LF with Cooke Anamorphic /i Full Frame Plus 40mm lens at T2.3, shallow depth of field rendering the pine trees outside the window into soft oval bokeh, natural film grain, 16:9 widescreen composition.
```

### 3.5 Mode G: 2x2 4-Panel Storyboard Grid

```text
A professional film production 4-panel storyboard grid arranged in a clean 2x2 rectangular layout with thin black gutters, illustrating a 4-beat cinematic sequence in sequential reading order (Panel 1: Top-Left, Panel 2: Top-Right, Panel 3: Bottom-Left, Panel 4: Bottom-Right):
Visual Continuity Lock: The same protagonist ([CHARACTER_NAME] in cobalt-blue chore jacket) and the same location ([ENVIRONMENT_NAME] with morning window light) appear consistently across all four panels.
- Panel 1 (Top-Left - 0s): Medium shot, character reaches toward the ceramic mug on the marble counter.
- Panel 2 (Top-Right - 3s): Tight close-up macro, fingers wrap around the warm ceramic surface; condensation and steam rise crisply.
- Panel 3 (Bottom-Left - 6s): Wide over-the-shoulder shot, character lifts the mug and takes a sip while gazing out the rain-streaked window.
- Panel 4 (Bottom-Right - 10s): Low-angle medium-close hero shot, character lowers the mug with a subtle, satisfied half-smile as the morning sun breaks through the clouds.
Aesthetic: Hand-drawn cinematic storyboard sketches with digital color wash, crisp linework, camera movement directional arrows indicated, professional A24 feature film pre-visualization sheet.
```

---

## 4. Nano Banana Technical Parameters & Negative Directives

When invoking `gemini-3-pro-image` via the Gen AI SDK:

```python
NANO_BANANA_CONFIG = {
    "aspect_ratio": "16:9",      # Or "9:16", "1:1", "2.39:1"
    "number_of_images": 1,
    "output_mime_type": "image/png",
    "person_generation": "ALLOW_ADULT",
}

NANO_BANANA_NEGATIVE_PROMPT = (
    "oversaturated HDR, plastic skin, mannequin face, airbrushed textures, "
    "deformed fingers, extra digits, unnatural limb bending, floating objects, "
    "warped architectural lines, fisheye distortion, double faces, cloned people, "
    "low resolution, watermark, stock photo watermark, jpeg compression artifacts"
)
```

---

## 5. Dark-Room Cinema HTML Animatic UI Specification

The compiled `storyboard_preview.html` delivers an A24 / Frame.io style presentation:
- **Color Tokens**:
  * Canvas: `#08090D` (Pitch Black)
  * Surface / Card: `#0F111A` (Elevation 1)
  * Border: `#23283B`
  * Director Telemetry: `#00F0FF` (Cyan)
  * Lighting & Notes: `#FFB703` (Amber)
  * Speed Lock: `#10B981` (Emerald)
  * DNA & Identity: `#A855F7` (Violet)
- **Interactive Capabilities**:
  * Click-to-copy Hex swatches with visual toast.
  * Collapsible prompt inspection drawers for Character Sheets and Master Plates.
  * Audio player with synchronized timecode progression.
  * Shot-by-shot timeline with dual media viewport (Keyframe Image $\leftrightarrow$ Live MP4 Video).
  * One-click "Copy Omni Prompt" button.
  * Fullscreen Theater Mode with keyboard navigation (`Left`/`Right` arrows, `Spacebar`, `C`).
