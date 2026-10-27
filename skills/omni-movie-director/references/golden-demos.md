# Golden Production Bibles & Prompt Suites (2026 Edition)

This reference contains the complete, battle-tested production bibles, prompt suites, sonic blueprints, and extension chains for two benchmark commercial productions:
1. **IKEA ASMR 2.0: "The Living Room Unfolds"** (Mode A Parallel Multi-Scene Cut)
2. **SEPHORA London Pulse 2.0: "Midnight Velvet"** (Mode A Parallel Montage & Mode B 40-Second Continuous Extension Chain)

---

## 1. Golden Demo 1: IKEA ASMR 2.0 ("The Living Room Unfolds")

### 1.1 Production Dossier
- **Client**: IKEA Commercial Sizzle
- **Regime**: `Regime 2: High-Kinetic & Precision Commercial`
- **Storytelling Mode**: `Mode A: Parallel Multi-Scene Cut (Montage)`
- **Aspect Ratio**: `16:9 Cinema Widescreen`
- **Total Runtime**: 32 Seconds (4 Scenes $\times$ 8 Seconds)
- **Logline**: In an empty sunlit Scandinavian apartment, an iconic flat-pack IKEA box violently trembles, then mechanically unpacks and self-assembles into a serene, fully furnished living sanctuary with hyper-tactile ASMR foley.

### 1.2 Master Production Bible JSON

```json
{
  "project_title": "IKEA: The Living Room Unfolds",
  "logline": "In an empty sunlit Scandinavian apartment, an iconic flat-pack IKEA box violently trembles, then mechanically unpacks and self-assembles into a pristine, serene living sanctuary with hyper-tactile ASMR foley.",
  "creative_regime": "Regime 2: High-Kinetic & Precision Commercial",
  "storytelling_mode": "Mode A: Parallel Multi-Scene Cut (Montage)",
  "aspect_ratio": "16:9",
  "total_runtime_seconds": 32,
  "characters": [],
  "environment": {
    "location_name": "Minimalist Stockholm Loft",
    "spatial_architecture": "An expansive 8x6 meter open-plan apartment with ultra-smooth pale blonde ash hardwood floors, matte-white limewashed walls, and floor-to-ceiling multi-pane Nordic windows on the left wall looking out to quiet birch trees.",
    "lighting_setup": "Soft, low-angled morning Scandinavian sunlight streaming through the windows at 5200K daylight balance, casting elongated warm rectangular light pools across the floor, filled with soft 6500K ambient room bounce.",
    "atmospheric_particles": "Delicate, slow-drifting micro-motes of atmospheric dust illuminated in the light beam; zero haze, zero smoke.",
    "positive_invariants": [
      "The pale blonde ash floorboards remain mechanically rigid with realistic wood grain that never distorts or changes direction.",
      "The walls remain pristine matte-white with consistent architectural baseboards.",
      "All furniture pieces retain exact Scandinavian minimalist geometry and color-true IKEA fabrics once assembled."
    ]
  },
  "camera_rig": {
    "rig_type": "Locked-off Studio Tripod on 35mm Prime Lens",
    "focal_length_mm": 35,
    "craft_profile": "Composition: Wide-angle eye-level architectural framing showing 80% of the room with the flat-pack box dead-center. Route: Completely locked-off static camera for the entire duration with zero drift, zero pan, and zero handheld shake. Action Anchor: Static frame holds observational discipline while hyper-kinetic assembly erupts within it. Focus: Deep f/8 depth of field keeping the center box and back walls tack-sharp. Tone: High-end architectural photography."
  },
  "sonic_blueprint": {
    "foley_cues": [
      "Low resonant cardboard vibration on wood floor",
      "Sharp, satisfying high-frequency tape tear and cardboard seam pop",
      "Crisp wood dowel clicks, rapid mechanical drawer slide swooshes, and solid pine locking thuds",
      "Soft, airy, deep 'fwoomp' of down-filled textiles settling onto wood",
      "Pristine, dead-silent room tone with gentle morning bird chirps outside glass"
    ],
    "dialogue_lines": [],
    "room_acoustics": "Bright, reverberant empty wooden room acoustics during the initial box opening, transitioning smoothly into a warm, dampened, acoustically insulated soundscape as fabrics, rugs, and cushions populate the space."
  },
  "master_bgm": {
    "track_title": "Nordic Serenity: Tactile Pulse",
    "genre_style": "Minimalist Acoustic Neo-Classical ASMR",
    "tempo_bpm": 84,
    "key_signature": "D Major",
    "instrumentation": [
      "Plucked acoustic cello pizzicato",
      "Felted upright piano playing delicate sparse arpeggios",
      "Subtle wooden xylophone clicks tuned to foley impacts",
      "Warm analog sub-bass drone resolving into absolute stillness"
    ],
    "dynamic_arc": "Seconds 00-08: Tense, playful pizzicato rhythm ticking like a clockwork box. Seconds 08-16: Rapid, polyrhythmic wooden mallet pulses synchronizing with furniture clicks. Seconds 16-24: Swelling warm cello and piano harmony. Seconds 24-32: All music decrescendos instantly on the final blanket drop, leaving only a sustained pure piano chord and serene silence.",
    "lyria_prompt": "Minimalist Scandinavian ASMR neo-classical acoustic cue, 84 BPM, D Major. Opens with delicate plucked cello pizzicato and light woodblock clicks. Builds into an intricate, satisfying, rhythmic clockwork pattern with felted upright piano. Resolves gracefully into a lush, peaceful ambient string chord that rings out into pristine silence."
  },
  "nano_banana_assets": [
    {
      "asset_id": "<image_1>",
      "job_description": "Defines the exact cardboard texture, proportions, blue-printed IKEA logo, and packing tape styling of the sealed flat-pack box.",
      "exclusion_clause": "Do not copy the studio background or white seamless floor from <image_1>.",
      "generation_prompt": "Commercial product photograph of a pristine, sealed flat-pack IKEA cardboard furniture box resting on a neutral background, sharp corners, kraft corrugated paper texture, classic blue IKEA logo clearly printed on top surface, reinforced brown paper packing tape along seams, clean architectural studio lighting."
    },
    {
      "asset_id": "<image_2>",
      "job_description": "Defines the exact Scandinavian living room interior palette, pale ash wood flooring, and floor-to-ceiling window architecture.",
      "exclusion_clause": "Do not copy any people, pets, or outdoor weather conditions from <image_2>.",
      "generation_prompt": "Architectural interior photograph of an empty, bright Scandinavian room with wide pale blonde ash plank flooring, pristine matte-white walls, high ceilings, large black-framed multi-pane windows on the left wall with morning sunlight casting geometric light pools across the clean floor, 8k resolution, shot on Hasselblad."
    },
    {
      "asset_id": "<image_3>",
      "job_description": "Defines the complete finished furniture suite (grey fabric sofa, oak coffee table, mustard-yellow wool throw blanket, minimalist white bookcase, potted fiddle-leaf fig).",
      "exclusion_clause": "Do not copy the room layout from <image_3>; use only the furniture design and fabric specifications.",
      "generation_prompt": "Catalog showcase photograph of a curated IKEA living room set: an ash-grey textured fabric two-seater sofa, a low solid oak oval coffee table, a folded mustard-yellow waffle-knit wool throw blanket, an open white-lacquered shelf unit with art books, and a terracotta potted green fiddle-leaf plant, photorealistic Scandinavian design."
    }
  ],
  "scenes": [
    {
      "scene_index": 1,
      "timestamp_range": "00:00 - 00:08",
      "scene_title": "The Awakening Box",
      "regime": "Regime 2: High-Kinetic & Precision Commercial",
      "action_beats": [
        "The sealed IKEA box sits dead-center on the bare ash floor in total stillness under morning sunlight.",
        "At second 03, the box begins to shudder rapidly with high-frequency tactile micro-vibrations.",
        "At second 07, the reinforced packing tape along the top center seam suddenly splits open with a crisp pop and a tiny puff of kraft paper dust."
      ],
      "kinetic_contact_chain": "Stillness -> Micro-oscillation of box edges against ash floorboards -> High-tension seam split -> Cardboard flaps spring open 15 degrees -> Settles into open posture.",
      "omni_prose_prompt": "A locked-off wide-angle architectural shot captures an empty, pristine Scandinavian room with pale blonde ash wood floors and sunlit white walls, based on the spatial layout of <image_2>. In the exact dead-center of the floor rests a sealed kraft cardboard IKEA flat-pack box matching the design in <image_1>. All action occurs at natural, real-time 1.0x playback speed with unyielding physical gravity. For the first three seconds, the box sits in dead stillness under warm morning sunlight streaming through the tall left windows. At second 03, the box begins to tremble and vibrate with intense, tactile micro-tremors, rattling crisply against the rigid hardwood floor without shifting location. At second 07, the center packing tape violently splits open, releasing a small puff of kraft dust as the top cardboard flaps spring slightly upward. The camera remains completely fixed on its tripod with zero movement, zero drift, and tack-sharp deep focus. Synchronized diegetic audio begins with dead-silent empty room tone, followed by the dry resonant woody rattling of cardboard against ash flooring, culminating in a sharp, hyper-tactile cardboard 'POP' and tearing tape sound."
    },
    {
      "scene_index": 2,
      "timestamp_range": "08:00 - 00:16",
      "scene_title": "The Hyper-Kinetic Self-Assembly",
      "regime": "Regime 2: High-Kinetic & Precision Commercial",
      "action_beats": [
        "The cardboard flaps fold flat onto the floor like blooming origami petals.",
        "Precision-cut solid oak furniture legs, white shelf panels, and frame components levitate out in structured order.",
        "Components interlock at high velocity into a low coffee table and a minimalist shelving unit with rigid mechanical clicks."
      ],
      "kinetic_contact_chain": "Flaps burst outward -> Wooden pieces slide on air trajectories -> Dovetail joints collide and snap together -> Base legs strike the hardwood floor with solid acoustic thuds -> Stable resting lock.",
      "omni_prose_prompt": "A locked-off wide-angle architectural shot from the exact same fixed camera position in the empty Scandinavian room. Continuing at 1.0x real-time speed with no slow motion, the cardboard box flaps instantly burst fully open, laying flat on the blonde ash floor. In a rapid, hyper-satisfying burst of choreographed kinetic assembly, flat-pack components derived from <image_3> erupt in crisp sequence: precision-cut solid oak table legs shoot outward and lock with rigid mechanical authority into an oval coffee table tabletop, while white-lacquered shelf panels slide and click into a vertical bookcase against the rear wall. Every wooden dowel, joint, and cam-lock snaps into place with zero elastic warping or rubbery bending, obeying rigid solid-state geometry. The camera holds perfectly static on its tripod, framing the explosive self-building choreography in tack-sharp focus. Synchronized diegetic ASMR audio features a rapid cascade of hyper-detailed mechanical sounds: high-speed sliding wood panels, sharp rhythmic 'CLICK-CLACK' dowel snaps, metallic fastener clicks, and the deep, solid 'THUD' of oak table legs planting firmly onto the hardwood floorboards, accompanied by playful acoustic cello pizzicato from the master score."
    },
    {
      "scene_index": 3,
      "timestamp_range": "00:16 - 00:24",
      "scene_title": "Upholstery & Soft Architecture",
      "regime": "Regime 2: High-Kinetic & Precision Commercial",
      "action_beats": [
        "A textured grey fabric sofa expands smoothly from the center staging area, cushions billowing outward.",
        "A woven natural wool area rug unrolls across the ash floor with rhythmic momentum.",
        "A ceramic table lamp and a potted green fiddle-leaf fig slide gracefully onto their finished surfaces."
      ],
      "kinetic_contact_chain": "Rug unrolls across floorboards with surface friction -> Sofa cushions drop under gravity -> Potted plant bases contact oak tabletop with ceramic clinks -> Secondary leaf settling oscillation.",
      "omni_prose_prompt": "The locked-off wide-angle shot maintains unbroken continuous framing of the evolving Scandinavian room. At natural real-time 1.0x speed, a large textured oat-grey fabric two-seater sofa matching <image_3> unfolds with solid mechanical grace in the center-left living space, its dense foam cushions plumping and expanding into taut upholstery. Simultaneously, a dense woven natural wool area rug unrolls rapidly across the ash floorboards from right to left, coming to a dead stop beneath the sofa legs with crisp surface friction. In the background, a white ceramic table lamp with a pleated paper shade and a potted fiddle-leaf plant glide smoothly into position onto the finished oak coffee table and bookcase surfaces, their bases landing with micro-second precision. Maintain rigid prop geometry and lighting continuity from the low morning sun. Synchronized diegetic audio layers the satisfying heavy unrolling friction of thick wool rug against hardwood, the deep, muffled 'FWUMP' of heavy sofa cushions settling, the delicate ceramic 'tink' of the lamp touching wood, and the subtle rustle of green plant leaves coming to rest."
    },
    {
      "scene_index": 4,
      "timestamp_range": "00:24 - 00:32",
      "scene_title": "The Final Flourish & The ASMR Stillness",
      "regime": "Regime 2: High-Kinetic & Precision Commercial",
      "action_beats": [
        "A folded mustard-yellow waffle-knit wool throw blanket arcs gracefully through the air over the sofa.",
        "The blanket lands dead-center on the grey sofa corner, sending a soft, visible air ripple through its knit folds.",
        "All motion abruptly freezes into an immaculate, serene, fully furnished architectural living room."
      ],
      "kinetic_contact_chain": "Throw blanket trajectory -> Gentle gravitational descent -> Impact with sofa cushion -> Micro-compression of textile knit -> Total static equilibrium.",
      "omni_prose_prompt": "The fixed wide-angle camera remains perfectly locked on the fully assembled Scandinavian living room under warm morning sunlight. Filmed at real-time 1.0x playback speed, the final missing element—a vibrant mustard-yellow waffle-knit wool throw blanket from <image_3>—descends smoothly through the sunlit air in a gentle, gravity-bound arc. At second 28, the blanket lands gracefully across the right armrest of the textured grey sofa, its soft wool folds settling with natural fabric weight and creating a momentary gentle compression in the seat cushion before coming to complete rest. As the blanket touches down, every moving element in the room reaches absolute, motionless stillness: the plants are static, the furniture is pristine, and warm sunlight bathes the peaceful sanctuary. The camera holds unbroken static discipline with no jump cuts and no morphing. Synchronized diegetic audio captures the gentle, airy 'fwoosh' of the descending wool, followed by a singular, supremely soft and satisfying 'fwoomp' as it cushions onto the sofa fabric. Instantly, all musical and mechanical sounds cut out, leaving only pristine, hushed Scandinavian room tone and the faint, distant chirp of morning birds outside."
    }
  ]
}
```

---

## 2. Golden Demo 2: SEPHORA London Pulse 2.0 ("Midnight Velvet")

### 2.1 Production Dossier
- **Client**: SEPHORA Flagship Launch
- **Regime**: `Regime 2: High-Kinetic & Precision Commercial`
- **Exhibition Canvas**: `9:16 Vertical Reel` (Mobile, Storefront Totems)
- **Runtime**: 32 Seconds (Mode A Montage) / 40 Seconds (Mode B Continuous Oner)
- **Logline**: A high-octane fashion collision through rainy midnight Soho, where two avant-garde models strut from London street grit into a gleaming SEPHORA flagship, culminating in a hero product lock.

### 2.2 Mode A: Parallel Multi-Scene Cut Prompts

#### Scene 1: The Soho Stare & The Night Pan (00:00 - 00:08)
```text
A 9:16 vertical high-fashion cinematic sequence begins in an extreme macro close-up on Model Maya's face matching <image_1>, focusing on her left eye adorned with shimmering emerald and gold holographic eyeshadow and immaculate winged eyeliner. Raindrops glisten on her cheek under wet Soho neon lighting at real-time 1.0x playback speed with zero slow motion. At second 02, Maya delivers a sharp, confident wink directly into the lens and whispers: "London, wake up." Triggered precisely by the eyelid closing, the vertical 50mm camera executes a high-speed horizontal whip-pan to the right, blurring neon lights into electric streaks before snapping to a halt in a medium-wide shot of a rain-slicked Soho cobblestone avenue, where an iconic red London double-decker bus streaks past in the background with wet asphalt tire hiss. Maintain crisp focal planes, rich saturated magenta and cyan reflections, and zero digital artifacting. Synchronized diegetic audio starts with the intimate, dry sound of an eyelid blink and whispered vocal close to mic, slamming instantly into a punching 138 BPM UK Garage drum hit, a whooshing whip-pan sound effect, and the wet tire spray of the passing bus.
```

#### Scene 2: The Flagship Infiltration: Tactile Glamour (00:08 - 00:16)
```text
Continuing in 9:16 vertical format at 1.0x real-time speed, the camera glides smoothly forward on a stabilized Steadicam through the automatic sliding glass doors of the SEPHORA flagship, transitioning instantly from wet dark Soho into brilliant, 5600K multi-point beauty lighting. Over seconds 08 to 11, Model Kaelen from <image_2> in his charcoal blazer with white-striped cuffs lifts a heavyweight gold metal lipstick tube with precision thumb flick, sliding the cap off with rigid mechanical alignment. Over seconds 11 to 14, in a snappy two-beat montage, Maya turns into frame and a plush black makeup brush sweeps firmly across her cheekbone, releasing a delicate micro-burst of golden cosmetic shimmer that catches the ring light. Over seconds 14 to 16, both models exchange a fierce, synchronized side-profile smile in front of a gleaming black lacquer cosmetic display. Keep cosmetics mechanically rigid and textures true to high-end beauty advertising. Synchronized diegetic audio features the heavy pneumatic whoosh of sliding glass doors, the loud, satisfying metallic 'CLACK' of the lipstick cap disengaging, the soft fibrous 'swoosh' of brush on skin, and high-energy driving UK Garage bassline.
```

#### Scene 3: The Soho Runway Strut (00:16 - 00:24)
```text
A tracking 9:16 vertical Steadicam shot moves backward at a rapid walking pace 2 meters ahead of Maya and Kaelen as they burst through the store exit onto the rainy London pavement in synchronized runway cadence at natural 1.0x speed. Maya wears her glossy scarlet trench coat from <image_1> and Kaelen wears his charcoal blazer from <image_2>, creating stark visual polarity against the night background. Maya's metallic stiletto heels plant firmly onto the wet asphalt with unmistakable physical weight, kicking up micro-droplets of water with each step. At second 21, Maya swings the black-and-white striped SEPHORA shopping bag from <image_3> smoothly forward toward the lens with runway attitude, holding the braided rope handle tight in her leather-gloved fingers. The camera keeps both models centered in vertical profile without crossing the action axis, capturing the glowing neon storefront behind them melting into creamy vertical anamorphic bokeh. Synchronized diegetic audio layers rapid, rhythmic stiletto clicks reverberating off brick walls, wet street splash foley, the crisp cardstock rustle of the shopping bag, and a soaring synth-pop riser sweep peaking in intensity.
```

#### Scene 4: The Bag Lock & The Soho Freeze (00:24 - 00:32)
```text
The vertical 9:16 camera executes a rapid, stabilized punch-in push of 60 centimeters directly toward the iconic black-and-white striped SEPHORA bag held firmly in Maya's gloved hand at chest height. Filmed at real-time 1.0x speed, the bag from <image_3> swings into the exact center of the vertical frame: its braided black rope handles are taut, its folded paper gussets are crisp and unwrinkled, and the embossed black SEPHORA typography is rendered in tack-sharp macro clarity. In the background, the glowing store portal and the wet London night street dissolve into beautiful out-of-focus bokeh circles. At exactly second 30, all motion abruptly halts into a pristine, high-resolution editorial freeze-frame on the bag, holding dead-still for the final two seconds with zero text distortion and zero geometric warping. Synchronized audio reaches its climax as the UK Garage track hits a massive final snare and bass drop, instantly cutting to absolute dead silence punctuated only by a single, crisp, mechanical 'SNAP' sound effect as the frame freezes, with a faint, luxurious reverb tail decaying into the silence.
```

---

## 3. Mode B: Continuous 40-Second Extension Chain (SEPHORA Oner)

Mode B utilizes Gemini Omni's native `previous_interaction_id` chaining to deliver an unbroken 40-second continuous oner without cuts:

### Turn 0: Base Clip (00:00 - 00:10) — The Soho Approach
```text
A 10-second continuous 9:16 vertical tracking shot glides backward at natural 1.0x real-time speed ahead of Model Maya, who struts down a rain-slicked Soho cobblestone avenue at midnight. Maya wears a high-gloss scarlet-red patent trench coat with metallic stiletto boots, her eyes adorned with vivid holographic emerald eyeshadow matching <image_1>. Neon signage from vintage clubs reflects across the wet asphalt as an iconic red London bus streaks past in the background. Maya approaches the glowing glass facade of a SEPHORA flagship, her heels clicking crisply against the stones. The camera holds a steady 2-meter distance at chest height with subtle Steadicam breathing. One continuous unbroken shot, no jump cuts, no time-ramping. Synchronized diegetic audio features rhythmic stiletto clicks, wet tire hisses, city rain mist, and a skipping 138 BPM UK Garage drum rhythm, ending as Maya extends her hand to push open the store entrance.
```

### Turn 1: Extension Turn 1 (+10s, 00:10 - 00:20) — The Store Transition
```text
The camera continues backward in one unbroken continuous shot through the opening glass doors as Maya struts inside without missing a beat, maintaining identical scarlet patent trench styling and physical pacing from the preceding interaction. The lighting shifts dynamically from wet moody London night into brilliant 5600K diffused beauty lighting bouncing off black-lacquered mirrored aisles. Model Kaelen, wearing a tailored charcoal blazer with chalk-white striped cuffs matching <image_2>, steps smoothly into frame alongside her. Kaelen flicks open a gold lipstick case with a crisp mechanical snap, smiling as Maya whispers: "London, wake up." The 138 BPM music drops into a heavy Moog bassline as both models strut in side-by-side synchronization down the central cosmetics corridor. One continuous shot, no jump cuts, no morphing. Synchronized audio seamlessly blends the pneumatic door whoosh, magnetic lipstick snap, and driving bassline.
```

### Turn 2: Extension Turn 2 (+10s, 00:20 - 00:30) — The Product Flourish
```text
The camera continues its unbroken vertical tracking movement, arcing 45 degrees to frame Maya from a low-angle three-quarter perspective as she reaches a central vanity display. In one fluid motion without stopping her stride, she picks up the iconic black-and-white striped SEPHORA shopping bag by its braided black rope handles. The bag swings forward in a controlled arc, its sharp paper folds and clean monochrome stripes catching the overhead beauty lights with pristine geometric rigidity. Kaelen pivots smoothly in the background, examining a shimmering powder compact. The bassline builds with intense white-noise risers and syncopated snare rolls. One continuous shot, no jump cuts.
```

### Turn 3: Extension Turn 3 (+10s, 00:30 - 00:40) — The Climactic Hero Lock
```text
The camera executes a smooth 50-centimeter punch-in toward the SEPHORA bag, locking the embossed brand logo dead-center in the vertical frame. Maya holds the bag firmly at chest height as she reaches the outdoor threshold once more, glancing over her shoulder directly into the lens. At second 38, all motion snaps into an immaculate high-fashion freeze-frame on the crisp bag, with Maya's scarlet trench and the glowing store interior blurring into lush bokeh behind. Synchronized audio hits a climactic percussion impact and cuts instantly to dead silence, leaving only a single crisp 'SNAP' and a faint decaying sub-bass hum. One continuous shot, no jump cuts.
```
