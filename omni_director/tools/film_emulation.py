"""Physical Film Stock Emulation & Chemical Chemistry Engine (PM-FEAT-017).

Provides mathematical simulation of microscopic silver halide / dye cloud RMS
granularity, boundary point-spread halation with rem-jet backing attenuation,
camera gate weave mechanics (Bell & Howell 2709 register pins), DaVinci Resolve
DCTL shader generation, Avid Log Exchange (ALE) film stock manifests, and
Gemini Omni CRAFT film prompt token authoring.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from omni_director.schemas import (
    FilmGaugeFormat,
    FilmStockManufacturer,
    FilmStockSpec,
    GateWeavePhysicsSpec,
    GrainPhysicsSpec,
    HalationPhysicsSpec,
    MasterProductionBible,
)


# ==============================================================================
# Gauge Area Normalization Factors
# ==============================================================================

GAUGE_GRAIN_SCALE_FACTORS: Dict[str, float] = {
    FilmGaugeFormat.GAUGE_16MM.value: 2.45,
    FilmGaugeFormat.GAUGE_35MM_2PERF.value: 1.38,
    FilmGaugeFormat.GAUGE_35MM_3PERF.value: 1.18,
    FilmGaugeFormat.GAUGE_35MM_4PERF.value: 1.00,
    FilmGaugeFormat.GAUGE_65MM_IMAX.value: 0.38,
}


# ==============================================================================
# Curated Film Stock Presets
# ==============================================================================

FILM_STOCK_PRESETS: Dict[str, FilmStockSpec] = {
    "kodak_vision3_500t": FilmStockSpec(
        stock_name="Kodak Vision3 500T",
        stock_code="5219",
        manufacturer=FilmStockManufacturer.KODAK,
        gauge=FilmGaugeFormat.GAUGE_35MM_4PERF,
        iso_rating=500,
        color_temp_k=3200,
        push_pull_stops=0.0,
        grain=GrainPhysicsSpec(
            rms_granularity=4.2,
            grain_size_microns=8.5,
            shadow_grain_weight=1.1,
            midtone_grain_weight=1.4,
            highlight_grain_weight=0.6,
        ),
        halation=HalationPhysicsSpec(
            halation_radius_pixels=6.5,
            halation_intensity=0.45,
            rem_jet_opacity=0.85,
            specular_threshold_nits=350.0,
            chromatic_tint_rgb=[1.0, 0.28, 0.08],
        ),
        gate_weave=GateWeavePhysicsSpec(
            lateral_drift_microns=1.2,
            vertical_judder_microns=0.8,
            registration_pin_type="bell_howell_2709",
            frequency_hz=24.0,
        ),
        description="Benchmark modern high-speed tungsten color negative film stock with rich toe latitude and distinct warm halation",
    ),
    "kodak_vision3_250d": FilmStockSpec(
        stock_name="Kodak Vision3 250D",
        stock_code="5207",
        manufacturer=FilmStockManufacturer.KODAK,
        gauge=FilmGaugeFormat.GAUGE_35MM_4PERF,
        iso_rating=250,
        color_temp_k=5500,
        push_pull_stops=0.0,
        grain=GrainPhysicsSpec(
            rms_granularity=3.2,
            grain_size_microns=6.2,
            shadow_grain_weight=0.9,
            midtone_grain_weight=1.2,
            highlight_grain_weight=0.5,
        ),
        halation=HalationPhysicsSpec(
            halation_radius_pixels=5.0,
            halation_intensity=0.35,
            rem_jet_opacity=0.90,
            specular_threshold_nits=400.0,
            chromatic_tint_rgb=[1.0, 0.25, 0.05],
        ),
        gate_weave=GateWeavePhysicsSpec(
            lateral_drift_microns=0.9,
            vertical_judder_microns=0.6,
            registration_pin_type="bell_howell_2709",
            frequency_hz=24.0,
        ),
        description="Clean daylight balanced negative stock with micro-fine silver dye clouds and natural skin tonality",
    ),
    "fuji_eterna_500t": FilmStockSpec(
        stock_name="Fujifilm Eterna 500T",
        stock_code="8573",
        manufacturer=FilmStockManufacturer.FUJI,
        gauge=FilmGaugeFormat.GAUGE_35MM_4PERF,
        iso_rating=500,
        color_temp_k=3200,
        push_pull_stops=0.0,
        grain=GrainPhysicsSpec(
            rms_granularity=4.5,
            grain_size_microns=9.0,
            shadow_grain_weight=1.2,
            midtone_grain_weight=1.3,
            highlight_grain_weight=0.7,
        ),
        halation=HalationPhysicsSpec(
            halation_radius_pixels=7.2,
            halation_intensity=0.40,
            rem_jet_opacity=0.82,
            specular_threshold_nits=320.0,
            chromatic_tint_rgb=[0.95, 0.32, 0.12],
        ),
        gate_weave=GateWeavePhysicsSpec(
            lateral_drift_microns=1.3,
            vertical_judder_microns=0.9,
            registration_pin_type="mitchell_dual_pin",
            frequency_hz=24.0,
        ),
        description="Subtle, pastel-biased Japanese color negative emulsion with gentle highlight roll-off and cool shadow separation",
    ),
    "ilford_hp5_plus_400": FilmStockSpec(
        stock_name="Ilford HP5 Plus 400",
        stock_code="HP5-135",
        manufacturer=FilmStockManufacturer.ILFORD,
        gauge=FilmGaugeFormat.GAUGE_35MM_4PERF,
        iso_rating=400,
        color_temp_k=5500,
        push_pull_stops=0.0,
        grain=GrainPhysicsSpec(
            rms_granularity=5.8,
            grain_size_microns=11.5,
            shadow_grain_weight=1.3,
            midtone_grain_weight=1.6,
            highlight_grain_weight=0.9,
        ),
        halation=HalationPhysicsSpec(
            halation_radius_pixels=8.0,
            halation_intensity=0.55,
            rem_jet_opacity=0.75,
            specular_threshold_nits=280.0,
            chromatic_tint_rgb=[1.0, 1.0, 1.0],
        ),
        gate_weave=GateWeavePhysicsSpec(
            lateral_drift_microns=1.5,
            vertical_judder_microns=1.0,
            registration_pin_type="bell_howell_2709",
            frequency_hz=24.0,
        ),
        description="Legendary black-and-white cubic silver crystal film stock with punchy midtone contrast and gritty texture",
    ),
}


def synthesize_default_film_stock(
    manufacturer: Union[FilmStockManufacturer, str] = FilmStockManufacturer.KODAK,
    gauge: Union[FilmGaugeFormat, str] = FilmGaugeFormat.GAUGE_35MM_4PERF,
) -> FilmStockSpec:
    """Synthesizes a production default film stock specification."""
    m_val = manufacturer.value if hasattr(manufacturer, "value") else str(manufacturer).lower()
    g_val = gauge.value if hasattr(gauge, "value") else str(gauge).lower()

    if "fuji" in m_val:
        stock = FILM_STOCK_PRESETS["fuji_eterna_500t"].model_copy(deep=True)
    elif "ilford" in m_val:
        stock = FILM_STOCK_PRESETS["ilford_hp5_plus_400"].model_copy(deep=True)
    else:
        stock = FILM_STOCK_PRESETS["kodak_vision3_500t"].model_copy(deep=True)

    # Apply gauge format
    try:
        stock.gauge = FilmGaugeFormat(g_val)
    except Exception:
        stock.gauge = FilmGaugeFormat.GAUGE_35MM_4PERF

    return stock


# ==============================================================================
# Microscopic Grain Density Simulation
# ==============================================================================

def calculate_rms_grain_density(
    luminance: float,
    gauge: FilmGaugeFormat,
    rms_rating: float,
) -> float:
    """Calculates apparent silver halide / dye cloud grain density at a given luminance.

    Applies the photographic D-log-H density curve where grain visibility peaks in
    Zone III-V (midtones/shadows) and rolls off in highlights (dense dye clouds)
    and deep black toe regions. Normalized against negative gauge area scaling.
    """
    lum = max(0.0, min(1.0, float(luminance)))
    gauge_key = gauge.value if hasattr(gauge, "value") else str(gauge).lower()
    gauge_factor = GAUGE_GRAIN_SCALE_FACTORS.get(gauge_key, 1.0)

    # Zone V midtone bell-curve weighted slightly towards shadows (peak ~0.38)
    # Bell curve: sin(pi * lum^0.75)
    curve = math.sin(math.pi * math.pow(lum, 0.75))
    density = float(rms_rating) * gauge_factor * max(0.05, curve)
    return round(density, 4)


# ==============================================================================
# Point-Spread Halation & Rem-Jet Physics
# ==============================================================================

def simulate_halation_psf(
    specular_intensity: float,
    rem_jet_opacity: float,
    radius: float,
) -> Tuple[float, float, float]:
    """Calculates optical halation point-spread reflection through film base and emulsion.

    Halation occurs when intense specular illumination penetrates the emulsion,
    reflects off the film acetate/polyester backing, and re-exposes the red-sensitive
    emulsion layer from behind. The carbon rem-jet backing layer attenuates this reflection.

    Returns:
        Tuple of (r_intensity, g_intensity, b_intensity) halation bleed response.
    """
    specular = max(0.0, float(specular_intensity))
    rem_jet = max(0.0, min(1.0, float(rem_jet_opacity)))
    r_px = max(0.5, float(radius))

    # Transmittance through anti-halation backing
    transmittance = 1.0 - rem_jet

    # Effective halation energy
    base_glow = specular * transmittance * (1.0 / math.sqrt(r_px * 0.2 + 1.0))

    # Red emulsion sensitivity bias (deep warm amber/crimson halo)
    r = base_glow * 1.00
    g = base_glow * 0.28
    b = base_glow * 0.08

    return (round(r, 4), round(g, 4), round(b, 4))


# ==============================================================================
# Mechanical Camera Gate Weave Kinematics
# ==============================================================================

def calculate_gate_weave_offsets(
    frame_number: int,
    pin_tolerance_microns: float,
    fps: int = 24,
) -> Tuple[float, float]:
    """Calculates mechanical horizontal drift and vertical claw judder offsets.

    Simulates the mechanical film transport through camera gate registration pins
    (e.g., Bell & Howell 2709 register pins).

    Returns:
        Tuple of (dx_microns, dy_microns).
    """
    frame = int(frame_number)
    tol = max(0.0, float(pin_tolerance_microns))
    rate = max(1, int(fps))

    t = frame / rate

    # Dual harmonic lateral oscillation with slow thermal drift
    dx = tol * (
        0.55 * math.sin(2.0 * math.pi * 12.0 * t) +
        0.35 * math.sin(2.0 * math.pi * 3.7 * t) +
        0.10 * math.sin(2.0 * math.pi * 0.4 * t)
    )

    # Vertical pulldown claw registration judder (dominant at framing rate)
    dy = (tol * 0.72) * (
        0.65 * math.cos(2.0 * math.pi * float(rate) * t) +
        0.25 * math.cos(2.0 * math.pi * 5.1 * t) +
        0.10 * math.cos(2.0 * math.pi * 1.2 * t)
    )

    return (round(dx, 4), round(dy, 4))


# ==============================================================================
# DaVinci Resolve DCTL Shader Generation
# ==============================================================================

def generate_davinci_dctl_shader(stock_spec: FilmStockSpec) -> str:
    """Generates an industrial DaVinci Resolve DCTL (Color Transform Language) shader script."""
    m_name = stock_spec.manufacturer.value.upper() if hasattr(stock_spec.manufacturer, "value") else str(stock_spec.manufacturer).upper()
    g_name = stock_spec.gauge.value if hasattr(stock_spec.gauge, "value") else str(stock_spec.gauge)
    tint = stock_spec.halation.chromatic_tint_rgb

    dctl_code = f"""// ==============================================================================
// DaVinci Resolve DCTL: {stock_spec.stock_name} ({stock_spec.stock_code}) Film Emulation
// Manufacturer: {m_name} | Gauge: {g_name}
// Native Balance: {stock_spec.color_temp_k}K | Base ISO: {stock_spec.iso_rating} | Push/Pull: {stock_spec.push_pull_stops:+.1f} stops
// Generated by Omni Movie Director v2.8.0 (PM-FEAT-017)
// ==============================================================================

DEFINE_UI_PARAMS(p_GrainGain, Film Grain Gain, DCTLUI_SLIDER_FLOAT, 1.0, 0.0, 3.0, 0.05)
DEFINE_UI_PARAMS(p_HalationGain, Halation Intensity, DCTLUI_SLIDER_FLOAT, 1.0, 0.0, 3.0, 0.05)
DEFINE_UI_PARAMS(p_GateWeaveGain, Gate Weave Amount, DCTLUI_SLIDER_FLOAT, 1.0, 0.0, 3.0, 0.05)

__DEVICE__ float pseudo_hash(int x, int y, int seed)
{{
    int n = x + y * 57 + seed * 131;
    n = (n << 13) ^ n;
    return (float)(1.0 - ((n * (n * n * 15731 + 789221) + 1376312589) & 0x7fffffff) / 1073741824.0);
}}

__DEVICE__ float3 transform(int p_Width, int p_Height, int p_X, int p_Y, float p_R, float p_G, float p_B)
{{
    // 1. Photographic Non-Linear Logarithmic Density Compression (D-Log-H characteristic)
    float r = p_R;
    float g = p_G;
    float b = p_B;

    // Push/Pull Chemical Compensation ({stock_spec.push_pull_stops:+.1f} EV)
    float ev_comp = {math.pow(2.0, stock_spec.push_pull_stops):.4f}f;
    r *= ev_comp;
    g *= ev_comp;
    b *= ev_comp;

    // Luminance calculation
    float lum = 0.2126f * r + 0.7152f * g + 0.0722f * b;

    // 2. Optical Halation & Rem-Jet Reflection Simulation
    // Specular Threshold: {stock_spec.halation.specular_threshold_nits:.1f} nits
    float spec_thresh = {stock_spec.halation.specular_threshold_nits / 1000.0:.4f}f;
    if (lum > spec_thresh) {{
        float bleed = (lum - spec_thresh) * {stock_spec.halation.halation_intensity:.4f}f * (1.0f - {stock_spec.halation.rem_jet_opacity:.4f}f) * p_HalationGain;
        r += bleed * {tint[0]:.4f}f;
        g += bleed * {tint[1]:.4f}f;
        b += bleed * {tint[2]:.4f}f;
    }}

    // 3. Microscopic Silver Halide / Dye Cloud Grain Synthesis
    // RMS Granularity: {stock_spec.grain.rms_granularity:.2f} | Size: {stock_spec.grain.grain_size_microns:.1f} um
    float grain_weight = {stock_spec.grain.shadow_grain_weight:.2f}f * (1.0f - lum) + {stock_spec.grain.midtone_grain_weight:.2f}f * (4.0f * lum * (1.0f - lum)) + {stock_spec.grain.highlight_grain_weight:.2f}f * lum;
    float noise = pseudo_hash(p_X, p_Y, 19283) * ({stock_spec.grain.rms_granularity:.4f}f / 100.0f) * grain_weight * p_GrainGain;
    r += noise;
    g += noise;
    b += noise;

    // 4. Color Negative Emulation Toe / Shoulder Density Saturation
    // Clamp to non-negative film boundary
    r = _fmaxf(0.0f, r);
    g = _fmaxf(0.0f, g);
    b = _fmaxf(0.0f, b);

    return make_float3(r, g, b);
}}
"""
    return dctl_code


# ==============================================================================
# Avid Log Exchange (ALE) Film Stock Exporter
# ==============================================================================

def generate_film_stock_ale(bible: Any) -> str:
    """Generates an Avid Log Exchange (ALE) film stock manifest string for NLE conform."""
    title = getattr(bible, "project_title", "Omni Film Production")
    scenes = getattr(bible, "scenes", [])
    master_stock = getattr(bible, "master_film_emulation", None) or getattr(bible, "film_emulation", None) or synthesize_default_film_stock()

    fps = 24
    lines: List[str] = [
        "Heading",
        "FIELD_DELIM\tTABS",
        "VIDEO_FORMAT\t1080",
        "FILM_FORMAT\t35mm",
        f"FPS\t{fps}",
        f"PROJECT\t{title}",
        "",
        "Column",
        "Name\tTracks\tStart\tEnd\tDuration\tFilm TC\tStock Name\tStock Code\tGauge\tISO\tColor Temp\tPush Pull\tGrain RMS",
        "",
        "Data",
    ]

    current_frame = 24 * 3600  # Start at 01:00:00:00

    if not scenes:
        # Generate dummy 3 scenes if raw stock
        for i in range(1, 4):
            dur = 240
            tc_in = f"01:{((current_frame // (24 * 60)) % 60):02d}:{((current_frame // 24) % 60):02d}:{(current_frame % 24):02d}"
            end_f = current_frame + dur
            tc_out = f"01:{((end_f // (24 * 60)) % 60):02d}:{((end_f // 24) % 60):02d}:{(end_f % 24):02d}"
            gauge_str = master_stock.gauge.value if hasattr(master_stock.gauge, "value") else str(master_stock.gauge)
            lines.append(
                f"Scene_{i:02d}\tV\t{tc_in}\t{tc_out}\t{dur}\t{tc_in}\t{master_stock.stock_name}\t{master_stock.stock_code}\t{gauge_str}\t{master_stock.iso_rating}\t{master_stock.color_temp_k}K\t{master_stock.push_pull_stops:+.1f}\t{master_stock.grain.rms_granularity:.1f}"
            )
            current_frame = end_f
    else:
        for idx, sc in enumerate(scenes):
            sc_stock = getattr(sc, "film_emulation", None) or master_stock
            dur = getattr(sc, "duration_frames", 240)
            tc_in = f"01:{((current_frame // (24 * 60)) % 60):02d}:{((current_frame // 24) % 60):02d}:{(current_frame % 24):02d}"
            end_f = current_frame + dur
            tc_out = f"01:{((end_f // (24 * 60)) % 60):02d}:{((end_f // 24) % 60):02d}:{(end_f % 24):02d}"
            sc_title = getattr(sc, "scene_title", f"Scene_{idx+1:02d}").replace("\t", " ")
            gauge_str = sc_stock.gauge.value if hasattr(sc_stock.gauge, "value") else str(sc_stock.gauge)
            lines.append(
                f"{sc_title}\tV\t{tc_in}\t{tc_out}\t{dur}\t{tc_in}\t{sc_stock.stock_name}\t{sc_stock.stock_code}\t{gauge_str}\t{sc_stock.iso_rating}\t{sc_stock.color_temp_k}K\t{sc_stock.push_pull_stops:+.1f}\t{sc_stock.grain.rms_granularity:.1f}"
            )
            current_frame = end_f

    return "\n".join(lines) + "\n"


def export_film_stock_ale(bible: Any, output_path: Path) -> Path:
    """Exports an Avid Log Exchange (ALE) film stock manifest for NLE conform."""
    target_path = Path(output_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(generate_film_stock_ale(bible), encoding="utf-8")
    return target_path


# ==============================================================================
# Complete Film Emulation Bundle Export
# ==============================================================================

def export_film_emulation_bundle(
    stock_spec: FilmStockSpec,
    output_dir: Path,
    bible: Optional[MasterProductionBible] = None,
) -> Dict[str, Path]:
    """Exports the complete physical film stock emulation bundle."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Spec JSON
    json_path = out_dir / "film_emulation_spec.json"
    json_path.write_text(json.dumps(stock_spec.model_dump(), indent=2), encoding="utf-8")

    # 2. DaVinci Resolve DCTL shader
    dctl_path = out_dir / "film_stock_shader.dctl"
    dctl_path.write_text(generate_davinci_dctl_shader(stock_spec), encoding="utf-8")

    # 3. Avid Log Exchange (ALE) manifest
    ale_path = out_dir / "film_stock.ale"
    export_film_stock_ale(bible or stock_spec, ale_path)

    return {
        "film_dctl": dctl_path,
        "film_ale": ale_path,
        "film_json": json_path,
        "film_bundle": json_path,
    }


# ==============================================================================
# Prompt Token Authoring (Gemini Omni CRAFT Grammar)
# ==============================================================================

def format_film_emulation_prompt_token(stock_spec: FilmStockSpec) -> str:
    """Formats an architectural CRAFT film emulation prompt token for Gemini Omni."""
    gauge_label = {
        FilmGaugeFormat.GAUGE_16MM.value: "16mm",
        FilmGaugeFormat.GAUGE_35MM_2PERF.value: "35mm 2-perf Techniscope",
        FilmGaugeFormat.GAUGE_35MM_3PERF.value: "35mm 3-perf",
        FilmGaugeFormat.GAUGE_35MM_4PERF.value: "35mm 4-perf Academy",
        FilmGaugeFormat.GAUGE_65MM_IMAX.value: "65mm 15-perf IMAX",
    }.get(stock_spec.gauge.value if hasattr(stock_spec.gauge, "value") else str(stock_spec.gauge), "35mm")

    temp_label = f"{stock_spec.color_temp_k}K Tungsten" if stock_spec.color_temp_k <= 3600 else f"{stock_spec.color_temp_k}K Daylight"
    comp_str = f" push {stock_spec.push_pull_stops:+.1f}EV" if abs(stock_spec.push_pull_stops) > 0.05 else ""

    token = (
        f"[FILM_STOCK: {stock_spec.stock_name} ({stock_spec.stock_code}), {gauge_label} negative, "
        f"ISO {stock_spec.iso_rating} {temp_label}{comp_str}, "
        f"RMS granularity {stock_spec.grain.rms_granularity:.1f} ({stock_spec.grain.grain_size_microns:.1f}μm dye clouds), "
        f"halation glow r={stock_spec.halation.halation_radius_pixels:.1f}px intensity={stock_spec.halation.halation_intensity:.2f} "
        f"(rem-jet {int(stock_spec.halation.rem_jet_opacity*100)}%), "
        f"gate weave ±{stock_spec.gate_weave.lateral_drift_microns:.1f}μm ({stock_spec.gate_weave.registration_pin_type})]"
    )
    return token
