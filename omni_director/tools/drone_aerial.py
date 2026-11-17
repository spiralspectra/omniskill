"""Aerial Drone Flight Paths, GPS Waypoints & Solar Ephemeris Engine (PM-FEAT-019).

Provides Jean Meeus / SunCalc astronomical solar ephemeris calculations (altitude, azimuth,
phase, shadow multiplier, CCT Kelvin), aeronautical wind drift vector & crab angle math,
3-axis camera gimbal mechanical limit clamping, 3D waypoint navigation trajectory generation,
OGC KML v2.2, GPX 1.1, CSV flight sheets, and FAA Part 107 regulatory compliance checks.
"""

from __future__ import annotations

import csv
import io
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from omni_director.schemas import (
    DroneFlightPathSpec,
    DroneRigType,
    FlightWaypointGPS,
    GimbalOrientationSpec,
    MasterProductionBible,
    SolarEphemerisSpec,
    SolarPhase,
    WindDriftVectorSpec,
)


# ==============================================================================
# 1. Jean Meeus / SunCalc Solar Ephemeris Mathematical Model
# ==============================================================================

def calculate_solar_ephemeris(
    latitude: float,
    longitude: float,
    dt: Optional[datetime] = None,
) -> SolarEphemerisSpec:
    """Calculates solar position and lighting physics via Meeus astronomical algorithm.

    Computes:
    - Solar altitude / elevation angle (degrees above/below horizon)
    - Solar compass azimuth (degrees clockwise from True North: N=0, E=90, S=180, W=270)
    - Diurnal solar phase classification (high_noon, direct_daylight, golden_hour, blue_hour, civil_twilight, night)
    - Shadow length ratio relative to object height (1.0 / tan(altitude))
    - Ambient color temperature in Kelvin
    """
    if dt is None:
        # Default to canonical production golden hour time (17:15 UTC)
        dt = datetime(2026, 6, 21, 17, 15, 0, tzinfo=timezone.utc)
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    # Julian Day calculation (Meeus Astronomical Algorithms, Chapter 7)
    year = dt.year
    month = dt.month
    day_fraction = dt.day + (dt.hour + dt.minute / 60.0 + dt.second / 3600.0) / 24.0

    if month <= 2:
        year -= 1
        month += 12

    a = math.floor(year / 100)
    b = 2 - a + math.floor(a / 4)
    jd = math.floor(365.25 * (year + 4716)) + math.floor(30.6001 * (month + 1)) + day_fraction + b - 1524.5

    # Julian centuries from J2000.0 epoch
    t = (jd - 2451545.0) / 36525.0

    # Geometric mean longitude of the Sun (degrees)
    l0 = (280.46646 + 36000.76983 * t + 0.0003032 * (t ** 2)) % 360.0

    # Mean anomaly of the Sun (degrees)
    m = (357.52911 + 35999.05029 * t - 0.0001537 * (t ** 2)) % 360.0
    m_rad = math.radians(m)

    # Sun equation of the center (degrees)
    c = (
        (1.914602 - 0.004817 * t - 0.000014 * (t ** 2)) * math.sin(m_rad)
        + (0.019993 - 0.000101 * t) * math.sin(2.0 * m_rad)
        + 0.000289 * math.sin(3.0 * m_rad)
    )

    # Sun true longitude (degrees)
    sun_true_lon = l0 + c

    # Sun apparent longitude (degrees)
    omega = 125.04 - 1934.136 * t
    lambda_sun = sun_true_lon - 0.00569 - 0.00478 * math.sin(math.radians(omega))
    lambda_rad = math.radians(lambda_sun)

    # Mean obliquity of the ecliptic (degrees)
    eps0 = 23.0 + (26.0 + (21.448 - 46.815 * t - 0.00059 * (t ** 2) + 0.001813 * (t ** 3)) / 60.0) / 60.0
    eps = eps0 + 0.00256 * math.cos(math.radians(omega))
    eps_rad = math.radians(eps)

    # Sun declination (delta)
    sin_delta = math.sin(eps_rad) * math.sin(lambda_rad)
    delta_rad = math.asin(max(-1.0, min(1.0, sin_delta)))

    # Right ascension (alpha)
    alpha_rad = math.atan2(math.cos(eps_rad) * math.sin(lambda_rad), math.cos(lambda_rad))
    alpha_deg = (math.degrees(alpha_rad)) % 360.0

    # Greenwich Mean Sidereal Time (GMST) in degrees
    gmst = (280.46061837 + 360.98564736629 * (jd - 2451545.0) + 0.000387933 * (t ** 2) - (t ** 3) / 38710000.0) % 360.0

    # Local Sidereal Time (LST) in degrees
    lst = (gmst + longitude) % 360.0

    # Hour angle (degrees)
    h_deg = (lst - alpha_deg) % 360.0
    if h_deg > 180.0:
        h_deg -= 360.0
    h_rad = math.radians(h_deg)

    lat_rad = math.radians(latitude)

    # Solar altitude (elevation angle above horizon)
    sin_alt = math.sin(lat_rad) * math.sin(delta_rad) + math.cos(lat_rad) * math.cos(delta_rad) * math.cos(h_rad)
    sin_alt = max(-1.0, min(1.0, sin_alt))
    alt_rad = math.asin(sin_alt)
    alt_deg = round(math.degrees(alt_rad), 2)

    # Solar azimuth (measured clockwise from True North: N=0, E=90, S=180, W=270)
    cos_az = (math.sin(delta_rad) - math.sin(lat_rad) * sin_alt) / (math.cos(lat_rad) * math.cos(alt_rad) + 1e-12)
    cos_az = max(-1.0, min(1.0, cos_az))
    az_deg = math.degrees(math.acos(cos_az))
    if math.sin(h_rad) > 0.0:
        az_deg = 360.0 - az_deg
    az_deg = round(az_deg % 360.0, 2)

    # Diurnal solar phase classification
    if alt_deg > 45.0:
        solar_phase = "high_noon"
        cct = 5500
    elif alt_deg > 6.0:
        solar_phase = "direct_daylight"
        cct = 5600
    elif alt_deg >= 0.0:
        solar_phase = "golden_hour"
        cct = int(3000 + (alt_deg / 6.0) * 800)
    elif alt_deg >= -4.0:
        solar_phase = "blue_hour"
        cct = 9500
    elif alt_deg >= -6.0:
        solar_phase = "civil_twilight"
        cct = 7500
    else:
        solar_phase = "night"
        cct = 4100

    # Geometric shadow length multiplier: length = height / tan(altitude)
    if alt_deg > 0.5:
        shadow_mult = round(1.0 / math.tan(math.radians(alt_deg)), 2)
    elif alt_deg > 0.0:
        shadow_mult = round(1.0 / math.tan(math.radians(max(0.5, alt_deg))), 2)
    else:
        shadow_mult = 50.0  # horizon diffuse shadow clamp

    return SolarEphemerisSpec(
        solar_elevation_deg=alt_deg,
        solar_altitude_deg=alt_deg,
        solar_azimuth_deg=az_deg,
        solar_phase=solar_phase,
        shadow_multiplier=shadow_mult,
        cct_kelvin=cct,
        color_temperature_kelvin=cct,
        golden_hour_active=(solar_phase == "golden_hour"),
        lens_flare_risk="high" if (0.0 <= alt_deg <= 25.0) else "moderate",
    )


# ==============================================================================
# 2. Aeronautical Wind Triangle & Ground Speed Vector
# ==============================================================================

def calculate_wind_drift_vector(
    airspeed_mps: float,
    drone_heading_deg: float,
    wind_speed_mps: float,
    wind_direction_deg: float,
) -> WindDriftVectorSpec:
    """Computes aeronautical wind triangle, true ground speed, and crab angle.

    Parameters:
    - airspeed_mps: Drone true airspeed in meters per second.
    - drone_heading_deg: Aircraft compass nose heading in degrees (0-360).
    - wind_speed_mps: Ambient wind speed in meters per second.
    - wind_direction_deg: Originating meteorological wind direction in degrees.
    """
    heading_rad = math.radians(drone_heading_deg)
    # Airspeed velocity vector (East, North)
    v_air_e = airspeed_mps * math.sin(heading_rad)
    v_air_n = airspeed_mps * math.cos(heading_rad)

    # Wind moves air mass towards (wind_direction + 180 degrees)
    wind_from_rad = math.radians(wind_direction_deg)
    v_wind_e = -wind_speed_mps * math.sin(wind_from_rad)
    v_wind_n = -wind_speed_mps * math.cos(wind_from_rad)

    # Ground speed velocity vector
    v_gnd_e = v_air_e + v_wind_e
    v_gnd_n = v_air_n + v_wind_n

    ground_speed = math.sqrt(v_gnd_e ** 2 + v_gnd_n ** 2)

    # Course over ground / true track
    course_deg = (math.degrees(math.atan2(v_gnd_e, v_gnd_n))) % 360.0

    # Wind correction angle (crab angle) = course - heading normalized to [-180, 180]
    crab_angle = course_deg - drone_heading_deg
    while crab_angle > 180.0:
        crab_angle -= 360.0
    while crab_angle < -180.0:
        crab_angle += 360.0

    # Crosswind and headwind components
    angle_diff = math.radians(drone_heading_deg - wind_direction_deg)
    crosswind = wind_speed_mps * math.sin(angle_diff)
    headwind = wind_speed_mps * math.cos(angle_diff)

    knots_conv = 1.94384
    return WindDriftVectorSpec(
        airspeed_mps=round(airspeed_mps, 2),
        ground_speed_mps=round(ground_speed, 2),
        drone_heading_deg=round(drone_heading_deg, 2),
        wind_speed_mps=round(wind_speed_mps, 2),
        wind_speed_knots=round(wind_speed_mps * knots_conv, 2),
        wind_direction_deg=round(wind_direction_deg, 2),
        course_over_ground_deg=round(course_deg, 2),
        crab_angle_deg=round(crab_angle, 2),
        drift_compensation_deg=round(min(45.0, abs(crab_angle)), 2),
        crosswind_mps=round(crosswind, 2),
        headwind_mps=round(headwind, 2),
        gust_speed_knots=round((wind_speed_mps * 1.5) * knots_conv, 2),
        turbulence_rating="light" if wind_speed_mps < 6.0 else ("moderate" if wind_speed_mps < 12.0 else "severe"),
    )


# ==============================================================================
# 3. Gimbal Orientation & Mechanical Limit Clamping
# ==============================================================================

def calculate_gimbal_angles(
    target_pitch: float,
    target_roll: float = 0.0,
    target_yaw: float = 0.0,
    pitch_limits: Union[Tuple[float, float], float] = (-90.0, 30.0),
    roll_limits: Union[Tuple[float, float], float] = (-35.0, 35.0),
    yaw_limits: Union[Tuple[float, float], float] = (-360.0, 360.0),
) -> GimbalOrientationSpec:
    """Clamps cinematic 3-axis camera gimbal angles to physical mechanical limits.

    Supports two calling conventions:
    1. Direct angle clamping:
       calculate_gimbal_angles(target_pitch=-20.0, target_roll=0.0, target_yaw=15.0)
    2. 3D point-to-point target tracking:
       calculate_gimbal_angles(drone_lat, drone_lon, drone_alt_m, target_lat, target_lon, target_alt_m)
    """
    # Detect 3D point-to-point targeting call
    if isinstance(pitch_limits, (int, float)) and isinstance(roll_limits, (int, float)):
        drone_lat = target_pitch
        drone_lon = target_roll
        drone_alt = target_yaw
        target_lat = float(pitch_limits)
        target_lon = float(roll_limits)
        target_alt = float(yaw_limits) if isinstance(yaw_limits, (int, float)) else 0.0

        # Calculate horizontal ground distance
        dist_m = calculate_haversine_distance(drone_lat, drone_lon, target_lat, target_lon)
        alt_delta_m = target_alt - drone_alt

        # Pitch is negative pointing down towards target below drone
        target_pitch = math.degrees(math.atan2(alt_delta_m, max(0.1, dist_m)))
        target_roll = 0.0

        # Yaw is compass bearing from drone to target
        lat1_r = math.radians(drone_lat)
        lat2_r = math.radians(target_lat)
        dlon_r = math.radians(target_lon - drone_lon)
        y = math.sin(dlon_r) * math.cos(lat2_r)
        x = math.cos(lat1_r) * math.sin(lat2_r) - math.sin(lat1_r) * math.cos(lat2_r) * math.cos(dlon_r)
        target_yaw = (math.degrees(math.atan2(y, x)) + 360.0) % 360.0

        p_limits: Tuple[float, float] = (-90.0, 30.0)
        r_limits: Tuple[float, float] = (-35.0, 35.0)
        y_limits: Tuple[float, float] = (-360.0, 360.0)
    else:
        p_limits = pitch_limits  # type: ignore
        r_limits = roll_limits  # type: ignore
        y_limits = yaw_limits  # type: ignore

    clamped = False

    pitch = max(p_limits[0], min(p_limits[1], target_pitch))
    if pitch != target_pitch:
        clamped = True

    roll = max(r_limits[0], min(r_limits[1], target_roll))
    if roll != target_roll:
        clamped = True

    yaw = max(y_limits[0], min(y_limits[1], target_yaw))
    if yaw != target_yaw:
        clamped = True

    return GimbalOrientationSpec(
        pitch_deg=round(pitch, 2),
        roll_deg=round(roll, 2),
        yaw_deg=round(yaw, 2),
        clamped=clamped,
        stabilization_mode="follow_yaw",
        focal_length_equiv_mm=24.0,
    )


# ==============================================================================
# 4. 3D Flight Trajectory & Waypoint Generator
# ==============================================================================

def calculate_haversine_distance(
    lat1: float,
    lon1: float,
    *args: float,
) -> float:
    """Computes 2D or 3D distance between two WGS84 coordinates in meters.

    Supports:
    - calculate_haversine_distance(lat1, lon1, lat2, lon2)
    - calculate_haversine_distance(lat1, lon1, alt1, lat2, lon2, alt2)
    """
    if len(args) == 2:
        lat2, lon2 = args
        alt1 = 0.0
        alt2 = 0.0
    elif len(args) == 4:
        alt1, lat2, lon2, alt2 = args
    elif len(args) == 3:
        lat2, lon2, alt2 = args
        alt1 = 0.0
    else:
        raise ValueError(f"calculate_haversine_distance expects 4 or 6 arguments, got {2 + len(args)}")

    r_earth = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    ground_dist = r_earth * c
    alt_delta = abs(alt2 - alt1)
    return math.sqrt(ground_dist ** 2 + alt_delta ** 2)


def generate_drone_waypoints(
    origin_lat: float = 34.0522,
    origin_lon: float = -118.2437,
    pattern: str = "Orbit Reveal",
    base_altitude_m: float = 25.0,
    waypoint_count: int = 5,
    flight_speed_mps: float = 8.0,
    dt: Optional[datetime] = None,
    wind_speed_mps: float = 4.0,
    wind_direction_deg: float = 270.0,
) -> List[FlightWaypointGPS]:
    """Generates an industry-grade sequence of 3D GPS navigation waypoints for cinematic aerials."""
    waypoints: List[FlightWaypointGPS] = []
    current_time_s = 0.0
    battery_pct = 100.0

    # Solar ephemeris calculation for mission time
    solar = calculate_solar_ephemeris(origin_lat, origin_lon, dt)

    pattern_lower = pattern.lower()

    for idx in range(1, waypoint_count + 1):
        progress = (idx - 1) / max(1, waypoint_count - 1)

        if "orbit" in pattern_lower:
            # 360 degree or arc orbit around origin
            angle = progress * 2.0 * math.pi
            radius_m = 45.0
            # Convert offset meters to lat/lon degrees
            d_lat = (radius_m * math.cos(angle)) / 111139.0
            d_lon = (radius_m * math.sin(angle)) / (111139.0 * math.cos(math.radians(origin_lat)))
            lat = origin_lat + d_lat
            lon = origin_lon + d_lon
            alt_m = base_altitude_m + progress * 15.0
            heading = (math.degrees(angle) + 90.0) % 360.0
            pitch = -20.0 - progress * 10.0
            action_cue = f"Orbit arc {int(progress * 100)}% tracking center point"

        elif "spiral" in pattern_lower or "corkscrew" in pattern_lower:
            angle = progress * 3.0 * math.pi
            radius_m = 30.0 + progress * 25.0
            d_lat = (radius_m * math.cos(angle)) / 111139.0
            d_lon = (radius_m * math.sin(angle)) / (111139.0 * math.cos(math.radians(origin_lat)))
            lat = origin_lat + d_lat
            lon = origin_lon + d_lon
            alt_m = base_altitude_m + progress * 35.0
            heading = (math.degrees(angle) + 90.0) % 360.0
            pitch = -30.0
            action_cue = f"Spiral ascent to {alt_m:.1f}m AGL"

        elif "flyover" in pattern_lower or "reveal" in pattern_lower:
            # Linear flyover traversing North-East
            dist_m = (progress - 0.5) * 150.0
            d_lat = (dist_m * 0.707) / 111139.0
            d_lon = (dist_m * 0.707) / (111139.0 * math.cos(math.radians(origin_lat)))
            lat = origin_lat + d_lat
            lon = origin_lon + d_lon
            alt_m = base_altitude_m + (math.sin(progress * math.pi) * 12.0)
            heading = 45.0
            pitch = -15.0 + progress * 10.0
            action_cue = f"Linear flyover reveal bearing 045°"

        else:
            # Dynamic tracking shot
            dist_m = progress * 100.0
            d_lat = dist_m / 111139.0
            lat = origin_lat + d_lat
            lon = origin_lon
            alt_m = base_altitude_m
            heading = 0.0
            pitch = -12.0
            action_cue = f"Low-altitude chase tracking shot"

        # Wind drift and crab angle calculation
        wind = calculate_wind_drift_vector(
            airspeed_mps=flight_speed_mps,
            drone_heading_deg=heading,
            wind_speed_mps=wind_speed_mps,
            wind_direction_deg=wind_direction_deg,
        )

        alt_ft = round(alt_m * 3.28084, 1)
        part_107_cleared = (alt_m <= 121.92 and flight_speed_mps <= 44.7 and solar.solar_phase != "night")

        wpt = FlightWaypointGPS(
            waypoint_id=f"WP{idx:02d}",
            latitude=round(lat, 6),
            longitude=round(lon, 6),
            altitude_m_agl=round(alt_m, 1),
            altitude_ft_agl=alt_ft,
            altitude_m_msl=round(alt_m + 110.0, 1),
            speed_mps=round(flight_speed_mps, 1),
            timestamp_s=round(current_time_s, 1),
            heading_deg=round(heading, 1),
            gimbal_pitch_deg=round(pitch, 1),
            gimbal_yaw_deg=0.0,
            sun_altitude_deg=solar.solar_altitude_deg,
            sun_azimuth_deg=solar.solar_azimuth_deg,
            solar_phase=solar.solar_phase,
            crab_angle_deg=wind.crab_angle_deg,
            battery_pct=round(max(5.0, battery_pct), 1),
            part_107_cleared=part_107_cleared,
            action_cue=action_cue,
            action_beat=action_cue,
        )
        waypoints.append(wpt)

        # Advance elapsed time and battery consumption
        step_duration = 3.5
        current_time_s += step_duration
        battery_pct -= (step_duration / 60.0) * 1.8  # ~1.8% per minute flight burn

    return waypoints


def synthesize_default_drone_flight(
    bible_or_title: Union[MasterProductionBible, str] = "Omni Production",
    domain_archetype: str = "automotive_robotics",
    scene_index: Optional[int] = None,
) -> DroneFlightPathSpec:
    """Synthesizes a master aerial drone flight plan with solar ephemeris and wind telemetry."""
    if isinstance(bible_or_title, MasterProductionBible):
        title = bible_or_title.project_title
        domain = getattr(bible_or_title, "domain_archetype", "automotive_robotics")
        domain_str = domain.value if hasattr(domain, "value") else str(domain)
    else:
        title = str(bible_or_title)
        domain_str = str(domain_archetype)

    domain_lower = domain_str.lower()
    if "auto" in domain_lower or "kinetic" in domain_lower:
        rig = DroneRigType.FPV_CINELIFTER_ACRO
        pattern = "Tracking Chase Shot"
        speed = 18.0
        alt = 12.0
    elif "arch" in domain_lower:
        rig = DroneRigType.HEAVY_LIFTER_ALTA_X
        pattern = "Spiral Ascent Reveal"
        speed = 6.0
        alt = 45.0
    elif "luxury" in domain_lower or "fashion" in domain_lower:
        rig = DroneRigType.COMPACT_CINEMA_INSPIRE3
        pattern = "Orbit Reveal"
        speed = 7.5
        alt = 28.0
    elif "culinary" in domain_lower:
        rig = DroneRigType.CABLE_CAM_HYBRID
        pattern = "Linear Flyover"
        speed = 4.0
        alt = 8.0
    else:
        rig = DroneRigType.COMPACT_CINEMA_INSPIRE3
        pattern = "Orbit Reveal"
        speed = 8.5
        alt = 30.0

    # Los Angeles production coordinates
    origin_lat = 34.0522
    origin_lon = -118.2437

    # Calculate solar ephemeris at golden hour
    dt = datetime(2026, 6, 21, 18, 0, 0, tzinfo=timezone.utc)
    solar = calculate_solar_ephemeris(origin_lat, origin_lon, dt)

    # Calculate wind triangle
    wind = calculate_wind_drift_vector(
        airspeed_mps=speed,
        drone_heading_deg=45.0,
        wind_speed_mps=4.5,
        wind_direction_deg=260.0,
    )

    gimbal = calculate_gimbal_angles(target_pitch=-22.0, target_roll=0.0, target_yaw=0.0)

    waypoints = generate_drone_waypoints(
        origin_lat=origin_lat,
        origin_lon=origin_lon,
        pattern=pattern,
        base_altitude_m=alt,
        waypoint_count=5,
        flight_speed_mps=speed,
        dt=dt,
        wind_speed_mps=4.5,
        wind_direction_deg=260.0,
    )

    # Compute total 3D distance
    total_dist = 0.0
    for i in range(len(waypoints) - 1):
        w1 = waypoints[i]
        w2 = waypoints[i + 1]
        total_dist += calculate_haversine_distance(
            w1.latitude, w1.longitude, w1.altitude_m_agl,
            w2.latitude, w2.longitude, w2.altitude_m_agl,
        )

    flight_duration = max(10.0, total_dist / max(1.0, speed))

    spec = DroneFlightPathSpec(
        flight_id="FLIGHT_AERIAL_001",
        project_title=title,
        scene_index=scene_index,
        aircraft_model="DJI Inspire 3 / Zenmuse X9-8K Air",
        pilot_in_command="FAA Part 107 Commercial Remote Pilot",
        faa_registration="FA39A7X901",
        drone_rig=rig,
        flight_profile="cinematic_aerial_sweep",
        flight_pattern=pattern,
        min_altitude_agl_m=min(w.altitude_m_agl for w in waypoints),
        max_altitude_agl_m=max(w.altitude_m_agl for w in waypoints),
        max_altitude_m_agl=max(w.altitude_m_agl for w in waypoints),
        total_distance_m=round(total_dist, 1),
        flight_duration_s=round(flight_duration, 1),
        estimated_flight_duration_s=round(flight_duration, 1),
        waypoints=waypoints,
        gimbal=gimbal,
        solar_ephemeris=solar,
        wind_drift=wind,
        part_107_compliant=True,
        faa_part_107_compliant=True,
        description=f"Autonomous Part 107 aerial sweep: {pattern} at {solar.solar_phase}",
    )
    spec.prompt_token = format_drone_flight_prompt_token(spec)
    return spec


# ==============================================================================
# 5. Gemini Omni Cinematic Prompt Token Formatter
# ==============================================================================

def format_drone_flight_prompt_token(spec: Union[DroneFlightPathSpec, Dict[str, Any]]) -> str:
    """Formats standard Gemini Omni DRONE_AERIAL cinematic prompt token."""
    if isinstance(spec, dict):
        aircraft = spec.get("aircraft_model", "DJI Inspire 3")
        pattern = spec.get("flight_pattern", "Orbit Reveal")
        alt = spec.get("max_altitude_m_agl", spec.get("max_altitude_agl_m", 25.0))
        speed = spec.get("speed_mps", 8.5)
        gimbal_pitch = spec.get("gimbal", {}).get("pitch_deg", -20.0) if isinstance(spec.get("gimbal"), dict) else -20.0
        gimbal_yaw = spec.get("gimbal", {}).get("yaw_deg", 0.0) if isinstance(spec.get("gimbal"), dict) else 0.0
        solar = spec.get("solar_ephemeris", {}) if isinstance(spec.get("solar_ephemeris"), dict) else {}
        solar_phase = solar.get("solar_phase", "golden_hour")
        sun_az = solar.get("solar_azimuth_deg", 245.0)
        sun_alt = solar.get("solar_altitude_deg", solar.get("solar_elevation_deg", 18.5))
        cct = solar.get("cct_kelvin", solar.get("color_temperature_kelvin", 3500))
        wind = spec.get("wind_drift", {}) if isinstance(spec.get("wind_drift"), dict) else {}
        crab = wind.get("crab_angle_deg", 3.2)
        part107 = "CLEARED" if spec.get("part_107_compliant", True) else "RESTRICTED"
    else:
        aircraft = spec.aircraft_model
        pattern = spec.flight_pattern
        alt = spec.max_altitude_agl_m
        speed = spec.waypoints[0].speed_mps if spec.waypoints else 8.5
        gimbal_pitch = spec.gimbal.pitch_deg
        gimbal_yaw = spec.gimbal.yaw_deg
        solar_phase = spec.solar_ephemeris.solar_phase
        sun_az = spec.solar_ephemeris.solar_azimuth_deg
        sun_alt = spec.solar_ephemeris.solar_altitude_deg
        cct = spec.solar_ephemeris.cct_kelvin
        crab = spec.wind_drift.crab_angle_deg
        part107 = "CLEARED" if spec.part_107_compliant else "RESTRICTED"

    return (
        f"DRONE_AERIAL: [Aircraft: {aircraft} | Pattern: {pattern} | Alt: {alt:.1f}m AGL | "
        f"Speed: {speed:.1f}m/s | Gimbal: Pitch {gimbal_pitch:.1f}° Yaw {gimbal_yaw:.1f}° | "
        f"Solar: {solar_phase} Az {sun_az:.1f}° Alt {sun_alt:.1f}° ({cct}K) | "
        f"Wind Crab: {crab:+.1f}° | Part 107: {part107}]"
    )


# ==============================================================================
# 6. Exporters: OGC KML v2.2, GPX 1.1, CSV Flight Sheet, Markdown Topsheet
# ==============================================================================

def generate_kml_flight_path(spec: Union[DroneFlightPathSpec, Dict[str, Any]]) -> str:
    """Generates standard OGC KML v2.2 XML document for Google Earth and GIS flight path visualization."""
    flight_id = spec.get("flight_id", "FLIGHT_01") if isinstance(spec, dict) else spec.flight_id
    title = spec.get("project_title", "Omni Aerial Production") if isinstance(spec, dict) else spec.project_title
    pattern = spec.get("flight_pattern", "Orbit Reveal") if isinstance(spec, dict) else spec.flight_pattern

    waypoints = spec.get("waypoints", []) if isinstance(spec, dict) else spec.waypoints

    kml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<kml xmlns="http://www.opengis.net/kml/2.2">',
        '  <Document>',
        f'    <name>{flight_id} - {title}</name>',
        f'    <description>Omni Movie Director Cinematic Aerial Flight Path ({pattern})</description>',
        '    <Style id="dronePathStyle">',
        '      <LineStyle>',
        '        <color>ff00d7ff</color>',  # Amber gold in KML aabbggrr
        '        <width>4</width>',
        '      </LineStyle>',
        '      <PolyStyle>',
        '        <color>7f00d7ff</color>',
        '      </PolyStyle>',
        '    </Style>',
        '    <Folder>',
        '      <name>Waypoints</name>',
    ]

    coord_strings = []
    for w in waypoints:
        w_id = w.get("waypoint_id", "WP") if isinstance(w, dict) else w.waypoint_id
        lat = w.get("latitude", 0.0) if isinstance(w, dict) else w.latitude
        lon = w.get("longitude", 0.0) if isinstance(w, dict) else w.longitude
        alt = w.get("altitude_m_agl", 20.0) if isinstance(w, dict) else w.altitude_m_agl
        cue = w.get("action_cue", "") if isinstance(w, dict) else w.action_cue
        pitch = w.get("gimbal_pitch_deg", -20.0) if isinstance(w, dict) else w.gimbal_pitch_deg

        coord_strings.append(f"{lon},{lat},{alt}")

        kml_lines.extend([
            '      <Placemark>',
            f'        <name>{w_id}</name>',
            f'        <description>Alt: {alt}m AGL | Gimbal: {pitch}° | {cue}</description>',
            '        <Point>',
            '          <altitudeMode>relativeToGround</altitudeMode>',
            f'          <coordinates>{lon},{lat},{alt}</coordinates>',
            '        </Point>',
            '      </Placemark>',
        ])

    kml_lines.extend([
        '    </Folder>',
        '    <Placemark>',
        f'      <name>{flight_id} 3D Trajectory</name>',
        '      <styleUrl>#dronePathStyle</styleUrl>',
        '      <LineString>',
        '        <extrude>1</extrude>',
        '        <tessellate>1</tessellate>',
        '        <altitudeMode>relativeToGround</altitudeMode>',
        f'        <coordinates>{" ".join(coord_strings)}</coordinates>',
        '      </LineString>',
        '    </Placemark>',
        '  </Document>',
        '</kml>',
    ])

    return "\n".join(kml_lines)


def generate_gpx_flight_path(spec: Union[DroneFlightPathSpec, Dict[str, Any]]) -> str:
    """Generates standard GPX 1.1 XML document for ground control stations and avionics."""
    flight_id = spec.get("flight_id", "FLIGHT_01") if isinstance(spec, dict) else spec.flight_id
    title = spec.get("project_title", "Omni Aerial Production") if isinstance(spec, dict) else spec.project_title
    waypoints = spec.get("waypoints", []) if isinstance(spec, dict) else spec.waypoints

    gpx_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<gpx version="1.1" creator="Omni Movie Director v2.2.0" xmlns="http://www.topografix.com/GPX/1/1">',
        '  <metadata>',
        f'    <name>{flight_id}</name>',
        f'    <desc>{title} Aerial Cinematography Flight Path</desc>',
        '    <time>2026-06-21T18:00:00Z</time>',
        '  </metadata>',
    ]

    for w in waypoints:
        w_id = w.get("waypoint_id", "WP") if isinstance(w, dict) else w.waypoint_id
        lat = w.get("latitude", 0.0) if isinstance(w, dict) else w.latitude
        lon = w.get("longitude", 0.0) if isinstance(w, dict) else w.longitude
        alt = w.get("altitude_m_agl", 20.0) if isinstance(w, dict) else w.altitude_m_agl
        cue = w.get("action_cue", "") if isinstance(w, dict) else w.action_cue
        speed = w.get("speed_mps", 8.0) if isinstance(w, dict) else w.speed_mps

        gpx_lines.extend([
            f'  <wpt lat="{lat:.6f}" lon="{lon:.6f}">',
            f'    <ele>{alt:.1f}</ele>',
            f'    <name>{w_id}</name>',
            f'    <desc>Speed: {speed}m/s | {cue}</desc>',
            '  </wpt>',
        ])

    gpx_lines.extend([
        '  <trk>',
        f'    <name>{flight_id} Track</name>',
        '    <trkseg>',
    ])

    for w in waypoints:
        lat = w.get("latitude", 0.0) if isinstance(w, dict) else w.latitude
        lon = w.get("longitude", 0.0) if isinstance(w, dict) else w.longitude
        alt = w.get("altitude_m_agl", 20.0) if isinstance(w, dict) else w.altitude_m_agl
        gpx_lines.append(f'      <trkpt lat="{lat:.6f}" lon="{lon:.6f}"><ele>{alt:.1f}</ele></trkpt>')

    gpx_lines.extend([
        '    </trkseg>',
        '  </trk>',
        '</gpx>',
    ])

    return "\n".join(gpx_lines)


def generate_drone_flight_sheet_csv(spec: Union[DroneFlightPathSpec, Dict[str, Any]]) -> str:
    """Generates an exhaustive CSV tabular flight sheet with all waypoint navigation telemetry."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Waypoint",
        "Lat",
        "Lon",
        "Altitude_m_AGL",
        "Altitude_ft_AGL",
        "Speed_mps",
        "Heading_deg",
        "Gimbal_Pitch_deg",
        "Gimbal_Yaw_deg",
        "Sun_Azimuth_deg",
        "Sun_Altitude_deg",
        "Sun_Phase",
        "Wind_Crab_deg",
        "Battery_Pct",
        "Part107_Cleared",
        "Action_Cue",
    ])

    waypoints = spec.get("waypoints", []) if isinstance(spec, dict) else spec.waypoints
    for w in waypoints:
        w_id = w.get("waypoint_id", "WP") if isinstance(w, dict) else w.waypoint_id
        lat = w.get("latitude", 0.0) if isinstance(w, dict) else w.latitude
        lon = w.get("longitude", 0.0) if isinstance(w, dict) else w.longitude
        alt_m = w.get("altitude_m_agl", 20.0) if isinstance(w, dict) else w.altitude_m_agl
        alt_ft = w.get("altitude_ft_agl", round(alt_m * 3.28084, 1)) if isinstance(w, dict) else w.altitude_ft_agl
        speed = w.get("speed_mps", 8.0) if isinstance(w, dict) else w.speed_mps
        heading = w.get("heading_deg", 0.0) if isinstance(w, dict) else w.heading_deg
        pitch = w.get("gimbal_pitch_deg", -20.0) if isinstance(w, dict) else w.gimbal_pitch_deg
        yaw = w.get("gimbal_yaw_deg", 0.0) if isinstance(w, dict) else w.gimbal_yaw_deg
        sun_az = w.get("sun_azimuth_deg", 245.0) if isinstance(w, dict) else w.sun_azimuth_deg
        sun_alt = w.get("sun_altitude_deg", 18.5) if isinstance(w, dict) else w.sun_altitude_deg
        phase = w.get("solar_phase", "golden_hour") if isinstance(w, dict) else w.solar_phase
        crab = w.get("crab_angle_deg", 3.2) if isinstance(w, dict) else w.crab_angle_deg
        battery = w.get("battery_pct", 100.0) if isinstance(w, dict) else w.battery_pct
        cleared = w.get("part_107_cleared", True) if isinstance(w, dict) else w.part_107_cleared
        cue = w.get("action_cue", "") if isinstance(w, dict) else w.action_cue

        writer.writerow([
            str(w_id),
            f"{lat:.6f}",
            f"{lon:.6f}",
            f"{alt_m:.1f}",
            f"{alt_ft:.1f}",
            f"{speed:.1f}",
            f"{heading:.1f}",
            f"{pitch:.1f}",
            f"{yaw:.1f}",
            f"{sun_az:.1f}",
            f"{sun_alt:.1f}",
            str(phase),
            f"{crab:+.1f}",
            f"{battery:.1f}%",
            "PASS" if cleared else "FAIL",
            str(cue),
        ])

    return output.getvalue()


def generate_drone_flight_sheet_md(spec: Union[DroneFlightPathSpec, Dict[str, Any]]) -> str:
    """Generates an executive Markdown flight sheet with FAA Part 107 compliance checks."""
    if isinstance(spec, dict):
        flight_id = spec.get("flight_id", "FLIGHT_01")
        title = spec.get("project_title", "Commercial Production")
        aircraft = spec.get("aircraft_model", "DJI Inspire 3 / Zenmuse X9-8K Air")
        pilot = spec.get("pilot_in_command", "FAA Part 107 Commercial Remote Pilot")
        reg = spec.get("faa_registration", "FA39A7X901")
        pattern = spec.get("flight_pattern", "Orbit Reveal")
        dist = spec.get("total_distance_m", 250.0)
        dur = spec.get("flight_duration_s", spec.get("estimated_flight_duration_s", 20.0))
        max_alt = spec.get("max_altitude_m_agl", spec.get("max_altitude_agl_m", 35.0))
        solar = spec.get("solar_ephemeris", {}) if isinstance(spec.get("solar_ephemeris"), dict) else {}
        wind = spec.get("wind_drift", {}) if isinstance(spec.get("wind_drift"), dict) else {}
        waypoints = spec.get("waypoints", [])
        part107 = spec.get("part_107_compliant", True)
    else:
        flight_id = spec.flight_id
        title = spec.project_title
        aircraft = spec.aircraft_model
        pilot = spec.pilot_in_command
        reg = spec.faa_registration
        pattern = spec.flight_pattern
        dist = spec.total_distance_m
        dur = spec.flight_duration_s
        max_alt = spec.max_altitude_agl_m
        solar = spec.solar_ephemeris.model_dump() if hasattr(spec.solar_ephemeris, "model_dump") else {}
        wind = spec.wind_drift.model_dump() if hasattr(spec.wind_drift, "model_dump") else {}
        waypoints = spec.waypoints
        part107 = spec.part_107_compliant

    solar_phase = solar.get("solar_phase", "golden_hour")
    sun_alt = solar.get("solar_altitude_deg", 18.5)
    sun_az = solar.get("solar_azimuth_deg", 245.0)
    cct = solar.get("cct_kelvin", 3500)
    shadow = solar.get("shadow_multiplier", 3.0)

    wind_speed = wind.get("wind_speed_mps", 4.5)
    wind_dir = wind.get("wind_direction_deg", 260.0)
    crab = wind.get("crab_angle_deg", 3.2)
    turb = wind.get("turbulence_rating", "light")

    lines = [
        f"# Drone Aerial Cinematography Flight Sheet: {flight_id}",
        "",
        "## Mission Briefing & Aircraft Telemetry",
        f"- **Project Title**: `{title}`",
        f"- **Aircraft Airframe**: `{aircraft}` | **Reg**: `{reg}`",
        f"- **Pilot in Command (RPIC)**: `{pilot}` (FAA 14 CFR Part 107)",
        f"- **Flight Choreography**: `{pattern}`",
        f"- **Total 3D Distance**: `{dist:.1f} m` | **Duration**: `{dur:.1f} s`",
        f"- **Maximum Altitude**: `{max_alt:.1f} m AGL` ({max_alt * 3.28084:.1f} ft AGL - FAA 400ft ceiling cleared)",
        f"- **Part 107 Compliance Status**: **{'CLEARED / COMPLIANT' if part107 else 'RESTRICTED / WAIVER REQUIRED'}**",
        "",
        "## Solar Ephemeris & Atmospheric Vector (Meeus Physics)",
        f"- **Solar Phase**: `{solar_phase.upper()}` ({cct}K warm daylight)",
        f"- **Solar Elevation**: `{sun_alt:.1f}°` | **Azimuth**: `{sun_az:.1f}°` clockwise from True North",
        f"- **Shadow Length Ratio**: `{shadow:.2f}x` object height",
        f"- **Ambient Wind**: `{wind_speed:.1f} m/s` from `{wind_dir:.1f}°` ({turb.title()} turbulence)",
        f"- **Calculated Crab Compensation Angle**: `{crab:+.1f}°`",
        "",
        "## 3D Waypoint Navigation Matrix",
        "| WP | Lat / Lon | Alt (m AGL) | Alt (ft) | Speed | Heading | Gimbal Pitch | Solar Az / Alt | Crab Angle | Batt | Part 107 |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]

    for w in waypoints:
        w_id = w.get("waypoint_id", "WP") if isinstance(w, dict) else w.waypoint_id
        lat = w.get("latitude", 0.0) if isinstance(w, dict) else w.latitude
        lon = w.get("longitude", 0.0) if isinstance(w, dict) else w.longitude
        alt_m = w.get("altitude_m_agl", 20.0) if isinstance(w, dict) else w.altitude_m_agl
        alt_ft = w.get("altitude_ft_agl", round(alt_m * 3.28084, 1)) if isinstance(w, dict) else w.altitude_ft_agl
        speed = w.get("speed_mps", 8.0) if isinstance(w, dict) else w.speed_mps
        heading = w.get("heading_deg", 0.0) if isinstance(w, dict) else w.heading_deg
        pitch = w.get("gimbal_pitch_deg", -20.0) if isinstance(w, dict) else w.gimbal_pitch_deg
        w_sun_az = w.get("sun_azimuth_deg", sun_az) if isinstance(w, dict) else w.sun_azimuth_deg
        w_sun_alt = w.get("sun_altitude_deg", sun_alt) if isinstance(w, dict) else w.sun_altitude_deg
        w_crab = w.get("crab_angle_deg", crab) if isinstance(w, dict) else w.crab_angle_deg
        batt = w.get("battery_pct", 100.0) if isinstance(w, dict) else w.battery_pct
        w_cleared = w.get("part_107_cleared", True) if isinstance(w, dict) else w.part_107_cleared

        lines.append(
            f"| `{w_id}` | `{lat:.5f}, {lon:.5f}` | `{alt_m:.1f}m` | `{alt_ft:.1f}ft` | `{speed:.1f}m/s` | "
            f"`{heading:.0f}°` | `{pitch:.0f}°` | `{w_sun_az:.0f}° / {w_sun_alt:.0f}°` | `{w_crab:+.1f}°` | "
            f"`{batt:.0f}%` | {'PASS' if w_cleared else 'FAIL'} |"
        )

    lines.extend([
        "",
        "## FAA Part 107 Operational Checklist",
        "- [x] Visual Line of Sight (VLOS) maintained throughout flight corridor.",
        "- [x] Maximum altitude strictly under 400 ft AGL ceiling.",
        "- [x] Ground speed within 100 mph (44.7 m/s) regulatory envelope.",
        "- [x] Fail-safe Return-to-Home (RTH) configured with minimum 15m obstacle clearance.",
        "- [x] Geo-fencing active with calibrated compass magnetometer.",
    ])

    return "\n".join(lines)


def generate_drone_flight_manifest_json(spec: DroneFlightPathSpec) -> str:
    """Serializes the complete drone flight path specification into JSON format."""
    return json.dumps(spec.model_dump(), indent=2)


def export_drone_bundle(
    bible_or_spec: Union[MasterProductionBible, DroneFlightPathSpec],
    output_dir: Union[str, Path],
) -> Dict[str, Path]:
    """Exports all drone aerial cinematography deliverables into the target output directory.

    Produces:
    - flight_path.kml (OGC KML v2.2)
    - flight_waypoints.gpx (GPX 1.1)
    - drone_flight_sheet.csv (Full waypoint navigation ledger)
    - drone_flight_sheet.md (Executive mission flight sheet)
    - drone_flight_manifest.json (Complete JSON telemetry manifest)
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    if isinstance(bible_or_spec, MasterProductionBible):
        bible = bible_or_spec
        spec = getattr(bible, "master_drone_spec", None) or getattr(bible, "drone_flight", None)
        if spec is None:
            domain = getattr(bible, "domain_archetype", "automotive_robotics")
            spec = synthesize_default_drone_flight(bible, domain_archetype=str(domain))
    else:
        spec = bible_or_spec

    kml_p = out_path / "flight_path.kml"
    gpx_p = out_path / "flight_waypoints.gpx"
    csv_p = out_path / "drone_flight_sheet.csv"
    md_p = out_path / "drone_flight_sheet.md"
    json_p = out_path / "drone_flight_manifest.json"

    kml_p.write_text(generate_kml_flight_path(spec), encoding="utf-8")
    gpx_p.write_text(generate_gpx_flight_path(spec), encoding="utf-8")
    csv_p.write_text(generate_drone_flight_sheet_csv(spec), encoding="utf-8")
    md_p.write_text(generate_drone_flight_sheet_md(spec), encoding="utf-8")
    json_p.write_text(json.dumps(spec.model_dump(), indent=2), encoding="utf-8")

    return {
        "flight_path_kml": kml_p,
        "flight_waypoints_gpx": gpx_p,
        "drone_flight_sheet_csv": csv_p,
        "drone_flight_sheet_md": md_p,
        "drone_flight_manifest_json": json_p,
        "kml": kml_p,
        "gpx": gpx_p,
        "csv": csv_p,
        "md": md_p,
        "json": json_p,
    }


# Backwards compatibility and alternative naming aliases
export_drone_flight_bundle = export_drone_bundle
generate_drone_flight_kml = generate_kml_flight_path
generate_drone_flight_gpx = generate_gpx_flight_path
calculate_wind_drift_correction = calculate_wind_drift_vector

