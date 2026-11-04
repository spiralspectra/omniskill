"""Cinematic Optical Lens & Sensor Framing Suite (PM-FEAT-007).

Provides optical calculations, field-of-view (FOV) mapping across film and digital sensor
standards, hyperfocal distance calculations, prompt token synthesis, and post-production
optical lens metadata CSV exporting.
"""

import csv
import io
import math
from pathlib import Path
from typing import Dict, Tuple, Union

from omni_director.schemas import MasterProductionBible, OpticalLensSpec, SensorFormat

# Standard active sensor gate dimensions in millimeters (width x height)
SENSOR_DIMENSIONS_MM: Dict[str, Tuple[float, float]] = {
    "super_35": (24.89, 18.66),
    "full_frame": (36.00, 24.00),
    "arri_lf": (36.70, 25.54),
    "imax_70mm": (70.41, 52.63),
    "vistavision": (40.96, 21.60),
}


def get_sensor_dimensions(sensor_format: Union[SensorFormat, str]) -> Tuple[float, float]:
    """Resolves width and height in mm for any SensorFormat or string alias."""
    key = str(getattr(sensor_format, "value", sensor_format)).lower()
    if "super" in key or "35" in key and "full" not in key:
        return SENSOR_DIMENSIONS_MM["super_35"]
    if "arri" in key or "large" in key:
        return SENSOR_DIMENSIONS_MM["arri_lf"]
    if "imax" in key:
        return SENSOR_DIMENSIONS_MM["imax_70mm"]
    if "vista" in key:
        return SENSOR_DIMENSIONS_MM["vistavision"]
    return SENSOR_DIMENSIONS_MM["full_frame"]


def calculate_sensor_fov(
    sensor_format: Union[SensorFormat, str],
    focal_length_mm: int,
    anamorphic_squeeze: float = 1.0,
) -> Tuple[float, float]:
    """Calculates horizontal and vertical Field of View (FOV) in degrees.

    FOV = 2 * atan((dimension * squeeze) / (2 * focal_length)) * (180 / pi).
    Horizontal dimension accounts for optical anamorphic desqueeze.
    """
    if focal_length_mm <= 0:
        focal_length_mm = 35

    w_mm, h_mm = get_sensor_dimensions(sensor_format)
    squeeze = max(1.0, float(anamorphic_squeeze))

    # Horizontal FOV (accounting for anamorphic squeeze)
    h_fov = 2.0 * math.atan((w_mm * squeeze) / (2.0 * focal_length_mm)) * (180.0 / math.pi)
    # Vertical FOV
    v_fov = 2.0 * math.atan(h_mm / (2.0 * focal_length_mm)) * (180.0 / math.pi)

    return (round(h_fov, 2), round(v_fov, 2))


def calculate_hyperfocal_distance(
    focal_length_mm: int,
    aperture_t_stop: float,
    circle_of_confusion_mm: float = 0.03,
) -> float:
    """Calculates optical hyperfocal distance in meters.

    H = (focal_length ** 2) / (N * c * 1000)
    where N is aperture (T-stop), c is circle of confusion (0.03mm standard for 35mm).
    """
    if aperture_t_stop <= 0:
        aperture_t_stop = 2.8
    if circle_of_confusion_mm <= 0:
        circle_of_confusion_mm = 0.03

    hyperfocal_m = (focal_length_mm ** 2) / (aperture_t_stop * circle_of_confusion_mm * 1000.0)
    return round(hyperfocal_m, 2)


def format_optical_prompt_token(lens: OpticalLensSpec) -> str:
    """Synthesizes an optical camera and lens prompt descriptor for Gemini Omni."""
    raw_sensor = lens.sensor_format.value if hasattr(lens.sensor_format, "value") else str(lens.sensor_format)
    sensor_title = raw_sensor.split("(")[0].strip()

    squeeze_str = (
        f" ({lens.anamorphic_squeeze:.2f}x anamorphic squeeze)"
        if lens.anamorphic_squeeze > 1.0
        else " spherical"
    )

    return (
        f"Shot on {sensor_title} sensor, {lens.lens_series} {lens.focal_length_mm}mm T{lens.aperture_t_stop:.1f}{squeeze_str}, "
        f"{lens.bokeh_characteristic}, {lens.chromatic_aberration}, {lens.distortion_profile}"
    )


def export_lens_metadata_csv(bible: MasterProductionBible) -> str:
    """Exports structured optical lens and sensor framing metadata as CSV."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        [
            "scene_index",
            "scene_title",
            "sensor_format",
            "focal_length_mm",
            "aperture_t_stop",
            "anamorphic_squeeze",
            "lens_series",
            "horizontal_fov_deg",
            "vertical_fov_deg",
            "hyperfocal_distance_m",
            "bokeh_characteristic",
            "distortion_profile",
        ]
    )

    for idx, scene in enumerate(bible.scenes, start=1):
        lens = scene.optical_lens
        if lens is None and scene.craft_camera and scene.craft_camera.optical_lens:
            lens = scene.craft_camera.optical_lens
        if lens is None and bible.master_lens_package:
            lens = bible.master_lens_package
        if lens is None:
            focal = scene.craft_camera.focal_length_mm if scene.craft_camera else 35
            lens = OpticalLensSpec(focal_length_mm=focal)

        hfov, vfov = calculate_sensor_fov(lens.sensor_format, lens.focal_length_mm, lens.anamorphic_squeeze)
        h_fov_val = lens.horizontal_fov_deg if lens.horizontal_fov_deg is not None else hfov
        v_fov_val = lens.vertical_fov_deg if lens.vertical_fov_deg is not None else vfov
        hyperfocal_val = (
            lens.hyperfocal_distance_m
            if lens.hyperfocal_distance_m is not None
            else calculate_hyperfocal_distance(lens.focal_length_mm, lens.aperture_t_stop)
        )
        sensor_str = lens.sensor_format.value if hasattr(lens.sensor_format, "value") else str(lens.sensor_format)

        writer.writerow(
            [
                scene.scene_index,
                scene.scene_title,
                sensor_str,
                lens.focal_length_mm,
                lens.aperture_t_stop,
                lens.anamorphic_squeeze,
                lens.lens_series,
                h_fov_val,
                v_fov_val,
                hyperfocal_val,
                lens.bokeh_characteristic,
                lens.distortion_profile,
            ]
        )

    return buffer.getvalue()


def export_lens_metadata_file(bible: MasterProductionBible, output_path: Union[str, Path]) -> Path:
    """Writes optical lens metadata CSV to a file and returns the Path."""
    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(export_lens_metadata_csv(bible), encoding="utf-8")
    return out_p
