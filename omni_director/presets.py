import re
from typing import Any, Dict, List, Optional

from omni_director.schemas import (
    ActionBeatSpec,
    AspectRatio,
    CharacterTurnaroundSpec,
    CraftCameraSpec,
    DiegeticSonicSpec,
    MasterBgmSpec,
    MasterEnvironmentSpec,
    MasterProductionBible,
    NanoBananaReference,
    RegimeType,
    ScenePromptSpec,
    StorytellingMode,
)

# 1. IKEA ASMR Golden Preset
IKEA_ASMR_BIBLE = MasterProductionBible(
    project_title="IKEA: The Living Room Unfolds",
    logline="In an empty sunlit Scandinavian apartment, an iconic flat-pack IKEA box violently trembles, then mechanically unpacks and self-assembles into a pristine, serene living sanctuary with hyper-tactile ASMR foley.",
    creative_regime=RegimeType.REGIME_2_KINETIC,
    storytelling_mode=StorytellingMode.MODE_A_PARALLEL_CUT,
    aspect_ratio=AspectRatio.RATIO_16_9,
    total_runtime_seconds=32,
    color_palette=["#1E293B", "#F59E0B", "#0284C7", "#F8FAFC"],
    characters=[],
    environment=MasterEnvironmentSpec(
        location_name="Minimalist Stockholm Loft",
        spatial_architecture="An expansive 8x6 meter open-plan apartment with ultra-smooth pale blonde ash hardwood floors, matte-white limewashed walls, and floor-to-ceiling multi-pane Nordic windows on the left wall looking out to quiet birch trees.",
        lighting_setup="Soft, low-angled morning Scandinavian sunlight streaming through the windows at 5200K daylight balance, casting elongated warm rectangular light pools across the floor, filled with soft 6500K ambient room bounce.",
        atmospheric_particles="Delicate, slow-drifting micro-motes of atmospheric dust illuminated in the light beam; zero haze, zero smoke.",
        positive_invariants=[
            "The pale blonde ash floorboards remain mechanically rigid with realistic wood grain that never distorts or changes direction.",
            "The walls remain pristine matte-white with consistent architectural baseboards.",
            "All furniture pieces retain exact Scandinavian minimalist geometry and color-true IKEA fabrics once assembled."
        ]
    ),
    camera_rig=CraftCameraSpec(
        rig_type="Locked-off Studio Tripod on 35mm Prime Lens",
        focal_length_mm=35,
        composition="Wide-angle eye-level architectural framing showing 80% of the room with the flat-pack box dead-center.",
        route="Completely locked-off static camera for the entire duration with zero drift, zero pan, and zero handheld shake.",
        action_anchor="Static frame holds observational discipline while hyper-kinetic assembly erupts within it.",
        focus_axis="Deep f/8 depth of field keeping the center box and back walls tack-sharp.",
        tone_rig="High-end architectural photography."
    ),
    sonic_blueprint=DiegeticSonicSpec(
        foley_cues=[
            "Low resonant cardboard vibration on wood floor",
            "Sharp, satisfying high-frequency tape tear and cardboard seam pop",
            "Crisp wood dowel clicks, rapid mechanical drawer slide swooshes, and solid pine locking thuds",
            "Soft, airy, deep 'fwoomp' of down-filled textiles settling onto wood",
            "Pristine, dead-silent room tone with gentle morning bird chirps outside glass"
        ],
        dialogue_lines=[],
        room_acoustics="Bright, reverberant empty wooden room acoustics during the initial box opening, transitioning smoothly into a warm, dampened, acoustically insulated soundscape as fabrics, rugs, and cushions populate the space."
    ),
    master_bgm=MasterBgmSpec(
        track_title="Nordic Serenity: Tactile Pulse",
        genre_style="Minimalist Acoustic Neo-Classical ASMR",
        tempo_bpm=84,
        key_signature="D Major",
        instrumentation=[
            "Plucked acoustic cello pizzicato",
            "Felted upright piano playing delicate sparse arpeggios",
            "Subtle wooden xylophone clicks tuned to foley impacts",
            "Warm analog sub-bass drone resolving into absolute stillness"
        ],
        dynamic_arc="Seconds 00-08: Tense, playful pizzicato rhythm ticking like a clockwork box. Seconds 08-16: Rapid, polyrhythmic wooden mallet pulses synchronizing with furniture clicks. Seconds 16-24: Swelling warm cello and piano harmony. Seconds 24-32: All music decrescendos instantly on the final blanket drop, leaving only a sustained pure piano chord and serene silence.",
        lyria_prompt="Minimalist Scandinavian ASMR neo-classical acoustic cue, 84 BPM, D Major. Opens with delicate plucked cello pizzicato and light woodblock clicks. Builds into an intricate, satisfying, rhythmic clockwork pattern with felted upright piano. Resolves gracefully into a lush, peaceful ambient string chord that rings out into pristine silence."
    ),
    nano_banana_assets=[
        NanoBananaReference(
            asset_id="<image_1>",
            job_description="Defines the exact cardboard texture, proportions, blue-printed IKEA logo, and packing tape styling of the sealed flat-pack box.",
            exclusion_clause="Do not copy the studio background or white seamless floor from <image_1>.",
            generation_prompt="Commercial product photograph of a pristine, sealed flat-pack IKEA cardboard furniture box resting on a neutral background, sharp corners, kraft corrugated paper texture, classic blue IKEA logo clearly printed on top surface, reinforced brown paper packing tape along seams, clean architectural studio lighting."
        ),
        NanoBananaReference(
            asset_id="<image_2>",
            job_description="Defines the exact Scandinavian living room interior palette, pale ash wood flooring, and floor-to-ceiling window architecture.",
            exclusion_clause="Do not copy any people, pets, or outdoor weather conditions from <image_2>.",
            generation_prompt="Architectural interior photograph of an empty, bright Scandinavian room with wide pale blonde ash plank flooring, pristine matte-white walls, high ceilings, large black-framed multi-pane windows on the left wall with morning sunlight casting geometric light pools across the clean floor, 8k resolution, shot on Hasselblad."
        ),
        NanoBananaReference(
            asset_id="<image_3>",
            job_description="Defines the complete finished furniture suite (grey fabric sofa, oak coffee table, mustard-yellow wool throw blanket, minimalist white bookcase, potted fiddle-leaf fig).",
            exclusion_clause="Do not copy the room layout from <image_3>; use only the furniture design and fabric specifications.",
            generation_prompt="Catalog showcase photograph of a curated IKEA living room set: an ash-grey textured fabric two-seater sofa, a low solid oak oval coffee table, a folded mustard-yellow waffle-knit wool throw blanket, an open white-lacquered shelf unit with art books, and a terracotta potted green fiddle-leaf plant, photorealistic Scandinavian design."
        )
    ],
    scenes=[
        ScenePromptSpec(
            scene_index=1,
            timestamp_range="00:00 - 00:08",
            scene_title="The Awakening Box",
            regime=RegimeType.REGIME_2_KINETIC,
            action_beats=[
                "The sealed IKEA box sits dead-center on the bare ash floor in total stillness under morning sunlight.",
                "At second 03, the box begins to shudder rapidly with high-frequency tactile micro-vibrations.",
                "At second 07, the reinforced packing tape along the top center seam suddenly splits open with a crisp pop and a tiny puff of kraft paper dust."
            ],
            kinetic_contact_chain="Stillness -> Micro-oscillation of box edges against ash floorboards -> High-tension seam split -> Cardboard flaps spring open 15 degrees -> Settles into open posture.",
            omni_prose_prompt="A locked-off wide-angle architectural shot captures an empty, pristine Scandinavian room with pale blonde ash wood floors and sunlit white walls, based on the spatial layout of <image_2>. In the exact dead-center of the floor rests a sealed kraft cardboard IKEA flat-pack box matching the design in <image_1>. All action occurs at natural, real-time 1.0x playback speed with unyielding physical gravity. For the first three seconds, the box sits in dead stillness under warm morning sunlight streaming through the tall left windows. At second 03, the box begins to tremble and vibrate with intense, tactile micro-tremors, rattling crisply against the rigid hardwood floor without shifting location. At second 07, the center packing tape violently splits open, releasing a small puff of kraft dust as the top cardboard flaps spring slightly upward. The camera remains completely fixed on its tripod with zero movement, zero drift, and tack-sharp deep focus. Synchronized diegetic audio begins with dead-silent empty room tone, followed by the dry resonant woody rattling of cardboard against ash flooring, culminating in a sharp, hyper-tactile cardboard POP and tearing tape sound.",
            conversational_edit_deltas=[
                "Turn 2: Make the box tremble more violently and add visible paper dust curling into the sunbeam.",
                "Turn 3: Change the morning sun to soft overcast afternoon daylight while keeping the box action identical."
            ]
        ),
        ScenePromptSpec(
            scene_index=2,
            timestamp_range="00:08 - 00:16",
            scene_title="The Hyper-Kinetic Self-Assembly",
            regime=RegimeType.REGIME_2_KINETIC,
            action_beats=[
                "The cardboard flaps fold flat onto the floor like blooming origami petals.",
                "Precision-cut solid oak furniture legs, white shelf panels, and frame components levitate out in structured order.",
                "Components interlock at high velocity into a low coffee table and a minimalist shelving unit with rigid mechanical clicks."
            ],
            kinetic_contact_chain="Flaps burst outward -> Wooden pieces slide on air trajectories -> Dovetail joints collide and snap together -> Base legs strike the hardwood floor with solid acoustic thuds -> Stable resting lock.",
            omni_prose_prompt="A locked-off wide-angle architectural shot from the exact same fixed camera position in the empty Scandinavian room. Continuing at 1.0x real-time speed with no slow motion, the cardboard box flaps instantly burst fully open, laying flat on the blonde ash floor. In a rapid, hyper-satisfying burst of choreographed kinetic assembly, flat-pack components derived from <image_3> erupt in crisp sequence: precision-cut solid oak table legs shoot outward and lock with rigid mechanical authority into an oval coffee table tabletop, while white-lacquered shelf panels slide and click into a vertical bookcase against the rear wall. Every wooden dowel, joint, and cam-lock snaps into place with zero elastic warping or rubbery bending, obeying rigid solid-state geometry. The camera holds perfectly static on its tripod, framing the explosive self-building choreography in tack-sharp focus. Synchronized diegetic ASMR audio features a rapid cascade of hyper-detailed mechanical sounds: high-speed sliding wood panels, sharp rhythmic CLICK-CLACK dowel snaps, metallic fastener clicks, and the deep, solid THUD of oak table legs planting firmly onto the hardwood floorboards, accompanied by playful acoustic cello pizzicato from the master score.",
            conversational_edit_deltas=[
                "Turn 2: Increase the speed of the shelf assembly and add subtle sawdust motes catching the sunlight.",
                "Turn 3: Ensure the bookcase locks against the wall with an audible resonant tap."
            ]
        ),
        ScenePromptSpec(
            scene_index=3,
            timestamp_range="00:16 - 00:24",
            scene_title="Upholstery & Soft Architecture",
            regime=RegimeType.REGIME_2_KINETIC,
            action_beats=[
                "A textured grey fabric sofa expands smoothly from the center staging area, cushions billowing outward.",
                "A woven natural wool area rug unrolls across the ash floor with rhythmic momentum.",
                "A ceramic table lamp and a potted green fiddle-leaf fig slide gracefully onto their finished surfaces."
            ],
            kinetic_contact_chain="Rug unrolls across floorboards with surface friction -> Sofa cushions drop under gravity -> Potted plant bases contact oak tabletop with ceramic clinks -> Secondary leaf settling oscillation.",
            omni_prose_prompt="The locked-off wide-angle shot maintains unbroken continuous framing of the evolving Scandinavian room. At natural real-time 1.0x speed, a large textured oat-grey fabric two-seater sofa matching <image_3> unfolds with solid mechanical grace in the center-left living space, its dense foam cushions plumping and expanding into taut upholstery. Simultaneously, a dense woven natural wool area rug unrolls rapidly across the ash floorboards from right to left, coming to a dead stop beneath the sofa legs with crisp surface friction. In the background, a white ceramic table lamp with a pleated paper shade and a potted fiddle-leaf plant glide smoothly into position onto the finished oak coffee table and bookcase surfaces, their bases landing with micro-second precision. Maintain rigid prop geometry and lighting continuity from the low morning sun. Synchronized diegetic audio layers the satisfying heavy unrolling friction of thick wool rug against hardwood, the deep, muffled FWUMP of heavy sofa cushions settling, the delicate ceramic tink of the lamp touching wood, and the subtle rustle of green plant leaves coming to rest.",
            conversational_edit_deltas=[
                "Turn 2: Add a soft warm light turning on inside the pleated paper table lamp upon landing.",
                "Turn 3: Make the fiddle-leaf fig leaves oscillate gently for 2 seconds after touching down."
            ]
        ),
        ScenePromptSpec(
            scene_index=4,
            timestamp_range="00:24 - 00:32",
            scene_title="The Final Flourish & The ASMR Stillness",
            regime=RegimeType.REGIME_2_KINETIC,
            action_beats=[
                "A folded mustard-yellow waffle-knit wool throw blanket arcs gracefully through the air over the sofa.",
                "The blanket lands dead-center on the grey sofa corner, sending a soft, visible air ripple through its knit folds.",
                "All motion abruptly freezes into an immaculate, serene, fully furnished architectural living room."
            ],
            kinetic_contact_chain="Throw blanket trajectory -> Gentle gravitational descent -> Impact with sofa cushion -> Micro-compression of textile knit -> Total static equilibrium.",
            omni_prose_prompt="The fixed wide-angle camera remains perfectly locked on the fully assembled Scandinavian living room under warm morning sunlight. Filmed at real-time 1.0x playback speed, the final missing element—a vibrant mustard-yellow waffle-knit wool throw blanket from <image_3>—descends smoothly through the sunlit air in a gentle, gravity-bound arc. At second 28, the blanket lands gracefully across the right armrest of the textured grey sofa, its soft wool folds settling with natural fabric weight and creating a momentary gentle compression in the seat cushion before coming to complete rest. As the blanket touches down, every moving element in the room reaches absolute, motionless stillness: the plants are static, the furniture is pristine, and warm sunlight bathes the peaceful sanctuary. The camera holds unbroken static discipline with no jump cuts and no morphing. Synchronized diegetic audio captures the gentle, airy fwoosh of the descending wool, followed by a singular, supremely soft and satisfying fwoomp as it cushions onto the sofa fabric. Instantly, all musical and mechanical sounds cut out, leaving only pristine, hushed Scandinavian room tone and the faint, distant chirp of morning birds outside.",
            conversational_edit_deltas=[
                "Turn 2: Add a small steaming white ceramic coffee mug resting on the oak coffee table in the final second.",
                "Turn 3: Softly rack focus to the mustard throw blanket texture in the final 2 seconds."
            ]
        )
    ],
    domain_archetype="architectural_sanctuary",
)

# 2. SEPHORA London Pulse (Mode A Parallel Cut)
SEPHORA_PULSE_BIBLE = MasterProductionBible(
    project_title="SEPHORA: London Pulse (Midnight Velvet)",
    logline="A high-octane, 9:16 vertical fashion collision through rainy midnight Soho, where two avant-garde models strut from London street grit into a gleaming SEPHORA flagship, culminating in a hero product lock.",
    creative_regime=RegimeType.REGIME_2_KINETIC,
    storytelling_mode=StorytellingMode.MODE_A_PARALLEL_CUT,
    aspect_ratio=AspectRatio.RATIO_9_16,
    total_runtime_seconds=32,
    color_palette=["#0A0A10", "#FF0055", "#00F0FF", "#FCEE09"],
    characters=[
        CharacterTurnaroundSpec(
            name="Model Maya (The Neon Siren)",
            silhouette="Tall, athletic, razor-sharp high cheekbones, graphic slicked-back raven architectural bob.",
            wardrobe_polarity="HIGH POLARITY A: Vivid high-gloss scarlet-red patent trench coat with oversized structured lapels, sheer black mesh collar, and metallic silver pointed-toe stiletto boots.",
            movement_signature="Aggressive, predatory, fast-tempo runway stride with zero hip sway and sharp head pivots."
        ),
        CharacterTurnaroundSpec(
            name="Model Kaelen (The Shimmer Rebel)",
            silhouette="Androgynous, dark glowing skin, cropped bleached-platinum buzz cut, sharp jawline.",
            wardrobe_polarity="HIGH POLARITY B: Matte charcoal-grey tailored wool blazer with chalk-white pinstripes on sleeves, jet-black silk camisole, and heavy distressed combat boots.",
            movement_signature="Fluid, rhythm-locked street bounce with syncopated shoulder dips matching the UK Garage groove."
        )
    ],
    environment=MasterEnvironmentSpec(
        location_name="Midnight Soho to SEPHORA Flagship",
        spatial_architecture="Exterior: Rain-slicked London cobblestones and wet asphalt reflecting neon signage. Interior: High-gloss black lacquer and mirrored vanity aisles bathed in brilliant 5600K beauty lighting.",
        lighting_setup="Exterior: Moody 3200K tungsten streetlamps with electric magenta and cyan neon rim light. Interior: 5600K high-CRI diffused beauty lighting.",
        atmospheric_particles="Fine airborne London rain drizzle, water droplets on patent leather, cosmetic shimmer powder catching light.",
        positive_invariants=[
            "The black-and-white SEPHORA shopping bag retains exact vertical stripe geometry and clean typography.",
            "Maya's scarlet trench coat remains high-gloss patent leather without texture drift.",
            "Kaelen's charcoal blazer maintains chalk-white stripe accents without color bleeding."
        ]
    ),
    camera_rig=CraftCameraSpec(
        rig_type="9:16 Vertical Steadicam on 50mm Anamorphic Lens",
        focal_length_mm=50,
        composition="Dynamic vertical framing emphasizing towering model silhouettes, high-fashion angles, and macro beauty details.",
        route="Rapid tracking shots, snappy whip-pans, and stabilizing push-ins.",
        action_anchor="Model facial expressions and tactile product interactions.",
        focus_axis="Shallow f/1.8 depth of field creating vertical oval anamorphic bokeh in wet city lights.",
        tone_rig="High-fashion commercial editorial."
    ),
    sonic_blueprint=DiegeticSonicSpec(
        foley_cues=[
            "Rapid rhythmic stiletto heel clicks on wet cobblestone",
            "Passing double-decker bus wet tire spray and diesel roar",
            "Pneumatic whoosh of glass sliding doors opening",
            "Metallic magnetic click of luxury lipstick cap disengaging",
            "Crisp paper bag snap and handle tension sound"
        ],
        dialogue_lines=["Maya: 'London, wake up.'"],
        room_acoustics="Wet, reverberant London street exterior transitioning sharply into hyper-clean, acoustically dampened luxury retail interior."
    ),
    master_bgm=MasterBgmSpec(
        track_title="Midnight Velvet: UK Garage Pulse",
        genre_style="Syncopated UK Garage / Hyper-Pop Runway Sizzle",
        tempo_bpm=138,
        key_signature="F Minor",
        instrumentation=[
            "Syncopated 2-step drum groove with punchy kick and crisp rimshots",
            "Deep rolling Moog Reese bassline",
            "Glittering hyper-pop synth arpeggios and vocal chops",
            "Dramatic snare roll risers and white-noise sweeps"
        ],
        dynamic_arc="Seconds 00-08: Snappy 2-step rhythm kicks in on the wink. Seconds 08-16: Heavy bassline drops inside flagship. Seconds 16-24: Massive riser sweep building energy. Seconds 24-32: Sudden cut to dead silence on final freeze-frame bag snap, leaving only a sub-bass decay.",
        lyria_prompt="High-energy UK Garage fashion runway track, 138 BPM, F Minor. Syncopated skipping 2-step beats, punchy kick drum, driving Moog bassline, glittering hyper-pop synth arpeggios, and edgy vocal chops. Builds rapidly with dramatic snare roll risers into an explosive, sleek high-fashion drop, ending abruptly on a crisp impact hit."
    ),
    nano_banana_assets=[
        NanoBananaReference(
            asset_id="<image_1>",
            job_description="Defines the exact facial structure, avant-garde graphic eyeliner, and scarlet patent trench coat for Model Maya.",
            exclusion_clause="Do not copy the studio lighting or plain grey background from <image_1>.",
            generation_prompt="Fashion editorial portrait of a striking woman with high cheekbones and slicked-back raven hair, wearing avant-garde metallic holographic graphic eyeliner and bold matte crimson lipstick, dressed in a high-gloss scarlet-red patent leather trench coat, vertical 9:16 framing, Hasselblad high-fashion beauty lighting."
        ),
        NanoBananaReference(
            asset_id="<image_2>",
            job_description="Defines the androgynous facial features, bleached platinum hair, and striped-cuff charcoal blazer for Model Kaelen.",
            exclusion_clause="Do not copy the pose or static background from <image_2>.",
            generation_prompt="Fashion editorial portrait of an androgynous model with dark glowing skin, bleached-platinum short hair, subtle holographic shimmer across cheekbones, wearing an oversized matte-charcoal tailored blazer with chalk-white striped cuffs, confident fierce expression, vertical 9:16 format, sleek editorial aesthetic."
        ),
        NanoBananaReference(
            asset_id="<image_3>",
            job_description="Defines the exact physical construction, black-and-white vertical stripe pattern, braided rope handle, and embossed logo of the SEPHORA shopping bag.",
            exclusion_clause="Do not copy any store background from <image_3>; maintain only the bag's rigid geometry and texture.",
            generation_prompt="Product photograph of an iconic SEPHORA retail shopping bag made of thick matte paper with clean black and vertical white stripes, black braided rope handles, crisp rectangular folds, embossed black SEPHORA logo centered, studio lighting, photorealistic commercial product shot."
        )
    ],
    scenes=[
        ScenePromptSpec(
            scene_index=1,
            timestamp_range="00:00 - 00:08",
            scene_title="The Soho Stare & The Night Pan",
            regime=RegimeType.REGIME_2_KINETIC,
            action_beats=[
                "Extreme vertical macro close-up on Model Maya's eye with shimmering holographic eyeshadow in Soho rain.",
                "Maya executes a sharp, deliberate runway wink directly into lens at second 02.",
                "On the wink, camera whip-pans 90 degrees right to reveal a rain-slicked Soho street with a motion-blurred red double-decker bus streaking past."
            ],
            kinetic_contact_chain="Micro-eye movement -> High-velocity eyelid closure (wink) -> Triggered camera whip-pan acceleration -> Rapid rotational deceleration -> Wet asphalt perspective stabilization.",
            omni_prose_prompt="A 9:16 vertical high-fashion cinematic sequence begins in an extreme macro close-up on Model Maya's face matching <image_1>, focusing on her left eye adorned with shimmering emerald and gold holographic eyeshadow and immaculate winged eyeliner. Raindrops glisten on her cheek under wet Soho neon lighting at real-time 1.0x playback speed with zero slow motion. At second 02, Maya delivers a sharp, confident wink directly into the lens and whispers: 'London, wake up.' Triggered precisely by the eyelid closing, the vertical 50mm camera executes a high-speed horizontal whip-pan to the right, blurring neon lights into electric streaks before snapping to a halt in a medium-wide shot of a rain-slicked Soho cobblestone avenue, where an iconic red London double-decker bus streaks past in the background with wet asphalt tire hiss. Maintain crisp focal planes, rich saturated magenta and cyan reflections, and zero digital artifacting. Synchronized diegetic audio starts with the intimate, dry sound of an eyelid blink and whispered vocal close to mic, slamming instantly into a punching 138 BPM UK Garage drum hit, a whooshing whip-pan sound effect, and the wet tire spray of the passing bus.",
            conversational_edit_deltas=[
                "Turn 2: Enhance the neon reflections in the street puddles and add more visible rain mist.",
                "Turn 3: Change the lipstick color on Maya to a deeper midnight burgundy while keeping the wink identical."
            ]
        ),
        ScenePromptSpec(
            scene_index=2,
            timestamp_range="00:08 - 00:16",
            scene_title="The Flagship Infiltration: Tactile Glamour",
            regime=RegimeType.REGIME_2_KINETIC,
            action_beats=[
                "Camera pushes forward through glowing glass sliding doors into the hyper-bright SEPHORA flagship.",
                "Model Kaelen slides a metallic gold lipstick casing open, revealing a vibrant crimson bullet.",
                "A large soft makeup brush sweeps across Maya's cheekbone in a rapid beauty montage, dusting fine shimmering particles."
            ],
            kinetic_contact_chain="Door glide -> Hand grips weighted lipstick tube -> Thumb drives cap removal with magnetic click -> Brush fibers compress against cheek skin -> Shimmer cloud dispersion.",
            omni_prose_prompt="Continuing in 9:16 vertical format at 1.0x real-time speed, the camera glides smoothly forward on a stabilized Steadicam through the automatic sliding glass doors of the SEPHORA flagship, transitioning instantly from wet dark Soho into brilliant, 5600K multi-point beauty lighting. Over seconds 08 to 11, Model Kaelen from <image_2> in his charcoal blazer with white-striped cuffs lifts a heavyweight gold metal lipstick tube with precision thumb flick, sliding the cap off with rigid mechanical alignment. Over seconds 11 to 14, in a snappy two-beat montage, Maya turns into frame and a plush black makeup brush sweeps firmly across her cheekbone, releasing a delicate micro-burst of golden cosmetic shimmer that catches the ring light. Over seconds 14 to 16, both models exchange a fierce, synchronized side-profile smile in front of a gleaming black lacquer cosmetic display. Keep cosmetics mechanically rigid and textures true to high-end beauty advertising. Synchronized diegetic audio features the heavy pneumatic whoosh of sliding glass doors, the loud, satisfying metallic CLACK of the lipstick cap disengaging, the soft fibrous swoosh of brush on skin, and high-energy driving UK Garage bassline.",
            conversational_edit_deltas=[
                "Turn 2: Make the cosmetic shimmer dust reflect rainbow sparkles under the beauty lights.",
                "Turn 3: Rack focus from the lipstick bullet directly to Kaelen's smiling eyes."
            ]
        ),
        ScenePromptSpec(
            scene_index=3,
            timestamp_range="00:16 - 00:24",
            scene_title="The Soho Runway Strut",
            regime=RegimeType.REGIME_2_KINETIC,
            action_beats=[
                "Maya and Kaelen strut in synchronized lockstep out of the store entrance onto the wet London sidewalk.",
                "Maya's stiletto heels plant firmly onto the wet pavement with zero slip or float.",
                "Maya swings the iconic black-and-white SEPHORA shopping bag forward in an assertive arc toward camera."
            ],
            kinetic_contact_chain="Stiletto strike on wet cobblestone -> Ground reaction force pushes hip forward -> Arm swings bag from shoulder -> Centrifugal arc of braided handle -> Forward presentation.",
            omni_prose_prompt="A tracking 9:16 vertical Steadicam shot moves backward at a rapid walking pace 2 meters ahead of Maya and Kaelen as they burst through the store exit onto the rainy London pavement in synchronized runway cadence at natural 1.0x speed. Maya wears her glossy scarlet trench coat from <image_1> and Kaelen wears his charcoal blazer from <image_2>, creating stark visual polarity against the night background. Maya's metallic stiletto heels plant firmly onto the wet asphalt with unmistakable physical weight, kicking up micro-droplets of water with each step. At second 21, Maya swings the black-and-white striped SEPHORA shopping bag from <image_3> smoothly forward toward the lens with runway attitude, holding the braided rope handle tight in her leather-gloved fingers. The camera keeps both models centered in vertical profile without crossing the action axis, capturing the glowing neon storefront behind them melting into creamy vertical anamorphic bokeh. Synchronized diegetic audio layers rapid, rhythmic stiletto clicks reverberating off brick walls, wet street splash foley, the crisp cardstock rustle of the shopping bag, and a soaring synth-pop riser sweep peaking in intensity.",
            conversational_edit_deltas=[
                "Turn 2: Increase the stride speed slightly and add dramatic billow to Maya's red trench coat hem.",
                "Turn 3: Add steam rising from a nearby underground subway grate in the background."
            ]
        ),
        ScenePromptSpec(
            scene_index=4,
            timestamp_range="00:24 - 00:32",
            scene_title="The Bag Lock & The Soho Freeze",
            regime=RegimeType.REGIME_2_KINETIC,
            action_beats=[
                "The camera punches in 60 centimeters directly toward the SEPHORA shopping bag held firmly in Maya's hand.",
                "The bag halts dead-center in the vertical frame, perfectly upright with sharp paper edges.",
                "At second 30, the video cuts to a crisp editorial freeze-frame on the bag and SEPHORA logo, with blurred glowing Soho neon behind."
            ],
            kinetic_contact_chain="Punch-in camera motion -> Arm locks bag at chest height -> Rope handles tension under gravity -> Abrupt momentum cessation -> Total frozen frame.",
            omni_prose_prompt="The vertical 9:16 camera executes a rapid, stabilized punch-in push of 60 centimeters directly toward the iconic black-and-white striped SEPHORA bag held firmly in Maya's gloved hand at chest height. Filmed at real-time 1.0x speed, the bag from <image_3> swings into the exact center of the vertical frame: its braided black rope handles are taut, its folded paper gussets are crisp and unwrinkled, and the embossed black SEPHORA typography is rendered in tack-sharp macro clarity. In the background, the glowing store portal and the wet London night street dissolve into beautiful out-of-focus bokeh circles. At exactly second 30, all motion abruptly halts into a pristine, high-resolution editorial freeze-frame on the bag, holding dead-still for the final two seconds with zero text distortion and zero geometric warping. Synchronized audio reaches its climax as the UK Garage track hits a massive final snare and bass drop, instantly cutting to absolute dead silence punctuated only by a single, crisp, mechanical SNAP sound effect as the frame freezes, with a faint, luxurious reverb tail decaying into the silence.",
            conversational_edit_deltas=[
                "Turn 2: Add a bold white sans-serif kinetic text overlay in the center that pops in reading 'FEEL THE PULSE'.",
                "Turn 3: Shift the background bokeh color balance to rich ambers and golds."
            ]
        )
    ],
    domain_archetype="luxury_fashion",
)

# 3. SEPHORA Continuous Extension 40s (Mode B)
SEPHORA_EXTENSION_40S_BIBLE = MasterProductionBible(
    project_title="SEPHORA: London Pulse (Continuous 40s Oner)",
    logline="A seamless, unbroken 40-second continuous 9:16 vertical Steadicam oner tracking two avant-garde models through rainy midnight Soho into the SEPHORA flagship and back to the wet pavement, linked across four +10s Gemini Omni extensions.",
    creative_regime=RegimeType.REGIME_2_KINETIC,
    storytelling_mode=StorytellingMode.MODE_B_CONTINUOUS_CHAIN,
    aspect_ratio=AspectRatio.RATIO_9_16,
    total_runtime_seconds=40,
    color_palette=["#0A0A10", "#FF0055", "#00F0FF", "#FCEE09"],
    characters=SEPHORA_PULSE_BIBLE.characters,
    environment=SEPHORA_PULSE_BIBLE.environment,
    camera_rig=SEPHORA_PULSE_BIBLE.camera_rig,
    sonic_blueprint=SEPHORA_PULSE_BIBLE.sonic_blueprint,
    master_bgm=SEPHORA_PULSE_BIBLE.master_bgm,
    nano_banana_assets=SEPHORA_PULSE_BIBLE.nano_banana_assets,
    scenes=[
        ScenePromptSpec(
            scene_index=1,
            timestamp_range="00:00 - 00:10 (Base Clip)",
            scene_title="The Soho Approach",
            regime=RegimeType.REGIME_2_KINETIC,
            action_beats=[
                "Model Maya struts down rain-slicked Soho cobblestones at midnight under glowing neon signage.",
                "A red double-decker bus streaks past with wet tire spray in the background.",
                "Maya reaches the glowing glass facade of the SEPHORA flagship, heels clicking firmly on wet stone."
            ],
            kinetic_contact_chain="Stiletto strike -> Ground reaction force -> Arm swing momentum -> Controlled approach -> Hand touches entrance door handle.",
            omni_prose_prompt="A 10-second continuous 9:16 vertical tracking shot glides backward at natural 1.0x real-time speed ahead of Model Maya matching <image_1>, who struts down a rain-slicked Soho cobblestone avenue at midnight. Maya wears a high-gloss scarlet-red patent trench coat with metallic stiletto boots, her eyes adorned with vivid holographic emerald eyeshadow. Neon signage from vintage clubs reflects across the wet asphalt with genuine physical reflections as an iconic red London bus streaks past in the background with wet asphalt tire hiss. Maya approaches the glowing glass facade of a SEPHORA flagship, her heels clicking crisply against the stones with unyielding physical gravity. Synchronized diegetic audio features rhythmic stiletto clicks, wet tire hisses, city rain mist, and a skipping 138 BPM UK Garage drum rhythm, ending as Maya extends her hand to push open the store entrance.",
            conversational_edit_deltas=["Turn 2: Enhance neon puddle reflections."]
        ),
        ScenePromptSpec(
            scene_index=2,
            timestamp_range="+10s extension (00:10 - 00:20)",
            scene_title="The Store Transition",
            regime=RegimeType.REGIME_2_KINETIC,
            action_beats=[
                "Camera glides backward without jump cuts through opening glass doors into brilliant 5600K beauty light.",
                "Model Kaelen in charcoal blazer steps into frame alongside Maya.",
                "Kaelen flicks open a gold lipstick case with a crisp mechanical snap as Maya whispers 'London, wake up.'"
            ],
            kinetic_contact_chain="Door glide momentum -> Footfall cadence unchanged -> Thumb drives lipstick cap removal -> Snappy mechanical disengagement -> Side-by-side synchronized stride.",
            omni_prose_prompt="The camera continues backward in one unbroken continuous shot through the opening glass doors as Maya struts inside without missing a beat, continuing at 1.0x real-time speed. The lighting shifts dynamically from wet moody London night into brilliant 5600K diffused beauty lighting bouncing off black-lacquered mirrored aisles. Model Kaelen from <image_2>, wearing a tailored charcoal blazer with chalk-white striped cuffs, steps smoothly into frame alongside her. Kaelen flicks open a gold lipstick case with a crisp mechanical snap, smiling as Maya whispers: 'London, wake up.' The 138 BPM music drops into a heavy Moog bassline as both models strut in side-by-side synchronization down the central cosmetics corridor with rigid physical postures. One continuous shot, no jump cuts.",
            conversational_edit_deltas=["Turn 2: Increase beauty light bounce off mirrors."]
        ),
        ScenePromptSpec(
            scene_index=3,
            timestamp_range="+10s extension (00:20 - 00:30)",
            scene_title="The Product Flourish",
            regime=RegimeType.REGIME_2_KINETIC,
            action_beats=[
                "Vertical tracking camera arcs 45 degrees to frame Maya from a low-angle three-quarter angle.",
                "Maya smoothly picks up the striped SEPHORA shopping bag by its braided rope handles in stride.",
                "The bag swings forward in a controlled arc, catching overhead beauty lights with rigid paper folds."
            ],
            kinetic_contact_chain="Tracking arc -> Fingers grasp braided rope handle -> Upward impulse lifts bag -> Centrifugal acceleration swings bag forward -> Stable chest-height carry.",
            omni_prose_prompt="The camera continues its unbroken vertical tracking movement at 1.0x real-time speed, arcing 45 degrees to frame Maya from a low-angle three-quarter perspective as she reaches a central vanity display. In one fluid motion without stopping her stride, she picks up the iconic black-and-white striped SEPHORA shopping bag from <image_3> by its braided black rope handles. The bag swings forward in a controlled arc, its sharp paper folds and clean monochrome stripes catching the overhead beauty lights with pristine geometric rigidity and natural fabric weight. Kaelen pivots smoothly in the background, examining a shimmering powder compact. Synchronized diegetic audio features the crisp rustle of thick luxury paper, rope handle tension, stiletto clicks echoing on mirrored tiles, and a building bassline with white-noise sweeps. One continuous shot, no jump cuts.",
            conversational_edit_deltas=["Turn 2: Enhance white-noise sweep intensity."]
        ),
        ScenePromptSpec(
            scene_index=4,
            timestamp_range="+10s extension (00:30 - 00:40)",
            scene_title="The Climactic Hero Lock",
            regime=RegimeType.REGIME_2_KINETIC,
            action_beats=[
                "Camera punches in 50 centimeters directly toward the SEPHORA bag.",
                "Embossed brand logo locks dead-center at chest height as Maya reaches the outdoor threshold.",
                "At second 38, motion snaps into a high-fashion freeze-frame on the bag, with neon bokeh behind."
            ],
            kinetic_contact_chain="Punch-in deceleration -> Arm locks bag upright -> Rope handles hold vertical tension -> Immediate kinetic freeze -> Sustained static frame.",
            omni_prose_prompt="The camera executes a smooth 50-centimeter punch-in toward the SEPHORA bag from <image_3>, locking the embossed brand logo dead-center in the vertical frame at 1.0x real-time playback speed. Maya holds the bag firmly at chest height as she reaches the outdoor threshold once more, glancing over her shoulder directly into the lens. At second 38, all motion snaps into an immaculate high-fashion freeze-frame on the crisp bag with unyielding geometric precision, with Maya's scarlet trench and the glowing store interior blurring into lush bokeh behind. Synchronized audio hits a climactic percussion impact and cuts instantly to dead silence, leaving only a single crisp SNAP and a faint decaying sub-bass hum. One continuous shot, no jump cuts.",
            conversational_edit_deltas=["Turn 2: Shift background bokeh to warm ambers."]
        )
    ],
    domain_archetype="luxury_fashion",
)

# 4. Kinetic Fabric Golden Preset
KINETIC_FABRIC_BIBLE = MasterProductionBible(
    project_title="The Kinetic Fabric: Grounded Innovation",
    logline="A dynamic material exploration of high-performance technical fabric moving from microscopic weave tension to high-velocity athletic aerodynamic turbulence.",
    creative_regime=RegimeType.REGIME_2_KINETIC,
    storytelling_mode=StorytellingMode.MODE_A_PARALLEL_CUT,
    aspect_ratio=AspectRatio.RATIO_16_9,
    total_runtime_seconds=32,
    color_palette=["#0F172A", "#38BDF8", "#F43F5E", "#E2E8F0"],
    characters=[],
    environment=MasterEnvironmentSpec(
        location_name="Aerodynamic Wind Tunnel Test Lab",
        spatial_architecture="High-tech wind tunnel facility with matte-black carbon-fiber walls, illuminated laminar flow nozzles, and a mirror-finish titanium test stage.",
        lighting_setup="High-contrast precision 5600K laser line lighting combined with deep blue ambient wash.",
        atmospheric_particles="Ultra-fine white condensation smoke tracing aerodynamic streamlines with zero random turbulence.",
        positive_invariants=[
            "The woven carbon-fiber grid structure remains mathematically consistent without digital warping.",
            "Laser illumination ribbons maintain clean geometric parallelism."
        ]
    ),
    camera_rig=CraftCameraSpec(
        rig_type="High-Speed Robotic Motion Control Track on 100mm Macro Prime",
        focal_length_mm=100,
        composition="Extreme macro geometric framing focusing on microfiber elasticity, tension vectors, and aerodynamic deflection.",
        route="High-precision linear tracking along the air velocity axis with micro-rotational rolls.",
        action_anchor="Woven yarn contact points and laser streamline vortices.",
        focus_axis="Razor-thin f/2.8 macro depth of field with micro-racks across thread layers.",
        tone_rig="Hyper-technical industrial commercial."
    ),
    sonic_blueprint=DiegeticSonicSpec(
        foley_cues=[
            "High-tension textile stretch creak and microfiber friction",
            "Pneumatic wind tunnel airflow whoosh and turbine hum",
            "High-frequency laser hum and ultrasonic resonance",
            "Tactile snap of fabric reaching maximum tensile load"
        ],
        dialogue_lines=[],
        room_acoustics="Acoustically treated industrial aerodynamic testing chamber with dead reflections and heavy sub-bass air pressure."
    ),
    master_bgm=MasterBgmSpec(
        track_title="Tensile Dynamics: Kinetic Pulse",
        genre_style="Futuristic Minimalist Glitch & Cinematic Sub-Bass",
        tempo_bpm=120,
        key_signature="C Minor",
        instrumentation=[
            "Pulsing analog modular synthesizer bassline",
            "Textured metallic percussion clicks tuned to micro-foley",
            "Granular synth pads that expand with airflow velocity",
            "Low sub-bass drops at maximum tension markers"
        ],
        dynamic_arc="Seconds 00-08: Micro-clicks and quiet sub-hum. Seconds 08-16: Rhythmic drive kicks in. Seconds 16-24: High-energy polyrhythms. Seconds 24-32: Sudden sharp deceleration leaving resonant metallic ring.",
        lyria_prompt="Futuristic industrial electronic score, 120 BPM, C Minor. Crisp tactile clicks, modular synth pulses, deep sub-bass drops, and precise microscopic rhythms. High-tech and aerodynamic aesthetic."
    ),
    nano_banana_assets=[
        NanoBananaReference(
            asset_id="<image_1>",
            job_description="Defines the exact microscopic weave pattern, iridescent cyan and scarlet yarn fibers, and tensile thread geometry.",
            exclusion_clause="Do not copy any human hands or background lab equipment from <image_1>.",
            generation_prompt="Macro photograph of high-performance technical athletic fabric: intricate interlocking weave of matte-black carbon fibers and luminous electric-cyan microfibers, 100mm macro lens, ultra-sharp thread details, precision studio rim lighting."
        ),
        NanoBananaReference(
            asset_id="<image_2>",
            job_description="Defines the titanium test stage, wind tunnel nozzle geometry, and laser illumination setup.",
            exclusion_clause="Do not introduce any human operators or unrelated tools from <image_2>.",
            generation_prompt="Architectural interior of an advanced aerodynamic wind tunnel testing facility: mirror-finish dark titanium floor, matte-black composite walls, high-velocity wind nozzle bathed in electric-blue LED rim lights, clean high-tech industrial aesthetic."
        ),
        NanoBananaReference(
            asset_id="<image_3>",
            job_description="Defines the finished aerodynamic winglet drape showing the fabric under maximum aerodynamic deflection.",
            exclusion_clause="Do not change the fabric weave from <image_1>; inherit only the aerodynamic curve geometry.",
            generation_prompt="Product design photograph of a streamlined athletic aerodynamic fabric winglet mounted on a carbon-fiber arm, flexing under high-speed laminar airflow with visible white smoke streamlines, high-speed photography."
        )
    ],
    scenes=[
        ScenePromptSpec(
            scene_index=1,
            timestamp_range="00:00 - 00:08",
            scene_title="The Microscopic Weave",
            regime=RegimeType.REGIME_2_KINETIC,
            action_beats=[
                "Extreme macro view of the interlocking cyan and carbon weave in complete stillness.",
                "At second 03, tension applies and individual yarn microfibers stretch taut with visible physical elongation.",
                "Laser line sweeps across the weave, highlighting microscopic fiber textures."
            ],
            kinetic_contact_chain="Relaxed fibers -> Tensile load applied -> Yarn elongation under force -> Surface micro-flattening -> Stable high-tension lock.",
            omni_prose_prompt="An extreme macro 100mm camera shot frames the intricate technical fabric weave from <image_1> resting on the titanium stage of <image_2>. Filmed at 1.0x real-time speed with rigid physics, the intertwined matte-black carbon yarns and luminous cyan microfibers sit in sharp stillness for the first three seconds under deep blue lab lighting. At second 03, mechanical tension applies from the edges, causing the interlocking threads to pull taut with realistic elasticity, elongating slightly without tearing or morphing. A crisp emerald laser scan line sweeps smoothly across the surface at second 06, catching the micro-ridges of each fiber in tack-sharp focus. Synchronized diegetic audio layers a deep, tactile microfiber stretch sound, a soft pneumatic pressure release, and high-precision electronic equipment hum.",
            conversational_edit_deltas=["Turn 2: Add visible micro-dust particle displacement upon tension snap."]
        ),
        ScenePromptSpec(
            scene_index=2,
            timestamp_range="00:08 - 00:16",
            scene_title="The Airflow Ignition",
            regime=RegimeType.REGIME_2_KINETIC,
            action_beats=[
                "Camera pulls back to a medium shot as wind tunnel nozzles ignite with high-speed laminar airflow.",
                "White condensation streamlines wrap smoothly over the taut fabric sheet with zero turbulence.",
                "The fabric ripples rhythmically with high-frequency aerodynamic waves."
            ],
            kinetic_contact_chain="Nozzle airflow discharge -> Air pressure boundary layer forms -> Fluid-structure interaction on fabric -> Aerodynamic ripple wave propagation -> Stable laminar wave state.",
            omni_prose_prompt="The camera executes a smooth backward robotic dolly move at 1.0x real-time playback speed, transitioning from macro into a medium-wide shot of the aerodynamic wind tunnel test bench from <image_2>. At second 09, high-velocity laminar airflow surges from the circular intake nozzle: smooth, parallel ribbons of white condensation smoke glide over the taut cyan-and-black fabric sheet matching <image_1>, adhering perfectly to its surface without turbulent separation. The fabric vibrates with ultra-precise, high-frequency aerodynamic micro-ripples, displaying authentic mass and aerodynamic resistance. The robotic camera holds a perfectly stabilized low-angle tracking position. Synchronized diegetic audio captures the rising pneumatic whoosh of high-speed laminar wind, deep acoustic turbine hum, and the rapid, crisp fluttering friction of synthetic fabric in air.",
            conversational_edit_deltas=["Turn 2: Enhance the brightness of the smoke streamlines under the blue laser light."]
        ),
        ScenePromptSpec(
            scene_index=3,
            timestamp_range="00:16 - 00:24",
            scene_title="The Aerodynamic Deflection",
            regime=RegimeType.REGIME_2_KINETIC,
            action_beats=[
                "Camera tracks laterally around the fabric as it flexes into an aerodynamic winglet curve.",
                "Laser illumination reveals vortices rolling smoothly off the trailing edge.",
                "The material maintains rigid structural integrity under maximum velocity."
            ],
            kinetic_contact_chain="Peak wind velocity -> Aerodynamic lift force generates deflection -> Flexible composite arm reaches planned bend angle -> Trailing edge sheds micro-vortex -> Dynamic equilibrium under load.",
            omni_prose_prompt="A dynamic lateral tracking arc shot sweeps 90 degrees around the testing rig at natural 1.0x speed. The technical fabric sheet, mounted on a sleek carbon-fiber arm like <image_3>, flexes smoothly under extreme aerodynamic pressure into a graceful, low-drag winglet profile. Twin violet laser sheets slice across the trailing edge, illuminating micro-vortices of smoke that curl gracefully off the fabric lip without fluttering into chaotic turbulence. Maintain exact thread pattern geometry and pristine lighting reflections on the dark titanium floor. Synchronized diegetic audio features a powerful, resonant wind tunnel roar, the high-pitch harmonic whistle of shedding vortices, and heavy sub-bass air compression pulses.",
            conversational_edit_deltas=["Turn 2: Increase the camber of the fabric winglet curve."]
        ),
        ScenePromptSpec(
            scene_index=4,
            timestamp_range="00:24 - 00:32",
            scene_title="The Deceleration & The Form Lock",
            regime=RegimeType.REGIME_2_KINETIC,
            action_beats=[
                "Wind tunnel airflow suddenly cuts off with a deep pneumatic thud.",
                "The fabric springs back into its pristine planar resting position with a satisfying tactile snap.",
                "Laser illumination freezes on the pristine weave as smoke gently dissipates into stillness."
            ],
            kinetic_contact_chain="Airflow cutoff -> Pressure drop -> Elastic restoring force snaps fabric -> Momentum damping oscillation -> Absolute static resting state.",
            omni_prose_prompt="The camera punches in smoothly on the fabric center from the front at 1.0x real-time speed. At second 27, the wind tunnel turbines instantly power down with a solid acoustic drop: the high-speed smoke ribbons dissipate into thin air, and the flexed fabric springs crisply back to its initial flat resting plane with a singular, satisfying physical SNAP. The material settles instantly into flawless, motionless stillness, its black-and-cyan weave catching the steady ambient blue glow of the lab with razor-sharp macro clarity. Zero camera drift and zero digital artifacting. Synchronized diegetic audio captures the heavy pneumatic clunk of the wind valves closing, the crisp, singular SNAP of the taut textile rebounding, and the smooth decay of turbine whine into dead-silent lab room tone.",
            conversational_edit_deltas=["Turn 2: Rack focus to the central carbon fiber thread in the final second."]
        )
    ],
    domain_archetype="kinetic_action",
)

SEPHORA_LONDON_PULSE_BIBLE = SEPHORA_PULSE_BIBLE


def build_ikea_asmr_bible() -> MasterProductionBible:
    """Builds a fresh instance of the IKEA ASMR golden preset bible."""
    return IKEA_ASMR_BIBLE.model_copy(deep=True)


def build_sephora_pulse_bible() -> MasterProductionBible:
    """Builds a fresh instance of the SEPHORA London Pulse preset bible."""
    return SEPHORA_PULSE_BIBLE.model_copy(deep=True)


def build_sephora_extension_40s_bible() -> MasterProductionBible:
    """Builds a fresh instance of the SEPHORA 40s Continuous Extension preset bible."""
    return SEPHORA_EXTENSION_40S_BIBLE.model_copy(deep=True)


def build_kinetic_fabric_bible() -> MasterProductionBible:
    """Builds a fresh instance of the Kinetic Fabric preset bible."""
    return KINETIC_FABRIC_BIBLE.model_copy(deep=True)


def build_sephora_london_pulse_bible() -> MasterProductionBible:
    """Builds a fresh instance of the SEPHORA London Pulse preset bible."""
    return SEPHORA_LONDON_PULSE_BIBLE.model_copy(deep=True)


PRESETS: Dict[str, MasterProductionBible] = {
    "ikea-asmr": IKEA_ASMR_BIBLE,
    "sephora-pulse": SEPHORA_PULSE_BIBLE,
    "sephora-london-pulse": SEPHORA_LONDON_PULSE_BIBLE,
    "sephora-extension-40s": SEPHORA_EXTENSION_40S_BIBLE,
    "kinetic-fabric": KINETIC_FABRIC_BIBLE,
}
CURATED_PRESETS = PRESETS


def get_preset_bible(name: str) -> MasterProductionBible:
    """Retrieves a pre-configured MasterProductionBible preset by name."""
    clean_name = name.lower().replace("_", "-")
    if clean_name not in PRESETS:
        available = ", ".join(PRESETS.keys())
        raise ValueError(f"Unknown preset: '{name}'. Available presets: {available}")
    return PRESETS[clean_name]


get_preset = get_preset_bible

DOMAIN_PRIORITY: List[str] = [
    "automotive_robotics",
    "culinary_asmr",
    "luxury_fashion",
    "kinetic_action",
    "tech_hardware",
    "architectural_sanctuary",
]

DOMAIN_ARCHETYPES: Dict[str, Dict[str, Any]] = {
    "automotive_robotics": {
        "keywords": [
            "vehicle", "vehicles", "drone", "drones", "robot", "robotics", "hypercar", "hypercars", "car", "cars",
            "motorsport", "motorsports", "motorcycle", "motorcycles", "pursuit", "engine", "chassis", "autonomous",
            "telemetry", "hydraulic", "suspension", "carbon fiber", "speedway", "racing"
        ],
        "default_camera": "Russian Arm 28mm Anamorphic with dynamic low-angle tracking",
        "default_focal_length": 28,
        "default_lighting": "Cool 6500K high-contrast industrial LED with sharp metallic rim highlights",
        "default_foley": [
            "High-torque electric motor whine",
            "Tire friction on slick asphalt",
            "Pneumatic valve hiss",
            "Mechanical robotic servo snaps"
        ],
        "default_bpm": 130,
        "default_key": "F Minor",
        "default_bgm_genre": "Industrial Electronic & Cybernetic Kinetic Score",
        "color_palette": ["#0B0E14", "#00F0FF", "#FF3B30", "#8E8E93"],
        "regime": RegimeType.REGIME_2_KINETIC,
    },
    "culinary_asmr": {
        "keywords": [
            "food", "coffee", "matcha", "cooking", "beverage", "kitchen", "culinary", "chef", "sizzle",
            "caramelization", "knife", "ingredient", "recipe", "baking", "espresso", "dining", "texture",
            "crunch", "taste", "flavor", "dough", "tea"
        ],
        "default_camera": "100mm Macro Probe Lens with micro-fluidic pan and tilt",
        "default_focal_length": 100,
        "default_lighting": "Warm 3200K tungsten backlight emphasizing surface steam and glistening oils",
        "default_foley": [
            "Crisp blade cutting through textured crust",
            "Gentle butter sizzle in cast iron",
            "Tactile ceramic clink",
            "Subtle simmering bubble pops"
        ],
        "default_bpm": 68,
        "default_key": "C Major",
        "default_bgm_genre": "Intimate Acoustic & Organic Ambient ASMR",
        "color_palette": ["#1C1917", "#D97706", "#F59E0B", "#FEF3C7"],
        "regime": RegimeType.REGIME_2_KINETIC,
    },
    "luxury_fashion": {
        "keywords": [
            "fashion", "runway", "cosmetics", "perfume", "couture", "jewelry", "model", "models", "haute",
            "makeup", "velvet", "silk", "wardrobe", "strut", "editorial", "beauty", "lipstick", "fragrance",
            "vogue", "glamour", "apparel", "luxury", "monogram", "flagship"
        ],
        "default_camera": "50mm Prime on Steadicam Ultra with gentle vertical float",
        "default_focal_length": 50,
        "default_lighting": "5600K diffused commercial beauty illumination with reflective mirror bounce",
        "default_foley": [
            "Rhythmic stiletto heel clicks on polished marble",
            "Crisp textile rustle of silk taffeta",
            "Metallic snap of luxury compact",
            "Subtle perfume atomizer mist spray"
        ],
        "default_bpm": 118,
        "default_key": "A Minor",
        "default_bgm_genre": "Deep House Runway & Parisian Haute Couture Pulse",
        "color_palette": ["#09090B", "#F43F5E", "#E2E8F0", "#D4AF37"],
        "regime": RegimeType.REGIME_2_KINETIC,
    },
    "kinetic_action": {
        "keywords": [
            "sport", "sports", "running", "martial arts", "parkour", "athletics", "dance", "athlete",
            "jump", "boxing", "climbing", "kick", "sprint", "workout", "fitness", "dynamic movement",
            "stunt", "acrobatic", "action"
        ],
        "default_camera": "High-Speed Wire Rig with 24mm Ultra-Wide lens and zero horizon roll",
        "default_focal_length": 24,
        "default_lighting": "Dynamic high-noon direct daylight with deep hard directional shadows",
        "default_foley": [
            "Athletic shoe sole squeak and ground impact",
            "Heavy synchronized breath cadence",
            "Wind rush over aerodynamic limbs",
            "Resonant physical force transfer thud"
        ],
        "default_bpm": 140,
        "default_key": "E Minor",
        "default_bgm_genre": "High-Velocity Orchestral Breakbeat & Hybrid Trap",
        "color_palette": ["#18181B", "#22C55E", "#3B82F6", "#FAFAFA"],
        "regime": RegimeType.REGIME_2_KINETIC,
    },
    "tech_hardware": {
        "keywords": [
            "semiconductor", "semiconductors", "smartphone", "smartphones", "laptop", "laptops", "cnc aluminum",
            "aluminum", "optics", "wearables", "wearable", "hardware", "chip", "silicon", "circuit", "processor",
            "device", "gadget", "anodized", "microchip", "chassis", "motherboard", "cleanroom"
        ],
        "default_camera": "CNC Motion Control Arm with 85mm Macro Prime and laser-guided rack focus",
        "default_focal_length": 85,
        "default_lighting": "Cleanroom 5000K pure white illumination with razor-thin linear specular highlights",
        "default_foley": [
            "Precision magnetic latch click",
            "Anodized aluminum bevel contact",
            "Subtle ultrasonic cleanroom hum",
            "Haptic motor vibration pulse"
        ],
        "default_bpm": 110,
        "default_key": "D Minor",
        "default_bgm_genre": "Minimalist Glitch & Micro-Acoustic Electronic Pulse",
        "color_palette": ["#030712", "#38BDF8", "#94A3B8", "#F8FAFC"],
        "regime": RegimeType.REGIME_2_KINETIC,
    },
    "architectural_sanctuary": {
        "keywords": [
            "architecture", "interior", "furniture", "brutalist", "home", "pavilion", "sanctuary",
            "building", "concrete", "travertine", "limestone", "space", "facade", "gallery", "atrium",
            "minimalist living", "structure", "courtyard", "zen", "residence", "sculpture"
        ],
        "default_camera": "24mm Tilt-Shift Prime on heavy hydraulic dolly with perspective control",
        "default_focal_length": 24,
        "default_lighting": "Low-angle golden hour sunlight casting geometric window shadows through dust motes",
        "default_foley": [
            "Acoustic reverberation in tall stone hall",
            "Subtle distant wind through bamboo atrium",
            "Soft leather creak on timber seat",
            "Gentle water fountain trickle"
        ],
        "default_bpm": 60,
        "default_key": "G Major",
        "default_bgm_genre": "Neo-Classical Piano & Spatial Drone Sanctuary",
        "color_palette": ["#1C1917", "#78716C", "#D6D3D1", "#E7E5E4"],
        "regime": RegimeType.REGIME_1_ATMOSPHERIC,
    },
}


def classify_brief_domain(brief_text: str) -> str:
    """Classifies a user creative brief into one of 6 commercial domain archetypes.

    Rules:
    - Counts whole-word / substring keyword matches across all 6 archetypes.
    - Selects the archetype with the highest match count.
    - Breaks ties deterministically in priority order:
      1. automotive_robotics
      2. culinary_asmr
      3. luxury_fashion
      4. kinetic_action
      5. tech_hardware
      6. architectural_sanctuary
    - Falls back to 'architectural_sanctuary' if match count is zero.
    """
    clean_text = brief_text.lower()
    scores: Dict[str, int] = {}

    for domain in DOMAIN_PRIORITY:
        data = DOMAIN_ARCHETYPES[domain]
        count = 0
        for kw in data["keywords"]:
            pattern = r"\b" + re.escape(kw) + r"\b"
            matches = re.findall(pattern, clean_text)
            count += len(matches)
        scores[domain] = count

    max_score = max(scores.values()) if scores else 0
    if max_score == 0:
        return "architectural_sanctuary"

    for domain in DOMAIN_PRIORITY:
        if scores.get(domain, 0) == max_score:
            return domain

    return "architectural_sanctuary"

