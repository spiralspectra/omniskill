"""Aerial Drone Flight Paths, GPS Waypoints & Gimbal Telemetry Engine (PM-FEAT-019).

Provides 3D GPS navigation waypoint calculation, WGS84 coordinates, solar ephemeris
alignment, aerodynamic wind drift and crab angle compensation, Google Earth KML
and GPX telemetry export, flight sheet generation, and Gemini Omni CRAFT drone tokens.
"""

from __future__ import annotations

import csv
import io
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from omni_director.schemas import (
    DroneFlightPathSpec,
    DroneRigType,
    FlightWaypointGPS,
    GimbalOrientationSpec,
    MasterProductionBible,
    SolarEphemerisSpec,
    WindDriftVectorSpec,
)


def calculate_solar_ephemeris(
    hour_utc: float = 17.5,
    latitude: float = 34.0522,
    camera_heading_deg: float = 245.0,
) -> SolarEphemerisSpec:
    """Calculates approximate solar position and lens flare risk for aerial cinematography."""
    # Approximate solar elevation and azimuth from time of day
    noon_delta = abs(hour_utc - 12.0)
    elevation = max(-5.0, 65.0 - (noon_delta * 9.5))
    azimuth = (hour_utc / 24.0) * 360.0
    is_golden_hour = 0.0 <= elevation <= 22.0
    rel_bearing = abs(camera_heading_deg - azimuth) % 360.0
    if rel_bearing > 180.0:
        rel_bearing = 360.0 - rel_bearing

    flare_risk = "high" if (is_golden_hour and rel_bearing < 45.0) else "moderate" if rel_bearing < 75.0 else "low"
    kelvin = 3200 if elevation < 10.0 else 3800 if elevation < 25.0 else 5600

    return SolarEphemerisSpec(
        solar_elevation_deg=round(elevation, 1),
        solar_azimuth_deg=round(azimuth, 1),
        golden_hour_active=is_golden_hour,
        lens_flare_risk=flare_risk,
        color_temperature_kelvin=kelvin,
    )


def calculate_wind_drift_correction(
    flight_heading_deg: float = 45.0,
    drone_speed_mps: float = 8.5,
    wind_speed_knots: float = 8.0,
    wind_direction_deg: float = 270.0,
) -> WindDriftVectorSpec:
    """Calculates crab angle aerodynamic drift correction vector for aerial camera stability."""
    wind_speed_mps = wind_speed_knots * 0.514444
    crosswind_angle = math.radians(wind_direction_deg - flight_heading_deg)
    crosswind_component = wind_speed_mps * math.sin(crosswind_angle)
    ratio = max(-1.0, min(1.0, crosswind_component / max(0.1, drone_speed_mps)))
    drift_deg = math.degrees(math.asin(ratio))

    turbulence = (
        "none" if wind_speed_knots < 4.0
        else "light" if wind_speed_knots < 12.0
        else "moderate" if wind_speed_knots < 20.0
        else "severe"
    )

    return WindDriftVectorSpec(
        wind_speed_knots=round(wind_speed_knots, 1),
        wind_direction_deg=round(wind_direction_deg, 1),
        gust_speed_knots=round(wind_speed_knots * 1.4, 1),
        drift_compensation_deg=round(drift_deg, 1),
        turbulence_rating=turbulence,
    )


def format_drone_flight_prompt_token(spec: DroneFlightPathSpec) -> str:
    """Formats a concise CRAFT camera prompt token for aerial drone flight telemetry."""
    rig_val = spec.drone_rig.value if hasattr(spec.drone_rig, "value") else str(spec.drone_rig)
    min_alt = int(round(spec.min_altitude_agl_m))
    max_alt = int(round(spec.max_altitude_agl_m))
    pitch = int(round(spec.gimbal.pitch_deg))
    speed = spec.waypoints[0].speed_mps if spec.waypoints else 8.5
    wind = int(round(spec.wind_drift.wind_speed_knots))
    profile = spec.flight_profile or "flyover_reveal"

    return (
        f"[DRONE_FLIGHT: RIG={rig_val} ALT={min_alt}-{max_alt}m "
        f"PROFILE={profile} GIMBAL_PITCH={pitch}° SPEED={speed:.1f}mps WIND={wind}kt]"
    )


def synthesize_default_drone_flight(
    profile: str = "flyover_reveal",
    alt_m: float = 25.0,
    domain: Optional[str] = None,
    flight_id: str = "FLIGHT_01",
) -> DroneFlightPathSpec:
    """Synthesizes a realistic 3D GPS drone flight path calibrated to domain archetypes."""
    base_lat = 34.0522
    base_lon = -118.2437
    base_msl = 120.0

    rig = DroneRigType.COMPACT_CINEMA_INSPIRE3
    speed = 8.5
    pitch = -18.0
    duration = 15.0

    norm_domain = str(domain or "").lower()
    if "kinetic" in norm_domain or "fpv" in norm_domain or "action" in norm_domain:
        rig = DroneRigType.FPV_CINELIFTER_ACRO
        speed = 18.0
        pitch = -25.0
        profile = "fpv_acro_chase"
    elif "automotive" in norm_domain or "heavy" in norm_domain:
        rig = DroneRigType.HEAVY_LIFTER_ALTA_X
        speed = 14.0
        pitch = -15.0
        profile = "low_altitude_chase"
    elif "fashion" in norm_domain or "sanctuary" in norm_domain or "architectural" in norm_domain:
        rig = DroneRigType.COMPACT_CINEMA_INSPIRE3
        speed = 6.0
        pitch = -12.0
        profile = "orbit_reveal"

    waypoints: List[FlightWaypointGPS] = []
    num_wp = 4

    for i in range(num_wp):
        fraction = i / max(1, num_wp - 1)
        t_s = fraction * duration
        # Trajectory progression along lat/lon heading
        cur_lat = base_lat + (fraction * 0.0015)
        cur_lon = base_lon + (fraction * 0.0018)
        cur_agl = max(2.0, alt_m + (math.sin(fraction * math.pi) * 8.0))
        cur_msl = base_msl + cur_agl
        cue = (
            "Ascent & Establish Framing" if i == 0
            else "Cruising Orbit Sweep" if i == 1
            else "Apex Reveal & Horizon Lock" if i == 2
            else "Kinetic Deceleration & Settle"
        )
        wp = FlightWaypointGPS(
            waypoint_id=i + 1,
            latitude=round(cur_lat, 6),
            longitude=round(cur_lon, 6),
            altitude_m_agl=round(cur_agl, 1),
            altitude_m_msl=round(cur_msl, 1),
            speed_mps=speed,
            timestamp_s=round(t_s, 2),
            heading_deg=round(45.0 + (fraction * 30.0), 1),
            action_cue=cue,
        )
        waypoints.append(wp)

    gimbal = GimbalOrientationSpec(
        pitch_deg=pitch,
        yaw_deg=0.0,
        roll_deg=0.0,
        stabilization_mode="follow_yaw",
        focal_length_equiv_mm=24.0,
    )

    solar = SolarEphemerisSpec(
        solar_elevation_deg=18.5,
        solar_azimuth_deg=245.0,
        golden_hour_active=True,
        lens_flare_risk="moderate",
        color_temperature_kelvin=3500,
    )

    wind = WindDriftVectorSpec(
        wind_speed_knots=8.0,
        wind_direction_deg=270.0,
        gust_speed_knots=12.0,
        drift_compensation_deg=3.2,
        turbulence_rating="light",
    )

    return DroneFlightPathSpec(
        flight_id=flight_id,
        drone_rig=rig,
        flight_profile=profile,
        min_altitude_agl_m=round(min(w.altitude_m_agl for w in waypoints), 1),
        max_altitude_agl_m=round(max(w.altitude_m_agl for w in waypoints), 1),
        total_distance_m=280.0,
        flight_duration_s=duration,
        waypoints=waypoints,
        gimbal=gimbal,
        solar_ephemeris=solar,
        wind_drift=wind,
        faa_part_107_compliant=True,
        description=f"Autonomous GPS waypointed cinematic aerial sweep ({profile})",
    )


def generate_drone_flight_kml(spec: DroneFlightPathSpec, title: str = "Cinematic Flight Path") -> str:
    """Generates an OGC KML 2.2 XML file for Google Earth and DJI Pilot 2 flight plan visualization."""
    coords_list = []
    for wp in spec.waypoints:
        coords_list.append(f"{wp.longitude:.6f},{wp.latitude:.6f},{wp.altitude_m_agl:.1f}")
    coords_str = " ".join(coords_list)

    kml = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<kml xmlns="http://www.opengis.net/kml/2.2">',
        '  <Document>',
        f'    <name>{title}</name>',
        f'    <description>Mission: {spec.flight_id} - Profile: {spec.flight_profile} (Rig: {spec.drone_rig})</description>',
        '    <Style id="flightPathStyle">',
        '      <LineStyle>',
        '        <color>ff00ffff</color>',  # Yellow-cyan path
        '        <width>4</width>',
        '      </LineStyle>',
        '      <PolyStyle>',
        '        <color>7f00aaee</color>',
        '      </PolyStyle>',
        '    </Style>',
        '    <Placemark>',
        f'      <name>{spec.flight_id} Trajectory</name>',
        '      <styleUrl>#flightPathStyle</styleUrl>',
        '      <LineString>',
        '        <extrude>1</extrude>',
        '        <tessellate>1</tessellate>',
        '        <altitudeMode>relativeToGround</altitudeMode>',
        f'        <coordinates>{coords_str}</coordinates>',
        '      </LineString>',
        '    </Placemark>',
    ]

    for wp in spec.waypoints:
        kml.extend([
            '    <Placemark>',
            f'      <name>WP {wp.waypoint_id}: {wp.action_cue}</name>',
            f'      <description>Time: {wp.timestamp_s}s | Alt AGL: {wp.altitude_m_agl}m | Speed: {wp.speed_mps}m/s | Heading: {wp.heading_deg}°</description>',
            '      <Point>',
            '        <altitudeMode>relativeToGround</altitudeMode>',
            f'        <coordinates>{wp.longitude:.6f},{wp.latitude:.6f},{wp.altitude_m_agl:.1f}</coordinates>',
            '      </Point>',
            '    </Placemark>',
        ])

    kml.extend([
        '  </Document>',
        '</kml>',
    ])
    return "\n".join(kml)


def generate_drone_flight_gpx(spec: DroneFlightPathSpec, title: str = "Flight Waypoints") -> str:
    """Generates a standard GPX 1.1 XML file for GPS flight controllers and GIS tools."""
    gpx = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<gpx version="1.1" creator="OmniDirector-v2.13.0" xmlns="http://www.topografix.com/GPX/1/1">',
        '  <metadata>',
        f'    <name>{title}</name>',
        f'    <desc>Flight Plan {spec.flight_id} ({spec.flight_profile})</desc>',
        '  </metadata>',
    ]

    for wp in spec.waypoints:
        gpx.extend([
            f'  <wpt lat="{wp.latitude:.6f}" lon="{wp.longitude:.6f}">',
            f'    <ele>{wp.altitude_m_msl:.1f}</ele>',
            f'    <name>WP_{wp.waypoint_id:02d}</name>',
            f'    <desc>{wp.action_cue} (AGL: {wp.altitude_m_agl}m, Speed: {wp.speed_mps}m/s, Heading: {wp.heading_deg}°)</desc>',
            '  </wpt>',
        ])

    gpx.append('  <trk>')
    gpx.append(f'    <name>{spec.flight_id}_Track</name>')
    gpx.append('    <trkseg>')
    for wp in spec.waypoints:
        gpx.append(f'      <trkpt lat="{wp.latitude:.6f}" lon="{wp.longitude:.6f}">')
        gpx.append(f'        <ele>{wp.altitude_m_msl:.1f}</ele>')
        gpx.append('      </trkpt>')
    gpx.append('    </trkseg>')
    gpx.append('  </trk>')
    gpx.append('</gpx>')
    return "\n".join(gpx)


def generate_drone_flight_sheet_csv(spec: DroneFlightPathSpec) -> str:
    """Generates a flight sheet CSV log table for the remote pilot in command (RPIC) and gimbal operator."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Waypoint",
        "Time_s",
        "Latitude",
        "Longitude",
        "Alt_AGL_m",
        "Alt_MSL_m",
        "Speed_mps",
        "Heading_deg",
        "Gimbal_Pitch_deg",
        "Action_Cue",
    ])
    pitch = spec.gimbal.pitch_deg
    for wp in spec.waypoints:
        writer.writerow([
            wp.waypoint_id,
            f"{wp.timestamp_s:.1f}",
            f"{wp.latitude:.6f}",
            f"{wp.longitude:.6f}",
            f"{wp.altitude_m_agl:.1f}",
            f"{wp.altitude_m_msl:.1f}",
            f"{wp.speed_mps:.1f}",
            f"{wp.heading_deg:.1f}",
            f"{pitch:.1f}",
            wp.action_cue,
        ])
    return output.getvalue()


def generate_drone_flight_sheet_md(spec: DroneFlightPathSpec, project_title: str = "") -> str:
    """Generates an executive flight briefing markdown document with FAA Part 107 compliance."""
    rig_val = spec.drone_rig.value if hasattr(spec.drone_rig, "value") else str(spec.drone_rig)
    lines = [
        f"# Drone Flight Operations Sheet - {project_title or spec.flight_id}",
        "",
        "## Mission Telemetry Overview",
        f"- **Flight ID**: `{spec.flight_id}`",
        f"- **Aircraft Rig**: `{rig_val}`",
        f"- **Flight Choreography Profile**: `{spec.flight_profile}`",
        f"- **Operating Altitude**: `{spec.min_altitude_agl_m}m` - `{spec.max_altitude_agl_m}m` AGL",
        f"- **Total Path Distance**: `{spec.total_distance_m}m`",
        f"- **Flight Duration**: `{spec.flight_duration_s}s`",
        f"- **FAA Part 107 Compliance**: `{'PASS' if spec.faa_part_107_compliant else 'NON-COMPLIANT'}`",
        "",
        "## Camera Gimbal & Optical Setup",
        f"- **Pitch Angle**: `{spec.gimbal.pitch_deg}°`",
        f"- **Yaw Offset**: `{spec.gimbal.yaw_deg}°`",
        f"- **Roll Trim**: `{spec.gimbal.roll_deg}°`",
        f"- **Stabilization Mode**: `{spec.gimbal.stabilization_mode}`",
        f"- **35mm Equiv Focal Length**: `{spec.gimbal.focal_length_equiv_mm}mm`",
        "",
        "## Environmental & Atmospheric Telemetry",
        f"- **Solar Elevation**: `{spec.solar_ephemeris.solar_elevation_deg}°` ({'Golden Hour Active' if spec.solar_ephemeris.golden_hour_active else 'Daylight'})",
        f"- **Solar Azimuth**: `{spec.solar_ephemeris.solar_azimuth_deg}°` | **Lens Flare Risk**: `{spec.solar_ephemeris.lens_flare_risk}`",
        f"- **Color Temperature**: `{spec.solar_ephemeris.color_temperature_kelvin}K`",
        f"- **Wind Velocity**: `{spec.wind_drift.wind_speed_knots} kt` from `{spec.wind_drift.wind_direction_deg}°` (Gusts: `{spec.wind_drift.gust_speed_knots} kt`)",
        f"- **Crab Heading Offset**: `{spec.wind_drift.drift_compensation_deg}°` | **Turbulence**: `{spec.wind_drift.turbulence_rating}`",
        "",
        "## 3D GPS Waypoint Roster",
        "| WP | Time (s) | Latitude | Longitude | AGL (m) | MSL (m) | Speed (m/s) | Heading | Action Cue |",
        "|---|---|---|---|---|---|---|---|---|",
    ]

    for wp in spec.waypoints:
        lines.append(
            f"| {wp.waypoint_id} | {wp.timestamp_s:.1f} | {wp.latitude:.6f} | {wp.longitude:.6f} | "
            f"{wp.altitude_m_agl:.1f} | {wp.altitude_m_msl:.1f} | {wp.speed_mps:.1f} | {wp.heading_deg:.1f}° | {wp.action_cue} |"
        )

    lines.append("")
    return "\n".join(lines)


def export_drone_flight_bundle(
    bible_or_spec: Union[MasterProductionBible, DroneFlightPathSpec],
    output_dir: Union[str, Path],
) -> Dict[str, str]:
    """Exports all drone flight deliverables (KML, GPX, CSV, MD, JSON manifest) into output_dir."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    project_title = "Drone Flight Operations"
    if isinstance(bible_or_spec, MasterProductionBible):
        bible = bible_or_spec
        project_title = bible.project_title
        flight_spec = bible.master_drone_spec or getattr(bible, "drone_spec", None)
        if flight_spec is None:
            # Check scene-level drone specs
            for s in bible.scenes:
                if getattr(s, "drone_flight", None) is not None:
                    flight_spec = s.drone_flight
                    break
        if flight_spec is None:
            domain = getattr(bible, "domain_archetype", None)
            flight_spec = synthesize_default_drone_flight(domain=domain)
    else:
        flight_spec = bible_or_spec

    kml_p = out_path / "flight_path.kml"
    gpx_p = out_path / "flight_waypoints.gpx"
    csv_p = out_path / "drone_flight_sheet.csv"
    md_p = out_path / "drone_flight_sheet.md"
    json_p = out_path / "drone_flight_manifest.json"

    kml_p.write_text(generate_drone_flight_kml(flight_spec, title=project_title), encoding="utf-8")
    gpx_p.write_text(generate_drone_flight_gpx(flight_spec, title=project_title), encoding="utf-8")
    csv_p.write_text(generate_drone_flight_sheet_csv(flight_spec), encoding="utf-8")
    md_p.write_text(generate_drone_flight_sheet_md(flight_spec, project_title=project_title), encoding="utf-8")
    json_p.write_text(json.dumps(flight_spec.model_dump(), indent=2), encoding="utf-8")

    return {
        "drone_kml": str(kml_p),
        "drone_gpx": str(gpx_p),
        "drone_csv": str(csv_p),
        "drone_md": str(md_p),
        "drone_manifest": str(json_p),
    }
